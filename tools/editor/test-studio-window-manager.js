'use strict';

const assert = require('node:assert/strict');
const { EventEmitter } = require('node:events');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');
const {
    StudioWindowManager,
    createJsonWindowStateStore,
} = require('./studio-window-manager');

class FakeWindow extends EventEmitter {
    constructor(options) {
        super();
        this.options = options;
        this.bounds = {
            x: options.x,
            y: options.y,
            width: options.width,
            height: options.height,
        };
        this.maximized = false;
        this.minimized = false;
        this.destroyed = false;
        this.visible = false;
        this.showCount = 0;
        this.focusCount = 0;
        this.restoreCount = 0;
        this.closeCount = 0;
    }

    getBounds() { return { ...this.bounds }; }
    isMaximized() { return this.maximized; }
    maximize() { this.maximized = true; }
    isMinimized() { return this.minimized; }
    restore() { this.minimized = false; this.restoreCount += 1; }
    isDestroyed() { return this.destroyed; }
    isVisible() { return this.visible; }
    show() { this.visible = true; this.showCount += 1; }
    focus() { this.focusCount += 1; }
    close() {
        this.closeCount += 1;
        let prevented = false;
        this.emit('close', { preventDefault() { prevented = true; } });
        if (prevented) return;
        this.destroyed = true;
        this.visible = false;
        this.emit('closed');
    }
}

function makeManager(stateStore) {
    const created = [];
    const manager = new StudioWindowManager({
        createWindow(options) {
            const win = new FakeWindow(options);
            created.push(win);
            return win;
        },
        stateStore,
    });
    return { manager, created };
}

test('open creates one window per registered surface and focuses an existing instance', () => {
    const stateStore = {
        load() { return { width: 800, height: 600, isMaximized: false }; },
        save() {},
    };
    const { manager, created } = makeManager(stateStore);
    manager.register('database', {
        defaultState: { width: 640, height: 480, isMaximized: false },
        buildOptions: state => ({ width: state.width, height: state.height }),
    });

    const first = manager.open('database');
    first.minimized = true;
    const second = manager.open('database');

    assert.equal(first, second);
    assert.equal(created.length, 1);
    assert.equal(first.restoreCount, 1);
    assert.equal(first.showCount, 1);
    assert.equal(first.focusCount, 1);
});

test('autoShow false surfaces stay hidden across repeated opens until renderer readiness', () => {
    const stateStore = {
        load() { return { width: 800, height: 600, isMaximized: false }; },
        save() {},
    };
    const { manager } = makeManager(stateStore);
    manager.register('database', {
        autoShow: false,
        buildOptions: state => ({ width: state.width, height: state.height }),
    });

    const win = manager.open('database');
    win.emit('ready-to-show');
    manager.open('database');
    assert.equal(win.showCount, 0);
    assert.equal(win.focusCount, 0);

    // Simulate the renderer-owned surfaceReady IPC revealing the BrowserWindow.
    win.show();
    manager.open('database');
    assert.equal(win.showCount, 2);
    assert.equal(win.focusCount, 1);
});

test('window lifecycle restores persisted state and saves state on close', () => {
    const saves = [];
    const stateStore = {
        load(surfaceId, defaults) {
            assert.equal(surfaceId, 'database');
            assert.equal(defaults.width, 640);
            return { x: 11, y: 22, width: 900, height: 700, isMaximized: true };
        },
        save(surfaceId, state) { saves.push({ surfaceId, state }); },
    };
    const { manager } = makeManager(stateStore);
    let configured = null;
    manager.register('database', {
        defaultState: { width: 640, height: 480, isMaximized: false },
        buildOptions: state => ({ x: state.x, y: state.y, width: state.width, height: state.height }),
        configure(win, state) { configured = { win, state }; },
    });

    const win = manager.open('database');
    assert.equal(win.maximized, true);
    assert.equal(win.options.width, 900);
    assert.equal(configured.win, win);

    win.emit('ready-to-show');
    assert.equal(win.showCount, 1);

    win.bounds = { x: 31, y: 42, width: 1000, height: 800 };
    win.maximized = false;
    win.close();

    assert.deepEqual(saves, [{
        surfaceId: 'database',
        state: { x: 31, y: 42, width: 1000, height: 800, isMaximized: false },
    }]);
    assert.equal(manager.has('database'), false);
});

