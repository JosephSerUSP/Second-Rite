'use strict';

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const { spawn: nodeSpawn, spawnSync: nodeSpawnSync } = require('child_process');
const projectRootAuthority = require('./project-root');
const projectPlay = require('./project-play');
const semanticRoots = require('../semantic-roots');
const exportGame = require('../export/export-game');

const READY_MARKER = 'RENDERABLE WORKER READY';
const REQUEST_MARKER = 'RENDERABLE WORKER REQUEST';
const DONE_MARKER = 'RENDERABLE WORKER REQUEST DONE';
const ERROR_MARKER = 'RENDERABLE WORKER ERROR';
const DEFAULT_TIMEOUT_MS = 60000;
const DEFAULT_STARTUP_TIMEOUT_MS = 15000;
const DEFAULT_SHUTDOWN_TIMEOUT_MS = 2000;
const DEFAULT_MAX_OUTPUT_BYTES = 64 * 1024 * 1024;
const DEFAULT_MAX_DIAGNOSTIC_BYTES = 1024 * 1024;
const MAX_PROTOCOL_TOKEN_BYTES = 1024;
const WORKER_MAIN = path.join(__dirname, 'runtime-renderable-worker-main.lua');
const SLEEP_ARRAY = new Int32Array(new SharedArrayBuffer(4));
const GENERATED_RUNTIME_INPUTS = Object.freeze([
    path.join('tools', 'export', 'runtime-semantic-resources.lua'),
    path.join('tools', 'export', 'runtime-engine-server.lua'),
]);

function resolvePreviewExe(loveExe) {
    const configured = loveExe || process.env.LOVE_PATH || 'C:\\Program Files\\LOVE\\love.exe';
    const lovec = configured.replace(/love\.exe$/i, 'lovec.exe');
    try {
        if (lovec !== configured && fs.existsSync(lovec)) return lovec;
    } catch (_) { /* fall through */ }
    return configured;
}

function normalizeRelative(root, target) {
    return path.relative(root, target).split(path.sep).join('/');
}

function fileChangeIdentity(stat) {
    // mtime+size alone is not an authority contract: editors can preserve mtime
    // and rewrite same-size content. ctime is changed by such rewrites, while
    // dev+ino/birthtime also catch atomic replacement. These fields only decide
    // whether an already-computed CONTENT digest may be reused; the generation
    // revision itself is still made from SHA-256 content digests.
    return [
        stat.dev,
        stat.ino,
        stat.size,
        stat.mtimeNs,
        stat.ctimeNs,
        stat.birthtimeNs,
    ].map(value => String(value)).join(':');
}

function contentDigest(filePath, stat, digestCache) {
    const cacheKey = path.resolve(filePath);
    const identity = fileChangeIdentity(stat);
    const cached = digestCache && digestCache.get(cacheKey);
    if (cached && cached.identity === identity) return cached.digest;

    const hash = crypto.createHash('sha256');
    const fd = fs.openSync(filePath, 'r');
    const buffer = Buffer.allocUnsafe(64 * 1024);
    try {
        let bytesRead;
        do {
            bytesRead = fs.readSync(fd, buffer, 0, buffer.length, null);
            if (bytesRead > 0) hash.update(buffer.subarray(0, bytesRead));
        } while (bytesRead > 0);
    } finally {
        fs.closeSync(fd);
    }
    const digest = hash.digest();
    if (digestCache) digestCache.set(cacheKey, { identity, digest });
    return digest;
}

function appendTreeContent(hash, root, target, digestCache) {
    const relative = normalizeRelative(root, target) || '.';
    let stat;
    try {
        stat = fs.statSync(target, { bigint: true });
    } catch (error) {
        if (error && error.code === 'ENOENT') {
            if (digestCache) digestCache.delete(path.resolve(target));
            hash.update(`missing\0${relative}\0`);
            return;
        }
        throw error;
    }

    if (stat.isDirectory()) {
        hash.update(`d\0${relative}\0`);
        const names = fs.readdirSync(target).sort();
        for (const name of names) appendTreeContent(hash, root, path.join(target, name), digestCache);
        return;
    }

    hash.update(`f\0${relative}\0${stat.size}\0`);
    hash.update(contentDigest(target, stat, digestCache));
    hash.update('\0');
}

