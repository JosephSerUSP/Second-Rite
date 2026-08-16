'use strict';

// EXPERIMENT for #632: compile source-oriented authored storage into a small
// runtime-facing monolith set *after* Project/RTP defaults have already been
// materialized into the stage.
//
// This intentionally reuses Studio's resolved Node authored-storage authority
// during the spike rather than writing a fourth fragment parser in the
// exporter. If the experiment is accepted, that shared authority should move
// to a neutral tools/data module; the exporter must not permanently depend on
// an editor-owned path merely because the proof started here.

const fs = require('fs');
const path = require('path');
const authoredStorage = require('../editor/authored-storage');

const RUNTIME_RESOURCES = ['units', 'maps', 'flows', 'scenes', 'tilesets'];
const SOURCE_STORAGE_RUNTIME_FILES = [
    'authored_storage.lua',
    'authored_storage_resolved.lua',
    'authored_storage_manifest.json',
];

function putJson(filePath, value) {
    fs.mkdirSync(path.dirname(filePath), { recursive: true });
    fs.writeFileSync(filePath, JSON.stringify(value, null, 2) + '\n', 'utf8');
}

function runtimeResourceSpec(dataRoot, stem) {
    const source = authoredStorage.resourceSpec(stem);
    const spec = Object.assign({}, source);

    // `_test` is a repository/validator-only Flow module. The source runtime
    // already projects it out for external/sparse Projects when the file is
    // absent. Preserve that existing runtime contract here rather than forcing
    // every exported game to ship a test fixture. This special case is evidence
    // for #632: a production compiler should own one explicit runtime projection
    // of the storage schema instead of making loaders rediscover it.
    if (stem === 'flows' && Array.isArray(source.modules)
            && !fs.existsSync(path.join(dataRoot, 'flows', '_test.json'))) {
        spec.modules = source.modules.filter(module => module !== '_test');
    }
    return spec;
}

function sourcePaths(dataRoot, stem, spec) {
    return authoredStorage.authoritativeFiles(dataRoot, stem, spec)
        .map(filePath => path.relative(dataRoot, filePath).split(path.sep).join('/'));
}

function materializeRuntimeData({ stageDir } = {}) {
    if (!stageDir) throw new Error('runtime data materialization requires stageDir');
    const root = path.resolve(stageDir);
    const dataRoot = path.join(root, 'data');
    if (!fs.existsSync(dataRoot) || !fs.statSync(dataRoot).isDirectory()) {
        throw new Error(`staged runtime has no data directory: ${dataRoot}`);
    }

    const markerPath = path.join(dataRoot, 'authored_runtime_snapshot.json');
    if (fs.existsSync(markerPath)) {
        throw new Error(`staged runtime data is already materialized: ${markerPath}`);
    }

    // Read every source resource before writing any target monolith. A
    // fragment-backed resource rejects a coexisting monolith by design, so
    // interleaving reads/writes would turn the compiler itself into a false
    // dual-authority state half way through the operation.
    const resolved = {};
    const provenance = {};
    for (const stem of RUNTIME_RESOURCES) {
        const spec = runtimeResourceSpec(dataRoot, stem);
        const sources = sourcePaths(dataRoot, stem, spec);
        const loaded = authoredStorage.loadResource(dataRoot, stem, spec);
        resolved[stem] = loaded.value;
        provenance[stem] = {
            sourceRepresentation: loaded.storage,
            sources,
            runtimePath: `data/${stem}.json`,
        };
    }

    for (const stem of RUNTIME_RESOURCES) {
        putJson(path.join(dataRoot, `${stem}.json`), resolved[stem]);
        fs.rmSync(path.join(dataRoot, stem), { recursive: true, force: true });
    }

    // The proof is stronger if the stage can no longer fall back to source
    // storage machinery. Direct same-root development still owns these files;
    // only a materialized stage drops them.
    for (const filename of SOURCE_STORAGE_RUNTIME_FILES) {
        fs.rmSync(path.join(dataRoot, filename), { force: true });
    }

    const marker = {
        version: 1,
        materialized: true,
        resources: provenance,
    };
    putJson(markerPath, marker);
    return { markerPath, marker, resources: resolved };
}

module.exports = {
    RUNTIME_RESOURCES,
    SOURCE_STORAGE_RUNTIME_FILES,
    materializeRuntimeData,
    runtimeResourceSpec,
};
