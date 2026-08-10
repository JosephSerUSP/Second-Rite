'use strict';

const assert = require('assert');
const path = require('path');
const net = require('net');
const { spawn } = require('child_process');
const test = require('node:test');

function reservePort() {
    return new Promise((resolve, reject) => {
        const probe = net.createServer();
        probe.on('error', reject);
        probe.listen(0, '127.0.0.1', () => {
            const { port } = probe.address();
            probe.close(err => err ? reject(err) : resolve(port));
        });
    });
}

function waitForServer(child, timeoutMs = 8000) {
    return new Promise((resolve, reject) => {
        let output = '';
        const timer = setTimeout(() => {
            reject(new Error('editor server did not announce startup\n' + output));
        }, timeoutMs);
        const absorb = chunk => {
            output += chunk.toString();
            if (output.includes('Editor server running at')) {
                clearTimeout(timer);
                resolve();
            }
        };
        child.stdout.on('data', absorb);
        child.stderr.on('data', absorb);
        child.once('exit', code => {
            clearTimeout(timer);
            reject(new Error(`editor server exited before startup (code ${code})\n${output}`));
        });
    });
}

test('editor model API enumerates and serves authored OBJ files', async (t) => {
    const port = await reservePort();
    const editorDir = path.resolve(__dirname, '..');
    const installRoot = path.resolve(editorDir, '..', '..');
    const child = spawn(process.execPath, [path.join(editorDir, 'server.js')], {
        cwd: installRoot,
        env: Object.assign({}, process.env, { PORT: String(port) }),
        stdio: ['ignore', 'pipe', 'pipe']
    });
    t.after(() => {
        if (!child.killed) child.kill();
    });

    await waitForServer(child);
    const base = `http://127.0.0.1:${port}`;

    const inventoryResponse = await fetch(`${base}/api/models?root=models/items`);
    assert.strictEqual(inventoryResponse.status, 200, 'model inventory endpoint responds');
    const inventory = await inventoryResponse.json();
    assert.strictEqual(inventory.root, 'assets/models/items');
    assert.ok(Array.isArray(inventory.files) && inventory.files.length > 0,
        'model inventory returns authored OBJ files');

    const known = inventory.files.find(entry =>
        entry.path === 'assets/models/items/bottle_family__basis.obj'
    );
    assert.ok(known, 'inventory contains the HP Tonic bottle model');
    assert.ok(known.size > 0, 'inventory reports a non-zero OBJ size');

    const objResponse = await fetch(`${base}/${known.path}`);
    assert.strictEqual(objResponse.status, 200, 'model asset is served through the editor server');
    const objText = await objResponse.text();
    assert.match(objText, /^mtllib\s|\nmtllib\s/m, 'served OBJ retains its material-library declaration');
    assert.match(objText, /^v\s/m, 'served OBJ contains geometry');
});
