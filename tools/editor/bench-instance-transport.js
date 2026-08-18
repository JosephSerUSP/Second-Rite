'use strict';

// Reproducible #757 experiment harness. Run from the repository checkout after
// staging a runnable Project, for example:
//   node tools/editor/bench-instance-transport.js --root <stage> --lovec <lovec.exe>
//
// It deliberately gives the child a 256 MiB stdout allowance: Map 3 exceeds the
// production bridge's 64 MiB ceiling in the baseline format, and that overflow
// is one of the things this representation experiment is meant to measure.
const assert = require('node:assert/strict');
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
    // metadata difference fails the experiment immediately.
    assert.deepStrictEqual(compact, baselineIO.value,
        `Map ${id}: decoded instance transport differs from the authoritative expanded bundle`);

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
