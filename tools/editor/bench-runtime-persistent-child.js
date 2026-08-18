'use strict';

// #754 bounded persistence falsifier. This does NOT add a production daemon.
// Each bridge generation owns one disposable Test-Play stage plus one LÖVE
// process. Repeated transient map snapshots are sent over stdin to a benchmark-
// only staged main.lua which delegates every request to the existing runtime
// bridge authority. A fresh generation is used for the restart control.
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const { spawn } = require('node:child_process');
const { performance } = require('node:perf_hooks');
const authoredStorage = require('./authored-storage');
const projectPlay = require('./project-play');
const adapter = require('./js/second-rite-editor-adapter.js');

const SEED = 1735689600;
const MAX_STDOUT_BYTES = 16 * 1024 * 1024;
const REQUEST_TIMEOUT_MS = 30000;

function argument(name, fallback) {
    const index = process.argv.indexOf(name);
    return index >= 0 && process.argv[index + 1] ? process.argv[index + 1] : fallback;
}
function round(value) { return value == null || !Number.isFinite(value) ? null : Number(value.toFixed(3)); }
function mib(bytes) { return Number((bytes / (1024 * 1024)).toFixed(3)); }
function revisionOf(map) { return crypto.createHash('sha256').update(JSON.stringify(map)).digest('hex'); }

const installRoot = path.resolve(argument('--install-root', path.join(__dirname, '..', '..')));
const projectRoot = path.resolve(argument('--project-root', path.join(installRoot, 'projects', 'hichaukitoden-game')));
const loveExe = path.resolve(argument('--love', process.env.LOVE_PATH || 'C:\\Program Files\\LOVE\\love.exe'));
const previewExe = /love\.exe$/i.test(loveExe) ? loveExe.replace(/love\.exe$/i, 'lovec.exe') : loveExe;
const mapId = argument('--map', '2');
const fixtureMain = path.join(__dirname, 'fixtures', 'issue754-persistent-renderable-main.lua');

if (!fs.existsSync(previewExe)) throw new Error(`LÖVE console executable not found: ${previewExe}`);
if (!fs.existsSync(fixtureMain)) throw new Error(`persistent bridge fixture missing: ${fixtureMain}`);

const loadedMaps = authoredStorage.loadOrderedCollection(path.join(projectRoot, 'data'), 'maps').entries;
const baseMap = loadedMaps.find(map => String(map.id) === String(mapId));
if (!baseMap) throw new Error(`Map ${mapId} not found in opened Project`);

function requestPath(runtimeRoot, label) {
    const relativeDir = path.join('tmp', 'issue-754-persistent');
    const absoluteDir = path.join(runtimeRoot, relativeDir);
    fs.mkdirSync(absoluteDir, { recursive: true });
    const name = `${process.pid}-${label}-${Date.now()}-${crypto.randomBytes(4).toString('hex')}.json`;
    return {
        absolute: path.join(absoluteDir, name),
        relative: path.join(relativeDir, name).split(path.sep).join('/'),
    };
}

function parseEnvelope(stdout) {
    const match = String(stdout).match(/RENDERABLE BEGIN\s*([\s\S]*?)\s*RENDERABLE END/);
    if (!match) throw new Error('persistent LÖVE returned no complete renderable envelope');
    return match[1];
}
function parseLuaTimings(stdout) {
    const match = String(stdout).match(/RENDERABLE TIMINGS\s+(\{[^\r\n]*\})/);
    if (!match) throw new Error('persistent LÖVE returned no timing marker');
    return JSON.parse(match[1]);
}

