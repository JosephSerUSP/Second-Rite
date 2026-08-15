'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, 'js', 'studio-surface-host.js'), 'utf8');

function classList() {
    const values = new Set();
    return {
        add(value) { values.add(value); },
        contains(value) { return values.has(value); },
    };
}

function eventWindow(base = {}) {
    const listeners = new Map();
    return Object.assign(base, {
        addEventListener(name, fn, capture) {
            if (!listeners.has(name)) listeners.set(name, []);
            listeners.get(name).push({ fn, capture: !!capture });
        },
        dispatchForTest(name, event = {}) {
            const ordered = (listeners.get(name) || []).slice().sort((a, b) => Number(b.capture) - Number(a.capture));
            for (const listener of ordered) {
                listener.fn(event);
                if (event.__stopped) break;
            }
        },
    });
}

function makeKey(key) {
    return {
        key,
        defaultPrevented: false,
        __stopped: false,
        preventDefault() { this.defaultPrevented = true; },
        stopImmediatePropagation() { this.__stopped = true; },
    };
}

function settle() {
    return new Promise(resolve => setImmediate(resolve));
}

function makeTilesetContext(options = {}) {
    const bodyClasses = classList();
    const okButton = {};
    const modal = {
        style: { display: 'none' },
        classList: classList(),
        setAttribute(name, value) { this[name] = value; },
        querySelector(selector) {
            return selector === '.dialog-footer .win98-btn-success' ? okButton : null;
        },
    };
    const closeRequests = [];
    const ready = [];
    const resolves = [];
    const choices = [];
    let openCalls = 0;
    let saveCalls = 0;
    let discardCalls = 0;
    let dirty = options.dirty !== false;
    let closeHandler = null;
    let owners = options.owners || ['dialog:tileset-studio-modal'];

    const context = {
        console,
        URLSearchParams,
        window: eventWindow({
            location: { search: '?surface=tileset' },
            thestraDatabaseBootState: options.bootState || { done: true, ok: true },
            changedDbResourceNames: () => ['maps'],
            thestraPrepareForSurfaceClose: () => options.prepare !== false,
            ThestraInteractionState: {
                snapshot: () => ({ blocked: owners.length > 0, owners: owners.slice() }),
            },
            async openTilesetStudioModal() {
                openCalls += 1;
                if (options.mountFails) throw new Error('tileset load failed');
                modal.style.display = 'flex';
                await Promise.resolve();
                return true;
            },
            closeTilesetStudioModal() { throw new Error('legacy Tileset close should be replaced'); },
            thestraTilesetStudioTransaction: {
                isDirty: () => dirty,
                async save() {
                    saveCalls += 1;
                    if (options.saveResult !== false) dirty = false;
                    return options.saveResult !== false;
                },
                discard() {
                    discardCalls += 1;
                    dirty = false;
                    return options.discardResult !== false;
                },
            },
            thestraStudio: {
                openSurface: async () => ({}),
                closeSurface(id) { closeRequests.push(id); return Promise.resolve({ requested: true }); },
                surfaceReady(id) { ready.push(id); return Promise.resolve({ shown: true }); },
                chooseCloseAction: async id => {
                    choices.push(id);
                    return options.choice || 'cancel';
                },
                onCloseRequest(fn) { closeHandler = fn; },
                resolveCloseRequest(surfaceId, allow) { resolves.push({ surfaceId, allow }); },
            },
        }),
        document: {
            title: '',
            body: { classList: bodyClasses },
            getElementById(id) {
                if (id === 'tileset-studio-modal') return modal;
                if (id === 'thestra-surface-host-styles') return {};
                return null;
            },
        },
        setImmediate,
    };

    vm.createContext(context);
    vm.runInContext(source, context, { filename: 'studio-surface-host.js' });
    return {
        context,
        modal,
        okButton,
        bodyClasses,
        closeRequests,
        ready,
        resolves,
        choices,
        openCalls: () => openCalls,
        saveCalls: () => saveCalls,
        discardCalls: () => discardCalls,
        dirty: () => dirty,
        close: payload => closeHandler(payload),
        setOwners(next) { owners = next.slice(); },
    };
}

test('Electron main redirects both Tileset entrypoints to the native singleton surface', async () => {
    const opens = [];
    const context = {
        console,
        URLSearchParams,
        window: eventWindow({
            location: { search: '' },
            changedDbResourceNames: () => [],
            thestraPrepareForSurfaceClose: () => true,
            thestraStudio: {
                openSurface(id) { opens.push(id); return Promise.resolve({ surfaceId: id }); },
                chooseCloseAction: async () => 'cancel',
                onCloseRequest() {},
                resolveCloseRequest() {},
            },
        }),
        document: { body: { classList: classList() } },
    };
    vm.createContext(context);
    vm.runInContext(source, context, { filename: 'studio-surface-host.js' });

    await context.window.openTilesetStudioModal();
    await context.window.openTilesetStudioForCurrentMap();
    assert.deepEqual(opens, ['tileset', 'tileset']);
});

