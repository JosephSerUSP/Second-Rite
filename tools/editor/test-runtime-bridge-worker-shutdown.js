'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const runtimeBridge = require('./runtime-bridge-server');

test('runtime bridge close synchronously shuts down persistent worker before HTTP close', async () => {
    const calls = [];
    const renderableWorker = {
        compile() { throw new Error('not used'); },
        invalidate() {},
        shutdown() { calls.push('shutdown'); return Promise.resolve(); },
        shutdownSync() { calls.push('shutdownSync'); },
        state() { return {}; },
    };
    const server = runtimeBridge.createRuntimeBridgeServer({ renderableWorker });

    await new Promise((resolve, reject) => {
        server.once('error', reject);
        server.listen(0, '127.0.0.1', resolve);
    });
    await new Promise((resolve, reject) => {
        server.close(error => error ? reject(error) : resolve());
    });

    assert.deepEqual(calls, ['shutdownSync'],
        'Studio/server exit uses the hard synchronous child cleanup boundary exactly once');
});
