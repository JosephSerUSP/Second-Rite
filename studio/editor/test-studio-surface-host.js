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
            if (fn) return fn({ type: name, detail });
        },
    });
}

function mainCloseContext(options = {}) {
    let closeHandler = null;
    const resolves = [];
    const choices = [];
    let saves = 0;
    const context = {
        console,
        URLSearchParams,
        window: eventWindow({
            location: { search: '' },
            changedDbResourceNames: () => options.changed || [],
            thestraPrepareForSurfaceClose: () => options.prepare !== false,
            thestraStudio: {
                openSurface: async () => ({ surfaceId: 'database' }),
                chooseCloseAction: async surfaceId => {
                    choices.push(surfaceId);
                    return options.choice || 'cancel';
                },
                onCloseRequest(fn) { closeHandler = fn; },
                resolveCloseRequest(surfaceId, allow) { resolves.push({ surfaceId, allow }); },
            },
        }),
        document: { body: { classList: classList() } },
        saveData: async () => {
            saves += 1;
            return options.saveResult !== false;
        },
    };
    context.__close = payload => closeHandler(payload);
    context.__resolves = resolves;
    context.__choices = choices;
    context.__saves = () => saves;
    vm.createContext(context);
    vm.runInContext(source, context, { filename: 'studio-surface-host.js' });
    return context;
}

test('Electron main redirects the existing Database command to the native surface', async () => {
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
            openDatabaseModal() { throw new Error('legacy modal path should have been replaced'); },
        }),
        document: { body: { classList: classList() } },
    };
    vm.createContext(context);
    vm.runInContext(source, context, { filename: 'studio-surface-host.js' });

    await context.window.openDatabaseModal();
    assert.deepEqual(opens, ['database']);
});

test('clean main workspace approves native Alt+F4 without a choice dialog', async () => {
    const context = mainCloseContext({ changed: [] });
    await context.__close({ surfaceId: 'main' });
    assert.deepEqual(context.__resolves, [{ surfaceId: 'main', allow: true }]);
    assert.deepEqual(context.__choices, []);
    assert.equal(context.__saves(), 0);
});

test('dirty main workspace honors Discard, Cancel, and Save close choices', async () => {
    async function run(choice, saveResult = true) {
        const context = mainCloseContext({ changed: ['maps'], choice, saveResult });
        await context.__close({ surfaceId: 'main' });
        return {
            resolve: context.__resolves[0],
            choices: context.__choices,
            saves: context.__saves(),
        };
    }

    assert.deepEqual(await run('discard'), {
        resolve: { surfaceId: 'main', allow: true }, choices: ['main'], saves: 0,
    });
    assert.deepEqual(await run('cancel'), {
        resolve: { surfaceId: 'main', allow: false }, choices: ['main'], saves: 0,
    });
    assert.deepEqual(await run('save', true), {
        resolve: { surfaceId: 'main', allow: true }, choices: ['main'], saves: 1,
    });
    assert.deepEqual(await run('save', false), {
        resolve: { surfaceId: 'main', allow: false }, choices: ['main'], saves: 1,
    });
});

test('main native close is canceled when a staged child interaction refuses to close', async () => {
    const context = mainCloseContext({ changed: ['maps'], prepare: false, choice: 'discard' });
    await context.__close({ surfaceId: 'main' });
    assert.deepEqual(context.__resolves, [{ surfaceId: 'main', allow: false }]);
    assert.deepEqual(context.__choices, []);
    assert.equal(context.__saves(), 0);
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
