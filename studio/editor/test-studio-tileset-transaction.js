'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, 'js', 'tileset-editor.js'), 'utf8');

function classList() {
    const values = new Set();
    return {
        add(value) { values.add(value); },
        remove(value) { values.delete(value); },
        toggle(value, enabled) { if (enabled) values.add(value); else values.delete(value); },
        contains(value) { return values.has(value); },
    };
}

function makeElement(id) {
    return {
        id,
        style: {},
        dataset: {},
        classList: classList(),
        value: '',
        checked: false,
        disabled: false,
        innerHTML: '',
        textContent: '',
        width: 128,
        height: 128,
        children: [],
        appendChild(child) { this.children.push(child); return child; },
        addEventListener() {},
        removeAttribute(name) { delete this[name]; },
        setAttribute(name, value) { this[name] = value; },
        getBoundingClientRect() { return { left: 0, top: 0, width: this.width, height: this.height }; },
        getContext() {
            return {
                clearRect() {}, drawImage() {}, fillRect() {}, fillText() {}, strokeRect() {},
                beginPath() {}, moveTo() {}, lineTo() {}, stroke() {},
                set imageSmoothingEnabled(_value) {}, set fillStyle(_value) {},
                set strokeStyle(_value) {}, set lineWidth(_value) {}, set font(_value) {},
            };
        },
    };
}

function makeContext(options = {}) {
    const elements = new Map();
    const el = id => {
        if (!elements.has(id)) elements.set(id, makeElement(id));
        return elements.get(id);
    };
    el('ts-select-tileset').value = 'dungeon_default';
    el('ts-select-texture').value = 'assets/tilesets/template_tileset.png';
    el('ts-tileset-name').value = 'Dungeon Default';

    let version = 'v1';
    let stale = false;
    let confirmResult = options.confirmResult !== false;
    const committed = [];
    const toasts = [];
    const records = {
        dungeon_default: {
            id: 'dungeon_default', name: 'Dungeon Default',
            texture: 'assets/tilesets/template_tileset.png', tileWidth: 64, tileHeight: 64,
            base: { walls: [], floors: [], ceilings: [] }, doors: [], features: [],
        },
        castle: {
            id: 'castle', name: 'Castle', texture: 'assets/tilesets/template_tileset.png',
            tileWidth: 64, tileHeight: 64,
            base: { walls: [], floors: [], ceilings: [] }, doors: [], features: [],
        },
    };

    function listedRecords() {
        return Object.values(records).map(record => ({ ...JSON.parse(JSON.stringify(record)), _storageVersion: version }));
    }

    const context = {
        console,
        JSON,
        Math,
        Date,
        Number,
        parseInt,
        parseFloat,
        isNaN,
        prompt: () => null,
        confirmDiscard: () => confirmResult,
        showToast(message) { toasts.push(message); },
        Image: class {
            constructor() { this.width = 128; this.height = 128; this.onload = null; this.onerror = null; }
            set src(value) { this._src = value; }
            get src() { return this._src; }
        },
        fetch: async (url, init) => {
            if (url === '/api/tilesets' && (!init || !init.method)) {
                return { ok: true, status: 200, json: async () => ({ tilesets: listedRecords(), textures: ['template_tileset.png'] }) };
            }
            if (url === '/api/tilesets/save' && init && init.method === 'POST') {
                const record = JSON.parse(init.body);
                if (stale) {
                    return { ok: false, status: 409, json: async () => ({ success: false, stale: true, message: 'stale' }) };
                }
                const exists = Object.prototype.hasOwnProperty.call(records, record.id);
                if (exists && record._storageVersion !== version) {
                    return { ok: false, status: 409, json: async () => ({ success: false, stale: true, message: 'stale' }) };
                }
                const stored = JSON.parse(JSON.stringify(record));
                delete stored._storageVersion;
                records[record.id] = stored;
                version = version === 'v1' ? 'v2' : 'v3';
                return { ok: true, status: 200, json: async () => ({ success: true, version }) };
            }
            throw new Error(`unexpected fetch ${url}`);
        },
        document: {
            getElementById(id) { return el(id); },
            createElement(tag) { return makeElement(tag); },
        },
        window: {
            addEventListener() {},
            thestraSurfaceKind: options.surfaceKind,
            thestraStudio: options.surfaceKind === 'tileset' ? {
                chooseCloseAction: async () => options.choice || 'cancel',
                announceResourceCommit: async resources => { committed.push(resources); },
            } : {
                announceResourceCommit: async resources => { committed.push(resources); },
            },
        },
    };
    context.window.window = context.window;
    vm.createContext(context);
    vm.runInContext(source, context, { filename: 'tileset-editor.js' });

    return {
        context,
        el,
        committed,
        toasts,
        setStale(value) { stale = value; },
        setConfirm(value) { confirmResult = value; },
        version: () => version,
        records,
    };
}

