'use strict';

// #967 contract publication tests.
//
// Two jobs. Against the real repository, prove the published values are the
// authored values and nothing else. Against fixtures, prove the three
// properties the architecture actually rests on: identity moves when any
// contributing input moves, a missing resource is reported rather than
// papered over, and an unresolvable font stops the build instead of starting
// an adapter against a font it cannot load.

const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const test = require('node:test');

const contract = require('./contract');

const REPO = path.resolve(__dirname, '..', '..');
const PROJECT = path.join(REPO, 'projects', 'hichaukitoden-game');
const RUNTIME = path.join(REPO, 'runtime');
const RTP = path.join(REPO, 'rtp');

function real() {
    return contract.build({ projectDir: PROJECT, runtimeDir: RUNTIME, rtpRoot: RTP });
}

function put(file, value) {
    fs.mkdirSync(path.dirname(file), { recursive: true });
    fs.writeFileSync(file, value);
}
function json(file, value) { put(file, JSON.stringify(value, null, 2) + '\n'); }

// A self-contained installation + Project + RTP triple, so a test can move one
// input at a time and watch the identity respond.
function fixture(mutate = () => {}) {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'presentation-contract-'));
    const runtimeDir = path.join(root, 'runtime');
    const projectDir = path.join(root, 'project');
    const rtpRoot = path.join(root, 'rtp');

    const installation = {
        version: 1,
        metrics: { tileSize: 8, screenWidthTiles: 32, screenHeightTiles: 30, gaugeHeight: 2, panelMinWidth: 16, panelMinHeight: 9 },
        atlas: {
            windowskin: {
                background: { x: 0, y: 0, w: 32, h: 32 }, border: 8, backgroundInset: 4,
                parts: { tl: { x: 32, y: 0, w: 8, h: 8 } },
                roles: { back: 'windowskin_back' },
            },
            target: { image: 'UI_Target', border: 8, parts: { tl: { x: 0, y: 0, w: 8, h: 8 } } },
        },
        palettes: { tone: { good: [0.45, 0.95, 0.5, 1] } },
    };
    const system = {
        ui: { activeFont: 'Fixture', fontSize: 16, fontOffsetY: -4, textPalette: [[1, 1, 1, 1]] },
        rtp: { revision: '1.0' },
        combat: { secretGameplayPolicy: true },
    };

    const state = { installation, system, root, runtimeDir, projectDir, rtpRoot };
    mutate(state);

    json(path.join(runtimeDir, 'presentation', 'presentation.json'), state.installation);
    json(path.join(projectDir, 'data', 'system.json'), state.system);
    put(path.join(projectDir, 'assets', 'fonts', 'Fixture.ttf'), 'FONT BYTES');
    put(path.join(projectDir, 'assets', 'system', 'windowskin_back.png'), 'BACK SKIN');
    put(path.join(projectDir, 'assets', 'system', 'UI_Target.png'), 'TARGET');
    put(path.join(projectDir, 'assets', 'system', 'iconset.png'), 'ICONSET');
    put(path.join(projectDir, 'assets', 'system', 'Cursor.png'), 'CURSOR');
    json(path.join(rtpRoot, 'revisions', '1.0', 'manifest.json'), { version: 1, revision: '1.0', resources: [] });

    return state;
}
function buildFixture(state) {
    return contract.build({ projectDir: state.projectDir, runtimeDir: state.runtimeDir, rtpRoot: state.rtpRoot });
}

test('publishes the installation facts byte-for-byte', () => {
    const published = real();
    const authored = JSON.parse(fs.readFileSync(path.join(RUNTIME, 'presentation', 'presentation.json'), 'utf8'));

    assert.deepStrictEqual(published.metrics, stripComments(authored.metrics));
    assert.deepStrictEqual(published.atlas, stripComments(authored.atlas));
    assert.deepStrictEqual(published.palettes, stripComments(authored.palettes));

    function stripComments(value) {
        if (Array.isArray(value)) return value.map(stripComments);
        if (!value || typeof value !== 'object') return value;
        return Object.fromEntries(Object.entries(value).filter(([k]) => !k.startsWith('_')).map(([k, v]) => [k, stripComments(v)]));
    }
});

test('publishes the Project UI values byte-for-byte and nothing else from system.json', () => {
    const published = real();
    const system = JSON.parse(fs.readFileSync(path.join(PROJECT, 'data', 'system.json'), 'utf8'));

    for (const [key, value] of Object.entries(published.project)) {
        assert.deepStrictEqual(value, system.ui[key], `published project.${key} is not the authored value`);
    }
    // The allowlist is the point: system.json also carries combat, growth,
    // permadeath and spawn policy, and a presentation consumer has no business
    // receiving any of it.
    for (const forbidden of ['combat', 'growth', 'permadeath', 'spawn', 'dungeon', 'summoner']) {
        assert.strictEqual(published.project[forbidden], undefined, `${forbidden} leaked into the presentation contract`);
        assert.ok(!Object.prototype.hasOwnProperty.call(published, forbidden), `${forbidden} leaked into the presentation contract`);
    }
});

