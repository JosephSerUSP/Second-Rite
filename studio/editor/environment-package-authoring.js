'use strict';

const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');

function logicalPath(value) {
    if (typeof value !== 'string' || !value.trim()) {
        throw new Error('Environment package path is required.');
    }
    const normalized = value.replace(/\\/g, '/').replace(/^\/+/, '');
    const segments = normalized.split('/');
    if (segments.includes('..') || segments.includes('.') || segments.some(segment => segment === '')) {
        throw new Error('Environment package path must be a normalized Project-relative path.');
    }
    if (!/^assets\/environments\/.+\/environment\.json$/.test(normalized)) {
        throw new Error('Environment package calibration is limited to assets/environments/**/environment.json.');
    }
    return normalized;
}

function resolve(projectRoot, value) {
    const logical = logicalPath(value);
    const root = path.resolve(projectRoot);
    const file = path.resolve(root, ...logical.split('/'));
    if (file !== root && !file.startsWith(root + path.sep)) {
        throw new Error('Environment package path escapes the opened Project.');
    }
    return { logical, file };
}

function token(raw) {
    return crypto.createHash('sha256').update(raw).digest('hex');
}

function parse(raw, logical) {
    let manifest;
    try { manifest = JSON.parse(raw); }
    catch (error) { throw new Error(`Environment package ${logical} is not valid JSON: ${error.message}`); }
    if (!manifest || manifest.contractVersion !== 1) {
        throw new Error(`Environment package ${logical} does not use contractVersion 1.`);
    }
    const spec = manifest.preRendered;
    if (!spec || spec.mode !== 'layered_2d') {
        throw new Error(`Environment package ${logical} has no layered_2d preRendered calibration.`);
    }
    if (!spec.playerProjection || typeof spec.playerProjection !== 'object') {
        throw new Error(`Environment package ${logical} has no playerProjection.`);
    }
    return manifest;
}

function read(projectRoot, value) {
    const { logical, file } = resolve(projectRoot, value);
    const raw = fs.readFileSync(file, 'utf8');
    return { path: logical, file, version: token(raw), value: parse(raw, logical) };
}

function finite(value, label) {
    const number = Number(value);
    if (!Number.isFinite(number)) throw new Error(`${label} must be finite.`);
    return number;
}

function objectRangeForKey(raw, key) {
    const keyIndex = raw.indexOf(JSON.stringify(key));
    if (keyIndex < 0) throw new Error('Environment package is missing ' + key + '.');
    const colon = raw.indexOf(':', keyIndex);
    const start = raw.indexOf('{', colon);
    if (colon < 0 || start < 0) throw new Error('Environment package ' + key + ' is not an object.');
    let depth = 0, string = false, escape = false;
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
    const range = objectRangeForKey(raw, 'playerProjection');
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
    const current = read(projectRoot, value);
    if (expectedVersion && expectedVersion !== current.version) {
        const error = new Error('Environment package changed on disk after Studio loaded it.');
        error.code = 'STALE_ENVIRONMENT_PACKAGE';
        error.currentVersion = current.version;
        throw error;
    }
    if (!patch || typeof patch !== 'object' || Array.isArray(patch)) {
        throw new Error('Environment calibration patch must be an object.');
    }
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
        const nextValue = finite(patch[key], `playerProjection.${key}`);
        normalizedPatch[key] = nextValue;
        if (projection[key] !== nextValue) changed = true;
    }

    if (!changed) {
        return { path: current.path, version: current.version, value: current.value, changed: false };
    }
    const nextRaw = patchPlayerProjectionRaw(fs.readFileSync(current.file, 'utf8'), normalizedPatch);
    const nextValue = parse(nextRaw, current.path);
    fs.writeFileSync(current.file, nextRaw, 'utf8');
    return {
        path: current.path,
        version: token(nextRaw),
        value: nextValue,
        changed: true
    };
}

module.exports = {
    logicalPath, resolve, token, read, writeCalibration,
    objectRangeForKey, patchPlayerProjectionRaw
};
