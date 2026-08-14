'use strict';

// Resolved authored-storage surface used by Studio. The physical JSON/fragments
// implementation is preserved in authored-storage-physical.js; this layer adds
// only the #390 inherited engineRegistry contract so callers do not each invent
// their own RTP overlay semantics.
const fs = require('fs');
const path = require('path');
const physical = require('./authored-storage-physical');
const rtp = require('../export/rtp-resource-resolver');
const engineRegistry = require('../export/engine-registry-resolver');

function engineResolution(root) {
    const projectDir = path.dirname(path.resolve(root));
    const system = rtp.projectSystem(projectDir);
    const rtpRoot = process.env[rtp.RTP_ROOT_ENV] || path.resolve(__dirname, '..', '..', 'rtp');
    return engineRegistry.resolve({ projectDir, systemValue: system.value, rtpRoot });
}

function authoritativeFiles(root, stem, spec = physical.resourceSpec(stem)) {
    if (stem !== 'engine') return physical.authoritativeFiles(root, stem, spec);
    return engineResolution(root).sources.map(source => source.sourcePath);
}

function loadResource(root, stem, spec = physical.resourceSpec(stem)) {
    if (stem !== 'engine') return physical.loadResource(root, stem, spec);
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
    if (stem !== 'engine') return physical.versionToken(root, stem, spec);
    return engineResolution(root).version;
}

function writeResource(root, stem, value, spec = physical.resourceSpec(stem)) {
    if (stem !== 'engine') return physical.writeResource(root, stem, value, spec);
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

function snapshotResource(root, stem, destinationRoot, spec = physical.resourceSpec(stem)) {
    if (stem !== 'engine') return physical.snapshotResource(root, stem, destinationRoot, spec);
    const loaded = loadResource(root, stem, spec);
    const target = path.join(destinationRoot, `${stem}.json`);
    fs.mkdirSync(path.dirname(target), { recursive: true });
    fs.writeFileSync(target, JSON.stringify(loaded.value, null, 2) + '\n', 'utf8');
    return target;
}

module.exports = Object.assign({}, physical, {
    authoritativeFiles,
    engineResolution,
    loadResource,
    snapshotResource,
    versionToken,
    writeResource,
});
