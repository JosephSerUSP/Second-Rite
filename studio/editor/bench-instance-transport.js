'use strict';

// Reproducible #757 experiment harness. Run from the repository checkout after
// staging a runnable Project, for example:
//   node studio/editor/bench-instance-transport.js --root <stage> --lovec <lovec.exe>
//
// It deliberately gives the child a 256 MiB stdout allowance: Map 3 exceeds the
// production bridge's 64 MiB ceiling in the baseline format, and that overflow
// is one of the things this representation experiment is meant to measure.
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { performance } = require('node:perf_hooks');
const adapter = require('./js/second-rite-editor-adapter.js');

const MAX_BUFFER = 256 * 1024 * 1024;
const SEED = 1735689600;
const INT16_REFERENCE_BYTES = 15 * 1024 * 1024;

function argument(name, fallback) {
    const index = process.argv.indexOf(name);
    return index >= 0 && process.argv[index + 1] ? process.argv[index + 1] : fallback;
}

const runtimeRoot = path.resolve(argument('--root', ''));
const lovec = argument('--lovec', process.env.LOVEC || 'lovec');
if (!runtimeRoot || !fs.existsSync(runtimeRoot)) {
    throw new Error('bench-instance-transport requires --root <runnable staged Project>');
}

function mapSnapshot(id) {
    const individual = path.join(runtimeRoot, 'data', 'maps', `${id}.json`);
    if (fs.existsSync(individual)) return JSON.parse(fs.readFileSync(individual, 'utf8'));
    const aggregate = path.join(runtimeRoot, 'data', 'maps.json');
    if (!fs.existsSync(aggregate)) throw new Error(`No staged Map data found for ${id}.`);
    const decoded = JSON.parse(fs.readFileSync(aggregate, 'utf8'));
    const maps = Array.isArray(decoded) ? decoded : decoded.maps;
    const map = (maps || []).find(candidate => String(candidate.id) === String(id));
    if (!map) throw new Error(`No staged Map ${id}.`);
    return map;
}

function envelope(stdout) {
    const match = String(stdout || '').match(/RENDERABLE BEGIN\s*([\s\S]*?)\s*RENDERABLE END/);
    if (!match) throw new Error('LÖVE did not return a complete renderable envelope.');
    return match[1];
}

function runRuntime(id, mode) {
    const requestDir = path.join(runtimeRoot, 'tmp', 'issue-757-benchmark');
    fs.mkdirSync(requestDir, { recursive: true });
    const requestName = `map-${id}-${mode}.json`;
    const requestPath = path.join(requestDir, requestName);
    fs.writeFileSync(requestPath, JSON.stringify({ map: mapSnapshot(id), seed: SEED }));

    const env = { ...process.env };
    env.SECOND_RITE_RENDERABLE_REQUEST = path.relative(runtimeRoot, requestPath).split(path.sep).join('/');
    if (mode === 'instances') env.SECOND_RITE_RENDERABLE_ENCODING = 'instances';
    else delete env.SECOND_RITE_RENDERABLE_ENCODING;

    const started = performance.now();
    const child = spawnSync(lovec, ['.', 'preview-map', String(id)], {
        cwd: runtimeRoot,
        env,
        encoding: 'utf8',
        windowsHide: true,
        maxBuffer: MAX_BUFFER,
        timeout: 120000,
    });
    const runtimeMs = performance.now() - started;
    try { fs.unlinkSync(requestPath); } catch (error) { /* benchmark cleanup only */ }
    if (child.error) throw child.error;
    if (child.status !== 0) {
        throw new Error(`LÖVE ${mode} Map ${id} exited ${child.status}: ${child.stderr || child.stdout}`);
    }
    const jsonText = envelope(child.stdout);
    return { jsonText, runtimeMs };
}

function readAndParse(jsonText, label) {
    const file = path.join(os.tmpdir(), `second-rite-757-${process.pid}-${label}.json`);
    fs.writeFileSync(file, jsonText);
    const readStarted = performance.now();
    const raw = fs.readFileSync(file, 'utf8');
    const readMs = performance.now() - readStarted;
    const parseStarted = performance.now();
    const value = JSON.parse(raw);
    const parseMs = performance.now() - parseStarted;
    fs.unlinkSync(file);
    return { value, readMs, parseMs };
}

function formatValue(value) {
    if (value === undefined) return 'undefined';
    if (typeof value === 'number' || typeof value === 'boolean' || value === null) return String(value);
    if (typeof value === 'string') return JSON.stringify(value.length > 120 ? value.slice(0, 117) + '...' : value);
    return Array.isArray(value) ? `[array length=${value.length}]` : '[object]';
}

