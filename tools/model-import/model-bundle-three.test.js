'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');
const semanticRoots = require('../semantic-roots');
const importer = require('./import-model');
const threeBundle = require('./model-bundle-three');

const PROJECT_ROOT = semanticRoots.DEFAULT_PROJECT_ROOT;

test('Three consumes the same compiled Model Bundle without source OBJ/glTF parsing', async () => {
    const bundle = await importer.importModel({
        projectRoot: PROJECT_ROOT,
        modelId: 'system.placeholder_question',
    });
    const groups = threeBundle.toThreeGeometryGroups(bundle);
    assert.ok(groups.length > 0);

    let count = 0;
    for (const entry of groups) {
        const geometry = entry.geometry;
        assert.equal(geometry.userData.materialSlot, entry.materialSlot);
        assert.ok(geometry.getAttribute('position'));
        assert.ok(geometry.getAttribute('uv'));
        assert.ok(geometry.getAttribute('normal'));
        assert.ok(geometry.getAttribute('color'));
        assert.equal(geometry.getAttribute('position').count, geometry.getAttribute('uv').count);
        assert.equal(geometry.getAttribute('position').count, geometry.getAttribute('normal').count);
        assert.equal(geometry.getAttribute('position').count, geometry.getAttribute('color').count);
        count += geometry.getAttribute('position').count;
    }
    assert.equal(count, bundle.geometry.vertexCount);
});

test('Three adapter carries semantic material slots but creates no source-format material graph', () => {
    const bundle = {
        kind: 'thestra-model-bundle',
        version: 1,
        modelId: 'fixture.surface-slot',
        compiler: { id: 'thestra-model-import', version: 1 },
        source: { kind: 'gltf', path: 'assets/models/source.glb', sha256: '0'.repeat(64) },
        normalization: { up: 'z', unit: 'mapCell', sourceUnitsToMapCells: 1 },
        geometry: {
            groups: [{
                materialSlot: 'dress',
                vertices: [
                    [0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1],
                    [1, 0, 0, 1, 0, 0, 0, 1, 1, 1, 1, 1],
                    [0, 1, 0, 0, 1, 0, 0, 1, 1, 1, 1, 1],
                ],
            }],
            vertexCount: 3,
            bounds: { minX: 0, minY: 0, minZ: 0, maxX: 1, maxY: 1, maxZ: 0 },
        },
        materialSlots: [{ id: 'dress', surface: 'agnes_dress' }],
        provenance: { recipeSha256: '1'.repeat(64) },
        diagnostics: [],
    };
    const [entry] = threeBundle.toThreeGeometryGroups(bundle);
    assert.equal(entry.materialSlot, 'dress');
    assert.equal(entry.geometry.userData.materialSlot, 'dress');
    assert.equal(entry.geometry.material, undefined,
        'bundle adapter must not invent a Three/PBR material; Surface realization is downstream');
});
