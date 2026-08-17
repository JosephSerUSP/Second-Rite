'use strict';
// #547 experiment capture driver (DISPOSABLE, alongside the prototype).
//
// Drives the shared authoring gauntlet through the real Studio editor server
// and the real LÖVE renderable bridge, writing frames plus a measured metrics
// report. It does NOT touch G5/G6 canon: frames land in an experiment folder of
// its own and nothing here compares against a committed golden.
//
// Every "click a wall/floor/door" step goes through the viewport's real picking
// path at the real screen position of that runtime surface. Nothing is faked by
// calling the panel's internals directly.
//
// Usage: node tools/editor/capture-tileset-map-context-experiment.js
// Needs the editor server on 8080 and the runtime bridge on 8082.

const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');

const OUT = path.resolve(__dirname, '..', '..', 'docs', 'experiments', 'issue-547-map-context-capture');
const BASE = process.env.EXP547_BASE || 'http://127.0.0.1:8080';
const CHROME = process.env.CHROME_PATH
    || 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const steps = [];

function log(name, detail) {
    steps.push({ name, detail: detail === undefined ? null : String(detail) });
    console.log(`[capture] ${name}${detail === undefined ? '' : ` — ${detail}`}`);
}

// showToast() in this editor is a MODAL overlay, so a pending toast blocks
// every later interaction. Clear it before driving anything.
async function dismissToast(page) {
    await page.evaluate(() => {
        const modal = document.getElementById('toast-modal');
        if (!modal || !modal.classList.contains('active')) return;
        const text = document.getElementById('toast-text');
        window.__toasts = window.__toasts || [];
        window.__toasts.push(text ? text.textContent : '');
        if (typeof closeToast === 'function') closeToast();
        else modal.classList.remove('active');
    });
}

async function shot(page, name) {
    await dismissToast(page);
    fs.mkdirSync(OUT, { recursive: true });
    await page.screenshot({ path: path.join(OUT, `${name}.png`) });
    log(`frame ${name}`);
}

async function panelText(page) {
    return page.evaluate(() => {
        const panel = document.getElementById('exp547-map-context');
        return panel ? panel.innerText.replace(/\n{2,}/g, '\n') : '(no panel)';
    });
}

function flat(text, limit) {
    return String(text || '').replace(/\s+/g, ' ').slice(0, limit || 500);
}

async function panelFacts(page) {
    return page.evaluate(() => {
        const panel = document.getElementById('exp547-map-context');
        if (!panel) return null;
        const text = panel.innerText;
        const read = label => {
            const match = new RegExp(`${label}\\s*\\n([^\\n]+)`).exec(text);
            return match ? match[1].trim() : null;
        };
        return {
            surface: read('Surface'),
            cell: read('Cell'),
            job: read('Owner job'),
            owner: read('Owner variant'),
        };
    });
}

async function installSignals(page) {
    await page.evaluate(() => {
        if (window.__bundles !== undefined) return;
        window.__bundles = 0;
        window.addEventListener('thestra-map-bundle-installed', () => { window.__bundles += 1; });
    });
}

async function bundleCount(page) { return page.evaluate(() => window.__bundles || 0); }

async function waitForNewBundle(page, previous, timeout = 240000) {
    await page.waitForFunction(count => (window.__bundles || 0) > count, previous, { timeout });
    await page.waitForTimeout(900);
}

async function selectMapByTitle(page, titlePattern) {
    const before = await bundleCount(page);
    await dismissToast(page);
    const chosen = await page.evaluate(pattern => {
        const items = Array.from(document.querySelectorAll('.map-tree-item'));
        const target = items.find(item => new RegExp(pattern).test(item.textContent || ''));
        if (!target) return null;
        target.click();
        return target.textContent.trim();
    }, titlePattern);
    if (!chosen) return null;
    await waitForNewBundle(page, before);
    return chosen;
}

