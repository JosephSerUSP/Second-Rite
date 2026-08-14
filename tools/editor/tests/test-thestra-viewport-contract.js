'use strict';

const assert = require('assert');
const Contract = require('../js/thestra-viewport-contract.js');

(function testRuntimeFloorKeepsItsUpwardNormalAfterAxisConversion() {
    const positions = Contract.transformTriangleStream(
        [1, 1, 0, 2, 1, 0, 2, 2, 0], 3,
        value => Contract.runtimePositionToThestra(value, { runtimeGridOrigin: { x: 1, y: 1 } })
    );
    const normals = Contract.transformTriangleStream(
        [0, 0, 1, 0, 0, 1, 0, 0, 1], 3, Contract.runtimeNormalToThestra
    );
    assert.deepStrictEqual(positions, [0, 0, 0, 1, 0, 1, 1, 0, 0]);
    assert.deepStrictEqual(normals, [0, 1, 0, 0, 1, 0, 0, 1, 0]);

    const a = positions.slice(0, 3), b = positions.slice(3, 6), c = positions.slice(6, 9);
    const crossY = (b[2] - a[2]) * (c[0] - a[0]) - (b[0] - a[0]) * (c[2] - a[2]);
    assert.ok(crossY > 0, 'the converted triangle winding must agree with its upward normal');
})();

(function testAllVertexStreamsShareTheSameTrianglePermutation() {
    assert.deepStrictEqual(
        Contract.transformTriangleStream([0, 0, 1, 0, 1, 1], 2),
        [0, 0, 1, 1, 1, 0]
    );
    assert.deepStrictEqual(
        Contract.transformTriangleStream([1, 0, 0, 1, 0, 1, 0, 1, 1, 1, 1, 1], 4),
        [1, 0, 0, 1, 1, 1, 1, 1, 0, 1, 0, 1]
    );
})();

(function testEffectiveEventPresentationHasAnExplicitFallback() {
    assert.deepStrictEqual(Contract.eventVisualPlan({ model: 'assets/models/altar.obj', sprite: 'assets/sprites/altar.png' }),
        { kind: 'model', path: 'assets/models/altar.obj' });
    assert.deepStrictEqual(Contract.eventVisualPlan({ sprite: 'assets/sprites/altar.png' }),
        { kind: 'sprite', path: 'assets/sprites/altar.png' });
    assert.deepStrictEqual(Contract.eventVisualPlan({}), { kind: 'fallback', path: null });
})();

console.log('Thestra viewport contract tests OK');
