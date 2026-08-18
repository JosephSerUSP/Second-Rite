'use strict';

// Local LÖVE authority bridge for Developer Studio.
//
// Ordinary editor HTTP/data stays in server.js. This service owns the much
// narrower host capability "run Second Rite against this transient authored map
// and return its compiled static renderables". The browser never compiles map
// geometry and the bridge never saves the submitted map into project data.
const http = require('http');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { execFile: nodeExecFile } = require('child_process');
const projectRoot = require('./project-root');
const projectPlay = require('./project-play');
const { createRuntimeRenderableWorker } = require('./runtime-renderable-worker');

const DEFAULT_PORT = parseInt(process.env.RUNTIME_BRIDGE_PORT, 10) || 8082;
const DEFAULT_EDITOR_PORT = parseInt(process.env.EDITOR_PORT, 10) || 8080;
const LOVE_EXE = process.env.LOVE_PATH || 'C:\\Program Files\\LOVE\\love.exe';
const MAX_REQUEST_BYTES = 16 * 1024 * 1024;
// Response-side transport limits. These are real ceilings on authored content:
// a Map whose compiled bundle exceeds its limit cannot be returned at all, so
// the failure must name the limit instead of blaming the engine (#736).
const RENDERABLE_MAX_BUFFER = 64 * 1024 * 1024;
const INSPECTION_MAX_BUFFER = 16 * 1024 * 1024;
const BRIDGE_TIMEOUT_MS = 60000;

function resolvePreviewExe(loveExe = LOVE_EXE) {
    const lovec = loveExe.replace(/love\.exe$/i, 'lovec.exe');
    try {
        if (lovec !== loveExe && fs.existsSync(lovec)) return lovec;
    } catch (e) { /* fall through */ }
    return loveExe;
}

function parseRenderableOutput(stdout) {
    const match = String(stdout || '').match(/RENDERABLE BEGIN\s*([\s\S]*?)\s*RENDERABLE END/);
    if (!match) throw new Error('LÖVE did not return a renderable bundle');
    let value;
    try {
        value = JSON.parse(match[1]);
    } catch (error) {
        throw new Error('LÖVE returned invalid renderable JSON: ' + error.message);
    }
    if (value && value.error) throw new Error(String(value.error));
    return value;
}

function parseInspectionOutput(stdout) {
    const match = String(stdout || '').match(/MAP INSPECTION BEGIN\s*([\s\S]*?)\s*MAP INSPECTION END/);
    if (!match) throw new Error('LÖVE did not return a Map inspection');
    let value;
    try {
        value = JSON.parse(match[1]);
    } catch (error) {
        throw new Error('LÖVE returned invalid Map inspection JSON: ' + error.message);
    }
    if (value && value.error) throw new Error(String(value.error));
    return value;
}

function validateRequest(value) {
    if (!value || typeof value !== 'object' || Array.isArray(value)) {
        throw new Error('request body must be a JSON object');
    }
    if (!value.map || typeof value.map !== 'object' || Array.isArray(value.map)) {
        throw new Error('request needs a map snapshot');
    }
    if (value.map.id === undefined || value.map.id === null || value.map.id === '') {
        throw new Error('map snapshot needs an id');
    }
    if (value.seed !== undefined && !Number.isFinite(Number(value.seed))) {
        throw new Error('seed must be numeric');
    }
    return {
        map: value.map,
        seed: value.seed === undefined ? 1735689600 : Number(value.seed),
    };
}

function isAllowedOrigin(origin, editorPort = DEFAULT_EDITOR_PORT) {
    if (!origin) return true; // local non-browser tooling/curl
    return origin === `http://127.0.0.1:${editorPort}`
        || origin === `http://localhost:${editorPort}`;
}

function requestFilePath(installRoot) {
    const relativeDir = path.join('tmp', 'editor-renderable');
    const absoluteDir = path.join(installRoot, relativeDir);
    fs.mkdirSync(absoluteDir, { recursive: true });
    const name = `${process.pid}-${Date.now()}-${crypto.randomBytes(6).toString('hex')}.json`;
    return {
        absolute: path.join(absoluteDir, name),
        relative: path.join(relativeDir, name).split(path.sep).join('/'),
    };
}

function formatBytes(value) {
    const bytes = Number(value) || 0;
    if (bytes < 1024) return `${bytes} bytes`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KiB (${bytes} bytes)`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MiB (${bytes} bytes)`;
}

function isMaxBufferError(error) {
    if (!error) return false;
    return error.code === 'ERR_CHILD_PROCESS_STDIO_MAXBUFFER'
        || /maxBuffer/i.test(String(error.message || ''));
}

function isTimeoutError(error) {
    return !!error && error.killed === true && !isMaxBufferError(error);
}

