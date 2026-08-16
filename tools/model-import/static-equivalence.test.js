'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');
const { Accessor, Document } = require('@gltf-transform/core');
const { normalizeDocument } = require('./gltf-static-model');

const EXPECTED_MODEL = {
    groups: [{
        material: 'body',
        vertices: [
            [0, 0, 0, 0, 0, 0, -1, 0, 1, 1, 1, 1],
            [1, 0, 0, 1, 0, 0, -1, 0, 1, 1, 1, 1],
            [0, 0, 1, 0, 1, 0, -1, 0, 1, 1, 1, 1],
        ],
    }],
    vertexCount: 3,
    bounds: {
        minX: 0, minY: 0, minZ: 0,
        maxX: 1, maxY: 0, maxZ: 1,
    },
};

function equivalentGltfDocument() {
    const document = new Document();
    const buffer = document.createBuffer('buffer');
    const positions = document.createAccessor('positions')
        .setType(Accessor.Type.VEC3)
        .setArray(new Float32Array([
            0, 0, 0,
            1, 0, 0,
            0, 1, 0,
        ]))
        .setBuffer(buffer);
    const uvs = document.createAccessor('uvs')
        .setType(Accessor.Type.VEC2)
        .setArray(new Float32Array([
            0, 0,
            1, 0,
            0, 1,
        ]))
        .setBuffer(buffer);
    const normals = document.createAccessor('normals')
        .setType(Accessor.Type.VEC3)
        .setArray(new Float32Array([
            0, 0, 1,
            0, 0, 1,
            0, 0, 1,
        ]))
        .setBuffer(buffer);
    const material = document.createMaterial('body');
    const primitive = document.createPrimitive('triangle')
        .setAttribute('POSITION', positions)
        .setAttribute('TEXCOORD_0', uvs)
        .setAttribute('NORMAL', normals)
        .setMaterial(material);
    const mesh = document.createMesh('static-equivalence').addPrimitive(primitive);
    const node = document.createNode('static-equivalence').setMesh(mesh);
    const scene = document.createScene('main').addChild(node);
    document.getRoot().setDefaultScene(scene);
    return document;
}

test('equivalent glTF source normalizes to the established neutral static-model contract', () => {
    const bundle = normalizeDocument(equivalentGltfDocument(), {
        metersToMapCells: 1,
        sourcePath: 'tools/model-import/fixtures/static-equivalence.glb',
    });
    assert.deepEqual(bundle.model, EXPECTED_MODEL);
    assert.equal(bundle.model.groups[0].material, 'body');
    assert.ok(bundle.diagnostics.some(entry => entry.code === 'GLTF_PBR_METALLIC_ROUGHNESS_DEGRADED'));
});

module.exports = { EXPECTED_MODEL, equivalentGltfDocument };
