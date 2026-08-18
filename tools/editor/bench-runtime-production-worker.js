'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { performance } = require('node:perf_hooks');
const authoredStorage = require('./authored-storage');
const projectRoot = require('./project-root');
const runtimeBridge = require('./runtime-bridge-server');
const workerModule = require('./runtime-renderable-worker');
const adapter = require('./js/second-rite-editor-adapter.js');

function arg(name, fallback) {
    const i = process.argv.indexOf(name);
    return i >= 0 && process.argv[i + 1] ? process.argv[i + 1] : fallback;
}
function round(value) { return Number(value.toFixed(3)); }
function mib(bytes) { return Number((bytes / (1024 * 1024)).toFixed(3)); }
function gcHeap() { if (global.gc) global.gc(); return process.memoryUsage().heapUsed; }

const loveExe = path.resolve(arg('--love', process.env.LOVE_PATH || 'C:\\Program Files\\LOVE\\love.exe'));
const previewExe = runtimeBridge.resolvePreviewExe(loveExe);
const installRoot = path.resolve(arg('--install-root', projectRoot.INSTALL_ROOT));
const openedProjectRoot = path.resolve(arg('--project-root', projectRoot.PROJECT_ROOT));
const maps = authoredStorage.loadOrderedCollection(path.join(openedProjectRoot, 'data'), 'maps').entries;
const map = maps.find(candidate => String(candidate.id) === String(arg('--map', '2')));
if (!map) throw new Error('benchmark Map fixture not found');
if (!fs.existsSync(previewExe)) throw new Error(`LÖVE console executable not found: ${previewExe}`);

function measureAuthorityRevision() {
    const started = performance.now();
    const revision = workerModule.runtimeAuthorityRevision({ installRoot, projectRoot: openedProjectRoot });
    return { revision, ms: performance.now() - started };
}

async function measureCompile(worker, label, requestMap) {
    const fingerprint = measureAuthorityRevision();
    const started = performance.now();
    const value = await worker.compile({ map: requestMap, seed: 1735689600 });
    const compiledAt = performance.now();
    const state = worker.state();
    const compactBytes = Buffer.byteLength(JSON.stringify(value), 'utf8');

    const before = gcHeap();
    const decodeStarted = performance.now();
    adapter.decodeTransport(value);
    const decodeMs = performance.now() - decodeStarted;
    const after = process.memoryUsage().heapUsed;

    const result = {
        label,
        fingerprintMs: round(fingerprint.ms),
        compileMs: round(compiledAt - started),
        compactMiB: mib(compactBytes),
        decodeMs: round(decodeMs),
        decodeHeapDeltaMiB: mib(after - before),
        endToDecodedMs: round(performance.now() - started),
        pid: state.generation && state.generation.pid,
        revision: state.generation && state.generation.revision,
        definitions: Array.isArray(value.definitions) ? value.definitions.length : null,
        placements: Array.isArray(value.placements) ? value.placements.length : null,
        expandedSurfaces: Array.isArray(value.surfaces) ? value.surfaces.length : null,
    };
    console.log(`ISSUE754 PRODUCTION ${JSON.stringify(result)}`);
    return result;
}

(async () => {
    const worker = workerModule.createRuntimeRenderableWorker({
        installRoot,
        projectRoot: openedProjectRoot,
        previewExe,
        parseOutput: runtimeBridge.parseRenderableOutput,
        timeoutMs: 30000,
        startupTimeoutMs: 15000,
    });
    const results = [];
    try {
        results.push(await measureCompile(worker, 'first-request', map));
        results.push(await measureCompile(worker, 'identical-revision-second', JSON.parse(JSON.stringify(map))));

        const changed = JSON.parse(JSON.stringify(map));
        changed.name = `${changed.name || `Map ${map.id}`} [production worker transient revision]`;
        results.push(await measureCompile(worker, 'changed-transient-map', changed));

        worker.invalidate('benchmark forced non-transient authority invalidation');
        results.push(await measureCompile(worker, 'forced-invalidation-rebuild', map));
    } finally {
        await worker.shutdown();
    }

    const [first, identical, changed, invalidated] = results;
    if (!first.pid || identical.pid !== first.pid || changed.pid !== first.pid) {
        throw new Error('warm production requests did not reuse one worker generation');
    }
    if (!invalidated.pid || invalidated.pid === first.pid) {
        throw new Error('forced authority invalidation did not rebuild the worker generation');
    }
    if (results.some(result => result.definitions !== null || result.placements !== null)) {
        throw new Error('benchmark measured after compatibility expansion instead of compact response state');
    }

    // decodeTransport mutates compact objects in place, so compact definitions are
    // checked through the production parser before decode by response size plus
    // the worker's real runtime test. The headline here is hardened lifecycle cost.
    console.log('ISSUE754 PRODUCTION SUMMARY');
    console.log(JSON.stringify({
        map: String(map.id),
        note: 'Production runtime-renderable-worker.js, including stage-input fingerprint, compact bridge response, serial generation reuse, explicit invalidation rebuild and ordinary Studio compatibility decode.',
        results,
    }, null, 2));
})().catch(error => {
    console.error(error && error.stack || error);
    process.exitCode = 1;
});