function describeBridgeFailure(error, command, stdout, stderr, limits) {
    const received = Buffer.byteLength(String(stdout || ''), 'utf8');
    if (isMaxBufferError(error)) {
        return new Error(
            `LÖVE ${command} produced more output than the ${formatBytes(limits.maxBuffer)} stdout `
            + `transport limit (read ${formatBytes(received)} before truncation). The runtime compiled `
            + 'this Map; the bridge cannot carry a payload this large.'
        );
    }
    if (isTimeoutError(error)) {
        return new Error(
            `LÖVE ${command} did not finish within ${limits.timeout} ms and was terminated `
            + `(read ${formatBytes(received)} of output).`
        );
    }
    return new Error('LÖVE ' + command + ' bridge failed: ' + (stderr || error.message));
}

// Cold reference path retained for inspection and tests. Ordinary renderable
// HTTP traffic now uses the persistent generation below; keeping this function
// explicit preserves a deterministic one-shot fallback/reference contract.
function compileBridge(request, options, spec) {
    const { command, requestEnvironmentKey, envelope, parseOutput, maxBuffer } = spec;
    const installRoot = options.installRoot || projectRoot.INSTALL_ROOT;
    const openedProjectRoot = options.projectRoot || projectRoot.PROJECT_ROOT;
    const previewExe = options.previewExe || resolvePreviewExe();
    const execFile = options.execFile || nodeExecFile;

    if (!fs.existsSync(previewExe)) {
        return Promise.reject(new Error('LÖVE not found at ' + previewExe + ' (set LOVE_PATH)'));
    }

    const stageProject = options.stageProject || projectPlay.stageProject;
    const removeStage = options.removeStage || projectPlay.removeStage;
    const snapshotSameRoot = options.snapshotSameRoot || projectPlay.snapshotSameRoot;
    const removeSnapshot = options.removeSnapshot || (snapshot => projectPlay.cleanupLaunch(null, snapshot));
    let stageDir = null;
    let dataSnapshot = null;
    let runtimeRoot;
    const cleanup = () => {
        if (stageDir) removeStage(stageDir);
        if (dataSnapshot) removeSnapshot(dataSnapshot);
    };
    try {
        if (projectPlay.sameRoot(installRoot, openedProjectRoot)) {
            dataSnapshot = snapshotSameRoot({ installRoot, projectRoot: openedProjectRoot });
            runtimeRoot = openedProjectRoot;
        } else {
            stageDir = stageProject({ installRoot, projectRoot: openedProjectRoot });
            runtimeRoot = stageDir;
        }
    } catch (error) {
        cleanup();
        return Promise.reject(error);
    }

    const file = requestFilePath(runtimeRoot);
    fs.writeFileSync(file.absolute, JSON.stringify(request));
    const args = ['.', command, String(request.map.id)];
    const env = projectPlay.launchEnvironment(null, dataSnapshot);
    env[requestEnvironmentKey] = file.relative;

    return new Promise((resolve, reject) => {
        try {
            execFile(previewExe, args, {
                cwd: runtimeRoot,
                env,
                timeout: BRIDGE_TIMEOUT_MS,
                windowsHide: true,
                maxBuffer,
            }, (error, stdout, stderr) => {
                try { fs.unlinkSync(file.absolute); } catch (e) {}
                cleanup();
                const output = String(stdout || '');
                const complete = output.includes(envelope.begin) && output.includes(envelope.end);
                if (!complete && error) {
                    reject(describeBridgeFailure(error, command, output, stderr,
                        { maxBuffer, timeout: BRIDGE_TIMEOUT_MS }));
                    return;
                }
                if (!complete && output.includes(envelope.begin)) {
                    reject(new Error(
                        `LÖVE ${command} output ended without "${envelope.end}": the bundle was `
                        + `truncated in transport (read ${formatBytes(Buffer.byteLength(output, 'utf8'))}).`
                    ));
                    return;
                }
                try {
                    resolve(parseOutput(stdout));
                } catch (parseError) {
                    reject(parseError);
                }
            });
        } catch (error) {
            try { fs.unlinkSync(file.absolute); } catch (cleanupError) {}
            cleanup();
            reject(error);
        }
    });
}

function compileRenderable(request, options = {}) {
    return compileBridge(request, options, {
        command: 'preview-map',
        requestEnvironmentKey: 'SECOND_RITE_RENDERABLE_REQUEST',
        envelope: { begin: 'RENDERABLE BEGIN', end: 'RENDERABLE END' },
        parseOutput: parseRenderableOutput,
        maxBuffer: RENDERABLE_MAX_BUFFER,
    });
}

