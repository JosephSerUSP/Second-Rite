'use strict';

// The environment package is authored Project source, not a member of the
// editor's bulk data database. Keep its narrow Plate Composition save boundary
// here so a form cannot turn into an arbitrary Project-file writer.
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

function version(text) {
    return crypto.createHash('sha256').update(text).digest('hex');
}

function clone(value) { return JSON.parse(JSON.stringify(value)); }

function manifestPath(projectRoot, requested) {
    if (typeof requested !== 'string' || !/^assets\/environments\/.+\/environment\.json$/.test(requested)) {
        throw new Error('Plate manifest must be an environment.json below assets/environments.');
    }
    const normalized = requested.replace(/\\/g, '/');
    if (normalized.split('/').includes('..')) throw new Error('Plate manifest path leaves assets/environments.');
    const root = path.resolve(projectRoot);
    const file = path.resolve(root, normalized);
    if (!file.startsWith(root + path.sep)) throw new Error('Plate manifest path leaves the Project.');
    return { file, normalized };
}

function finite(value, label, positive) {
    if (typeof value !== 'number' || !Number.isFinite(value) || (positive && value <= 0)) {
        throw new Error(`${label} must be a ${positive ? 'positive ' : ''}finite number.`);
    }
}

function calibration(manifest) {
    const pre = manifest && manifest.preRendered;
    if (!pre || pre.mode !== 'layered_2d') throw new Error('Plate Composition requires a layered_2d preRendered package.');
    if (!Array.isArray(pre.imageSize) || pre.imageSize.length !== 2) throw new Error('preRendered.imageSize must be [width,height].');
    pre.imageSize.forEach((value, index) => finite(value, `preRendered.imageSize[${index}]`, true));
    if (!Array.isArray(pre.slicePositions) || pre.slicePositions.length === 0) throw new Error('preRendered.slicePositions must be non-empty.');
    pre.slicePositions.forEach((value, index) => finite(value, `preRendered.slicePositions[${index}]`));
    const projection = pre.playerProjection;
    if (!projection || typeof projection !== 'object') throw new Error('preRendered.playerProjection is required.');
    finite(projection.centerX, 'preRendered.playerProjection.centerX');
    finite(projection.screenY, 'preRendered.playerProjection.screenY');
    ['width', 'height', 'pixelsPerRuntimeY'].forEach(key => finite(projection[key], `preRendered.playerProjection.${key}`, true));
    if (!pre.lane || typeof pre.lane !== 'object') throw new Error('preRendered.lane is required.');
    finite(pre.lane.runtimeCenterY, 'preRendered.lane.runtimeCenterY');
    return {
        imageSize: clone(pre.imageSize),
        slicePositions: clone(pre.slicePositions),
        lane: { runtimeCenterY: pre.lane.runtimeCenterY },
        playerProjection: clone(projection),
    };
}

function applyCalibration(current, proposed) {
    const next = clone(current);
    const value = calibration(proposed);
    // Only the explicit calibration leaves may cross this boundary. Assets,
    // bounds, anchors, and provenance retain their own authoring surfaces.
    next.preRendered.imageSize = value.imageSize;
    next.preRendered.slicePositions = value.slicePositions;
    next.preRendered.lane = Object.assign({}, next.preRendered.lane, value.lane);
    next.preRendered.playerProjection = value.playerProjection;
    calibration(next);
    return next;
}

function read(projectRoot, requested) {
    const target = manifestPath(projectRoot, requested);
    const text = fs.readFileSync(target.file, 'utf8');
    return { path: target.normalized, manifest: JSON.parse(text), version: version(text) };
}

function write(projectRoot, requested, proposed, expectedVersion) {
    const loaded = read(projectRoot, requested);
    if (typeof expectedVersion !== 'string' || expectedVersion !== loaded.version) {
        const error = new Error('Plate package changed on disk after this editor view loaded. Reload it before saving calibration.');
        error.code = 'STALE_PLATE_MANIFEST';
        throw error;
    }
    const next = applyCalibration(loaded.manifest, proposed);
    const text = JSON.stringify(next, null, 2) + '\n';
    const target = manifestPath(projectRoot, requested);
    const temporary = `${target.file}.plate-composition-${process.pid}-${Date.now()}.tmp`;
    try {
        fs.writeFileSync(temporary, text, 'utf8');
        fs.renameSync(temporary, target.file);
    } finally {
        if (fs.existsSync(temporary)) fs.unlinkSync(temporary);
    }
    return { path: target.normalized, manifest: next, version: version(text) };
}

module.exports = { applyCalibration, calibration, manifestPath, read, write };
