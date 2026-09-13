'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const Spatial = require('../js/spatial-interaction.js');

test('semantic authoring axes do not leak Three.js Y-up permutation', () => {
    assert.equal(Spatial.semanticAxisToViewport('X'), 'X');
    assert.equal(Spatial.semanticAxisToViewport('Y'), 'Z');
    assert.equal(Spatial.semanticAxisToViewport('Z'), 'Y');
    assert.equal(Spatial.viewportAxisToSemantic('Y'), 'Z');
    assert.deepEqual(Spatial.viewportAxisColorSources(), ['X', 'Z', 'Y']);
    assert.equal(Spatial.semanticAxisColor('Z'), 0x3d8cff,
        'authored elevation Z keeps Blender-like blue even though Three uses Y-up');
});

test('shared spatial state propagates selection and modal transform state', () => {
    const snapshots = [];
    const state = Spatial.createState(snapshot => snapshots.push(snapshot));
    const selection = { kind: 'walk-profile-point', key: 'walk-profile-point:2', index: 2 };

    state.setSelection(selection);
    assert.equal(state.snapshot().selection, selection);

    state.beginMove();
    assert.equal(state.snapshot().operation, 'move');

    state.constrain('Z');
    assert.equal(state.snapshot().constraint, 'Z');

    state.setValue(0.5);
    assert.equal(state.snapshot().value, 0.5);

    state.reject('profile-order');
    assert.match(state.snapshot().feedback, /adjacent profile point/i);

    state.constrain('Y');
    assert.equal(state.snapshot().feedback, null,
        'a valid constraint clears stale rejection feedback');

    state.cancel();
    assert.equal(state.snapshot().operation, null);
    assert.equal(state.snapshot().constraint, null);
    assert.equal(state.snapshot().value, null);
    assert.ok(snapshots.length >= 6);
});

test('Blender-style transform shortcuts are viewport-scoped and form-safe', () => {
    const key = (code, extra) => ({
        code,
        target: { tagName: 'CANVAS' },
        ...(extra || {})
    });

    assert.deepEqual(Spatial.transformShortcut(key('KeyG'), true, null),
        { kind: 'begin-move' });
    assert.deepEqual(Spatial.transformShortcut(key('KeyZ'), true, 'move'),
        { kind: 'constraint', axis: 'Z' });
    assert.deepEqual(Spatial.transformShortcut(key('Escape'), true, 'move'),
        { kind: 'cancel' });
    assert.deepEqual(Spatial.transformShortcut(key('Enter'), true, 'move'),
        { kind: 'confirm' });

    assert.equal(Spatial.transformShortcut(key('KeyG'), false, null), null);
    assert.equal(Spatial.transformShortcut({
        code: 'KeyG', target: { tagName: 'INPUT' }
    }, true, null), null);
    assert.equal(Spatial.transformShortcut(key('KeyG', { ctrlKey: true }), true, null), null);
});

test('spatial rejection reasons are author-facing instead of raw command codes', () => {
    assert.match(Spatial.reasonMessage('profile-order'), /Cannot move/i);
    assert.match(Spatial.reasonMessage('profile-endpoint'), /cannot be deleted/i);
    assert.match(Spatial.reasonMessage('profile-fixed-depth'), /authored Y or Z/i);
    assert.equal(Spatial.reasonMessage('future-reason'), 'future reason');
});
