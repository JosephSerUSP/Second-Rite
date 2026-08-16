'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');
const { installStudioIpc } = require('./studio-electron');

function createIpcHarness() {
    const handlers = new Map();
    const listeners = new Map();
    const ipcMain = {
        handle(name, handler) { handlers.set(name, handler); },
        on(name, handler) { listeners.set(name, handler); },
    };
    return { handlers, ipcMain, listeners };
}

function fakeWebContents(id) {
    const sent = [];
    return {
        id,
        sent,
        isDestroyed: () => false,
        send(channel, payload) { sent.push({ channel, payload }); },
    };
}

function fakeWindowManager() {
    const mainContents = fakeWebContents(1);
    const databaseContents = fakeWebContents(2);
    const windows = new Map([
        ['main', { webContents: mainContents }],
        ['database', { webContents: databaseContents }],
    ]);
    return {
        mainContents,
        databaseContents,
        manager: {
            get(id) { return windows.get(id) || null; },
            has(id) { return windows.has(id); },
            open() {},
            close() { return true; },
        },
    };
}

test('external semantic resource invalidation uses the same bounded IPC event without values', () => {
    const ipc = createIpcHarness();
    const windows = fakeWindowManager();
    const studio = installStudioIpc({
        ipcMain: ipc.ipcMain,
        dialog: { showMessageBox: async () => ({ response: 2 }) },
        windowManager: windows.manager,
        allowedSurfaces: ['database'],
        allowedResources: ['system', 'units'],
    });

    const result = studio.broadcastResourceCommit('external', ['units', 'system']);
    assert.deepEqual(result, {
        sourceSurface: 'external',
        resources: ['units', 'system'],
        deliveredTo: ['main', 'database'],
    });
    for (const contents of [windows.mainContents, windows.databaseContents]) {
        assert.equal(contents.sent.length, 1);
        assert.equal(contents.sent[0].channel, 'thestra-studio-resource-committed');
        assert.deepEqual(contents.sent[0].payload, {
            sourceSurface: 'external',
            resources: ['units', 'system'],
        });
        assert.equal(Object.prototype.hasOwnProperty.call(contents.sent[0].payload, 'value'), false);
        assert.equal(Object.prototype.hasOwnProperty.call(contents.sent[0].payload, 'data'), false);
        assert.equal(Object.prototype.hasOwnProperty.call(contents.sent[0].payload, 'versions'), false,
            'version correlation metadata never broadcasts to sibling renderers');
    }
});

test('external asset invalidation stays a separate identity-only IPC class', () => {
    const ipc = createIpcHarness();
    const windows = fakeWindowManager();
    const studio = installStudioIpc({
        ipcMain: ipc.ipcMain,
        dialog: { showMessageBox: async () => ({ response: 2 }) },
        windowManager: windows.manager,
        allowedSurfaces: ['database'],
        allowedResources: ['system'],
    });

    const result = studio.broadcastAssetInvalidation([
        'sprites/pixie.png',
        'sprites/pixie.png',
        'models/prop.obj',
    ]);
    assert.deepEqual(result.assets, ['models/prop.obj', 'sprites/pixie.png']);
    assert.deepEqual(result.deliveredTo, ['main', 'database']);
    for (const contents of [windows.mainContents, windows.databaseContents]) {
        assert.equal(contents.sent[0].channel, 'thestra-studio-assets-invalidated');
        assert.deepEqual(contents.sent[0].payload, {
            sourceSurface: 'external',
            assets: ['models/prop.obj', 'sprites/pixie.png'],
        });
    }
});

test('renderer commit arms watcher correlation before identity-only sibling broadcast', async () => {
    const ipc = createIpcHarness();
    const windows = fakeWindowManager();
    const committed = [];
    installStudioIpc({
        ipcMain: ipc.ipcMain,
        dialog: { showMessageBox: async () => ({ response: 2 }) },
        windowManager: windows.manager,
        allowedSurfaces: ['database'],
        allowedResources: ['system'],
        onResourceCommit: (commit, sourceSurface) => committed.push({ commit, sourceSurface }),
    });

    const handler = ipc.handlers.get('thestra-studio-resource-commit');
    const result = await handler({ sender: windows.mainContents }, {
        resources: ['system'],
        versions: { system: 'sha256-system-v2' },
    });
    assert.deepEqual(committed, [{
        commit: { resources: ['system'], versions: { system: 'sha256-system-v2' } },
        sourceSurface: 'main',
    }]);
    assert.deepEqual(result.deliveredTo, ['database']);
    assert.equal(windows.mainContents.sent.length, 0, 'saving renderer is not echoed');
    assert.deepEqual(windows.databaseContents.sent[0].payload, {
        sourceSurface: 'main',
        resources: ['system'],
    });
});

test('commit version metadata is bounded to the committed resource set', async () => {
    const ipc = createIpcHarness();
    const windows = fakeWindowManager();
    installStudioIpc({
        ipcMain: ipc.ipcMain,
        dialog: { showMessageBox: async () => ({ response: 2 }) },
        windowManager: windows.manager,
        allowedSurfaces: ['database'],
        allowedResources: ['system', 'units'],
    });

    const handler = ipc.handlers.get('thestra-studio-resource-commit');
    await assert.rejects(() => handler({ sender: windows.mainContents }, {
        resources: ['system'],
        versions: { units: 'not-part-of-this-commit' },
    }), /uncommitted resource/);
    await assert.rejects(() => handler({ sender: windows.mainContents }, {
        resources: ['system'],
        versions: { system: '' },
    }), /non-empty string/);
});
