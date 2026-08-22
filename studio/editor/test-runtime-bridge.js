'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const bridge = require('./runtime-bridge-server');

test('validates transient map requests without mutating input', () => {
    const source = { map: { id: 7, layout: ['#.#'] }, seed: '42', renderableEncoding: 'instances' };
    const value = bridge.validateRequest(source);
    assert.equal(value.map, source.map);
    assert.equal(value.seed, 42);
    assert.equal(value.renderableEncoding, 'instances');
    assert.throws(() => bridge.validateRequest({ map: { id: 7 }, renderableEncoding: 'packed' }),
        /unsupported renderable encoding/);
});

test('rejects missing map identity', () => {
    assert.throws(() => bridge.validateRequest({ map: {} }), /needs an id/);
});

test('runtime bridge accepts only Studio browser origins', () => {
    assert.equal(bridge.isAllowedOrigin(undefined, 8080), true, 'origin-less local tooling remains possible');
    assert.equal(bridge.isAllowedOrigin('http://127.0.0.1:8080', 8080), true);
    assert.equal(bridge.isAllowedOrigin('http://localhost:8080', 8080), true);
    assert.equal(bridge.isAllowedOrigin('https://example.com', 8080), false);
    assert.equal(bridge.isAllowedOrigin('http://127.0.0.1:9999', 8080), false);
});

test('generic PORT never changes the expected Studio origin port', () => {
    const { spawnSync } = require('node:child_process');
    const env = Object.assign({}, process.env, { PORT: '8082' });
    delete env.EDITOR_PORT;
    const result = spawnSync(process.execPath, [
        '-e',
        "process.stdout.write(String(require('./runtime-bridge-server').DEFAULT_EDITOR_PORT))",
    ], {
        cwd: __dirname,
        env,
        encoding: 'utf8',
    });
    assert.equal(result.status, 0, result.stderr);
    assert.equal(result.stdout, '8080');
});

test('EDITOR_PORT explicitly configures the expected Studio origin port', () => {
    const { spawnSync } = require('node:child_process');
    const env = Object.assign({}, process.env, {
        PORT: '8082',
        EDITOR_PORT: '8090',
    });
    const result = spawnSync(process.execPath, [
        '-e',
        "process.stdout.write(String(require('./runtime-bridge-server').DEFAULT_EDITOR_PORT))",
    ], {
        cwd: __dirname,
        env,
        encoding: 'utf8',
    });
    assert.equal(result.status, 0, result.stderr);
    assert.equal(result.stdout, '8090');
});

test('rejected browser origins log the received and expected Studio origins', async () => {
    const http = require('node:http');
    const warnings = [];
    const server = bridge.createRuntimeBridgeServer({
        editorPort: 8080,
        warn(message) { warnings.push(message); },
    });
    await new Promise((resolve, reject) => {
        server.once('error', reject);
        server.listen(0, '127.0.0.1', resolve);
    });
    try {
        const address = server.address();
        const response = await new Promise((resolve, reject) => {
            const request = http.request({
                host: '127.0.0.1',
                port: address.port,
                path: '/api/map-renderable',
                method: 'OPTIONS',
                headers: { Origin: 'http://127.0.0.1:8082' },
            }, res => {
                res.resume();
                res.on('end', () => resolve(res));
            });
            request.on('error', reject);
            request.end();
        });
        assert.equal(response.statusCode, 403);
        assert.equal(warnings.length, 1);
        assert.match(warnings[0], /rejected browser origin http:\/\/127\.0\.0\.1:8082/);
        assert.match(warnings[0], /expected http:\/\/127\.0\.0\.1:8080 or http:\/\/localhost:8080/);
        assert.match(warnings[0], /EDITOR_PORT/);
    } finally {
        await new Promise(resolve => server.close(resolve));
    }
});

test('parses the dedicated LÖVE renderable envelope', () => {
    const value = bridge.parseRenderableOutput('noise\nRENDERABLE BEGIN\n{"version":1,"surfaces":[]}\nRENDERABLE END\nmore');
    assert.equal(value.version, 1);
    assert.deepEqual(value.surfaces, []);
});

