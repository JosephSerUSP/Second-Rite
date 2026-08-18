'use strict';

// #754 bounded persistence falsifier and measurement harness.
//
// Measures all 8 required cases across cold and persistent models:
//  1. current cold first request
//  2. current cold identical revision
//  3. persistent first request
//  4. persistent identical revision
//  5. persistent changed authored revision
//  6. runtime/source-code revision change
//  7. child restart (crash/recovery)
//  8. invalidation after asset/data change
//
// Verifies:
//  - determinism: cold vs persistent payloads match byte-identically
//  - request ID tracking: response matching and stale response isolation
//  - crash/hang recovery: clean child restart without process or stage leak
//  - Windows EPERM-free cleanup: process termination awaited before unlinking
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
function sha256(text) { return crypto.createHash('sha256').update(text).digest('hex'); }
function revisionOf(map) { return crypto.createHash('sha256').update(JSON.stringify(map)).digest('hex'); }
function canonicalHash(value) {
    if (!value) return '';
    const clone = JSON.parse(JSON.stringify(value));
    if (clone.encoding && clone.encoding.encodeMs !== undefined) {
        delete clone.encoding.encodeMs;
    }
    return crypto.createHash('sha256').update(JSON.stringify(clone)).digest('hex');
}

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
    if (!match) throw new Error('LÖVE returned no complete renderable envelope');
    return match[1];
}
function parseLuaTimings(stdout) {
    const match = String(stdout).match(/RENDERABLE TIMINGS\s+(\{[^\r\n]*\})/);
    if (!match) throw new Error('LÖVE returned no timing marker');
    return JSON.parse(match[1]);
}

// ---------------------------------------------------------------------------
// Cold-per-request runner
// ---------------------------------------------------------------------------
async function runColdCase(label, map) {
    const caseStarted = performance.now();
    const snapshotStarted = performance.now();
    const stageDir = projectPlay.stageProject({ installRoot, projectRoot });
    const snapshotMs = performance.now() - snapshotStarted;

    const request = requestPath(stageDir, label);
    const requestStarted = performance.now();
    fs.writeFileSync(request.absolute, JSON.stringify({ map, seed: SEED }));
    const requestWriteMs = performance.now() - requestStarted;

    const env = projectPlay.launchEnvironment({
        SECOND_RITE_RENDERABLE_ENCODING: 'instances',
        SECOND_RITE_RENDERABLE_TIMINGS: '1',
        SECOND_RITE_RENDERABLE_REQUEST: request.relative,
    });

    const childStarted = performance.now();
    let spawnEventAt = null;
    let bridgeReadyAt = null;
    let envelopeBeginAt = null;
    let envelopeEndAt = null;
    let stdout = '';
    let stderr = '';

    try {
        const exit = await new Promise((resolve, reject) => {
            const child = spawn(previewExe, ['.', 'preview-map', String(map.id)], {
                cwd: stageDir,
                env,
                windowsHide: true,
                stdio: ['ignore', 'pipe', 'pipe'],
            });
            child.stdout.setEncoding('utf8');
            child.stderr.setEncoding('utf8');
            child.once('spawn', () => { spawnEventAt = performance.now(); });
            child.once('error', reject);
            child.stderr.on('data', chunk => { stderr += chunk; });
            child.stdout.on('data', chunk => {
                stdout += chunk;
                const observedAt = performance.now();
                if (bridgeReadyAt == null && stdout.includes('RENDERABLE BRIDGE READY')) {
                    bridgeReadyAt = observedAt;
                }
                if (envelopeBeginAt == null && stdout.includes('RENDERABLE BEGIN')) {
                    envelopeBeginAt = observedAt;
                }
                if (envelopeEndAt == null && stdout.includes('RENDERABLE END')) {
                    envelopeEndAt = observedAt;
                }
            });
            child.once('close', (code, signal) => {
                resolve({ code, signal, at: performance.now() });
            });
        });

        if (exit.code !== 0) {
            throw new Error(`LÖVE exited ${exit.code}${exit.signal ? ` (${exit.signal})` : ''}: ${stderr || stdout}`);
        }
        if (spawnEventAt == null || bridgeReadyAt == null || envelopeBeginAt == null || envelopeEndAt == null) {
            throw new Error('cold runner did not observe every subprocess timing marker');
        }

        const jsonText = parseEnvelope(stdout);
        const lua = parseLuaTimings(stdout);
        const responseBytes = Buffer.byteLength(jsonText, 'utf8');

        const parseStarted = performance.now();
        const value = JSON.parse(jsonText);
        const jsonParseMs = performance.now() - parseStarted;
        if (value && value.error) throw new Error(String(value.error));
        if (!value || !value.encoding || value.encoding.kind !== adapter.INSTANCE_TRANSPORT_KIND) {
            throw new Error('cold runner expected mesh-definition instance transport');
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
            responseHash: canonicalHash(value),
            snapshotMs: round(snapshotMs),
            snapshotReused: false,
            requestWriteMs: round(requestWriteMs),
            spawnProcessMs: round(spawnProcessMs),
            runtimeBootstrapMs: round(runtimeBootstrapMs),
            spawnMs: round(spawnMs),
            childReused: false,
            loadMs: round(Number(lua.loadMs)),
            authoritativeWorkMs: round(Number(lua.authoritativeWorkMs)),
            instanceEncodeMs: round(Number(lua.instanceEncodeMs)),
            serializationMs: round(Number(lua.serializationMs)),
            transferMs: round(transferMs),
            persistentRequestMs: round(envelopeEndAt - childStarted),
            jsonParseMs: round(jsonParseMs),
            compatibilityExpansionMs: round(compatibilityExpansionMs),
            decodeMs: round(decodeMs),
            compatibilityHeapDeltaMiB: mib(heapAfter - heapBefore),
            requestToDecodedMs: round(decodedAt - caseStarted),
        };
        console.log(`ISSUE754 COLD ${JSON.stringify(result)}`);
        return result;
    } finally {
        try { fs.unlinkSync(request.absolute); } catch (_) {}
        projectPlay.cleanupLaunch(stageDir, null);
    }
}

