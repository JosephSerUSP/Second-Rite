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

(function testAuthoredCellCentersAreDistinctFromIntegerWorldGrid() {
    assert.strictEqual(Contract.cellCenter(2.01), 2.5);
    assert.strictEqual(Contract.cellCenter(2.99), 2.5);
    assert.strictEqual(Contract.cellCoordinate(2.5), 2);
    assert.strictEqual(Contract.cellCoordinate(3.5), 3);
})();

(function testBlenderCameraShortcutPolicyProtectsFormsAndMatchesNumpadViews() {
    const key = (code, extra) => ({ code, key: '', target: { tagName: 'CANVAS' }, ...(extra || {}) });

    assert.strictEqual(Contract.cameraShortcut(key('Numpad1'), true), 'front');
    assert.strictEqual(Contract.cameraShortcut(key('Numpad1', { ctrlKey: true }), true), 'back');
    assert.strictEqual(Contract.cameraShortcut(key('Numpad3'), true), 'right');
    assert.strictEqual(Contract.cameraShortcut(key('Numpad3', { ctrlKey: true }), true), 'left');
    assert.strictEqual(Contract.cameraShortcut(key('Numpad7'), true), 'top');
    assert.strictEqual(Contract.cameraShortcut(key('Numpad7', { ctrlKey: true }), true), 'bottom');
    assert.strictEqual(Contract.cameraShortcut(key('Numpad5'), true), 'toggle-projection');
    assert.strictEqual(Contract.cameraShortcut(key('Numpad2'), true), 'orbit-down');
    assert.strictEqual(Contract.cameraShortcut(key('Numpad4'), true), 'orbit-left');
    assert.strictEqual(Contract.cameraShortcut(key('Numpad6'), true), 'orbit-right');
    assert.strictEqual(Contract.cameraShortcut(key('Numpad8'), true), 'orbit-up');
    assert.strictEqual(Contract.cameraShortcut(key('Numpad9'), true), 'opposite-view');
    assert.strictEqual(Contract.cameraShortcut(key('Home'), true), 'frame-all');
    assert.strictEqual(Contract.cameraShortcut(key('NumpadPeriod'), true), 'frame-selection');
    assert.strictEqual(Contract.cameraShortcut(key('Escape'), true), 'cancel-navigation');

    assert.strictEqual(Contract.cameraShortcut(key('Home', { target: { tagName: 'INPUT' } }), true), null);
    assert.strictEqual(Contract.cameraShortcut(key('Home', { ctrlKey: true }), true), null,
        'Ctrl remains reserved except for Blender opposite axis-view shortcuts');
    assert.strictEqual(Contract.cameraShortcut(key('Home'), false), null);
})();

(function testBlenderAxisVocabularyIsYUpAndHasExplicitOpposites() {
    assert.deepStrictEqual(Contract.axisViewSpec('front'), { direction: [0, 0, 1], up: [0, 1, 0] });
    assert.deepStrictEqual(Contract.axisViewSpec('right'), { direction: [1, 0, 0], up: [0, 1, 0] });
    assert.deepStrictEqual(Contract.axisViewSpec('top'), { direction: [0, 1, 0], up: [0, 0, -1] });
    assert.deepStrictEqual(Contract.axisViewSpec('bottom'), { direction: [0, -1, 0], up: [0, 0, 1] });
    assert.strictEqual(Contract.oppositeOrientation('front'), 'back');
    assert.strictEqual(Contract.oppositeOrientation('right'), 'left');
    assert.strictEqual(Contract.oppositeOrientation('top'), 'bottom');
    assert.strictEqual(Contract.oppositeOrientation('user'), 'user');
    assert.strictEqual(Contract.ORBIT_STEP_DEGREES, 15);
    assert.throws(() => Contract.axisViewSpec('perspective'), /Unsupported axis view/,
        'projection must never masquerade as an orientation');
})();

console.log('Thestra viewport contract tests OK');
