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
function heap() { if (global.gc) global.gc(); return process.memoryUsage().heapUsed; }

const loveExe = path.resolve(arg('--love', process.env.LOVE_PATH || process.env.LOVEC || 'C:\\Program Files\\LOVE\\love.exe'));
const previewExe = runtimeBridge.resolvePreviewExe(loveExe);
const installRoot = path.resolve(arg('--install-root', projectRoot.INSTALL_ROOT));
const openedProjectRoot = path.resolve(arg('--project-root', projectRoot.PROJECT_ROOT));
const maps = authoredStorage.loadOrderedCollection(path.join(openedProjectRoot, 'data'), 'maps').entries;
const map = maps.find(candidate => String(candidate.id) === String(arg('--map', '2')));
if (!map) throw new Error('benchmark Map fixture not found');
if (!fs.existsSync(previewExe)) throw new Error(`LÖVE console executable not found: ${previewExe}`);

function prepareDirect(value, requestMap) {
    const before = heap();
    const started = performance.now();
    adapter.applyRenderableModulation(value, requestMap.vertexShadingLayers || []);
    const elapsed = performance.now() - started;
    const after = process.memoryUsage().heapUsed;
    if (!value.encoding || value.encoding.kind !== 'mesh-definitions-v1') {
        throw new Error('post-#766 benchmark did not retain mesh-definitions-v1');
    }
    if (!Array.isArray(value.definitions) || !Array.isArray(value.placements)) {
        throw new Error('post-#766 direct consumer lost definitions or placements');
    }
    return { directPrepMs: round(elapsed), directHeapDeltaMiB: mib(after - before) };
}

async function coldRequest(requestMap) {
    const started = performance.now();
    const value = await runtimeBridge.compileRenderable({
        map: requestMap,
        seed: 1735689600,
        renderableEncoding: 'instances',
    }, {
        installRoot,
        projectRoot: openedProjectRoot,
        previewExe,
    });
    const compiled = performance.now();
    const compactMiB = mib(Buffer.byteLength(JSON.stringify(value), 'utf8'));
    const direct = prepareDirect(value, requestMap);
    return {
        label: 'cold-one-shot',
        runtimeMs: round(compiled - started),
        endToDirectReadyMs: round(performance.now() - started),
        compactMiB,
        ...direct,
        definitions: value.definitions.length,
        placements: value.placements.length,
        literalSurfaces: Array.isArray(value.surfaces) ? value.surfaces.length : null,
    };
}

async function workerRequest(worker, label, requestMap) {
    const started = performance.now();
    const value = await worker.compile({ map: requestMap, seed: 1735689600, renderableEncoding: 'instances' });
    const compiled = performance.now();
    const state = worker.state();
    const compactMiB = mib(Buffer.byteLength(JSON.stringify(value), 'utf8'));
    const direct = prepareDirect(value, requestMap);
    return {
        label,
        runtimeMs: round(compiled - started),
        endToDirectReadyMs: round(performance.now() - started),
        compactMiB,
        ...direct,
        pid: state.generation && state.generation.pid,
        definitions: value.definitions.length,
        placements: value.placements.length,
        literalSurfaces: Array.isArray(value.surfaces) ? value.surfaces.length : null,
    };
}

(async () => {
    const results = [];
    results.push(await coldRequest(map));

    const worker = workerModule.createRuntimeRenderableWorker({
        installRoot,
        projectRoot: openedProjectRoot,
        previewExe,
        parseOutput: runtimeBridge.parseRenderableOutput,
        timeoutMs: 30000,
        startupTimeoutMs: 15000,
    });
    try {
        results.push(await workerRequest(worker, 'persistent-first-generation', map));
        results.push(await workerRequest(worker, 'persistent-identical-reuse', JSON.parse(JSON.stringify(map))));
        const changed = JSON.parse(JSON.stringify(map));
        changed.name = `${changed.name || `Map ${map.id}`} [issue754 transient]`;
        results.push(await workerRequest(worker, 'persistent-changed-transient-reuse', changed));
        worker.invalidate('benchmark forced non-transient authority invalidation');
        results.push(await workerRequest(worker, 'persistent-forced-rebuild', map));
    } finally {
        await worker.shutdown();
    }

    const first = results[1], identical = results[2], changed = results[3], rebuilt = results[4];
    if (!first.pid || identical.pid !== first.pid || changed.pid !== first.pid) {
        throw new Error('warm requests did not reuse one runtime generation');
    }
    if (!rebuilt.pid || rebuilt.pid === first.pid) {
        throw new Error('non-transient invalidation did not rebuild the generation');
    }

    console.log('ISSUE754 POST766 SUMMARY');
    console.log(JSON.stringify({
        map: String(map.id),
        note: 'Current main after #766: compact mesh-definitions-v1 stays compact through direct placement-colour preparation; no compatibility expansion is measured.',
        results,
    }, null, 2));
})().catch(error => {
    console.error(error && error.stack || error);
    process.exitCode = 1;
});
