'use strict';

// Resolved authored-storage surface used by Studio. The physical JSON/fragments
// implementation is preserved in authored-storage-physical.js; this layer adds
// inherited engineRegistry resolution (#390) plus #392's explicit empty
// fragmented-catalog representation for genuinely blank Projects.
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const physical = require('./authored-storage-physical');
const rtp = require('../export/rtp-resource-resolver');
const engineRegistry = require('../export/engine-registry-resolver');

function hasProjectSystem(root) {
    const systemPath = path.join(path.resolve(root), 'system.json');
    return fs.existsSync(systemPath) && fs.statSync(systemPath).isFile();
}

function engineResolution(root) {
    const projectDir = path.dirname(path.resolve(root));
    const system = rtp.projectSystem(projectDir);
    const rtpRoot = process.env[rtp.RTP_ROOT_ENV] || path.resolve(__dirname, '..', '..', 'rtp');
    return engineRegistry.resolve({ projectDir, systemValue: system.value, rtpRoot });
}

function emptyIndexPath(root, stem) {
    return path.join(path.resolve(root), stem, 'index.json');
}

function explicitEmptyIndex(root, stem, spec = physical.resourceSpec(stem)) {
    if (spec.representation !== 'fragments'
            || (spec.kind !== 'ordered_collection' && spec.kind !== 'keyed_registry')) return false;
    const filePath = emptyIndexPath(root, stem);
    if (!fs.existsSync(filePath) || !fs.statSync(filePath).isFile()) return false;
    let parsed;
    try { parsed = JSON.parse(fs.readFileSync(filePath, 'utf8')); }
    catch (error) { throw new Error(`authored empty-catalog marker is not readable JSON: ${filePath}: ${error.message}`); }
    const files = Array.isArray(parsed) ? parsed : parsed && parsed.files;
    return Array.isArray(files) && files.length === 0;
}

function emptyValue(spec) {
    return spec.kind === 'ordered_collection' ? [] : {};
}

function isExplicitEmptyValue(value, spec) {
    if (spec.kind === 'ordered_collection') return Array.isArray(value) && value.length === 0;
    if (spec.kind === 'keyed_registry') {
        return value && typeof value === 'object' && !Array.isArray(value) && Object.keys(value).length === 0;
    }
    return false;
}

function emptyVersion(root, stem, spec) {
    const filePath = emptyIndexPath(root, stem);
    const hash = crypto.createHash('sha256');
    hash.update(`authored-resource\0${stem}\0${spec.kind}\0${spec.representation}\0`);
    hash.update(fs.readFileSync(filePath));
    return hash.digest('hex');
}

function writeEmptyMarker(root, stem, spec) {
    const directory = path.join(path.resolve(root), stem);
    fs.mkdirSync(directory, { recursive: true });
    for (const name of fs.readdirSync(directory)) {
        if (name.toLowerCase().endsWith('.json')) fs.unlinkSync(path.join(directory, name));
    }
    fs.writeFileSync(path.join(directory, 'index.json'), JSON.stringify({ files: [] }, null, 2) + '\n', 'utf8');
    return { storage: 'fragments', version: emptyVersion(root, stem, spec) };
}

function authoritativeFiles(root, stem, spec = physical.resourceSpec(stem)) {
    if (explicitEmptyIndex(root, stem, spec)) return [emptyIndexPath(root, stem)];
    if (stem !== 'engine' || !hasProjectSystem(root)) return physical.authoritativeFiles(root, stem, spec);
    return engineResolution(root).sources.map(source => source.sourcePath);
}

function loadResource(root, stem, spec = physical.resourceSpec(stem)) {
    if (explicitEmptyIndex(root, stem, spec)) {
        return { value: emptyValue(spec), storage: 'fragments', sourceById: {} };
    }
    if (stem !== 'engine' || !hasProjectSystem(root)) return physical.loadResource(root, stem, spec);
    const resolved = engineResolution(root);
    physical.validateResource(resolved.value, stem, spec, '<resolved engineRegistry>');
    return {
        value: resolved.value,
        storage: resolved.baselineValue ? 'composed' : 'monolith',
        sourceById: {},
        provider: resolved.provider,
        sources: resolved.sources,
        baselineValue: resolved.baselineValue,
        overlayValue: resolved.overlayValue,
    };
}

