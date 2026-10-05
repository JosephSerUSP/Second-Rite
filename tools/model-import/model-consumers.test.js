'use strict';
const assert = require('node:assert/strict');
const test = require('node:test');
const THREE = require('three');
const importer = require('./import-model');
const adapter = require('./model-bundle-three');
const contract = require('./model-contract');
const viewport = require('../../studio/editor/js/thestra-viewport-contract');
const roots = require('../semantic-roots');

test('compiled appearance is consumed through stable slots without a source-format parser', async () => {
    const bundle = await importer.importModel({ projectRoot: roots.DEFAULT_PROJECT_ROOT, modelId: 'system.placeholder_question' });
    for (const slot of bundle.materialSlots) slot.appearance = { color: [0.2,0.4,0.6,1] };
    const object = adapter.toThreeObject(bundle);
    assert.equal(object.userData.modelId, bundle.modelId);
    assert.deepEqual(object.children.map(mesh => mesh.material.name), bundle.geometry.groups.map(g => g.materialSlot));
    assert.deepEqual(object.children[0].material.color.toArray(), [0.2,0.4,0.6]);
    delete bundle.materialSlots[0].appearance;
    assert.throws(() => adapter.toThreeObject(bundle), /no compiled appearance/);
});

test('runtime instance transforms preserve Z, scale and orientation at the Three boundary', () => {
    const instance = { id: 'event:7', modelId: 'item.lantern', transform: {
        translation: [3,4,1], orientation: [0,-1,0,1,0,0,0,0,1], scale: 2,
    }, provenance: {kind:'event',id:7} };
    const matrix = new THREE.Matrix4().set(...viewport.runtimePlacementTransformToThestra({modelInstance:instance}));
    const runtimePosition = viewport.transformModelInstancePoint(instance,[1,2,3]);
    assert.deepEqual(runtimePosition, [-1,6,7]);
    const threePosition = new THREE.Vector3(...viewport.runtimeLocalPositionToThestra([1,2,3])).applyMatrix4(matrix);
    assert.deepEqual(threePosition.toArray(), viewport.runtimePositionToThestra(runtimePosition));
    assert.deepEqual(viewport.transformModelInstancePoint(instance,[1,0,0],true), [0,1,0]);
    const local = new THREE.Vector3(1,2,3).applyMatrix4(new THREE.Matrix4().set(...viewport.runtimeLocalModelTransformToThestra()));
    assert.deepEqual(local.toArray(), [1,3,2]);
});

test('compiled native binding rejects corrupt appearance rather than rendering a default', async () => {
    const bundle = await importer.importModel({ projectRoot: roots.DEFAULT_PROJECT_ROOT, modelId: 'system.placeholder_question' });
    bundle.materialSlots[0].appearance = {color:[1,1,Infinity,1]};
    assert.throws(() => contract.validateBundle(bundle), /finite RGBA/);
    bundle.materialSlots[0].appearance = {color:[1,1,1,1],texture:'assets/../bad.png'};
    assert.throws(() => contract.validateBundle(bundle), /Project-relative/);
});
