'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const Contract = require('../js/thestra-viewport-contract.js');
const ROOT = path.resolve(__dirname, '..', '..', '..');

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
    assert.strictEqual(Contract.cameraShortcut(key('Digit1'), true), 'front');
    assert.strictEqual(Contract.cameraShortcut({ code: '', key: '1', target: { tagName: 'CANVAS' } }, true), 'front');
    assert.strictEqual(Contract.cameraShortcut(key('Numpad1', { ctrlKey: true }), true), 'back');
    assert.strictEqual(Contract.cameraShortcut(key('Digit1', { ctrlKey: true }), true), 'back');
    assert.strictEqual(Contract.cameraShortcut(key('Numpad3'), true), 'right');
    assert.strictEqual(Contract.cameraShortcut(key('Digit3'), true), 'right');
    assert.strictEqual(Contract.cameraShortcut(key('Numpad3', { ctrlKey: true }), true), 'left');
    assert.strictEqual(Contract.cameraShortcut(key('Numpad7'), true), 'top');
    assert.strictEqual(Contract.cameraShortcut(key('Digit7'), true), 'top');
    assert.strictEqual(Contract.cameraShortcut(key('Numpad7', { ctrlKey: true }), true), 'bottom');
    assert.strictEqual(Contract.cameraShortcut(key('Numpad5'), true), 'toggle-projection');
    assert.strictEqual(Contract.cameraShortcut(key('Digit5'), true), 'toggle-projection');
    assert.strictEqual(Contract.cameraShortcut(key('Numpad2'), true), 'orbit-down');
    assert.strictEqual(Contract.cameraShortcut(key('Digit2'), true), 'orbit-down');
    assert.strictEqual(Contract.cameraShortcut(key('Numpad4'), true), 'orbit-left');
    assert.strictEqual(Contract.cameraShortcut(key('Digit4'), true), 'orbit-left');
    assert.strictEqual(Contract.cameraShortcut(key('Numpad6'), true), 'orbit-right');
    assert.strictEqual(Contract.cameraShortcut(key('Digit6'), true), 'orbit-right');
    assert.strictEqual(Contract.cameraShortcut(key('Numpad8'), true), 'orbit-up');
    assert.strictEqual(Contract.cameraShortcut(key('Digit8'), true), 'orbit-up');
    assert.strictEqual(Contract.cameraShortcut(key('Numpad9'), true), 'opposite-view');
    assert.strictEqual(Contract.cameraShortcut(key('Digit9'), true), 'opposite-view');
    assert.strictEqual(Contract.cameraShortcut(key('NumpadAdd'), true), 'zoom-in');
    assert.strictEqual(Contract.cameraShortcut(key('Equal'), true), 'zoom-in');
    assert.strictEqual(Contract.cameraShortcut({ code: '', key: '+', target: { tagName: 'CANVAS' } }, true), 'zoom-in');
    assert.strictEqual(Contract.cameraShortcut({ code: '', key: '=', target: { tagName: 'CANVAS' } }, true), 'zoom-in');
    assert.strictEqual(Contract.cameraShortcut(key('NumpadSubtract'), true), 'zoom-out');
    assert.strictEqual(Contract.cameraShortcut(key('Minus'), true), 'zoom-out');
    assert.strictEqual(Contract.cameraShortcut({ code: '', key: '-', target: { tagName: 'CANVAS' } }, true), 'zoom-out');
    assert.strictEqual(Contract.cameraShortcut(key('Home'), true), 'frame-all');
    assert.strictEqual(Contract.cameraShortcut(key('NumpadPeriod'), true), 'frame-selection');
    assert.strictEqual(Contract.cameraShortcut(key('NumpadDecimal'), true), 'frame-selection');
    assert.strictEqual(Contract.cameraShortcut(key('NumpadComma'), true), 'frame-selection');
    assert.strictEqual(Contract.cameraShortcut(key('Comma'), true), 'frame-selection');
    assert.strictEqual(Contract.cameraShortcut(key('Period'), true), 'frame-selection');
    assert.strictEqual(Contract.cameraShortcut({ code: '', key: ',', target: { tagName: 'CANVAS' } }, true), 'frame-selection');
    assert.strictEqual(Contract.cameraShortcut({ code: '', key: '.', target: { tagName: 'CANVAS' } }, true), 'frame-selection');
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

(function testProvisionalRegionCoversTheEditedCellAndItsFaceNeighbours() {
    // A wall face is attributed to the cell it faces, so an edit invalidates
    // the four orthogonal neighbours as well as the cell itself.
    assert.deepStrictEqual(
        Contract.provisionalRegion([{ x: 4, y: 7 }]).sort(),
        ['3:7', '4:6', '4:7', '4:8', '5:7'].sort()
    );
})();

(function testProvisionalRegionExcludesDiagonals() {
    const keys = Contract.provisionalRegion([{ x: 0, y: 0 }]);
    // Widening to diagonals would discard authoritative geometry that no face
    // attribution can have invalidated.
    ['1:1', '-1:-1', '1:-1', '-1:1'].forEach(diagonal => {
        assert.ok(!keys.includes(diagonal), `diagonal ${diagonal} must stay authoritative`);
    });
    assert.strictEqual(keys.length, 5);
})();

(function testProvisionalRegionDeduplicatesOverlappingEdits() {
    // Two adjacent edits share three cells between them; a region must not
    // report the same cell twice or the caller double-counts dirty geometry.
    const keys = Contract.provisionalRegion([{ x: 2, y: 2 }, { x: 3, y: 2 }]);
    assert.strictEqual(new Set(keys).size, keys.length, 'region must be a set');
    assert.strictEqual(keys.length, 8);
    assert.ok(keys.includes('2:2') && keys.includes('3:2'));
})();

(function testProvisionalRegionRejectsUnusableInput() {
    assert.deepStrictEqual(Contract.provisionalRegion(null), []);
    assert.deepStrictEqual(Contract.provisionalRegion([]), []);
    assert.deepStrictEqual(Contract.provisionalRegion([null, undefined]), []);
    assert.deepStrictEqual(Contract.provisionalRegion([{ x: 'a', y: 1 }]), [],
        'a non-numeric cell must not silently become NaN:1');
})();

(function testViewportUsesTheSharedRegionAndSettlesOnAnArrivingBundle() {
    const source = fs.readFileSync(
        path.join(ROOT, 'tools', 'editor', 'js', 'three-editor-viewport-base.js'), 'utf8'
    );
    assert.match(source, /Contract\.provisionalRegion\(cells\)/,
        'the viewport must use the shared region rule, not a second copy of it');
    assert.match(source, /provisionalCells\.clear\(\)/,
        'an arriving authoritative bundle must settle every provisional cell');
    assert.match(source, /const visible = !hasAuthoritativeBundle \|\| provisionalCells\.has\(key\)/,
        'proxies show without a bundle, and otherwise only where an edit outran the runtime');
    assert.doesNotMatch(source, /opacity: hasAuthoritativeBundle \? 0 : 0\.72/,
        'proxy visibility is per mesh now; a shared material cannot express one dirty cell');
    assert.match(source, /if \(shouldFrame\) provisionalCells\.clear\(\)/,
        'provisional cells are per map; carrying them across a switch blanks the next map');
})();

console.log('Thestra viewport contract tests OK');
