 const http = require('http');
const fs = require('fs');
const path = require('path');
const authoredStorage = require('./authored-storage');
const { exec } = require('child_process');
const runtimeBridge = require('./runtime-bridge-server');

const exporter = require('../export/export-game');
const projectPlay = require('./project-play');

// Legacy AI generator bridge state. #369 migrates the generator itself from
// campaign-shaped output to explicit fixture Projects. It is deliberately not
// allowed to select or redirect the Project Studio has open.
let genProc = null;
let genLog = '';
let genStatus = 'idle';

// Export bridge state, same shape as the generator's: one run at a time,
// buffered log polled by the Export Game dialog.
let exportProc = null;
let exportLog = '';
let exportStatus = 'idle';
let exportResult = null;   // { target, outputDir } of the last run
let genApiKeys = {};       // { providerId: apiKey } — session memory only
let genModelCache = null;

// PORT env override lets a second instance (e.g. preview/CI tooling) run
// alongside a developer's own server on the default 8080.
const PORT = parseInt(process.env.PORT, 10) || 8080;
const GAME_PORT = 8081;
// #237/#299: Studio works from two roots -- the installation it ships as and
// the Project it has open. A Project is one authored/runnable game and data/
// is its one authored data authority.
const projectRoot = require('./project-root');
const INSTALL_ROOT = projectRoot.INSTALL_ROOT;
const PROJECT_ROOT = projectRoot.PROJECT_ROOT;
const inProject = projectRoot.inProject;
const DATA_ROOT = inProject('data');
const dataDir = () => DATA_ROOT;
// Shared authored-storage metadata owns the database resources exposed to the
// editor. Semantic kind and physical representation are deliberately separate,
// so a future scenes migration only changes the manifest representation.
const DATA_FILES = authoredStorage.bulkEditableResources();
// Override with the LOVE_PATH environment variable if LÖVE lives elsewhere
const LOVE_EXE = process.env.LOVE_PATH || 'C:\\Program Files\\LOVE\\love.exe';

// Stale-save guard: representation-aware compound tokens. Fragment-backed
// resources hash every authoritative file instead of pretending one legacy
// data/<name>.json owns the resource.
const resourceVersion = (name) => {
    try {
        return authoredStorage.versionToken(DATA_ROOT, name);
    } catch (e) {
        return null;
    }
};

const allFileVersions = () => {
    const versions = {};
    DATA_FILES.forEach(name => {
        versions[name] = resourceVersion(name);
    });
    return versions;
};

// E5: console-capable LOVE binary for the headless scene preview. On
// Windows only lovec.exe attaches a console, so stdout capture needs it;
// fall back to LOVE_EXE when no lovec sibling exists.
const previewExe = (() => {
    const lovec = LOVE_EXE.replace(/love\.exe$/i, 'lovec.exe');
    try {
        if (lovec !== LOVE_EXE && fs.existsSync(lovec)) return lovec;
    } catch (e) { /* fall through */ }
    return LOVE_EXE;
})();

// #247/#299: every saved-data preview and Test Play uses the exporter staging
// boundary. The stage materializes runtime code from INSTALL_ROOT and assets +
// authored data from PROJECT_ROOT, then is removed only when the child exits.
// Same-root development remains the direct/no-copy path in project-play.js.
function execOpenedProject(executable, args, options, callback) {
    const opts = options || {};
    return projectPlay.execStaged({
        executable,
        installRoot: INSTALL_ROOT,
        projectRoot: PROJECT_ROOT,
        args: args || [],
        timeout: opts.timeout,
        maxBuffer: opts.maxBuffer,
        windowsHide: opts.windowsHide !== false,
    }, callback).child;
}