async function startGeneration() {
    const stageStarted = performance.now();
    const runtimeRoot = projectPlay.stageProject({ installRoot, projectRoot });
    const stageMs = performance.now() - stageStarted;
    fs.copyFileSync(fixtureMain, path.join(runtimeRoot, 'main.lua'));

    const env = projectPlay.launchEnvironment({
        SECOND_RITE_RENDERABLE_ENCODING: 'instances',
        SECOND_RITE_RENDERABLE_TIMINGS: '1',
    });
    const childStarted = performance.now();
    let spawnEventAt = null;
    let readyAt = null;
    let buffer = '';
    let stderr = '';
    let pending = null;
    let readyResolve;
    let readyReject;
    const ready = new Promise((resolve, reject) => { readyResolve = resolve; readyReject = reject; });

    const child = spawn(previewExe, ['.'], {
        cwd: runtimeRoot,
        env,
        windowsHide: true,
        stdio: ['pipe', 'pipe', 'pipe'],
    });
    child.stdout.setEncoding('utf8');
    child.stderr.setEncoding('utf8');
    child.once('spawn', () => { spawnEventAt = performance.now(); });
    child.once('error', error => {
        if (readyReject) readyReject(error);
        if (pending) pending.reject(error);
    });
    child.stderr.on('data', chunk => { stderr += chunk; });
    child.stdout.on('data', chunk => {
        buffer += chunk;
        if (Buffer.byteLength(buffer, 'utf8') > MAX_STDOUT_BYTES) {
            const error = new Error(`persistent bridge stdout exceeded ${MAX_STDOUT_BYTES} bytes`);
            child.kill();
            if (readyReject) readyReject(error);
            if (pending) pending.reject(error);
            return;
        }
        const observedAt = performance.now();
        if (readyAt == null) {
            const marker = buffer.indexOf('RENDERABLE SERVER READY');
            if (marker >= 0) {
                const lineEnd = buffer.indexOf('\n', marker);
                if (lineEnd >= 0) {
                    readyAt = observedAt;
                    buffer = buffer.slice(lineEnd + 1);
                    const resolve = readyResolve;
                    readyResolve = null;
                    readyReject = null;
                    resolve();
                }
            }
        }
        if (pending) {
            if (pending.beginAt == null && buffer.includes('RENDERABLE BEGIN')) pending.beginAt = observedAt;
            if (pending.endAt == null && buffer.includes('RENDERABLE END')) pending.endAt = observedAt;
            const done = buffer.indexOf('RENDERABLE SERVER REQUEST DONE');
            if (done >= 0) {
                const segment = buffer.slice(0, done);
                const lineEnd = buffer.indexOf('\n', done);
                buffer = lineEnd >= 0 ? buffer.slice(lineEnd + 1) : '';
                const current = pending;
                pending = null;
                clearTimeout(current.timer);
                current.resolve({
                    stdout: segment,
                    beginAt: current.beginAt,
                    endAt: current.endAt || observedAt,
                    doneAt: observedAt,
                });
            }
        }
    });
    child.once('close', (code, signal) => {
        const error = new Error(`persistent LÖVE exited ${code}${signal ? ` (${signal})` : ''}: ${stderr}`);
        if (readyReject) readyReject(error);
        if (pending) pending.reject(error);
    });

    await ready;
    if (spawnEventAt == null || readyAt == null) throw new Error('persistent bridge emitted no spawn/ready timing');

    return {
        runtimeRoot,
        child,
        stageMs,
        spawnProcessMs: spawnEventAt - childStarted,
        runtimeBootstrapMs: readyAt - spawnEventAt,
        spawnMs: readyAt - childStarted,
        async request(relativePath, requestMapId) {
            if (pending) throw new Error('persistent bridge accepts one serial benchmark request at a time');
            return new Promise((resolve, reject) => {
                const timer = setTimeout(() => {
                    pending = null;
                    reject(new Error(`persistent request exceeded ${REQUEST_TIMEOUT_MS} ms`));
                }, REQUEST_TIMEOUT_MS);
                pending = { resolve, reject, timer, beginAt: null, endAt: null };
                child.stdin.write(`${requestMapId}\t${relativePath}\n`);
            });
        },
        stop() {
            try { child.stdin.write('QUIT\n'); } catch (_) {}
            try { child.stdin.end(); } catch (_) {}
            setTimeout(() => { try { child.kill(); } catch (_) {} }, 500).unref();
            projectPlay.cleanupLaunch(runtimeRoot, null);
        },
    };
}

