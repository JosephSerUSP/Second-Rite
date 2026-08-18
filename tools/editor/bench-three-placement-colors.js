'use strict';

// #765 follow-up: keep the compact runtime definition/placement transport and
// measure only the unresolved placement-dependent colour gate. This deliberately
// reuses SecondRiteEditorAdapter.applyVertexModulation as the colour authority;
// it does not duplicate lighting or vertex-shading semantics.
const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { performance } = require('node:perf_hooks');
const adapter = require('./js/second-rite-editor-adapter.js');
const projectPlay = require('./project-play');
const authoredStorage = require('./authored-storage');
const direct = require('./three-definition-transport.js');

const SEED = 1735689600;
const MAX_BUFFER = 16 * 1024 * 1024;

function argument(name, fallback) {
    const index = process.argv.indexOf(name);
    return index >= 0 && process.argv[index + 1] ? process.argv[index + 1] : fallback;
}
function round(value) { return Number(value.toFixed(3)); }
function mib(bytes) { return Number((bytes / (1024 * 1024)).toFixed(3)); }
function heap() { if (global.gc) global.gc(); return process.memoryUsage().heapUsed; }

const installRoot = path.resolve(argument('--install-root', path.join(__dirname, '..', '..')));
const projectRoot = path.resolve(argument('--project-root', path.join(installRoot, 'projects', 'hichaukitoden-game')));
const loveExe = path.resolve(argument('--love', process.env.LOVE_PATH || 'C:\\Program Files\\LOVE\\love.exe'));
const lovec = /love\.exe$/i.test(loveExe) ? loveExe.replace(/love\.exe$/i, 'lovec.exe') : loveExe;
if (!fs.existsSync(lovec)) throw new Error(`LÖVE console executable not found: ${lovec}`);

const authoredMaps = authoredStorage.loadOrderedCollection(path.join(projectRoot, 'data'), 'maps').entries;
function mapSnapshot(id) {
    const map = authoredMaps.find(candidate => String(candidate.id) === String(id));
    if (!map) throw new Error(`Map ${id} not found in opened Project.`);
    return map;
}

function runtimeCompact(runtimeRoot, id, map) {
    const requestDir = path.join(runtimeRoot, 'tmp', 'issue-765-colour-benchmark');
    fs.mkdirSync(requestDir, { recursive: true });
    const requestPath = path.join(requestDir, `map-${id}-${process.pid}.json`);
    fs.writeFileSync(requestPath, JSON.stringify({ map, seed: SEED }));
    const env = projectPlay.launchEnvironment({
        SECOND_RITE_RENDERABLE_REQUEST: path.relative(runtimeRoot, requestPath).split(path.sep).join('/'),
        SECOND_RITE_RENDERABLE_ENCODING: 'instances',
    });
    const child = spawnSync(lovec, ['.', 'preview-map', String(id)], {
        cwd: runtimeRoot,
        env,
        encoding: 'utf8',
        windowsHide: true,
        maxBuffer: MAX_BUFFER,
        timeout: 120000,
    });
    try { fs.unlinkSync(requestPath); } catch (_) {}
    if (child.error) throw child.error;
    if (child.status !== 0) throw new Error(`LÖVE Map ${id} failed: ${child.stderr || child.stdout}`);
    const match = String(child.stdout).match(/RENDERABLE BEGIN\s*([\s\S]*?)\s*RENDERABLE END/);
    if (!match) throw new Error(`Map ${id}: no complete renderable envelope.`);
    return match[1];
}

function placementRuntimeSurface(definition, placement) {
    const positions = definition.positions || [];
    const colors = definition.colors || [];
    const vertexCount = positions.length / 3;
    if (!Number.isInteger(vertexCount) || colors.length !== vertexCount * 4) {
        throw new Error(`Definition '${definition.id}' has incompatible position/color streams.`);
    }
    const transform = placement.transform || {};
    const matrix = transform.matrix2d;
    const translation = transform.translation;
    if (!Array.isArray(matrix) || matrix.length !== 4 || !Array.isArray(translation) || translation.length !== 3) {
        throw new Error(`Placement '${placement.id}' has invalid transform.`);
    }
    const world = new Array(positions.length);
    for (let index = 0; index < vertexCount; index++) {
        const p = index * 3;
        const x = Number(positions[p]);
        const y = Number(positions[p + 1]);
        world[p] = Number(translation[0]) + Number(matrix[0]) * x + Number(matrix[1]) * y;
        world[p + 1] = Number(translation[1]) + Number(matrix[2]) * x + Number(matrix[3]) * y;
        world[p + 2] = Number(translation[2]) + Number(positions[p + 2]);
    }
    return {
        id: placement.id,
        name: placement.name,
        source: placement.source,
        material: placement.material,
        positions: world,
        colors: colors.slice(),
    };
}

