'use strict';

const assert = require('assert');
const Scene = require('../js/thestra-editor-scene.js');
const Adapter = require('../js/second-rite-editor-adapter.js');

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
    assert.deepStrictEqual(scene.bounds, { width: 2, height: 2 });
    assert.strictEqual(scene.cells.find(c => c.key === 'cell:0:0').role, 'wall');
    assert.strictEqual(scene.cells.find(c => c.key === 'cell:1:0').role, 'opening');
    assert.deepStrictEqual(scene.events[0].world, { x: 1.5, y: 0.5, z: 1.5 });
    assert.deepStrictEqual(scene.events[0].size, { x: 1, y: 1, z: 1 });
    assert.strictEqual(scene.events[0].asset.model, 'assets/models/npc.obj');
    assert.strictEqual(scene.events[1].asset.model, null);
    assert.strictEqual(scene.events[1].asset.sprite, 'assets/sprites/npc.png');
    assert.strictEqual(scene.assets, undefined, 'semantic scene must not carry a browser-derived runtime tileset');
})();

(function testProceduralMapsAreMarkedAsEditorPlaceholders() {
    const layout = Scene.materializeLayout({ width: 4, height: 3 });
    assert.strictEqual(layout.provisional, true);
    assert.strictEqual(layout.source, 'editor-procedural-placeholder');
    assert.strictEqual(layout.rows[0], '####');
    assert.strictEqual(layout.rows[1], '#..#');
})();

(async function testAdapterKeepsSemanticSceneSeparateFromRuntimeRenderables() {
    const authoredMap = { id: 1, title: 'Unsaved title', layout: ['.'], events: [] };
    const payload = { maps: [authoredMap] };
    const scene = await Adapter.buildScene(payload, 0);
    assert.strictEqual(scene.map.title, 'Unsaved title');

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

    const refusalCalls = [];
    await assert.rejects(
        () => Adapter.loadRenderable(authoredMap, async (url, options) => {
            refusalCalls.push({ url, options });
            if (options.method === 'POST') throw new TypeError('Failed to fetch');
            return { type: 'opaque', status: 0 };
        }),
        error => {
            assert.strictEqual(error.code, 'bridge-refused');
            assert.match(error.message, /running but refused the Studio request/);
            assert.match(error.message, /EDITOR_PORT/);
            return true;
        }
    );
    assert.deepStrictEqual(refusalCalls.map(call => call.options.method), ['POST', 'GET']);
    assert.strictEqual(refusalCalls[1].options.mode, 'no-cors');
    assert.strictEqual(refusalCalls[1].options.cache, 'no-store');

    await assert.rejects(
        () => Adapter.loadRenderable(authoredMap, async () => {
            throw new TypeError('connection refused');
        }),
        error => {
            assert.strictEqual(error.code, 'bridge-unreachable');
            assert.match(error.message, /not reachable/);
            return true;
        }
    );

    await assert.rejects(
        () => Adapter.loadRenderable(authoredMap, async () => ({
            ok: false,
            status: 403,
            json: async () => ({ error: 'runtime bridge accepts only the local Studio origin' })
        })),
        error => {
            assert.strictEqual(error.code, 'bridge-refused');
            assert.match(error.message, /local Studio origin/);
            return true;
        }
    );

    console.log('Thestra Editor Scene tests OK');
})().catch(error => {
    console.error(error);
    process.exitCode = 1;
});
