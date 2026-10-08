'use strict';

const fs = require('node:fs');
const net = require('node:net');
const path = require('node:path');
const { _electron: electron } = require('playwright');
const electronExecutable = require('electron');

const REPO_ROOT = path.resolve(__dirname, '..', '..');
const STUDIO_ROOT = path.resolve(__dirname, '..');
const PROJECT_ROOT = path.join(REPO_ROOT, 'projects', 'experiments', 'continuous-surface-gauntlet');
const OUTPUT_ROOT = path.resolve(process.env.CONTINUOUS_SURFACE_VISUAL_OUT
    || path.join(REPO_ROOT, 'out', 'continuous-surface-studio'));
const TIMEOUT = 45000;

function freePort() {
    return new Promise((resolve, reject) => {
        const server = net.createServer();
        server.unref();
        server.once('error', reject);
        server.listen(0, '127.0.0.1', () => {
            const address = server.address();
            server.close(error => error ? reject(error) : resolve(address.port));
        });
    });
}

async function waitFor(description, probe, predicate = value => !!value, timeout = TIMEOUT) {
    const deadline = Date.now() + timeout;
    let last;
    while (Date.now() < deadline) {
        try {
            last = await probe();
            if (predicate(last)) return last;
        } catch (_) {}
        await new Promise(resolve => setTimeout(resolve, 75));
    }
    throw new Error(`Timed out waiting for ${description}; last=${JSON.stringify(last)}`);
}

async function capture(page, name) {
    const output = path.join(OUTPUT_ROOT, name);
    await page.screenshot({ path: output, animations: 'disabled' });
    console.log(`[continuous-surface-proof] ${output}`);
}

async function selectMap(page, index, packageFragment) {
    // The golden-editor harness uses this same live global boundary. The map
    // tree is workspace chrome and may be collapsed/absent depending on saved
    // layout; currentMapIndex + loadActiveMap are the actual editor selection
    // operation and therefore make the proof independent of incidental chrome.
    await page.evaluate(expectedIndex => {
        currentMapIndex = expectedIndex;
        loadActiveMap();
    }, index);
    await page.waitForFunction(({ expectedIndex, fragment }) => {
        const host = window.ThestraEditorHost;
        const viewport = window.ThestraRuntimeCameraViewport;
        if (!host || host.getMapIndex() !== expectedIndex || !viewport?.getWalkSurfaceInfo) return false;
        const info = viewport.getWalkSurfaceInfo();
        return info.available && String(info.manifestPath || '').includes(fragment);
    }, { expectedIndex: index, fragment: packageFragment }, { timeout: TIMEOUT });
    await page.evaluate(() => {
        const viewport = window.ThestraRuntimeCameraViewport;
        viewport.setCollisionVisible?.(false);
        viewport.setWalkSurfaceVisible?.(true);
        viewport.frameScene?.();
    });
    await page.waitForTimeout(400);
}

async function main() {
    fs.mkdirSync(OUTPUT_ROOT, { recursive: true });
    const [editorPort, bridgePort] = await Promise.all([freePort(), freePort()]);
    const diagnostics = [];
    let app;
    try {
        app = await electron.launch({
            executablePath: electronExecutable,
            args: [STUDIO_ROOT, '--project', PROJECT_ROOT],
            cwd: REPO_ROOT,
            env: {
                ...process.env,
                PORT: String(editorPort),
                EDITOR_PORT: String(editorPort),
                RUNTIME_BRIDGE_PORT: String(bridgePort),
                ELECTRON_DISABLE_GPU: '1',
            },
            timeout: TIMEOUT,
        });
        const page = await waitFor('main Studio renderer', () => app.windows().find(candidate =>
            /^http:\/\/127\.0\.0\.1:\d+\/(?:\?.*)?$/.test(candidate.url())) || null);
        page.on('pageerror', error => diagnostics.push(`pageerror: ${error.stack || error.message}`));
        page.on('console', message => {
            if (message.type() === 'error') diagnostics.push(`console: ${message.text()}`);
        });
        await page.waitForFunction(() => {
            const boot = window.thestraDatabaseBootState;
            return !!window.thestraStudio && !!boot && boot.done === true;
        }, null, { timeout: TIMEOUT });
        await app.evaluate(({ BrowserWindow }) => {
            const win = BrowserWindow.getAllWindows().find(candidate =>
                !candidate.webContents.getURL().includes('surface='));
            if (win) win.setSize(1440, 900);
        });
        await page.waitForTimeout(250);
        await page.waitForFunction(() => !!window.ThestraRuntimeCameraViewport?.getWalkSurfaceInfo,
            null, { timeout: TIMEOUT });

        await selectMap(page, 0, 'archive_antechamber');
        await page.evaluate(() => {
            const viewport = window.ThestraRuntimeCameraViewport;
            viewport.setMode?.('perspective');
            viewport.frameScene?.();
        });
        await page.waitForTimeout(300);
        await capture(page, '01-archive-perspective-walk-surface.png');

        await page.evaluate(() => {
            const viewport = window.ThestraRuntimeCameraViewport;
            viewport.setMode?.('top');
            viewport.setAxisView?.('top');
            viewport.frameScene?.();
        });
        await page.waitForTimeout(300);
        await capture(page, '02-archive-top-walk-surface.png');

        await selectMap(page, 1, 'service_annex');
        await page.evaluate(() => {
            const viewport = window.ThestraRuntimeCameraViewport;
            viewport.setMode?.('top');
            viewport.setAxisView?.('top');
            viewport.frameScene?.();
        });
        await page.waitForTimeout(300);
        await capture(page, '03-service-annex-top-walk-surface.png');

        await page.evaluate(() => {
            const viewport = window.ThestraRuntimeCameraViewport;
            viewport.setMode?.('perspective');
            viewport.setAxisView?.('front');
            viewport.setCollisionVisible?.(true);
            viewport.setWalkSurfaceVisible?.(true);
            viewport.frameScene?.();
        });
        await page.waitForTimeout(300);
        await capture(page, '04-service-annex-walk-vs-collision.png');

        const summary = await page.evaluate(() => {
            const host = window.ThestraEditorHost;
            const viewport = window.ThestraRuntimeCameraViewport;
            return {
                mapIndex: host?.getMapIndex?.(),
                walkSurface: viewport?.getWalkSurfaceInfo?.(),
                collisionVisible: viewport?.getCollisionVisible?.(),
            };
        });
        fs.writeFileSync(path.join(OUTPUT_ROOT, 'proof.json'), JSON.stringify({ summary, diagnostics }, null, 2) + '\n');
        if (diagnostics.some(line => /Walk-surface|renderable|pageerror/i.test(line))) {
            throw new Error(`Studio emitted visual-proof diagnostics:\n${diagnostics.join('\n')}`);
        }
    } finally {
        if (app) {
            try { await app.evaluate(({ app: electronApp }) => electronApp.exit(0)); } catch (_) {}
            try { await app.close(); } catch (_) {}
        }
    }
}

main().catch(error => {
    console.error(error.stack || error.message || String(error));
    process.exitCode = 1;
});