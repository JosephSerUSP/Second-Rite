'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');
const { installStudioIpc } = require('./studio-electron');

function fakeIpcMain() {
    const handlers = new Map();
    const listeners = new Map();
    return {
        handle(name, fn) { handlers.set(name, fn); },
        on(name, fn) { listeners.set(name, fn); },
        async invoke(name, event, ...args) {
            return handlers.get(name)(event, ...args);
        },
        emit(name, event, ...args) {
            return listeners.get(name)(event, ...args);
        },
    };
}

function fixture() {
    const ipcMain = fakeIpcMain();
    const sent = [];
    const mainSent = [];
    const webContents = {
        id: 17,
        isDestroyed: () => false,
        send(name, payload) { sent.push({ name, payload }); },
    };
    const mainWebContents = {
        id: 1,
        isDestroyed: () => false,
        send(name, payload) { mainSent.push({ name, payload }); },
    };
    const win = {
        webContents,
        showCount: 0,
        focusCount: 0,
        show() { this.showCount += 1; },
        focus() { this.focusCount += 1; },
    };
    const mainWin = { webContents: mainWebContents };
    const opens = [];
    const closes = [];
    const ready = [];
    let databaseOpen = false;
    const windowManager = {
        get(id) {
            if (id === 'main') return mainWin;
            if (id === 'database') return win;
            return null;
        },
        has(id) { return id === 'database' && databaseOpen; },
        open(id) {
            opens.push(id);
            if (id === 'database') databaseOpen = true;
            return win;
        },
        close(id) {
            closes.push(id);
            if (id === 'database') databaseOpen = false;
            return id === 'database';
        },
    };
    const dialogCalls = [];
    const dialog = {
        async showMessageBox(owner, options) {
            dialogCalls.push({ owner, options });
            return { response: 1 };
        },
    };
    const bridge = installStudioIpc({
        ipcMain,
        dialog,
        windowManager,
        allowedResources: ['maps', 'units'],
        onSurfaceReady(surfaceId, owner) { ready.push({ surfaceId, owner }); },
    });
    return {
        ipcMain,
        bridge,
        win,
        mainWin,
        webContents,
        mainWebContents,
        sent,
        mainSent,
        opens,
        closes,
        ready,
        dialogCalls,
    };
}

test('surface IPC opens and closes only registered secondary Studio surfaces', async () => {
    const f = fixture();
    assert.deepEqual(await f.ipcMain.invoke('thestra-studio-open-surface', { sender: {} }, 'database'), {
        surfaceId: 'database',
    });
    assert.deepEqual(await f.ipcMain.invoke('thestra-studio-close-surface', { sender: {} }, 'database'), {
        surfaceId: 'database', requested: true,
    });
    assert.deepEqual(f.opens, ['database']);
    assert.deepEqual(f.closes, ['database']);
    await assert.rejects(
        f.ipcMain.invoke('thestra-studio-open-surface', { sender: {} }, 'main'),
        /Unknown Studio surface/
    );
    await assert.rejects(
        f.ipcMain.invoke('thestra-studio-open-surface', { sender: {} }, 'arbitrary-window'),
        /Unknown Studio surface/
    );
});

test('surface ready can show/focus only the BrowserWindow owned by that renderer', async () => {
    const f = fixture();
    assert.deepEqual(await f.ipcMain.invoke(
        'thestra-studio-surface-ready',
        { sender: f.webContents },
        'database'
    ), { surfaceId: 'database', shown: true });
    assert.equal(f.win.showCount, 1);
    assert.equal(f.win.focusCount, 1);
    assert.deepEqual(f.ready, [{ surfaceId: 'database', owner: f.win }]);

    await assert.rejects(
        f.ipcMain.invoke('thestra-studio-surface-ready', { sender: { id: 99 } }, 'database'),
        /does not own Studio surface/
    );
    assert.equal(f.ready.length, 1, 'unowned readiness must never reach the observer');
});

test('committed resource invalidations go only to sibling Studio renderers', async () => {
    const f = fixture();

    const fromDatabase = await f.ipcMain.invoke(
        'thestra-studio-resource-commit',
        { sender: f.webContents },
        { resources: ['units', 'units'] }
    );
    assert.deepEqual(fromDatabase, {
        sourceSurface: 'database',
        resources: ['units'],
        deliveredTo: ['main'],
    });
    assert.deepEqual(f.sent, [], 'sender must not receive its own invalidation');
    assert.deepEqual(f.mainSent, [{
        name: 'thestra-studio-resource-committed',
        payload: { sourceSurface: 'database', resources: ['units'] },
    }]);

    const fromMain = await f.ipcMain.invoke(
        'thestra-studio-resource-commit',
        { sender: f.mainWebContents },
        { resources: ['maps'] }
    );
    assert.deepEqual(fromMain, {
        sourceSurface: 'main',
        resources: ['maps'],
        deliveredTo: ['database'],
    });
    assert.deepEqual(f.sent, [{
        name: 'thestra-studio-resource-committed',
        payload: { sourceSurface: 'main', resources: ['maps'] },
    }]);
});

