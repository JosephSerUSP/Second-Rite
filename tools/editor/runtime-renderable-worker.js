'use strict';

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const { spawn: nodeSpawn, spawnSync: nodeSpawnSync } = require('child_process');
const projectRootAuthority = require('./project-root');
const projectPlay = require('./project-play');
const semanticRoots = require('../semantic-roots');
const exportInternal = require('../export/export-game-internal');

const READY_MARKER = 'RENDERABLE WORKER READY';
const DONE_MARKER = 'RENDERABLE WORKER REQUEST DONE';
const ERROR_MARKER = 'RENDERABLE WORKER ERROR\t';
const DEFAULT_TIMEOUT_MS = 60000;
const DEFAULT_STARTUP_TIMEOUT_MS = 15000;
const DEFAULT_SHUTDOWN_TIMEOUT_MS = 2000;
const DEFAULT_MAX_OUTPUT_BYTES = 64 * 1024 * 1024;
const WORKER_MAIN = path.join(__dirname, 'runtime-renderable-worker-main.lua');

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

function appendTreeMetadata(hash, root, target) {
    const relative = normalizeRelative(root, target) || '.';
    let stat;
    try {
        stat = fs.statSync(target);
    } catch (error) {
        if (error && error.code === 'ENOENT') {
            hash.update(`missing\0${relative}\n`);
            return;
        }
        throw error;
    }
    hash.update(`${stat.isDirectory() ? 'd' : 'f'}\0${relative}\0${stat.size}\0${stat.mtimeMs}\n`);
    if (!stat.isDirectory()) return;
    const names = fs.readdirSync(target).sort();
    for (const name of names) appendTreeMetadata(hash, root, path.join(target, name));
}