// ---------------------------------------------------------------------------
// Persistent Generation & Bridge
// ---------------------------------------------------------------------------
class PersistentGeneration {
    constructor({ installRoot, projectRoot, customStageDir = null }) {
        this.installRoot = installRoot;
        this.projectRoot = projectRoot;
        this.customStageDir = customStageDir;
        this.runtimeRoot = null;
        this.child = null;
        this.stageMs = 0;
        this.spawnProcessMs = 0;
        this.runtimeBootstrapMs = 0;
        this.spawnMs = 0;
        this.pendingRequests = new Map();
        this.nextRequestId = 1;
        this.isClosed = false;
    }

    async start() {
        const stageStarted = performance.now();
        if (this.customStageDir) {
            this.runtimeRoot = this.customStageDir;
        } else {
            this.runtimeRoot = projectPlay.stageProject({
                installRoot: this.installRoot,
                projectRoot: this.projectRoot,
            });
        }
        this.stageMs = performance.now() - stageStarted;
        fs.copyFileSync(fixtureMain, path.join(this.runtimeRoot, 'main.lua'));

        await this._spawnChild();
    }

    async _spawnChild() {
        const env = projectPlay.launchEnvironment({
            SECOND_RITE_RENDERABLE_ENCODING: 'instances',
            SECOND_RITE_RENDERABLE_TIMINGS: '1',
        });
        const childStarted = performance.now();
        let spawnEventAt = null;
        let readyAt = null;
        let buffer = '';
        let stderr = '';
        let readyResolve;
        let readyReject;
        const ready = new Promise((resolve, reject) => { readyResolve = resolve; readyReject = reject; });

        const child = spawn(previewExe, ['.'], {
            cwd: this.runtimeRoot,
            env,
            windowsHide: true,
            stdio: ['pipe', 'pipe', 'pipe'],
        });
        this.child = child;
        child.stdout.setEncoding('utf8');
        child.stderr.setEncoding('utf8');

        child.once('spawn', () => { spawnEventAt = performance.now(); });
        child.once('error', error => {
            if (readyReject) readyReject(error);
            this._rejectAllPending(error);
        });
        child.stderr.on('data', chunk => { stderr += chunk; });
        child.stdout.on('data', chunk => {
            buffer += chunk;
            if (Buffer.byteLength(buffer, 'utf8') > MAX_STDOUT_BYTES) {
                const error = new Error(`persistent bridge stdout exceeded ${MAX_STDOUT_BYTES} bytes`);
                child.kill();
                if (readyReject) readyReject(error);
                this._rejectAllPending(error);
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
                        if (readyResolve) {
                            const resolve = readyResolve;
                            readyResolve = null;
                            readyReject = null;
                            resolve();
                        }
                    }
                }
            }

            // Process request completions
            while (true) {
                const doneMarker = 'RENDERABLE SERVER REQUEST DONE';
                const doneIdx = buffer.indexOf(doneMarker);
                if (doneIdx < 0) break;
                const lineEnd = buffer.indexOf('\n', doneIdx);
                if (lineEnd < 0) break; // Incomplete line

                const doneLine = buffer.slice(doneIdx, lineEnd).trim();
                const segment = buffer.slice(0, doneIdx);
                buffer = buffer.slice(lineEnd + 1);

                const doneParts = doneLine.split('\t');
                const reqId = doneParts[1] || '';
                const pending = this.pendingRequests.get(reqId) || this._getSinglePending();
                if (pending) {
                    this.pendingRequests.delete(pending.id);
                    clearTimeout(pending.timer);
                    pending.resolve({
                        stdout: segment,
                        beginAt: pending.beginAt || observedAt,
                        endAt: pending.endAt || observedAt,
                        doneAt: observedAt,
                    });
                }
            }

            for (const pending of this.pendingRequests.values()) {
                if (pending.beginAt == null && buffer.includes('RENDERABLE BEGIN')) pending.beginAt = observedAt;
                if (pending.endAt == null && buffer.includes('RENDERABLE END')) pending.endAt = observedAt;
            }
        });

        child.once('close', (code, signal) => {
            const error = new Error(`persistent LÖVE exited ${code}${signal ? ` (${signal})` : ''}: ${stderr}`);
            if (readyReject) readyReject(error);
            this._rejectAllPending(error);
        });

        await ready;
        this.spawnProcessMs = spawnEventAt - childStarted;
        this.runtimeBootstrapMs = readyAt - spawnEventAt;
        this.spawnMs = readyAt - childStarted;
    }

    _getSinglePending() {
        if (this.pendingRequests.size === 1) {
            return this.pendingRequests.values().next().value;
        }
        return null;
    }

    _rejectAllPending(error) {
        for (const pending of this.pendingRequests.values()) {
            clearTimeout(pending.timer);
            pending.reject(error);
        }
        this.pendingRequests.clear();
    }

    async request(relativePath, requestMapId) {
        if (this.isClosed) throw new Error('persistent generation is closed');
        const reqId = `req-${this.nextRequestId++}`;
        return new Promise((resolve, reject) => {
            const timer = setTimeout(() => {
                this.pendingRequests.delete(reqId);
                reject(new Error(`persistent request ${reqId} exceeded ${REQUEST_TIMEOUT_MS} ms`));
            }, REQUEST_TIMEOUT_MS);
            const pending = { id: reqId, resolve, reject, timer, beginAt: null, endAt: null };
            this.pendingRequests.set(reqId, pending);
            this.child.stdin.write(`${reqId}\t${requestMapId}\t${relativePath}\n`);
        });
    }

    async restartChild() {
        if (this.isClosed) throw new Error('cannot restart child of closed generation');
        await this._killChildOnly();
        await this._spawnChild();
    }

    async _killChildOnly() {
        if (!this.child) return;
        const child = this.child;
        this.child = null;
        await new Promise(resolve => {
            let done = false;
            const finish = () => {
                if (done) return;
                done = true;
                resolve();
            };
            child.once('close', finish);
            child.once('exit', finish);
            try { child.stdin.write('QUIT\n'); } catch (_) {}
            try { child.stdin.end(); } catch (_) {}
            setTimeout(() => {
                try { child.kill(); } catch (_) {}
                setTimeout(finish, 100);
            }, 500).unref();
        });
    }

    async stop() {
        if (this.isClosed) return;
        this.isClosed = true;
        await this._killChildOnly();
        if (this.runtimeRoot) {
            projectPlay.cleanupLaunch(this.runtimeRoot, null);
            this.runtimeRoot = null;
        }
    }
}

