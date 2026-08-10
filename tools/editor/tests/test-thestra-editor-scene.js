'use strict';

const assert = require('assert');
const Scene = require('../js/thestra-editor-scene.js');
const Commands = require('../js/second-rite-editor-commands.js');
const Adapter = require('../js/second-rite-editor-adapter.js');
const EventPresentation = require('../js/event_presentation.js');

(function testAuthoredGridAndEventProjection() {
    const payload = { commonEvents: { 7: { model: 'assets/models/npc.obj', sprite: 'assets/sprites/npc.png' } } };
    const map = {
        id: 3,
        title: 'Test',
        layout: ['#o', '..'],
        events: [
            { id: 9, scriptId: 7, x: 1, y: 1 },
            { id: 10, scriptId: 7, x: 0, y: 1, model: false }
        ]
    };
    const scene = Scene.buildScene(payload, map);
    assert.strictEqual(scene.version, 2);
    assert.deepStrictEqual(scene.bounds, { width: 2, height: 2 });
    assert.strictEqual(scene.cells.find(c => c.key === 'cell:0:0').role, 'wall');
    assert.strictEqual(scene.cells.find(c => c.key === 'cell:1:0').role, 'opening');
    assert.deepStrictEqual(scene.events[0].world, { x: 1.5, y: 0.5, z: 1.5 });
    assert.deepStrictEqual(scene.events[0].size, { x: 1, y: 1, z: 1 });
    assert.strictEqual(scene.events[0].index, 0);
    assert.strictEqual(scene.events[0].asset.model, 'assets/models/npc.obj');
    assert.strictEqual(scene.events[1].asset.model, null);
    assert.strictEqual(scene.events[1].asset.sprite, 'assets/sprites/npc.png');
    assert.strictEqual(scene.assets, undefined, 'semantic scene must not carry browser-derived runtime tileset state');
})();

(function testLightsOverridesAndSpawnAreSemantic() {
    const payload = {
        system: { spawn: { mapId: 4, x: 2, y: 1, dir: 'E' } }
    };
    const map = {
        id: 4,
        title: 'Semantics',
        layout: ['....', '....', '....'],
        events: [],
        lightObjects: [
            { x: 1, y: 2, radius: 5, falloff: 3, color: [0.2, 0.4, 0.8], material: 'mist' }
        ],
        overrides: [{ x: 3, y: 0, floor: 'moss' }]
    };
    const scene = Scene.buildScene(payload, map);
    assert.strictEqual(scene.lights.length, 1);
    assert.deepStrictEqual(scene.lights[0].cell, { x: 1, y: 2 });
    assert.strictEqual(scene.lights[0].radius, 5);
    assert.deepStrictEqual(scene.lights[0].color, [0.2, 0.4, 0.8]);
    assert.strictEqual(scene.annotations.overrides.length, 1);
    assert.strictEqual(scene.annotations.overrides[0].key, 'override:0');
    assert.deepStrictEqual(scene.annotations.spawn.cell, { x: 2, y: 1 });
})();

(function testProceduralMapsAreMarkedAndCannotBePainted() {
    const map = { id: 8, width: 4, height: 3 };
    const layout = Scene.materializeLayout(map);
    assert.strictEqual(layout.provisional, true);
    assert.strictEqual(layout.source, 'editor-procedural-placeholder');
    assert.strictEqual(layout.rows[0], '####');
    assert.strictEqual(layout.rows[1], '#..#');

    const payload = { maps: [map] };
    const paint = Commands.paintCell(payload, 0, 1, 1, '#');
    assert.deepStrictEqual(paint.cell, { x: 1, y: 1 });
    assert.strictEqual(paint.ok, false);
    assert.strictEqual(paint.reason, 'procedural-layout-uneditable');
    assert.strictEqual(map.layout, undefined, 'editing must not materialize the browser placeholder into authored data');
})();

(function testGridPaintingMutatesOnlyLegalAuthoredCells() {
    const map = { id: 1, layout: ['#.', '..'], events: [] };
    const payload = { maps: [map] };
    assert.strictEqual(Commands.tileForTool('wall'), '#');
    assert.strictEqual(Commands.tileForTool('opening'), 'o');

    const changed = Commands.paintCell(payload, 0, 1, 0, '#');
    assert.strictEqual(changed.ok, true);
    assert.strictEqual(changed.changed, true);
    assert.strictEqual(map.layout[0], '##');

    const same = Commands.paintCell(payload, 0, 1, 0, '#');
    assert.strictEqual(same.ok, true);
    assert.strictEqual(same.changed, false);

    assert.strictEqual(Commands.paintCell(payload, 0, 9, 9, '.').reason, 'out-of-bounds');
    assert.strictEqual(Commands.paintCell(payload, 0, 0, 0, 'x').reason, 'invalid-tile');
})();

