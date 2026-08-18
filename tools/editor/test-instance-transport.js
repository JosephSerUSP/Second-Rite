const test = require('node:test');
const assert = require('node:assert/strict');
const adapter = require('./js/second-rite-editor-adapter.js');
const Direct = require('./js/three-definition-consumer.js');
const THREE = require('three');

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


test('direct consumer keeps compact topology and owns colour per placement only', () => {
    const bundle = compactFixture();
    adapter.applyRenderableModulation(bundle, []);

    assert.equal(bundle.encoding.kind, adapter.INSTANCE_TRANSPORT_KIND);
    assert.equal(bundle.definitions.length, 1);
    assert.equal(bundle.placements.length, 2);
    assert.equal(bundle.surfaces.length, 1, 'literal surfaces remain literal; placements were not compatibility-expanded');
    assert.equal('positions' in bundle.placements[0], false, 'placement never grows an expanded spatial stream');

    const first = adapter.directPlacementColorState(bundle.placements[0]);
    const second = adapter.directPlacementColorState(bundle.placements[1]);
    assert.ok(first && second);
    assert.notStrictEqual(first.authoritative, second.authoritative);
    assert.notStrictEqual(first.unlit, second.unlit);
    assert.ok(second.authoritative[0] < first.authoritative[0],
        'placement-dependent orientation tint remains placement-owned');

    const spatial = Direct.definitionGeometry(THREE, bundle.definitions[0]);
    const firstGeometry = Direct.placementGeometry(THREE, spatial, first);
    const secondGeometry = Direct.placementGeometry(THREE, spatial, second);
    assert.strictEqual(firstGeometry.getAttribute('position'), secondGeometry.getAttribute('position'));
    assert.strictEqual(firstGeometry.getAttribute('normal'), secondGeometry.getAttribute('normal'));
    assert.strictEqual(firstGeometry.getAttribute('uv'), secondGeometry.getAttribute('uv'));
    assert.strictEqual(firstGeometry.index, secondGeometry.index);
    assert.notStrictEqual(firstGeometry.getAttribute('color'), secondGeometry.getAttribute('color'));
    assert.notStrictEqual(firstGeometry.getAttribute('color').array, secondGeometry.getAttribute('color').array);

    const peerBefore = secondGeometry.getAttribute('color').array.slice();
    firstGeometry.getAttribute('color').array[0] = 0.123;
    assert.deepEqual(Array.from(secondGeometry.getAttribute('color').array), Array.from(peerBefore),
        'mutating one placement RGB buffer must not leak into a peer sharing spatial attributes');

    const mesh = new THREE.Mesh(firstGeometry, new THREE.MeshBasicMaterial({ vertexColors: true, side: THREE.DoubleSide }));
    mesh.matrixAutoUpdate = false;
    mesh.matrix.copy(Direct.placementMatrix(THREE, bundle.placements[0], {}));
    mesh.matrixWorld.copy(mesh.matrix);
    const hit = Direct.raycastFirstTriangle(THREE, mesh);
    assert.ok(hit, 'ordinary THREE.Mesh remains raycastable');
    assert.ok(Math.abs(hit.distance - 0.1) < 1e-6);
});

test('direct geometry matches the compatibility path triangle-for-triangle', () => {
    const directBundle = compactFixture();
    adapter.applyRenderableModulation(directBundle, []);
    const control = compactFixture();
    adapter.decodeTransport(control);
    adapter.applyVertexModulation(control, []);

    const definition = directBundle.definitions[0];
    const placement = directBundle.placements[0];
    const spatial = Direct.definitionGeometry(THREE, definition);
    const geometry = Direct.placementGeometry(
        THREE, spatial, adapter.directPlacementColorState(placement)
    );
    const mesh = new THREE.Mesh(geometry, new THREE.MeshBasicMaterial({ vertexColors: true }));
    mesh.matrixAutoUpdate = false;
    mesh.matrix.copy(Direct.placementMatrix(THREE, placement, {}));
    mesh.matrixWorld.copy(mesh.matrix);

    const expectedSurface = control.surfaces[0];
    const Contract = require('./js/thestra-viewport-contract.js');
    const expectedPositions = Contract.transformTriangleStream(
        expectedSurface.positions, 3, value => Contract.runtimePositionToThestra(value, {})
    );
    const expectedUvs = Contract.transformTriangleStream(expectedSurface.uvs, 2);
    const expectedColors = Contract.transformTriangleStream(expectedSurface.colors, 4);
    const index = geometry.index;
    const position = geometry.getAttribute('position');
    const uv = geometry.getAttribute('uv');
    const color = geometry.getAttribute('color');
    const world = new THREE.Vector3();
    for (let out = 0; out < index.count; out++) {
        const source = index.getX(out);
        world.fromBufferAttribute(position, source).applyMatrix4(mesh.matrixWorld);
        const p = out * 3, u = out * 2, c = out * 4;
        assert.ok(Math.abs(world.x - expectedPositions[p]) < 1e-6);
        assert.ok(Math.abs(world.y - expectedPositions[p + 1]) < 1e-6);
        assert.ok(Math.abs(world.z - expectedPositions[p + 2]) < 1e-6);
        assert.ok(Math.abs(uv.getX(source) - expectedUvs[u]) < 1e-6);
        assert.ok(Math.abs(uv.getY(source) - expectedUvs[u + 1]) < 1e-6);
        assert.ok(Math.abs(color.getX(source) - expectedColors[c]) < 1e-6);
        assert.ok(Math.abs(color.getY(source) - expectedColors[c + 1]) < 1e-6);
        assert.ok(Math.abs(color.getZ(source) - expectedColors[c + 2]) < 1e-6);
    }
    assert.equal(placement.material, expectedSurface.material);
    assert.deepEqual(placement.source, expectedSurface.source);
});
