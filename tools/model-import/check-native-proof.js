'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const THREE = require('three');
const adapter = require('./model-bundle-three');
const viewport = require('../../studio/editor/js/thestra-viewport-contract');
const root = path.resolve(process.argv[2]);
const bundle = JSON.parse(fs.readFileSync(path.join(root, 'bundle.json')));
const object = adapter.toThreeObject(bundle);
assert.equal(object.userData.modelId, 'item.lantern');
const facts = JSON.parse(fs.readFileSync(path.join(root, 'instances.json')));
for (const fact of facts) {
    assert.deepEqual(viewport.transformModelInstancePoint(fact.instance, fact.point), fact.world);
    const matrix = new THREE.Matrix4().set(...viewport.runtimePlacementTransformToThestra({modelInstance:fact.instance}));
    const position = new THREE.Vector3(...viewport.runtimeLocalPositionToThestra(fact.point)).applyMatrix4(matrix);
    assert.deepEqual(position.toArray(), viewport.runtimePositionToThestra(fact.world));
}
console.log(`MODEL NATIVE/THREE FACT PARITY OK instances=${facts.length} groups=${object.children.length}`);
