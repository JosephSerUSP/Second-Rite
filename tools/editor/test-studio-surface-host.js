'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, 'js', 'studio-surface-host.js'), 'utf8');
const preloadSource = fs.readFileSync(path.join(__dirname, 'project-preload.js'), 'utf8');

function classList() {
    const values = new Set();
    return {
        add(value) { values.add(value); },
        contains(value) { return values.has(value); },
    };
}

function databaseModal(okButton = null) {
    return {
        classList: classList(),
        setAttribute(name, value) { this[name] = value; },
        querySelector(selector) {
            return selector === '.dialog-footer .win98-btn-success' ? okButton : null;
        },
    };
}

function eventWindow(base = {}) {
    const listeners = new Map();
    return Object.assign(base, {
        addEventListener(name, fn) { listeners.set(name, fn); },
        dispatchForTest(name, detail) {
            const fn = listeners.get(name);
            if (fn) fn({ type: name, detail });
        },
    });
}

test('Electron main redirects the existing Database command to the native surface', async () => {
    const opens = [];
    const context = {
        console,
        URLSearchParams,
        window: eventWindow({
            location: { search: '' },
            thestraStudio: {
                openSurface(id) { opens.push(id); return Promise.resolve({ surfaceId: id }); },
            },
            openDatabaseModal() { throw new Error('legacy modal path should have been replaced'); },
        }),
        document: { body: { classList: classList() } },
    };
    vm.createContext(context);
    vm.runInContext(source, context, { filename: 'studio-surface-host.js' });

    await context.window.openDatabaseModal();
    assert.deepEqual(opens, ['database']);
});

test('Database surface mounts the existing modal and signals readiness after an already-complete editor boot', async () => {
    const bodyClasses = classList();
    const okButton = {};
    const modal = databaseModal(okButton);
    const styles = {};
    let closeHandler = null;
    const closeRequests = [];
    const resolves = [];
    const ready = [];
    const context = {
        console,
        URLSearchParams,
        window: eventWindow({
            location: { search: '?surface=database' },
            thestraDatabaseBootState: { done: true, ok: true },
            changedDbResourceNames: () => [],
            thestraPrepareForSurfaceClose: () => true,
            thestraStudio: {
                openSurface: async () => ({}),
                closeSurface(id) { closeRequests.push(id); return Promise.resolve({ requested: true }); },
                surfaceReady(id) { ready.push(id); return Promise.resolve({ shown: true }); },
                chooseCloseAction: async () => 'cancel',
                onCloseRequest(fn) { closeHandler = fn; },
                resolveCloseRequest(surfaceId, allow) { resolves.push({ surfaceId, allow }); },
            },
            closeDatabaseModal() { throw new Error('legacy close should be replaced'); },
        }),
        document: {
            title: '',
            body: { classList: bodyClasses },
            getElementById(id) {
                if (id === 'db-modal') return modal;
                if (id === 'thestra-surface-host-styles') return styles;
                return null;
            },
        },
        saveData: async () => true,
    };
    vm.createContext(context);
    vm.runInContext(source, context, { filename: 'studio-surface-host.js' });

    assert.equal(bodyClasses.contains('thestra-surface-database'), true);
    assert.equal(modal.classList.contains('active'), true);
    assert.equal(modal['data-fixed-dialog'], 'true');
    assert.equal(typeof closeHandler, 'function');
    assert.deepEqual(ready, ['database']);

    context.window.closeDatabaseModal();
    assert.deepEqual(closeRequests, ['database']);

    await closeHandler({ surfaceId: 'database' });
    assert.deepEqual(resolves, [{ surfaceId: 'database', allow: true }]);
});

