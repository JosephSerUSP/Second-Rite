'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const test = require('node:test');
const vm = require('vm');

const SOURCE = fs.readFileSync(path.join(__dirname, 'js', 'project-manager.js'), 'utf8');

function harness(options = {}) {
    const calls = [];
    const bridge = {
        current: async () => ({
            info: { projectRoot: '/current', sameAsInstall: false, assetsPath: '/current/assets' },
            sparse: { available: true },
        }),
        chooseDirectory: async payload => { calls.push(['chooseDirectory', payload]); return options.directory || '/parent'; },
        create: async payload => { calls.push(['create', payload]); return { projectRoot: payload.target }; },
        open: async target => { calls.push(['open', target]); return { success: true, projectRoot: target }; },
        fork: async payload => { calls.push(['fork', payload]); return { projectRoot: payload.target }; },
    };
    const window = {
        thestraProjects: bridge,
        thestraStudio: {
            projectSwitchReady: async () => options.secondaryReady === false
                ? { ready: false, blockers: options.blockers || ['database'] }
                : { ready: true, blockers: [] },
        },
        thestraHasUnsavedProjectChanges: () => !!options.dirty,
        thestraPrepareForProjectSwitch: () => options.stagedReady !== false,
    };
    const document = {
        readyState: 'loading',
        addEventListener() {},
        querySelector() { return null; },
        createElement() { throw new Error('menu injection should not run in this harness'); },
    };
    const context = {
        window,
        document,
        alert: message => calls.push(['alert', message]),
        confirm: message => {
            calls.push(['confirm', message]);
            return options.confirm !== false;
        },
        prompt: (...args) => {
            calls.push(['prompt', ...args]);
            return options.name || 'tiny-game';
        },
    };
    vm.runInNewContext(SOURCE, context, { filename: 'project-manager.js' });
    return { window, calls };
}

test('Open Project selects a Project folder and relaunches into it', async () => {
    const h = harness({ directory: '/games/other' });
    await h.window.openThestraProject();
    assert.deepEqual(h.calls.filter(call => call[0] === 'chooseDirectory')[0][1], {
        title: 'Open Thestra Project Folder',
    });
    assert.ok(h.calls.some(call => call[0] === 'open' && call[1] === '/games/other'));
});

test('Project switching stops before filesystem UI when current Project is dirty and discard is declined', async () => {
    const h = harness({ dirty: true, confirm: false });
    await h.window.openThestraProject();
    assert.equal(h.calls[0][0], 'confirm');
    assert.ok(!h.calls.some(call => call[0] === 'chooseDirectory'));
    assert.ok(!h.calls.some(call => call[0] === 'open'));
});

test('Project switching stops when a staged editor refuses to discard its local changes', async () => {
    const h = harness({ stagedReady: false });
    await h.window.openThestraProject();
    assert.ok(!h.calls.some(call => call[0] === 'confirm'));
    assert.ok(!h.calls.some(call => call[0] === 'chooseDirectory'));
    assert.ok(!h.calls.some(call => call[0] === 'open'));
});

test('Project switching is blocked before local discard prompts while a native EditorSurface is open', async () => {
    const h = harness({ secondaryReady: false, dirty: true });
    await h.window.openThestraProject();
    assert.ok(h.calls.some(call => call[0] === 'alert' && /Close secondary Studio windows/.test(call[1])));
    assert.ok(!h.calls.some(call => call[0] === 'confirm'));
    assert.ok(!h.calls.some(call => call[0] === 'chooseDirectory'));
    assert.ok(!h.calls.some(call => call[0] === 'open'));
});

test('New Project turns the selected folder itself into the Project and immediately opens it', async () => {
    const h = harness({ directory: '/games/Saraba' });
    await h.window.createSparseThestraProject();
    assert.deepEqual(h.calls.filter(call => call[0] === 'chooseDirectory')[0][1], {
        title: 'Choose Folder for New Thestra Project',
    });
    assert.ok(h.calls.some(call => call[0] === 'create'
        && call[1].mode === 'sparse'
        && call[1].target === '/games/Saraba'));
    assert.ok(h.calls.some(call => call[0] === 'open' && call[1] === '/games/Saraba'));
    assert.ok(!h.calls.some(call => call[0] === 'prompt'),
        'New Project must not reinterpret the selected folder as a parent and ask for a hidden child name');
    assert.equal(h.calls.filter(call => call[0] === 'confirm').length, 0,
        'clean New Project must not ask a second open-it-now question');
});
