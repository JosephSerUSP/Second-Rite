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

function makeEngineContext(options = {}) {
    const bodyClasses = classList();
    const modalClasses = classList();
    const okButton = {};
    const modal = {
        classList: modalClasses,
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
    let closeHandler = null;
    let owners = options.owners || ['dialog:engine-modal'];

    const context = {
        console,
        URLSearchParams,
        window: eventWindow({
            location: { search: '?surface=engine' },
            thestraDatabaseBootState: options.bootState || { done: true, ok: true },
            changedDbResourceNames: () => options.changed || [],
            thestraPrepareForSurfaceClose: () => options.prepare !== false,
            ThestraInteractionState: {
                snapshot: () => ({ blocked: owners.length > 0, owners: owners.slice() }),
            },
            openEngineModal() {
                openCalls += 1;
                modalClasses.add('active');
            },
            closeEngineModal() { throw new Error('legacy Engine close should be replaced'); },
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
                if (id === 'engine-modal') return modal;
                if (id === 'thestra-surface-host-styles') return {};
                return null;
            },
        },
        saveData: async () => {
            saveCalls += 1;
            return options.saveResult !== false;
        },
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
        close: payload => closeHandler(payload),
        setOwners(next) { owners = next.slice(); },
    };
}

test('Electron main redirects the existing Engine command to the native singleton surface', async () => {
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
            openEngineModal() { throw new Error('legacy Engine modal path should have been replaced'); },
        }),
        document: { body: { classList: classList() } },
    };
    vm.createContext(context);
    vm.runInContext(source, context, { filename: 'studio-surface-host.js' });

    await context.window.openEngineModal();
    assert.deepEqual(opens, ['engine']);
});

test('Engine surface mounts existing editor content only after shared data boot and signals readiness', () => {
    const f = makeEngineContext();
    assert.equal(f.bodyClasses.contains('thestra-surface-engine'), true);
    assert.equal(f.modal.classList.contains('active'), true);
    assert.equal(f.modal['data-fixed-dialog'], 'true');
    assert.equal(f.openCalls(), 1, 'existing Engine initialization should mount exactly once');
    assert.deepEqual(f.ready, ['engine']);

    f.context.window.closeEngineModal();
    assert.deepEqual(f.closeRequests, ['engine']);
});

test('Engine readiness waits for shared data boot and terminal offline boot still reveals the editor', () => {
    const loading = makeEngineContext({ bootState: { done: false, ok: false } });
    assert.deepEqual(loading.ready, []);
    assert.equal(loading.openCalls(), 0);
    loading.context.window.dispatchForTest('thestra-database-boot-ready', { done: true, ok: true });
    assert.deepEqual(loading.ready, ['engine']);
    assert.equal(loading.openCalls(), 1);

    const offline = makeEngineContext({ bootState: { done: true, ok: false } });
    assert.deepEqual(offline.ready, ['engine']);
    assert.equal(offline.openCalls(), 1);
});

test('Engine native OK awaits scoped save before requesting native close', async () => {
    const f = makeEngineContext({ saveResult: true });
    await f.okButton.onclick();
    assert.equal(f.saveCalls(), 1);
    assert.deepEqual(f.closeRequests, ['engine']);

    const failed = makeEngineContext({ saveResult: false });
    await failed.okButton.onclick();
    assert.equal(failed.saveCalls(), 1);
    assert.deepEqual(failed.closeRequests, [], 'failed save must keep Engine open');
});

test('dirty Engine native close honors Save, Discard, and Cancel through generic close intent', async () => {
    async function run(choice, saveResult = true) {
        const f = makeEngineContext({ changed: ['engine'], choice, saveResult });
        await f.close({ surfaceId: 'engine' });
        return { resolve: f.resolves[0], choices: f.choices, saves: f.saveCalls() };
    }

    assert.deepEqual(await run('discard'), {
        resolve: { surfaceId: 'engine', allow: true }, choices: ['engine'], saves: 0,
    });
    assert.deepEqual(await run('cancel'), {
        resolve: { surfaceId: 'engine', allow: false }, choices: ['engine'], saves: 0,
    });
    assert.deepEqual(await run('save', true), {
        resolve: { surfaceId: 'engine', allow: true }, choices: ['engine'], saves: 1,
    });
    assert.deepEqual(await run('save', false), {
        resolve: { surfaceId: 'engine', allow: false }, choices: ['engine'], saves: 1,
    });
});

test('Escape never becomes native Engine close but still passes through for nested lightweight dialogs', () => {
    const f = makeEngineContext({ owners: ['dialog:engine-modal'] });
    const hostOnly = makeKey('Escape');
    f.context.window.dispatchForTest('keydown', hostOnly);
    assert.equal(hostOnly.defaultPrevented, true);
    assert.equal(hostOnly.__stopped, true);
    assert.deepEqual(f.closeRequests, []);

    f.setOwners(['dialog:engine-modal', 'dialog:damage-popup-modal']);
    const nested = makeKey('Escape');
    f.context.window.dispatchForTest('keydown', nested);
    assert.equal(nested.defaultPrevented, false);
    assert.equal(nested.__stopped, false, 'legacy interaction stack must receive Escape for nested dialogs');
});