// Revision identity is content-true, not mtime/size-true. A same-size edit with
// preserved mtime must still invalidate a live generation. A process-scoped
// digest cache avoids rereading unchanged large assets, but only while strong
// filesystem change identity (ctime + file identity + size/mtime) is unchanged.
// The inputs are exactly the source material the ordinary external-Project stage
// reads: manifest-selected runtime files/directories, generated runtime provider
// files, Project data + manifest-selected Project directories + project.json,
// and the pinned RTP tree. The unsaved Map request is deliberately NOT part of
// this identity because it is overlaid inside the disposable stage per request.
function runtimeAuthorityRevision(options = {}) {
    const installRoot = path.resolve(options.installRoot || projectRootAuthority.INSTALL_ROOT);
    const openedProjectRoot = path.resolve(options.projectRoot || projectRootAuthority.PROJECT_ROOT);
    const roots = semanticRoots.resolveSemanticRoots({
        installRoot,
        runtimeRoot: options.runtimeRoot,
        rtpRoot: options.rtpRoot,
        projectRoot: openedProjectRoot,
        env: {},
    });
    const manifestPath = path.resolve(options.manifestPath
        || path.join(installRoot, 'tools', 'export', 'runtime-manifest.json'));
    const manifest = exportGame.readManifest(manifestPath);
    const digestCache = options.digestCache || null;
    const hash = crypto.createHash('sha256');

    appendTreeContent(hash, installRoot, manifestPath, digestCache);
    for (const relative of manifest.rootFiles) {
        appendTreeContent(hash, roots.runtimeRoot, path.join(roots.runtimeRoot, relative), digestCache);
    }
    for (const relative of manifest.runtimeDirectories) {
        appendTreeContent(hash, roots.runtimeRoot, path.join(roots.runtimeRoot, relative), digestCache);
    }
    appendTreeContent(hash, roots.runtimeRoot, path.join(roots.runtimeRoot, manifest.releaseConfig), digestCache);
    for (const relative of GENERATED_RUNTIME_INPUTS) {
        appendTreeContent(hash, installRoot, path.join(installRoot, relative), digestCache);
    }
    appendTreeContent(hash, openedProjectRoot, path.join(openedProjectRoot, 'data'), digestCache);
    for (const relative of manifest.projectDirectories || []) {
        appendTreeContent(hash, openedProjectRoot, path.join(openedProjectRoot, relative), digestCache);
    }
    appendTreeContent(hash, openedProjectRoot, path.join(openedProjectRoot, 'project.json'), digestCache);
    appendTreeContent(hash, roots.rtpRoot, roots.rtpRoot, digestCache);
    return hash.digest('hex');
}

function requestFilePath(runtimeRoot) {
    const relativeDir = path.join('tmp', 'editor-renderable-worker');
    const absoluteDir = path.join(runtimeRoot, relativeDir);
    fs.mkdirSync(absoluteDir, { recursive: true });
    const name = `${process.pid}-${Date.now()}-${crypto.randomBytes(6).toString('hex')}.json`;
    return {
        absolute: path.join(absoluteDir, name),
        relative: path.join(relativeDir, name).split(path.sep).join('/'),
    };
}

function protocolMapId(request) {
    if (!request || !request.map || request.map.id === undefined || request.map.id === null
            || request.map.id === '') {
        throw new Error('runtime renderable worker request needs a map id');
    }
    const value = String(request.map.id);
    if (/[\t\r\n]/.test(value) || Buffer.byteLength(value, 'utf8') > MAX_PROTOCOL_TOKEN_BYTES) {
        throw new Error('runtime renderable worker map id cannot contain tab/newline framing characters or exceed 1 KiB');
    }
    return value;
}

function processIsAlive(pid) {
    if (!pid) return false;
    try {
        process.kill(pid, 0);
        return true;
    } catch (error) {
        return !!(error && error.code === 'EPERM');
    }
}

