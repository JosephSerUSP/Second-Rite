'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const http = require('node:http');
const bridge = require('./runtime-bridge-server');

function fakeWorker(compile) {
    return {
        compile,
        invalidate() {},
        shutdown() { return Promise.resolve(); },
        shutdownSync() {},
        state() { return { status: 'test' }; },
    };
}

function postJson(server, pathname, value) {
    return new Promise((resolve, reject) => {
        const address = server.address();
        const body = JSON.stringify(value);
        const request = http.request({
            host: '127.0.0.1',
            port: address.port,
            path: pathname,
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
                status: response.statusCode,
                body: JSON.parse(text || '{}'),
            }));
        });
        request.on('error', reject);
        request.end(body);
    });
}

test('#736 bare map-renderable HTTP requests use compact mesh-definition transport', async () => {
    const seen = [];
    const server = bridge.createRuntimeBridgeServer({
        renderableWorker: fakeWorker(async request => {
            seen.push(request);
            return {
                version: 1,
                map: { id: request.map.id },
                encoding: { kind: 'mesh-definitions-v1' },
                definitions: [],
                placements: [],
                surfaces: [],
                materials: [],
            };
        }),
    });
    await new Promise((resolve, reject) => {
        server.once('error', reject);
        server.listen(0, '127.0.0.1', resolve);
    });

    try {
        // This is the original #736 reproduction shape: no encoding hint.
        const response = await postJson(server, '/api/map-renderable', {
            map: { id: 3, layout: ['.'] },
        });
        assert.equal(response.status, 200);
        assert.equal(response.body.encoding.kind, 'mesh-definitions-v1');
        assert.equal(seen.length, 1);
        assert.equal(seen[0].renderableEncoding, 'instances',
            'the bridge owns the compact wire format even when the caller omits it');
        assert.deepEqual(seen[0].map, { id: 3, layout: ['.'] });
    } finally {
        await new Promise(resolve => server.close(resolve));
    }
});

test('#736 caller cannot accidentally select the expanded stdout wire format', async () => {
    let compiled = false;
    const server = bridge.createRuntimeBridgeServer({
        renderableWorker: fakeWorker(async () => {
            compiled = true;
            return { encoding: { kind: 'mesh-definitions-v1' }, surfaces: [], materials: [] };
        }),
    });
    await new Promise((resolve, reject) => {
        server.once('error', reject);
        server.listen(0, '127.0.0.1', resolve);
    });

    try {
        const response = await postJson(server, '/api/map-renderable', {
            map: { id: 3 },
            renderableEncoding: 'expanded',
        });
        assert.equal(response.status, 400);
        assert.match(response.body.error, /unsupported renderable encoding/);
        assert.equal(compiled, false);
    } finally {
        await new Promise(resolve => server.close(resolve));
    }
});
