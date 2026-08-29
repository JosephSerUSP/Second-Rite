'use strict';

// #968 adapter tests.
//
// The pixel question is answered by tools/presentation/parity against the real
// LÖVE renderer. What is left for a unit test is everything that is NOT a
// pixel: that the adapter refuses to invent facts, that the pure geometry it
// still owns matches ui.lua's rule, and -- most importantly -- the negative
// control that no browser file has regrown a handwritten copy of a promoted
// fact. That last one is what keeps the architecture enforceable instead of
// advisory: without it an author can paste the atlas back into JavaScript and
// every other check stays green.

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const test = require('node:test');

const adapter = require('./second-gate-ui');
const contractBuilder = require('../contract');

const REPO = path.resolve(__dirname, '..', '..', '..');
const PROJECT = path.join(REPO, 'projects', 'hichaukitoden-game');
const RUNTIME = path.join(REPO, 'runtime');
const RTP = path.join(REPO, 'rtp');

const contract = contractBuilder.build({ projectDir: PROJECT, runtimeDir: RUNTIME, rtpRoot: RTP });
const ui = adapter.create({ contract, images: {} });

test('refuses to start without a contract', () => {
    assert.throws(() => adapter.create({}), /has no contract/);
});

test('names the missing fact rather than guessing one', () => {
    const gutted = JSON.parse(JSON.stringify(contract));
    delete gutted.atlas.windowskin.border;
    assert.throws(() => adapter.create({ contract: gutted, images: {} }),
        /atlas\.windowskin\.border/);

    const shallow = JSON.parse(JSON.stringify(contract));
    delete shallow.palettes;
    assert.throws(() => adapter.create({ contract: shallow, images: {} }), /palettes/);
});

test('edge snapping matches ui.lua: both edges round, not position and size', () => {
    // The bug this rule exists to prevent: rounding x and w independently lets
    // the far edge jitter by a pixel while the near one settles, which is what
    // left a seam between the tiled interior and the border ring mid-animation.
    assert.deepStrictEqual(adapter.snapRect(10.4, 10.4, 20.4, 20.4), { x: 10, y: 10, w: 21, h: 21 });
    assert.deepStrictEqual(adapter.snapRect(10.6, 10.6, 20.4, 20.4), { x: 11, y: 11, w: 20, h: 20 });
    assert.deepStrictEqual(adapter.snapRect(0, 0, 16, 9), { x: 0, y: 0, w: 16, h: 9 });
});

test('opening geometry grows both axes at the same pixel rate', () => {
    const minW = contract.metrics.panelMinWidth;
    const minH = contract.metrics.panelMinHeight;

    // At p=0 the rect sits on its floors, and the floors are the contract's,
    // not a number this file chose.
    const closed = ui.rescaleRect(0, 0, 200, 100, 0);
    assert.strictEqual(closed.w, minW);
    assert.strictEqual(closed.h, minH);

    // At p=1 the longer axis completes exactly, which is what makes an
    // authored duration mean "time until fully open".
    const open = ui.rescaleRect(0, 0, 200, 100, 1);
    assert.strictEqual(open.w, 200);
    assert.strictEqual(open.h, 100);

    // Mid-way, a WIDE rect must be further along in height than in width --
    // it unrolls sideways. A per-axis-fraction implementation would make these
    // two ratios equal, which is the mistake this assertion exists to catch.
    const mid = ui.rescaleRect(0, 0, 200, 100, 0.5);
    assert.ok(mid.h / 100 > mid.w / 200,
        `expected height to lead width, got ${mid.w}x${mid.h}`);
    assert.strictEqual(mid.h, 100, 'at p=0.5 a 200-long rect has already reached its 100 height');

    // Out-of-range progress clamps rather than overshooting.
    assert.deepStrictEqual(ui.rescaleRect(0, 0, 200, 100, 5), ui.rescaleRect(0, 0, 200, 100, 1));
    assert.deepStrictEqual(ui.rescaleRect(0, 0, 200, 100, -5), ui.rescaleRect(0, 0, 200, 100, 0));
});

test('rich text splits on the authored palette, with ui.lua\'s wrap', () => {
    const palette = contract.project.textPalette;
    const runs = ui.parseRichText('plain \\c[2]red\\c[0] tail', [1, 1, 1, 1]);
    assert.deepStrictEqual(runs.map(run => run.text), ['plain ', 'red', ' tail']);
    assert.deepStrictEqual(runs[0].color, [1, 1, 1, 1]);
    // ui.lua indexes `palette[code % #palette + 1]`, which in a 1-based table
    // is element `code % n` in 0-based terms. Mirrored, not reinvented.
    assert.deepStrictEqual(runs[1].color, palette[2 % palette.length]);
    assert.deepStrictEqual(runs[2].color, palette[0]);
});

