'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { EventEmitter } = require('node:events');
const { PassThrough } = require('node:stream');
const workerModule = require('./runtime-renderable-worker');
const runtimeBridge = require('./runtime-bridge-server');
const authoredStorage = require('./authored-storage');
const projectRootAuthority = require('./project-root');

function parseOutput(stdout) {
    const match = String(stdout).match(/RENDERABLE BEGIN\s*([\s\S]*?)\s*RENDERABLE END/);
    if (!match) throw new Error('test worker returned no renderable envelope');
    return JSON.parse(match[1]);
}

function fakeHarness(options = {}) {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'second-rite-worker-test-'));
    const projectRoot = path.join(root, 'project');
    fs.mkdirSync(path.join(projectRoot, 'data'), { recursive: true });
    fs.mkdirSync(path.join(projectRoot, 'assets'), { recursive: true });
    fs.writeFileSync(path.join(projectRoot, 'project.json'), '{}');
    let revision = 'rev-a';
    let stageCount = 0;
    let spawnCount = 0;
    let beforeRespond = null;
    let responseMode = 'normal';
    let changedDuringStage = false;
    const removed = [];
    const children = [];
    const killSignals = [];
    const stageArgs = [];

    function stageProject(args) {
        stageArgs.push(args);
        stageCount += 1;
        const stage = path.join(root, `stage-${stageCount}`);
        fs.mkdirSync(stage, { recursive: true });
        fs.writeFileSync(path.join(stage, 'main.lua'), '-- staged');
        if (options.changeRevisionDuringStage && !changedDuringStage) {
            changedDuringStage = true;
            revision = 'rev-b';
        }
        return stage;
    }

    function spawn(_exe, _args, spawnOptions) {
        spawnCount += 1;
        const child = new EventEmitter();
        child.pid = 1000 + spawnCount;
        child.stdin = new PassThrough();
        child.stdout = new PassThrough();
        child.stderr = new PassThrough();
        child.closedForTest = false;
        children.push(child);

        let input = '';
        const close = (code = 0, signal = null) => {
            if (child.closedForTest) return;
            child.closedForTest = true;
            child.emit('close', code, signal);
        };
        child.kill = signal => {
            const normalized = signal || 'SIGTERM';
            killSignals.push(normalized);
            if (!options.stubbornKill || normalized === 'SIGKILL') close(137, normalized);
            return true;
        };
        child.stdin.setEncoding('utf8');
        child.stdin.on('data', chunk => {
            input += chunk;
            while (input.includes('\n')) {
                const index = input.indexOf('\n');
                const line = input.slice(0, index).replace(/\r$/, '');
                input = input.slice(index + 1);
                if (line === 'QUIT') {
                    if (!options.ignoreQuit) setImmediate(() => close(0));
                    continue;
                }
                const [marker, requestId, mapId, relative, ...extra] = line.split('\t');
                assert.equal(marker, workerModule.REQUEST_MARKER);
                assert.equal(extra.length, 0, 'protocol request has exactly four fields');
                const request = JSON.parse(fs.readFileSync(path.join(spawnOptions.cwd, relative), 'utf8'));
                assert.equal(String(request.map.id), mapId);
                setImmediate(() => {
                    if (beforeRespond) beforeRespond();
                    if (responseMode === 'crash') {
                        close(1);
                        return;
                    }
                    if (responseMode === 'child-error') {
                        child.emit('error', new Error('synthetic child error'));
                        return;
                    }
                    if (responseMode === 'partial') {
                        child.stdout.write('RENDERABLE BEGIN\n{"version":1');
                        return;
                    }
                    if (responseMode === 'oversize') {
                        child.stdout.write('x'.repeat(4096));
                        return;
                    }
                    if (responseMode === 'malformed') {
                        child.stdout.write('not a renderable envelope\n');
                        child.stdout.write(`${workerModule.DONE_MARKER}\t${requestId}\n`);
                        return;
                    }

                    child.stdout.write('RENDERABLE BEGIN\n');
                    child.stdout.write(JSON.stringify({
                        version: 1,
                        map: { id: request.map.id, name: request.map.name || null },
                        seed: request.seed,
                        materials: [],
                        surfaces: [],
                    }) + '\n');
                    child.stdout.write('RENDERABLE END\n');
                    const responseId = responseMode === 'wrong-id' ? String(Number(requestId) + 1) : requestId;
                    child.stdout.write(`${workerModule.DONE_MARKER}\t${responseId}\n`);
                });
            }
        });
        process.nextTick(() => {
            child.emit('spawn');
            child.stdout.write(`${workerModule.READY_MARKER}\n`);
        });
        return child;
    }

    const worker = workerModule.createRuntimeRenderableWorker({
        installRoot: root,
        projectRoot,
        previewExe: process.execPath,
        workerMain: workerModule.WORKER_MAIN,
        stageProject,
        removeStage(stage) {
            const child = children.find(candidate => path.basename(stage) === `stage-${candidate.pid - 1000}`);
            assert.ok(!child || child.closedForTest, 'stage must only be removed after its child closes');
            removed.push(stage);
            fs.rmSync(stage, { recursive: true, force: true });
        },
        spawn,
        authorityRevision: () => revision,
        parseOutput,
        platform: options.platform,
        startupTimeoutMs: options.startupTimeoutMs || 1000,
        timeoutMs: options.timeoutMs || 1000,
        shutdownTimeoutMs: options.shutdownTimeoutMs || 25,
        maxOutputBytes: options.maxOutputBytes || 1024 * 1024,
        maxDiagnosticBytes: options.maxDiagnosticBytes || 1024,
    });

    return {
        root,
        worker,
        children,
        removed,
        killSignals,
        stageArgs,
        setRevision(value) { revision = value; },
        setBeforeRespond(fn) { beforeRespond = fn; },
        setResponseMode(value) { responseMode = value; },
        counts() { return { stageCount, spawnCount }; },
        cleanup() { fs.rmSync(root, { recursive: true, force: true }); },
    };
}

