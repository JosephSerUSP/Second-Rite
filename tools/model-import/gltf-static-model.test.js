'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');
const { Accessor, Document, NodeIO } = require('@gltf-transform/core');
const {
    gltfVectorToWorld,
    hashBundle,
    normalizeDocument,
    normalizeFile,
    serializeBundle,
} = require('./gltf-static-model');

const ONE_PIXEL_PNG = Buffer.from(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=',
    'base64'
);

function nearly(actual, expected, epsilon = 1e-6) {
    assert.equal(actual.length, expected.length);
    actual.forEach((value, index) => {
        assert.ok(Math.abs(value - expected[index]) <= epsilon,
            `component ${index}: expected ${expected[index]}, got ${value}`);
    });
}

function makeAccessor(document, buffer, name, type, array, normalized = false) {
    return document.createAccessor(name)
        .setType(type)
        .setArray(array)
        .setNormalized(normalized)
        .setBuffer(buffer);
}

function makeStaticFixture(options = {}) {
    const document = new Document();
    const buffer = document.createBuffer('fixture-buffer');

    const positions = makeAccessor(document, buffer, 'positions', Accessor.Type.VEC3,
        new Float32Array([
            0, 0, 0,
            1, 0, 0,
            0, 1, 0,
        ]));
    const uvs = makeAccessor(document, buffer, 'uvs', Accessor.Type.VEC2,
        new Float32Array([
            0, 0,
            1, 0,
            0, 1,
        ]));
    const colors = makeAccessor(document, buffer, 'colors', Accessor.Type.VEC3,
        new Float32Array([
            1, 0, 0,
            0, 1, 0,
            0, 0, 1,
        ]));
    const indices = makeAccessor(document, buffer, 'indices', Accessor.Type.SCALAR,
        new Uint16Array([0, 1, 2]));

    const primitive = document.createPrimitive('triangle')
        .setAttribute('POSITION', positions)
        .setAttribute('TEXCOORD_0', uvs)
        .setAttribute('COLOR_0', colors)
        .setIndices(indices);

    if (options.withNormals !== false) {
        const normals = makeAccessor(document, buffer, 'normals', Accessor.Type.VEC3,
            new Float32Array([
                0, 0, 1,
                0, 0, 1,
                0, 0, 1,
            ]));
        primitive.setAttribute('NORMAL', normals);
    }

    const texture = document.createTexture('albedo-1px')
        .setImage(new Uint8Array(ONE_PIXEL_PNG))
        .setMimeType('image/png');
    const material = document.createMaterial('body')
        .setBaseColorFactor([0.25, 0.5, 0.75, 1])
        .setBaseColorTexture(texture)
        .setEmissiveFactor([0.1, 0.2, 0.3])
        .setMetallicFactor(0.2)
        .setRoughnessFactor(0.4);
    primitive.setMaterial(material);

    const mesh = document.createMesh('fixture-mesh').addPrimitive(primitive);
    const child = document.createNode('mesh-node')
        .setMesh(mesh)
        .setTranslation([1, 2, 3])
        .setScale(options.mirrored ? [-2, 3, 4] : [2, 3, 4]);
    const parent = document.createNode('parent-node')
        .setTranslation([10, 0, 0])
        .addChild(child);
    const scene = document.createScene('main').addChild(parent);
    document.getRoot().setDefaultScene(scene);

    return { document, material, primitive, scene };
}

test('basis conversion mirrors the established Y-up source -> Z-up Thestra contract', () => {
    assert.deepEqual(gltfVectorToWorld([1, 2, 3]), [1, -3, 2]);
    assert.deepEqual(gltfVectorToWorld([1, 2, 3], 2), [2, -6, 4]);
});