function versionToken(root, stem, spec = physical.resourceSpec(stem)) {
    if (explicitEmptyIndex(root, stem, spec)) return emptyVersion(root, stem, spec);
    if (stem !== 'engine' || !hasProjectSystem(root)) return physical.versionToken(root, stem, spec);
    return engineResolution(root).version;
}

function writeResource(root, stem, value, spec = physical.resourceSpec(stem)) {
    if (spec.representation === 'fragments'
            && (spec.kind === 'ordered_collection' || spec.kind === 'keyed_registry')) {
        if (isExplicitEmptyValue(value, spec)) return writeEmptyMarker(root, stem, spec);
        if (explicitEmptyIndex(root, stem, spec) && spec.kind === 'keyed_registry') {
            fs.unlinkSync(emptyIndexPath(root, stem));
        }
    }

    if (stem !== 'engine' || !hasProjectSystem(root)) return physical.writeResource(root, stem, value, spec);
    const resolved = engineResolution(root);
    if (!resolved.baselineValue) return physical.writeResource(root, stem, value, spec);

    physical.validateResource(value, stem, spec, '<write resolved engineRegistry>');
    for (const [key, inherited] of Object.entries(resolved.baselineValue)) {
        if (!Object.prototype.hasOwnProperty.call(value, key)
                || JSON.stringify(value[key]) !== JSON.stringify(inherited)) {
            throw new Error(`Cannot edit inherited engineRegistry key '${key}' through bulk save; Make Local belongs to #392.`);
        }
    }
    const local = {};
    for (const [key, entry] of Object.entries(value)) {
        if (!Object.prototype.hasOwnProperty.call(resolved.baselineValue, key)) local[key] = entry;
    }
    const written = physical.writeResource(root, stem, local, spec);
    return Object.assign({}, written, { version: versionToken(root, stem, spec) });
}

function loadRegistry(root, stem, spec = physical.resourceSpec(stem)) {
    if (spec.kind !== 'keyed_registry') throw new Error(`authored resource '${stem}' is not a keyed registry`);
    const loaded = loadResource(root, stem, spec);
    return { records: loaded.value, storage: loaded.storage, sourceById: loaded.sourceById || {} };
}

function loadOrderedCollection(root, stem, spec = physical.resourceSpec(stem)) {
    if (spec.kind !== 'ordered_collection') throw new Error(`authored resource '${stem}' is not an ordered collection`);
    const loaded = loadResource(root, stem, spec);
    return { entries: loaded.value, storage: loaded.storage };
}

function writeRegistryRecord(root, stem, record, expectedVersion = null, spec = physical.resourceSpec(stem)) {
    if (spec.kind !== 'keyed_registry') throw new Error(`authored resource '${stem}' is not a keyed registry`);
    const recordId = physical.validateRegistryRecord(record, stem, `<write ${stem}>`);
    const loaded = loadRegistry(root, stem, spec);
    const currentVersion = versionToken(root, stem, spec);
    const exists = Object.prototype.hasOwnProperty.call(loaded.records, recordId);
    if (exists && expectedVersion !== currentVersion) {
        const error = new Error(`registry '${stem}' changed on disk after the record was loaded`);
        error.code = 'STALE_AUTHORED_DATA';
        error.currentVersion = currentVersion;
        throw error;
    }
    const next = Object.assign({}, loaded.records, { [recordId]: record });
    return Object.assign({ id: recordId }, writeResource(root, stem, next, spec));
}

function snapshotResource(root, stem, destinationRoot, spec = physical.resourceSpec(stem)) {
    if (!explicitEmptyIndex(root, stem, spec) && (stem !== 'engine' || !hasProjectSystem(root))) {
        return physical.snapshotResource(root, stem, destinationRoot, spec);
    }
    const loaded = loadResource(root, stem, spec);
    const target = path.join(destinationRoot, `${stem}.json`);
    fs.mkdirSync(path.dirname(target), { recursive: true });
    fs.writeFileSync(target, JSON.stringify(loaded.value, null, 2) + '\n', 'utf8');
    return target;
}

module.exports = Object.assign({}, physical, {
    authoritativeFiles,
    emptyIndexPath,
    engineResolution,
    explicitEmptyIndex,
    hasProjectSystem,
    loadOrderedCollection,
    loadRegistry,
    loadResource,
    snapshotResource,
    versionToken,
    writeRegistryRecord,
    writeResource,
});