function write(filePath, value) {
    fs.mkdirSync(path.dirname(filePath), { recursive: true });
    fs.writeFileSync(filePath, value);
}

function authorityFixture() {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'second-rite-authority-revision-'));
    const installRoot = path.join(root, 'install');
    const projectRoot = path.join(root, 'project');
    const manifestPath = path.join(installRoot, 'tools', 'export', 'runtime-manifest.json');
    write(path.join(installRoot, 'main.lua'), '-- main A\n');
    write(path.join(installRoot, 'boot.lua'), '-- boot B\n');
    write(path.join(installRoot, 'engine', 'runtime.lua'), '-- engine A\n');
    write(path.join(installRoot, 'presentation', 'runtime.lua'), '-- present A\n');
    write(path.join(installRoot, 'tools', 'export', 'release-conf.lua'), '-- release A\n');
    write(path.join(installRoot, 'tools', 'export', 'runtime-semantic-resources.lua'), '-- provider A\n');
    write(path.join(installRoot, 'tools', 'export', 'runtime-engine-server.lua'), '-- server A\n');
    write(path.join(installRoot, 'rtp', 'revision-a', 'height.bin'), 'AAAA');
    write(path.join(projectRoot, 'data', 'system.json'), '{"rtp":"A"}\n');
    write(path.join(projectRoot, 'assets', 'tilesets', 'model.obj'), 'v 0 0 0\n');
    write(path.join(projectRoot, 'assets', 'tilesets', 'height.bin'), '0000');
    write(path.join(projectRoot, 'geometry-config', 'budget.json'), '{"q":1}\n');
    write(path.join(projectRoot, 'project.json'), '{"name":"A"}\n');
    write(manifestPath, JSON.stringify({
        version: 1,
        rootFiles: ['main.lua'],
        runtimeDirectories: ['engine', 'presentation'],
        projectDirectories: ['assets', 'geometry-config'],
        authoredDataExtensions: ['.json'],
        releaseConfig: 'tools/export/release-conf.lua',
    }));
    return { root, installRoot, projectRoot, manifestPath };
}

function sameMetadataEdit(filePath, before, after) {
    assert.equal(Buffer.byteLength(before), Buffer.byteLength(after), 'fixture edit must preserve size');
    const stat = fs.statSync(filePath);
    assert.equal(fs.readFileSync(filePath, 'utf8'), before);
    fs.writeFileSync(filePath, after);
    fs.utimesSync(filePath, stat.atime, stat.mtime);
    assert.equal(fs.statSync(filePath).size, stat.size, 'fixture edit preserved size');
}

