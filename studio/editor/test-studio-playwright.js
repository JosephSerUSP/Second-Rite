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
const STUDIO_ROOT = path.resolve(__dirname, '..');
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
    const page = awaitSurfaceReady(await nextWindow, surfaceId);

    // /data boot can finish before the Electron-only surface adapter has mounted
    // and installed its native close handler, especially on a second open when
    // caches are warm. BrowserWindow.show() happens only after the renderer calls
    // thestra-studio-surface-ready, which is downstream of that installation.
    // Wait for that actual native handshake instead of racing on HTTP readiness.
    await waitFor(`${surfaceId} BrowserWindow native surface-ready handshake`,
        () => app.evaluate(({ BrowserWindow }, expected) => {
            const marker = `surface=${expected}`;
            const win = BrowserWindow.getAllWindows().find(candidate =>
                candidate.webContents.getURL().includes(marker));
            return !!win && win.isVisible();
        }, surfaceId),
        visible => visible === true,
        SURFACE_BOOT_TIMEOUT);
    return page;
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
    const mapPath = path.join(projectRoot, 'data', 'maps', '1.json');
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

        const authoredMap = readJson(mapPath);
        authoredMap.traversal = {
            provider: 'bounded_lane',
            lane: {
                minY: 0,
                maxY: 10,
                depthX: 0,
                groundZ: 0,
                speed: 3.4,
                groundProfile: [
                    { y: 0, z: 0 },
                    { y: 5, z: 1 },
                    { y: 10, z: 0 },
                ],
            },
        };
        writeJson(mapPath, authoredMap);

        const [editorPort, bridgePort] = await Promise.all([freePort(), freePort()]);
        app = await electron.launch({
            executablePath: electronExecutable,
            args: [STUDIO_ROOT, '--project', projectRoot],
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

        await mainPage.waitForFunction(() =>
            !!window.ThestraRuntimeCameraViewport?.getWalkProfileStatus?.()?.available,
        null, { timeout: SURFACE_BOOT_TIMEOUT });
        const mapCanvas = mainPage.locator('#thestra-map-viewport canvas').first();
        await mapCanvas.focus();

        await mapCanvas.press('Tab');
        await mainPage.waitForFunction(() =>
            window.ThestraRuntimeCameraViewport?.getWalkProfileEditing?.() === true);
        assert.equal(await mainPage.evaluate(() =>
            window.ThestraRuntimeCameraViewport.getWalkProfileComponentMode()), 'point');
        mark(t, 'Tab entered Walk Profile Edit Mode through the real Map canvas');
        assert.equal(await mainPage.evaluate(() =>
            window.ThestraRuntimeCameraViewport.getWalkMeshVisible()), true,
        'derived Walk Mesh topology must remain visible while editing the authored profile');
        await mainPage.waitForFunction(() => {
            const hud = document.querySelector('[data-walk-profile-hud="true"]');
            return !!hud && hud.getClientRects().length > 0
                && /GROUND PROFILE EDIT[\s\S]*selection/i.test(hud.textContent || '');
        });
        mark(t, 'viewport HUD explained the unified Ground Profile selection state');

        await mainPage.evaluate(() => {
            window.ThestraRuntimeCameraViewport.setSelection({
                kind: 'walk-profile-point',
                key: 'walk-profile-point:1',
                index: 1,
            });
        });
        await mainPage.waitForFunction(() => {
            const input = document.querySelector('input[title="Active Walk Profile point · Lane Y"]');
            return !!input && input.getClientRects().length > 0 && input.value === '5';
        });
        assert.equal(await mainPage.evaluate(() => {
            const input = document.querySelector('input[title="Active Walk Profile point · Elevation Z"]');
            return input?.value;
        }), '1', 'active-point inspector must expose authored elevation Z');
        mark(t, 'active Walk Profile point exposed precise semantic Y/Z fields');

        const toolbarLayout = await mainPage.evaluate(() => {
            const panel = document.querySelector('#thestra-map-view-toolbar');
            const profile = document.querySelector('.thestra-toolbar-profile');
            const help = document.querySelector('.thestra-toolbar-help');
            if (!panel || !profile || !help) return { ok: false, reason: 'missing toolbar regions' };
            const rect = node => node.getBoundingClientRect();
            const overlaps = (a, b) => a.left < b.right && a.right > b.left
                && a.top < b.bottom && a.bottom > b.top;
            const helpRect = rect(help);
            const visibleControls = Array.from(profile.querySelectorAll('button, input'))
                .filter(node => node.getClientRects().length > 0)
                .map(node => ({ label: node.textContent || node.title, rect: rect(node) }));
            return {
                ok: panel.getClientRects().length > 0 && profile.getClientRects().length > 0
                    && help.getClientRects().length > 0,
                helpOverlapsControl: visibleControls.some(item => overlaps(helpRect, item.rect)),
                helpFitsPanel: helpRect.left >= rect(panel).left && helpRect.right <= rect(panel).right,
                helpText: help.textContent
            };
        });
        assert.equal(toolbarLayout.ok, true, 'Walk Profile inspector must be visible');
        assert.equal(toolbarLayout.helpOverlapsControl, false,
            'Walk Profile help must occupy its own non-overlapping region');
        assert.equal(toolbarLayout.helpFitsPanel, true,
            'Walk Profile help must remain inside the contextual panel');
        mark(t, 'Walk Profile controls and help occupy separate readable panel regions');

        const navigationBox = await mapCanvas.boundingBox();
        assert.ok(navigationBox, 'Map canvas must have a real pointer target');
        const beforeNavigation = await mainPage.evaluate(() =>
            JSON.stringify(window.ThestraRuntimeCameraViewport.captureCameraState()));
        const selectedBeforeNavigation = await mainPage.evaluate(() =>
            window.ThestraRuntimeCameraViewport.getWalkProfileSelection()?.key);
        await mainPage.mouse.move(
            navigationBox.x + navigationBox.width * 0.72,
            navigationBox.y + navigationBox.height * 0.30);
        await mainPage.mouse.down({ button: 'middle' });
        await mainPage.mouse.move(
            navigationBox.x + navigationBox.width * 0.80,
            navigationBox.y + navigationBox.height * 0.38,
            { steps: 4 });
        await mainPage.mouse.up({ button: 'middle' });
        await mainPage.waitForTimeout(1000);
        const afterNavigation = await mainPage.evaluate(() =>
            JSON.stringify(window.ThestraRuntimeCameraViewport.captureCameraState()));
        assert.notEqual(afterNavigation, beforeNavigation,
            'MMB must navigate the 3D camera while profile editing is active');
        assert.equal(await mainPage.evaluate(() =>
            window.ThestraRuntimeCameraViewport.getWalkProfileSelection()?.key),
        selectedBeforeNavigation,
        'camera navigation must not compete with Walk Profile selection');
        mark(t, 'MMB camera navigation remained responsive without stealing profile selection');

        await mainPage.evaluate(() => {
            window.__walkProfileRejection = null;
            window.addEventListener('thestra-spatial-operation-rejected', event => {
                window.__walkProfileRejection = event.detail || null;
            }, { once: true });
            const input = document.querySelector('input[title="Active Walk Profile point · Lane Y"]');
            input.value = '11';
            input.dispatchEvent(new Event('change', { bubbles: true }));
        });
        await mainPage.waitForFunction(() =>
            window.__walkProfileRejection?.reason === 'profile-order');
        assert.deepEqual(await mainPage.evaluate(() =>
            dbPayload.maps[currentMapIndex].traversal.lane.groundProfile.map(point => point.y)),
        [0, 5, 10], 'rejected numeric crossing must preserve authored profile ordering');
        mark(t, 'invalid profile crossing stayed cancel-safe and surfaced a local reason');

        await mainPage.evaluate(() => {
            window.ThestraRuntimeCameraViewport.setSelection({
                kind: 'walk-profile-segment',
                key: 'walk-profile-segment:0',
                index: 0,
            });
        });
        await mainPage.waitForFunction(() => {
            const button = Array.from(document.querySelectorAll('button'))
                .find(candidate => candidate.textContent.trim() === 'Insert point');
            return !!button && !button.disabled && button.getClientRects().length > 0;
        });
        mark(t, 'segment selection immediately enabled Insert point in the unified toolbar');

        await mapCanvas.press('1');
        await mainPage.evaluate(() => {
            window.ThestraRuntimeCameraViewport.setSelection({
                kind: 'walk-profile-point',
                key: 'walk-profile-point:1',
                index: 1,
            });
        });
        await mapCanvas.press('a');
        assert.equal(await mainPage.evaluate(() =>
            window.ThestraRuntimeCameraViewport.getSpatialInteractionState().selectionSet.length), 3,
        'A must select all Walk Profile points in point mode');

        const beforeMove = await mainPage.evaluate(() =>
            JSON.stringify(dbPayload.maps[currentMapIndex].traversal.lane.groundProfile));
        await mapCanvas.press('g');
        await mapCanvas.press('z');
        await mainPage.waitForFunction(() => {
            const state = window.ThestraRuntimeCameraViewport.getSpatialInteractionState();
            return state.operation === 'move' && state.constraint === 'Z';
        });
        await mapCanvas.press('Escape');
        assert.equal(await mainPage.evaluate(() =>
            JSON.stringify(dbPayload.maps[currentMapIndex].traversal.lane.groundProfile)), beforeMove,
        'Esc-canceled modal G must not mutate authored profile data');
        assert.equal(await mainPage.evaluate(() =>
            window.ThestraRuntimeCameraViewport.getSpatialInteractionState().operation), null);
        mark(t, 'G Z entered semantic modal move and Esc canceled without authored mutation');

        await mainPage.evaluate(() => {
            window.ThestraRuntimeCameraViewport.setSelection({
                kind: 'walk-profile-point',
                key: 'walk-profile-point:0',
                index: 0,
            });
        });
        const beforeExtrude = await mainPage.evaluate(() =>
            JSON.stringify(dbPayload.maps[currentMapIndex].traversal.lane.groundProfile));
        await mapCanvas.press('e');
        await mainPage.waitForFunction(() =>
            window.ThestraRuntimeCameraViewport.getSpatialInteractionState().operation === 'move');
        await mapCanvas.press('Escape');
        assert.equal(await mainPage.evaluate(() =>
            JSON.stringify(dbPayload.maps[currentMapIndex].traversal.lane.groundProfile)), beforeExtrude,
        'Esc-canceled E extrusion must leave Map profile byte-for-byte unchanged');
        mark(t, 'E created only temporary endpoint topology until confirmation');

        await mainPage.evaluate(() => {
            window.ThestraRuntimeCameraViewport.setSelection({
                kind: 'walk-profile-segment',
                key: 'walk-profile-segment:0',
                index: 0,
            });
        });
        const beforeInsertCount = await mainPage.evaluate(() =>
            dbPayload.maps[currentMapIndex].traversal.lane.groundProfile.length);
        await mainPage.locator('button', { hasText: /^Insert point$/ }).click();
        await mainPage.waitForFunction(count =>
            dbPayload.maps[currentMapIndex].traversal.lane.groundProfile.length === count + 1,
        beforeInsertCount);
        mark(t, 'live Insert point action added authored profile topology');

        await mapCanvas.focus();
        await mapCanvas.press('1');
        await mainPage.evaluate(() => {
            window.ThestraRuntimeCameraViewport.setSelection({
                kind: 'walk-profile-point',
                key: 'walk-profile-point:1',
                index: 1,
            });
        });
        const beforeDissolveCount = await mainPage.evaluate(() =>
            dbPayload.maps[currentMapIndex].traversal.lane.groundProfile.length);
        await mapCanvas.press('Delete');
        await mainPage.waitForFunction(count =>
            dbPayload.maps[currentMapIndex].traversal.lane.groundProfile.length === count - 1,
        beforeDissolveCount);
        mark(t, 'live Delete shortcut dissolved valid interior profile topology');

        await mapCanvas.press('Tab');
        await mainPage.waitForFunction(() =>
            window.ThestraRuntimeCameraViewport?.getWalkProfileEditing?.() === false);
        assert.equal(await mainPage.evaluate(() =>
            window.ThestraRuntimeCameraViewport.getSpatialInteractionState().selection), null,
        'leaving Edit Mode must clear the shared profile selection');
        mark(t, 'Tab exited Walk Profile Edit Mode and cleared shared selection');

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
