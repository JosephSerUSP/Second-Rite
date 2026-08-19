'use strict';

const assert = require('node:assert/strict');
const { EventEmitter } = require('node:events');
const test = require('node:test');
const {
    SURFACES,
    EXCLUSIVE_NATIVE_SURFACE_IDS,
} = require('./studio-surface-registry');
const { StudioWindowManager } = require('./studio-window-manager');

class FakeWindow extends EventEmitter {
    constructor(options) {
        super();
        this.options = options;
        this.destroyed = false;
        this.visible = false;
    }

    getBounds() {
        return {
            x: this.options.x,
            y: this.options.y,
            width: this.options.width,
            height: this.options.height,
        };
    }

    isMaximized() { return false; }
    isDestroyed() { return this.destroyed; }
    isVisible() { return this.visible; }
    isMinimized() { return false; }
    show() { this.visible = true; }
    focus() {}
    close() {
        let prevented = false;
        this.emit('close', { preventDefault() { prevented = true; } });
        if (prevented) return;
        this.destroyed = true;
        this.emit('closed');
    }
}

function managerFixture() {
    const manager = new StudioWindowManager({
        createWindow(options) { return new FakeWindow(options); },
        stateStore: {
            load(_surfaceId, defaults) { return { ...(defaults || {}) }; },
            save() {},
        },
    });

    for (const id of ['main', 'database', 'engine', 'tileset']) {
        manager.register(id, {
            defaultState: { width: 800, height: 600, isMaximized: false },
            buildOptions: state => ({ width: state.width, height: state.height }),
        });
    }
    return manager;
}

test('EditorSurface registry declares project-level exclusivity independently from host choice', () => {
    assert.equal(SURFACES.main.interactionPolicy, 'workspace-root');
    assert.equal(SURFACES.database.interactionPolicy, 'exclusive');
    assert.equal(SURFACES.engine.interactionPolicy, 'exclusive');
    assert.equal(SURFACES.tileset.interactionPolicy, 'concurrent');
    assert.deepEqual(EXCLUSIVE_NATIVE_SURFACE_IDS, ['database', 'engine']);
});

test('exclusive native editors are Electron modal children of the main workspace', () => {
    const manager = managerFixture();
    const main = manager.open('main');

    const database = manager.open('database');
    assert.equal(database.options.parent, main);
    assert.equal(database.options.modal, true);

    database.close();
    const engine = manager.open('engine');
    assert.equal(engine.options.parent, main);
    assert.equal(engine.options.modal, true);
});

test('concurrent native editors remain independent top-level windows', () => {
    const manager = managerFixture();
    manager.open('main');

    const tileset = manager.open('tileset');
    assert.equal(tileset.options.parent, undefined);
    assert.equal(tileset.options.modal, undefined);
});