test('authority revision hashes content across every staged Map authority input', () => {
    const f = authorityFixture();
    try {
        const revision = () => workerModule.runtimeAuthorityRevision({
            installRoot: f.installRoot,
            projectRoot: f.projectRoot,
            manifestPath: f.manifestPath,
        });
        let previous = revision();
        const change = (label, filePath, before, after) => {
            sameMetadataEdit(filePath, before, after);
            const current = revision();
            assert.notEqual(current, previous, `${label} must change authority identity despite same size/mtime`);
            previous = current;
        };
        change('runtime Lua source', path.join(f.installRoot, 'engine', 'runtime.lua'), '-- engine A\n', '-- engine B\n');
        change('release/compiler config', path.join(f.installRoot, 'tools', 'export', 'release-conf.lua'), '-- release A\n', '-- release B\n');
        change('generated runtime provider', path.join(f.installRoot, 'tools', 'export', 'runtime-semantic-resources.lua'), '-- provider A\n', '-- provider B\n');
        change('generated runtime server', path.join(f.installRoot, 'tools', 'export', 'runtime-engine-server.lua'), '-- server A\n', '-- server B\n');
        change('Project non-transient data', path.join(f.projectRoot, 'data', 'system.json'), '{"rtp":"A"}\n', '{"rtp":"B"}\n');
        change('Project model asset', path.join(f.projectRoot, 'assets', 'tilesets', 'model.obj'), 'v 0 0 0\n', 'v 1 0 0\n');
        change('Project height-map asset', path.join(f.projectRoot, 'assets', 'tilesets', 'height.bin'), '0000', '1111');
        change('manifest-selected geometry config', path.join(f.projectRoot, 'geometry-config', 'budget.json'), '{"q":1}\n', '{"q":2}\n');
        change('Project project.json', path.join(f.projectRoot, 'project.json'), '{"name":"A"}\n', '{"name":"B"}\n');
        change('RTP fallback input', path.join(f.installRoot, 'rtp', 'revision-a', 'height.bin'), 'AAAA', 'BBBB');

        const originalManifest = fs.readFileSync(f.manifestPath, 'utf8');
        const changedManifest = originalManifest.replace('main.lua', 'boot.lua');
        sameMetadataEdit(f.manifestPath, originalManifest, changedManifest);
        assert.notEqual(revision(), previous, 'runtime manifest content changes authority identity');
    } finally {
        fs.rmSync(f.root, { recursive: true, force: true });
    }
});

test('persistent renderable worker reuses one generation across transient Map revisions', async () => {
    const h = fakeHarness();
    try {
        const first = await h.worker.compile({ map: { id: 2, name: 'A' }, seed: 1 });
        const changed = await h.worker.compile({ map: { id: 2, name: 'B' }, seed: 2 });
        assert.equal(first.map.name, 'A');
        assert.equal(changed.map.name, 'B', 'changed unsaved Map snapshot is handled inside the same generation');
        assert.deepEqual(h.counts(), { stageCount: 1, spawnCount: 1 });
        assert.equal(h.stageArgs[0].runtimeRoot, h.root, 'generation stage uses the fingerprinted runtime root');
        assert.equal(h.stageArgs[0].rtpRoot, path.join(h.root, 'rtp'), 'generation stage uses the fingerprinted RTP root');
        await h.worker.shutdown();
        assert.equal(h.removed.length, 1);
    } finally {
        h.cleanup();
    }
});

test('explicit authority invalidation rebuilds before the next request', async () => {
    const h = fakeHarness();
    try {
        await h.worker.compile({ map: { id: 2 }, seed: 1 });
        h.worker.invalidate('Project assets changed');
        await h.worker.compile({ map: { id: 2 }, seed: 1 });
        assert.deepEqual(h.counts(), { stageCount: 2, spawnCount: 2 });
        assert.equal(h.removed.length, 1, 'stale generation is removed before its replacement is used');
        await h.worker.shutdown();
        assert.equal(h.removed.length, 2);
    } finally {
        h.cleanup();
    }
});

test('repeated invalidations collapse into one fresh generation on next request', async () => {
    const h = fakeHarness();
    try {
        await h.worker.compile({ map: { id: 2 }, seed: 1 });
        h.worker.invalidate('data changed');
        h.worker.invalidate('assets changed');
        await h.worker.compile({ map: { id: 2 }, seed: 1 });
        assert.deepEqual(h.counts(), { stageCount: 2, spawnCount: 2 });
        assert.equal(h.worker.state().invalidationEpoch, 2);
        await h.worker.shutdown();
    } finally {
        h.cleanup();
    }
});

test('runtime authority fingerprint change rebuilds even without watcher delivery', async () => {
    const h = fakeHarness();
    try {
        await h.worker.compile({ map: { id: 2 }, seed: 1 });
        h.setRevision('rev-b');
        await h.worker.compile({ map: { id: 2 }, seed: 1 });
        assert.deepEqual(h.counts(), { stageCount: 2, spawnCount: 2 });
        await h.worker.shutdown();
    } finally {
        h.cleanup();
    }
});

