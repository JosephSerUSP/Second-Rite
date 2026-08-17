'use strict';

// Branch-only evidence harness for issue #547's live-specimen experiment.
// It drives the real Electron Tileset surface, the real localhost runtime
// bridge, and LÖVE. The checkout is disposable in CI: Save is intentionally
// exercised, but no generated data or capture is committed back to the branch.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const childProcess = require('node:child_process');
const { _electron: electron } = require('playwright');
const electronExecutable = require('electron');

const REPO_ROOT = path.resolve(__dirname, '..', '..');
const OUT_DIR = path.join(REPO_ROOT, 'artifacts', 'tileset-live-specimen');
const TIMEOUT = 60000;

function delay(ms) { return new Promise(resolve => setTimeout(resolve, ms)); }
function surfaceId(page) {
    try { return new URL(page.url()).searchParams.get('surface') || 'main'; }
    catch (_) { return null; }
}
async function waitFor(description, probe, predicate = value => !!value, timeoutMs = TIMEOUT) {
    const deadline = Date.now() + timeoutMs;
    let last;
    let lastError;
    while (Date.now() < deadline) {
        try {
            last = await probe();
            lastError = null;
            if (predicate(last)) return last;
        } catch (error) { lastError = error; }
        await delay(80);
    }
    throw new Error(`Timed out waiting for ${description}; last=${JSON.stringify(last)}${lastError ? `; error=${lastError.message}` : ''}`);
}
async function awaitSurfaceReady(page, expected) {
    await page.waitForFunction(surface => {
        const actual = new URLSearchParams(location.search).get('surface') || 'main';
        const boot = window.thestraDatabaseBootState;
        return actual === surface && !!window.thestraStudio && !!boot && boot.done === true;
    }, expected, { timeout: TIMEOUT });
    return page;
}
function attachDiagnostics(page, label, diagnostics) {
    page.on('pageerror', error => diagnostics.push(`${label} pageerror: ${error.stack || error.message}`));
    page.on('console', message => {
        if (message.type() === 'error') diagnostics.push(`${label} console: ${message.text()}`);
    });
    page.on('dialog', dialog => {
        diagnostics.push(`${label} dialog(${dialog.type()}): ${dialog.message()}`);
        dialog.dismiss().catch(() => {});
    });
}
async function openSurface(app, mainPage, id, diagnostics) {
    const next = app.waitForEvent('window', { timeout: TIMEOUT });
    await mainPage.evaluate(surface => window.thestraStudio.openSurface(surface), id);
    const page = await next;
    // Attach before boot/host mounting so a failed dynamic import or layout
    // exception cannot disappear before the evidence harness starts listening.
    attachDiagnostics(page, id, diagnostics);
    await awaitSurfaceReady(page, id);
    await waitFor(`${id} native ready`, () => app.evaluate(({ BrowserWindow }, expected) => {
        const win = BrowserWindow.getAllWindows().find(candidate => candidate.webContents.getURL().includes(`surface=${expected}`));
        return !!win && win.isVisible();
    }, id), value => value === true);
    return page;
}
async function surfaceState(page) {
    return page.evaluate(() => {
        function rect(selector) {
            const node = document.querySelector(selector);
            if (!node) return null;
            const r = node.getBoundingClientRect();
            const style = getComputedStyle(node);
            return {
                width: r.width, height: r.height, left: r.left, top: r.top,
                display: style.display, visibility: style.visibility, opacity: style.opacity,
                overflow: style.overflow,
            };
        }
        const status = document.getElementById('tsls-status');
        return {
            url: location.href,
            bodyClass: document.body.className,
            hasLiveApi: !!window.thestraTilesetLiveSpecimen,
            hasTransactionApi: !!window.thestraTilesetStudioTransaction,
            modal: rect('#tileset-studio-modal'),
            window: rect('#tileset-studio-modal > .db-modal-window'),
            body: rect('.tsls-body'),
            center: rect('.tsls-center'),
            viewport: rect('#tsls-viewport'),
            canvas: rect('#tsls-viewport canvas'),
            viewportChildren: document.getElementById('tsls-viewport')?.childElementCount || 0,
            status: status?.textContent || null,
            title: document.querySelector('#tileset-studio-modal .title-bar-text')?.textContent || null,
            modalHtmlPrefix: document.getElementById('tileset-studio-modal')?.innerHTML.slice(0, 1200) || null,
        };
    });
}
async function writeFailureEvidence(page, notes, error) {
    notes.failure = { message: error.message, stack: error.stack };
    if (page && !page.isClosed()) {
        try { notes.failure.surfaceState = await surfaceState(page); } catch (stateError) { notes.failure.stateError = stateError.message; }
        try { await page.screenshot({ path: path.join(OUT_DIR, '00-failure-state.png') }); } catch (shotError) { notes.failure.screenshotError = shotError.message; }
    }
    fs.writeFileSync(path.join(OUT_DIR, 'failure-state.json'), JSON.stringify(notes, null, 2) + '\n', 'utf8');
}
async function setControl(page, selector, value) {
    await page.locator(selector).evaluate((control, next) => {
        if (control.type === 'checkbox') control.checked = !!next;
        else control.value = String(next);
        control.dispatchEvent(new Event('change', { bubbles: true }));
    }, value);
}
async function clickRole(page, role) {
    await page.locator(`[data-role="${role}"]`).click();
    await page.waitForFunction(expected => document.getElementById('tsls-owner')?.textContent === expected,
        ({ wall: 'Wall', floor: 'Floor', ceiling: 'Ceiling', door: 'Opening / Door', wall_feature: 'Wall Feature', floor_feature: 'Floor Feature', wall_top: 'Wall Top' })[role],
        { timeout: 5000 });
}
async function waitForRuntime(page, expectedSeed) {
    return waitFor(`runtime bundle seed ${expectedSeed}`, () => page.evaluate(() => {
        const api = window.thestraTilesetLiveSpecimen;
        return api && api.bundle ? api.bundle() : null;
    }), bundle => !!bundle && !!bundle.request && bundle.request.transientTileset === true
        && Number(bundle.request.seed) === Number(expectedSeed) && (bundle.stats?.triangleCount || 0) > 0);
}
function wallSignature(bundle) {
    const walls = (bundle.surfaces || []).filter(surface => {
        const role = surface?.source?.surface;
        return typeof role === 'string' && role.endsWith('wall') && role !== 'wall-top';
    });
    return JSON.stringify(walls.map(surface => [surface.source.surface, surface.source.x, surface.source.y, surface.uvs]));
}
async function forceExit(app) {
    if (!app) return;
    try { await Promise.race([app.evaluate(({ app: electronApp }) => electronApp.exit(0)), delay(1200)]); }
    catch (_) {}
    const proc = app.process();
    if (!proc || proc.exitCode !== null) return;
    if (process.platform === 'win32') {
        childProcess.spawnSync('taskkill.exe', ['/PID', String(proc.pid), '/T', '/F'], { stdio: 'ignore', windowsHide: true });
    } else {
        try { proc.kill('SIGKILL'); } catch (_) {}
    }
}