test('Tileset native surface awaits its real editor load before semantic readiness', async () => {
    const f = makeTilesetContext();
    assert.equal(f.bodyClasses.contains('thestra-surface-tileset'), true);
    assert.equal(f.modal['data-fixed-dialog'], 'true');
    assert.deepEqual(f.ready, [], 'async Tileset mount must finish before BrowserWindow is shown');
    await settle();
    assert.equal(f.openCalls(), 1);
    assert.equal(f.modal.style.display, 'flex');
    assert.deepEqual(f.ready, ['tileset']);

    f.context.window.closeTilesetStudioModal();
    assert.deepEqual(f.closeRequests, ['tileset']);
});

test('Tileset native readiness waits for shared Studio data boot first', async () => {
    const f = makeTilesetContext({ bootState: { done: false, ok: false } });
    await settle();
    assert.equal(f.openCalls(), 0);
    assert.deepEqual(f.ready, []);

    f.context.window.dispatchForTest('thestra-database-boot-ready', { done: true, ok: true });
    await settle();
    assert.equal(f.openCalls(), 1);
    assert.deepEqual(f.ready, ['tileset']);
});

test('Tileset native OK awaits record save and closes only on confirmed success', async () => {
    const saved = makeTilesetContext({ dirty: true, saveResult: true });
    await settle();
    await saved.okButton.onclick();
    assert.equal(saved.saveCalls(), 1);
    assert.deepEqual(saved.closeRequests, ['tileset']);

    const failed = makeTilesetContext({ dirty: true, saveResult: false });
    await settle();
    await failed.okButton.onclick();
    assert.equal(failed.saveCalls(), 1);
    assert.equal(failed.dirty(), true);
    assert.deepEqual(failed.closeRequests, [], 'stale/failed record save must keep Tileset open');
});

test('dirty Tileset native close uses its record transaction for Save, Discard, and Cancel', async () => {
    async function run(choice, saveResult = true) {
        const f = makeTilesetContext({ dirty: true, choice, saveResult });
        await settle();
        await f.close({ surfaceId: 'tileset' });
        return {
            resolve: f.resolves[0],
            choices: f.choices,
            saves: f.saveCalls(),
            discards: f.discardCalls(),
            dirty: f.dirty(),
        };
    }

    assert.deepEqual(await run('discard'), {
        resolve: { surfaceId: 'tileset', allow: true }, choices: ['tileset'],
        saves: 0, discards: 1, dirty: false,
    });
    assert.deepEqual(await run('cancel'), {
        resolve: { surfaceId: 'tileset', allow: false }, choices: ['tileset'],
        saves: 0, discards: 0, dirty: true,
    });
    assert.deepEqual(await run('save', true), {
        resolve: { surfaceId: 'tileset', allow: true }, choices: ['tileset'],
        saves: 1, discards: 0, dirty: false,
    });
    assert.deepEqual(await run('save', false), {
        resolve: { surfaceId: 'tileset', allow: false }, choices: ['tileset'],
        saves: 1, discards: 0, dirty: true,
    });
});

test('Tileset close cancellation from a nested staged interaction prevents record close choice', async () => {
    const f = makeTilesetContext({ dirty: true, prepare: false, choice: 'discard' });
    await settle();
    await f.close({ surfaceId: 'tileset' });
    assert.deepEqual(f.resolves, [{ surfaceId: 'tileset', allow: false }]);
    assert.deepEqual(f.choices, []);
    assert.equal(f.discardCalls(), 0);
});

test('Escape never becomes native Tileset close but nested lightweight interactions still receive it', async () => {
    const f = makeTilesetContext({ owners: ['dialog:tileset-studio-modal'] });
    await settle();
    const hostOnly = makeKey('Escape');
    f.context.window.dispatchForTest('keydown', hostOnly);
    assert.equal(hostOnly.defaultPrevented, true);
    assert.equal(hostOnly.__stopped, true);
    assert.deepEqual(f.closeRequests, []);

    f.setOwners(['dialog:tileset-studio-modal', 'dialog:model-picker-modal']);
    const nested = makeKey('Escape');
    f.context.window.dispatchForTest('keydown', nested);
    assert.equal(nested.defaultPrevented, false);
    assert.equal(nested.__stopped, false);
});

test('browser-hosted Tileset Save waits for commit and closes only on success', async () => {
    async function run(saveResult) {
        const okButton = {};
        let saves = 0;
        let closes = 0;
        const modal = {
            querySelector(selector) {
                return selector === '.dialog-footer .win98-btn-success' ? okButton : null;
            },
        };
        const context = {
            console,
            window: {
                async saveTilesetStudioData() { saves += 1; return saveResult; },
                closeTilesetStudioModal() { closes += 1; },
            },
            document: {
                getElementById(id) { return id === 'tileset-studio-modal' ? modal : null; },
            },
        };
        vm.createContext(context);
        vm.runInContext(source, context, { filename: 'studio-surface-host.js' });
        await okButton.onclick();
        return { saves, closes };
    }

    assert.deepEqual(await run(true), { saves: 1, closes: 1 });
    assert.deepEqual(await run(false), { saves: 1, closes: 0 });
});