(function testEventMovementHonorsGridAndOccupancy() {
    const map = {
        id: 1,
        layout: ['...', '...', '...'],
        events: [
            { id: 10, x: 0, y: 0 },
            { id: 11, x: 1, y: 1 }
        ]
    };
    const payload = { maps: [map] };
    const occupied = Commands.canMoveEvent(payload, 0, 10, 1, 1);
    assert.strictEqual(occupied.ok, false);
    assert.strictEqual(occupied.reason, 'occupied');

    const moved = Commands.moveEvent(payload, 0, 10, 2, 2);
    assert.strictEqual(moved.ok, true);
    assert.strictEqual(moved.changed, true);
    assert.deepStrictEqual({ x: map.events[0].x, y: map.events[0].y }, { x: 2, y: 2 });
    assert.deepStrictEqual(moved.selection.cell, { x: 2, y: 2 });
    assert.strictEqual(Commands.moveEvent(payload, 0, 10, 2.5, 2).reason, 'invalid-cell');
})();

(function testLightMovementHonorsGridAndOccupancy() {
    const map = {
        id: 1,
        layout: ['...', '...', '...'],
        lightObjects: [
            { x: 0, y: 0 },
            { x: 1, y: 1 }
        ]
    };
    const payload = { maps: [map] };
    const occupied = Commands.canMoveLight(payload, 0, 0, 1, 1);
    assert.strictEqual(occupied.ok, false);
    assert.strictEqual(occupied.reason, 'occupied');

    const moved = Commands.moveLight(payload, 0, 0, 2, 1);
    assert.strictEqual(moved.ok, true);
    assert.strictEqual(moved.changed, true);
    assert.deepStrictEqual({ x: map.lightObjects[0].x, y: map.lightObjects[0].y }, { x: 2, y: 1 });
    assert.deepStrictEqual(moved.selection.cell, { x: 2, y: 1 });
})();

(function testEventPresentationStillLoadsWithoutBrowserGlobals() {
    const target = { model: 'old.obj' };
    EventPresentation.serializeEventPresentation({ modelMode: 'suppress', modelValue: false }, target);
    assert.strictEqual(target.model, false);
})();

(async function testAdapterKeepsSemanticSceneSeparateFromRuntimeRenderables() {
    const authoredMap = { id: 1, title: 'Unsaved title', layout: ['.'], events: [] };
    const payload = { maps: [authoredMap] };
    const scene = await Adapter.buildScene(payload, 0);
    assert.strictEqual(scene.map.title, 'Unsaved title');
    assert.strictEqual(scene.assets, undefined);

    let request = null;
    const fakeFetch = async (url, options) => {
        request = { url, options };
        return {
            ok: true,
            status: 200,
            json: async () => ({
                version: 1,
                map: { id: 1, name: 'Unsaved title' },
                coordinateSystem: {
                    handedness: 'right', up: 'z', unit: 'map-cell',
                    runtimeGridOrigin: { x: 1, y: 1 }, authoredGridOrigin: { x: 0, y: 0 }, uvOrigin: 'top-left'
                },
                materials: [{ id: 'material_001', color: [1, 1, 1, 1] }],
                surfaces: [{
                    id: 'floor_1_1', material: 'material_001',
                    source: { kind: 'cell', x: 0, y: 0, surface: 'floor' },
                    positions: [1, 1, 0, 2, 1, 0, 2, 2, 0],
                    uvs: [0, 0, 1, 0, 1, 1],
                    normals: [0, 0, 1, 0, 0, 1, 0, 0, 1],
                    colors: [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
                }],
                stats: { surfaceCount: 1, materialCount: 1, vertexCount: 3, triangleCount: 1 }
            })
        };
    };

    const bundle = await Adapter.loadRenderable(authoredMap, fakeFetch);
    assert.strictEqual(request.url, Adapter.DEFAULT_RENDERABLE_URL);
    assert.strictEqual(request.options.method, 'POST');
    assert.strictEqual(request.options.headers['Content-Type'], 'application/json');
    assert.deepStrictEqual(JSON.parse(request.options.body), { map: authoredMap });
    assert.strictEqual(bundle.surfaces[0].source.x, 0);
    assert.strictEqual(authoredMap.title, 'Unsaved title', 'runtime rendering must not mutate authored map data');
    console.log('Thestra Editor Scene PR2 tests OK');
})().catch(error => {
    console.error(error);
    process.exitCode = 1;
});
