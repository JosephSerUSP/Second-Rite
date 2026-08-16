'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const { Accessor, Document } = require('@gltf-transform/core');
const { normalizeDocument } = require('./gltf-static-model');
const { createThreeGeometryGroups, validateBundle } = require('./static-bundle-three');

const FIXTURE_PATH = path.join(__dirname, 'fixtures', 'static-equivalence.bundle.json');

function equivalentDocument() {
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

test('committed bundle fixture is the deterministic glTF normalizer output', () => {
    const committed = JSON.parse(fs.readFileSync(FIXTURE_PATH, 'utf8'));
    const normalized = normalizeDocument(equivalentDocument(), {
        metersToMapCells: 1,
        sourcePath: 'tools/model-import/fixtures/static-equivalence.glb',
    });
    assert.deepEqual(normalized, committed);
    assert.equal(validateBundle(committed), committed);
});

test('Three-side adapter consumes the same normalized rows without re-parsing source glTF', async () => {
    const THREE = await import('three');
    const bundle = JSON.parse(fs.readFileSync(FIXTURE_PATH, 'utf8'));
    const groups = createThreeGeometryGroups(bundle, THREE);

    assert.equal(groups.length, 1);
    assert.equal(groups[0].material, 'body');
    assert.equal(groups[0].geometry.userData.thestraMaterial, 'body');

    assert.deepEqual(Array.from(groups[0].geometry.getAttribute('position').array), [
        0, 0, 0,
        1, 0, 0,
        0, 0, 1,
    ]);
    assert.deepEqual(Array.from(groups[0].geometry.getAttribute('uv').array), [
        0, 0,
        1, 0,
        0, 1,
    ]);
    assert.deepEqual(Array.from(groups[0].geometry.getAttribute('normal').array), [
        0, -1, 0,
        0, -1, 0,
        0, -1, 0,
    ]);
    assert.deepEqual(Array.from(groups[0].geometry.getAttribute('color').array), [
        1, 1, 1, 1,
        1, 1, 1, 1,
        1, 1, 1, 1,
    ]);

    const box = groups[0].geometry.boundingBox;
    assert.ok(box);
    assert.deepEqual(box.min.toArray(), [0, 0, 0]);
    assert.deepEqual(box.max.toArray(), [1, 0, 1]);
});

test('Three-side adapter fails closed on malformed bundle rows', () => {
    const bundle = JSON.parse(fs.readFileSync(FIXTURE_PATH, 'utf8'));
    bundle.model.groups[0].vertices[0] = [0, 0, 0];
    assert.throws(() => validateBundle(bundle), /must have 12 floats/);
});