// Click the real runtime surface. The viewport reports every candidate
// position nearest-first; another surface can sit in front of any of them, so
// each click is VERIFIED against what the panel then reports and the next
// candidate is tried on a mismatch. A miss is reported, never papered over.
async function clickRuntimeSurface(page, spec) {
    await dismissToast(page);
    await ensureNotPicking(page);
    const candidates = await page.evaluate(({ surfaces, needFeature }) => {
        const viewport = window.ThestraMapWorkspaceContext.viewport();
        if (!viewport || !viewport.screenPositionsForProvenance) return [];
        return viewport.screenPositionsForProvenance(source => {
            if (!source || source.kind !== 'cell') return false;
            if (needFeature && !source.featureId) return false;
            if (!needFeature && source.featureId) return false;
            return surfaces.includes(source.surface);
        });
    }, spec);
    if (candidates.length === 0) return { hit: null, reason: 'no matching surface is on screen', tried: 0 };

    const wantedJob = spec.expectJob ? new RegExp(spec.expectJob, 'i') : null;
    let last = null;
    const limit = Math.min(candidates.length, spec.maxTries || 24);
    for (let index = 0; index < limit; index++) {
        await dismissToast(page);
        await page.mouse.click(candidates[index].x, candidates[index].y);
        await page.waitForTimeout(260);
        const facts = await panelFacts(page);
        last = facts;
        if (!facts || !facts.job) continue;
        if (!wantedJob || wantedJob.test(facts.job)) {
            return { hit: facts, point: candidates[index], tried: index + 1, candidates: candidates.length };
        }
    }
    return {
        hit: null,
        reason: `clicked ${limit} of ${candidates.length} candidates; a nearer surface always won (last: ${JSON.stringify(last)})`,
        tried: limit,
    };
}

async function panelButton(page, label) {
    await dismissToast(page);
    const button = page.locator('#exp547-map-context button', { hasText: new RegExp(`^${label}`) }).first();
    await button.waitFor({ state: 'visible', timeout: 8000 });
    await button.click();
    await page.waitForTimeout(250);
}

async function pickerOpen(page) {
    return page.evaluate(() =>
        !!document.querySelector('#exp547-map-context canvas[style*="crosshair"]'));
}

// Leaving the source picker open silently poisons every later step, so the
// driver must never assume a pick succeeded.
async function ensureNotPicking(page) {
    if (!(await pickerOpen(page))) return true;
    await panelButton(page, 'Cancel');
    return !(await pickerOpen(page));
}

// Click a source region and VERIFY the assignment closed the picker. A wall
// needs a join column to its right, so some regions are legitimately refused;
// try a few before reporting failure.
async function pickSourceRegion(page, offsets) {
    if (!(await pickerOpen(page))) return 'no picker was open';
    for (const fx of offsets) {
        await page.evaluate(({ fx }) => {
            const canvas = document.querySelector('#exp547-map-context canvas[style*="crosshair"]');
            if (!canvas) return;
            const rect = canvas.getBoundingClientRect();
            canvas.dispatchEvent(new MouseEvent('click', {
                bubbles: true,
                clientX: rect.x + rect.width * fx,
                clientY: rect.y + rect.height * 0.42,
            }));
        }, { fx });
        await page.waitForTimeout(300);
        await dismissToast(page);
        if (!(await pickerOpen(page))) return `assigned by pointing at x=${fx.toFixed(2)}`;
    }
    await ensureNotPicking(page);
    return `refused every offered region (${offsets.join(', ')})`;
}

async function selectFromPalette(page, pattern) {
    await ensureNotPicking(page);
    await panelButton(page, 'Palette');
    await page.waitForTimeout(400);
    const chosen = await page.evaluate(source => {
        const cards = Array.from(document.querySelectorAll('#exp547-map-context div[title$="click to edit"]'));
        const target = cards.find(card => new RegExp(source, 'i').test(card.title));
        if (!target) return null;
        target.click();
        return target.title;
    }, pattern);
    await page.waitForTimeout(500);
    return chosen;
}

