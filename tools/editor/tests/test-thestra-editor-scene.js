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
    const scene = Scene.buildScene(payload, map, { tilesetId: 'test' });
    assert.deepStrictEqual(scene.bounds, { width: 2, height: 2 });
    assert.strictEqual(scene.cells.find(c => c.key === 'cell:0:0').role, 'wall');
    assert.strictEqual(scene.cells.find(c => c.key === 'cell:1:0').role, 'opening');
    assert.deepStrictEqual(scene.events[0].world, { x: 1.5, y: 0.5, z: 1.5 });
    assert.deepStrictEqual(scene.events[0].size, { x: 1, y: 1, z: 1 });
    assert.strictEqual(scene.events[0].asset.model, 'assets/models/npc.obj');
    assert.strictEqual(scene.events[1].asset.model, null);
    assert.strictEqual(scene.events[1].asset.sprite, 'assets/sprites/npc.png');
})();

(function testProceduralMapsAreMarkedAsEditorPlaceholders() {
    const layout = Scene.materializeLayout({ width: 4, height: 3 });
    assert.strictEqual(layout.provisional, true);
    assert.strictEqual(layout.source, 'editor-procedural-placeholder');
    assert.strictEqual(layout.rows[0], '####');
    assert.strictEqual(layout.rows[1], '#..#');
})();

(function testTilesetOverridesMirrorRuntimePoolRules() {
    const base = {
        id: 'dungeon_default',
        texture: 'assets/tilesets/base.png',
        base: {
            walls: [{ id: 'wall_a', weight: 100, middle: [1, 0] }],
            floors: [{ id: 'floor_a', weight: 100, atlas: [0, 1] }]
        },
        doors: [{ id: 'door_a', atlas: [1, 1] }],
        features: [{ id: 'torch', role: 'wall_feature', model: 'assets/models/torch.obj' }]
    };
    const map = {
        tilesetOverride: {
            texture: 'assets/tilesets/override.png',
            base: { walls: [{ id: 'wall_a', middle: [2, 0] }] },
            features: [
                { id: 'torch', remove: true },
                { id: 'column', role: 'floor_feature', model: 'assets/models/column.obj' }
            ]
        }
    };
    const value = Adapter.resolveTileset(base, map);
    assert.strictEqual(value.texture, 'assets/tilesets/override.png');
    assert.deepStrictEqual(value.base.walls[0].middle, [2, 0]);
    assert.strictEqual(value.base.walls[0].weight, 100);
    assert.strictEqual(value.features.length, 1);
    assert.strictEqual(value.features[0].id, 'column');
    assert.strictEqual(base.features[0].id, 'torch', 'resolution must not mutate authored tileset data');
})();

(async function testProjectAdapterLoadsRegistryWithoutWritingAuthoredData() {
    const payload = { maps: [{ id: 1, layout: ['.'], events: [] }] };
    const fakeFetch = async url => {
        assert.strictEqual(url, '/api/tilesets');
        return {
            ok: true,
            json: async () => ({
                tilesets: [{
                    id: 'dungeon_default',
                    texture: 'assets/tilesets/dungeon.png',
                    tileWidth: 64,
                    tileHeight: 64,
                    base: { walls: [], floors: [], ceilings: [] },
                    doors: []
                }]
            })
        };
    };
    const scene = await Adapter.buildScene(payload, 0, fakeFetch);
    assert.strictEqual(scene.assets.texture, 'assets/tilesets/dungeon.png');
    assert.strictEqual(scene.assets.tilesetId, 'dungeon_default');
    console.log('Thestra Editor Scene tests OK');
})().catch(error => {
    console.error(error);
    process.exitCode = 1;
});
