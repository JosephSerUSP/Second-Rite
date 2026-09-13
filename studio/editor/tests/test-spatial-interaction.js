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
    assert.match(Spatial.reasonMessage('profile-endpoint-required'), /endpoint/i);
    assert.match(Spatial.reasonMessage('invalid-subdivision-count'), /1 to 64/i);
    assert.equal(Spatial.reasonMessage('future-reason'), 'future reason');
});


test('projected semantic axis solver remains usable when the profile plane is edge-on', () => {
    assert.equal(Spatial.projectedAxisDelta(
        { x: 100, y: 100 },
        { x: 120, y: 110 },
        { x: 10, y: 5 }
    ), 2.0);

    assert.equal(Spatial.projectedAxisDelta(
        { x: 0, y: 0 },
        { x: 50, y: 50 },
        { x: 0.01, y: 0.01 }
    ), null, 'an axis projected nearly into the camera is explicitly unavailable');
});

test('committed spatial transactions preserve immutable before/after semantic values', () => {
    const selection = { kind: 'walk-profile-point', key: 'walk-profile-point:2', index: 2 };
    const before = { Y: 1, Z: 0.5 };
    const after = { Y: 2, Z: 1.25 };
    const transaction = Spatial.createTransaction('move', selection, before, after);

    assert.deepEqual(transaction, {
        kind: 'move',
        target: selection,
        before,
        after
    });
    assert.equal(Object.isFrozen(transaction), true);

    selection.index = 99;
    before.Y = -100;
    after.Z = -100;
    assert.equal(transaction.target.index, 2);
    assert.equal(transaction.before.Y, 1);
    assert.equal(transaction.after.Z, 1.25);
});


test('spatial selection state tracks active component inside a selected set', () => {
    const state = Spatial.createState();
    const a = { kind: 'walk-profile-point', key: 'walk-profile-point:1', index: 1 };
    const b = { kind: 'walk-profile-point', key: 'walk-profile-point:2', index: 2 };

    state.setSelection(a);
    let snapshot = state.toggleSelection(b);
    assert.deepEqual(snapshot.selectionSet.map(item => item.key), [a.key, b.key]);
    assert.equal(snapshot.selection.key, b.key);

    snapshot = state.toggleSelection(b);
    assert.deepEqual(snapshot.selectionSet.map(item => item.key), [a.key]);
    assert.equal(snapshot.selection.key, a.key);

    snapshot = state.setSelectionSet([a, b, a], a);
    assert.deepEqual(snapshot.selectionSet.map(item => item.key), [a.key, b.key],
        'selection sets deduplicate by semantic key');
    assert.equal(snapshot.selection.key, a.key);
});