test('Tileset Studio baseline is clean, form divergence is dirty, and discard restores the record', async () => {
    const f = makeContext();
    await f.context.window.openTilesetStudioModal();
    const tx = f.context.window.thestraTilesetStudioTransaction;

    assert.equal(tx.isDirty(), false);
    f.el('ts-tileset-name').value = 'Changed Name';
    assert.equal(tx.isDirty(), true);

    assert.equal(tx.discard(), true);
    assert.equal(tx.isDirty(), false);
    assert.equal(f.el('ts-tileset-name').value, 'Dungeon Default');
    assert.equal(tx.workingCopy().name, 'Dungeon Default');
});

test('successful Tileset save adopts the new compound version, refreshes baseline, and announces only tilesets', async () => {
    const f = makeContext();
    await f.context.window.openTilesetStudioModal();
    const tx = f.context.window.thestraTilesetStudioTransaction;
    f.el('ts-tileset-name').value = 'Saved Name';

    assert.equal(await tx.save(), true);
    assert.equal(f.version(), 'v2');
    assert.equal(tx.isDirty(), false);
    assert.equal(tx.baseline()._storageVersion, 'v2');
    assert.equal(tx.baseline().name, 'Saved Name');
    assert.deepEqual(JSON.parse(JSON.stringify(f.committed)), [['tilesets']]);
});

test('stale Tileset save fails closed and keeps the working record dirty', async () => {
    const f = makeContext();
    await f.context.window.openTilesetStudioModal();
    const tx = f.context.window.thestraTilesetStudioTransaction;
    f.el('ts-tileset-name').value = 'Local Dirty Name';
    f.setStale(true);

    assert.equal(await tx.save(), false);
    assert.equal(tx.isDirty(), true);
    assert.equal(tx.workingCopy().name, 'Local Dirty Name');
    assert.deepEqual(f.committed, []);
});

test('dirty Tileset selection change is cancelable and does not silently replace the working record', async () => {
    const f = makeContext({ confirmResult: false });
    await f.context.window.openTilesetStudioModal();
    const tx = f.context.window.thestraTilesetStudioTransaction;
    f.el('ts-tileset-name').value = 'Do Not Lose';
    f.el('ts-select-tileset').value = 'castle';

    assert.equal(await f.context.window.onTilesetSelected('castle'), false);
    assert.equal(tx.currentId(), 'dungeon_default');
    assert.equal(tx.isDirty(), true);
    assert.equal(f.el('ts-select-tileset').value, 'dungeon_default');
});

test('native dirty Tileset selection can Save before switching records', async () => {
    const f = makeContext({ surfaceKind: 'tileset', choice: 'save' });
    await f.context.window.openTilesetStudioModal();
    const tx = f.context.window.thestraTilesetStudioTransaction;
    f.el('ts-tileset-name').value = 'Save Before Switch';

    assert.equal(await f.context.window.onTilesetSelected('castle'), true);
    assert.equal(f.records.dungeon_default.name, 'Save Before Switch');
    assert.equal(tx.currentId(), 'castle');
    assert.equal(tx.isDirty(), false);
});