function compileInspection(request, options = {}) {
    return compileBridge(request, options, {
        command: 'preview-map-inspection',
        requestEnvironmentKey: 'SECOND_RITE_MAP_INSPECTION_REQUEST',
        envelope: { begin: 'MAP INSPECTION BEGIN', end: 'MAP INSPECTION END' },
        parseOutput: parseInspectionOutput,
        maxBuffer: INSPECTION_MAX_BUFFER,
    });
}

function createRuntimeBridgeServer(options = {}) {
    const editorPort = options.editorPort || DEFAULT_EDITOR_PORT;
    const warn = options.warn || console.warn.bind(console);
    const renderableWorker = options.renderableWorker || createRuntimeRenderableWorker({
        installRoot: options.installRoot || projectRoot.INSTALL_ROOT,
        projectRoot: options.projectRoot || projectRoot.PROJECT_ROOT,
        previewExe: options.previewExe || resolvePreviewExe(),
        parseOutput: parseRenderableOutput,
        timeoutMs: BRIDGE_TIMEOUT_MS,
        maxOutputBytes: RENDERABLE_MAX_BUFFER,
        authorityRevision: options.authorityRevision,
        stageProject: options.workerStageProject,
        removeStage: options.workerRemoveStage,
        spawn: options.workerSpawn,
        spawnSync: options.workerSpawnSync,
        workerMain: options.workerMain,
    });
    const compileRenderableRequest = options.renderableCompiler
        || (request => renderableWorker.compile(request));
    const compileInspectionRequest = options.inspectionCompiler
        || (request => compileInspection(request, options));

    const server = http.createServer((req, res) => {
        const origin = req.headers.origin;
        if (!isAllowedOrigin(origin, editorPort)) {
            warn(
                `Second Rite runtime renderable bridge rejected browser origin ${origin}; `
                + `expected http://127.0.0.1:${editorPort} or http://localhost:${editorPort}. `
                + 'Set EDITOR_PORT to the Studio HTTP port if it is not 8080.'
            );
            res.writeHead(403, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: 'runtime bridge accepts only the local Studio origin' }));
            return;
        }
        if (origin) res.setHeader('Access-Control-Allow-Origin', origin);
        res.setHeader('Vary', 'Origin');
        res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
        res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
        if (req.method === 'OPTIONS') {
            res.writeHead(204);
            res.end();
            return;
        }
        if (req.method !== 'POST'
                || (req.url !== '/api/map-renderable' && req.url !== '/api/map-inspection')) {
            res.writeHead(404, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: 'not found' }));
            return;
        }

        let body = '';
        let tooLarge = false;
        req.on('data', chunk => {
            if (tooLarge) return;
            body += chunk;
            if (Buffer.byteLength(body, 'utf8') > MAX_REQUEST_BYTES) tooLarge = true;
        });
        req.on('end', async () => {
            const respond = (status, value) => {
                res.writeHead(status, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify(value));
            };
            if (tooLarge) return respond(413, { error: 'renderable request exceeds 16 MiB' });
            let request;
            try {
                request = validateRequest(JSON.parse(body || '{}'));
            } catch (error) {
                return respond(400, { error: error.message });
            }
            try {
                const value = req.url === '/api/map-inspection'
                    ? await compileInspectionRequest(request)
                    : await compileRenderableRequest(request);
                respond(200, value);
            } catch (error) {
                respond(500, { error: error.message });
            }
        });
        req.on('error', error => {
            if (!res.headersSent) {
                res.writeHead(400, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ error: error.message }));
            }
        });
    });

    server.invalidateRenderables = reason => renderableWorker.invalidate(reason);
    server.shutdownRuntimeWorker = () => renderableWorker.shutdown();
    server.runtimeRenderableWorkerState = () => renderableWorker.state();
    return server;
}

function startRuntimeBridgeServer(options = {}) {
    const server = createRuntimeBridgeServer(options);
    const port = options.port || DEFAULT_PORT;
    server.on('error', error => {
        console.error('Second Rite runtime renderable bridge failed:', error.message);
    });
    server.listen(port, '127.0.0.1', () => {
        console.log(`Second Rite runtime renderable bridge listening on http://127.0.0.1:${port}`);
    });
    return server;
}

if (require.main === module) startRuntimeBridgeServer();

module.exports = {
    DEFAULT_PORT,
    DEFAULT_EDITOR_PORT,
    MAX_REQUEST_BYTES,
    RENDERABLE_MAX_BUFFER,
    INSPECTION_MAX_BUFFER,
    BRIDGE_TIMEOUT_MS,
    resolvePreviewExe,
    parseRenderableOutput,
    parseInspectionOutput,
    validateRequest,
    isAllowedOrigin,
    compileRenderable,
    compileInspection,
    createRuntimeBridgeServer,
    startRuntimeBridgeServer,
};
