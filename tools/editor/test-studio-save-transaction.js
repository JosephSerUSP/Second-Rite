'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, 'js', 'net.js'), 'utf8');

function makeContext(payload) {
    const noop = () => {};
    const context = {
        console,
        JSON,
        Object,
        Array,
        Promise,
        setTimeout,
        confirm: () => false,
        API_URL: '',
        isDirty: false,
        dbPayload: structuredClone(payload),
        document: {
            addEventListener: noop,
            querySelector: () => null,
            getElementById: () => ({
                textContent: '',
                classList: { add: noop, remove: noop },
                disabled: false,
            }),
        },
        window: {
            addEventListener: noop,
            dbModalSnapshotHelper: null,
        },
        fetch: async () => { throw new Error('unexpected fetch'); },
        setDirty: noop,
        initMapEditor: noop,
        initDatabaseEditor: noop,
        initSystemTab: noop,
    };
    vm.createContext(context);
    vm.runInContext(source, context, { filename: 'net.js' });
    return context;
}

function plain(value) {
    return JSON.parse(JSON.stringify(value));
}

test('save payload contains only resources that diverged from this renderer baseline', () => {
    const context = makeContext({
        maps: [{ id: 'map-a' }],
        units: [{ id: 'unit-a' }],
        _fileVersions: { maps: 'm1', units: 'u1' },
    });
    context.captureDbSaveBaseline();

    context.dbPayload.units[0].id = 'unit-edited';
    const changed = plain(context.changedDbResourceNames());
    const payload = plain(context.buildDbSavePayload(changed));

    assert.deepEqual(changed, ['units']);
    assert.deepEqual(payload, {
        _fileVersions: { units: 'u1' },
        units: [{ id: 'unit-edited' }],
    });
});

test('an unrelated newer resource token is not adopted after a scoped save', () => {
    const context = makeContext({
        maps: [{ id: 'map-a' }],
        units: [{ id: 'unit-a' }],
        _fileVersions: { maps: 'm1', units: 'u1' },
    });
    context.captureDbSaveBaseline();
    context.dbPayload.units[0].id = 'unit-edited';
    const payload = context.buildDbSavePayload(['units']);

    const remaining = plain(context.acceptDbSaveResult(payload, {
        versions: { maps: 'm2-from-another-renderer', units: 'u2' },
    }));

    assert.equal(context.dbPayload._fileVersions.units, 'u2');
    assert.equal(context.dbPayload._fileVersions.maps, 'm1');
    assert.deepEqual(remaining, []);
});

test('an edit made while save is in flight remains dirty after accepting the sent revision', () => {
    const context = makeContext({
        units: [{ id: 'unit-a', hp: 10 }],
        _fileVersions: { units: 'u1' },
    });
    context.captureDbSaveBaseline();
    context.dbPayload.units[0].hp = 20;
    const payload = context.buildDbSavePayload(['units']);

    // User keeps typing after the request body was captured.
    context.dbPayload.units[0].hp = 30;
    const remaining = plain(context.acceptDbSaveResult(payload, {
        versions: { units: 'u2' },
    }));

    assert.deepEqual(remaining, ['units']);
    assert.equal(context.dbPayload.units[0].hp, 30);
    assert.equal(payload.units[0].hp, 20);
});

test('transport metadata never becomes an authored resource transaction', () => {
    const context = makeContext({
        maps: [{ id: 'map-a' }],
        _fileVersions: { maps: 'm1' },
    });
    context.captureDbSaveBaseline();
    context.dbPayload._fileVersions.maps = 'different-local-token';

    assert.deepEqual(plain(context.changedDbResourceNames()), []);
    assert.deepEqual(plain(context.dbEditableResourceNames()), ['maps']);
});

test('normalizing a changed resource can return it to a clean baseline', () => {
    const context = makeContext({
        units: [{ id: 'unit-a' }],
        _fileVersions: { units: 'u1' },
    });
    context.captureDbSaveBaseline();
    context.dbPayload.units[0].meta = {};

    assert.deepEqual(plain(context.changedDbResourceNames()), ['units']);
    context.stripEmptyMeta(context.dbPayload.units);
    assert.deepEqual(plain(context.changedDbResourceNames()), []);
});

test('changed resources without a storage version fail before a request can be built', () => {
    const context = makeContext({
        units: [{ id: 'unit-a' }],
        _fileVersions: {},
    });
    context.captureDbSaveBaseline();
    context.dbPayload.units[0].id = 'edited';

    assert.throws(() => context.buildDbSavePayload(['units']), /missing authored-storage version/);
});