// Fast deterministic stage-input revision. Content authored through Studio and
// ordinary external edits update file metadata; scanning the exact stage input
// roots makes correctness independent of watcher delivery timing. Transient Map
// snapshots are deliberately absent because they are per-request overlays.
function runtimeAuthorityRevision(options = {}) {
    const installRoot = path.resolve(options.installRoot || projectRootAuthority.INSTALL_ROOT);
    const openedProjectRoot = path.resolve(options.projectRoot || projectRootAuthority.PROJECT_ROOT);
    const roots = semanticRoots.resolveSemanticRoots({
        installRoot,
        runtimeRoot: options.runtimeRoot || installRoot,
        rtpRoot: options.rtpRoot,
        projectRoot: openedProjectRoot,
        env: {},
    });
    const manifestPath = path.resolve(options.manifestPath || path.join(installRoot, 'tools', 'export', 'runtime-manifest.json'));
    const manifest = exportInternal.readManifest(manifestPath);
    const hash = crypto.createHash('sha256');

    appendTreeMetadata(hash, installRoot, manifestPath);
    for (const relative of manifest.rootFiles) appendTreeMetadata(hash, roots.runtimeRoot, path.join(roots.runtimeRoot, relative));
    for (const relative of manifest.runtimeDirectories) appendTreeMetadata(hash, roots.runtimeRoot, path.join(roots.runtimeRoot, relative));
    appendTreeMetadata(hash, roots.runtimeRoot, path.join(roots.runtimeRoot, manifest.releaseConfig));

    // These are the remaining inputs materialized by stageProject(): authored
    // Project data/assets/identity and pinned RTP fallbacks. Metadata scanning is
    // intentionally cheaper than re-hashing large art/audio files on every map
    // request while still invalidating normal editor/filesystem writes.
    appendTreeMetadata(hash, openedProjectRoot, path.join(openedProjectRoot, 'data'));
    appendTreeMetadata(hash, openedProjectRoot, path.join(openedProjectRoot, 'assets'));
    appendTreeMetadata(hash, openedProjectRoot, path.join(openedProjectRoot, 'project.json'));
    appendTreeMetadata(hash, roots.rtpRoot, roots.rtpRoot);
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

function createRuntimeRenderableWorker(options = {}) {
    const installRoot = path.resolve(options.installRoot || projectRootAuthority.INSTALL_ROOT);
    const openedProjectRoot = path.resolve(options.projectRoot || projectRootAuthority.PROJECT_ROOT);
    const previewExe = options.previewExe || resolvePreviewExe(options.loveExe);
    const stageProject = options.stageProject || projectPlay.stageProject;
    const removeStage = options.removeStage || projectPlay.removeStage;
    const spawn = options.spawn || nodeSpawn;
    const spawnSync = options.spawnSync || nodeSpawnSync;
    const parseOutput = options.parseOutput;
    const authorityRevision = options.authorityRevision || (() => runtimeAuthorityRevision({
        installRoot,
        projectRoot: openedProjectRoot,
        runtimeRoot: options.runtimeRoot,
        rtpRoot: options.rtpRoot,
        manifestPath: options.manifestPath,
    }));
    const timeoutMs = options.timeoutMs || DEFAULT_TIMEOUT_MS;
    const startupTimeoutMs = options.startupTimeoutMs || DEFAULT_STARTUP_TIMEOUT_MS;
    const shutdownTimeoutMs = options.shutdownTimeoutMs || DEFAULT_SHUTDOWN_TIMEOUT_MS;
    const maxOutputBytes = options.maxOutputBytes || DEFAULT_MAX_OUTPUT_BYTES;
    const workerMain = options.workerMain || WORKER_MAIN;

    let generation = null;
    let invalidationEpoch = 0;
    let closed = false;
    let tail = Promise.resolve();

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
        try { gen.child.kill(); } catch (_) {}
        if (await waitForClose(gen, shutdownTimeoutMs)) return;
        if (process.platform === 'win32' && gen.child.pid) {
            try {
                spawnSync('taskkill.exe', ['/PID', String(gen.child.pid), '/T', '/F'], {
                    windowsHide: true,
                    stdio: 'ignore',
                    timeout: shutdownTimeoutMs,
                });
            } catch (_) {}
        }
        if (!(await waitForClose(gen, shutdownTimeoutMs))) {
            throw new Error(`runtime renderable worker pid ${gen.child.pid || '(unknown)'} did not terminate; stage retained for safety`);
        }
    }

    async function disposeGeneration(gen = generation) {
        if (!gen) return;
        if (generation === gen) generation = null;
        try {
            await stopChild(gen);
        } finally {
            // Never remove a stage while its LÖVE process may still own files.
            // If stopChild failed, retain the stage instead of racing Windows.
            if (gen.closed) removeStage(gen.runtimeRoot);
        }
    }

    async function startGeneration(revision) {
        if (!fs.existsSync(previewExe)) throw new Error(`LÖVE not found at ${previewExe} (set LOVE_PATH)`);
        if (!fs.existsSync(workerMain)) throw new Error(`runtime renderable worker entrypoint is missing: ${workerMain}`);

        let runtimeRoot = null;
        let child = null;
        try {
            runtimeRoot = stageProject({ installRoot, projectRoot: openedProjectRoot });
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
            revision,
            runtimeRoot,
            child,
            closed: false,
            closeError: null,
            buffer: '',
            stderr: '',
            pending: null,
            ready: false,
            stale: false,
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
                if (gen.pending) {
                    const pending = gen.pending;
                    gen.pending = null;
                    clearTimeout(pending.timer);
                    pending.reject(error);
                }
                resolve();
            });
        });

        child.stderr.setEncoding('utf8');
        child.stderr.on('data', chunk => { gen.stderr += chunk; });
        child.stdout.setEncoding('utf8');

        const readyPromise = new Promise((resolve, reject) => {
            const timer = setTimeout(() => reject(new Error(
                `runtime renderable worker did not become ready within ${startupTimeoutMs} ms`
            )), startupTimeoutMs);
            const fail = error => {
                clearTimeout(timer);
                reject(error);
            };
            child.once('error', fail);
            gen.failReady = fail;
            gen.resolveReady = () => {
                clearTimeout(timer);
                child.removeListener('error', fail);
                gen.failReady = null;
                gen.resolveReady = null;
                resolve();
            };
        });

        child.stdout.on('data', chunk => {
            gen.buffer += chunk;
            if (!gen.ready) {
                const marker = gen.buffer.indexOf(READY_MARKER);
                if (marker >= 0) {
                    const lineEnd = gen.buffer.indexOf('\n', marker);
                    if (lineEnd >= 0) {
                        gen.buffer = gen.buffer.slice(lineEnd + 1);
                        gen.ready = true;
                        if (gen.resolveReady) gen.resolveReady();
                    }
                }
            }
            if (!gen.pending) return;
            if (Buffer.byteLength(gen.buffer, 'utf8') > maxOutputBytes) {
                const pending = gen.pending;
                gen.pending = null;
                clearTimeout(pending.timer);
                gen.stale = true;
                pending.reject(new Error(
                    `runtime renderable worker produced more than ${(maxOutputBytes / (1024 * 1024)).toFixed(1)} MiB for one request`
                ));
                return;
            }
            const done = gen.buffer.indexOf(DONE_MARKER);
            if (done < 0) return;
            const segment = gen.buffer.slice(0, done);
            const lineEnd = gen.buffer.indexOf('\n', done);
            gen.buffer = lineEnd >= 0 ? gen.buffer.slice(lineEnd + 1) : '';
            const pending = gen.pending;
            gen.pending = null;
            clearTimeout(pending.timer);
            if (segment.includes(ERROR_MARKER)) {
                const match = segment.match(/RENDERABLE WORKER ERROR\t([^\r\n]*)/);
                pending.reject(new Error(match ? match[1] : 'runtime renderable worker failed'));
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
        if (generation && (!generation.closed && !generation.stale && generation.revision === revision)) {
            return generation;
        }
        if (generation) await disposeGeneration(generation);
        generation = await startGeneration(revision);
        return generation;
    }

    function requestGeneration(gen, request) {
        if (gen.pending) return Promise.reject(new Error('runtime renderable worker received concurrent requests'));
        const file = requestFilePath(gen.runtimeRoot);
        fs.writeFileSync(file.absolute, JSON.stringify(request));
        return new Promise((resolve, reject) => {
            const timer = setTimeout(() => {
                if (gen.pending) gen.pending = null;
                gen.stale = true;
                reject(new Error(`runtime renderable worker did not finish within ${timeoutMs} ms`));
            }, timeoutMs);
            gen.pending = {
                timer,
                resolve: output => {
                    try { fs.unlinkSync(file.absolute); } catch (_) {}
                    resolve(output);
                },
                reject: error => {
                    try { fs.unlinkSync(file.absolute); } catch (_) {}
                    reject(error);
                },
            };
            try {
                gen.child.stdin.write(`${request.map.id}\t${file.relative}\n`);
            } catch (error) {
                const pending = gen.pending;
                gen.pending = null;
                clearTimeout(timer);
                pending.reject(error);
            }
        });
    }

    async function compileSerial(request) {
        if (closed) throw new Error('runtime renderable worker is shut down');
        if (typeof parseOutput !== 'function') throw new Error('runtime renderable worker requires parseOutput');
        const epoch = invalidationEpoch;
        const gen = await ensureGeneration();
        let output;
        try {
            output = await requestGeneration(gen, request);
        } catch (error) {
            gen.stale = true;
            throw error;
        }
        if (epoch !== invalidationEpoch || gen.stale) {
            gen.stale = true;
            throw new Error('runtime authority changed during renderable request; retry');
        }
        return parseOutput(output);
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
            return enqueue(async () => {
                if (generation) await disposeGeneration(generation);
            });
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
    DONE_MARKER,
    ERROR_MARKER,
    DEFAULT_TIMEOUT_MS,
    DEFAULT_STARTUP_TIMEOUT_MS,
    DEFAULT_SHUTDOWN_TIMEOUT_MS,
    DEFAULT_MAX_OUTPUT_BYTES,
    WORKER_MAIN,
    resolvePreviewExe,
    runtimeAuthorityRevision,
    createRuntimeRenderableWorker,
};