test('resource commit IPC rejects unowned senders and unknown resource names', async () => {
    const f = fixture();
    await assert.rejects(
        f.ipcMain.invoke('thestra-studio-resource-commit', { sender: { id: 99 } }, { resources: ['units'] }),
        /does not own a Studio surface/
    );
    await assert.rejects(
        f.ipcMain.invoke('thestra-studio-resource-commit', { sender: f.webContents }, { resources: ['secrets'] }),
        /Unknown authored resource/
    );
    await assert.rejects(
        f.ipcMain.invoke('thestra-studio-resource-commit', { sender: f.webContents }, { resources: [] }),
        /bounded resource list/
    );
});

test('Project switching is blocked while a secondary native surface is open', async () => {
    const f = fixture();
    assert.deepEqual(await f.ipcMain.invoke(
        'thestra-studio-project-switch-ready',
        { sender: f.mainWebContents }
    ), { ready: true, blockers: [] });

    await f.ipcMain.invoke('thestra-studio-open-surface', { sender: f.mainWebContents }, 'database');
    assert.deepEqual(await f.ipcMain.invoke(
        'thestra-studio-project-switch-ready',
        { sender: f.mainWebContents }
    ), { ready: false, blockers: ['database'] });

    await assert.rejects(
        f.ipcMain.invoke('thestra-studio-project-switch-ready', { sender: { id: 99 } }),
        /does not own Studio surface: main/
    );
});

test('close choice is native, three-way, surface-specific, and owner-restricted', async () => {
    const f = fixture();
    const databaseChoice = await f.ipcMain.invoke(
        'thestra-studio-close-choice', { sender: f.webContents }, 'database'
    );
    const mainChoice = await f.ipcMain.invoke(
        'thestra-studio-close-choice', { sender: f.mainWebContents }, 'main'
    );
    assert.equal(databaseChoice, 'discard');
    assert.equal(mainChoice, 'discard');
    assert.equal(f.dialogCalls.length, 2);
    assert.deepEqual(f.dialogCalls[0].options.buttons, ['Save', 'Discard', 'Cancel']);
    assert.match(f.dialogCalls[0].options.title, /Database/);
    assert.match(f.dialogCalls[1].options.title, /Project/);

    await assert.rejects(
        f.ipcMain.invoke('thestra-studio-close-choice', { sender: { id: 99 } }, 'database'),
        /does not own Studio surface/
    );
});

test('native close request reports both cancellation and approval from the owning renderer', () => {
    const f = fixture();
    const decisions = [];
    f.bridge.requestClose('database', f.win, allow => { decisions.push(allow); });

    assert.deepEqual(f.sent, [{
        name: 'thestra-studio-close-request',
        payload: { surfaceId: 'database' },
    }]);
    assert.deepEqual(decisions, []);

    f.ipcMain.emit('thestra-studio-close-response', { sender: f.webContents }, {
        surfaceId: 'database', allow: false,
    });
    assert.deepEqual(decisions, [false]);

    f.bridge.requestClose('database', f.win, allow => { decisions.push(allow); });
    f.ipcMain.emit('thestra-studio-close-response', { sender: f.webContents }, {
        surfaceId: 'database', allow: true,
    });
    assert.deepEqual(decisions, [false, true]);
});

test('main workspace participates in the same bounded close-response channel', () => {
    const f = fixture();
    const decisions = [];
    f.bridge.requestClose('main', f.mainWin, allow => { decisions.push(allow); });
    assert.deepEqual(f.mainSent, [{
        name: 'thestra-studio-close-request',
        payload: { surfaceId: 'main' },
    }]);

    f.ipcMain.emit('thestra-studio-close-response', { sender: f.mainWebContents }, {
        surfaceId: 'main', allow: true,
    });
    assert.deepEqual(decisions, [true]);
});

test('repeated native close requests share the first pending close decision', () => {
    const f = fixture();
    const first = [];
    const second = [];

    f.bridge.requestClose('database', f.win, allow => { first.push(allow); });
    f.bridge.requestClose('database', f.win, allow => { second.push(allow); });

    assert.equal(f.sent.length, 1, 'only one renderer close request should be in flight');
    f.ipcMain.emit('thestra-studio-close-response', { sender: f.webContents }, {
        surfaceId: 'database', allow: true,
    });
    assert.deepEqual(first, [true]);
    assert.deepEqual(second, []);
});