test('static document normalization bakes hierarchy, non-uniform scale, UVs, colors, normals and material facts', () => {
    const { document } = makeStaticFixture();
    const bundle = normalizeDocument(document, {
        metersToMapCells: 2,
        sourcePath: 'assets/models/Árvore fixture.glb',
    });

    assert.equal(bundle.kind, 'thestra-static-model-spike');
    assert.equal(bundle.version, 0);
    assert.deepEqual(bundle.source, {
        kind: 'gltf',
        path: 'assets/models/Árvore fixture.glb',
        sha256: null,
    });
    assert.deepEqual(bundle.normalization, {
        sourceUp: 'y',
        targetUp: 'z',
        metersToMapCells: 2,
        uvOrigin: 'upper-left',
    });

    assert.equal(bundle.model.vertexCount, 3);
    assert.equal(bundle.model.groups.length, 1);
    assert.equal(bundle.model.groups[0].material, 'body');
    const vertices = bundle.model.groups[0].vertices;

    // parent + child translation and child scale are baked before the basis
    // conversion. glTF UVs already use an upper-left origin and are not flipped.
    nearly(vertices[0].slice(0, 3), [22, -6, 4]);
    nearly(vertices[1].slice(0, 3), [26, -6, 4]);
    nearly(vertices[2].slice(0, 3), [22, -6, 10]);
    nearly(vertices[0].slice(3, 5), [0, 0]);
    nearly(vertices[1].slice(3, 5), [1, 0]);
    nearly(vertices[2].slice(3, 5), [0, 1]);
    vertices.forEach(vertex => nearly(vertex.slice(5, 8), [0, -1, 0]));
    nearly(vertices[0].slice(8, 12), [1, 0, 0, 1]);
    nearly(vertices[1].slice(8, 12), [0, 1, 0, 1]);
    nearly(vertices[2].slice(8, 12), [0, 0, 1, 1]);

    assert.deepEqual(bundle.model.bounds, {
        minX: 22, minY: -6, minZ: 4,
        maxX: 26, maxY: -6, maxZ: 10,
    });

    assert.equal(bundle.materials.length, 1);
    const material = bundle.materials[0];
    assert.equal(material.id, 'body');
    assert.equal(material.sourceName, 'body');
    nearly(material.baseColorFactor, [0.25, 0.5, 0.75, 1]);
    nearly(material.emissiveFactor, [0.1, 0.2, 0.3]);
    assert.equal(material.baseColorTexture.name, 'albedo-1px');
    assert.equal(material.baseColorTexture.mimeType, 'image/png');
    assert.ok(material.baseColorTexture.byteLength > 0);
    assert.match(material.baseColorTexture.sha256, /^[0-9a-f]{64}$/);

    const pbr = bundle.diagnostics.find(entry => entry.code === 'GLTF_PBR_METALLIC_ROUGHNESS_DEGRADED');
    assert.ok(pbr, 'PBR semantic loss must be explicit rather than silent');
    assert.equal(pbr.material, 'body');
    assert.equal(pbr.detail.metallicFactor, 0.2);
    assert.equal(pbr.detail.roughnessFactor, 0.4);
});

test('missing vertex normals use transformed Thestra-space flat face normals', () => {
    const { document } = makeStaticFixture({ withNormals: false });
    const bundle = normalizeDocument(document, {
        metersToMapCells: 1,
        sourcePath: 'fixture.glb',
    });
    for (const vertex of bundle.model.groups[0].vertices) {
        nearly(vertex.slice(5, 8), [0, -1, 0]);
    }
});

test('GLB file normalization is deterministic and provenance never needs an absolute local path', async () => {
    const { document } = makeStaticFixture();
    const io = new NodeIO();
    const glb = await io.writeBinary(document);
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'thestra-gltf-spike-'));
    const filePath = path.join(dir, 'fixture with spaces.glb');
    try {
        fs.writeFileSync(filePath, Buffer.from(glb));
        const options = {
            metersToMapCells: 1,
            sourcePath: 'assets/models/fixtures/águas fixture.glb',
        };
        const first = await normalizeFile(filePath, options);
        const second = await normalizeFile(filePath, options);

        assert.equal(first.source.path, options.sourcePath);
        assert.equal(first.source.path.includes(dir), false);
        assert.match(first.source.sha256, /^[0-9a-f]{64}$/);
        assert.equal(serializeBundle(first), serializeBundle(second));
        assert.equal(hashBundle(first), hashBundle(second));
        assert.match(hashBundle(first), /^[0-9a-f]{64}$/);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('static spike refuses semantic cases whose production policy is not decided', () => {
    const animated = makeStaticFixture().document;
    animated.createAnimation('idle');
    assert.throws(() => normalizeDocument(animated, {
        metersToMapCells: 1,
        sourcePath: 'animated.glb',
    }), /does not accept animation/);

    const mirrored = makeStaticFixture({ mirrored: true }).document;
    assert.throws(() => normalizeDocument(mirrored, {
        metersToMapCells: 1,
        sourcePath: 'mirrored.glb',
    }), /mirrored transform/);

    const ambiguous = new Document();
    ambiguous.createScene('one');
    ambiguous.createScene('two');
    assert.throws(() => normalizeDocument(ambiguous, {
        metersToMapCells: 1,
        sourcePath: 'ambiguous.glb',
    }), /multiple scenes but no default scene/);

    const { document: unscaled } = makeStaticFixture();
    assert.throws(() => normalizeDocument(unscaled, {
        sourcePath: 'requires-scale.glb',
    }), /metersToMapCells must be a finite positive number/);
});
