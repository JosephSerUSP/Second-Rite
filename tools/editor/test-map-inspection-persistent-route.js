'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const http = require('node:http');
const bridge = require('./runtime-bridge-server');

function postJson(port, route, value) {
    return new Promise((resolve, reject) => {
        const body = JSON.stringify(value);
        const request = http.request({
            host: '127.0.0.1',
            port,
            path: route,
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Content-Length': Buffer.byteLength(body),
            },
        }, response => {
            let text = '';
            response.setEncoding('utf8');
            response.on('data', chunk => { text += chunk; });
            response.on('end', () => resolve({
                statusCode: response.statusCode,
                body: JSON.parse(text || '{}'),
            }));
        });
        request.on('error', reject);
        request.end(body);
    });
}

test('/api/map-inspection uses the persistent Map authority by default', async () => {
    const calls = [];
    const fakeAuthority = {
        async compile(request) {
            calls.push(['renderable', request.map.id]);
            return { representation: 'mesh-definitions-v1' };
        },
        async compileInspection(request) {
            calls.push(['inspection', request.map.id, request.seed]);
            return { kind: 'generated-map-inspection', request: { seed: request.seed } };
        },
        invalidate() {},
        shutdown() { return Promise.resolve(); },
        shutdownSync() {},
        state() { return { generation: { pid: 4242 } }; },
    };

    const server = bridge.createRuntimeBridgeServer({ renderableWorker: fakeAuthority });
    await new Promise((resolve, reject) => {
        server.once('error', reject);
        server.listen(0, '127.0.0.1', resolve);
    });
    try {
        const response = await postJson(server.address().port, '/api/map-inspection', {
            map: { id: 2, width: 17, height: 17 },
            seed: 424242,
        });
        assert.equal(response.statusCode, 200);
        assert.equal(response.body.kind, 'generated-map-inspection');
        assert.deepEqual(calls, [['inspection', 2, 424242]]);
        assert.equal(server.runtimeRenderableWorkerState().generation.pid, 4242,
            'existing G6 state seam observes the unified authority generation');
    } finally {
        await new Promise(resolve => server.close(resolve));
    }
});

test('an explicitly injected inspection compiler still overrides the production authority route', async () => {
    let explicitCalls = 0;
    const fakeAuthority = {
        async compile() { return {}; },
        async compileInspection() { throw new Error('persistent authority must not be called'); },
        invalidate() {},
        shutdown() { return Promise.resolve(); },
        shutdownSync() {},
        state() { return {}; },
    };
    const server = bridge.createRuntimeBridgeServer({
        renderableWorker: fakeAuthority,
        inspectionCompiler: async request => {
            explicitCalls += 1;
            return { kind: 'generated-map-inspection', mapId: request.map.id };
        },
    });
    await new Promise((resolve, reject) => {
        server.once('error', reject);
        server.listen(0, '127.0.0.1', resolve);
    });
    try {
        const response = await postJson(server.address().port, '/api/map-inspection', { map: { id: 5 }, seed: 9 });
        assert.equal(response.statusCode, 200);
        assert.equal(response.body.mapId, 5);
        assert.equal(explicitCalls, 1);
    } finally {
        await new Promise(resolve => server.close(resolve));
    }
});
