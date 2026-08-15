'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const http = require('node:http');
const net = require('node:net');
const path = require('node:path');
const { spawn } = require('node:child_process');
const test = require('node:test');

const repoRoot = path.resolve(__dirname, '..', '..');
const expectedIndex = fs.readFileSync(path.join(__dirname, 'index.html'), 'utf8');

function reservePort() {
    return new Promise((resolve, reject) => {
        const probe = net.createServer();
        probe.once('error', reject);
        probe.listen(0, '127.0.0.1', () => {
            const address = probe.address();
            probe.close(error => {
                if (error) reject(error);
                else resolve(address.port);
            });
        });
    });
}

function request(port, requestPath) {
    return new Promise((resolve, reject) => {
        const req = http.get({ hostname: '127.0.0.1', port, path: requestPath }, res => {
            let body = '';
            res.setEncoding('utf8');
            res.on('data', chunk => { body += chunk; });
            res.on('end', () => resolve({
                statusCode: res.statusCode,
                contentType: res.headers['content-type'],
                body,
            }));
        });
        req.once('error', reject);
    });
}

function startEditorServer(port) {
    return new Promise((resolve, reject) => {
        const child = spawn(process.execPath, [path.join(__dirname, 'server.js')], {
            cwd: repoRoot,
            env: Object.assign({}, process.env, { PORT: String(port) }),
            stdio: ['ignore', 'pipe', 'pipe'],
        });

        let stdout = '';
        let stderr = '';
        const cleanup = () => {
            child.stdout.removeAllListeners();
            child.stderr.removeAllListeners();
            child.removeAllListeners();
        };
        const fail = error => {
            cleanup();
            if (!child.killed) child.kill();
            reject(error);
        };

        child.stdout.setEncoding('utf8');
        child.stderr.setEncoding('utf8');
        child.stdout.on('data', chunk => {
            stdout += chunk;
            if (stdout.includes(`Editor server running at http://127.0.0.1:${port}`)) {
                cleanup();
                resolve(child);
            }
        });
        child.stderr.on('data', chunk => { stderr += chunk; });
        child.once('error', fail);
        child.once('exit', code => {
            fail(new Error(`Editor server exited before readiness (code ${code}).\n${stdout}\n${stderr}`));
        });
    });
}

test('root query URLs serve the same Studio document while API queries keep routing', async t => {
    const port = await reservePort();
    const child = await startEditorServer(port);
    t.after(() => {
        if (!child.killed) child.kill();
    });

    const root = await request(port, '/');
    const queriedRoot = await request(port, '/?surface=database');
    const explicitDocument = await request(port, '/index.html?surface=database');

    for (const response of [root, queriedRoot, explicitDocument]) {
        assert.equal(response.statusCode, 200);
        assert.match(response.contentType || '', /^text\/html(?:;|$)/);
        assert.equal(response.body, expectedIndex);
    }

    const ping = await request(port, '/ping?scene=map');
    assert.equal(ping.statusCode, 200);
    assert.match(ping.contentType || '', /^application\/json(?:;|$)/);
    assert.deepEqual(JSON.parse(ping.body), { success: true });
});
