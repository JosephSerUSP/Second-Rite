'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');
const projectInvalidation = require('./project-resource-invalidation');

const source = fs.readFileSync(path.join(__dirname, 'js', 'studio-resource-sync.js'), 'utf8');

function clone(value) {
    if (value === undefined) return undefined;
    return JSON.parse(JSON.stringify(value));
}

function makeContext(payload, options = {}) {
    const announced = [];
    const emitted = [];
    const dirtyStates = [];
    const toasts = [];
    let commitHandler = null;

    class FakeCustomEvent {
        constructor(type, init = {}) {
            this.type = type;
            this.detail = init.detail;
        }
    }

    const baseline = {};
    const dbPayload = clone(payload);
    for (const name of Object.keys(dbPayload).filter(name => !name.startsWith('_'))) {
        baseline[name] = clone(dbPayload[name]);
    }

    const studio = {
        onResourceCommit(callback) { commitHandler = callback; },
        announceResourceCommit(resources) {
            announced.push(clone(resources));
            return Promise.resolve({ resources });
        },
    };

    const context = {
        console,
        JSON,
        Object,
        Array,
        Promise,
        Set,
        CustomEvent: FakeCustomEvent,
        API_URL: '',
        dbPayload,
        dbSaveBaseline: baseline,
        window: {
            thestraStudio: studio,
            thestraDatabaseBootState: { done: true, ok: true },
            addEventListener() {},
            dispatchEvent(event) { emitted.push(event); return true; },
        },
        fetch: options.fetch || (async () => { throw new Error('unexpected fetch'); }),
        showToast(message) { toasts.push(message); },
        setDirty(value) { dirtyStates.push(!!value); },
        cloneDbResource: clone,
        dbResourcesEqual(a, b) { return JSON.stringify(a) === JSON.stringify(b); },
        dbEditableResourceNames(value = dbPayload) {
            return Object.keys(value || {}).filter(name => !name.startsWith('_'));
        },
        captureDbSaveBaseline(names) {
            for (const name of names) baseline[name] = clone(dbPayload[name]);
        },
        changedDbResourceNames() {
            return Object.keys(dbPayload).filter(name => !name.startsWith('_'))
                .filter(name => JSON.stringify(dbPayload[name]) !== JSON.stringify(baseline[name]));
        },
        acceptDbSaveResult(sentPayload, result) {
            for (const name of Object.keys(sentPayload).filter(name => !name.startsWith('_'))) {
                baseline[name] = clone(sentPayload[name]);
                if (result.versions && result.versions[name] !== undefined) {
                    if (!dbPayload._fileVersions) dbPayload._fileVersions = {};
                    dbPayload._fileVersions[name] = result.versions[name];
                }
            }
            return context.changedDbResourceNames();
        },
    };

    context.__announced = announced;
    context.__emitted = emitted;
    context.__dirtyStates = dirtyStates;
    context.__toasts = toasts;
    context.__commit = payload => commitHandler(payload);

    vm.createContext(context);
    vm.runInContext(source, context, { filename: 'studio-resource-sync.js' });
    return context;
}

function plain(value) {
    return JSON.parse(JSON.stringify(value));
}

test('successful transaction acceptance announces exactly the committed resource names', async () => {
    const context = makeContext({
        maps: [{ id: 'map-a' }],
        units: [{ id: 'unit-a' }],
        _fileVersions: { maps: 'm1', units: 'u1' },
    });

    context.acceptDbSaveResult({
        units: [{ id: 'unit-edited' }],
        _fileVersions: { units: 'u1' },
    }, { versions: { units: 'u2' } });
    await Promise.resolve();

    assert.deepEqual(context.__announced, [['units']]);
});

test('clean committed resource refresh adopts server truth without disturbing unrelated local edits', async () => {
    const context = makeContext({
        maps: [{ id: 'map-a', note: 'original' }],
        units: [{ id: 'unit-a', hp: 10 }],
        _fileVersions: { maps: 'm1', units: 'u1' },
    }, {
        fetch: async () => ({
            ok: true,
            json: async () => ({
                maps: [{ id: 'map-a', note: 'server' }],
                units: [{ id: 'unit-a', hp: 20 }],
                _fileVersions: { maps: 'm2', units: 'u2' },
            }),
        }),
    });
    context.dbPayload.maps[0].note = 'local unsaved';

    context.__commit({ sourceSurface: 'database', resources: ['units'] });
    await context.window.thestraResourceRefreshIdle();

    assert.equal(context.dbPayload.units[0].hp, 20);
    assert.equal(context.dbPayload._fileVersions.units, 'u2');
    assert.equal(context.dbPayload.maps[0].note, 'local unsaved');
    assert.equal(context.dbPayload._fileVersions.maps, 'm1');
    assert.deepEqual(plain(context.changedDbResourceNames()), ['maps']);
    assert.equal(context.__dirtyStates.at(-1), true);
    assert.deepEqual(plain(context.__emitted.at(-1).detail), {
        sourceSurface: 'database', refreshed: ['units'], blocked: [],
    });
});

test('same-resource local edits are never overwritten and retain their stale token', async () => {
    const context = makeContext({
        units: [{ id: 'unit-a', hp: 10 }],
        _fileVersions: { units: 'u1' },
    }, {
        fetch: async () => ({
            ok: true,
            json: async () => ({
                units: [{ id: 'unit-a', hp: 20 }],
                _fileVersions: { units: 'u2' },
            }),
        }),
    });
    context.dbPayload.units[0].hp = 15;

    context.__commit({ sourceSurface: 'main', resources: ['units'] });
    await context.window.thestraResourceRefreshIdle();

    assert.equal(context.dbPayload.units[0].hp, 15);
    assert.equal(context.dbPayload._fileVersions.units, 'u1');
    assert.deepEqual(plain(context.window.thestraExternallyChangedResources()), ['units']);
    assert.match(context.__toasts.at(-1), /local edits were kept/i);
    assert.deepEqual(plain(context.__emitted.at(-1).detail), {
        sourceSurface: 'main', refreshed: [], blocked: ['units'],
    });
});

