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

test('Tileset is a registered secondary IPC surface with Tileset-specific dirty close copy', async () => {
    assert.deepEqual(ALLOWED_SURFACES, ['database', 'engine', 'tileset']);

    const ipcMain = fakeIpcMain();
    const mainContents = webContents(1, []);
    const tilesetContents = webContents(4, []);
    const windows = {
        main: { webContents: mainContents },
        tileset: {
            webContents: tilesetContents,
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
    installStudioIpc({ ipcMain, dialog, windowManager, onSurfaceReady(id) { ready.push(id); } });

    assert.deepEqual(await ipcMain.invoke('thestra-studio-open-surface', { sender: mainContents }, 'tileset'), {
        surfaceId: 'tileset',
    });
    assert.deepEqual(openCalls, ['tileset']);
    assert.deepEqual(await ipcMain.invoke('thestra-studio-project-switch-ready', { sender: mainContents }), {
        ready: false,
        blockers: ['tileset'],
    });

    assert.deepEqual(await ipcMain.invoke('thestra-studio-surface-ready', { sender: tilesetContents }, 'tileset'), {
        surfaceId: 'tileset', shown: true,
    });
    assert.equal(windows.tileset.showCount, 1);
    assert.equal(windows.tileset.focusCount, 1);
    assert.deepEqual(ready, ['tileset']);

    const choice = await ipcMain.invoke('thestra-studio-close-choice', { sender: tilesetContents }, 'tileset');
    assert.equal(choice, 'cancel');
    assert.equal(dialogCalls.length, 1);
    assert.match(dialogCalls[0].options.title, /Tileset Studio/);
    assert.match(dialogCalls[0].options.message, /closing Tileset Studio/);
    assert.deepEqual(dialogCalls[0].options.buttons, ['Save', 'Discard', 'Cancel']);

    assert.deepEqual(await ipcMain.invoke('thestra-studio-close-surface', { sender: tilesetContents }, 'tileset'), {
        surfaceId: 'tileset', requested: true,
    });
    assert.deepEqual(closeCalls, ['tileset']);
});

test('Tileset commit invalidation fans out to main, Database, and Engine but never carries record values', async () => {
    const ipcMain = fakeIpcMain();
    const sent = { main: [], database: [], engine: [], tileset: [] };
    const windows = {
        main: { webContents: webContents(1, sent.main) },
        database: { webContents: webContents(2, sent.database) },
        engine: { webContents: webContents(3, sent.engine) },
        tileset: { webContents: webContents(4, sent.tileset) },
    };
    const windowManager = {
        get(id) { return windows[id] || null; },
        has() { return true; },
        open() {},
        close() { return true; },
    };
    installStudioIpc({ ipcMain, dialog: { async showMessageBox() { return { response: 2 }; } }, windowManager });

    const result = await ipcMain.invoke(
        'thestra-studio-resource-commit',
        { sender: windows.tileset.webContents },
        { resources: ['tilesets'] }
    );
    assert.deepEqual(result, {
        sourceSurface: 'tileset',
        resources: ['tilesets'],
        deliveredTo: ['main', 'database', 'engine'],
    });
    assert.deepEqual(sent.tileset, []);
    for (const id of ['main', 'database', 'engine']) {
        assert.deepEqual(sent[id], [{
            name: 'thestra-studio-resource-committed',
            payload: { sourceSurface: 'tileset', resources: ['tilesets'] },
        }]);
        assert.equal(Object.prototype.hasOwnProperty.call(sent[id][0].payload, 'record'), false);
        assert.equal(Object.prototype.hasOwnProperty.call(sent[id][0].payload, 'value'), false);
    }
});

test('coordinated Studio shutdown resolves all three secondary editors before main', async () => {
    const order = [];
    const windowManager = {
        has(id) { return ALLOWED_SURFACES.includes(id); },
        async closeAndWait(id) { order.push(id); return true; },
    };
    const studioIpc = {
        requestClose(id, _win, decide) { order.push(id); decide(true); },
    };
    const coordinator = createStudioShutdownCoordinator({
        windowManager,
        studioIpc,
        secondarySurfaces: ALLOWED_SURFACES,
    });

    const result = await new Promise(resolve => coordinator.requestMainClose({ webContents: {} }, resolve));
    assert.equal(result, true);
    assert.deepEqual(order, ['database', 'engine', 'tileset', 'main']);
});

test('Tileset cancellation aborts coordinated shutdown before main close intent', async () => {
    const order = [];
    const windowManager = {
        has(id) { return ALLOWED_SURFACES.includes(id); },
        async closeAndWait(id) {
            order.push(id);
            return id !== 'tileset';
        },
    };
    const studioIpc = {
        requestClose(id, _win, decide) { order.push(id); decide(true); },
    };
    const coordinator = createStudioShutdownCoordinator({
        windowManager,
        studioIpc,
        secondarySurfaces: ALLOWED_SURFACES,
    });

    const result = await new Promise(resolve => coordinator.requestMainClose({ webContents: {} }, resolve));
    assert.equal(result, false);
    assert.deepEqual(order, ['database', 'engine', 'tileset']);
});
