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
    if (normalized.split('/').some(part => !part || part === '.' || part === '..')) {
        throw new Error('Plate manifest path must be normalized below assets/environments.');
    }
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

function writeManifestText(file, text) {
    const temporary = `${file}.plate-composition-${process.pid}-${Date.now()}.tmp`;
    try {
        fs.writeFileSync(temporary, text, 'utf8');
        fs.renameSync(temporary, file);
    } finally {
        if (fs.existsSync(temporary)) fs.unlinkSync(temporary);
    }
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
    writeManifestText(target.file, text);
    return { path: target.normalized, manifest: next, version: version(text) };
}

// The focused Plate Calibration panel and the full Plate Composition
// inspector share this persistence authority, path checks and version token.
function readPackage(projectRoot, requested) {
    const loaded = read(projectRoot, requested);
    if (loaded.manifest.contractVersion !== 1) throw new Error('Environment package must use contractVersion 1.');
    return {path: loaded.path, file: manifestPath(projectRoot, requested).file,
        version: loaded.version, value: loaded.manifest};
}

function calibrationNumber(value, label) {
    finite(value, label);
    return value;
}

function objectRangeForKey(raw, key) {
    let keyIndex = -1, depth = 0;
    for (let index = 0; index < raw.length; index++) {
        const char = raw[index];
        if (char === '{' || char === '[') depth += 1;
        else if (char === '}' || char === ']') depth -= 1;
        else if (char === '"') {
            const start = index;
            for (index += 1; index < raw.length; index++) {
                if (raw[index] === '\\') index += 1;
                else if (raw[index] === '"') break;
            }
            if (depth === 1 && JSON.parse(raw.slice(start, index + 1)) === key
                    && /^\s*:/.test(raw.slice(index + 1))) {
                keyIndex = start;
                break;
            }
        }
    }
    if (keyIndex < 0) throw new Error('Environment package is missing ' + key + '.');
    const colon = raw.indexOf(':', keyIndex);
    const start = raw.indexOf('{', colon);
    if (colon < 0 || start < 0) throw new Error('Environment package ' + key + ' is not an object.');
    depth = 0;
    let string = false, escape = false;
    for (let index = start; index < raw.length; index++) {
        const char = raw[index];
        if (string) {
            if (escape) escape = false;
            else if (char === '\\') escape = true;
            else if (char === '"') string = false;
            continue;
        }
        if (char === '"') { string = true; continue; }
        if (char === '{') depth += 1;
        else if (char === '}') {
            depth -= 1;
            if (depth === 0) return { start, end: index + 1 };
        }
    }
    throw new Error('Environment package ' + key + ' object is unterminated.');
}

function patchPlayerProjectionRaw(raw, patch) {
    const preRendered = objectRangeForKey(raw, 'preRendered');
    const localRange = objectRangeForKey(raw.slice(preRendered.start, preRendered.end), 'playerProjection');
    const range = { start: preRendered.start + localRange.start, end: preRendered.start + localRange.end };
    let body = raw.slice(range.start, range.end);
    for (const [field, value] of Object.entries(patch)) {
        const pattern = new RegExp('(\\"' + field + '\\"\\s*:\\s*)' +
            '-?(?:\\d+\\.?\\d*|\\.\\d+)(?:[eE][+-]?\\d+)?');
        if (!pattern.test(body)) {
            throw new Error('Environment package playerProjection.' + field + ' is missing or non-numeric.');
        }
        body = body.replace(pattern, (_, prefix) => prefix + JSON.stringify(value));
    }
    return raw.slice(0, range.start) + body + raw.slice(range.end);
}
function writeCalibration(projectRoot, value, patch, expectedVersion) {
    const current = readPackage(projectRoot, value);
    if (typeof expectedVersion !== 'string' || expectedVersion !== current.version) {
        const error = new Error('Environment package changed on disk after Studio loaded it.');
        error.code = 'STALE_ENVIRONMENT_PACKAGE';
        error.currentVersion = current.version;
        throw error;
    }
    if (!patch || typeof patch !== 'object' || Array.isArray(patch)) {
        throw new Error('Environment calibration patch must be an object.');
    }
    calibration(current.value);
    const allowed = new Set(['centerX', 'screenY']);
    const keys = Object.keys(patch);
    if (!keys.length) throw new Error('Environment calibration patch is empty.');
    for (const key of keys) {
        if (!allowed.has(key)) {
            throw new Error(`Environment calibration field '${key}' is not authorable here.`);
        }
    }

    const projection = current.value.preRendered.playerProjection;
    const normalizedPatch = {};
    let changed = false;
    for (const key of keys) {
        const nextValue = calibrationNumber(patch[key], `playerProjection.${key}`);
        normalizedPatch[key] = nextValue;
        if (projection[key] !== nextValue) changed = true;
    }

    if (!changed) {
        return { path: current.path, version: current.version, value: current.value, changed: false };
    }
    const nextRaw = patchPlayerProjectionRaw(fs.readFileSync(current.file, 'utf8'), normalizedPatch);
    const nextValue = JSON.parse(nextRaw);
    calibration(nextValue);
    for (const [field, value] of Object.entries(normalizedPatch)) {
        if (nextValue.preRendered.playerProjection[field] !== value) {
            throw new Error('Calibration patch did not resolve the authored playerProjection.' + field);
        }
    }
    writeManifestText(current.file, nextRaw);
    return {
        path: current.path,
        version: version(nextRaw),
        value: nextValue,
        changed: true
    };
}

module.exports = { applyCalibration, calibration, manifestPath, read, write, readPackage, writeCalibration };
