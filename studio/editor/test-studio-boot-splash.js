'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const test = require('node:test');
const { createStudioBootSplash } = require('./studio-boot-splash');

const EDITOR_HTML = fs.readFileSync(path.join(__dirname, 'index.html'), 'utf8');
const SPLASH_HTML = fs.readFileSync(path.join(__dirname, 'boot-splash.html'), 'utf8');
const INLINE_BOOT = EDITOR_HTML.match(/<script>\s*([\s\S]*?)<\/script>/);
assert.ok(INLINE_BOOT, 'index.html must keep its early boot coordinator inline');

function createBoot(surface = 'main') {
    const events = [];
    const windowListeners = new Map();
    const studio = {
        bootProgress(payload) { events.push({ type: 'progress', payload }); return Promise.resolve(); },
        bootReady() { events.push({ type: 'ready' }); return Promise.resolve(); },
        bootFailed(message) { events.push({ type: 'failed', message }); return Promise.resolve(); },
    };
    const window = {
        thestraStudio: studio,
        location: { search: surface === 'main' ? '' : `?surface=${surface}` },
        addEventListener(name, listener) {
            const list = windowListeners.get(name) || [];
            list.push(listener);
            windowListeners.set(name, list);
        },
        dispatchEvent(event) {
            for (const listener of windowListeners.get(event.type) || []) listener(event);
        },
    };
    const document = {
        body: { dataset: { studioBoot: 'loading' } },
        addEventListener() {},
    };
    vm.runInNewContext(INLINE_BOOT[1], {
        window,
        document,
        URLSearchParams,
        CustomEvent: class CustomEvent { constructor(type, options = {}) { this.type = type; this.detail = options.detail; } },
        console,
    });
    return { boot: window.ThestraBoot, document, events, window };
}

function makeController() {
    const handlers = new Map();
    const ipcMain = { handle(name, callback) { handlers.set(name, callback); } };
    const app = { quitCount: 0, quit() { this.quitCount += 1; } };
    const clipboard = { text: '', writeText(text) { this.text = text; } };
    const windows = [];
    class FakeWindow {
        constructor(options) {
            this.options = options;
            this.handlers = new Map();
            this.onceHandlers = new Map();
            this.sent = [];
            this.closed = false;
            this.showCount = 0;
            this.focusCount = 0;
            this.webContents = {
                on() {},
                send: (name, payload) => this.sent.push({ name, payload }),
                reload: () => { this.reloadCount = (this.reloadCount || 0) + 1; },
            };
            windows.push(this);
        }
        once(name, callback) { this.onceHandlers.set(name, callback); }
        on(name, callback) { this.handlers.set(name, callback); }
        emit(name) {
            if (this.onceHandlers.has(name)) {
                const callback = this.onceHandlers.get(name);
                this.onceHandlers.delete(name);
                callback();
            }
            if (this.handlers.has(name)) this.handlers.get(name)();
        }
        loadFile(file) { this.loadedFile = file; }
        show() { this.showCount += 1; this.emit('show'); }
        focus() { this.focusCount += 1; }
        close() { this.closed = true; this.handlers.get('closed')?.(); }
        isDestroyed() { return this.closed; }
    }
    const controller = createStudioBootSplash({
        app, BrowserWindow: FakeWindow, clipboard, ipcMain,
        productName: 'Thestra Studio',
        icon: 'icon.ico', htmlPath: 'boot-splash.html', preloadPath: 'splash-preload.js',
    });
    const splash = controller.open();
    const main = {
        events: new Map(),
        showCount: 0,
        focusCount: 0,
        webContents: {
            on(name, callback) { main.events.set(name, callback); },
            reload() { this.reloadCount = (this.reloadCount || 0) + 1; },
        },
        show() { this.showCount += 1; },
        focus() { this.focusCount += 1; },
    };
    controller.attachMain(main);
    async function invoke(name, sender, ...args) {
        return handlers.get(name)({ sender }, ...args);
    }
    return { app, clipboard, controller, invoke, main, splash, windows };
}

test('main splash waits for database and first workspace, then signals the native host', () => {
    const f = createBoot();
    f.boot.setStudioName('Thestra Studio');
    f.boot.setProject('Studio Editor Fixture');
    f.boot.markDatabaseReady(true);
    assert.equal(f.boot.state, 'loading');
    assert.equal(f.document.body.dataset.studioBoot, 'loading');

    f.window.dispatchEvent({ type: 'thestra-map-workspace-progress', detail: { status: 'Map · Persp · compiling' } });
    assert.equal(f.events.at(-1).payload.status, 'Map · Persp · compiling');
    f.window.dispatchEvent({ type: 'thestra-map-workspace-ready', detail: { status: 'Map · Persp · runtime geometry' } });
    assert.equal(f.boot.state, 'ready');
    assert.equal(f.document.body.dataset.studioBoot, 'ready');
    assert.equal(f.events.at(-1).type, 'ready');
});