async function main() {
    fs.mkdirSync(OUT_DIR, { recursive: true });
    const diagnostics = [];
    const notes = { branch: 'exp/tileset-live-specimen', issue: 547, diagnostics };
    let app = null;
    let activePage = null;
    try {
        app = await electron.launch({
            executablePath: electronExecutable,
            args: [REPO_ROOT, '--project', REPO_ROOT],
            cwd: REPO_ROOT,
            env: {
                ...process.env,
                PORT: '8080',
                EDITOR_PORT: '8080',
                RUNTIME_BRIDGE_PORT: '8082',
            },
            timeout: TIMEOUT,
        });
        const mainPage = await app.firstWindow();
        attachDiagnostics(mainPage, 'main', diagnostics);
        await awaitSurfaceReady(mainPage, 'main');

        const page = activePage = await openSurface(app, mainPage, 'tileset', diagnostics);
        assert.equal(surfaceId(page), 'tileset');
        await page.waitForFunction(() => !!window.thestraTilesetLiveSpecimen && !!window.thestraTilesetStudioTransaction,
            null, { timeout: TIMEOUT });
        notes.openState = await surfaceState(page);
        fs.writeFileSync(path.join(OUT_DIR, '00-open-state.json'), JSON.stringify(notes.openState, null, 2) + '\n', 'utf8');
        await page.screenshot({ path: path.join(OUT_DIR, '00-surface-open.png') });
        const visibleCanvas = await waitFor('visible live specimen canvas', surfaceState,
            state => !!state.canvas && state.canvas.width > 100 && state.canvas.height > 100,
            12000).catch(async error => {
                // `waitFor` receives the page through a closure below; keeping
                // this branch explicit makes the failure JSON much more useful.
                throw error;
            });
        void visibleCanvas;

        const initialBundle = await waitForRuntime(page, 547001);
        assert.equal(initialBundle.request.tilesetId, 'dungeon_default');
        notes.initial = {
            tileset: initialBundle.request.tilesetId,
            triangleCount: initialBundle.stats?.triangleCount || 0,
            transientTileset: initialBundle.request.transientTileset,
            roleCounts: await page.evaluate(() => Object.fromEntries(
                Array.from(document.querySelectorAll('#tsls-roles [data-role]')).map(button => [
                    button.dataset.role,
                    Number(button.querySelector('.count')?.textContent || 0)
                ])
            )),
        };

        // Core ownership gauntlet: use the rendered object as the first input,
        // not the vocabulary list. Try representative rays until a runtime cell
        // provenance reaches the Inspector.
        const canvas = page.locator('#tsls-viewport canvas');
        const box = await canvas.boundingBox();
        assert.ok(box && box.width > 100 && box.height > 100, '3D specimen canvas must be visible');
        const attempts = [[.5,.72],[.5,.52],[.35,.66],[.65,.66],[.25,.5],[.75,.5],[.5,.3]];
        let clickedOwner = null;
        for (const [rx, ry] of attempts) {
            await canvas.click({ position: { x: box.width * rx, y: box.height * ry } });
            await delay(180);
            clickedOwner = await page.locator('#tsls-owner-detail').textContent();
            if (/Runtime cell/.test(clickedOwner || '')) break;
        }
        assert.match(clickedOwner || '', /Runtime cell/, 'clicking the visible specimen should select semantic runtime ownership');
        notes.visibleSelection = {
            owner: await page.locator('#tsls-owner').textContent(),
            detail: clickedOwner,
        };
        await page.screenshot({ path: path.join(OUT_DIR, '01-live-specimen-selection.png') });

        // Replace the base wall through the contextual source browser. The stock
        // dungeon atlas is 2x2 64px cells: row 0 becomes the replacement, while
        // row 1 remains available to make the second weighted variant distinct.
        await clickRole(page, 'wall');
        await waitFor('atlas source browser', () => page.locator('#tsls-atlas').evaluate(node => ({ width: node.width, height: node.height })), size => size.width > 40 && size.height > 40);
        await page.locator('#tsls-atlas').click({ position: { x: 23, y: 23 } });
        await waitForRuntime(page, 547001);
        const replacedWall = await page.evaluate(() => window.thestraTilesetLiveSpecimen.workingCopy().base.walls[0]);
        assert.deepEqual(replacedWall.middle, [0, 0]);

        // Add a weighted alternative and bind it to the stock wall row.
        await page.locator('#tsls-add').click();
        await page.locator('#tsls-atlas').click({ position: { x: 23, y: 69 } });
        await setControl(page, '[data-field="weight"]', 35);
        await waitForRuntime(page, 547001);
        const weighted = await page.evaluate(() => window.thestraTilesetLiveSpecimen.workingCopy().base.walls.map(item => ({ id: item.id, middle: item.middle, weight: item.weight })));
        assert.equal(weighted.length, 2);
        assert.equal(weighted[1].weight, 35);
        notes.wall = { replacedBase: replacedWall.middle, variants: weighted };
        await page.screenshot({ path: path.join(OUT_DIR, '02-weighted-wall-source-browser.png') });

        // Same seed must be stable, while cycling seeds after the weighted pool
        // exists should eventually produce at least two wall UV resolutions.
        await page.evaluate(() => window.thestraTilesetLiveSpecimen.setSeed(547001));
        const seedA1 = await waitForRuntime(page, 547001);
        await page.evaluate(() => window.thestraTilesetLiveSpecimen.setSeed(547001));
        const seedA2 = await waitForRuntime(page, 547001);
        assert.equal(wallSignature(seedA1), wallSignature(seedA2));
        const signatures = new Set([wallSignature(seedA1)]);
        let variantSeed = 547001;
        for (let candidate = 547002; candidate <= 547020 && signatures.size < 2; candidate++) {
            await page.evaluate(next => window.thestraTilesetLiveSpecimen.setSeed(next), candidate);
            const bundle = await waitForRuntime(page, candidate);
            signatures.add(wallSignature(bundle));
            variantSeed = candidate;
        }
        assert.ok(signatures.size >= 2, 'weighted wall pool should visibly resolve differently across deterministic seeds');
        notes.determinism = { sameSeedStable: true, distinctWallResolutions: signatures.size, scannedThroughSeed: variantSeed };

        // Floor + relief and ceiling vocabulary are edited through the same
        // working copy and immediately re-resolved through LÖVE.
        await clickRole(page, 'floor');
        await setControl(page, '[data-field="heightOffset"]', 0.12);
        await waitForRuntime(page, variantSeed);
        assert.equal(await page.evaluate(() => window.thestraTilesetLiveSpecimen.workingCopy().base.floors[0].heightOffset), 0.12);
        await clickRole(page, 'ceiling');
        assert.ok((await page.locator('#tsls-variants .tsls-variant').count()) >= 1, 'ceiling should be directly inspectable');
        await clickRole(page, 'door');
        assert.ok((await page.locator('#tsls-variants .tsls-variant').count()) >= 1, 'opening/door pool should be directly inspectable');

        // Fixture gauntlet: existing torch demonstrates a model-backed Surface.
        // Convert its convenience prefab to an advanced exact predicate, set
        // probability, and tune a warm emitted light while watching real runtime.
        await clickRole(page, 'wall_feature');
        assert.ok(await page.locator('[data-field="model"]').inputValue(), 'wall fixture should expose its model-backed source');
        await setControl(page, '[data-field="injectProbability"]', 41);
        await setControl(page, '[data-field="prefab"]', '');
        await setControl(page, '[data-field="whereJson"]', JSON.stringify({ all: [
            { adjacent: 'floor' },
            { not: { adjacent: 'opening' } }
        ] }));
        if (!(await page.locator('[data-field="emitsLight"]').isChecked())) await setControl(page, '[data-field="emitsLight"]', true);
        await setControl(page, '[data-field="lightColor"]', '#ff9a40');
        await setControl(page, '[data-field="lightRadius"]', 5.5);
        await setControl(page, '[data-field="lightFalloff"]', 3);
        await waitForRuntime(page, variantSeed);
        const fixture = await page.evaluate(() => window.thestraTilesetLiveSpecimen.workingCopy().features.find(item => item.role === 'wall_feature'));
        assert.equal(fixture.injectProbability, 0.41);
        assert.deepEqual(fixture.where, { all: [{ adjacent: 'floor' }, { not: { adjacent: 'opening' } }] });
        assert.ok(fixture.model);
        assert.ok(fixture.emitsLight && fixture.emitsLight.radius === 5.5);
        notes.feature = {
            id: fixture.id,
            model: fixture.model,
            probability: fixture.injectProbability,
            where: fixture.where,
            emitsLight: fixture.emitsLight,
        };
        await page.screenshot({ path: path.join(OUT_DIR, '03-warm-model-feature-exact-predicate.png') });

        // Save / discard / switch gauntlet. Save writes only this CI checkout.
        assert.equal(await page.evaluate(() => window.thestraTilesetStudioTransaction.isDirty()), true);
        assert.equal(await page.evaluate(() => window.thestraTilesetStudioTransaction.save()), true);
        assert.equal(await page.evaluate(() => window.thestraTilesetStudioTransaction.isDirty()), false);
        const savedName = await page.locator('#tsls-name').inputValue();
        await page.locator('#tsls-name').fill(savedName + ' discard-probe');
        await page.locator('#tsls-name').dispatchEvent('input');
        assert.equal(await page.evaluate(() => window.thestraTilesetStudioTransaction.isDirty()), true);
        assert.equal(await page.evaluate(() => window.thestraTilesetStudioTransaction.discard()), true);
        assert.equal(await page.locator('#tsls-name').inputValue(), savedName);
        assert.equal(await page.evaluate(() => window.thestraTilesetStudioTransaction.isDirty()), false);

        const alternate = await page.locator('#tsls-tileset option').evaluateAll(options => options.map(option => option.value).find(value => value !== 'dungeon_default'));
        assert.ok(alternate, 'gauntlet needs a second Tileset to exercise switching');
        await setControl(page, '#tsls-tileset', alternate);
        await waitFor('Tileset switch', () => page.evaluate(() => window.thestraTilesetStudioTransaction.currentId()), value => value === alternate);
        const switchedBundle = await waitFor(`runtime bundle for ${alternate}`, () => page.evaluate(() => window.thestraTilesetLiveSpecimen.bundle()), bundle =>
            bundle?.request?.transientTileset === true && bundle.request.tilesetId === alternate && (bundle.stats?.triangleCount || 0) > 0);
        notes.transaction = { saved: true, discardedUnsavedProbe: true, switchedTo: alternate, switchedTriangles: switchedBundle.stats?.triangleCount || 0 };
        await page.screenshot({ path: path.join(OUT_DIR, '04-switched-tileset.png') });

        notes.qualitative = {
            jsonExposure: 'Normal wall/floor/ceiling/door/weight/light/placement work stays in semantic controls. Advanced exact predicate intentionally exposes a compact JSON predicate as the expert escape hatch.',
            feedback: 'Every source/property mutation requests an unsaved transient Tileset + fixed specimen Map from the existing LÖVE authority bridge; the viewport displays the returned runtime bundle.',
            ownership: 'A click on rendered specimen geometry resolves to runtime cell/semantic provenance before the Inspector chooses the corresponding Tileset role.',
            inference: 'The fixed room exposes floor, ceiling, straight walls, interior corners, an opening, wall/floor feature opportunities, relief, weighted variants and emitted-light feedback in one view.',
            exactness: 'Weights, probability, predicate JSON, model path, height offset, light color/radius/falloff remain directly editable without changing runtime schema.'
        };
        notes.diagnosticsClean = diagnostics.length === 0;
        fs.writeFileSync(path.join(OUT_DIR, 'gauntlet-evidence.json'), JSON.stringify(notes, null, 2) + '\n', 'utf8');
        if (diagnostics.length) throw new Error('Renderer diagnostics were not clean:\n' + diagnostics.join('\n'));
        console.log(JSON.stringify(notes, null, 2));
    } catch (error) {
        await writeFailureEvidence(activePage, notes, error);
        throw error;
    } finally {
        await forceExit(app);
    }
}

main().catch(error => {
    console.error(error && error.stack ? error.stack : error);
    process.exitCode = 1;
});
