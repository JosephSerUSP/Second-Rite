'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const stateSource = fs.readFileSync(path.join(__dirname, 'js', 'state.js'), 'utf8');
const workspaceSource = fs.readFileSync(path.join(__dirname, 'js', 'thestra-editor-workspace.js'), 'utf8');

function fakeElement(active = false, display = 'none') {
    let isActive = active;
    return {
        style: { display },
        classList: {
            contains(name) { return name === 'active' && isActive; },
            add(name) { if (name === 'active') isActive = true; },
            remove(name) { if (name === 'active') isActive = false; },
        },
        addEventListener() {},
        setActive(value) { isActive = !!value; },
    };
}

function makeStateContext() {
    const elements = new Map();
    const observers = [];
    const emitted = [];
    const windowListeners = new Map();

    class FakeMutationObserver {
        constructor(callback) {
            this.callback = callback;
            this.targets = [];
            observers.push(this);
        }
        observe(target) { this.targets.push(target); }
    }
    class FakeCustomEvent {
        constructor(type, init = {}) {
            this.type = type;
            this.detail = init.detail;
        }
    }

    const context = {
        console,
        location: { protocol: 'http:' },
        confirm: () => true,
        CustomEvent: FakeCustomEvent,
        MutationObserver: FakeMutationObserver,
        document: {
            getElementById(id) { return elements.get(id) || null; },
        },
        window: {
            getComputedStyle(el) {
                return {
                    display: el && el.style ? el.style.display : 'none',
                    visibility: 'visible',
                };
            },
            addEventListener(name, fn) { windowListeners.set(name, fn); },
            dispatchEvent(event) { emitted.push(event); return true; },
        },
    };
    context.window.window = context.window;
    context.__elements = elements;
    context.__observers = observers;
    context.__emitted = emitted;

    vm.createContext(context);
    vm.runInContext(stateSource, context, { filename: 'state.js' });
    return context;
}

function plain(value) {
    return JSON.parse(JSON.stringify(value));
}

test('registered legacy interaction blocks semantically and clears after its exact owner closes', () => {
    const context = makeStateContext();
    const eventModal = fakeElement(false, 'none');
    context.__elements.set('event-modal', eventModal);

    // The element was added after state.js in this fixture, so refresh is the
    // explicit migration-adapter seam; production markup already exists before
    // state.js runs and is observed automatically.
    context.window.ThestraInteractionState.refresh();
    assert.deepEqual(plain(context.window.ThestraInteractionState.snapshot()), {
        blocked: false, owners: [],
    });

    eventModal.style.display = 'flex';
    eventModal.setActive(true);
    context.window.ThestraInteractionState.refresh();
    assert.deepEqual(plain(context.window.ThestraInteractionState.snapshot()), {
        blocked: true, owners: ['dialog:event-modal'],
    });

    eventModal.style.display = 'none';
    eventModal.setActive(false);
    context.window.ThestraInteractionState.refresh();
    assert.equal(context.window.ThestraInteractionState.isMapBlocked(), false);
});

test('arbitrary modal-looking DOM is not interaction authority', () => {
    const context = makeStateContext();
    const unregistered = fakeElement(true, 'flex');
    unregistered.className = 'modal modal-overlay picker-overlay';
    context.__elements.set('totally-unregistered-modal', unregistered);

    context.window.ThestraInteractionState.refresh();
    assert.deepEqual(plain(context.window.ThestraInteractionState.snapshot()), {
        blocked: false, owners: [],
    });
});

test('explicit semantic owners can block Map without any DOM modal', () => {
    const context = makeStateContext();
    const snapshots = [];
    const unsubscribe = context.window.ThestraInteractionState.subscribe(value => {
        snapshots.push(plain(value));
    });

    context.window.ThestraInteractionState.setBlocked('surface:future-docked-editor', true);
    assert.equal(context.window.ThestraInteractionState.isMapBlocked(), true);
    assert.deepEqual(plain(context.window.ThestraInteractionState.snapshot()), {
        blocked: true, owners: ['surface:future-docked-editor'],
    });

    context.window.ThestraInteractionState.setBlocked('surface:future-docked-editor', false);
    assert.equal(context.window.ThestraInteractionState.isMapBlocked(), false);
    unsubscribe();
    assert.ok(snapshots.length >= 3, 'subscriber receives initial, blocked, and unblocked states');
});

test('Map workspace consumes semantic interaction state instead of broad modal CSS inference', () => {
    assert.match(workspaceSource, /const InteractionState = window\.ThestraInteractionState;/);
    assert.match(workspaceSource, /!InteractionState\.isMapBlocked\(\)/);
    assert.match(workspaceSource, /InteractionState\.subscribe\(syncWorkspaceVisibility\)/);
    assert.doesNotMatch(workspaceSource, /querySelectorAll\([^\n]*(modal|picker-overlay)/);
    assert.doesNotMatch(workspaceSource, /surfaceObserver\.observe\(document\.body/);
    assert.match(workspaceSource, /mapHostObserver\.observe\(legacyCanvas/);
});
