'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, 'js', 'studio-resource-sync.js'), 'utf8');

function plain(value) {
    return JSON.parse(JSON.stringify(value));
}

function makeContext() {
    const events = [];
    const fetches = [];
    let commitListener = null;
    const studio = {
        onResourceCommit(fn) { commitListener = fn; },
        async announceResourceCommit() {},
    };
    const context = {
        console,
        Promise,
        API_URL: '',
        dbPayload: { units: [{ id: 'u1' }], _fileVersions: { units: 'u1-v1' } },
        dbSaveBaseline: { units: [{ id: 'u1' }] },
        dbResourcesEqual(a, b) { return JSON.stringify(a) === JSON.stringify(b); },
        cloneDbResource(value) { return plain(value); },
        captureDbSaveBaseline() {},
        changedDbResourceNames() { return []; },
        dbEditableResourceNames(value) {
            return value && Object.prototype.hasOwnProperty.call(value, 'units') ? ['units'] : [];
        },
        setDirty() {},
        acceptDbSaveResult() { return []; },
        fetch: async url => {
            fetches.push(url);
            if (url === '/api/tilesets') {
                return {
                    ok: true,
                    status: 200,
                    json: async () => ({
                        tilesets: [{ id: 'dungeon_default', _storageVersion: 'tiles-v2' }],
                        textures: ['template_tileset.png'],
                        storage: { kind: 'registry' },
                    }),
                };
            }
            throw new Error(`unexpected fetch ${url}`);
        },
        CustomEvent: class {
            constructor(type, options) { this.type = type; this.detail = options && options.detail; }
        },
        window: {
            thestraStudio: studio,
            thestraDatabaseBootState: { done: true, ok: true },
            addEventListener() {},
            dispatchEvent(event) { events.push({ type: event.type, detail: plain(event.detail) }); },
        },
    };
    context.window.window = context.window;
    vm.createContext(context);
    vm.runInContext(source, context, { filename: 'studio-resource-sync.js' });
    return {
        context,
        events,
        fetches,
        commit(payload) { return commitListener(payload); },
    };
}

test('record-managed Tileset invalidation refreshes through /api/tilesets rather than bulk /data', async () => {
    const f = makeContext();
    f.commit({ sourceSurface: 'tileset', resources: ['tilesets'] });
    await f.context.window.thestraResourceRefreshIdle();

    assert.deepEqual(f.fetches, ['/api/tilesets']);
    assert.deepEqual(f.events, [
        {
            type: 'thestra-tilesets-refreshed',
            detail: {
                sourceSurface: 'tileset',
                tilesets: [{ id: 'dungeon_default', _storageVersion: 'tiles-v2' }],
                textures: ['template_tileset.png'],
                storage: { kind: 'registry' },
            },
        },
        {
            type: 'thestra-resources-refreshed',
            detail: { sourceSurface: 'tileset', refreshed: ['tilesets'], blocked: [] },
        },
    ]);
});

test('mixed bulk + Tileset invalidation uses each resource normal read authority', async () => {
    const f = makeContext();
    f.context.fetch = async url => {
        f.fetches.push(url);
        if (url === '/data') {
            return {
                ok: true,
                status: 200,
                json: async () => ({ units: [{ id: 'u2' }], _fileVersions: { units: 'u2-v2' } }),
            };
        }
        if (url === '/api/tilesets') {
            return {
                ok: true,
                status: 200,
                json: async () => ({ tilesets: [{ id: 'castle' }], textures: [], storage: null }),
            };
        }
        throw new Error(`unexpected fetch ${url}`);
    };

    f.commit({ sourceSurface: 'database', resources: ['units', 'tilesets'] });
    await f.context.window.thestraResourceRefreshIdle();

    assert.deepEqual(f.fetches, ['/data', '/api/tilesets']);
    assert.deepEqual(plain(f.context.dbPayload.units), [{ id: 'u2' }]);
    const final = f.events[f.events.length - 1];
    assert.deepEqual(final, {
        type: 'thestra-resources-refreshed',
        detail: { sourceSurface: 'database', refreshed: ['units', 'tilesets'], blocked: [] },
    });
});