(async () => {
    fs.mkdirSync(OUT, { recursive: true });
    const browser = await chromium.launch(
        fs.existsSync(CHROME) ? { executablePath: CHROME } : {});
    const page = await browser.newPage({ viewport: { width: 1500, height: 940 } });
    const consoleErrors = [];
    page.on('console', message => { if (message.type() === 'error') consoleErrors.push(message.text()); });
    page.on('pageerror', error => consoleErrors.push(String(error)));

    await page.goto(`${BASE}/?exp=tileset-map-context`, { waitUntil: 'load' });
    await page.waitForFunction(
        () => document.getElementById('thestra-map-view-status')
            && /runtime geometry/.test(document.getElementById('thestra-map-view-status').textContent),
        null, { timeout: 180000 }
    );
    await page.waitForTimeout(1200);
    await installSignals(page);

    // GAUNTLET 1 — open an unfamiliar Map and understand its vocabulary.
    // A dungeon Map is used because doors and fixtures are part of the tasks.
    const opened = await selectMapByTitle(page, 'Entry Hall');
    log('gauntlet 1 · opened an unfamiliar Map', opened);
    const context = await page.evaluate(() => window.ThestraMapWorkspaceContext.runtimeContext());
    log('gauntlet 1 · runtime context', JSON.stringify(context));

    await panelButton(page, 'Palette');
    await shot(page, '01-vocabulary-of-this-place');
    log('gauntlet 1 · vocabulary read from Map context', flat(await panelText(page), 900));
    await panelButton(page, 'Palette');

    // GAUNTLET 2 — click a visible wall and reach its semantic owner.
    const wall = await clickRuntimeSurface(page, {
        surfaces: ['north-wall', 'south-wall', 'east-wall', 'west-wall'],
        needFeature: false, expectJob: 'Wall$',
    });
    log('gauntlet 2 · clicked wall reaches owner', JSON.stringify(wall.hit || wall.reason));
    await shot(page, '02-clicked-wall-reaches-owner');

    // GAUNTLET 3 — replace its Surface without typing coordinates.
    await panelButton(page, 'Replace this look');
    await shot(page, '03-source-picking-no-coordinates');
    log('gauntlet 3 · replaced the wall look by pointing',
        await pickSourceRegion(page, [0.10, 0.18, 0.34]));
    await shot(page, '04-provisional-marking-after-replace');
    log('gauntlet 3 · panel after replace', flat(await panelText(page), 600));

    // GAUNTLET 4 — add second and third weighted variants.
    await panelButton(page, '\\+ Variant');
    log('gauntlet 4 · second wall variant assigned visually',
        await pickSourceRegion(page, [0.30, 0.40, 0.14]));
    await panelButton(page, '\\+ Variant');
    log('gauntlet 4 · third wall variant assigned visually',
        await pickSourceRegion(page, [0.52, 0.60, 0.26]));
    // Author a meaningful weight through the pool slider.
    const weighted = await page.evaluate(() => {
        const sliders = Array.from(document.querySelectorAll('#exp547-map-context input[data-exp="weight"]'));
        if (sliders.length < 2) return null;
        sliders[1].value = '35';
        sliders[1].dispatchEvent(new Event('input', { bubbles: true }));
        sliders[1].dispatchEvent(new Event('change', { bubbles: true }));
        return sliders.map(slider => `${slider.dataset.variant}=${slider.value}`).join(' ');
    });
    log('gauntlet 4 · authored a weight', weighted ? `weights now ${weighted}` : 'no weight slider');
    await shot(page, '05-weighted-variants-authored-and-realized');

    // GAUNTLET 5 — inspect deterministic variant choices.
    log('gauntlet 5 · authored vs runtime-realized shares', flat(await panelText(page), 900));
    log('gauntlet 5 · realized census (engine truth)',
        JSON.stringify((await page.evaluate(() => window.exp547MapContextMetrics())).census));

    // GAUNTLET 6 — author floor and ceiling.
    const floor = await clickRuntimeSurface(page, {
        surfaces: ['floor'], needFeature: false, expectJob: 'Floor$',
    });
    log('gauntlet 6 · clicked floor reaches owner', JSON.stringify(floor.hit || floor.reason));
    await shot(page, '06-floor-owner-in-map-context');
    const ceilingCard = await selectFromPalette(page, 'ceiling');
    log('gauntlet 6 · ceiling reached from the palette board', ceilingCard || 'no ceiling card');
    await shot(page, '07-ceiling-owner');

    // GAUNTLET 7 — author a door / opening.
    const opening = await clickRuntimeSurface(page, {
        surfaces: ['opening'], needFeature: false, expectJob: 'Door',
    });
    log('gauntlet 7 · clicked opening reaches owner', JSON.stringify(opening.hit || opening.reason));
    await shot(page, '08-opening-owner');

    // GAUNTLET 8 — select a visible fixture and edit its Surface/model.
    const fixtureHit = await clickRuntimeSurface(page, {
        surfaces: ['north-wall', 'south-wall', 'east-wall', 'west-wall', 'floor-feature'],
        needFeature: true, expectJob: 'fixture',
    });
    let fixtureSource = fixtureHit.hit && fixtureHit.hit.owner;
    if (!fixtureHit.hit) {
        fixtureSource = await selectFromPalette(page, 'torch|sconce|brazier|crystal|column|chest|lamp|barrel');
        log('gauntlet 8 · fixture reached from the palette instead', `${fixtureHit.reason}; used ${fixtureSource}`);
    } else {
        log('gauntlet 8 · clicked fixture reaches owner', JSON.stringify(fixtureHit.hit));
    }
    await shot(page, '09-fixture-behaviour-editor');

    const controls = await page.evaluate(() => ({
        placementRule: document.querySelectorAll('#exp547-map-context select[data-exp="placement"]').length,
        chance: document.querySelectorAll('#exp547-map-context input[data-exp="chance"]').length,
        emission: document.querySelectorAll('#exp547-map-context button[data-exp="emission-warm"]').length,
        advanced: document.querySelectorAll('#exp547-map-context textarea[data-exp="advanced"]').length,
    }));
    log('gauntlet 8 · fixture controls present', JSON.stringify(controls));

    // GAUNTLET 10 — placement probability/rule without raw JSON.
    const ruleEdit = await page.evaluate(() => {
        const panel = document.getElementById('exp547-map-context');
        const out = {};
        const select = panel.querySelector('select[data-exp="placement"]');
        if (select) {
            const before = select.options[select.selectedIndex] && select.options[select.selectedIndex].text;
            select.value = 'beside_floor';
            select.dispatchEvent(new Event('change', { bubbles: true }));
            out.ruleWas = before;
            out.ruleNow = 'Beside open floor';
        }
        return out;
    });
    await page.waitForTimeout(300);
    const chanceEdit = await page.evaluate(() => {
        const panel = document.getElementById('exp547-map-context');
        const range = panel.querySelector('input[data-exp="chance"]');
        if (!range) return null;
        range.value = '40';
        range.dispatchEvent(new Event('input', { bubbles: true }));
        range.dispatchEvent(new Event('change', { bubbles: true }));
        return range.value;
    });
    log('gauntlet 10 · placement rule + chance set with no JSON',
        `${JSON.stringify(ruleEdit)} chance=${chanceEdit}%`);

    // GAUNTLET 9 — emission, judged in context.
    const emission = await page.evaluate(() => {
        const warm = document.querySelector('#exp547-map-context button[data-exp="emission-warm"]');
        if (!warm) return false;
        warm.click();
        return true;
    });
    await page.waitForTimeout(300);
    log('gauntlet 9 · warm emission authored', emission ? 'yes' : 'no');
    await shot(page, '10-emission-and-placement-rule');

    // GAUNTLET 11 — exact predicate representation as an advanced path.
    const advanced = await page.evaluate(() => {
        const area = document.querySelector('#exp547-map-context textarea[data-exp="advanced"]');
        return area ? area.value : null;
    });
    log('gauntlet 11 · exact authored record', flat(advanced, 700) || 'unavailable');
    await shot(page, '11-advanced-exact-record');

    // GAUNTLET 12 — structural / relief behaviour where vocabulary supports it.
    const wallAgain = await clickRuntimeSurface(page, {
        surfaces: ['north-wall', 'south-wall', 'east-wall', 'west-wall'],
        needFeature: false, expectJob: 'Wall$',
    });
    const structure = await page.evaluate(() => {
        const text = document.getElementById('exp547-map-context').innerText;
        const match = /Structure[\s\S]{0,340}/.exec(text);
        return match ? match[0] : null;
    });
    log('gauntlet 12 · structure/relief report',
        `${wallAgain.hit ? 'wall reselected' : wallAgain.reason} :: ${flat(structure, 400)}`);
    await shot(page, '12-structure-and-relief');

    // GAUNTLET 13/15 — save, then measure the authoritative correction and show
    // the provisional/authoritative boundary.
    const before = await page.evaluate(() => window.exp547MapContextMetrics());
    log('gauntlet 13 · dirty before save', String(before.dirty));
    if (!before.dirty) throw new Error('nothing was authored; the save/correction step would be vacuous');
    const bundlesBefore = await bundleCount(page);
    const wallClock = Date.now();
    await panelButton(page, 'Save');
    await page.waitForFunction(() => window.exp547MapContextMetrics().lastCorrectionMs != null,
        null, { timeout: 240000 });
    await waitForNewBundle(page, bundlesBefore).catch(() => {});
    const after = await page.evaluate(() => window.exp547MapContextMetrics());
    log('gauntlet 15 · provisional edit to authoritative correction',
        `${Math.round(after.lastCorrectionMs)} ms measured in-page, ${Date.now() - wallClock} ms wall clock`);
    log('gauntlet 13 · dirty after save', String(after.dirty));
    await shot(page, '13-authoritative-correction-applied');
    log('gauntlet 5b · realized census after the edit landed', JSON.stringify(after.census));

    // GAUNTLET 14 — another Map using the same palette; committed refresh.
    const switched = await selectMapByTitle(page, 'Chasm Crossing');
    log('gauntlet 14 · switched to another Map on the same palette', switched);
    await shot(page, '14-second-map-same-palette');
    const secondContext = await page.evaluate(() => window.ThestraMapWorkspaceContext.runtimeContext());
    const secondMetrics = await page.evaluate(() => window.exp547MapContextMetrics());
    log('gauntlet 14 · palette + census on the second Map',
        `${JSON.stringify(secondContext.bundleTileset)} census=${JSON.stringify(secondMetrics.census)}`);
    await panelButton(page, 'Palette');
    await shot(page, '15-second-map-vocabulary');
    log('gauntlet 14 · second Map vocabulary shows the committed edit',
        flat(await panelText(page), 900));

    const report = {
        capturedAt: new Date().toISOString(),
        base: BASE,
        firstMap: context,
        secondMap: secondContext,
        metrics: secondMetrics,
        consoleErrors,
        toasts: await page.evaluate(() => window.__toasts || []),
        steps,
    };
    fs.writeFileSync(path.join(OUT, 'capture-report.json'), JSON.stringify(report, null, 2));
    console.log('\n[capture] console errors:', consoleErrors.length);
    consoleErrors.slice(0, 12).forEach(error => console.log('   !', error));
    console.log(`[capture] wrote ${OUT}`);
    await browser.close();
})().catch(error => {
    console.error('[capture] failed:', error && error.message);
    process.exitCode = 1;
});
