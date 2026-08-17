'use strict';

// #667 / architecture decision #666: authored physical storage stops at the
// source/build boundary. This compiler runs only after exact Project + pinned
// RTP/package/default materialization and emits one ordinary JSON document per
// semantic runtime resource.
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const authoredStorage = require('../data/authored-storage');

const COMPILER_ID = 'thestra-runtime-data';
const COMPILER_VERSION = 1;
const RUNTIME_RESOURCES = Object.freeze(['units', 'maps', 'flows', 'scenes', 'tilesets']);
const MANIFEST_NAME = 'runtime_data_manifest.json';
const SOURCE_STORAGE_RUNTIME_FILES = Object.freeze([
    'engine/data/authored_storage.lua',
    'engine/data/authored_storage_resolved.lua',
    'engine/data/authored_storage_manifest.json',
]);
const SOURCE_ONLY_PLAYER_FILES = Object.freeze([
    // Deterministic authoring review harness: hashes exact physical Tileset
    // source files and writes review artifacts. It is intentionally source-
    // aware and therefore has no place in a compiled/distributable player.
    'engine/model_census_review.lua',
]);
const DEFAULT_RUNTIME_PROVIDER = path.join(__dirname, 'runtime-semantic-resources.lua');
const DEFAULT_RUNTIME_SERVER = path.join(__dirname, 'runtime-engine-server.lua');

function sha256(value) {
    return crypto.createHash('sha256').update(value).digest('hex');
}

function encodeJson(value) {
    return JSON.stringify(value, null, 2) + '\n';
}

function writeFileAtomic(filePath, contents) {
    fs.mkdirSync(path.dirname(filePath), { recursive: true });
    const temp = path.join(path.dirname(filePath), `.${path.basename(filePath)}.${process.pid}.${Date.now()}.tmp`);
    fs.writeFileSync(temp, contents);
    try {
        fs.renameSync(temp, filePath);
    } catch (error) {
        try { fs.unlinkSync(temp); } catch (_) {}
        throw error;
    }
}

function requireDataRoot(dataRoot, label) {
    if (!dataRoot) throw new Error(`${label || 'runtime data compiler'} requires a data root`);
    const root = path.resolve(dataRoot);
    if (!fs.existsSync(root) || !fs.statSync(root).isDirectory()) {
        throw new Error(`${label || 'runtime data compiler'} data root is missing: ${root}`);
    }
    return root;
}

function requireFile(filePath, label) {
    if (!filePath || !fs.existsSync(filePath) || !fs.statSync(filePath).isFile()) {
        throw new Error(`${label} is missing: ${filePath}`);
    }
    return path.resolve(filePath);
}

function runtimeResourceSpec(dataRoot, stem) {
    const source = authoredStorage.resourceSpec(stem);
    const spec = Object.assign({}, source);

    // `_test` is a repository/validator-only Flow module. A sparse/external
    // Project does not acquire that fixture merely because the source manifest
    // declares it for the root development Project. This is a deliberate
    // source->runtime projection, not loader policy.
    if (stem === 'flows' && Array.isArray(source.modules)
            && !fs.existsSync(path.join(dataRoot, 'flows', '_test.json'))) {
        spec.modules = source.modules.filter(module => module !== '_test');
    }
    return spec;
}

function relativeSourcePath(dataRoot, filePath) {
    const relative = path.relative(dataRoot, filePath);
    if (!relative || relative === '.' || relative.startsWith(`..${path.sep}`) || path.isAbsolute(relative)) {
        throw new Error(`runtime-data provenance escaped staged data root: ${filePath}`);
    }
    return relative.split(path.sep).join('/');
}

function resolveRuntimeData({ dataRoot } = {}) {
    const root = requireDataRoot(dataRoot, 'resolveRuntimeData');
    const values = {};
    const provenance = {};

    // Read every source resource before writing anything. Fragment-backed
    // resources intentionally reject a coexisting monolith; interleaving reads
    // and writes would therefore make the compiler manufacture a false
    // dual-authority state halfway through its own transaction.
    for (const stem of RUNTIME_RESOURCES) {
        const spec = runtimeResourceSpec(root, stem);
        const sources = authoredStorage.authoritativeFiles(root, stem, spec);
        const loaded = authoredStorage.loadResource(root, stem, spec);
        values[stem] = loaded.value;
        provenance[stem] = {
            runtimePath: `data/${stem}.json`,
            sourceRepresentation: loaded.storage,
            sourceVersion: authoredStorage.versionToken(root, stem, spec),
            sourceFiles: sources.map(filePath => relativeSourcePath(root, filePath)),
            projections: stem === 'flows' && !spec.modules.includes('_test')
                ? [{ kind: 'omit-source-only-module', module: '_test' }]
                : [],
        };
    }

    return { values, provenance };
}