test('rich text refuses to run without an authored palette', () => {
    const gutted = JSON.parse(JSON.stringify(contract));
    delete gutted.project.textPalette;
    const bare = adapter.create({ contract: gutted, images: {} });
    assert.throws(() => bare.parseRichText('x', [1, 1, 1, 1]), /textPalette/);
});

test('theme CSS carries only published facts', () => {
    const css = ui.themeCss({ assetBase: '/' });
    assert.match(css, /@font-face/);
    assert.match(css, new RegExp(contract.font.logicalPath.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
    assert.match(css, /--sg-font-size: 16px/);
    assert.match(css, /--sg-font-offset-y: -4px/);
    assert.match(css, /--sg-tone-good:/);
    assert.match(css, /image-rendering: pixelated/);
    contract.project.textPalette.forEach((_, index) => {
        assert.match(css, new RegExp(`--sg-text-${index}:`));
    });
});

test('the engine-default font is never given a substitute face', () => {
    const defaulted = JSON.parse(JSON.stringify(contract));
    defaulted.font = { active: 'Lucida', engineDefault: true, logicalPath: null, provider: null };
    const css = adapter.create({ contract: defaulted, images: {} }).themeCss();
    assert.ok(!/@font-face/.test(css), 'the engine default has no file to declare');
    assert.match(css, /--sg-font-family: monospace/);
});

test('reports a resource the contract declared unavailable', () => {
    const degraded = JSON.parse(JSON.stringify(contract));
    const skin = degraded.assets.find(entry => entry.role === 'windowskin.back');
    skin.available = false;
    skin.sha256 = null;
    skin.unavailableReason = 'Project does not provide assets/system/windowskin_back.png';
    const missing = adapter.create({ contract: degraded, images: {} }).missingAssets();
    assert.ok(missing.some(entry => entry.role === 'windowskin.back'),
        'a surface must be able to SAY a windowskin was missing, not just render without it');
});

test('no browser file respells a promoted presentation fact', () => {
    // The negative control. Scans the adapter and every browser surface that
    // consumes it for the literal spellings of facts the contract owns.
    const scanned = [
        path.join(__dirname, 'second-gate-ui.js'),
        ...[path.join(REPO, 'tools', 'npc-gauntlet', 'public')]
            .filter(dir => fs.existsSync(dir))
            .flatMap(dir => fs.readdirSync(dir).filter(name => name.endsWith('.js')).map(name => path.join(dir, name))),
    ];

    const rects = [];
    for (const [atlasName, atlas] of Object.entries(contract.atlas)) {
        for (const [partName, rect] of Object.entries(atlas.parts)) {
            rects.push({ label: `atlas.${atlasName}.parts.${partName}`, rect });
        }
    }

    for (const file of scanned) {
        const source = fs.readFileSync(file, 'utf8');
        const relative = path.relative(REPO, file);

        for (const { label, rect } of rects) {
            // The four numbers together, in the orders a drawImage or an
            // object literal would put them. Any one number alone is a
            // coincidence; all four in order is a transcribed rectangle.
            for (const spelling of [
                `${rect.x}, ${rect.y}, ${rect.w}, ${rect.h}`,
                `${rect.x},${rect.y},${rect.w},${rect.h}`,
                `x: ${rect.x}, y: ${rect.y}, w: ${rect.w}, h: ${rect.h}`,
            ]) {
                assert.ok(!source.includes(spelling),
                    `${relative} spells the atlas rectangle ${label} as a literal ('${spelling}'); `
                    + 'it belongs to runtime/presentation/presentation.json (#967)');
            }
        }

        for (const [group, entries] of Object.entries(contract.palettes)) {
            for (const [name, value] of Object.entries(entries)) {
                if (!Array.isArray(value)) continue;
                for (const spelling of [`[${value.join(', ')}]`, `[${value.join(',')}]`]) {
                    assert.ok(!source.includes(spelling),
                        `${relative} spells the colour palettes.${group}.${name} as a literal ('${spelling}'); `
                        + 'it belongs to runtime/presentation/presentation.json (#967)');
                }
            }
        }
    }
});
