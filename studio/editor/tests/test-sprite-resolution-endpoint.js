'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const http = require('node:http');
const os = require('node:os');
const path = require('node:path');
const { createSpriteResolutionEndpoint } = require('../sprite-resolution-endpoint');

function write(filePath, body) {
    fs.mkdirSync(path.dirname(filePath), { recursive: true });
    fs.writeFileSync(filePath, body);
}

function makeProject(label) {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), `thestra-sprite-endpoint-${label}-`));
    fs.mkdirSync(path.join(root, 'data'), { recursive: true });
    for (const dir of ['assets/smallBattlers', 'assets/sprites', 'assets/system']) {
        fs.mkdirSync(path.join(root, ...dir.split('/')), { recursive: true });
    }
    write(path.join(root, 'presentation', 'sprite_sheet.lua'), '-- runtime authority\n');
    write(path.join(root, 'assets', 'smallBattlers', 'pixie[fps=15].png'), `pixie-${label}`);
    return root;
}

function listen(handler) {
    return new Promise((resolve, reject) => {
        const server = http.createServer((req, res) => handler(req, res));
        server.once('error', reject);
        server.listen(0, '127.0.0.1', () => resolve(server));
    });
}

function request(server, requestPath) {
    const address = server.address();
    return new Promise((resolve, reject) => {
        const req = http.get({ hostname: '127.0.0.1', port: address.port, path: requestPath }, res => {
            let body = '';
            res.setEncoding('utf8');
            res.on('data', chunk => { body += chunk; });
            res.on('end', () => resolve({
                statusCode: res.statusCode,
                body,
                json: JSON.parse(body),
            }));
        });
        req.once('error', reject);
    });
}

function close(server) {
    return new Promise((resolve, reject) => server.close(error => error ? reject(error) : resolve()));
}

function endpointFor(projectRoot, runtimeResolver) {
    return createSpriteResolutionEndpoint({
        projectRoot,
        runtimeAuthorityPath: path.join(projectRoot, 'presentation', 'sprite_sheet.lua'),
        runtimeResolver,
    });
}

