const test = require('node:test');
const assert = require('node:assert/strict');
const adapter = require('./js/second-rite-editor-adapter.js');

function compactFixture() {
    return {
        version: 1,
        materials: [{ id: 'material_001' }],
        surfaces: [{
            id: 'literal', name: 'literal', source: { kind: 'cell', surface: 'opening' },
            material: 'material_001', transportOrder: 2,
            positions: [1, 1, 0, 2, 1, 0, 1, 2, 0],
            uvs: [0, 0, 1, 0, 0, 1],
            normals: [0, 0, 1, 0, 0, 1, 0, 0, 1],
            colors: [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
        }],
        definitions: [{
            id: 'mesh_001',
            positions: [0, 0, 0, 1, 0, 0, 1, 1, 0, 0, 1, 0],
            uvs: [0, 0, 1, 0, 1, 1, 0, 1],
            normals: [0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1],
            colors: [
                1, 0, 0, 1,
                0, 1, 0, 1,
                0, 0, 1, 1,
                1, 1, 1, 1
            ],
            indices: [0, 1, 2, 0, 2, 3]
        }],
        placements: [
            {
                order: 1, id: 'identity', name: 'identity',
                source: { kind: 'cell', surface: 'floor' }, material: 'material_001',
                definition: 'mesh_001',
                transform: { translation: [10, 20, 0], matrix2d: [1, 0, 0, 1] }
            },
            {
                order: 3, id: 'rotated', name: 'rotated',
                source: { kind: 'cell', surface: 'opening', axis: 'y' }, material: 'material_001',
                definition: 'mesh_001',
                transform: { translation: [5, 6, 0], matrix2d: [0, -1, 1, 0] }
            }
        ],
        encoding: { kind: adapter.INSTANCE_TRANSPORT_KIND, lossless: true }
    };
}

test('mesh definition placements expand to the ordinary surface contract in original order', () => {
    const bundle = compactFixture();
    const decoded = adapter.decodeTransport(bundle);

    assert.equal(decoded, bundle);
    assert.deepEqual(decoded.surfaces.map(surface => surface.id), ['identity', 'literal', 'rotated']);
    assert.deepEqual(decoded.surfaces[0].positions, [
        10, 20, 0, 11, 20, 0, 11, 21, 0,
        10, 20, 0, 11, 21, 0, 10, 21, 0
    ]);
    assert.deepEqual(decoded.surfaces[2].positions, [
        5, 6, 0, 5, 7, 0, 4, 7, 0,
        5, 6, 0, 4, 7, 0, 4, 6, 0
    ]);
    assert.deepEqual(decoded.surfaces[2].normals, [
        0, 0, 1, 0, 0, 1, 0, 0, 1,
        0, 0, 1, 0, 0, 1, 0, 0, 1
    ]);
    assert.deepEqual(decoded.surfaces[0].uvs, [0, 0, 1, 0, 1, 1, 0, 0, 1, 1, 0, 1]);
    assert.deepEqual(decoded.surfaces[0].colors, [
        1, 0, 0, 1, 0, 1, 0, 1, 0, 0, 1, 1,
        1, 0, 0, 1, 0, 0, 1, 1, 1, 1, 1, 1
    ]);
    assert.equal(decoded.surfaces[0].source.surface, 'floor');
    assert.equal(decoded.surfaces[0].material, 'material_001');
    assert.equal('transportOrder' in decoded.surfaces[1], false);
    assert.equal('definitions' in decoded, false);
    assert.equal('placements' in decoded, false);
    assert.equal('encoding' in decoded, false);
});

test('ordinary float bundles pass through untouched', () => {
    const bundle = { version: 1, materials: [], surfaces: [] };
    assert.equal(adapter.decodeTransport(bundle), bundle);
});

test('instance decoder fails loud on an unknown runtime definition', () => {
    const bundle = compactFixture();
    bundle.placements[0].definition = 'missing';
    assert.throws(() => adapter.decodeTransport(bundle), /unknown definition 'missing'/);
});

test('instance decoder fails loud on invalid indices and transforms', () => {
    const badIndex = compactFixture();
    badIndex.definitions[0].indices[0] = 99;
    assert.throws(() => adapter.decodeTransport(badIndex), /out-of-range index 99/);

    const badTransform = compactFixture();
    badTransform.placements[0].transform.matrix2d = [1, 0, 0];
    assert.throws(() => adapter.decodeTransport(badTransform), /invalid transform/);
});