function waitForProcessExitSync(pid, timeoutMs) {
    const deadline = Date.now() + timeoutMs;
    while (processIsAlive(pid) && Date.now() < deadline) {
        Atomics.wait(SLEEP_ARRAY, 0, 0, 25);
    }
    return !processIsAlive(pid);
}

function appendBoundedDiagnostic(previous, chunk, maxBytes) {
    const combined = `${previous || ''}${chunk || ''}`;
    if (Buffer.byteLength(combined, 'utf8') <= maxBytes) return combined;
    const encoded = Buffer.from(combined, 'utf8');
    return `[earlier stderr truncated]\n${encoded.subarray(encoded.length - maxBytes).toString('utf8')}`;
}

function createRuntimeRenderableWorker(options = {}) {
    const installRoot = path.resolve(options.installRoot || projectRootAuthority.INSTALL_ROOT);
    const openedProjectRoot = path.resolve(options.projectRoot || projectRootAuthority.PROJECT_ROOT);
    const roots = semanticRoots.resolveSemanticRoots({
        installRoot,
        runtimeRoot: options.runtimeRoot,
        rtpRoot: options.rtpRoot,
        projectRoot: openedProjectRoot,
        env: {},
    });
    const manifestPath = path.resolve(options.manifestPath
        || path.join(installRoot, 'tools', 'export', 'runtime-manifest.json'));
    const previewExe = options.previewExe || resolvePreviewExe(options.loveExe);
    const stageProject = options.stageProject || projectPlay.stageProject;
    const removeStage = options.removeStage || projectPlay.removeStage;
    const spawn = options.spawn || nodeSpawn;
    const spawnSync = options.spawnSync || nodeSpawnSync;
    const parseOutput = options.parseOutput;
    const platform = options.platform || process.platform;
    const authorityDigestCache = options.authorityDigestCache || new Map();
    const authorityRevision = options.authorityRevision || (() => runtimeAuthorityRevision({
        installRoot,
        projectRoot: openedProjectRoot,
        runtimeRoot: roots.runtimeRoot,
        rtpRoot: roots.rtpRoot,
        manifestPath,
        digestCache: authorityDigestCache,
    }));
    // Which protocol route a request takes. Map renderables derive it from the
    // map id; the preview worker (runtime-preview-worker.js) supplies a command
    // name instead. Everything else about the generation lifecycle -- staging,
    // revision scoping, serial queueing, crash recovery -- is identical, which
    // is why it is one module and not two.
    const routeOf = options.routeOf || protocolMapId;
    const timeoutMs = options.timeoutMs || DEFAULT_TIMEOUT_MS;
    const startupTimeoutMs = options.startupTimeoutMs || DEFAULT_STARTUP_TIMEOUT_MS;
    const shutdownTimeoutMs = options.shutdownTimeoutMs || DEFAULT_SHUTDOWN_TIMEOUT_MS;
    const maxOutputBytes = options.maxOutputBytes || DEFAULT_MAX_OUTPUT_BYTES;
    const maxDiagnosticBytes = options.maxDiagnosticBytes || DEFAULT_MAX_DIAGNOSTIC_BYTES;
    const workerMain = options.workerMain || WORKER_MAIN;

    let generation = null;
    let invalidationEpoch = 0;
    let closed = false;
    let tail = Promise.resolve();
    let nextRequestId = 1;

    function enqueue(task) {
        const run = tail.then(task, task);
        tail = run.catch(() => {});
        return run;
    }

    function waitForClose(gen, timeout) {
        if (!gen || gen.closed) return Promise.resolve(true);
        return Promise.race([
            gen.closePromise.then(() => true),
            new Promise(resolve => setTimeout(() => resolve(false), timeout)),
        ]);
    }

    async function stopChild(gen) {
        if (!gen || gen.closed) return;
        try { gen.child.stdin.write('QUIT\n'); } catch (_) {}
        try { gen.child.stdin.end(); } catch (_) {}
        if (await waitForClose(gen, shutdownTimeoutMs)) return;

        try { gen.child.kill('SIGTERM'); } catch (_) {}
        if (await waitForClose(gen, shutdownTimeoutMs)) return;

        if (platform === 'win32' && gen.child.pid) {
            try {
                spawnSync('taskkill.exe', ['/PID', String(gen.child.pid), '/T', '/F'], {
                    windowsHide: true,
                    stdio: 'ignore',
                    timeout: shutdownTimeoutMs,
                });
            } catch (_) {}
        } else {
            try { gen.child.kill('SIGKILL'); } catch (_) {}
        }
        if (!(await waitForClose(gen, shutdownTimeoutMs))) {
            throw new Error(`runtime renderable worker pid ${gen.child.pid || '(unknown)'} did not terminate; stage retained for safety`);
        }
    }

    function stopChildSync(gen) {
        if (!gen || gen.closed) return;
        try { gen.child.stdin.write('QUIT\n'); } catch (_) {}
        try { gen.child.stdin.end(); } catch (_) {}
        if (waitForProcessExitSync(gen.child.pid, Math.min(shutdownTimeoutMs, 500))) {
            gen.closed = true;
            return;
        }
        if (platform === 'win32' && gen.child.pid) {
            try {
                spawnSync('taskkill.exe', ['/PID', String(gen.child.pid), '/T', '/F'], {
                    windowsHide: true,
                    stdio: 'ignore',
                    timeout: shutdownTimeoutMs,
                });
            } catch (_) {}
        } else if (gen.child.pid) {
            try { process.kill(gen.child.pid, 'SIGTERM'); } catch (_) {}
        }
        if (!waitForProcessExitSync(gen.child.pid, shutdownTimeoutMs) && platform !== 'win32' && gen.child.pid) {
            try { process.kill(gen.child.pid, 'SIGKILL'); } catch (_) {}
        }
        if (!waitForProcessExitSync(gen.child.pid, shutdownTimeoutMs)) {
            throw new Error(`runtime renderable worker pid ${gen.child.pid || '(unknown)'} did not terminate synchronously; stage retained for safety`);
        }
        gen.closed = true;
    }

    async function disposeGeneration(gen = generation) {
        if (!gen) return;
        if (generation === gen) generation = null;
        try {
            await stopChild(gen);
        } finally {
            if (gen.closed) removeStage(gen.runtimeRoot);
        }
    }

    function disposeGenerationSync(gen = generation) {
        if (!gen) return;
        if (generation === gen) generation = null;
        stopChildSync(gen);
        if (gen.closed) removeStage(gen.runtimeRoot);
    }

    function rejectPending(gen, error) {
        if (!gen.pending) return;
        const pending = gen.pending;
        gen.pending = null;
        clearTimeout(pending.timer);
        pending.reject(error);
    }

    async function startGeneration(revision) {
        if (!fs.existsSync(previewExe)) throw new Error(`LÖVE not found at ${previewExe} (set LOVE_PATH)`);
        if (!fs.existsSync(workerMain)) throw new Error(`runtime renderable worker entrypoint is missing: ${workerMain}`);
        let runtimeRoot = null;
        let child = null;
        try {
            runtimeRoot = stageProject({
                installRoot,
                projectRoot: openedProjectRoot,
                runtimeRoot: roots.runtimeRoot,
                rtpRoot: roots.rtpRoot,
                manifestPath,
            });
            // A stage is only allowed to represent the source revision selected
            // before materialization. If files changed while copying/compiling,
            // reject this generation before an initialized LÖVE child can own it.
            if (authorityRevision() !== revision) {
                const error = new Error('runtime authority changed while staging renderable generation; retry');
                error.code = 'RUNTIME_AUTHORITY_CHANGED_DURING_STAGE';
                throw error;
            }
            fs.copyFileSync(workerMain, path.join(runtimeRoot, 'main.lua'));
            const env = projectPlay.launchEnvironment({ SECOND_RITE_RENDERABLE_ENCODING: 'instances' });
            child = spawn(previewExe, ['.'], {
                cwd: runtimeRoot,
                env,
                windowsHide: true,
                stdio: ['pipe', 'pipe', 'pipe'],
            });
        } catch (error) {
            if (runtimeRoot) {
                try { removeStage(runtimeRoot); } catch (_) {}
            }
            throw error;
        }

        const gen = {
            revision, runtimeRoot, child, closed: false, closeError: null,
            buffer: '', stderr: '', pending: null, ready: false, stale: false,
        };
        gen.closePromise = new Promise(resolve => {
            child.once('close', (code, signal) => {
                gen.closed = true;
                gen.closeCode = code;
                gen.closeSignal = signal;
                const error = new Error(
                    `runtime renderable worker exited ${code}${signal ? ` (${signal})` : ''}`
                    + (gen.stderr ? `: ${gen.stderr.trim()}` : '')
                );
                gen.closeError = error;
                if (!gen.ready && gen.failReady) gen.failReady(error);
                rejectPending(gen, error);
                resolve();
            });
        });

        child.stderr.setEncoding('utf8');
        child.stderr.on('data', chunk => {
            gen.stderr = appendBoundedDiagnostic(gen.stderr, chunk, maxDiagnosticBytes);
        });
        child.stdout.setEncoding('utf8');

        const readyPromise = new Promise((resolve, reject) => {
            const timer = setTimeout(() => reject(new Error(
                `runtime renderable worker did not become ready within ${startupTimeoutMs} ms`
            )), startupTimeoutMs);
            const fail = error => { clearTimeout(timer); reject(error); };
            gen.failReady = fail;
            gen.resolveReady = () => {
                clearTimeout(timer);
                gen.failReady = null;
                gen.resolveReady = null;
                resolve();
            };
        });

        // Keep a permanent error listener. ChildProcess can emit 'error' after a
        // successful spawn (for example, a later stdio/process failure); removing
        // the startup listener used to make that an unhandled EventEmitter error.
        child.on('error', error => {
            gen.stale = true;
            if (!gen.ready && gen.failReady) gen.failReady(error);
            rejectPending(gen, error);
        });

        child.stdout.on('data', chunk => {
            gen.buffer += chunk;
            if (Buffer.byteLength(gen.buffer, 'utf8') > maxOutputBytes) {
                const error = new Error(
                    `runtime renderable worker produced more than ${(maxOutputBytes / (1024 * 1024)).toFixed(1)} MiB of stdout without completing the current protocol frame`
                );
                gen.stale = true;
                if (!gen.ready && gen.failReady) gen.failReady(error);
                rejectPending(gen, error);
                gen.buffer = '';
                return;
            }

            if (!gen.ready) {
                const match = /(?:^|\n)RENDERABLE WORKER READY\r?\n/.exec(gen.buffer);
                if (match) {
                    gen.buffer = gen.buffer.slice(match.index + match[0].length);
                    gen.ready = true;
                    if (gen.resolveReady) gen.resolveReady();
                }
            }
            if (!gen.pending) return;

            const done = /(?:^|\n)RENDERABLE WORKER REQUEST DONE\t([0-9]+)\r?\n/.exec(gen.buffer);
            if (!done) return;
            const responseId = Number(done[1]);
            const pending = gen.pending;
            const segment = gen.buffer.slice(0, done.index);
            gen.buffer = gen.buffer.slice(done.index + done[0].length);
            gen.pending = null;
            clearTimeout(pending.timer);
            if (responseId !== pending.id) {
                gen.stale = true;
                pending.reject(new Error(
                    `runtime renderable worker response id ${responseId} did not match request ${pending.id}`
                ));
                return;
            }
            const errors = [...segment.matchAll(/(?:^|\n)RENDERABLE WORKER ERROR\t([0-9]+)\t([^\r\n]*)/g)];
            if (errors.length) {
                const own = errors.find(match => Number(match[1]) === pending.id);
                if (!own || errors.some(match => Number(match[1]) !== pending.id)) {
                    gen.stale = true;
                    pending.reject(new Error('runtime renderable worker emitted an error for the wrong request id'));
                    return;
                }
                pending.reject(new Error(own[2] || 'runtime renderable worker failed'));
                return;
            }
            pending.resolve(segment);
        });

        try {
            await readyPromise;
        } catch (error) {
            gen.stale = true;
            try { await stopChild(gen); } catch (_) {}
            if (gen.closed) {
                try { removeStage(runtimeRoot); } catch (_) {}
            }
            throw error;
        }
        return gen;
    }

    async function ensureGeneration() {
        const revision = authorityRevision();
        if (generation && !generation.closed && !generation.stale && generation.revision === revision) {
            return generation;
        }
        if (generation) await disposeGeneration(generation);
        generation = await startGeneration(revision);
        return generation;
    }

    function requestGeneration(gen, request, mapId) {
        if (gen.pending) return Promise.reject(new Error('runtime renderable worker received concurrent requests'));
        const file = requestFilePath(gen.runtimeRoot);
        fs.writeFileSync(file.absolute, JSON.stringify(request));
        const requestId = nextRequestId++;
        return new Promise((resolve, reject) => {
            const pending = {
                id: requestId,
                timer: null,
                resolve: output => { try { fs.unlinkSync(file.absolute); } catch (_) {} resolve(output); },
                reject: error => { try { fs.unlinkSync(file.absolute); } catch (_) {} reject(error); },
            };
            pending.timer = setTimeout(() => {
                if (gen.pending === pending) gen.pending = null;
                gen.stale = true;
                pending.reject(new Error(`runtime renderable worker did not finish within ${timeoutMs} ms`));
            }, timeoutMs);
            gen.pending = pending;
            try {
                gen.child.stdin.write(`${REQUEST_MARKER}\t${requestId}\t${mapId}\t${file.relative}\n`);
            } catch (error) {
                if (gen.pending === pending) gen.pending = null;
                clearTimeout(pending.timer);
                pending.reject(error);
            }
        });
    }

    async function compileSerial(request) {
        if (closed) throw new Error('runtime renderable worker is shut down');
        if (typeof parseOutput !== 'function') throw new Error('runtime renderable worker requires parseOutput');
        const route = routeOf(request);
        const epoch = invalidationEpoch;
        const gen = await ensureGeneration();
        let output;
        try {
            output = await requestGeneration(gen, request, route);
        } catch (error) {
            gen.stale = true;
            throw error;
        }
        // Re-prove the content identity after the runtime finishes. A
        // non-transient change during execution cannot be accepted as current
        // truth even when filesystem watcher delivery is late or unavailable.
        const completedRevision = authorityRevision();
        if (epoch !== invalidationEpoch || gen.stale || completedRevision !== gen.revision) {
            gen.stale = true;
            throw new Error('runtime authority changed during renderable request; retry');
        }
        try {
            return parseOutput(output);
        } catch (error) {
            // A complete DONE frame with malformed/missing renderable content is
            // a protocol/runtime corruption, not a reusable semantic failure.
            gen.stale = true;
            throw error;
        }
    }

    return {
        compile(request) {
            if (closed) return Promise.reject(new Error('runtime renderable worker is shut down'));
            return enqueue(() => compileSerial(request));
        },
        invalidate(reason = 'runtime authority changed') {
            invalidationEpoch += 1;
            if (generation) {
                generation.stale = true;
                generation.staleReason = reason;
            }
        },
        shutdown() {
            if (closed) return tail;
            closed = true;
            invalidationEpoch += 1;
            return enqueue(async () => { if (generation) await disposeGeneration(generation); });
        },
        shutdownSync() {
            if (closed && !generation) return;
            closed = true;
            invalidationEpoch += 1;
            if (generation) disposeGenerationSync(generation);
        },
        state() {
            return {
                closed,
                invalidationEpoch,
                generation: generation ? {
                    revision: generation.revision,
                    stale: generation.stale,
                    closed: generation.closed,
                    pid: generation.child && generation.child.pid || null,
                } : null,
            };
        },
    };
}

module.exports = {
    READY_MARKER,
    REQUEST_MARKER,
    DONE_MARKER,
    ERROR_MARKER,
    DEFAULT_TIMEOUT_MS,
    DEFAULT_STARTUP_TIMEOUT_MS,
    DEFAULT_SHUTDOWN_TIMEOUT_MS,
    DEFAULT_MAX_OUTPUT_BYTES,
    DEFAULT_MAX_DIAGNOSTIC_BYTES,
    GENERATED_RUNTIME_INPUTS,
    WORKER_MAIN,
    resolvePreviewExe,
    runtimeAuthorityRevision,
    createRuntimeRenderableWorker,
};
