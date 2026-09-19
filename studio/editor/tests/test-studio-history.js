'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const History = require('../js/studio-history.js');

function record(kind, before, after, authority = 'maps:walk-profile:26') {
    return {
        kind,
        authority,
        target: { kind: 'walk-profile', key: authority },
        before,
        after,
    };
}

test('Studio history reverses and reapplies exact move and topology snapshots', () => {
    let authority = 'maps:walk-profile:26';
    let authored = [{ y: 0, z: 0 }, { y: 3, z: 0 }];
    const history = History.create({
        getAuthority: () => authority,
        apply(entry, direction) {
            authored = History.clone(direction === 'undo' ? entry.before.groundProfile : entry.after.groundProfile);
            return true;
        }
    });
    const moved = record('move',
        { hasGroundProfile: true, groundProfile: authored },
        { hasGroundProfile: true, groundProfile: [{ y: 0, z: 0 }, { y: 3, z: 1 }] });
    authored = History.clone(moved.after.groundProfile);
    assert.equal(history.commit(moved), true);

    const subdivided = record('subdivide',
        { hasGroundProfile: true, groundProfile: authored },
        { hasGroundProfile: true, groundProfile: [{ y: 0, z: 0 }, { y: 1.5, z: 0.5 }, { y: 3, z: 1 }] });
    authored = History.clone(subdivided.after.groundProfile);
    assert.equal(history.commit(subdivided), true);

    assert.equal(history.undo(), true);
    assert.deepEqual(authored, moved.after.groundProfile, 'topology undo restores the precise prior JSON');
    assert.equal(history.undo(), true);
    assert.deepEqual(authored, moved.before.groundProfile, 'move undo restores the precise prior JSON');
    assert.equal(history.redo(), true);
    assert.equal(history.redo(), true);
    assert.deepEqual(authored, subdivided.after.groundProfile, 'redo reapplies exact topology JSON');
});

test('rejected/canceled operations and focused form shortcuts do not affect history', () => {
    let applied = 0;
    const history = History.create({
        getAuthority: () => 'maps:walk-profile:26',
        apply() { applied += 1; return true; }
    });
    assert.equal(history.commit({ authority: 'maps:walk-profile:26' }), false,
        'a rejected/canceled operation has no complete before/after transaction to commit');
    assert.equal(history.snapshot().undo.length, 0);
    const inputEvent = {
        code: 'KeyZ', ctrlKey: true, target: { tagName: 'INPUT' },
        preventDefault() { throw new Error('form shortcut must not be stolen'); }
    };
    assert.equal(history.handleKeydown(inputEvent), false);
    assert.equal(applied, 0);
});

test('history rejects stale records after the active authored authority changes', () => {
    let authority = 'maps:walk-profile:26';
    let applied = 0;
    const history = History.create({
        getAuthority: () => authority,
        apply() { applied += 1; return true; }
    });
    assert.equal(history.commit(record('move', { value: 1 }, { value: 2 })), true);
    authority = 'maps:walk-profile:27';
    assert.equal(history.undo(), false);
    assert.equal(applied, 0, 'a stale record is never replayed into another map');
    assert.deepEqual(history.snapshot(), { undo: [], redo: [] });
});

test('Ctrl-Z and Ctrl-Shift-Z consume only successful Studio history shortcuts', () => {
    let value = 2;
    let prevented = 0;
    const history = History.create({
        getAuthority: () => 'maps:walk-profile:26',
        apply(entry, direction) { value = direction === 'undo' ? entry.before.value : entry.after.value; return true; }
    });
    history.commit(record('move', { value: 1 }, { value: 2 }));
    const event = shiftKey => ({
        code: 'KeyZ', ctrlKey: true, shiftKey, target: { tagName: 'CANVAS' },
        preventDefault() { prevented += 1; }
    });
    assert.equal(history.handleKeydown(event(false)), true);
    assert.equal(value, 1);
    assert.equal(history.handleKeydown(event(true)), true);
    assert.equal(value, 2);
    assert.equal(prevented, 2);
});

test('one property commit restores an exact map snapshot without renderer state', () => {
    let map = { id: 26, title: 'Port', lightObjects: [{ x: 1, y: 2 }] };
    const history = History.create({
        getAuthority: () => 'maps:26',
        apply(entry, direction) {
            map = History.clone((direction === 'undo' ? entry.before : entry.after).map);
            return true;
        }
    });
    const before = History.clone(map);
    map.title = 'Port at Dusk';
    map.lightObjects[0].x = 3;
    assert.equal(history.commit({
        kind: 'property', authority: 'maps:26', target: { kind: 'map', key: 'maps:26' },
        before: { map: before }, after: { map: History.clone(map) }
    }), true);
    assert.equal(history.undo(), true);
    assert.deepEqual(map, before, 'undo restores the complete authored map value');
    assert.equal(history.redo(), true);
    assert.equal(map.title, 'Port at Dusk');
    assert.equal(map.lightObjects[0].x, 3);
});