test('resolves the active font to a real file with an ownership provider', () => {
    const published = real();
    assert.strictEqual(published.font.active, 'monogram-extended-italic');
    assert.strictEqual(published.font.engineDefault, false);
    assert.ok(fs.existsSync(path.join(PROJECT, published.font.logicalPath)), 'active font logicalPath does not resolve');
    assert.ok(['project', 'rtp'].includes(published.font.provider.kind));
    for (const asset of published.assets) {
        assert.ok(asset.provider && ['project', 'rtp'].includes(asset.provider.kind),
            `asset ${asset.logicalPath} has no Project/RTP ownership`);
    }
});

test('every declared windowskin role appears as an asset, present or not', () => {
    const published = real();
    const roles = Object.keys(published.atlas.windowskin.roles);
    for (const role of roles) {
        const asset = published.assets.find(entry => entry.role === `windowskin.${role}`);
        assert.ok(asset, `windowskin role '${role}' is not represented in assets`);
        assert.strictEqual(typeof asset.available, 'boolean');
    }
});

test('identity is stable for identical inputs and independent of key order', () => {
    assert.strictEqual(real().identity, real().identity);
    assert.strictEqual(
        contract.canonical({ b: 1, a: { d: 2, c: 3 } }),
        contract.canonical({ a: { c: 3, d: 2 }, b: 1 }));
});

test('identity moves when an installation fact moves', () => {
    const before = buildFixture(fixture()).identity;
    const after = buildFixture(fixture(state => { state.installation.metrics.tileSize = 16; })).identity;
    assert.notStrictEqual(before, after);
});

test('identity moves when an authored Project UI value moves', () => {
    const before = buildFixture(fixture()).identity;
    const after = buildFixture(fixture(state => { state.system.ui.fontOffsetY = -3; })).identity;
    assert.notStrictEqual(before, after);
});

test('identity moves when an asset\'s BYTES move, with no authored change at all', () => {
    // The stale-cache case that matters most: someone repaints the windowskin
    // and every JSON file in the Project is untouched.
    const state = fixture();
    const before = buildFixture(state).identity;
    put(path.join(state.projectDir, 'assets', 'system', 'windowskin_back.png'), 'REPAINTED SKIN');
    assert.notStrictEqual(before, buildFixture(state).identity);
});

test('identity moves when the pinned RTP revision moves', () => {
    const state = fixture();
    const before = buildFixture(state).identity;
    state.system.rtp = { revision: '2.0' };
    json(path.join(state.projectDir, 'data', 'system.json'), state.system);
    json(path.join(state.rtpRoot, 'revisions', '2.0', 'manifest.json'), { version: 1, revision: '2.0', resources: [] });
    assert.notStrictEqual(before, buildFixture(state).identity);
});

test('a missing system asset is reported, not dropped and not invented', () => {
    const state = fixture();
    fs.rmSync(path.join(state.projectDir, 'assets', 'system', 'windowskin_back.png'));
    const published = buildFixture(state);
    const skin = published.assets.find(entry => entry.role === 'windowskin.back');
    assert.ok(skin, 'a missing skin must still appear in the asset list');
    assert.strictEqual(skin.available, false);
    assert.strictEqual(skin.sha256, null);
    assert.match(skin.unavailableReason, /windowskin_back\.png/);
});

test('an unresolvable font stops the build', () => {
    const state = fixture();
    fs.rmSync(path.join(state.projectDir, 'assets', 'fonts', 'Fixture.ttf'));
    assert.throws(() => buildFixture(state), /Fixture is missing from the Project and pinned RTP revision/);
});

test('a malformed installation contract stops the build', () => {
    for (const [label, mutate] of [
        ['unsupported version', state => { state.installation.version = 2; }],
        ['missing palettes', state => { delete state.installation.palettes; }],
        ['zero-area rectangle', state => { state.installation.atlas.windowskin.parts.tl = { x: 0, y: 0, w: 0, h: 8 }; }],
        ['negative origin', state => { state.installation.atlas.target.parts.tl = { x: -1, y: 0, w: 8, h: 8 }; }],
    ]) {
        assert.throws(() => buildFixture(fixture(mutate)), undefined, `${label} must stop the build`);
    }
});

test('the engine-default font is named, never substituted', () => {
    const state = fixture(s => { s.system.ui.activeFont = contract.ENGINE_DEFAULT_FONT; });
    const published = buildFixture(state);
    assert.strictEqual(published.font.active, contract.ENGINE_DEFAULT_FONT);
    assert.strictEqual(published.font.engineDefault, true);
    assert.strictEqual(published.font.logicalPath, null,
        'the engine default has no file; publishing a path for it would be a substituted face');
});
