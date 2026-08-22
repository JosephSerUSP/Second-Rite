'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const {
    createRuntimeMapAuthorityWorker,
} = require('./runtime-map-authority-worker');

function fixture() {
    const events = [];
    let capturedOptions = null;
    const fakeWorker = {
        async compile(request) {
            const route = capturedOptions.routeOf(request);
            events.push({ kind: 'compile', route, json: JSON.stringify(request) });
            if (route.startsWith('inspection:')) {
                return 'MAP INSPECTION BEGIN\n{"kind":"generated-map-inspection","request":{"seed":424242}}\nMAP INSPECTION END\n';
            }
            return 'RENDERABLE BEGIN\n{"version":1,"representation":"mesh-definitions-v1"}\nRENDERABLE END\n';
        },
        invalidate(reason) { events.push({ kind: 'invalidate', reason }); },
        shutdown() { events.push({ kind: 'shutdown' }); return Promise.resolve(); },
        shutdownSync() { events.push({ kind: 'shutdownSync' }); },
        state() { return { generation: { pid: 1234 } }; },
    };
    const worker = createRuntimeMapAuthorityWorker({
        createWorker(options) {
            capturedOptions = options;
            return fakeWorker;
        },
        parseRenderableOutput(text) {
            const match = text.match(/RENDERABLE BEGIN\s*([\s\S]*?)\s*RENDERABLE END/);
            if (!match) throw new Error('missing renderable');
            return JSON.parse(match[1]);
        },
        parseInspectionOutput(text) {
            const match = text.match(/MAP INSPECTION BEGIN\s*([\s\S]*?)\s*MAP INSPECTION END/);
            if (!match) throw new Error('missing inspection');
            return JSON.parse(match[1]);
        },
    });
    return { worker, events, getOptions: () => capturedOptions };
}

test('one underlying worker routes renderables and inspections by typed Map route', async () => {
    const { worker, events, getOptions } = fixture();
    const request = { map: { id: 2, width: 17 }, seed: 424242, renderableEncoding: 'instances' };

    const renderable = await worker.compile(request);
    const inspection = await worker.compileInspection(request);

    assert.equal(renderable.representation, 'mesh-definitions-v1');
    assert.equal(inspection.kind, 'generated-map-inspection');
    assert.deepEqual(events.filter(event => event.kind === 'compile').map(event => event.route), [
        'renderable:2',
        'inspection:2',
    ]);
    assert.equal(getOptions().workerMain.endsWith('runtime-map-authority-worker-main.lua'), true);
});

test('internal route kind never leaks into the transient runtime request JSON', async () => {
    const { worker, events } = fixture();
    const request = { map: { id: 9 }, seed: 7 };
    await worker.compileInspection(request);
    const compiled = events.find(event => event.kind === 'compile');
    assert.deepEqual(JSON.parse(compiled.json), request);
    assert.equal(Object.getOwnPropertySymbols(request).length, 0, 'caller request remains untouched');
});

test('Map authority routes reject framing injection and missing identity', async () => {
    const { worker } = fixture();
    await assert.rejects(worker.compileInspection({ map: { id: '2\nQUIT' } }), /framing characters/);
    await assert.rejects(worker.compile({ map: {} }), /needs a map id/);
});

test('inspection response keeps the existing 16 MiB semantic ceiling', async () => {
    const events = [];
    let capturedOptions;
    const worker = createRuntimeMapAuthorityWorker({
        inspectionMaxBytes: 64,
        createWorker(options) {
            capturedOptions = options;
            return {
                async compile(request) {
                    capturedOptions.routeOf(request);
                    return 'MAP INSPECTION BEGIN\n' + 'x'.repeat(80) + '\nMAP INSPECTION END';
                },
                invalidate(reason) { events.push(reason); },
                shutdown() { return Promise.resolve(); },
                shutdownSync() {},
                state() { return {}; },
            };
        },
        parseRenderableOutput() { return {}; },
        parseInspectionOutput() { return {}; },
    });
    await assert.rejects(worker.compileInspection({ map: { id: 2 } }), /more than 0\.0 MiB/);
    assert.match(events[0], /response contract/);
});

test('a malformed semantic envelope invalidates the reusable generation', async () => {
    const events = [];
    let capturedOptions;
    const worker = createRuntimeMapAuthorityWorker({
        createWorker(options) {
            capturedOptions = options;
            return {
                async compile(request) {
                    capturedOptions.routeOf(request);
                    return 'not an inspection envelope';
                },
                invalidate(reason) { events.push(reason); },
                shutdown() { return Promise.resolve(); },
                shutdownSync() {},
                state() { return { generation: { pid: 777 } }; },
            };
        },
        parseRenderableOutput() { throw new Error('bad renderable'); },
        parseInspectionOutput() { throw new Error('bad inspection'); },
    });
    await assert.rejects(worker.compileInspection({ map: { id: 2 } }), /bad inspection/);
    assert.match(events[0], /parser rejected/);
});

test('lifecycle and state delegate to the one underlying authority', async () => {
    const { worker, events } = fixture();
    assert.equal(worker.state().generation.pid, 1234);
    worker.invalidate('fixture invalidation');
    await worker.shutdown();
    worker.shutdownSync();
    assert.deepEqual(events.filter(event => event.kind !== 'compile'), [
        { kind: 'invalidate', reason: 'fixture invalidation' },
        { kind: 'shutdown' },
        { kind: 'shutdownSync' },
    ]);
});
