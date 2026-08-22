'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');
const { createStudioShutdownCoordinator } = require('./studio-shutdown');

function fixture(options = {}) {
    const events = [];
    const open = new Set(options.openSurfaces || ['database']);
    const secondaryDecision = options.secondaryDecision !== undefined ? options.secondaryDecision : true;
    const mainDecision = options.mainDecision !== undefined ? options.mainDecision : true;
    let secondaryRequests = 0;
    let mainRequests = 0;

    const windowManager = {
        has(surfaceId) { return open.has(surfaceId); },
        async closeAndWait(surfaceId) {
            secondaryRequests += 1;
            events.push(`secondary:${surfaceId}`);
            if (secondaryDecision) open.delete(surfaceId);
            return secondaryDecision;
        },
    };
    const studioIpc = {
        requestClose(surfaceId, mainWindow, decide) {
            mainRequests += 1;
            events.push(`main:${surfaceId}`);
            assert.equal(surfaceId, 'main');
            assert.equal(mainWindow, options.mainWindow || null);
            decide(mainDecision);
        },
    };
    const errors = [];
    const coordinator = createStudioShutdownCoordinator({
        windowManager,
        studioIpc,
        secondarySurfaces: ['database'],
        logger: { error(...args) { errors.push(args); } },
    });

    return {
        coordinator,
        events,
        errors,
        secondaryRequests: () => secondaryRequests,
        mainRequests: () => mainRequests,
    };
}

function request(coordinator, mainWindow = null) {
    return new Promise(resolve => coordinator.requestMainClose(mainWindow, resolve));
}

test('secondary cancel aborts shutdown before main close is requested', async () => {
    const f = fixture({ secondaryDecision: false, mainDecision: true });
    assert.equal(await request(f.coordinator), false);
    assert.deepEqual(f.events, ['secondary:database']);
    assert.equal(f.secondaryRequests(), 1);
    assert.equal(f.mainRequests(), 0);
});

test('main cancel leaves Studio alive after safe secondary closure', async () => {
    const f = fixture({ secondaryDecision: true, mainDecision: false });
    assert.equal(await request(f.coordinator), false);
    assert.deepEqual(f.events, ['secondary:database', 'main:main']);
    assert.equal(f.secondaryRequests(), 1);
    assert.equal(f.mainRequests(), 1);
});

test('clean coordinated shutdown resolves secondary surfaces before main', async () => {
    const f = fixture({ secondaryDecision: true, mainDecision: true });
    assert.equal(await request(f.coordinator), true);
    assert.deepEqual(f.events, ['secondary:database', 'main:main']);
});

test('repeated main close requests share one in-flight shutdown decision', async () => {
    let resolveSecondary;
    const events = [];
    let secondaryRequests = 0;
    let mainRequests = 0;
    const windowManager = {
        has() { return true; },
        closeAndWait() {
            secondaryRequests += 1;
            events.push('secondary');
            return new Promise(resolve => { resolveSecondary = resolve; });
        },
    };
    const studioIpc = {
        requestClose(_surfaceId, _mainWindow, decide) {
            mainRequests += 1;
            events.push('main');
            decide(true);
        },
    };
    const coordinator = createStudioShutdownCoordinator({
        windowManager,
        studioIpc,
        secondarySurfaces: ['database'],
    });

    const first = request(coordinator);
    const second = request(coordinator);
    assert.equal(secondaryRequests, 1);
    resolveSecondary(true);
    assert.equal(await first, true);
    assert.equal(await second, true);
    assert.equal(mainRequests, 1);
    assert.deepEqual(events, ['secondary', 'main']);
});