test('surfaces LÖVE-side bridge errors instead of returning a partial bundle', () => {
    assert.throws(
        () => bridge.parseRenderableOutput('RENDERABLE BEGIN\n{"error":"broken height field"}\nRENDERABLE END'),
        /broken height field/);
});

test('transient bridge stages an external Project and removes its request and stage', async () => {
    const fs = require('node:fs');
    const os = require('node:os');
    const path = require('node:path');
    const installRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'second-rite-install-'));
    const externalRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'second-rite-project-'));
    const stagedRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'second-rite-staged-project-'));
    let requestPath = null;
    let removedStage = null;
    try {
        const value = await bridge.compileRenderable({ map: { id: 1 }, seed: 1, renderableEncoding: 'instances' }, {
                installRoot,
                projectRoot: externalRoot,
                previewExe: process.execPath,
                stageProject(options) {
                    assert.deepEqual(options, { installRoot, projectRoot: externalRoot });
                    return stagedRoot;
                },
                removeStage(stage) { removedStage = stage; },
                execFile(exe, args, options, callback) {
                    assert.equal(exe, process.execPath);
                    assert.deepEqual(args, ['.', 'preview-map', '1']);
                    assert.equal(options.cwd, stagedRoot);
                    assert.equal(options.env.THESTRA_RUNTIME_DATA_ROOT, undefined,
                        'external compiled stage must not need same-root data override');
                    assert.equal(options.env.SECOND_RITE_RENDERABLE_ENCODING, 'instances');
                    requestPath = path.join(stagedRoot, options.env.SECOND_RITE_RENDERABLE_REQUEST);
                    assert.deepEqual(JSON.parse(fs.readFileSync(requestPath, 'utf8')),
                        { map: { id: 1 }, seed: 1, renderableEncoding: 'instances' });
                    callback(null, 'RENDERABLE BEGIN\n{"version":1,"map":{"id":1}}\nRENDERABLE END\n', '');
                },
            });
        assert.equal(value.map.id, 1);
        assert.equal(fs.existsSync(requestPath), false);
        assert.equal(removedStage, stagedRoot);
    } finally {
        fs.rmSync(installRoot, { recursive: true, force: true });
        fs.rmSync(externalRoot, { recursive: true, force: true });
        fs.rmSync(stagedRoot, { recursive: true, force: true });
    }
});

test('same-root bridge layers transient Map over a short-lived compiled data snapshot', async () => {
    const fs = require('node:fs');
    const os = require('node:os');
    const path = require('node:path');
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'second-rite-renderable-'));
    // Poison the checkout-shaped root with the retired pointer. The spawned
    // argv assertion below is the deterministic proof that it cannot select
    // authored content or reintroduce the old CLI protocol.
    fs.writeFileSync(path.join(root, 'campaign.json'), '{"active":"zombie"}', 'utf8');
    let requestPath = null;
    let removedSnapshot = null;
    const fakeSnapshot = {
        env: { THESTRA_RUNTIME_DATA_ROOT: 'tmp/editor-runtime-data/snapshot-fixture/data' },
    };
    const request = { map: { id: 12, layout: ['.'] }, seed: 9 };
    try {
        const value = await bridge.compileRenderable(request, {
            installRoot: root,
            projectRoot: root,
            previewExe: process.execPath,
            snapshotSameRoot(options) {
                assert.deepEqual(options, { installRoot: root, projectRoot: root });
                return fakeSnapshot;
            },
            removeSnapshot(value) { removedSnapshot = value; },
            execFile(exe, args, options, callback) {
                assert.equal(exe, process.execPath);
                assert.deepEqual(args, ['.', 'preview-map', '12']);
                assert.equal(options.cwd, root, 'engine/assets stay direct in same-root preview');
                assert.equal(options.env.THESTRA_RUNTIME_DATA_ROOT,
                    'tmp/editor-runtime-data/snapshot-fixture/data');
                assert.equal(options.env.SECOND_RITE_RENDERABLE_ENCODING, undefined,
                    'expanded control must not inherit compact encoding');
                requestPath = path.join(root, options.env.SECOND_RITE_RENDERABLE_REQUEST);
                assert.deepEqual(JSON.parse(fs.readFileSync(requestPath, 'utf8')), request);
                callback(null, 'RENDERABLE BEGIN\n{"version":1,"map":{"id":12}}\nRENDERABLE END\n', '');
            },
        });
        assert.equal(value.map.id, 12);
        assert.equal(fs.existsSync(requestPath), false);
        assert.equal(removedSnapshot, fakeSnapshot);
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
    }
});

