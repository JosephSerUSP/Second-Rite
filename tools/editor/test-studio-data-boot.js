'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, 'js', 'net.js'), 'utf8');

function makeContext(surface = 'main') {
    const listeners = new Map();
    const calls = { fetch: 0, map: 0, database: 0, system: 0 };
    const noop = () => {};

    class FakeCustomEvent {
        constructor(type, init = {}) {
            this.type = type;
            this.detail = init.detail;
        }
    }

    const loaded = {
        maps: [{ id: 'map-a' }],
        units: [{ id: 'unit-a' }],
        _fileVersions: { maps: 'm1', units: 'u1' },
    };

    const genericElement = () => ({
        textContent: '',
        classList: { add: noop, remove: noop },
        disabled: false,
    });

    const context = {
        console,
        JSON,
        Object,
        Array,
        Promise,
        URLSearchParams,
        CustomEvent: FakeCustomEvent,
        setTimeout,
        confirm: () => false,
        API_URL: '',
        isDirty: false,
        dbPayload: {},
        document: {
            addEventListener(type, fn) {
                if (!listeners.has(type)) listeners.set(type, []);
                listeners.get(type).push(fn);
            },
            querySelector: () => null,
            getElementById(id) {
                if (id === 'campaign-picker') return null;
                return genericElement();
            },
        },
        window: {
            location: { search: surface === 'main' ? '' : `?surface=${surface}` },
            addEventListener: noop,
            dispatchEvent: noop,
            dbModalSnapshotHelper: null,
        },
        fetch: async () => {
            calls.fetch += 1;
            return { ok: true, json: async () => structuredClone(loaded) };
        },
        setDirty: noop,
        initMapEditor() { calls.map += 1; },
        initDatabaseEditor() { calls.database += 1; },
        initSystemTab() { calls.system += 1; },
    };

    context.__calls = calls;
    context.__dispatch = async type => {
        const pending = (listeners.get(type) || []).map(fn => fn());
        await Promise.all(pending.filter(value => value && typeof value.then === 'function'));
    };

    vm.createContext(context);
    vm.runInContext(source, context, { filename: 'net.js' });
    return context;
}

test('DOM readiness and the legacy fetchDatabase caller share one authored-data boot', async () => {
    const context = makeContext('main');

    await Promise.all([
        context.__dispatch('DOMContentLoaded'),
        context.fetchDatabase(),
    ]);

    assert.equal(context.__calls.fetch, 1);
    assert.equal(context.__calls.map, 1);
    assert.equal(context.__calls.database, 1);
    assert.equal(context.__calls.system, 1);
    assert.deepEqual(
        JSON.parse(JSON.stringify(context.window.thestraDatabaseBootState)),
        { done: true, ok: true }
    );
});

test('native Database boot initializes Database/System without booting Map', async () => {
    const context = makeContext('database');

    await context.__dispatch('DOMContentLoaded');
    await context.fetchDatabase();

    assert.equal(context.__calls.fetch, 1);
    assert.equal(context.__calls.map, 0);
    assert.equal(context.__calls.database, 1);
    assert.equal(context.__calls.system, 1);
});