test('Database native readiness waits for the real editor boot event when data is still loading', () => {
    const modal = databaseModal();
    const ready = [];
    const context = {
        console,
        URLSearchParams,
        window: eventWindow({
            location: { search: '?surface=database' },
            thestraDatabaseBootState: { done: false, ok: false },
            changedDbResourceNames: () => [],
            thestraPrepareForSurfaceClose: () => true,
            thestraStudio: {
                closeSurface: async () => ({}),
                surfaceReady(id) { ready.push(id); return Promise.resolve({ shown: true }); },
                chooseCloseAction: async () => 'cancel',
                onCloseRequest() {},
                resolveCloseRequest() {},
            },
        }),
        document: {
            title: '',
            body: { classList: classList() },
            getElementById(id) {
                if (id === 'db-modal') return modal;
                if (id === 'thestra-surface-host-styles') return {};
                return null;
            },
        },
        saveData: async () => true,
    };
    vm.createContext(context);
    vm.runInContext(source, context);

    assert.deepEqual(ready, []);
    context.window.dispatchForTest('thestra-database-boot-ready', { done: true, ok: true });
    assert.deepEqual(ready, ['database']);
    context.window.dispatchForTest('thestra-database-boot-ready', { done: true, ok: true });
    assert.deepEqual(ready, ['database'], 'readiness must be signalled exactly once');
});

test('terminal offline boot still reveals Database so its error state is visible', () => {
    const modal = databaseModal();
    const ready = [];
    const context = {
        console,
        URLSearchParams,
        window: eventWindow({
            location: { search: '?surface=database' },
            thestraDatabaseBootState: { done: true, ok: false },
            changedDbResourceNames: () => [],
            thestraPrepareForSurfaceClose: () => true,
            thestraStudio: {
                closeSurface: async () => ({}),
                surfaceReady(id) { ready.push(id); return Promise.resolve({ shown: true }); },
                chooseCloseAction: async () => 'cancel',
                onCloseRequest() {},
                resolveCloseRequest() {},
            },
        }),
        document: {
            title: '',
            body: { classList: classList() },
            getElementById(id) {
                if (id === 'db-modal') return modal;
                if (id === 'thestra-surface-host-styles') return {};
                return null;
            },
        },
        saveData: async () => true,
    };
    vm.createContext(context);
    vm.runInContext(source, context);
    assert.deepEqual(ready, ['database']);
});

test('preload serializes host CSS before injecting the native surface adapter', () => {
    assert.match(preloadSource,
        /const injectSurfaceScript = \(\) => \{[\s\S]*document\.head\.appendChild\(surfaceScript\);[\s\S]*\};/);
    assert.match(preloadSource,
        /surfaceStyles\.addEventListener\('load', injectSurfaceScript, \{ once: true \}\);[\s\S]*document\.head\.appendChild\(surfaceStyles\);/);
    assert.doesNotMatch(preloadSource,
        /document\.head\.appendChild\(surfaceStyles\);\s*\n\s*const surfaceScript/);
});

test('dirty Database native close honors Discard and Cancel choices', async () => {
    async function runChoice(choice) {
        let closeHandler = null;
        const resolves = [];
        const modal = databaseModal();
        const context = {
            console,
            URLSearchParams,
            window: eventWindow({
                location: { search: '?surface=database' },
                thestraDatabaseBootState: { done: true, ok: true },
                changedDbResourceNames: () => ['units'],
                thestraPrepareForSurfaceClose: () => true,
                thestraStudio: {
                    closeSurface: async () => ({ requested: true }),
                    surfaceReady: async () => ({ shown: true }),
                    chooseCloseAction: async () => choice,
                    onCloseRequest(fn) { closeHandler = fn; },
                    resolveCloseRequest(surfaceId, allow) { resolves.push({ surfaceId, allow }); },
                },
            }),
            document: {
                title: '',
                body: { classList: classList() },
                getElementById(id) {
                    if (id === 'db-modal') return modal;
                    if (id === 'thestra-surface-host-styles') return {};
                    return null;
                },
            },
            saveData: async () => true,
        };
        vm.createContext(context);
        vm.runInContext(source, context);
        await closeHandler({ surfaceId: 'database' });
        return resolves[0];
    }

    assert.deepEqual(await runChoice('discard'), { surfaceId: 'database', allow: true });
    assert.deepEqual(await runChoice('cancel'), { surfaceId: 'database', allow: false });
});
