'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');
const { ALLOWED_SURFACES, installStudioIpc } = require('./studio-electron');
const { createStudioShutdownCoordinator } = require('./studio-shutdown');

function fakeIpcMain() {
    const handlers = new Map();
    const listeners = new Map();
    return {
        handle(name, fn) { handlers.set(name, fn); },
        on(name, fn) { listeners.set(name, fn); },
        invoke(name, event, ...args) { return handlers.get(name)(event, ...args); },
        emit(name, event, ...args) { return listeners.get(name)(event, ...args); },
    };
}

function webContents(id, sent) {
    return {
        id,
        isDestroyed: () => false,
        send(name, payload) { sent.push({ name, payload }); },
    };
}

test('Engine is a registered secondary IPC surface with Engine-specific dirty close copy', async () => {
    assert.deepEqual(ALLOWED_SURFACES, ['database', 'engine', 'tileset']);

    const ipcMain = fakeIpcMain();
    const mainSent = [];
    const databaseSent = [];
    const engineSent = [];
    const mainContents = webContents(1, mainSent);
    const databaseContents = webContents(2, databaseSent);
    const engineContents = webContents(3, engineSent);
    const windows = {
        main: { webContents: mainContents },
        database: { webContents: databaseContents },
        engine: {
            webContents: engineContents,
            showCount: 0,
            focusCount: 0,
            show() { this.showCount += 1; },
            focus() { this.focusCount += 1; },
        },
    };
    const open = new Set();
    const openCalls = [];
    const closeCalls = [];
    const dialogCalls = [];
    const ready = [];
    const windowManager = {
        get(id) { return windows[id] || null; },
        has(id) { return open.has(id); },
        open(id) { open.add(id); openCalls.push(id); return windows[id]; },
        close(id) { open.delete(id); closeCalls.push(id); return true; },
    };
    const dialog = {
        async showMessageBox(owner, options) {
            dialogCalls.push({ owner, options });
            return { response: 2 };
        },
    };
    installStudioIpc({
        ipcMain,
        dialog,
        windowManager,
        allowedResources: ['engine', 'system', 'maps'],
        onSurfaceReady(id) { ready.push(id); },
    });

    assert.deepEqual(await ipcMain.invoke('thestra-studio-open-surface', { sender: mainContents }, 'engine'), {
        surfaceId: 'engine',
    });
    assert.deepEqual(openCalls, ['engine']);
    assert.deepEqual(await ipcMain.invoke('thestra-studio-project-switch-ready', { sender: mainContents }), {
        ready: false,
        blockers: ['engine'],
    });

    assert.deepEqual(await ipcMain.invoke('thestra-studio-surface-ready', { sender: engineContents }, 'engine'), {
        surfaceId: 'engine', shown: true,
    });
    assert.equal(windows.engine.showCount, 1);
    assert.equal(windows.engine.focusCount, 1);
    assert.deepEqual(ready, ['engine']);

    const choice = await ipcMain.invoke('thestra-studio-close-choice', { sender: engineContents }, 'engine');
    assert.equal(choice, 'cancel');
    assert.equal(dialogCalls.length, 1);
    assert.match(dialogCalls[0].options.title, /Engine Editor/);
    assert.match(dialogCalls[0].options.message, /closing Engine Editor/);
    assert.deepEqual(dialogCalls[0].options.buttons, ['Save', 'Discard', 'Cancel']);

    assert.deepEqual(await ipcMain.invoke('thestra-studio-close-surface', { sender: engineContents }, 'engine'), {
        surfaceId: 'engine', requested: true,
    });
    assert.deepEqual(closeCalls, ['engine']);
});

test('Engine commits invalidate clean sibling renderers without echoing authored values to sender', async () => {
    const ipcMain = fakeIpcMain();
    const mainSent = [];
    const databaseSent = [];
    const engineSent = [];
    const windows = {
        main: { webContents: webContents(1, mainSent) },
        database: { webContents: webContents(2, databaseSent) },
        engine: { webContents: webContents(3, engineSent) },
    };
    const windowManager = {
        get(id) { return windows[id] || null; },
        has() { return true; },
        open() {},
        close() { return true; },
    };
    installStudioIpc({
        ipcMain,
        dialog: { async showMessageBox() { return { response: 2 }; } },
        windowManager,
        allowedResources: ['engine', 'system', 'maps'],
    });

    const result = await ipcMain.invoke(
        'thestra-studio-resource-commit',
        { sender: windows.engine.webContents },
        { resources: ['system', 'engine', 'system'] }
    );
    assert.deepEqual(result, {
        sourceSurface: 'engine',
        resources: ['system', 'engine'],
        deliveredTo: ['main', 'database'],
    });
    assert.deepEqual(engineSent, [], 'sender must never receive its own invalidation');
    for (const sent of [mainSent, databaseSent]) {
        assert.deepEqual(sent, [{
            name: 'thestra-studio-resource-committed',
            payload: { sourceSurface: 'engine', resources: ['system', 'engine'] },
        }]);
    }
});

test('coordinated Studio shutdown resolves Database and Engine before main', async () => {
    const order = [];
    const windowManager = {
        has(id) { return id === 'database' || id === 'engine'; },
        async closeAndWait(id) { order.push(id); return true; },
    };
    const studioIpc = {
        requestClose(id, _win, decide) {
            order.push(id);
            decide(true);
        },
    };
    const coordinator = createStudioShutdownCoordinator({
        windowManager,
        studioIpc,
        secondarySurfaces: ALLOWED_SURFACES,
    });

    const result = await new Promise(resolve => {
        coordinator.requestMainClose({ webContents: {} }, resolve);
    });
    assert.equal(result, true);
    assert.deepEqual(order, ['database', 'engine', 'main']);
});

test('Engine cancellation aborts shutdown before main close intent', async () => {
    const order = [];
    const windowManager = {
        has(id) { return id === 'database' || id === 'engine'; },
        async closeAndWait(id) {
            order.push(id);
            return id !== 'engine';
        },
    };
    const studioIpc = {
        requestClose(id, _win, decide) {
            order.push(id);
            decide(true);
        },
    };
    const coordinator = createStudioShutdownCoordinator({
        windowManager,
        studioIpc,
        secondarySurfaces: ALLOWED_SURFACES,
    });

    const result = await new Promise(resolve => {
        coordinator.requestMainClose({ webContents: {} }, resolve);
    });
    assert.equal(result, false);
    assert.deepEqual(order, ['database', 'engine']);
});
