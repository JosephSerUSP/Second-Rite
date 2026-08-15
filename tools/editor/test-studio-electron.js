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
    const webContents = {
        id: 17,
        isDestroyed: () => false,
        send(name, payload) { sent.push({ name, payload }); },
    };
    const mainWebContents = { id: 1 };
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
        onSurfaceReady(surfaceId, owner) { ready.push({ surfaceId, owner }); },
    });
    return {
        ipcMain,
        bridge,
        win,
        webContents,
        mainWebContents,
        sent,
        opens,
        closes,
        ready,
        dialogCalls,
    };
}

test('surface IPC opens and closes only registered Studio surfaces', async () => {
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

test('close choice is native, three-way, and restricted to the owning surface renderer', async () => {
    const f = fixture();
    const choice = await f.ipcMain.invoke('thestra-studio-close-choice', { sender: f.webContents }, 'database');
    assert.equal(choice, 'discard');
    assert.equal(f.dialogCalls.length, 1);
    assert.deepEqual(f.dialogCalls[0].options.buttons, ['Save', 'Discard', 'Cancel']);

    await assert.rejects(
        f.ipcMain.invoke('thestra-studio-close-choice', { sender: { id: 99 } }, 'database'),
        /does not own Studio surface/
    );
});

test('native close request completes only after the owning renderer approves', () => {
    const f = fixture();
    let approvals = 0;
    f.bridge.requestClose('database', f.win, () => { approvals += 1; });

    assert.deepEqual(f.sent, [{
        name: 'thestra-studio-close-request',
        payload: { surfaceId: 'database' },
    }]);
    assert.equal(approvals, 0);

    f.ipcMain.emit('thestra-studio-close-response', { sender: f.webContents }, {
        surfaceId: 'database', allow: false,
    });
    assert.equal(approvals, 0);

    f.bridge.requestClose('database', f.win, () => { approvals += 1; });
    f.ipcMain.emit('thestra-studio-close-response', { sender: f.webContents }, {
        surfaceId: 'database', allow: true,
    });
    assert.equal(approvals, 1);
});

test('repeated native close requests share the first pending close decision', () => {
    const f = fixture();
    let firstApprovals = 0;
    let secondApprovals = 0;

    f.bridge.requestClose('database', f.win, () => { firstApprovals += 1; });
    f.bridge.requestClose('database', f.win, () => { secondApprovals += 1; });

    assert.equal(f.sent.length, 1, 'only one renderer close request should be in flight');
    f.ipcMain.emit('thestra-studio-close-response', { sender: f.webContents }, {
        surfaceId: 'database', allow: true,
    });
    assert.equal(firstApprovals, 1);
    assert.equal(secondApprovals, 0);
});
