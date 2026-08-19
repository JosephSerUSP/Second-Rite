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

test('/api/map-inspection uses the persistent Map authority, not the cold compiler', async () => {
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
    const server = bridge.createRuntimeBridgeServer({
        renderableWorker: fakeAuthority,
        inspectionCompiler() {
            throw new Error('test must not replace the production default');
        },
    });
    // Remove the explicit compiler override: construction above proves the
    // option seam exists, while the second server exercises the real default.
    server.close();

    const productionDefault = bridge.createRuntimeBridgeServer({ renderableWorker: fakeAuthority });
    await new Promise((resolve, reject) => {
        productionDefault.once('error', reject);
        productionDefault.listen(0, '127.0.0.1', resolve);
    });
    try {
        const response = await postJson(productionDefault.address().port, '/api/map-inspection', {
            map: { id: 2, width: 17, height: 17 },
            seed: 424242,
        });
        assert.equal(response.statusCode, 200);
        assert.equal(response.body.kind, 'generated-map-inspection');
        assert.deepEqual(calls, [['inspection', 2, 424242]]);
        assert.equal(productionDefault.runtimeRenderableWorkerState().generation.pid, 4242,
            'existing G6 state seam observes the unified authority generation');
    } finally {
        await new Promise(resolve => productionDefault.close(resolve));
    }
});

test('legacy injected workers without inspection support retain the cold fallback seam', async () => {
    let coldCalls = 0;
    const fakeLegacyWorker = {
        async compile() { return {}; },
        invalidate() {},
        shutdown() { return Promise.resolve(); },
        shutdownSync() {},
        state() { return {}; },
    };
    const server = bridge.createRuntimeBridgeServer({
        renderableWorker: fakeLegacyWorker,
        inspectionCompiler: async request => {
            coldCalls += 1;
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
        assert.equal(coldCalls, 1);
    } finally {
        await new Promise(resolve => server.close(resolve));
    }
});