test('state store keeps main legacy path while giving each future surface its own file', () => {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'thestra-window-state-'));
    const errors = [];
    const store = createJsonWindowStateStore({
        fs,
        userDataDir: dir,
        logger: { error(...args) { errors.push(args); } },
    });

    store.save('main', { width: 1200, height: 800, isMaximized: false });
    store.save('database', { width: 900, height: 700, isMaximized: true });

    assert.equal(store.pathFor('main'), path.join(dir, 'window-state.json'));
    assert.equal(store.pathFor('database'), path.join(dir, 'window-state-database.json'));
    assert.deepEqual(store.load('main', { width: 1 }), {
        width: 1200,
        height: 800,
        isMaximized: false,
    });
    assert.deepEqual(store.load('database', { width: 1 }), {
        width: 900,
        height: 700,
        isMaximized: true,
    });
    assert.deepEqual(errors, []);
});

test('closed windows are removed so the same surface can be created again', () => {
    const stateStore = {
        load() { return { width: 800, height: 600, isMaximized: false }; },
        save() {},
    };
    const { manager, created } = makeManager(stateStore);
    manager.register('animation', {
        buildOptions: state => ({ width: state.width, height: state.height }),
    });

    const first = manager.open('animation');
    first.close();
    const second = manager.open('animation');

    assert.notEqual(first, second);
    assert.equal(created.length, 2);
});

test('closeAll requests closure of each live Studio-owned window', () => {
    const stateStore = {
        load() { return { width: 800, height: 600, isMaximized: false }; },
        save() {},
    };
    const { manager } = makeManager(stateStore);
    for (const id of ['main', 'database']) {
        manager.register(id, {
            buildOptions: state => ({ width: state.width, height: state.height }),
        });
        manager.open(id);
    }

    const main = manager.get('main');
    const database = manager.get('database');
    manager.closeAll();

    assert.equal(main.closeCount, 1);
    assert.equal(database.closeCount, 1);
    assert.equal(manager.has('main'), false);
    assert.equal(manager.has('database'), false);
});

test('requestClose can defer native destruction until the surface approves', () => {
    const saves = [];
    const stateStore = {
        load() { return { x: 1, y: 2, width: 800, height: 600, isMaximized: false }; },
        save(surfaceId, state) { saves.push({ surfaceId, state }); },
    };
    const { manager } = makeManager(stateStore);
    let decide = null;
    let requests = 0;
    manager.register('database', {
        buildOptions: state => ({ x: state.x, y: state.y, width: state.width, height: state.height }),
        requestClose(_win, closeDecision) {
            requests += 1;
            decide = closeDecision;
        },
    });

    const win = manager.open('database');
    assert.equal(manager.close('database'), true);
    assert.equal(requests, 1);
    assert.equal(win.destroyed, false);
    assert.equal(saves.length, 0);

    decide(true);
    assert.equal(win.destroyed, true);
    assert.equal(manager.has('database'), false);
    assert.equal(win.closeCount, 2);
    assert.equal(saves.length, 1);
});

test('closeAndWait resolves false on cancel without destroying or persisting the window', async () => {
    const saves = [];
    const stateStore = {
        load() { return { x: 1, y: 2, width: 800, height: 600, isMaximized: false }; },
        save(surfaceId, state) { saves.push({ surfaceId, state }); },
    };
    const { manager } = makeManager(stateStore);
    let decide = null;
    manager.register('database', {
        buildOptions: state => ({ x: state.x, y: state.y, width: state.width, height: state.height }),
        requestClose(_win, closeDecision) { decide = closeDecision; },
    });

    const win = manager.open('database');
    const outcome = manager.closeAndWait('database');
    assert.equal(win.destroyed, false);
    decide(false);

    assert.equal(await outcome, false);
    assert.equal(win.destroyed, false);
    assert.equal(manager.has('database'), true);
    assert.deepEqual(saves, []);
});

test('closeAndWait resolves true only after an approved BrowserWindow actually closes', async () => {
    const stateStore = {
        load() { return { x: 1, y: 2, width: 800, height: 600, isMaximized: false }; },
        save() {},
    };
    const { manager } = makeManager(stateStore);
    let decide = null;
    manager.register('database', {
        buildOptions: state => ({ x: state.x, y: state.y, width: state.width, height: state.height }),
        requestClose(_win, closeDecision) { decide = closeDecision; },
    });

    const win = manager.open('database');
    const outcome = manager.closeAndWait('database');
    decide(true);

    assert.equal(await outcome, true);
    assert.equal(win.destroyed, true);
    assert.equal(manager.has('database'), false);
});