function placementColorBuffers(compact, map) {
    const definitions = new Map((compact.definitions || []).map(definition => [definition.id, definition]));
    const layers = map.vertexShadingLayers || compact.vertexShadingLayers || [];
    const buffers = new Map();
    let bytes = 0;
    const started = performance.now();
    for (const placement of compact.placements || []) {
        const definition = definitions.get(placement.definition);
        if (!definition) throw new Error(`Unknown definition '${placement.definition}'.`);
        const surface = placementRuntimeSurface(definition, placement);
        // Existing Studio modulation remains the sole semantic authority. It is
        // applied to indexed definition vertices in world coordinates rather
        // than to the expanded triangle stream.
        adapter.applyVertexModulation({
            surfaces: [surface],
            light: compact.light,
            vertexShadingLayers: compact.vertexShadingLayers || [],
        }, layers);
        const vertexCount = surface.positions.length / 3;
        const rgb = new Float32Array(vertexCount * 3);
        for (let src = 0, dst = 0; src < surface.colors.length; src += 4, dst += 3) {
            rgb[dst] = Number(surface.colors[src]);
            rgb[dst + 1] = Number(surface.colors[src + 1]);
            rgb[dst + 2] = Number(surface.colors[src + 2]);
        }
        buffers.set(placement.id, rgb);
        bytes += rgb.byteLength;
    }
    return { buffers, bytes, ms: performance.now() - started };
}

function compareAgainstExpanded(jsonText, map, compact, placementColors) {
    const expanded = JSON.parse(jsonText);
    adapter.decodeTransport(expanded);
    adapter.applyVertexModulation(expanded, map.vertexShadingLayers || expanded.vertexShadingLayers || []);
    const definitions = new Map((compact.definitions || []).map(definition => [definition.id, definition]));
    let compared = 0;
    let maxAbsError = 0;
    let mismatchCount = 0;
    for (const placement of compact.placements || []) {
        const definition = definitions.get(placement.definition);
        const indices = definition.indices || [];
        const expected = expanded.surfaces[Number(placement.order) - 1];
        const rgb = placementColors.buffers.get(placement.id);
        if (!expected || !rgb) throw new Error(`Placement '${placement.id}' has no expanded/control surface.`);
        for (let triangleVertex = 0; triangleVertex < indices.length; triangleVertex++) {
            const sourceIndex = Number(indices[triangleVertex]);
            const expectedColor = triangleVertex * 4;
            const directColor = sourceIndex * 3;
            for (let channel = 0; channel < 3; channel++) {
                const a = Number(expected.colors[expectedColor + channel]);
                const b = Number(rgb[directColor + channel]);
                const error = Math.abs(a - b);
                if (error > maxAbsError) maxAbsError = error;
                if (error > 1e-6) mismatchCount++;
                compared++;
            }
        }
    }
    return { compared, mismatchCount, maxAbsError };
}

function spatialBytesWithoutDefinitionColors(compact) {
    let bytes = 0;
    for (const definition of compact.definitions || []) {
        const vertexCount = (definition.positions || []).length / 3;
        const IndexBytes = vertexCount > 65535 ? 4 : 2;
        bytes += (definition.positions || []).length * 4;
        bytes += (definition.normals || []).length * 4;
        bytes += (definition.uvs || []).length * 4;
        bytes += (definition.indices || []).length * IndexBytes;
    }
    return bytes;
}

function literalAttributeBytes(compact) {
    let bytes = 0;
    for (const surface of compact.surfaces || []) {
        const vertexCount = (surface.positions || []).length / 3;
        bytes += (surface.positions || []).length * 4;
        bytes += (surface.normals || []).length * 4;
        bytes += (surface.uvs || []).length * 4;
        // Production direct literals remain ordinary expanded RGB attributes.
        bytes += vertexCount * 3 * 4;
    }
    return bytes;
}

function runMap(runtimeRoot, id) {
    const map = mapSnapshot(id);
    const jsonText = runtimeCompact(runtimeRoot, id, map);
    const compact = JSON.parse(jsonText);
    if (!compact.encoding || compact.encoding.kind !== direct.INSTANCE_TRANSPORT_KIND) {
        throw new Error(`Map ${id}: expected ${direct.INSTANCE_TRANSPORT_KIND}.`);
    }

    const before = heap();
    const placementColors = placementColorBuffers(compact, map);
    const after = process.memoryUsage().heapUsed;
    const parity = compareAgainstExpanded(jsonText, map, compact, placementColors);
    const spatialBytes = spatialBytesWithoutDefinitionColors(compact);
    const literalBytes = literalAttributeBytes(compact);
    const exactDirectBytes = spatialBytes + literalBytes + placementColors.bytes;

    const result = {
        map: id,
        definitions: compact.definitions.length,
        placements: compact.placements.length,
        literals: compact.surfaces.length,
        placementColorBuildMs: round(placementColors.ms),
        placementColorBufferMiB: mib(placementColors.bytes),
        placementColorHeapDeltaMiB: mib(after - before),
        sharedSpatialAttributeMiB: mib(spatialBytes),
        literalAttributeMiB: mib(literalBytes),
        exactDirectAttributeMiB: mib(exactDirectBytes),
        parity,
        falsifierPassed: parity.mismatchCount === 0 && parity.maxAbsError <= 1e-6,
    };
    console.log(`ISSUE765 COLOR ${JSON.stringify(result)}`);
    return result;
}

let stageDir = null;
try {
    stageDir = projectPlay.stageProject({ installRoot, projectRoot });
    const results = [runMap(stageDir, 2), runMap(stageDir, 3)];
    if (results.some(result => !result.falsifierPassed)) {
        throw new Error('Placement-owned colour buffers did not exactly match current expanded Studio modulation.');
    }
    console.log('ISSUE765 COLOR SUMMARY');
    console.log(JSON.stringify(results, null, 2));
} finally {
    projectPlay.cleanupLaunch(stageDir, null);
}
