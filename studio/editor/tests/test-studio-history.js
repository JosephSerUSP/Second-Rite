'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const History = require('../js/studio-history.js');

test('Studio history commits atomically and clears redo on new work', async () => {
    const states = [];
    const history = History.createHistory({ onChange: state => states.push(state) });
    const first = { kind: 'walk-profile', target: { mapId: 1 },
        before: { profile: [{ y: 0, z: 0 }] },
        after: { profile: [{ y: 1, z: 0 }] }, label: 'Move Walk Profile' };
    history.commit(first);
    assert.equal(history.snapshot().undoCount, 1);
    assert.equal(history.snapshot().redoCount, 0);

    const applied = [];
    await history.undo((entry, side) => { applied.push([entry, side]); return { ok: true }; });
    assert.equal(history.snapshot().undoCount, 0);
    assert.equal(history.snapshot().redoCount, 1);
    assert.equal(applied[0][1], 'before');

    history.commit({ ...first, label: 'New Move' });
    assert.equal(history.snapshot().redoCount, 0, 'new work must invalidate redo history');
    assert.equal(history.snapshot().undoLabel, 'New Move');
    assert.ok(states.length >= 3);
});

test('failed undo leaves history untouched', async () => {
    const history = History.createHistory();
    history.commit({ kind: 'walk-profile', target: { mapId: 1 },
        before: { profile: [] }, after: { profile: [{ y: 0, z: 0 }] } });
    const result = await history.undo(() => ({ ok: false }));
    assert.equal(result, null);
    assert.deepEqual(history.snapshot(), {
        undoCount: 1, redoCount: 0, undoLabel: 'walk-profile', redoLabel: null
    });
});

test('history shortcuts preserve native focused-input undo', () => {
    const event = (code, extra = {}) => ({
        code,
        target: { tagName: 'CANVAS' },
        ...extra
    });
    assert.equal(History.historyShortcut(event('KeyZ', { ctrlKey: true })), 'undo');
    assert.equal(History.historyShortcut(event('KeyZ', { ctrlKey: true, shiftKey: true })), 'redo');
    assert.equal(History.historyShortcut(event('KeyZ', { metaKey: true })), 'undo');
    assert.equal(History.historyShortcut({
        code: 'KeyZ', ctrlKey: true, target: { tagName: 'INPUT' }
    }), null);
    assert.equal(History.historyShortcut(event('KeyZ')), null);
});
