'use strict';

// #754: measure the CURRENT cold-per-request Studio -> LÖVE renderable path
// after #761's lossless mesh-definition transport. This is deliberately a
// measurement harness, not a persistent-child implementation.
//
// Run with --expose-gc when heap deltas are desired:
//   node --expose-gc tools/editor/bench-runtime-request-stages.js \
//     --love <love.exe> --map 2
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

function argument(name, fallback) {
    const index = process.argv.indexOf(name);
    return index >= 0 && process.argv[index + 1] ? process.argv[index + 1] : fallback;
}

function round(value) {
    return value == null || !Number.isFinite(value) ? null : Number(value.toFixed(3));
}

function revisionOf(map) {
    return crypto.createHash('sha256').update(JSON.stringify(map)).digest('hex');
}

function mib(bytes) {
    return Number((bytes / (1024 * 1024)).toFixed(3));
}

const installRoot = path.resolve(argument('--install-root', path.join(__dirname, '..', '..')));
const projectRoot = path.resolve(argument('--project-root', path.join(installRoot, 'projects', 'hichaukitoden-game')));
const loveExe = path.resolve(argument('--love', process.env.LOVE_PATH || 'C:\\Program Files\\LOVE\\love.exe'));
const previewExe = /love\.exe$/i.test(loveExe) ? loveExe.replace(/love\.exe$/i, 'lovec.exe') : loveExe;
const mapId = argument('--map', '2');

if (!fs.existsSync(installRoot)) throw new Error(`install root not found: ${installRoot}`);
if (!fs.existsSync(projectRoot)) throw new Error(`project root not found: ${projectRoot}`);
if (!fs.existsSync(previewExe)) throw new Error(`LÖVE console executable not found: ${previewExe}`);

const loadedMaps = authoredStorage.loadOrderedCollection(path.join(projectRoot, 'data'), 'maps').entries;
const baseMap = loadedMaps.find(map => String(map.id) === String(mapId));
if (!baseMap) throw new Error(`Map ${mapId} not found in opened Project`);

function requestPath(runtimeRoot, label) {
    const relativeDir = path.join('tmp', 'issue-754-benchmark');
    const absoluteDir = path.join(runtimeRoot, relativeDir);
    fs.mkdirSync(absoluteDir, { recursive: true });
    const name = `${process.pid}-${label}-${Date.now()}-${crypto.randomBytes(4).toString('hex')}.json`;
    return {
        absolute: path.join(absoluteDir, name),
        relative: path.join(relativeDir, name).split(path.sep).join('/'),
    };
}

function parseEnvelope(stdout) {
    const match = stdout.match(/RENDERABLE BEGIN\s*([\s\S]*?)\s*RENDERABLE END/);
    if (!match) throw new Error('LÖVE returned no complete renderable envelope');
    return match[1];
}

function parseLuaTimings(stdout) {
    const match = stdout.match(/RENDERABLE TIMINGS\s+(\{[^\r\n]*\})/);
    if (!match) throw new Error('LÖVE returned no #754 timing marker');
    return JSON.parse(match[1]);
}