// GitHub's Windows verify job exports the just-installed lovec.exe as LOVEC
// before this Node suite runs. Use it when present to gate the whole host ->
// compiled semantic data snapshot -> transient unsaved Map -> real LÖVE
// loader/compiler -> JSON bundle path. Local Node-only runs skip this one
// rather than inventing a second runtime.
test('real LÖVE bridge compiles an unsaved authored map over compiled semantic data', {
    skip: !process.env.LOVEC,
}, async () => {
    const fs = require('node:fs');
    const path = require('node:path');
    const repoRoot = path.resolve(__dirname, '..', '..');
    const projectRoot = require('../../tools/semantic-roots').DEFAULT_PROJECT_ROOT;
    assert.ok(fs.existsSync(process.env.LOVEC), 'LOVEC points at the installed CI runtime');

    const authoredStorage = require('./authored-storage');
    const loaded = authoredStorage.loadResource(path.join(projectRoot, 'data'), 'maps').value;
    const authoredMap = (loaded || []).find(map => Array.isArray(map.layout) && map.layout.length > 0);
    assert.ok(authoredMap, 'default Project contains a hand-authored map');

    const transient = JSON.parse(JSON.stringify(authoredMap));
    delete transient.name;
    transient.title = '__unsaved_renderable_bridge_test__';
    const value = await bridge.compileRenderable({ map: transient, seed: 1735689600 }, {
        installRoot: repoRoot,
        projectRoot,
        previewExe: process.env.LOVEC,
    });

    assert.equal(value.version, 1);
    assert.equal(value.map.id, transient.id);
    assert.equal(value.map.name, transient.title,
        'returned bundle came from transient Map overlay, not last-saved map data');
    assert.equal(value.request && value.request.transient, true);
    assert.ok(Array.isArray(value.surfaces) && value.surfaces.length > 0,
        'real runtime bridge returns compiled static surfaces');
    assert.ok(value.stats && value.stats.triangleCount > 0,
        'real runtime bridge returns compiled triangle statistics');
});

// --- #736: transport failures must name themselves ---------------------------
//
// The bundle travels as JSON on stdout under execFile's maxBuffer. When it
// overflows, execFile truncates and reports ERR_CHILD_PROCESS_STDIO_MAXBUFFER.
// Because "RENDERABLE BEGIN" is printed BEFORE the payload, truncated output
// still contains it, so a begin-marker-only success check swallowed the real
// error and let the envelope parser blame the engine instead.

function bridgeRoot() {
    const fs = require('node:fs');
    const os = require('node:os');
    const path = require('node:path');
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'second-rite-bridge-736-'));
    fs.mkdirSync(path.join(root, 'data'), { recursive: true });
    return root;
}

function compileWith(root, handler, request = { map: { id: 4 }, seed: 1 }) {
    return bridge.compileRenderable(request, {
        installRoot: root,
        projectRoot: root,
        previewExe: process.execPath,
        snapshotSameRoot: () => null,
        removeSnapshot() {},
        execFile(exe, args, options, callback) { handler(options, callback); },
    });
}

function maxBufferError() {
    const error = new Error('stdout maxBuffer length exceeded');
    error.code = 'ERR_CHILD_PROCESS_STDIO_MAXBUFFER';
    return error;
}