// Node's deepStrictEqual tries to build a Myers diff for mismatching arrays.
// These bundles contain millions of numeric attributes, so a mismatch can make
// the diagnostic itself exhaust memory. Walk in public-bundle order and stop at
// the first difference instead. JSON cannot preserve signed zero, so ordinary
// numeric equality is the correct comparison for transported numeric values.
function firstDifference(actual, expected, at = 'bundle') {
    if (actual === expected) return null;
    if (actual === null || expected === null
            || typeof actual !== 'object' || typeof expected !== 'object') {
        return `${at}: ${formatValue(actual)} !== ${formatValue(expected)}`;
    }

    const actualIsArray = Array.isArray(actual);
    const expectedIsArray = Array.isArray(expected);
    if (actualIsArray !== expectedIsArray) {
        return `${at}: ${formatValue(actual)} !== ${formatValue(expected)}`;
    }

    if (actualIsArray) {
        if (actual.length !== expected.length) {
            return `${at}.length: ${actual.length} !== ${expected.length}`;
        }
        for (let index = 0; index < actual.length; index++) {
            const a = actual[index], e = expected[index];
            if (a === e) continue;
            const childPath = `${at}[${index}]`;
            if (a !== null && e !== null && typeof a === 'object' && typeof e === 'object') {
                const nested = firstDifference(a, e, childPath);
                if (nested) return nested;
            } else {
                return `${childPath}: ${formatValue(a)} !== ${formatValue(e)}`;
            }
        }
        return null;
    }

    const actualKeys = Object.keys(actual).sort();
    const expectedKeys = Object.keys(expected).sort();
    if (actualKeys.length !== expectedKeys.length) {
        return `${at}: keys ${JSON.stringify(actualKeys)} !== ${JSON.stringify(expectedKeys)}`;
    }
    for (let index = 0; index < actualKeys.length; index++) {
        if (actualKeys[index] !== expectedKeys[index]) {
            return `${at}: keys ${JSON.stringify(actualKeys)} !== ${JSON.stringify(expectedKeys)}`;
        }
    }
    for (const key of actualKeys) {
        const a = actual[key], e = expected[key];
        if (a === e) continue;
        const nested = firstDifference(a, e, `${at}.${key}`);
        if (nested) return nested;
    }
    return null;
}

function mib(bytes) {
    return (bytes / (1024 * 1024)).toFixed(2);
}

function benchmarkMap(id) {
    const map = mapSnapshot(id);
    const baselineRun = runRuntime(id, 'float');
    const compactRun = runRuntime(id, 'instances');
    const baselineBytes = Buffer.byteLength(baselineRun.jsonText, 'utf8');
    const compactBytes = Buffer.byteLength(compactRun.jsonText, 'utf8');

    const baselineIO = readAndParse(baselineRun.jsonText, `map-${id}-float`);
    const compactIO = readAndParse(compactRun.jsonText, `map-${id}-instances`);
    const compact = compactIO.value;
    const encoding = { ...(compact.encoding || {}) };
    const definitionsBytes = Buffer.byteLength(JSON.stringify(compact.definitions || []), 'utf8');
    const placementsBytes = Buffer.byteLength(JSON.stringify(compact.placements || []), 'utf8');
    const literalBytes = Buffer.byteLength(JSON.stringify(compact.surfaces || []), 'utf8');
    const uniqueVertices = (compact.definitions || []).reduce((sum, definition) =>
        sum + Number(definition.vertexCount || 0), 0);
    const definitionTriangles = (compact.definitions || []).reduce((sum, definition) =>
        sum + Number(definition.triangleCount || 0), 0);

    if (global.gc) global.gc();
    const heapBefore = process.memoryUsage().heapUsed;
    const expandStarted = performance.now();
    adapter.decodeTransport(compact);
    const expandMs = performance.now() - expandStarted;
    const heapAfter = process.memoryUsage().heapUsed;

    // This is a semantic equality assertion over the ordinary public bundle,
    // not a screenshot approximation. Any tuple, ordering, material, source or
    // metadata difference fails the experiment immediately and names its first
    // differing field without allocating a second giant diagnostic structure.
    const difference = firstDifference(compact, baselineIO.value);
    if (difference) {
        throw new Error(
            `Map ${id}: decoded instance transport differs from the authoritative expanded bundle; `
            + `first difference: ${difference}`
        );
    }

    const result = {
        map: id,
        width: map.width,
        height: map.height,
        expandedSurfaces: baselineIO.value.stats && baselineIO.value.stats.surfaceCount,
        expandedVertices: baselineIO.value.stats && baselineIO.value.stats.vertexCount,
        expandedTriangles: baselineIO.value.stats && baselineIO.value.stats.triangleCount,
        definitionCount: encoding.definitionCount,
        placementCount: encoding.placementCount,
        literalSurfaceCount: encoding.literalSurfaceCount,
        uniqueDefinitionVertices: uniqueVertices,
        definitionTriangles,
        baselineBytes,
        compactBytes,
        definitionsBytes,
        placementsBytes,
        literalBytes,
        sizeRatio: compactBytes / baselineBytes,
        versusInt16Ratio: compactBytes / INT16_REFERENCE_BYTES,
        baselineRuntimeMs: baselineRun.runtimeMs,
        compactRuntimeMs: compactRun.runtimeMs,
        encodeMs: encoding.encodeMs,
        baselineReadMs: baselineIO.readMs,
        compactReadMs: compactIO.readMs,
        baselineParseMs: baselineIO.parseMs,
        compactParseMs: compactIO.parseMs,
        boundaryExpandMs: expandMs,
        boundaryHeapDeltaBytes: heapAfter - heapBefore,
        exactEquivalent: true,
    };

    console.log(`ISSUE757 ${JSON.stringify(result)}`);
    console.log(
        `Map ${id}: ${mib(baselineBytes)} MiB -> ${mib(compactBytes)} MiB `
        + `(${(result.sizeRatio * 100).toFixed(1)}%); `
        + `${result.definitionCount} definitions / ${result.placementCount} placements; `
        + `decode ${expandMs.toFixed(1)} ms; exact equivalent.`
    );
    return result;
}

const results = [benchmarkMap(2), benchmarkMap(3)];
console.log('ISSUE757 SUMMARY');
console.log(JSON.stringify(results, null, 2));
