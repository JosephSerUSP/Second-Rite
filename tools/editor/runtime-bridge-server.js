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

const DEFAULT_PORT = parseInt(process.env.RUNTIME_BRIDGE_PORT, 10) || 8082;
const DEFAULT_EDITOR_PORT = parseInt(process.env.EDITOR_PORT, 10) || 8080;
const LOVE_EXE = process.env.LOVE_PATH || 'C:\\Program Files\\LOVE\\love.exe';
const MAX_REQUEST_BYTES = 16 * 1024 * 1024;

function resolvePreviewExe(loveExe = LOVE_EXE) {
    const lovec = loveExe.replace(/love\.exe$/i, 'lovec.exe');
    try {
        if (lovec !== loveExe && fs.existsSync(lovec)) return lovec;
    } catch (e) { /* fall through */ }
    return loveExe;
}

function readCampaignPointer(projectRootPath) {
    try {
        const value = JSON.parse(fs.readFileSync(path.join(projectRootPath, 'campaign.json'), 'utf8'));
        return value && typeof value.active === 'string' ? value.active : null;
    } catch (e) {
        return null;
    }
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

function compileRenderable(request, options = {}) {
    const installRoot = options.installRoot || projectRoot.INSTALL_ROOT;
    const openedProjectRoot = options.projectRoot || projectRoot.PROJECT_ROOT;
    const previewExe = options.previewExe || resolvePreviewExe();
    const execFile = options.execFile || nodeExecFile;

    // #237 deliberately leaves external-project Test Play/preview unresolved.
    // Compiling the installation's data while Studio has another project open
    // would be worse than no preview, so fail loudly until that runtime-root
    // bridge exists instead of returning a believable bundle for the wrong game.
    if (path.resolve(openedProjectRoot) !== path.resolve(installRoot)) {
        return Promise.reject(new Error(
            'authoritative renderables for an external project require the pending runtime project-root bridge (#237)'));
    }
    if (!fs.existsSync(previewExe)) {
        return Promise.reject(new Error('LÖVE not found at ' + previewExe + ' (set LOVE_PATH)'));
    }

    const file = requestFilePath(installRoot);
    fs.writeFileSync(file.absolute, JSON.stringify(request));
    const campaign = readCampaignPointer(openedProjectRoot);
    const args = ['.', 'preview-map', String(request.map.id)];
    if (campaign) args.push('campaign=' + campaign);
    const env = Object.assign({}, process.env, {
        SECOND_RITE_RENDERABLE_REQUEST: file.relative,
    });

    return new Promise((resolve, reject) => {
        execFile(previewExe, args, {
            cwd: installRoot,
            env,
            timeout: 60000,
            windowsHide: true,
            maxBuffer: 64 * 1024 * 1024,
        }, (error, stdout, stderr) => {
            try { fs.unlinkSync(file.absolute); } catch (e) {}
            if (error && !String(stdout || '').includes('RENDERABLE BEGIN')) {
                reject(new Error('LÖVE renderable bridge failed: ' + (stderr || error.message)));
                return;
            }
            try {
                resolve(parseRenderableOutput(stdout));
            } catch (parseError) {
                reject(parseError);
            }
        });
    });
}

function createRuntimeBridgeServer(options = {}) {
    const editorPort = options.editorPort || DEFAULT_EDITOR_PORT;
    const warn = options.warn || console.warn.bind(console);
    return http.createServer((req, res) => {
        // This localhost endpoint can launch a LÖVE subprocess. Unlike ordinary
        // read-only asset serving it must not be callable by an arbitrary web
        // page the author happens to visit. Browser requests are restricted to
        // the Studio origin; origin-less local tooling remains possible.
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
        if (req.method !== 'POST' || req.url !== '/api/map-renderable') {
            res.writeHead(404, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: 'not found' }));
            return;
        }

        let body = '';
        let tooLarge = false;
        req.on('data', chunk => {
            if (tooLarge) return;
            body += chunk;
            if (Buffer.byteLength(body, 'utf8') > MAX_REQUEST_BYTES) {
                tooLarge = true;
            }
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
                const value = await compileRenderable(request, options);
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
}

function startRuntimeBridgeServer(options = {}) {
    const server = createRuntimeBridgeServer(options);
    const port = options.port || DEFAULT_PORT;
    server.on('error', error => {
        // The rest of Studio is still useful without this optional authority
        // service; report a port/startup problem instead of taking Electron down.
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
    resolvePreviewExe,
    readCampaignPointer,
    parseRenderableOutput,
    validateRequest,
    isAllowedOrigin,
    compileRenderable,
    createRuntimeBridgeServer,
    startRuntimeBridgeServer,
};
