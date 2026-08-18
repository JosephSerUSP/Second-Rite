'use strict';

// #667: same-root Test Play / transient preview must consume the same semantic
// runtime data as a staged player without copying engine/assets. Build a
// disposable, Project-relative data tree, apply exact Project/RTP/default
// resolution there, then compile the five source-layout-aware resources.
const fs = require('node:fs');
const path = require('node:path');
const authoredDefaults = require('./authored-default-materializer');
const runtimeDataCompiler = require('./runtime-data-compiler');

const RUNTIME_DATA_ENV = 'THESTRA_RUNTIME_DATA_ROOT';
const SNAPSHOT_PARENT = path.join('tmp', 'editor-runtime-data');

function portable(value) {
    return value.split(path.sep).join('/');
}

function inside(root, candidate, label) {
    const relative = path.relative(root, candidate);
    if (!relative || relative === '.' || relative.startsWith(`..${path.sep}`) || path.isAbsolute(relative)) {
        throw new Error(`${label} must be inside Project root: ${candidate}`);
    }
    return relative;
}

function copyJsonTree(source, destination) {
    if (!fs.existsSync(source) || !fs.statSync(source).isDirectory()) {
        throw new Error(`Project authored data is missing: ${source}`);
    }
    for (const entry of fs.readdirSync(source, { withFileTypes: true })) {
        const from = path.join(source, entry.name);
        const to = path.join(destination, entry.name);
        if (entry.isDirectory()) {
            copyJsonTree(from, to);
        } else if (entry.isFile() && path.extname(entry.name).toLowerCase() === '.json') {
            fs.mkdirSync(path.dirname(to), { recursive: true });
            fs.copyFileSync(from, to);
        }
    }
}

function pruneSourceRepresentation(dataRoot) {
    for (const stem of runtimeDataCompiler.RUNTIME_RESOURCES) {
        fs.rmSync(path.join(dataRoot, stem), { recursive: true, force: true });
    }
}

function createRuntimeDataSnapshot({
    projectDir,
    runtimeDir,
    rtpRoot,
    packageContributions,
    parentDir,
} = {}) {
    if (!projectDir || !runtimeDir) {
        throw new Error('createRuntimeDataSnapshot requires projectDir and runtimeDir');
    }
    const projectRoot = fs.realpathSync(projectDir);
    const runtimeRoot = fs.realpathSync(runtimeDir);
    const sourceDataRoot = path.join(projectRoot, 'data');
    // THESTRA_RUNTIME_DATA_ROOT is resolved by the engine against the mounted
    // LOVE source -- the runtime root. Base the snapshot there so the value
    // means something. Before #700 the Project and runtime roots always
    // coincided, so a Project-relative path was accidentally correct; once they
    // differ it points at nothing and the engine silently falls back to the
    // un-compiled source layout (#744).
    const parent = path.resolve(parentDir || path.join(runtimeRoot, SNAPSHOT_PARENT));
    inside(runtimeRoot, parent, 'runtime-data snapshot parent');
    fs.mkdirSync(parent, { recursive: true });

    const snapshotRoot = fs.mkdtempSync(path.join(parent, 'snapshot-'));
    const dataRoot = path.join(snapshotRoot, 'data');
    try {
        copyJsonTree(sourceDataRoot, dataRoot);
        authoredDefaults.resolveAndMaterialize({
            projectDir: projectRoot,
            runtimeDir: runtimeRoot,
            stageDir: snapshotRoot,
            rtpRoot,
            packageContributions,
            includeSounds: false,
        });
        const compiled = runtimeDataCompiler.materializeRuntimeData({
            sourceDataRoot: dataRoot,
            outputDataRoot: dataRoot,
        });
        pruneSourceRepresentation(dataRoot);

        const relativeDataRoot = portable(inside(runtimeRoot, dataRoot, 'runtime-data snapshot'));
        return {
            snapshotRoot,
            dataRoot,
            relativeDataRoot,
            env: { [RUNTIME_DATA_ENV]: relativeDataRoot },
            manifest: compiled.manifest,
        };
    } catch (error) {
        fs.rmSync(snapshotRoot, { recursive: true, force: true });
        throw error;
    }
}

function removeRuntimeDataSnapshot(snapshot) {
    const root = typeof snapshot === 'string' ? snapshot : snapshot && snapshot.snapshotRoot;
    if (!root) return;
    try {
        fs.rmSync(root, { recursive: true, force: true });
    } catch (error) {
        console.warn(`[runtime-data-snapshot] could not remove ${root}: ${error.message}`);
    }
}

module.exports = {
    RUNTIME_DATA_ENV,
    SNAPSHOT_PARENT,
    copyJsonTree,
    createRuntimeDataSnapshot,
    pruneSourceRepresentation,
    removeRuntimeDataSnapshot,
};
