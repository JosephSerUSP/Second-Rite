'use strict';

// #833: the Map inspection request had no deadline, so a bridge that never
// answered left the editor waiting forever.
//
// The negative controls are the substance. The bug was an error path that never
// ran, so asserting the happy path still works proves nothing about it.
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const test = require('node:test');

const ROOT = path.resolve(__dirname, '..', '..', '..');
const { createInspectionRequester, DEFAULT_TIMEOUT_MS } =
    require('../js/map-inspection-request.js');

const bridgeSource = fs.readFileSync(
    path.join(ROOT, 'studio', 'editor', 'runtime-bridge-server.js'), 'utf8');
const mapEditorSource = fs.readFileSync(
    path.join(ROOT, 'studio', 'editor', 'js', 'map-editor.js'), 'utf8');

function bridgeTimeoutMs() {
    const match = /BRIDGE_TIMEOUT_MS\s*=\s*(\d+)/.exec(bridgeSource);
    assert.ok(match, 'runtime-bridge-server.js no longer declares BRIDGE_TIMEOUT_MS');
    return Number(match[1]);
}

// A controller stub, so these run without a DOM.
function fakeController() {
    const listeners = [];
    return {
        signal: { addEventListener: (_, fn) => listeners.push(fn), aborted: false },
        abort() { this.signal.aborted = true; listeners.forEach(fn => fn()); },
    };
}

function requesterWith(fetchImpl, timeoutMs = 50) {
    return createInspectionRequester({
        fetch: fetchImpl,
        timeoutMs,
        createController: fakeController,
    });
}

test('the client deadline exceeds the bridge deadline', () => {
    // If the client gave up first it would abandon a request the server is
    // still legitimately serving -- #815, repeated where the user cannot rerun.
    assert.ok(DEFAULT_TIMEOUT_MS > bridgeTimeoutMs(),
        `client ${DEFAULT_TIMEOUT_MS}ms must exceed bridge ${bridgeTimeoutMs()}ms`);
});

test('a prompt response is returned unchanged', async () => {
    const requester = requesterWith(async () => ({ ok: true, body: 'payload' }));
    assert.deepStrictEqual(await requester.request('/api/map-inspection', { seed: 1 }),
        { ok: true, body: 'payload' });
});

test('NEGATIVE CONTROL: a bridge that never answers fails, and says so', async () => {
    // Without a deadline this promise never settles and the test times out.
    const requester = requesterWith(() => new Promise(() => {}));
    await assert.rejects(
        requester.request('/api/map-inspection', { seed: 1 }),
        (error) => /did not answer within/.test(error.message),
    );
});

test('NEGATIVE CONTROL: the abort is actually signalled to fetch', async () => {
    let sawSignal = null;
    const requester = requesterWith((url, init) => {
        sawSignal = init.signal;
        return new Promise(() => {});
    });
    await assert.rejects(requester.request('/api/map-inspection', {}));
    assert.ok(sawSignal, 'fetch was called without an abort signal');
    assert.strictEqual(sawSignal.aborted, true, 'the signal was never aborted');
});

test('a genuine fetch error is not disguised as a timeout', async () => {
    const requester = requesterWith(async () => { throw new Error('ECONNREFUSED'); });
    await assert.rejects(requester.request('/api/map-inspection', {}),
        (error) => /ECONNREFUSED/.test(error.message));
});

test('a second request cannot stack behind an in-flight one', async () => {
    const requester = requesterWith(() => new Promise(() => {}), 10000);
    const first = requester.request('/api/map-inspection', {});
    first.catch(() => {});
    assert.strictEqual(requester.busy(), true);
    await assert.rejects(requester.request('/api/map-inspection', {}),
        (error) => /already in flight/.test(error.message));
});

test('the slot is released after a failure, not just a success', async () => {
    // A requester that stays busy forever after one timeout would be worse than
    // the bug: the editor could never resolve again without a reload.
    const requester = requesterWith(() => new Promise(() => {}));
    await assert.rejects(requester.request('/api/map-inspection', {}));
    assert.strictEqual(requester.busy(), false);
    const ok = requesterWith(async () => ({ ok: true }));
    assert.deepStrictEqual(await ok.request('/api/map-inspection', {}), { ok: true });
});

test('map-editor.js uses the shared requester rather than a bare fetch', () => {
    assert.ok(/ThestraMapInspectionRequest|createInspectionRequester/.test(mapEditorSource),
        'map-editor.js must go through the deadline-bearing requester');
    assert.ok(!/await fetch\(`\$\{RUNTIME_API_URL\}\/api\/map-inspection`/.test(mapEditorSource),
        'the bare, deadline-free fetch is back in map-editor.js');
});