test('secondary editor surfaces finish on database readiness without waiting for Map workspace', () => {
    const f = createBoot('database');
    f.boot.markDatabaseReady(true);
    assert.equal(f.boot.state, 'ready');
    assert.equal(f.document.body.dataset.studioBoot, 'ready');
    assert.deepEqual(f.events, [], 'secondary surfaces do not message the main startup splash');
});

test('startup failures are sent to the splash host with useful details', () => {
    const f = createBoot();
    f.boot.fail('Three.js vendor files are missing.');
    assert.equal(f.boot.state, 'error');
    assert.equal(f.document.body.dataset.studioBoot, 'error');
    assert.deepEqual(f.events.at(-1), { type: 'failed', message: 'Three.js vendor files are missing.' });
    assert.doesNotMatch(EDITOR_HTML, /id="studio-boot-splash"/,
        'the editor renderer must not implement the native splash as a full-window overlay');
});

test('native splash is a compact, centered, independent BrowserWindow', async () => {
    const f = makeController();
    assert.equal(f.windows.length, 1);
    assert.equal(f.splash.options.width, 840);
    assert.equal(f.splash.options.height, 502);
    assert.equal(f.splash.options.center, true);
    assert.equal(f.splash.options.fullscreenable, false);
    assert.equal(f.splash.options.frame, false);
    assert.equal(f.splash.options.show, false);
    assert.equal(f.splash.loadedFile, 'boot-splash.html');
    assert.match(SPLASH_HTML, /studio-boot-splash\.png/);

    let shown = false;
    const shownPromise = f.controller.whenShown().then(() => { shown = true; });
    await Promise.resolve();
    assert.equal(shown, false, 'the main editor must not start until the splash can paint');
    f.splash.emit('ready-to-show');
    await shownPromise;
    assert.equal(shown, true);
    assert.equal(f.controller.isShown(), true);
    assert.equal(f.splash.showCount, 1);
    assert.equal(f.main.showCount, 0);

    assert.deepEqual(await f.invoke('thestra-boot-splash-progress', f.main.webContents, {
        studioName: 'Thestra Studio', projectName: 'Test Project', status: 'Loading map workspace…',
    }), { state: 'loading' });
    assert.deepEqual(f.splash.sent.at(-1), {
        name: 'thestra-boot-splash-state',
        payload: { state: 'loading', studioName: 'Thestra Studio', projectName: 'Test Project', status: 'Loading map workspace…', error: '' },
    });

    await f.invoke('thestra-boot-splash-ready', f.main.webContents);
    assert.equal(f.splash.closed, true);
    assert.equal(f.main.showCount, 1);
    assert.equal(f.main.focusCount, 1);
});

test('closing the splash before it appears quits instead of opening a hidden editor', async () => {
    const f = makeController();
    const shown = f.controller.whenShown();
    f.splash.close();
    assert.equal(await shown, null);
    assert.equal(f.app.quitCount, 1);
});

test('splash retains startup errors, supports retry and copy, and rejects unowned renderers', async () => {
    const f = makeController();
    await f.invoke('thestra-boot-splash-failed', f.main.webContents, 'Three.js vendor files are missing.');
    const error = await f.invoke('thestra-boot-splash-get-state', f.splash.webContents);
    assert.equal(error.state, 'error');
    assert.equal(error.error, 'Three.js vendor files are missing.');
    assert.deepEqual(await f.invoke('thestra-boot-splash-copy-error', f.splash.webContents), { copied: true });
    assert.equal(f.clipboard.text, error.error);
    assert.deepEqual(await f.invoke('thestra-boot-splash-reload', f.splash.webContents), { reloading: true });
    assert.equal(f.main.webContents.reloadCount, 1);
    const retry = await f.invoke('thestra-boot-splash-get-state', f.splash.webContents);
    assert.equal(retry.state, 'loading');
    assert.equal(retry.error, '');

    await assert.rejects(
        f.invoke('thestra-boot-splash-ready', {}),
        /does not own the main window/
    );
    await assert.rejects(
        f.invoke('thestra-boot-splash-quit', {}),
        /does not own the splash window/
    );
});
