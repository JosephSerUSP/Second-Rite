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

function expectedLegacyCanvasDiagnostic(line) {
    return line.includes("InvalidStateError: Failed to execute 'drawImage'")
        && line.includes('map-editor.js');
}

function relevantDiagnostic(line) {
    if (expectedLegacyCanvasDiagnostic(line)) return false;
    if (line.includes('ERR_CONNECTION_REFUSED')
            && !/walk[- ]surface|renderable/i.test(line)) return false;
    if (/walk[- ]surface|renderable/i.test(line)) return true;
    return line.startsWith('pageerror:');
}

async function authoritySnapshot(page) {
    return page.evaluate(() => {
        const host = window.ThestraEditorHost;
        const viewport = window.ThestraRuntimeCameraViewport;
        const failure = document.getElementById('thestra-map-runtime-failure');
        return {
            mapIndex: host?.getMapIndex?.(),
            status: document.getElementById('thestra-map-view-status')?.textContent || '',
            failureVisible: !!failure && getComputedStyle(failure).display !== 'none',
            failureText: failure?.textContent || '',
            walkSurface: viewport?.getWalkSurfaceInfo?.() || null,
            inspector: document.getElementById('thestra-map-inspector-body')?.textContent || '',
            renderableUrl: globalThis.THESTRA_RENDERABLE_URL || null,
        };
    });
}

async function selectMap(page, index, packageFragment, expectedTitle) {
    // This original-content gauntlet intentionally has no legacy tileset art.
    // The retired hidden 2D canvas still attempts to draw that absent image
    // during map selection; suppress only its InvalidStateError in this proof
    // harness. The live Three/runtime path remains untouched and is gated below.
    await page.evaluate(expectedIndex => {
        const proto = CanvasRenderingContext2D.prototype;
        const nativeDrawImage = proto.drawImage;
        proto.drawImage = function (...args) {
            try {
                return nativeDrawImage.apply(this, args);
            } catch (error) {
                if (error && error.name === 'InvalidStateError') return undefined;
                throw error;
            }
        };
        try {
            currentMapIndex = expectedIndex;
            loadActiveMap();
            window.ThestraEditorHost?.selectSemantic?.(null);
        } finally {
            proto.drawImage = nativeDrawImage;
        }
    }, index);

    try {
        await page.waitForFunction(({ expectedIndex, fragment }) => {
            const host = window.ThestraEditorHost;
            const viewport = window.ThestraRuntimeCameraViewport;
            const status = document.getElementById('thestra-map-view-status')?.textContent || '';
            const failure = document.getElementById('thestra-map-runtime-failure');
            const failed = failure && getComputedStyle(failure).display !== 'none';
            const info = viewport?.getWalkSurfaceInfo?.();
            return !!host && host.getMapIndex() === expectedIndex
                && !!info?.available
                && String(info.manifestPath || '').includes(fragment)
                && !failed
                && /runtime geometry/i.test(status);
        }, { expectedIndex: index, fragment: packageFragment }, { timeout: TIMEOUT });
    } catch (error) {
        const snapshot = await authoritySnapshot(page);
        throw new Error(`runtime authority did not settle for ${expectedTitle}: ${JSON.stringify(snapshot)}`);
    }

    // Force the Inspector through its public selection boundary after the map
    // has settled. It is visual context, not an engine gate.
    await page.evaluate(() => {
        window.ThestraEditorHost?.selectSemantic?.(null);
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

        // Exactly the same isolation contract as G6: the CI host owns a random
        // bridge port and publishes it to the browser adapter before requesting
        // an authoritative bundle.
        await page.evaluate(url => { globalThis.THESTRA_RENDERABLE_URL = url; },
            `http://127.0.0.1:${bridgePort}/api/map-renderable`);

        await app.evaluate(({ BrowserWindow }) => {
            const win = BrowserWindow.getAllWindows().find(candidate =>
                !candidate.webContents.getURL().includes('surface='));
            if (win) win.setSize(1440, 900);
        });
        await page.waitForTimeout(250);
        await page.waitForFunction(() => !!window.ThestraRuntimeCameraViewport?.getWalkSurfaceInfo,
            null, { timeout: TIMEOUT });

        await selectMap(page, 0, 'archive_antechamber', 'Archive Antechamber');
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

        await selectMap(page, 1, 'service_annex', 'Service Annex');
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

        const summary = await authoritySnapshot(page);
        summary.collisionVisible = await page.evaluate(() =>
            window.ThestraRuntimeCameraViewport?.getCollisionVisible?.());
        const fatalDiagnostics = diagnostics.filter(relevantDiagnostic);
        fs.writeFileSync(path.join(OUTPUT_ROOT, 'proof.json'), JSON.stringify({
            summary,
            diagnostics,
            fatalDiagnostics,
        }, null, 2) + '\n');
        if (fatalDiagnostics.length) {
            throw new Error(`Studio emitted relevant visual-proof diagnostics:\n${fatalDiagnostics.join('\n')}`);
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