async function runCase(generation, label, map, reuseStageAndChild) {
    const caseStarted = performance.now();
    const request = requestPath(generation.runtimeRoot, label);
    const requestStarted = performance.now();
    fs.writeFileSync(request.absolute, JSON.stringify({ map, seed: SEED }));
    const requestWriteMs = performance.now() - requestStarted;
    try {
        const sentAt = performance.now();
        const response = await generation.request(request.relative, String(map.id));
        const jsonText = parseEnvelope(response.stdout);
        const lua = parseLuaTimings(response.stdout);
        const responseBytes = Buffer.byteLength(jsonText, 'utf8');

        const parseStarted = performance.now();
        const value = JSON.parse(jsonText);
        const jsonParseMs = performance.now() - parseStarted;
        if (value && value.error) throw new Error(String(value.error));
        if (!value || !value.encoding || value.encoding.kind !== adapter.INSTANCE_TRANSPORT_KIND) {
            throw new Error('persistent benchmark expected mesh-definition instance transport');
        }

        if (global.gc) global.gc();
        const heapBefore = process.memoryUsage().heapUsed;
        const compatStarted = performance.now();
        adapter.decodeTransport(value);
        const compatibilityExpansionMs = performance.now() - compatStarted;
        const heapAfter = process.memoryUsage().heapUsed;
        const decodedAt = performance.now();

        const result = {
            label,
            map: String(map.id),
            revision: revisionOf(map),
            processModel: reuseStageAndChild ? 'persistent-reused' : 'persistent-new-generation',
            responseMiB: mib(responseBytes),
            snapshotMs: round(reuseStageAndChild ? 0 : generation.stageMs),
            snapshotReused: !!reuseStageAndChild,
            requestWriteMs: round(requestWriteMs),
            spawnProcessMs: round(reuseStageAndChild ? 0 : generation.spawnProcessMs),
            runtimeBootstrapMs: round(reuseStageAndChild ? 0 : generation.runtimeBootstrapMs),
            spawnMs: round(reuseStageAndChild ? 0 : generation.spawnMs),
            childReused: !!reuseStageAndChild,
            loadMs: round(Number(lua.loadMs)),
            authoritativeWorkMs: round(Number(lua.authoritativeWorkMs)),
            instanceEncodeMs: round(Number(lua.instanceEncodeMs)),
            serializationMs: round(Number(lua.serializationMs)),
            transferMs: round(response.endAt - response.beginAt),
            persistentRequestMs: round(response.doneAt - sentAt),
            jsonParseMs: round(jsonParseMs),
            compatibilityExpansionMs: round(compatibilityExpansionMs),
            decodeMs: round(jsonParseMs + compatibilityExpansionMs),
            compatibilityHeapDeltaMiB: mib(heapAfter - heapBefore),
            requestToDecodedMs: round(decodedAt - caseStarted),
        };
        console.log(`ISSUE754 PERSISTENT ${JSON.stringify(result)}`);
        return result;
    } finally {
        try { fs.unlinkSync(request.absolute); } catch (_) {}
    }
}

(async () => {
    const sameRevision = JSON.parse(JSON.stringify(baseMap));
    const changedRevision = JSON.parse(JSON.stringify(baseMap));
    changedRevision.name = `${changedRevision.name || `Map ${mapId}`} [#754 persistent revision]`;
    const restartControl = JSON.parse(JSON.stringify(baseMap));

    let firstGeneration = null;
    let restartGeneration = null;
    try {
        firstGeneration = await startGeneration();
        const results = [];
        results.push(await runCase(firstGeneration, 'first-request', baseMap, false));
        results.push(await runCase(firstGeneration, 'identical-revision-second', sameRevision, true));
        results.push(await runCase(firstGeneration, 'changed-revision', changedRevision, true));
        firstGeneration.stop();
        firstGeneration = null;

        restartGeneration = await startGeneration();
        results.push(await runCase(restartGeneration, 'fresh-restart-control', restartControl, false));

        if (results[0].revision !== results[1].revision || results[1].revision === results[2].revision) {
            throw new Error('persistent benchmark revision controls are invalid');
        }
        console.log('ISSUE754 PERSISTENT SUMMARY');
        console.log(JSON.stringify({
            map: String(mapId),
            transport: adapter.INSTANCE_TRANSPORT_KIND,
            note: 'Benchmark-only persistent LÖVE authority. The same staged Project generation is reused for identical and changed transient Map revisions; fresh restart creates a new stage and child.',
            results,
        }, null, 2));
    } finally {
        if (firstGeneration) firstGeneration.stop();
        if (restartGeneration) restartGeneration.stop();
    }
})().catch(error => {
    console.error(error && error.stack || error);
    process.exitCode = 1;
});
