'use strict';

const assert = require('node:assert/strict');
const childProcess = require('node:child_process');
const fs = require('node:fs');
const net = require('node:net');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');
const { _electron: electron } = require('playwright');
const electronExecutable = require('electron');
const { createProject } = require('./project-lifecycle');

const REPO_ROOT = path.resolve(__dirname, '..', '..');
const SURFACE_BOOT_TIMEOUT = 30000;

function freePort() {
    return new Promise((resolve, reject) => {
        const server = net.createServer();
        server.unref();
        server.once('error', reject);
        server.listen(0, '127.0.0.1', () => {
            const address = server.address();
            const port = address && address.port;
            server.close(error => error ? reject(error) : resolve(port));
        });
    });
}

function readJson(filePath) {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function writeJson(filePath, value) {
    fs.writeFileSync(filePath, JSON.stringify(value, null, 2) + '\n', 'utf8');
}

function mark(t, message) {
    console.log(`[studio-playwright] ${message}`);
    t.diagnostic(message);
}

async function waitFor(description, probe, predicate = value => !!value, timeoutMs = 15000) {
    const deadline = Date.now() + timeoutMs;
    let last;
    let lastError;
    while (Date.now() < deadline) {
        try {
            last = await probe();
            lastError = null;
            if (predicate(last)) return last;
        } catch (error) {
            lastError = error;
        }
        await new Promise(resolve => setTimeout(resolve, 50));
    }
    const suffix = lastError
        ? `; last error: ${lastError.message}`
        : `; last value: ${JSON.stringify(last)}`;
    throw new Error(`Timed out waiting for ${description}${suffix}`);
}

function surfaceIdFromPage(page) {
    try {
        return new URL(page.url()).searchParams.get('surface') || 'main';
    } catch (_) {
        return null;
    }
}

async function awaitSurfaceReady(page, surfaceId) {
    await page.waitForFunction(expected => {
        const actual = new URLSearchParams(window.location.search).get('surface') || 'main';
        const boot = window.thestraDatabaseBootState;
        return actual === expected && !!window.thestraStudio && !!boot && boot.done === true;
    }, surfaceId, { timeout: SURFACE_BOOT_TIMEOUT });
    return page;
}

async function openSurface(app, mainPage, surfaceId) {
    const nextWindow = app.waitForEvent('window', { timeout: SURFACE_BOOT_TIMEOUT });
    await mainPage.evaluate(id => window.thestraStudio.openSurface(id), surfaceId);
    return awaitSurfaceReady(await nextWindow, surfaceId);
}

async function setDialogResponse(app, response) {
    await app.evaluate(({ dialog }, nextResponse) => {
        if (!globalThis.__thestraPlaywrightDialog) {
            globalThis.__thestraPlaywrightDialog = { calls: 0, response: nextResponse };
            dialog.showMessageBox = async () => {
                const state = globalThis.__thestraPlaywrightDialog;
                state.calls += 1;
                return { response: state.response };
            };
        }
        globalThis.__thestraPlaywrightDialog.response = nextResponse;
    }, response);
}

async function dialogCalls(app) {
    return app.evaluate(() => globalThis.__thestraPlaywrightDialog
        ? globalThis.__thestraPlaywrightDialog.calls
        : 0);
}

async function requestSurfaceClose(page, surfaceId) {
    return page.evaluate(id => window.thestraStudio.closeSurface(id), surfaceId);
}

function attachDiagnostics(page, label, diagnostics) {
    page.on('pageerror', error => diagnostics.push(`${label} pageerror: ${error.stack || error.message}`));
    page.on('console', message => {
        if (message.type() === 'error') diagnostics.push(`${label} console: ${message.text()}`);
    });
    // Playwright auto-dismisses renderer dialogs when no listener exists. A
    // BrowserWindow can disappear in the same turn as that automatic dismissal,
    // producing a protocol-level "No dialog is showing" race that obscures the
    // Studio behavior we are testing. Own the dialog lifecycle explicitly and
    // make every legacy renderer prompt visible in CI diagnostics instead.
    page.on('dialog', dialog => {
        const description = `${label} dialog(${dialog.type()}): ${dialog.message()}`;
        console.log(`[studio-playwright] ${description}`);
        diagnostics.push(description);
        dialog.dismiss().catch(error => {
            diagnostics.push(`${label} dialog dismissal raced window close: ${error.message}`);
        });
    });
}

async function forceStopElectron(app, electronProcess) {
    if (!electronProcess || !electronProcess.pid || electronProcess.exitCode !== null) return;

    // Test cleanup is deliberately stronger than the behavior under test. Once
    // an assertion has failed we must not ask Studio's user-facing close protocol
    // for permission to exit, because a dirty surface can keep the test runner
    // alive and hide the original assertion. First request Electron's force-exit
    // primitive through Playwright; then kill the process tree if the connection
    // is already wedged.
    try {
        await Promise.race([
            app.evaluate(({ app: electronApp }) => electronApp.exit(0)),
            new Promise(resolve => setTimeout(resolve, 1000)),
        ]);
    } catch (_) {}

    if (electronProcess.exitCode === null && process.platform === 'win32') {
        childProcess.spawnSync('taskkill.exe', ['/PID', String(electronProcess.pid), '/T', '/F'], {
            windowsHide: true,
            stdio: 'ignore',
            timeout: 10000,
        });
    } else if (electronProcess.exitCode === null) {
        try { electronProcess.kill('SIGKILL'); } catch (_) {}
    }
}

test('Playwright drives native EditorSurface transaction lifecycle through real Electron', {
    skip: process.platform !== 'win32',
    timeout: 120000,
}, async t => {
    const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'thestra-playwright-'));
    const projectRoot = path.join(tempRoot, 'project');
    const termsPath = path.join(projectRoot, 'data', 'terms.json');
    const diagnostics = [];
    let app = null;
    let electronProcess = null;
    let appClosed = false;

    try {
        createProject({
            target: projectRoot,
            installRoot: REPO_ROOT,
            name: 'Playwright Fixture',
        });
        assert.equal(readJson(termsPath).project.title, 'Playwright Fixture');

        const [editorPort, bridgePort] = await Promise.all([freePort(), freePort()]);
        app = await electron.launch({
            executablePath: electronExecutable,
            args: [REPO_ROOT, '--project', projectRoot],
            cwd: REPO_ROOT,
            env: {
                ...process.env,
                PORT: String(editorPort),
                EDITOR_PORT: String(editorPort),
                RUNTIME_BRIDGE_PORT: String(bridgePort),
                ELECTRON_DISABLE_GPU: '1',
            },
            timeout: 30000,
        });
        electronProcess = app.process();
        app.on('close', () => { appClosed = true; });

        const mainPage = await app.firstWindow();
        attachDiagnostics(mainPage, 'main', diagnostics);
        await awaitSurfaceReady(mainPage, 'main');
        mark(t, 'main Studio renderer reached semantic Database readiness');

        let databasePage = await openSurface(app, mainPage, 'database');
        attachDiagnostics(databasePage, 'database', diagnostics);
        await app.evaluate(({ BrowserWindow }) => {
            const win = BrowserWindow.getAllWindows().find(candidate =>
                candidate.webContents.getURL().includes('surface=database'));
            if (!win) throw new Error('Database BrowserWindow not found');
            const originalFocus = win.focus.bind(win);
            globalThis.__thestraPlaywrightFocus = { id: win.id, calls: 0 };
            win.focus = function () {
                globalThis.__thestraPlaywrightFocus.calls += 1;
                return originalFocus();
            };
        });
        await mainPage.evaluate(() => window.thestraStudio.openSurface('database'));
        await waitFor('existing Database BrowserWindow focus()',
            () => app.evaluate(() => globalThis.__thestraPlaywrightFocus.calls),
            calls => calls >= 1);
        assert.equal(app.windows().filter(page => surfaceIdFromPage(page) === 'database').length, 1,
            'opening Database twice must reuse one native transaction window');
        mark(t, 'Database singleton was reused and focused');

        await databasePage.evaluate(() => {
            dbPayload.terms.project.title = 'Cancel Probe';
        });
        assert.deepEqual(await databasePage.evaluate(() => changedDbResourceNames()), ['terms']);
        await setDialogResponse(app, 2);
        const cancelCalls = await dialogCalls(app);
        await requestSurfaceClose(databasePage, 'database');
        await waitFor('native Cancel close choice', () => dialogCalls(app), calls => calls > cancelCalls);
        assert.equal(databasePage.isClosed(), false, 'Cancel must keep Database open');
        assert.equal(await databasePage.evaluate(() => dbPayload.terms.project.title), 'Cancel Probe');
        assert.equal(readJson(termsPath).project.title, 'Playwright Fixture');
        mark(t, 'dirty Cancel preserved the working copy without touching Project authority');

        await setDialogResponse(app, 1);
        const discarded = databasePage.waitForEvent('close', { timeout: 15000 });
        await requestSurfaceClose(databasePage, 'database');
        await discarded;
        assert.equal(readJson(termsPath).project.title, 'Playwright Fixture');
        mark(t, 'dirty Discard closed the surface without committing');

        mark(t, 'opening fresh Database surface for Save workflow');
        databasePage = await openSurface(app, mainPage, 'database');
        attachDiagnostics(databasePage, 'database-save', diagnostics);
        const savedTitle = 'Saved Through Playwright';
        await databasePage.evaluate(title => {
            dbPayload.terms.project.title = title;
        }, savedTitle);
        assert.deepEqual(await databasePage.evaluate(() => changedDbResourceNames()), ['terms']);
        await setDialogResponse(app, 0);
        const savedClose = databasePage.waitForEvent('close', { timeout: 15000 });
        await requestSurfaceClose(databasePage, 'database');
        await savedClose;
        assert.equal(readJson(termsPath).project.title, savedTitle,
            'Save close choice must commit Project authority exactly once');
        await mainPage.waitForFunction(title => dbPayload.terms.project.title === title, savedTitle,
            { timeout: 15000 });
        mark(t, 'Save committed terms and clean main sibling re-read the committed resource');

        await new Promise(resolve => setTimeout(resolve, 300));

        mark(t, 'opening Database surface for external stale-write workflow');
        databasePage = await openSurface(app, mainPage, 'database');
        attachDiagnostics(databasePage, 'database-stale', diagnostics);
        const localDirtyTitle = 'Unsaved Local Title';
        const externalTitle = 'External Tool Title';
        await databasePage.evaluate(title => {
            dbPayload.terms.project.title = title;
        }, localDirtyTitle);

        const externalTerms = readJson(termsPath);
        externalTerms.project.title = externalTitle;
        writeJson(termsPath, externalTerms);

        await mainPage.waitForFunction(title => dbPayload.terms.project.title === title, externalTitle,
            { timeout: 15000 });
        await databasePage.waitForFunction(() =>
            typeof window.thestraExternallyChangedResources === 'function'
                && window.thestraExternallyChangedResources().includes('terms'),
        null, { timeout: 15000 });
        assert.equal(await databasePage.evaluate(() => dbPayload.terms.project.title), localDirtyTitle,
            'external invalidation must never overwrite a dirty working copy');
        mark(t, 'external watcher refreshed clean main and preserved dirty Database working copy');

        await setDialogResponse(app, 0);
        const staleResponse = databasePage.waitForResponse(response => {
            try {
                return new URL(response.url()).pathname === '/save'
                    && response.request().method() === 'POST';
            } catch (_) {
                return false;
            }
        }, { timeout: 15000 });
        await requestSurfaceClose(databasePage, 'database');
        const response = await staleResponse;
        const staleResult = await response.json();
        assert.equal(staleResult.success, false, 'stale save must fail');
        assert.equal(databasePage.isClosed(), false, 'failed stale Save must keep Database open');
        assert.equal(readJson(termsPath).project.title, externalTitle,
            'failed stale Save must preserve external authority');
        mark(t, `external stale-write protection rejected unsafe Save (HTTP ${response.status()})`);

        await setDialogResponse(app, 1);
        const staleDiscarded = databasePage.waitForEvent('close', { timeout: 15000 });
        await requestSurfaceClose(databasePage, 'database');
        await staleDiscarded;

        mark(t, 'opening clean Database and Engine surfaces for coordinated shutdown');
        const shutdownDatabase = await openSurface(app, mainPage, 'database');
        const shutdownEngine = await openSurface(app, mainPage, 'engine');
        attachDiagnostics(shutdownDatabase, 'database-shutdown', diagnostics);
        attachDiagnostics(shutdownEngine, 'engine-shutdown', diagnostics);
        assert.ok(app.windows().length >= 3, 'shutdown fixture must have main + secondary surfaces');

        const applicationClosed = app.waitForEvent('close', { timeout: 20000 });
        await app.evaluate(({ BrowserWindow }) => {
            const main = BrowserWindow.getAllWindows().find(win => {
                const url = win.webContents.getURL();
                return url && !url.includes('surface=');
            });
            if (!main) throw new Error('main Studio BrowserWindow not found');
            main.close();
        });
        await applicationClosed;
        assert.equal(appClosed, true, 'coordinated shutdown must terminate the Electron application');
        mark(t, 'main close coordinated secondary shutdown and Electron exited');
    } catch (error) {
        if (diagnostics.length) {
            error.message += '\nRenderer diagnostics:\n' + diagnostics.join('\n');
        }
        throw error;
    } finally {
        if (app && !appClosed) await forceStopElectron(app, electronProcess);
        fs.rmSync(tempRoot, { recursive: true, force: true });
    }
});