async function main() {
    const projectA = makeProject('a');
    const projectB = makeProject('b');
    let serverA;
    let serverB;
    try {
        let calls = 0;
        const expectedPayload = {
            key: 'pixie',
            resolved: true,
            path: 'assets/smallBattlers/pixie[fps=15].png',
            timing: { fps: 15, frameDuration: 1 / 15, source: 'filename', token: 'fps', value: 15 },
            summary: '15 fps from filename token [fps=15]',
        };
        const runtimeResolver = async spec => {
            calls += 1;
            return Object.assign({}, expectedPayload, spec.key === undefined ? { key: undefined } : { key: spec.key });
        };
        const endpointA = endpointFor(projectA, runtimeResolver);
        serverA = await listen(endpointA);

        const first = await request(serverA, '/api/sprite-resolution?key=pixie');
        const repeated = await request(serverA, '/api/sprite-resolution?key=pixie');
        assert.equal(first.statusCode, 200);
        assert.equal(repeated.statusCode, 200);
        assert.equal(calls, 1, 'repeated endpoint request should amortize the runtime consultation');
        assert.deepEqual(first.json, expectedPayload, 'endpoint must return the runtime payload semantics unchanged');
        assert.deepEqual(repeated.json, expectedPayload, 'cache hit must return the same runtime-produced payload');

        endpointA.cache.clear();
        calls = 0;
        let release;
        let markStarted;
        const gate = new Promise(resolve => { release = resolve; });
        const started = new Promise(resolve => { markStarted = resolve; });
        const burstEndpoint = endpointFor(projectA, async spec => {
            calls += 1;
            markStarted();
            await gate;
            return Object.assign({}, expectedPayload, { key: spec.key });
        });
        const burstServer = await listen(burstEndpoint);
        try {
            const burst = [
                request(burstServer, '/api/sprite-resolution?key=pixie'),
                request(burstServer, '/api/sprite-resolution?key=pixie'),
                request(burstServer, '/api/sprite-resolution?key=pixie'),
            ];
            await started;
            assert.equal(calls, 1, 'concurrent endpoint requests should coalesce behind one runtime consultation');
            release();
            const responses = await Promise.all(burst);
            assert.ok(responses.every(response => response.statusCode === 200));
            assert.ok(responses.every(response => response.json.summary === expectedPayload.summary));
        } finally {
            await close(burstServer);
        }

        endpointA.cache.clear();
        calls = 0;
        await request(serverA, '/api/sprite-resolution?key=pixie');
        const resolvedFile = path.join(projectA, 'assets', 'smallBattlers', 'pixie[fps=15].png');
        write(resolvedFile, 'replacement-content-longer-than-before');
        await request(serverA, '/api/sprite-resolution?key=pixie');
        assert.equal(calls, 2, 'resolved-file replacement should invalidate an endpoint cache hit');

        const alternate = path.join(projectA, 'assets', 'sprites', 'pixie[speed=2].png');
        write(alternate, 'alternate');
        await request(serverA, '/api/sprite-resolution?key=pixie');
        assert.equal(calls, 3, 'adding a lookup candidate should invalidate the key result');
        const renamed = path.join(projectA, 'assets', 'sprites', 'pixie[speed=3].png');
        fs.renameSync(alternate, renamed);
        await request(serverA, '/api/sprite-resolution?key=pixie');
        assert.equal(calls, 4, 'renaming a lookup candidate should invalidate the key result');
        fs.rmSync(renamed);
        await request(serverA, '/api/sprite-resolution?key=pixie');
        assert.equal(calls, 5, 'removing a lookup candidate should invalidate the key result');

        const directPath = encodeURIComponent('assets/smallBattlers/pixie[fps=15].png');
        const direct = await request(serverA, `/api/sprite-resolution?path=${directPath}`);
        assert.equal(direct.statusCode, 200);
        assert.equal(calls, 6, 'direct-path request must have a distinct cache identity from the authored key');

        const missingDirect = encodeURIComponent('assets/smallBattlers/nope.png');
        const missing = await request(serverA, `/api/sprite-resolution?path=${missingDirect}`);
        assert.equal(missing.statusCode, 404);
        assert.equal(missing.json.error, 'sprite file no longer exists');
        assert.equal(calls, 6, 'direct-path existence validation must run before the runtime/cache membrane');

        const escaped = await request(serverA, '/api/sprite-resolution?path=../outside.png');
        assert.equal(escaped.statusCode, 400);
        assert.equal(calls, 6, 'unsafe direct paths must be rejected before runtime consultation');

        const noSpec = await request(serverA, '/api/sprite-resolution');
        assert.equal(noSpec.statusCode, 400);
        assert.equal(noSpec.json.error, 'sprite-resolution requires key or path');

        let retryCalls = 0;
        const retryEndpoint = endpointFor(projectA, async () => {
            retryCalls += 1;
            if (retryCalls === 1) throw new Error('runtime transport failed');
            return expectedPayload;
        });
        const retryServer = await listen(retryEndpoint);
        try {
            const failed = await request(retryServer, '/api/sprite-resolution?key=pixie');
            const retried = await request(retryServer, '/api/sprite-resolution?key=pixie');
            assert.equal(failed.statusCode, 500);
            assert.match(failed.json.error, /runtime transport failed/);
            assert.equal(retried.statusCode, 200);
            assert.equal(retryCalls, 2, 'runtime transport errors must remain retryable at the endpoint');
        } finally {
            await close(retryServer);
        }

        let projectACalls = 0;
        let projectBCalls = 0;
        const rootAEndpoint = endpointFor(projectA, async () => {
            projectACalls += 1;
            return Object.assign({}, expectedPayload, { summary: 'project A runtime answer' });
        });
        const rootBEndpoint = endpointFor(projectB, async () => {
            projectBCalls += 1;
            return Object.assign({}, expectedPayload, { summary: 'project B runtime answer' });
        });
        const rootAServer = await listen(rootAEndpoint);
        serverB = await listen(rootBEndpoint);
        try {
            const rootA = await request(rootAServer, '/api/sprite-resolution?key=pixie');
            const rootB = await request(serverB, '/api/sprite-resolution?key=pixie');
            assert.equal(rootA.json.summary, 'project A runtime answer');
            assert.equal(rootB.json.summary, 'project B runtime answer');
            assert.equal(projectACalls, 1);
            assert.equal(projectBCalls, 1,
                'separate opened-Project endpoint instances must never share cache entries');
        } finally {
            await close(rootAServer);
            await close(serverB);
            serverB = null;
        }

        console.log('sprite resolution endpoint: OK');
    } finally {
        if (serverA) await close(serverA);
        if (serverB) await close(serverB);
        fs.rmSync(projectA, { recursive: true, force: true });
        fs.rmSync(projectB, { recursive: true, force: true });
    }
}

main().catch(error => {
    console.error(error);
    process.exitCode = 1;
});
