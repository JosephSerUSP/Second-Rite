'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, 'js', 'state.js'), 'utf8');

function modal(active) {
    return {
        classList: { contains: name => name === 'active' && active },
        style: { display: active ? 'block' : 'none' },
        addEventListener() {},
    };
}

function makeContext(options = {}) {
    const handlers = {};
    const dbModal = modal(true);
    const iconModal = modal(!!options.iconPickerActive);
    let databaseCloses = 0;
    let iconCloses = 0;

    class FakeCustomEvent {
        constructor(type, init = {}) {
            this.type = type;
            this.detail = init.detail;
        }
    }

    const context = {
        console,
        location: { protocol: 'http:' },
        CustomEvent: FakeCustomEvent,
        confirm: () => true,
        closeDatabaseModal() { databaseCloses += 1; },
        closeIconPicker() { iconCloses += 1; },
        document: {
            getElementById(id) {
                if (id === 'db-modal') return dbModal;
                if (id === 'icon-picker-modal') return iconModal;
                if (id === 'map-context-menu') return { style: { display: 'none' } };
                return null;
            },
        },
        window: {
            thestraSurfaceKind: options.surfaceKind,
            addEventListener(name, fn) { handlers[name] = fn; },
            dispatchEvent() { return true; },
            getComputedStyle(el) {
                return {
                    display: el.style && el.style.display ? el.style.display : 'none',
                    visibility: 'visible',
                };
            },
        },
    };
    context.window.window = context.window;
    vm.createContext(context);
    vm.runInContext(source, context, { filename: 'state.js' });
    return {
        pressEscape() { handlers.keydown({ key: 'Escape' }); },
        databaseCloses: () => databaseCloses,
        iconCloses: () => iconCloses,
    };
}

test('browser-hosted Database preserves legacy Escape-to-close modal behavior', () => {
    const f = makeContext();
    f.pressEscape();
    assert.equal(f.databaseCloses(), 1);
});

test('native Database Escape skips its host window but still dismisses nested interactions', () => {
    const clean = makeContext({ surfaceKind: 'database' });
    clean.pressEscape();
    assert.equal(clean.databaseCloses(), 0);
    assert.equal(clean.iconCloses(), 0);

    const nested = makeContext({ surfaceKind: 'database', iconPickerActive: true });
    nested.pressEscape();
    assert.equal(nested.iconCloses(), 1);
    assert.equal(nested.databaseCloses(), 0);
});