test('an edit started while refresh fetch is in flight wins over the arriving committed snapshot', async () => {
    let resolveFetch;
    let markFetchStarted;
    const fetchStarted = new Promise(resolve => { markFetchStarted = resolve; });
    const context = makeContext({
        units: [{ id: 'unit-a', hp: 10 }],
        _fileVersions: { units: 'u1' },
    }, {
        fetch: async () => {
            markFetchStarted();
            return new Promise(resolve => { resolveFetch = resolve; });
        },
    });

    context.__commit({ sourceSurface: 'database', resources: ['units'] });
    await fetchStarted;
    context.dbPayload.units[0].hp = 15;
    resolveFetch({
        ok: true,
        json: async () => ({
            units: [{ id: 'unit-a', hp: 20 }],
            _fileVersions: { units: 'u2' },
        }),
    });
    await context.window.thestraResourceRefreshIdle();

    assert.equal(context.dbPayload.units[0].hp, 15);
    assert.equal(context.dbPayload._fileVersions.units, 'u1');
    assert.deepEqual(plain(context.window.thestraExternallyChangedResources()), ['units']);
});

test('Project paths classify to manifest-owned semantic resources without exposing fragments', () => {
    const classify = projectInvalidation.classifyProjectRelativePath;

    assert.deepEqual(classify('data/items.json'), {
        kind: 'resource', resource: 'items', relativePath: 'data/items.json',
    });
    assert.deepEqual(classify('data/system.json'), {
        kind: 'resource', resource: 'system', relativePath: 'data/system.json',
    });
    assert.deepEqual(classify('data/units/pixie.json'), {
        kind: 'resource', resource: 'units', relativePath: 'data/units/pixie.json',
    });
    assert.deepEqual(classify('data\\units\\index.json'), {
        kind: 'resource', resource: 'units', relativePath: 'data/units/index.json',
    });
    assert.deepEqual(classify('data/tilesets/new-wall.JSON'), {
        kind: 'resource', resource: 'tilesets', relativePath: 'data/tilesets/new-wall.JSON',
    });
    // Even an undeclared semantic-config module invalidates its owning resource:
    // the normal authoritative re-read/validator is responsible for rejecting it.
    assert.deepEqual(classify('data/flows/new-module.json'), {
        kind: 'resource', resource: 'flows', relativePath: 'data/flows/new-module.json',
    });
});

test('Project invalidation refuses alternate representations and non-authoritative data paths', () => {
    const classify = projectInvalidation.classifyProjectRelativePath;

    assert.equal(classify('data/units.json'), null, 'fragment resource must not gain a monolith authority');
    assert.equal(classify('data/items/other.json'), null, 'monolith resource must not gain fragment authority');
    assert.equal(classify('data/scenes/nested/page.json'), null, 'nested fragment paths are not authoritative');
    assert.equal(classify('data/unknown.json'), null, 'unknown data stem is not a semantic resource');
    assert.equal(classify('data/authored_storage_manifest.json'), null, 'runtime storage schema is not Project authored data');
    assert.equal(classify('data/units/readme.md'), null, 'non-JSON fragment is not authored resource data');
    assert.equal(classify('../data/items.json'), null, 'relative traversal is never Project authority');
});

test('Project assets are classified separately from authored resource commits', () => {
    const invalidation = projectInvalidation.classifyProjectRelativePath('assets/models/props/chest.obj');
    assert.deepEqual(invalidation, {
        kind: 'asset',
        assetPath: 'models/props/chest.obj',
        relativePath: 'assets/models/props/chest.obj',
    });
    assert.equal(projectInvalidation.classifyProjectRelativePath('tools/editor/index.html'), null);
});

test('absolute Project classification rejects outside and prefix-collision paths', () => {
    const projectRoot = path.resolve('tmp', 'thestra-invalidation-project');
    const inside = path.join(projectRoot, 'data', 'units', 'pixie.json');
    const outside = path.resolve(projectRoot, '..', 'other-project', 'data', 'units', 'pixie.json');
    const prefixCollision = projectRoot + '-copy' + path.sep + 'data' + path.sep + 'items.json';

    assert.equal(projectInvalidation.classifyProjectPath(projectRoot, inside).resource, 'units');
    assert.equal(projectInvalidation.classifyProjectPath(projectRoot, outside), null);
    assert.equal(projectInvalidation.classifyProjectPath(projectRoot, prefixCollision), null);
    assert.equal(projectInvalidation.classifyProjectPath(projectRoot, projectRoot), null);
});

test('resource-name projection de-duplicates fragments and ignores asset-only invalidations', () => {
    const projectRoot = path.resolve('tmp', 'thestra-invalidation-project');
    const resources = projectInvalidation.resourceNamesForProjectPaths(projectRoot, [
        path.join(projectRoot, 'data', 'units', 'pixie.json'),
        path.join(projectRoot, 'data', 'units', 'index.json'),
        path.join(projectRoot, 'data', 'tilesets', 'stone.json'),
        path.join(projectRoot, 'assets', 'sprites', 'pixie.png'),
        path.resolve(projectRoot, '..', 'outside', 'data', 'items.json'),
    ]);
    assert.deepEqual(resources, ['units', 'tilesets']);
});