test('#736 a stdout overflow names the transport limit, not a missing bundle', async () => {
    const fs = require('node:fs');
    const root = bridgeRoot();
    try {
        // Truncated exactly the way execFile truncates: begin marker and payload
        // present, end marker cut off.
        const truncated = 'RENDERABLE BEGIN\n{"version":1,"map":{"id":4},"surfaces":[';
        await assert.rejects(
            compileWith(root, (options, callback) => callback(maxBufferError(), truncated, '')),
            error => {
                assert.match(error.message, /stdout transport limit/i,
                    'the failure must say the payload was too large for the transport');
                assert.match(error.message, /64\.0 MiB/, 'it must state the limit that was hit');
                assert.match(error.message, /read .*bytes/i, 'it must state how much was read');
                assert.doesNotMatch(error.message, /did not return a renderable bundle/,
                    'a transport limit must never be reported as an engine refusal');
                return true;
            }
        );
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
    }
});

test('#736 the overflow diagnosis survives a runtime without the Node error code', async () => {
    const fs = require('node:fs');
    const root = bridgeRoot();
    try {
        const error = new Error('spawn failed: stdout maxBuffer length exceeded');
        await assert.rejects(
            compileWith(root, (options, callback) => callback(error, 'RENDERABLE BEGIN\n{', '')),
            /stdout transport limit/i
        );
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
    }
});

test('#736 a killed subprocess reports the timeout rather than the buffer', async () => {
    const fs = require('node:fs');
    const root = bridgeRoot();
    try {
        const error = new Error('Command failed');
        error.killed = true;
        error.signal = 'SIGTERM';
        await assert.rejects(
            compileWith(root, (options, callback) => callback(error, 'RENDERABLE BEGIN\n{', '')),
            error => {
                assert.match(error.message, /did not finish within \d+ ms/);
                assert.doesNotMatch(error.message, /transport limit/i);
                return true;
            }
        );
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
    }
});

test('#736 truncation with no execFile error is reported as truncation', async () => {
    const fs = require('node:fs');
    const root = bridgeRoot();
    try {
        await assert.rejects(
            compileWith(root, (options, callback) => callback(null, 'RENDERABLE BEGIN\n{"version":1', '')),
            error => {
                assert.match(error.message, /ended without "RENDERABLE END"/);
                assert.match(error.message, /truncated in transport/);
                return true;
            }
        );
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
    }
});

test('#736 a noisy but complete run still succeeds', async () => {
    const fs = require('node:fs');
    const root = bridgeRoot();
    try {
        // LÖVE routinely exits non-zero or prints driver noise (`AL lib: (EE)
        // alc_cleanup`) while producing a perfectly good bundle. That tolerance
        // is the reason the original guard existed and must be preserved.
        const error = new Error('Command failed with exit code 1');
        const value = await compileWith(root, (options, callback) => callback(
            error,
            'RENDERABLE BEGIN\n{"version":1,"map":{"id":4}}\nRENDERABLE END\n',
            'AL lib: (EE) alc_cleanup: 1 device not closed'
        ));
        assert.equal(value.map.id, 4);
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
    }
});

test('#736 an empty run still reports that no bundle was produced', async () => {
    const fs = require('node:fs');
    const root = bridgeRoot();
    try {
        // No markers at all is a genuine "the engine produced nothing" case and
        // must keep its original message.
        await assert.rejects(
            compileWith(root, (options, callback) => callback(null, 'Error: something exploded\n', '')),
            /did not return a renderable bundle/
        );
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
    }
});

test('#736 inspection overflow names its own smaller limit', async () => {
    const fs = require('node:fs');
    const root = bridgeRoot();
    try {
        await assert.rejects(
            bridge.compileInspection({ map: { id: 4 }, seed: 1 }, {
                installRoot: root,
                projectRoot: root,
                previewExe: process.execPath,
                snapshotSameRoot: () => null,
                removeSnapshot() {},
                execFile(exe, args, options, callback) {
                    assert.equal(options.maxBuffer, bridge.INSPECTION_MAX_BUFFER);
                    callback(maxBufferError(), 'MAP INSPECTION BEGIN\n{', '');
                },
            }),
            /16\.0 MiB/
        );
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
    }
});