test('authority change while staging rejects and removes the mixed generation before spawn', async () => {
    const h = fakeHarness({ changeRevisionDuringStage: true });
    try {
        await assert.rejects(
            h.worker.compile({ map: { id: 2 }, seed: 1 }),
            /authority changed while staging/
        );
        assert.deepEqual(h.counts(), { stageCount: 1, spawnCount: 0 });
        assert.equal(h.removed.length, 1, 'mixed-revision stage is cleaned before any child starts');
        await h.worker.shutdown();
    } finally {
        h.cleanup();
    }
});

test('authority change during a request suppresses the stale response', async () => {
    const h = fakeHarness();
    try {
        let changed = false;
        h.setBeforeRespond(() => {
            if (changed) return;
            changed = true;
            h.setRevision('rev-b');
        });
        await assert.rejects(
            h.worker.compile({ map: { id: 2, name: 'stale' }, seed: 1 }),
            /runtime authority changed during renderable request/
        );
        assert.equal(h.worker.state().generation.stale, true);
        h.setBeforeRespond(null);
        const fresh = await h.worker.compile({ map: { id: 2, name: 'fresh' }, seed: 1 });
        assert.equal(fresh.map.name, 'fresh');
        assert.deepEqual(h.counts(), { stageCount: 2, spawnCount: 2 });
        await h.worker.shutdown();
    } finally {
        h.cleanup();
    }
});

test('concurrent callers are serialized onto the same generation', async () => {
    const h = fakeHarness();
    try {
        const [a, b, c] = await Promise.all([
            h.worker.compile({ map: { id: 2, name: 'one' }, seed: 1 }),
            h.worker.compile({ map: { id: 2, name: 'two' }, seed: 1 }),
            h.worker.compile({ map: { id: 2, name: 'three' }, seed: 1 }),
        ]);
        assert.deepEqual([a.map.name, b.map.name, c.map.name], ['one', 'two', 'three']);
        assert.deepEqual(h.counts(), { stageCount: 1, spawnCount: 1 });
        await h.worker.shutdown();
    } finally {
        h.cleanup();
    }
});

test('map ids cannot inject tab/newline protocol frames', async () => {
    const h = fakeHarness();
    try {
        await assert.rejects(
            h.worker.compile({ map: { id: '2\nQUIT' }, seed: 1 }),
            /cannot contain tab\/newline framing characters/
        );
        assert.deepEqual(h.counts(), { stageCount: 0, spawnCount: 0 }, 'invalid framing is rejected before staging');
        await h.worker.shutdown();
    } finally {
        h.cleanup();
    }
});

test('wrong response request id is rejected and stales the generation', async () => {
    const h = fakeHarness();
    try {
        h.setResponseMode('wrong-id');
        await assert.rejects(h.worker.compile({ map: { id: 2 }, seed: 1 }), /did not match request/);
        assert.equal(h.worker.state().generation.stale, true);
        h.setResponseMode('normal');
        await h.worker.compile({ map: { id: 2 }, seed: 1 });
        assert.deepEqual(h.counts(), { stageCount: 2, spawnCount: 2 });
        await h.worker.shutdown();
    } finally {
        h.cleanup();
    }
});

test('malformed complete output is not reused as a healthy generation', async () => {
    const h = fakeHarness();
    try {
        h.setResponseMode('malformed');
        await assert.rejects(h.worker.compile({ map: { id: 2 }, seed: 1 }), /no renderable envelope/);
        assert.equal(h.worker.state().generation.stale, true);
        h.setResponseMode('normal');
        await h.worker.compile({ map: { id: 2 }, seed: 1 });
        assert.deepEqual(h.counts(), { stageCount: 2, spawnCount: 2 });
        await h.worker.shutdown();
    } finally {
        h.cleanup();
    }
});

test('partial output times out, stales the generation, and rebuilds on retry', async () => {
    const h = fakeHarness({ timeoutMs: 20 });
    try {
        h.setResponseMode('partial');
        await assert.rejects(h.worker.compile({ map: { id: 2 }, seed: 1 }), /did not finish within 20 ms/);
        assert.equal(h.worker.state().generation.stale, true);
        h.setResponseMode('normal');
        await h.worker.compile({ map: { id: 2 }, seed: 1 });
        assert.deepEqual(h.counts(), { stageCount: 2, spawnCount: 2 });
        await h.worker.shutdown();
    } finally {
        h.cleanup();
    }
});

test('oversized stdout is bounded and forces a fresh generation', async () => {
    const h = fakeHarness({ maxOutputBytes: 256 });
    try {
        h.setResponseMode('oversize');
        await assert.rejects(h.worker.compile({ map: { id: 2 }, seed: 1 }), /produced more than/);
        assert.equal(h.worker.state().generation.stale, true);
        h.setResponseMode('normal');
        await h.worker.compile({ map: { id: 2 }, seed: 1 });
        assert.deepEqual(h.counts(), { stageCount: 2, spawnCount: 2 });
        await h.worker.shutdown();
    } finally {
        h.cleanup();
    }
});