const server = http.createServer((req, res) => {
    // Enable CORS
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

    if (req.method === 'OPTIONS') {
        res.writeHead(200);
        res.end();
        return;
    }

    req.on('error', (err) => {
        console.error('Request stream error:', err);
    });

    try {
        let requestPath = req.url === '/' ? '/index.html' : req.url;
    requestPath = requestPath.split('?')[0];
    const decodedUrl = decodeURIComponent(requestPath);
    const relativePath = decodedUrl.replace(/^[\/\\]/, '');
    // Project art resolves through the opened project; everything else is the
    // editor's own UI, served from beside this file. Either way the resolver
    // REFUSES a path that leaves its root rather than rewriting it into one
    // that stays -- a silently rewritten path serves the wrong file just as
    // quietly as a traversal would have.
    const isAsset = relativePath.startsWith('assets');
    let filePath;
    try {
        filePath = projectRoot.resolveWithin(isAsset ? PROJECT_ROOT : __dirname, relativePath);
    } catch (e) {
        res.writeHead(403, { 'Content-Type': 'text/plain' });
        res.end('Forbidden');
        return;
    }

    if (req.method === 'GET' && fs.existsSync(filePath) && fs.statSync(filePath).isFile()) {
        console.log(`GET ${req.url} -> ${filePath} [FOUND]`);
        const ext = path.extname(filePath).toLowerCase();
        let contentType = 'text/html';
        if (ext === '.js') contentType = 'text/javascript';
        else if (ext === '.css') contentType = 'text/css';
        else if (ext === '.png') contentType = 'image/png';
        else if (ext === '.jpg' || ext === '.jpeg') contentType = 'image/jpeg';
        else if (ext === '.json') contentType = 'application/json';
        else if (ext === '.ttf') contentType = 'font/ttf';
        else if (ext === '.otf') contentType = 'font/otf';
        else if (ext === '.obj' || ext === '.mtl') contentType = 'text/plain';

        fs.readFile(filePath, (err, content) => {
            if (err) {
                res.writeHead(500, { 'Content-Type': 'text/plain' });
                res.end('Error loading asset');
            } else {
                res.writeHead(200, { 'Content-Type': contentType });
                res.end(content);
            }
        });
        return;
    }
    
    if (req.method === 'GET' && req.url === '/data') {
        const data = {};
        DATA_FILES.forEach(name => {
            try {
                data[name] = authoredStorage.loadResource(DATA_ROOT, name).value;
            } catch (e) {
                data[name] = null;
            }
        });
        // The editor posts the whole payload back on /save, so the tokens
        // round-trip without any bookkeeping on the client.
        data._fileVersions = allFileVersions();

        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(data));
    } else if (req.method === 'GET' && req.url === '/api/effects') {
        // Effekseer effects, for the animation editor's effect dropdown.
        // Separate from /api/assets because that one is image-only and does not
        // recurse, while effects live in per-library subfolders under
        // assets/effects (e.g. assets/effects/SecondRite/basic_attack.efkefc).
        const root = path.join(PROJECT_ROOT, 'assets', 'effects');
        const out = [];
        const walk = (dir) => {
            let entries = [];
            try { entries = fs.readdirSync(dir, { withFileTypes: true }); } catch (e) { return; }
            entries.forEach(ent => {
                const full = path.join(dir, ent.name);
                if (ent.isDirectory()) { walk(full); return; }
                if (!/\.efkefc?$/i.test(ent.name)) return;
                out.push(path.relative(PROJECT_ROOT, full).split(path.sep).join('/'));
            });
        };
        walk(root);
        out.sort();
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ files: out }));

    } else if (req.method === 'GET' && req.url.startsWith('/api/models')) {
        // Shared 3D model picker inventory. Unlike /api/assets (which is an
        // image picker and deliberately non-recursive), model libraries are
        // grouped into nested folders such as models/items and models/dungeon.
        // Scan the opened PROJECT, not the editor installation, so external
        // projects get exactly their own model library.
        const parsedUrl = new URL(req.url, 'http://127.0.0.1:8080');
        const requestedRoot = parsedUrl.searchParams.get('root') || 'models';
        const safeRoot = path.normalize(requestedRoot).split(path.sep).join('/');
        if (!/^models(?:\/|$)/.test(safeRoot) || safeRoot.split('/').includes('..')) {
            res.writeHead(403, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: 'model root must stay under assets/models' }));
            return;
        }

        let modelsRoot;
        try {
            modelsRoot = inProject('assets', safeRoot);
        } catch (e) {
            res.writeHead(403, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: 'model root outside the project' }));
            return;
        }

        const files = [];
        const walk = (dir) => {
            let entries = [];
            try { entries = fs.readdirSync(dir, { withFileTypes: true }); } catch (e) { return; }
            entries.forEach(ent => {
                const full = path.join(dir, ent.name);
                if (ent.isDirectory()) { walk(full); return; }
                if (!ent.isFile() || !/\.obj$/i.test(ent.name)) return;
                let size = 0;
                try { size = fs.statSync(full).size; } catch (e) {}
                files.push({
                    path: path.relative(PROJECT_ROOT, full).split(path.sep).join('/'),
                    size
                });
            });
        };
        if (fs.existsSync(modelsRoot) && fs.statSync(modelsRoot).isDirectory()) walk(modelsRoot);
        files.sort((a, b) => a.path.localeCompare(b.path));
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ root: `assets/${safeRoot}`, files }));

    } else if (req.method === 'GET' && req.url.startsWith('/api/assets')) {
        const parsedUrl = new URL(req.url, 'http://127.0.0.1:8080');
        const subDir = parsedUrl.searchParams.get('dir') || 'sprites';
        const safeSubDir = path.normalize(subDir);
        let assetsDir;
        try {
            assetsDir = inProject('assets', safeSubDir);
        } catch (e) {
            res.writeHead(403, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: 'asset directory outside the project' }));
            return;
        }

        if (fs.existsSync(assetsDir) && fs.statSync(assetsDir).isDirectory()) {
            fs.readdir(assetsDir, (err, files) => {
                if (err) {
                    res.writeHead(500, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ error: err.message }));
                } else {
                    const result = {
                        directories: [],
                        files: []
                    };
                    
                    try {
                        const parentFiles = fs.readdirSync(path.join(PROJECT_ROOT, 'assets'));
                        result.directories = parentFiles.filter(f => {
                            return fs.statSync(path.join(PROJECT_ROOT, 'assets', f)).isDirectory();
                        });
                    } catch(e) {}

                    files.forEach(f => {
                        try {
                            const stat = fs.statSync(path.join(assetsDir, f));
                            if (stat.isFile() && /\.(png|jpe?g|gif|webp)$/i.test(f)) {
                                result.files.push(`assets/${safeSubDir}/${f}`);
                            }
                        } catch(e) {}
                    });
                    
                    res.writeHead(200, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify(result));
                }
            });
        } else {
            res.writeHead(400, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: 'Invalid directory' }));
        }
    } else if (req.method === 'GET' && req.url === '/api/tilesets') {
        try {
            const root = DATA_ROOT;
            const loaded = authoredStorage.loadRegistry(root, 'tilesets');
            const version = authoredStorage.versionToken(root, 'tilesets');
            const tilesetsDir = path.join(PROJECT_ROOT, 'assets', 'tilesets');
            let pngFiles = [];
            try {
                pngFiles = fs.readdirSync(tilesetsDir).filter(f => /\.png$/i.test(f));
            } catch (e) {}

            // _storageVersion is editor transport metadata, not authored data.
            // Tileset Studio deep-copies this record and naturally posts the
            // token back on save; successful saves reload the list and receive
            // a fresh compound token.
            const tilesets = Object.keys(loaded.records).sort().map(id =>
                Object.assign({}, loaded.records[id], { _storageVersion: version })
            );

            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ tilesets, textures: pngFiles, storage: loaded.storage }));
        } catch (e) {
            res.writeHead(500, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: e.message }));
        }
    } else if (req.method === 'POST' && req.url === '/api/tilesets/save') {
        let body = '';
        req.on('data', c => { body += c; });
        req.on('end', () => {
            try {
                const p = JSON.parse(body);
                const expectedVersion = typeof p._storageVersion === 'string' ? p._storageVersion : null;
                delete p._storageVersion;
                const id = p.id;
                if (!id || !/^[a-zA-Z0-9_-]+$/.test(id)) {
                    throw new Error('Invalid tileset ID.');
                }

                const result = authoredStorage.writeRegistryRecord(
                    DATA_ROOT, 'tilesets', p, expectedVersion
                );
                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({
                    success: true,
                    id,
                    version: result.version,
                    storage: result.storage
                }));
            } catch (e) {
                if (e && e.code === 'STALE_AUTHORED_DATA') {
                    res.writeHead(409, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({
                        success: false,
                        stale: true,
                        version: e.currentVersion,
                        message: 'Save blocked: tilesets changed on disk after this record was loaded. Reload Tileset Studio before saving.'
                    }));
                    return;
                }
                res.writeHead(400, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ success: false, message: e.message }));
            }
        });
    } else if (req.method === 'POST' && req.url === '/api/tilesets/create') {
        let body = '';
        req.on('data', c => { body += c; });
        req.on('end', () => {
            try {
                const p = JSON.parse(body);
                const name = p.name ? p.name.trim() : '';
                if (!name || !/^[a-zA-Z0-9_-]+$/.test(name)) {
                    throw new Error('Invalid tileset name.');
                }

                const loaded = authoredStorage.loadRegistry(DATA_ROOT, 'tilesets');
                if (loaded.records[name]) {
                    throw new Error(`Tileset '${name}' already exists.`);
                }

                const tilesetsDir = path.join(PROJECT_ROOT, 'assets', 'tilesets');
                const targetPng = path.join(tilesetsDir, `${name}.png`);
                let tmplPng = path.join(tilesetsDir, 'template_tileset.png');
                if (!fs.existsSync(tmplPng)) tmplPng = path.join(tilesetsDir, 'dungeon_001.png');

                if (!fs.existsSync(targetPng) && fs.existsSync(tmplPng)) {
                    fs.copyFileSync(tmplPng, targetPng);
                }

                const record = {
                    id: name,
                    name: p.displayName || name,
                    texture: `assets/tilesets/${name}.png`,
                    tileWidth: 64,
                    tileHeight: 64,
                    base: { walls: [], floors: [], ceilings: [] },
                    doors: [],
                    features: []
                };
                const result = authoredStorage.writeRegistryRecord(DATA_ROOT, 'tilesets', record, null);

                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({
                    success: true,
                    name,
                    id: name,
                    version: result.version,
                    storage: result.storage
                }));
            } catch (e) {
                if (e && e.code === 'STALE_AUTHORED_DATA') {
                    res.writeHead(409, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({
                        success: false,
                        stale: true,
                        version: e.currentVersion,
                        message: 'Create blocked: tilesets changed on disk while the new record was being created. Reload Tileset Studio and try again.'
                    }));
                    return;
                }
                res.writeHead(400, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ success: false, message: e.message }));
            }
        });
    } else if (req.method === 'GET' && req.url === '/api/fonts') {
        // Font picker choices, read straight off disk so dropping a new
        // .ttf/.otf into assets/fonts/ is the only step needed — no editor
        // code change. "Lucida" is prepended as the pseudo-entry with no
        // file, mirroring presentation/ui.lua's built-in-font fallback.
        const fontsDir = path.join(PROJECT_ROOT, 'assets', 'fonts');
        let names = [];
        try {
            names = fs.readdirSync(fontsDir)
                .filter(f => /\.(ttf|otf)$/i.test(f))
                .map(f => f.replace(/\.(ttf|otf)$/i, ''))
                .sort((a, b) => a.localeCompare(b));
        } catch (e) { /* no fonts dir yet — just Lucida */ }
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ fonts: ['Lucida', ...names] }));
    } else if (req.method === 'GET' && req.url === '/api/templates/scenes') {
        // E4: scene template registry — read-only JSON files, one per
        // template, each a scenes.json entry shape (minus id) plus a
        // _template { label, description } metadata block. Adding a preset
        // means dropping a file here; nothing else changes.
        const tplDir = path.join(__dirname, 'templates', 'scenes');
        const templates = [];
        if (fs.existsSync(tplDir) && fs.statSync(tplDir).isDirectory()) {
            fs.readdirSync(tplDir).forEach(f => {
                if (!f.endsWith('.json')) return;
                try {
                    templates.push(JSON.parse(fs.readFileSync(path.join(tplDir, f), 'utf8')));
                } catch (e) {
                    console.warn(`Skipping unparsable scene template ${f}: ${e.message}`);
                }
            });
        }
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(templates));
    } else if (req.method === 'GET' && req.url.startsWith('/preview-scene')) {
        // E5: invoke the engine's headless preview against the SAVED data
        // files and return the materialized window state. The preview
        // reflects the last save, not unsaved editor state — the UI states
        // that caveat. Failures are structured JSON (the canvas renders
        // them), never a 500 that kills the tab.
        const parsedUrl = new URL(req.url, 'http://127.0.0.1:8080');
        const sceneId = parsedUrl.searchParams.get('id');
        console.log(`[preview-scene] handler invoked — req.url="${req.url}" sceneId="${sceneId}"`);
        const fail = (msg) => {
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: msg }));
        };
        if (!sceneId || !/^[\w-]+$/.test(sceneId)) return fail('missing or invalid scene id');
        console.log(`[preview-scene] previewExe="${previewExe}" exists=${fs.existsSync(previewExe)}`);
        if (!fs.existsSync(previewExe)) return fail('preview unavailable — LOVE not found at ' + previewExe + ' (set LOVE_PATH)');
        execOpenedProject(previewExe, ['preview-scene', sceneId], {
            timeout: 15000,
            windowsHide: true,
            maxBuffer: 4 * 1024 * 1024
        }, (err, stdout) => {
            const text = String(stdout || '');
            const begin = text.indexOf('PREVIEW BEGIN');
            const end = text.indexOf('PREVIEW END');
            if (begin === -1 || end === -1 || end < begin) {
                return fail('preview produced no output' + (err ? ' (' + err.message + ')' : ''));
            }
            const jsonText = text.slice(begin + 'PREVIEW BEGIN'.length, end).trim();
            try {
                JSON.parse(jsonText); // validate before relaying
            } catch (e) {
                return fail('preview output was not valid JSON: ' + e.message);
            }
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(jsonText);
        });
    } else if (req.method === 'POST' && req.url === '/api/map-inspection') {
        // Read-only semantic generated-Map preview. The browser submits an
        // unsaved snapshot; the bridge launches LÖVE and returns the engine's
        // resolved facts without writing authored data or a save instance.
        let body = '';
        req.on('data', chunk => { body += chunk; });
        req.on('end', async () => {
            const respond = (status, value) => {
                res.writeHead(status, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify(value));
            };
            try {
                const request = runtimeBridge.validateRequest(JSON.parse(body || '{}'));
                const value = await runtimeBridge.compileInspection(request, {
                    installRoot: INSTALL_ROOT,
                    projectRoot: PROJECT_ROOT,
                    previewExe,
                });
                respond(200, value);
            } catch (error) {
                respond(500, { error: error.message });
            }
        });
    } else if (req.method === 'POST' && req.url === '/preview-window') {
        // E12: invoke the engine's headless SINGLE-WINDOW preview against
        // the SAVED windowLayout registry (same staleness caveat as
        // /preview-scene: reflects the last save). POST because the mock
        // spec (list source, sample text, sibling windows for sel()) can
        // be nontrivially sized — a GET query string would be fragile.
        // Body: { id: "windowId", mock: { ...mockSpec, see main.lua
        // runPreviewWindow } }. Failures are structured JSON, never a 500.
        let body = '';
        req.on('data', chunk => { body += chunk; });
        req.on('end', () => {
            const fail = (msg) => {
                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ error: msg }));
            };
            let parsed;
            try {
                parsed = JSON.parse(body || '{}');
            } catch (e) {
                return fail('request body was not valid JSON: ' + e.message);
            }
            const windowId = parsed.id;
            if (!windowId || !/^[\w-]+$/.test(windowId)) return fail('missing or invalid window id');
            if (!fs.existsSync(previewExe)) return fail('preview unavailable — LOVE not found at ' + previewExe + ' (set LOVE_PATH)');

            let mockJson;
            try {
                mockJson = JSON.stringify(parsed.mock || {});
            } catch (e) {
                return fail('mock spec could not be serialized: ' + e.message);
            }

            execOpenedProject(previewExe, ['preview-window', windowId, mockJson], {
                timeout: 15000,
                windowsHide: true,
                maxBuffer: 4 * 1024 * 1024
            }, (err, stdout) => {
                const text = String(stdout || '');
                const begin = text.indexOf('PREVIEW BEGIN');
                const end = text.indexOf('PREVIEW END');
                if (begin === -1 || end === -1 || end < begin) {
                    return fail('preview produced no output' + (err ? ' (' + err.message + ')' : ''));
                }
                const jsonText = text.slice(begin + 'PREVIEW BEGIN'.length, end).trim();
                try {
                    JSON.parse(jsonText); // validate before relaying
                } catch (e) {
                    return fail('preview output was not valid JSON: ' + e.message);
                }
                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(jsonText);
            });
        });
    } else if (req.method === 'POST' && req.url === '/preview-anim') {
        // A3: invoke the engine's headless preview for animations.
        // Body: { id: "animId", sprite: "spritePath", data: { ... } }.
        let body = '';
        req.on('data', chunk => { body += chunk; });
        req.on('end', () => {
            const fail = (msg) => {
                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ error: msg }));
            };
            let parsed;
            try {
                parsed = JSON.parse(body || '{}');
            } catch (e) {
                return fail('request body was not valid JSON: ' + e.message);
            }
            const animId = parsed.id;
            // No sprite is a legitimate animation-preview state. #203 made the
            // engine support that explicitly, but this HTTP seam immediately
            // replaced an empty request with the same hardcoded missing pixie
            // path that #203 removed. Preserve absence across the boundary so
            // the server and direct CLI exercise the same contract (#204).
            const spritePath = parsed.sprite === undefined || parsed.sprite === null
                ? ''
                : parsed.sprite;
            if (typeof spritePath !== 'string') return fail('sprite must be a string');
            if (!animId) return fail('missing animation id');
            if (!fs.existsSync(previewExe)) return fail('preview unavailable — LOVE not found at ' + previewExe + ' (set LOVE_PATH)');

            let mockJson;
            try {
                mockJson = JSON.stringify(parsed.data || {});
            } catch (e) {
                return fail('animation data could not be serialized: ' + e.message);
            }

            execOpenedProject(previewExe, ['preview-anim', animId, mockJson, spritePath], {
                timeout: 15000,
                windowsHide: true,
                maxBuffer: 4 * 1024 * 1024
            }, (err, stdout) => {
                const text = String(stdout || '');
                const begin = text.indexOf('PREVIEW BEGIN');
                const end = text.indexOf('PREVIEW END');
                if (begin === -1 || end === -1 || end < begin) {
                    return fail('preview produced no output' + (err ? ' (' + err.message + ')' : ''));
                }
                const jsonText = text.slice(begin + 'PREVIEW BEGIN'.length, end).trim();
                try {
                    JSON.parse(jsonText); // validate before relaying
                } catch (e) {
                    return fail('preview output was not valid JSON: ' + e.message);
                }
                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(jsonText);
            });
        });
    } else if (req.method === 'GET' && req.url.startsWith('/preview-font')) {
        // Font picker preview: invokes the engine's real ui.drawPanel +
        // ui.drawString path with a candidate font/size, never touching
        // data/system.json — so the editor shows exactly what the engine
        // will render instead of a browser-side approximation.
        const parsedUrl = new URL(req.url, 'http://127.0.0.1:8080');
        const fontName = parsedUrl.searchParams.get('name') || '';
        const fontSize = parsedUrl.searchParams.get('size') || '8';
        const fail = (msg) => {
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: msg }));
        };
        if (!/^[\w-]*$/.test(fontName)) return fail('invalid font name');
        if (!/^\d+$/.test(fontSize)) return fail('invalid font size');
        if (!fs.existsSync(previewExe)) return fail('preview unavailable — LOVE not found at ' + previewExe + ' (set LOVE_PATH)');
        execOpenedProject(previewExe, ['preview-font', fontName, fontSize], {
            timeout: 15000,
            windowsHide: true,
            maxBuffer: 4 * 1024 * 1024
        }, (err, stdout) => {
            const text = String(stdout || '');
            const begin = text.indexOf('PREVIEW BEGIN');
            const end = text.indexOf('PREVIEW END');
            if (begin === -1 || end === -1 || end < begin) {
                return fail('preview produced no output' + (err ? ' (' + err.message + ')' : ''));
            }
            const jsonText = text.slice(begin + 'PREVIEW BEGIN'.length, end).trim();
            try {
                JSON.parse(jsonText);
            } catch (e) {
                return fail('preview output was not valid JSON: ' + e.message);
            }
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(jsonText);
        });
    } else if (req.method === 'POST' && req.url === '/preview-fog') {
        let body = '';
        req.on('data', chunk => { body += chunk; });
        req.on('end', () => {
            const fail = (msg) => {
                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ error: msg }));
            };
            let parsed;
            try {
                parsed = JSON.parse(body || '{}');
            } catch (e) {
                return fail('request body was not valid JSON: ' + e.message);
            }
            if (!fs.existsSync(previewExe)) return fail('preview unavailable — LOVE not found at ' + previewExe + ' (set LOVE_PATH)');

            const fogSpecJson = JSON.stringify(parsed.fog || {});
            const mapId = String(parsed.mapId || '');

            execOpenedProject(previewExe, ['preview-fog', fogSpecJson, mapId], {
                timeout: 15000,
                windowsHide: true,
                maxBuffer: 4 * 1024 * 1024
            }, (err, stdout) => {
                const text = String(stdout || '');
                const begin = text.indexOf('PREVIEW BEGIN');
                const end = text.indexOf('PREVIEW END');
                if (begin === -1 || end === -1 || end < begin) {
                    return fail('preview produced no output' + (err ? ' (' + err.message + ')' : ''));
                }
                const jsonText = text.slice(begin + 'PREVIEW BEGIN'.length, end).trim();
                try {
                    JSON.parse(jsonText);
                } catch (e) {
                    return fail('preview output was not valid JSON: ' + e.message);
                }
                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(jsonText);
            });
        });
    } else if (req.method === 'POST' && req.url === '/save') {
        let body = '';
        req.on('data', chunk => { body += chunk; });
        req.on('end', () => {
            try {
                const payload = JSON.parse(body);

                // Stale-save guard: refuse the whole save if any resource the
                // payload would write changed on disk since the editor loaded
                // its representation-aware token.
                const clientVersions = payload._fileVersions;
                if (clientVersions && typeof clientVersions === 'object') {
                    const stale = DATA_FILES.filter(name =>
                        payload[name] !== undefined &&
                        payload[name] !== null &&
                        clientVersions[name] !== undefined &&
                        clientVersions[name] !== null &&
                        clientVersions[name] !== resourceVersion(name)
                    );
                    if (stale.length > 0) {
                        console.warn(`SAVE REJECTED (stale): ${stale.join(', ')} changed on disk since the editor loaded`);
                        res.writeHead(409, { 'Content-Type': 'application/json' });
                        res.end(JSON.stringify({
                            success: false,
                            staleFiles: stale,
                            message: `Save blocked: ${stale.join(', ')} changed on disk after the editor loaded. Reload the editor (browser refresh) to pick up the new data, or your save would overwrite it.`
                        }));
                        return;
                    }
                }

                // Validate the complete authored payload before the first write.
                // Storage kind is explicit metadata: never infer an ordered
                // collection or keyed registry from JavaScript/Lua table shape.
                const pending = [];
                DATA_FILES.forEach(name => {
                    const content = payload[name];
                    if (content === undefined || content === null) return;
                    const spec = authoredStorage.resourceSpec(name);
                    authoredStorage.validateResource(content, name, spec);
                    pending.push({ name, content, spec });
                });

                pending.forEach(({ name, content, spec }) => {
                    authoredStorage.writeResource(DATA_ROOT, name, content, spec);
                });

                // Notify Love2D game to reload if it is running
                const notifyReq = http.request({
                    hostname: '127.0.0.1',
                    port: GAME_PORT,
                    path: '/reload',
                    method: 'GET',
                    timeout: 500
                }, (notifyRes) => {});
                notifyReq.on('error', (err) => {
                    // Ignore errors if game is not running
                });
                notifyReq.on('timeout', () => {
                    notifyReq.destroy();
                });
                notifyReq.end();

                res.writeHead(200, { 'Content-Type': 'application/json' });
                // Fresh tokens so the editor's next save validates against
                // the representation it just wrote.
                res.end(JSON.stringify({ success: true, message: 'Saved successfully!', versions: allFileVersions() }));
            } catch (err) {
                res.writeHead(400, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ success: false, message: err.message }));
            }
        });
    } else if (req.method === 'GET' && req.url === '/validate') {
        // Runs the engine's own validator (`lovec . validate`) against the
        // SAVED data files and relays its verdict. One validator, zero
        // duplicated schema: the editor surfaces exactly what the game
        // would refuse to load. Reflects the last save, like the previews.
        const respond = (payload) => {
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify(payload));
        };
        if (!fs.existsSync(previewExe)) {
            return respond({ ok: false, problems: ['validation unavailable — LOVE not found at ' + previewExe + ' (set LOVE_PATH)'] });
        }
        execOpenedProject(previewExe, ['validate'], {
            timeout: 60000,
            windowsHide: true,
            maxBuffer: 4 * 1024 * 1024
        }, (err, stdout) => {
            const text = String(stdout || '');
            if (text.includes('VALIDATE OK')) return respond({ ok: true, problems: [] });
            const idx = text.indexOf('VALIDATE FAIL:');
            const problems = idx >= 0
                ? text.slice(idx + 'VALIDATE FAIL:'.length).trim().split('\n').map(l => l.trim()).filter(Boolean)
                : ['validator produced no verdict' + (err ? ' (' + err.message + ')' : '')];
            respond({ ok: false, problems });
        });
    } else if (req.method === 'POST' && req.url === '/play') {
        if (!fs.existsSync(LOVE_EXE)) {
            res.writeHead(500, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ success: false, message: 'LOVE not found at ' + LOVE_EXE + ' (set LOVE_PATH)' }));
            return;
        }
        execOpenedProject(LOVE_EXE, [], {}, (err) => {
            if (err) console.error(`Failed to launch Love2D: ${err}`);
        });
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ success: true, message: 'Game launched!' }));
    } else if (req.method === 'POST' && req.url === '/screenshots') {
        const respond = (payload) => {
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify(payload));
        };
        if (!fs.existsSync(previewExe)) {
            return respond({ success: false, message: 'LOVE not found at ' + previewExe + ' (set LOVE_PATH)' });
        }
        execOpenedProject(previewExe, ['screenshots'], {
            timeout: 120000,
            windowsHide: true,
            maxBuffer: 64 * 1024 * 1024
        }, (err, stdout) => {
            const text = String(stdout || '');
            const begin = text.indexOf('SCREENSHOTS BEGIN');
            const end = text.indexOf('SCREENSHOTS END', begin);
            if (begin < 0 || end < 0) {
                return respond({ success: false, message: err ? err.message : 'capture suite produced no result' });
            }
            let payload;
            try {
                payload = JSON.parse(text.slice(begin + 'SCREENSHOTS BEGIN'.length, end).trim());
            } catch (e) {
                return respond({ success: false, message: 'capture result was not valid JSON: ' + e.message });
            }
            if (payload.error) {
                return respond({ success: false, message: payload.error });
            }

            const outputDir = path.resolve(INSTALL_ROOT, 'screenshots');
            if (path.dirname(outputDir) !== INSTALL_ROOT) {
                return respond({ success: false, message: 'refusing unsafe screenshot output path' });
            }
            fs.rmSync(outputDir, { recursive: true, force: true });
            for (const capture of payload.captures || []) {
                if (!/^[a-z0-9_-]+\/[a-z0-9_-]+\/[a-z0-9_.-]+\.png$/.test(capture.path)) {
                    return respond({ success: false, message: 'invalid capture path: ' + capture.path });
                }
                const filePath = path.resolve(outputDir, capture.path);
                if (!filePath.startsWith(outputDir + path.sep)) {
                    return respond({ success: false, message: 'refusing capture path outside output directory' });
                }
                fs.mkdirSync(path.dirname(filePath), { recursive: true });
                fs.writeFileSync(filePath, Buffer.from(capture.image, 'base64'));
            }
            respond({
                success: true,
                count: (payload.captures || []).length,
                width: payload.width,
                height: payload.height,
                directory: outputDir
            });
        });
    // ------------------------------------------------------------------
    // Legacy AI generator bridge. #369 replaces its campaign-shaped output
    // with explicit fixture Projects. These endpoints may generate/inspect old
    // output in the meantime, but there is intentionally no activate endpoint
    // and no path from generator state to DATA_ROOT/Test Play.
    // ------------------------------------------------------------------
    } else if (req.method === 'POST' && req.url === '/campaign-gen/start') {
        let body = '';
        req.on('data', c => { body += c; });
        req.on('end', () => {
            if (genProc) {
                res.writeHead(409, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ success: false, message: 'A generation run is already in progress.' }));
                return;
            }
            let p;
            try { p = JSON.parse(body); } catch (e) { p = null; }
            if (!p || !p.name || !/^[a-z0-9_]+$/.test(p.name) || !p.pitch) {
                res.writeHead(400, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ success: false, message: 'Need a snake_case name and a pitch.' }));
                return;
            }

            // Provider selection: defaults to openrouter
            const provider = p.provider || 'openrouter';

            // Resolve API key for the selected provider.
            const keyMap = {
                openrouter: { field: 'openrouterApiKey', env: 'OPENROUTER_API_KEY' },
                deepseek:  { field: 'deepseekApiKey',  env: 'DEEPSEEK_API_KEY' },
                gemini:    { field: 'geminiApiKey',    env: 'GEMINI_API_KEY' },
            };
            const km = keyMap[provider];
            if (!km) {
                res.writeHead(400, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ success: false, message: `Unknown provider '${provider}'.` }));
                return;
            }
            const apiKey = p[km.field] || process.env[km.env] || genApiKeys[provider];
            if (!apiKey) {
                const hint = provider === 'openrouter' ? 'OPENROUTER_API_KEY' : provider === 'deepseek' ? 'DEEPSEEK_API_KEY' : 'GEMINI_API_KEY';
                res.writeHead(400, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ success: false, message: `No API key for ${provider}: set ${hint} or supply one in the UI.` }));
                return;
            }
            if (p[km.field]) genApiKeys[provider] = p[km.field]; // session memory only

            const { spawn } = require('child_process');
            const args = [path.join(INSTALL_ROOT, 'tools', 'campaign-gen', 'gen.js'), '--name', p.name];
            if (p.stage) args.push('--stage', p.stage);
            if (p.resume) args.push('--resume');
            if (provider !== 'openrouter') args.push('--provider', provider);
            args.push(p.pitch);
            genLog = '';
            genStatus = 'running';
            genProc = spawn(process.execPath, args, {
                cwd: INSTALL_ROOT,
                env: Object.assign({}, process.env, {
                    [km.env]: apiKey,
                    CAMPAIGN_GEN_PROVIDER: provider,
                    CAMPAIGN_GEN_MODELS: JSON.stringify(p.models || {}),
                }),
            });
            genProc.stdout.on('data', d => { genLog += d.toString(); if (genLog.length > 2000000) genLog = genLog.slice(-1500000); });
            genProc.stderr.on('data', d => { genLog += d.toString(); });
            genProc.on('exit', code => {
                genStatus = code === 0 ? 'success' : 'failed';
                genProc = null;
            });
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ success: true }));
        });
    } else if (req.method === 'GET' && req.url.startsWith('/campaign-gen/status')) {
        const from = parseInt(new URL(req.url, 'http://x').searchParams.get('from') || '0', 10) || 0;
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ status: genStatus, len: genLog.length, chunk: genLog.slice(from) }));
    } else if (req.method === 'POST' && req.url === '/campaign-gen/cancel') {
        if (genProc) { genProc.kill(); genStatus = 'cancelled'; }
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ success: true }));
    } else if (req.method === 'GET' && req.url === '/campaign-gen/models') {
        // Public OpenRouter catalogue, cached for the session; trimmed to
        // what the picker needs (id, name, prompt/completion pricing).
        if (genModelCache) {
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(genModelCache);
        } else {
            fetch('https://openrouter.ai/api/v1/models').then(r => r.json()).then(j => {
                const trimmed = (j.data || []).map(m => ({
                    id: m.id, name: m.name,
                    promptPrice: m.pricing && m.pricing.prompt,
                    completionPrice: m.pricing && m.pricing.completion,
                }));
                genModelCache = JSON.stringify(trimmed);
                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(genModelCache);
            }).catch(e => {
                res.writeHead(502, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ error: String(e) }));
            });
        }
    } else if (req.method === 'GET' && req.url === '/campaign-gen/config') {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(fs.readFileSync(path.join(INSTALL_ROOT, 'tools', 'campaign-gen', 'config.json'), 'utf8'));
    // ------------------------------------------------------------------
    // Export bridge (tools/export/export-game.js): File -> Export Game...
    // The exporter is a standalone CLI and stays that way -- the editor
    // spawns it and relays its log. No build logic lives here, and the
    // destination is always the installation's dist/ so a browser request can
    // never choose where the filesystem gets written.
    // ------------------------------------------------------------------
    } else if (req.method === 'GET' && req.url.startsWith('/export/preflight')) {
        const query = new URL(req.url, 'http://x').searchParams;
        const target = query.get('target') || 'love';
        const checks = [];
        const check = (label, fn) => {
            try {
                const detail = fn();
                checks.push({ label, state: 'ok', detail: detail || '' });
            } catch (e) {
                checks.push({ label, state: 'fail', detail: e.message });
            }
        };

        check('Project authored data present', () => {
            const source = exporter.projectDataSource(PROJECT_ROOT);
            if (!fs.existsSync(source) || !fs.statSync(source).isDirectory()) throw new Error('missing Project data/');
            return 'data/';
        });
        check('Runtime manifest valid', () => {
            const manifest = exporter.readManifest();
            const runtimeSources = [
                ...manifest.rootFiles,
                ...manifest.runtimeDirectories,
                manifest.releaseConfig,
                ...manifest.dataRuntimeFiles.map(f => path.join('data', f)),
            ];
            const projectSources = manifest.projectDirectories || [];
            const missingRuntime = runtimeSources.filter(rel => !fs.existsSync(path.join(INSTALL_ROOT, rel)));
            const missingProject = projectSources.filter(rel => !fs.existsSync(path.join(PROJECT_ROOT, rel)));
            const missing = [
                ...missingRuntime.map(rel => `runtime:${rel}`),
                ...missingProject.map(rel => `project:${rel}`),
            ];
            if (missing.length) throw new Error('declared but missing: ' + missing.join(', '));
            return `${runtimeSources.length} runtime + ${projectSources.length} project sources`;
        });
        // Success details stay free of machine-specific absolute paths --
        // this dialog is one of G6's photographed states. A failure names
        // the path, because there the path is the actionable part.
        check('LÖVE runtime found', () => {
            if (target === 'windows-x64') {
                exporter.requiredWindowsRuntime(LOVE_EXE);
                return 'configured runtime + its redistributable DLLs';
            }
            if (!fs.existsSync(LOVE_EXE)) throw new Error('not found at ' + LOVE_EXE + ' (set LOVE_PATH)');
            return 'configured runtime';
        });
        check('Effekseer shim', () => {
            // The shim ships beside the executable, so only a platform
            // packager can carry it — a bare .love never does.
            if (target !== 'windows-x64') return 'not applicable to this target';
            if (!exporter.projectNeedsEffekseer(PROJECT_ROOT)) return 'not required — Project authors no Effekseer tracks';
            const shim = path.join(INSTALL_ROOT, 'effekseer_shim.dll');
            if (!fs.existsSync(shim)) throw new Error('required by authored animations but missing — build it with tools/effekseer/build.ps1');
            const exported = exporter.verifyShim(shim, INSTALL_ROOT);
            return `exports all ${exported} declared symbols; ships beside the executable`;
        });
        // The authored-data validator is the exporter's first stage validation;
        // it costs a full LÖVE boot, so the dialog reports it rather than
        // paying for it twice on every open.
        checks.push({ label: 'Authored data valid', state: 'pending', detail: 'runs against the exact staged Project before packing' });

        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({
            target,
            outputDir: 'dist/',
            checks,
        }));
    } else if (req.method === 'POST' && req.url === '/export/start') {
        let body = '';
        req.on('data', c => { body += c; });
        req.on('end', () => {
            const fail = (code, message) => {
                res.writeHead(code, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ success: false, message }));
            };
            if (exportProc) return fail(409, 'An export is already in progress.');
            let p;
            try { p = JSON.parse(body); } catch (e) { p = null; }
            if (!p) return fail(400, 'Malformed export request.');
            const target = p.target || 'love';
            if (!['love', 'windows-x64'].includes(target)) return fail(400, `Unknown export target '${target}'.`);

            const outputDir = path.join(INSTALL_ROOT, 'dist');
            const args = [
                path.join(INSTALL_ROOT, 'tools', 'export', 'export-game.js'),
                '--target', target,
                '--project', PROJECT_ROOT,
                '--output', outputDir,
            ];
            const { spawn } = require('child_process');
            // Do not leak a machine-specific absolute Project path into the
            // Studio log/G6 state; the subprocess still receives the real path.
            exportLog = `> node tools/export/export-game.js --target ${target} --project <opened-project>\n`;
            exportStatus = 'running';
            exportResult = { target, outputDir: 'dist/' };
            exportProc = spawn(process.execPath, args, { cwd: INSTALL_ROOT });
            const absorb = d => {
                exportLog += d.toString();
                if (exportLog.length > 2000000) exportLog = exportLog.slice(-1500000);
            };
            exportProc.stdout.on('data', absorb);
            exportProc.stderr.on('data', absorb);
            exportProc.on('exit', code => {
                exportStatus = exportStatus === 'cancelled' ? 'cancelled' : (code === 0 ? 'success' : 'failed');
                exportProc = null;
            });
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ success: true, outputDir }));
        });
    } else if (req.method === 'GET' && req.url.startsWith('/export/status')) {
        const from = parseInt(new URL(req.url, 'http://x').searchParams.get('from') || '0', 10) || 0;
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ status: exportStatus, len: exportLog.length, chunk: exportLog.slice(from), result: exportResult }));
    } else if (req.method === 'POST' && req.url === '/export/cancel') {
        if (exportProc) { exportStatus = 'cancelled'; exportProc.kill(); }
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ success: true }));
    } else if (req.method === 'POST' && req.url === '/export/open-folder') {
        // Deliberately takes no path: the only folder the editor will open
        // is the export root it just wrote.
        const outputDir = path.join(INSTALL_ROOT, 'dist');
        if (!fs.existsSync(outputDir)) {
            res.writeHead(404, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ success: false, message: 'No export output yet.' }));
        } else {
            require('child_process').spawn('explorer.exe', [outputDir], { detached: true, stdio: 'ignore' }).unref();
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ success: true }));
        }
    } else if (req.method === 'POST' && req.url === '/play-test-battle') {
        if (!fs.existsSync(LOVE_EXE)) {
            res.writeHead(500, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ success: false, message: 'LOVE not found at ' + LOVE_EXE + ' (set LOVE_PATH)' }));
            return;
        }
        execOpenedProject(LOVE_EXE, ['test-battle'], {}, (err) => {
            if (err) console.error(`Failed to launch Love2D in test battle: ${err}`);
        });
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ success: true, message: 'Test battle launched!' }));
    } else if (req.method === 'GET' && req.url.startsWith('/ping')) {
        const parsedUrl = new URL(req.url, 'http://127.0.0.1:8080');
        const scene = parsedUrl.searchParams.get('scene') || 'unknown';
        console.log(`\n[GAME STATUS PING] Game connected! Scene: ${scene.toUpperCase()}`);
        console.log(`[GAME STATUS PING] Build checks: Input Cooldown & Repeat Filters are fully active.\n`);
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ success: true }));
    } else if (req.method === 'GET' && req.url === '/api/editor-themes') {
        try {
            const filePath = path.join(__dirname, 'themes.json');
            if (fs.existsSync(filePath)) {
                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(fs.readFileSync(filePath, 'utf8'));
            } else {
                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify([]));
            }
        } catch (e) {
            res.writeHead(500, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: e.message }));
        }
    } else if (req.method === 'POST' && req.url === '/api/editor-themes') {
        let body = '';
        req.on('data', chunk => { body += chunk; });
        req.on('end', () => {
            try {
                const themes = JSON.parse(body);
                const filePath = path.join(__dirname, 'themes.json');
                fs.writeFileSync(filePath, JSON.stringify(themes, null, 2) + '\n', 'utf8');
                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ success: true }));
            } catch (e) {
                res.writeHead(400, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ success: false, message: e.message }));
            }
        });
    } else {
        res.writeHead(404, { 'Content-Type': 'text/plain' });
        res.end('Not Found');
    }
    } catch (serverErr) {
        console.error('Unhandled server request error:', serverErr);
        if (!res.headersSent) {
            res.writeHead(500, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: 'Internal server error', message: serverErr.message }));
        }
    }
});

process.on('uncaughtException', (err) => {
    console.error('[CRITICAL] Uncaught Exception in editor server:', err);
});

process.on('unhandledRejection', (reason, promise) => {
    console.error('[CRITICAL] Unhandled Rejection in editor server at:', promise, 'reason:', reason);
});

server.listen(PORT, '127.0.0.1', () => {
    console.log(`Editor server running at http://127.0.0.1:${PORT}`);
});

module.exports = server;