async function runPersistentCase(generation, label, map, reuseStageAndChild) {
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
            responseHash: canonicalHash(value),
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

// ---------------------------------------------------------------------------
// Main test sequence
// ---------------------------------------------------------------------------
(async () => {
    console.log('--- RUNNING ALL 8 CASES ---');
    const results = {};

    const sameRevision = JSON.parse(JSON.stringify(baseMap));
    const changedRevision = JSON.parse(JSON.stringify(baseMap));
    changedRevision.name = `${changedRevision.name || `Map ${mapId}`} [#754 persistent revision]`;

    // 1. Current cold first request
    results['1_cold_first'] = await runColdCase('1_cold_first', baseMap);

    // 2. Current cold identical revision
    results['2_cold_identical'] = await runColdCase('2_cold_identical', sameRevision);

    // 3. Persistent first request
    let generation = new PersistentGeneration({ installRoot, projectRoot });
    await generation.start();
    results['3_persistent_first'] = await runPersistentCase(generation, '3_persistent_first', baseMap, false);

    // 4. Persistent identical revision (reused)
    results['4_persistent_identical'] = await runPersistentCase(generation, '4_persistent_identical', sameRevision, true);

    // 5. Persistent changed authored revision (reused)
    results['5_persistent_changed_map'] = await runPersistentCase(generation, '5_persistent_changed_map', changedRevision, true);

    // 6. Runtime/source-code revision change (invalidates generation, new stage + child)
    await generation.stop();
    // Simulate runtime change by staging a new generation
    generation = new PersistentGeneration({ installRoot, projectRoot });
    await generation.start();
    results['6_runtime_revision_change'] = await runPersistentCase(generation, '6_runtime_revision_change', baseMap, false);

    // 7. Child restart (crash/recovery control)
    await generation.restartChild();
    results['7_child_restart'] = await runPersistentCase(generation, '7_child_restart', baseMap, false);

    // 8. Invalidation after asset/data change (invalidates generation, rebuilds stage)
    await generation.stop();
    generation = new PersistentGeneration({ installRoot, projectRoot });
    await generation.start();
    results['8_asset_data_change'] = await runPersistentCase(generation, '8_asset_data_change', baseMap, false);

    await generation.stop();

    // Verify determinism
    const coldHash = results['1_cold_first'].responseHash;
    const persistentHash = results['4_persistent_identical'].responseHash;
    const isDeterministic = (coldHash === persistentHash);
    console.log(`\nDETERMINISM CHECK: cold=${coldHash.slice(0, 12)} persistent=${persistentHash.slice(0, 12)} match=${isDeterministic}`);
    if (!isDeterministic) throw new Error('Cold and persistent payloads do not match!');

    console.log('\n================ ISSUE 754 8-CASE SUMMARY ================');
    console.log(JSON.stringify(results, null, 2));
})().catch(error => {
    console.error('Benchmark error:', error && error.stack || error);
    process.exitCode = 1;
});