async function runCase(label, map) {
    const caseStarted = performance.now();
    let stageDir = null;
    let dataSnapshot = null;
    let runtimeRoot = null;
    let request = null;

    const snapshotStarted = performance.now();
    if (projectPlay.sameRoot(installRoot, projectRoot)) {
        dataSnapshot = projectPlay.snapshotSameRoot({ installRoot, projectRoot });
        runtimeRoot = projectRoot;
    } else {
        stageDir = projectPlay.stageProject({ installRoot, projectRoot });
        runtimeRoot = stageDir;
    }
    const snapshotMs = performance.now() - snapshotStarted;

    try {
        request = requestPath(runtimeRoot, label);
        const requestValue = { map, seed: SEED };
        const requestWriteStarted = performance.now();
        fs.writeFileSync(request.absolute, JSON.stringify(requestValue));
        const requestWriteMs = performance.now() - requestWriteStarted;

        const env = projectPlay.launchEnvironment({
            SECOND_RITE_RENDERABLE_REQUEST: request.relative,
            SECOND_RITE_RENDERABLE_ENCODING: 'instances',
            SECOND_RITE_RENDERABLE_TIMINGS: '1',
        }, dataSnapshot);

        const childStarted = performance.now();
        let spawnEventAt = null;
        let bridgeReadyAt = null;
        let envelopeBeginAt = null;
        let envelopeEndAt = null;
        let stdout = '';
        let stderr = '';

        const exit = await new Promise((resolve, reject) => {
            const child = spawn(previewExe, ['.', 'preview-map', String(map.id)], {
                cwd: runtimeRoot,
                env,
                windowsHide: true,
                stdio: ['ignore', 'pipe', 'pipe'],
            });
            child.once('spawn', () => { spawnEventAt = performance.now(); });
            child.once('error', reject);
            child.stdout.setEncoding('utf8');
            child.stderr.setEncoding('utf8');
            child.stdout.on('data', chunk => {
                stdout += chunk;
                if (Buffer.byteLength(stdout, 'utf8') > MAX_STDOUT_BYTES) {
                    child.kill();
                    reject(new Error(`benchmark stdout exceeded ${MAX_STDOUT_BYTES} bytes`));
                    return;
                }
                const observedAt = performance.now();
                if (bridgeReadyAt == null && stdout.includes('RENDERABLE BRIDGE READY')) bridgeReadyAt = observedAt;
                if (envelopeBeginAt == null && stdout.includes('RENDERABLE BEGIN')) envelopeBeginAt = observedAt;
                if (envelopeEndAt == null && stdout.includes('RENDERABLE END')) envelopeEndAt = observedAt;
            });
            child.stderr.on('data', chunk => { stderr += chunk; });
            child.once('close', (code, signal) => resolve({ code, signal, at: performance.now() }));
        });

        if (exit.code !== 0) {
            throw new Error(`LÖVE exited ${exit.code}${exit.signal ? ` (${exit.signal})` : ''}: ${stderr || stdout}`);
        }
        if (spawnEventAt == null || bridgeReadyAt == null || envelopeBeginAt == null || envelopeEndAt == null) {
            throw new Error('benchmark did not observe every subprocess timing marker');
        }

        const jsonText = parseEnvelope(stdout);
        const lua = parseLuaTimings(stdout);
        const responseBytes = Buffer.byteLength(jsonText, 'utf8');

        const parseStarted = performance.now();
        const value = JSON.parse(jsonText);
        const jsonParseMs = performance.now() - parseStarted;
        if (value && value.error) throw new Error(String(value.error));
        if (!value || !value.encoding || value.encoding.kind !== adapter.INSTANCE_TRANSPORT_KIND) {
            throw new Error('benchmark expected #761 mesh-definition instance transport');
        }

        if (global.gc) global.gc();
        const heapBefore = process.memoryUsage().heapUsed;
        const compatStarted = performance.now();
        adapter.decodeTransport(value);
        const compatibilityExpansionMs = performance.now() - compatStarted;
        const heapAfter = process.memoryUsage().heapUsed;
        const decodedAt = performance.now();

        const spawnProcessMs = spawnEventAt - childStarted;
        const runtimeBootstrapMs = bridgeReadyAt - spawnEventAt;
        const spawnMs = bridgeReadyAt - childStarted;
        const transferMs = envelopeEndAt - envelopeBeginAt;
        const decodeMs = jsonParseMs + compatibilityExpansionMs;

        const result = {
            label,
            map: String(map.id),
            revision: revisionOf(map),
            processModel: 'cold-per-request',
            responseMiB: mib(responseBytes),
            snapshotMs: round(snapshotMs),
            requestWriteMs: round(requestWriteMs),
            spawnProcessMs: round(spawnProcessMs),
            runtimeBootstrapMs: round(runtimeBootstrapMs),
            spawnMs: round(spawnMs),
            loadMs: round(Number(lua.loadMs)),
            authoritativeWorkMs: round(Number(lua.authoritativeWorkMs)),
            instanceEncodeMs: round(Number(lua.instanceEncodeMs)),
            serializationMs: round(Number(lua.serializationMs)),
            transferMs: round(transferMs),
            jsonParseMs: round(jsonParseMs),
            compatibilityExpansionMs: round(compatibilityExpansionMs),
            decodeMs: round(decodeMs),
            compatibilityHeapDeltaMiB: mib(heapAfter - heapBefore),
            childTotalMs: round(exit.at - childStarted),
            requestToDecodedMs: round(decodedAt - caseStarted),
        };
        console.log(`ISSUE754 ${JSON.stringify(result)}`);
        return result;
    } finally {
        if (request) {
            try { fs.unlinkSync(request.absolute); } catch (error) { /* cleanup only */ }
        }
        projectPlay.cleanupLaunch(stageDir, dataSnapshot);
    }
}

(async () => {
    const sameRevision = JSON.parse(JSON.stringify(baseMap));
    const changedRevision = JSON.parse(JSON.stringify(baseMap));
    changedRevision.name = `${changedRevision.name || `Map ${mapId}`} [#754 timing revision]`;
    const restartControl = JSON.parse(JSON.stringify(baseMap));

    const results = [];
    results.push(await runCase('first-request', baseMap));
    results.push(await runCase('identical-revision-second', sameRevision));
    results.push(await runCase('changed-revision', changedRevision));
    // The production baseline owns no reusable child: every call above is
    // already a fresh process. This fourth request is therefore the explicit
    // fresh-restart/cold control the persistent-child experiment must beat.
    results.push(await runCase('fresh-restart-control', restartControl));

    const identical = results[0].revision === results[1].revision;
    const changed = results[1].revision !== results[2].revision;
    if (!identical || !changed) throw new Error('benchmark revision controls are invalid');

    console.log('ISSUE754 SUMMARY');
    console.log(JSON.stringify({
        map: String(mapId),
        transport: adapter.INSTANCE_TRANSPORT_KIND,
        note: 'Every case is cold-per-request. Same-revision reuse does not exist in the baseline.',
        results,
    }, null, 2));
})().catch(error => {
    console.error(error && error.stack || error);
    process.exitCode = 1;
});
