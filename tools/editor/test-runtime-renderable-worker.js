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

function fakeHarness() {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'second-rite-worker-test-'));
    const projectRoot = path.join(root, 'project');
    fs.mkdirSync(path.join(projectRoot, 'data'), { recursive: true });
    fs.mkdirSync(path.join(projectRoot, 'assets'), { recursive: true });
    fs.writeFileSync(path.join(projectRoot, 'project.json'), '{}');
    let revision = 'rev-a';
    let stageCount = 0;
    let spawnCount = 0;
    let beforeRespond = null;
    const removed = [];
    const children = [];

    function stageProject() {
        stageCount += 1;
        const stage = path.join(root, `stage-${stageCount}`);
        fs.mkdirSync(stage, { recursive: true });
        fs.writeFileSync(path.join(stage, 'main.lua'), '-- staged');
        return stage;
    }

    function spawn(_exe, _args, options) {
        spawnCount += 1;
        const child = new EventEmitter();
        child.pid = 1000 + spawnCount;
        child.stdin = new PassThrough();
        child.stdout = new PassThrough();
        child.stderr = new PassThrough();
        child.closedForTest = false;
        children.push(child);

        let input = '';
        const close = (code = 0) => {
            if (child.closedForTest) return;
            child.closedForTest = true;
            child.emit('close', code, null);
        };
        child.kill = () => { close(137); return true; };
        child.stdin.setEncoding('utf8');
        child.stdin.on('data', chunk => {
            input += chunk;
            while (input.includes('\n')) {
                const index = input.indexOf('\n');
                const line = input.slice(0, index).replace(/\r$/, '');
                input = input.slice(index + 1);
                if (line === 'QUIT') {
                    setImmediate(() => close(0));
                    continue;
                }
                const [mapId, relative] = line.split('\t');
                const request = JSON.parse(fs.readFileSync(path.join(options.cwd, relative), 'utf8'));
                setImmediate(() => {
                    if (beforeRespond) beforeRespond();
                    child.stdout.write('RENDERABLE BEGIN\n');
                    child.stdout.write(JSON.stringify({
                        version: 1,
                        map: { id: request.map.id, name: request.map.name || null },
                        seed: request.seed,
                        materials: [],
                        surfaces: [],
                    }) + '\n');
                    child.stdout.write('RENDERABLE END\n');
                    child.stdout.write('RENDERABLE WORKER REQUEST DONE\n');
                });
                assert.equal(String(request.map.id), mapId);
            }
        });
        process.nextTick(() => {
            child.emit('spawn');
            child.stdout.write('RENDERABLE WORKER READY\n');
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
        startupTimeoutMs: 1000,
        timeoutMs: 1000,
        shutdownTimeoutMs: 100,
    });

    return {
        root,
        worker,
        children,
        removed,
        setRevision(value) { revision = value; },
        setBeforeRespond(fn) { beforeRespond = fn; },
        counts() { return { stageCount, spawnCount }; },
        cleanup() { fs.rmSync(root, { recursive: true, force: true }); },
    };
}

test('persistent renderable worker reuses one generation across transient Map revisions', async () => {
    const h = fakeHarness();
    try {
        const first = await h.worker.compile({ map: { id: 2, name: 'A' }, seed: 1 });
        const changed = await h.worker.compile({ map: { id: 2, name: 'B' }, seed: 2 });
        assert.equal(first.map.name, 'A');
        assert.equal(changed.map.name, 'B', 'changed unsaved Map snapshot is handled inside the same generation');
        assert.deepEqual(h.counts(), { stageCount: 1, spawnCount: 1 });
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
    } finally {
        await worker.shutdown();
        assert.equal(worker.state().generation, null);
    }
});
