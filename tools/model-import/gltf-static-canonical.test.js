'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');
const { Accessor, Document } = require('@gltf-transform/core');
const { canonicalNumber, gltfVectorToWorld, normalizeDocument } = require('./gltf-static-model');

test('cross-language neutral numbers canonicalize IEEE signed zero', () => {
    assert.equal(Object.is(canonicalNumber(-0), -0), false);
    assert.deepEqual(gltfVectorToWorld([0, 0, 0]), [0, 0, 0]);
    assert.equal(Object.is(gltfVectorToWorld([0, 0, 0])[1], -0), false);
});

test('normalized model rows and bounds contain no negative zero', () => {
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
            -0, 0,
            1, -0,
            0, 1,
        ]))
        .setBuffer(buffer);
    const normals = document.createAccessor('normals')
        .setType(Accessor.Type.VEC3)
        .setArray(new Float32Array([
            -0, 0, 1,
            0, -0, 1,
            0, 0, 1,
        ]))
        .setBuffer(buffer);
    const primitive = document.createPrimitive('triangle')
        .setAttribute('POSITION', positions)
        .setAttribute('TEXCOORD_0', uvs)
        .setAttribute('NORMAL', normals);
    const mesh = document.createMesh('mesh').addPrimitive(primitive);
    const node = document.createNode('node').setMesh(mesh);
    const scene = document.createScene('main').addChild(node);
    document.getRoot().setDefaultScene(scene);

    const bundle = normalizeDocument(document, {
        metersToMapCells: 1,
        sourcePath: 'signed-zero.glb',
    });
    const numbers = bundle.model.groups.flatMap(group => group.vertices.flat())
        .concat(Object.values(bundle.model.bounds));
    assert.equal(numbers.some(value => Object.is(value, -0)), false);
});