test('child crash rejects active work and next request rebuilds', async () => {
    const h = fakeHarness();
    try {
        h.setResponseMode('crash');
        await assert.rejects(h.worker.compile({ map: { id: 2 }, seed: 1 }), /exited 1/);
        h.setResponseMode('normal');
        await h.worker.compile({ map: { id: 2 }, seed: 1 });
        assert.deepEqual(h.counts(), { stageCount: 2, spawnCount: 2 });
        await h.worker.shutdown();
    } finally {
        h.cleanup();
    }
});

test('child error after readiness is handled instead of becoming an unhandled EventEmitter error', async () => {
    const h = fakeHarness();
    try {
        h.setResponseMode('child-error');
        await assert.rejects(h.worker.compile({ map: { id: 2 }, seed: 1 }), /synthetic child error/);
        assert.equal(h.worker.state().generation.stale, true);
        await h.worker.shutdown();
    } finally {
        h.cleanup();
    }
});

test('POSIX async shutdown escalates from QUIT to SIGTERM to SIGKILL before deleting stage', async () => {
    const h = fakeHarness({ platform: 'linux', ignoreQuit: true, stubbornKill: true, shutdownTimeoutMs: 5 });
    try {
        await h.worker.compile({ map: { id: 2 }, seed: 1 });
        await h.worker.shutdown();
        assert.deepEqual(h.killSignals, ['SIGTERM', 'SIGKILL']);
        assert.equal(h.children[0].closedForTest, true);
        assert.equal(h.removed.length, 1);
    } finally {
        h.cleanup();
    }
});

test('shutdown rejects new work and closes child before deleting stage', async () => {
    const h = fakeHarness();
    try {
        await h.worker.compile({ map: { id: 2 }, seed: 1 });
        await h.worker.shutdown();
        assert.equal(h.children[0].closedForTest, true);
        assert.equal(h.removed.length, 1);
        await assert.rejects(
            h.worker.compile({ map: { id: 2 }, seed: 1 }),
            /shut down/
        );
    } finally {
        h.cleanup();
    }
});

test('real persistent LÖVE worker emits compact definitions and reuses its child', {
    skip: process.platform !== 'win32' || !process.env.LOVE_PATH,
    timeout: 30000,
}, async () => {
    const maps = authoredStorage.loadOrderedCollection(
        path.join(projectRootAuthority.PROJECT_ROOT, 'data'),
        'maps'
    ).entries;
    const map = maps.find(candidate => String(candidate.id) === '2');
    assert.ok(map, 'Map 2 fixture is available');
    const originalName = map.name;

    const worker = workerModule.createRuntimeRenderableWorker({
        installRoot: projectRootAuthority.INSTALL_ROOT,
        projectRoot: projectRootAuthority.PROJECT_ROOT,
        previewExe: runtimeBridge.resolvePreviewExe(process.env.LOVE_PATH),
        parseOutput: runtimeBridge.parseRenderableOutput,
        timeoutMs: 20000,
        startupTimeoutMs: 10000,
    });
    try {
        const first = await worker.compile({ map, seed: 1735689600 });
        const firstState = worker.state();
        assert.equal(first.encoding && first.encoding.kind, 'mesh-definitions-v1');
        assert.ok(Array.isArray(first.definitions) && first.definitions.length > 0);
        assert.ok(Array.isArray(first.placements) && first.placements.length > 0);
        assert.ok(firstState.generation && firstState.generation.pid, 'real worker generation is live');

        const changed = JSON.parse(JSON.stringify(map));
        changed.name = `${changed.name || 'Map 2'} [persistent worker test]`;
        const second = await worker.compile({ map: changed, seed: 1735689600 });
        const secondState = worker.state();
        assert.equal(second.encoding && second.encoding.kind, 'mesh-definitions-v1');
        assert.equal(secondState.generation.pid, firstState.generation.pid,
            'transient Map revision reuses the live runtime authority');

        const reloaded = authoredStorage.loadOrderedCollection(
            path.join(projectRootAuthority.PROJECT_ROOT, 'data'),
            'maps'
        ).entries.find(candidate => String(candidate.id) === '2');
        assert.equal(reloaded.name, originalName,
            'transient Map overlay never mutates persistent Project source');
    } finally {
        await worker.shutdown();
        assert.equal(worker.state().generation, null);
    }
});