function materializeRuntimeData({ sourceDataRoot, outputDataRoot = sourceDataRoot } = {}) {
    const sourceRoot = requireDataRoot(sourceDataRoot, 'materializeRuntimeData');
    if (!outputDataRoot) throw new Error('materializeRuntimeData requires outputDataRoot');
    const outputRoot = path.resolve(outputDataRoot);
    const resolved = resolveRuntimeData({ dataRoot: sourceRoot });
    fs.mkdirSync(outputRoot, { recursive: true });

    for (const stem of RUNTIME_RESOURCES) {
        const encoded = Buffer.from(encodeJson(resolved.values[stem]), 'utf8');
        writeFileAtomic(path.join(outputRoot, `${stem}.json`), encoded);
        resolved.provenance[stem].runtimeSha256 = sha256(encoded);
    }

    const manifest = {
        version: 1,
        compiler: { id: COMPILER_ID, version: COMPILER_VERSION },
        resources: resolved.provenance,
    };
    const manifestPath = path.join(outputRoot, MANIFEST_NAME);
    writeFileAtomic(manifestPath, Buffer.from(encodeJson(manifest), 'utf8'));
    return { manifestPath, manifest, resources: resolved.values };
}

function compileRuntimeStage({
    stageDir,
    runtimeProviderSource = DEFAULT_RUNTIME_PROVIDER,
    runtimeServerSource = DEFAULT_RUNTIME_SERVER,
} = {}) {
    if (!stageDir) throw new Error('compileRuntimeStage requires stageDir');
    const root = path.resolve(stageDir);
    const dataRoot = requireDataRoot(path.join(root, 'data'), 'compileRuntimeStage');
    const marker = path.join(dataRoot, MANIFEST_NAME);
    if (fs.existsSync(marker)) {
        throw new Error(`runtime data is already compiled: ${marker}`);
    }
    const providerSource = requireFile(runtimeProviderSource, 'compiled semantic-resource provider');
    const serverSource = requireFile(runtimeServerSource, 'compiled engine server');

    const result = materializeRuntimeData({ sourceDataRoot: dataRoot, outputDataRoot: dataRoot });

    for (const stem of RUNTIME_RESOURCES) {
        fs.rmSync(path.join(dataRoot, stem), { recursive: true, force: true });
    }
    for (const relative of SOURCE_STORAGE_RUNTIME_FILES) {
        fs.rmSync(path.join(root, ...relative.split('/')), { force: true });
    }
    for (const relative of SOURCE_ONLY_PLAYER_FILES) {
        fs.rmSync(path.join(root, ...relative.split('/')), { force: true });
    }

    // Replace source-side adapters instead of teaching them runtime modes. The
    // final player contains only semantic JSON reads, and its engine.server is
    // inert: localhost authored-resource write authority is a Studio/developer
    // capability, not part of a distributable player.
    fs.mkdirSync(path.join(root, 'engine', 'data'), { recursive: true });
    fs.copyFileSync(providerSource, path.join(root, 'engine', 'data', 'semantic_resources.lua'));
    fs.mkdirSync(path.join(root, 'engine'), { recursive: true });
    fs.copyFileSync(serverSource, path.join(root, 'engine', 'server.lua'));

    return Object.assign({ stageDir: root, dataRoot }, result);
}

module.exports = {
    COMPILER_ID,
    COMPILER_VERSION,
    DEFAULT_RUNTIME_PROVIDER,
    DEFAULT_RUNTIME_SERVER,
    MANIFEST_NAME,
    RUNTIME_RESOURCES,
    SOURCE_ONLY_PLAYER_FILES,
    SOURCE_STORAGE_RUNTIME_FILES,
    compileRuntimeStage,
    materializeRuntimeData,
    resolveRuntimeData,
    runtimeResourceSpec,
};
