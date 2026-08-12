'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');
const inspector = require('./js/tileset-surface-inspector');
const runtimeBridge = require('./runtime-bridge-server');

function canonicalTileset() {
    return {
        id: 'probe_tileset',
        name: 'Probe',
        texture: 'assets/tilesets/probe.png',
        heightMap: 'assets/geometry/probe-height.png',
        heightMapScale: { wall: 0.1, floor: 0.05, ceiling: 0.02 },
        base: {
            walls: [
                { id: 'wall_a', role: 'base_wall', middle: [0, 0], weight: 50 },
                { id: 'wall_b', role: 'base_wall', middle: [0, 1], weight: 50 },
            ],
            floors: [{ id: 'floor_a', role: 'base_floor', atlas: [1, 0], weight: 100 }],
            ceilings: [{ id: 'ceiling_a', role: 'base_ceiling', atlas: [2, 0], weight: 100 }],
        },
        doors: [],
        features: [],
        _storageVersion: 'transport-only',
    };
}

function studio(role, variantId) {
    const canonical = canonicalTileset();
    const tileset = JSON.parse(JSON.stringify(canonical));
    delete tileset._storageVersion;
    return { canonical, tileset, role, variantId };
}

test('probe override carries unsaved values and forces one selected variant', () => {
    const snapshot = studio('wall', 'wall_b');
    snapshot.tileset.base.walls[1].geometry = 'assets/geometry/unsaved-wall';
    snapshot.tileset.heightMapScale.wall = 0.22;

    const probe = inspector.buildProbeRequest(snapshot);
    assert.equal(probe.request.geometryProfile, 'authoring');
    assert.deepEqual(probe.request.map.layout, ['###', '#.#', '###']);
    assert.equal(probe.request.map.safe, true);
    assert.equal(probe.request.map.tileset, 'probe_tileset');
    assert.equal(probe.request.map.tilesetOverride._storageVersion, undefined);
    assert.equal(probe.request.map.tilesetOverride.id, undefined);
    assert.equal(probe.request.map.tilesetOverride.heightMapScale.wall, 0.22);

    const forced = probe.request.map.tilesetOverride.base.walls;
    assert.equal(forced[0].id, 'wall_b');
    assert.equal(forced[0].geometry, 'assets/geometry/unsaved-wall');
    assert.deepEqual(forced.slice(1), [{ id: 'wall_a', remove: true }]);
});

test('renamed unsaved variant removes its old canonical identity', () => {
    const snapshot = studio('wall', 'wall_b');
    snapshot.tileset.base.walls[1].id = 'wall_b_renamed';
    snapshot.variantId = 'wall_b_renamed';
    const forced = inspector.buildProbeRequest(snapshot).request.map.tilesetOverride.base.walls;
    assert.equal(forced[0].id, 'wall_b_renamed');
    assert(forced.some(v => v.id === 'wall_b' && v.remove === true));
    assert(forced.some(v => v.id === 'wall_a' && v.remove === true));
});

test('ceiling asks the runtime for play visibility so a ceiling actually exists', () => {
    const probe = inspector.buildProbeRequest(studio('ceiling', 'ceiling_a'));
    assert.equal(probe.request.geometryProfile, 'play');
});

test('renderable request validation accepts only explicit visibility profiles', () => {
    const base = inspector.buildProbeRequest(studio('floor', 'floor_a')).request;
    assert.equal(runtimeBridge.validateRequest(base).geometryProfile, 'authoring');
    assert.throws(
        () => runtimeBridge.validateRequest({ ...base, geometryProfile: 'editor-but-not-real' }),
        /geometryProfile must be authoring or play/);
});

test('resolved surface filtering consumes engine provenance rather than rebuilding geometry', () => {
    const bundle = {
        surfaces: [
            { id: 'wanted', source: { x: 1, y: 0, surface: 'south-wall' }, positions: [0,0,0, 1,0,0, 0,0,1] },
            { id: 'other-wall', source: { x: 0, y: 1, surface: 'east-wall' }, positions: [0,0,0, 1,0,0, 0,0,1] },
            { id: 'floor', source: { x: 1, y: 1, surface: 'floor' }, positions: [0,0,0, 1,0,0, 0,1,0] },
        ],
    };
    assert.deepEqual(inspector.filterResolvedSurfaces(bundle, 'wall').map(s => s.id), ['wanted']);
    assert.deepEqual(inspector.filterResolvedSurfaces(bundle, 'floor').map(s => s.id), ['floor']);
});

test('non-structural roles fail loudly instead of pretending to resolve them', () => {
    assert.throws(
        () => inspector.buildProbeRequest({ canonical: canonicalTileset(), tileset: canonicalTileset(), role: 'door', variantId: 'door_a' }),
        /select a Wall, Floor, or Ceiling/);
});
