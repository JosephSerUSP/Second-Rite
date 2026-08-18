
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { performance } = require('node:perf_hooks');
const THREE = require('three');
const adapter = require('./js/second-rite-editor-adapter.js');
const Contract = require('./js/thestra-viewport-contract.js');
const Direct = require('./js/three-definition-consumer.js');
const projectPlay = require('./project-play');
const authoredStorage = require('./authored-storage');

const SEED = 1735689600;
const MAX_BUFFER = 16 * 1024 * 1024;
function argument(name, fallback) {
    const index = process.argv.indexOf(name);
    return index >= 0 && process.argv[index + 1] ? process.argv[index + 1] : fallback;
}
function round(value) { return Number(value.toFixed(3)); }
function mib(bytes) { return Number((bytes / (1024 * 1024)).toFixed(3)); }
function heap() { if (global.gc) global.gc(); return process.memoryUsage().heapUsed; }
function close(a, b, epsilon = 1e-6) { return Math.abs(Number(a) - Number(b)) <= epsilon; }

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
    const requestDir = path.join(runtimeRoot, 'tmp', 'issue-765-final-benchmark');
    fs.mkdirSync(requestDir, { recursive: true });
    const requestPath = path.join(requestDir, `map-${id}-${process.pid}.json`);
    fs.writeFileSync(requestPath, JSON.stringify({ map, seed: SEED }));
    const env = projectPlay.launchEnvironment({
        SECOND_RITE_RENDERABLE_REQUEST: path.relative(runtimeRoot, requestPath).split(path.sep).join('/'),
        SECOND_RITE_RENDERABLE_ENCODING: 'instances',
    });
    const child = spawnSync(lovec, ['.', 'preview-map', String(id)], {
        cwd: runtimeRoot, env, encoding: 'utf8', windowsHide: true,
        maxBuffer: MAX_BUFFER, timeout: 120000,
    });
    try { fs.unlinkSync(requestPath); } catch (_) {}
    if (child.error) throw child.error;
    if (child.status !== 0) throw new Error(`LÖVE Map ${id} failed: ${child.stderr || child.stdout}`);
    const match = String(child.stdout).match(/RENDERABLE BEGIN\s*([\s\S]*?)\s*RENDERABLE END/);
    if (!match) throw new Error(`Map ${id}: no complete renderable envelope.`);
    return match[1];
}

function expandedLiteralGeometry(surface, coordinateSystem) {
    const source = surface && surface.positions || [];
    if (!Array.isArray(source) || source.length < 9 || source.length % 9 !== 0) return null;
    const positions = new Float32Array(Contract.transformTriangleStream(
        source, 3, value => Contract.runtimePositionToThestra(value, coordinateSystem)
    ));
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    const normals = surface.normals || [];
    if (normals.length === positions.length) {
        geometry.setAttribute('normal', new THREE.BufferAttribute(new Float32Array(
            Contract.transformTriangleStream(normals, 3, Contract.runtimeNormalToThestra)
        ), 3));
    } else geometry.computeVertexNormals();
    const uvs = surface.uvs || [];
    if (uvs.length === positions.length / 3 * 2) {
        geometry.setAttribute('uv', new THREE.BufferAttribute(new Float32Array(
            Contract.transformTriangleStream(uvs, 2)
        ), 2));
    }
    const rgba = surface.colors || [];
    const reordered = Contract.transformTriangleStream(rgba, 4);
    const rgb = new Float32Array(positions.length);
    for (let src = 0, dst = 0; src < reordered.length; src += 4, dst += 3) {
        rgb[dst] = reordered[src]; rgb[dst + 1] = reordered[src + 1]; rgb[dst + 2] = reordered[src + 2];
    }
    geometry.setAttribute('color', new THREE.BufferAttribute(rgb, 3));
    geometry.computeBoundingBox(); geometry.computeBoundingSphere();
    return geometry;
}

function buildProductionDirect(bundle) {
    const scene = new THREE.Scene();
    const material = new THREE.MeshBasicMaterial({ vertexColors: true, side: THREE.DoubleSide });
    const definitions = new Map();
    const spatialGeometries = [];
    for (const definition of bundle.definitions) {
        const geometry = Direct.definitionGeometry(THREE, definition);
        definitions.set(definition.id, geometry);
        spatialGeometries.push(geometry);
    }
    const placementMeshes = [];
    const literalMeshes = [];
    for (const entry of Direct.orderedRenderables(bundle)) {
        if (entry.kind === 'literal') {
            const surface = entry.value;
            const geometry = expandedLiteralGeometry(surface, bundle.coordinateSystem || {});
            if (!geometry) continue;
            const mesh = new THREE.Mesh(geometry, material);
            mesh.userData.thestraSource = surface.source || null;
            mesh.userData.thestraMaterialId = surface.material || null;
            mesh.userData.thestraTransportOrder = surface.transportOrder;
            scene.add(mesh); literalMeshes.push(mesh);
            continue;
        }
        const placement = entry.value;
        const geometry = Direct.placementGeometry(
            THREE, definitions.get(placement.definition), adapter.directPlacementColorState(placement)
        );
        const mesh = new THREE.Mesh(geometry, material);
        mesh.matrixAutoUpdate = false;
        mesh.matrix.copy(Direct.placementMatrix(THREE, placement, bundle.coordinateSystem || {}));
        mesh.userData.thestraSource = placement.source || null;
        mesh.userData.thestraMaterialId = placement.material || null;
        mesh.userData.thestraTransportOrder = placement.order;
        geometry.userData.thestraPlacementMatrix = mesh.matrix;
        scene.add(mesh); placementMeshes.push(mesh);
    }
    scene.updateMatrixWorld(true);
    return { scene, material, spatialGeometries, placementMeshes, literalMeshes };
}

function placementStateBytes(bundle) {
    let bytes = 0;
    for (const placement of bundle.placements) {
        const state = adapter.directPlacementColorState(placement);
        bytes += state.unlit.byteLength + state.authoritative.byteLength;
    }
    return bytes;
}
function placementAttributeBytes(built) {
    return built.placementMeshes.reduce((sum, mesh) => sum + mesh.geometry.getAttribute('color').array.byteLength, 0);
}
function literalAttributeBytes(built) {
    return Direct.uniqueAttributeBytes(built.literalMeshes.map(mesh => mesh.geometry));
}

function parityAgainstExpanded(jsonText, map, directBundle) {
    const expanded = JSON.parse(jsonText);
    adapter.decodeTransport(expanded);
    adapter.applyVertexModulation(expanded, map.vertexShadingLayers || expanded.vertexShadingLayers || []);
    const definitions = new Map(directBundle.definitions.map(definition => [definition.id, definition]));
    let tuples = 0, colorComponents = 0, mismatchCount = 0, maxAbsError = 0;
    for (const placement of directBundle.placements) {
        const definition = definitions.get(placement.definition);
        const expected = expanded.surfaces[Number(placement.order) - 1];
        const state = adapter.directPlacementColorState(placement);
        if (!expected || !definition || !state) throw new Error(`Missing parity data for ${placement.id}`);
        if (expected.material !== placement.material || JSON.stringify(expected.source) !== JSON.stringify(placement.source)) {
            throw new Error(`Provenance/material mismatch for ${placement.id}`);
        }
        const matrix = placement.transform.matrix2d, translation = placement.transform.translation;
        for (let out = 0; out < definition.indices.length; out++) {
            const sourceIndex = Number(definition.indices[out]);
            const p = sourceIndex * 3, uv = sourceIndex * 2, c = sourceIndex * 4;
            const ep = out * 3, euv = out * 2, ec = out * 4;
            const x = Number(definition.positions[p]), y = Number(definition.positions[p + 1]);
            const expectedValues = [
                Number(translation[0]) + Number(matrix[0]) * x + Number(matrix[1]) * y,
                Number(translation[1]) + Number(matrix[2]) * x + Number(matrix[3]) * y,
                Number(translation[2]) + Number(definition.positions[p + 2]),
                Number(definition.uvs[uv]), Number(definition.uvs[uv + 1])
            ];
            const controlValues = [
                expected.positions[ep], expected.positions[ep + 1], expected.positions[ep + 2],
                expected.uvs[euv], expected.uvs[euv + 1]
            ];
            for (let i = 0; i < expectedValues.length; i++) {
                if (!close(expectedValues[i], controlValues[i])) mismatchCount++;
                maxAbsError = Math.max(maxAbsError, Math.abs(expectedValues[i] - controlValues[i]));
            }
            for (let channel = 0; channel < 3; channel++) {
                const error = Math.abs(Number(expected.colors[ec + channel]) - Number(state.authoritative[sourceIndex * 3 + channel]));
                if (error > 1e-6) mismatchCount++;
                maxAbsError = Math.max(maxAbsError, error);
                colorComponents++;
            }
            tuples++;
        }
    }
    return { tuples, colorComponents, mismatchCount, maxAbsError };
}

function liveLightingProof(bundle, built) {
    if (!Array.isArray(bundle.light)) return { updateMs: 0, compared: 0, mismatchCount: 0, maxAbsError: 0, noLeak: true };
    const started = performance.now();
    let compared = 0, mismatchCount = 0, maxAbsError = 0;
    for (const mesh of built.placementMeshes) {
        Direct.updatePlacementLighting(THREE, mesh.geometry, mesh.matrix, bundle.light);
        const current = mesh.geometry.getAttribute('color').array;
        const baseline = mesh.geometry.userData.thestraAuthoritativeColors;
        for (let index = 0; index < current.length; index++) {
            const error = Math.abs(Number(current[index]) - Number(baseline[index]));
            if (error > 1e-6) mismatchCount++;
            maxAbsError = Math.max(maxAbsError, error); compared++;
        }
    }
    const updateMs = performance.now() - started;

    let noLeak = true;
    const byDefinition = new Map();
    for (let index = 0; index < bundle.placements.length; index++) {
        const placement = bundle.placements[index];
        const list = byDefinition.get(placement.definition) || [];
        list.push(built.placementMeshes[index]);
        byDefinition.set(placement.definition, list);
    }
    const peers = [...byDefinition.values()].find(list => list.length >= 2);
    if (peers) {
        const before = peers[1].geometry.getAttribute('color').array.slice();
        const zero = bundle.light.map(row => row.map(() => [0, 0, 0]));
        Direct.updatePlacementLighting(THREE, peers[0].geometry, peers[0].matrix, zero);
        const after = peers[1].geometry.getAttribute('color').array;
        noLeak = before.length === after.length && before.every((value, index) => value === after[index]);
    }
    return { updateMs: round(updateMs), compared, mismatchCount, maxAbsError, noLeak };
}

function pickProof(built) {
    for (const mesh of built.placementMeshes.concat(built.literalMeshes)) {
        if (!mesh.userData.thestraSource) continue;
        const hit = Direct.raycastFirstTriangle(THREE, mesh);
        if (hit) return {
            hit: true,
            source: mesh.userData.thestraSource,
            material: mesh.userData.thestraMaterialId,
            order: mesh.userData.thestraTransportOrder,
            distance: round(hit.distance)
        };
    }
    return { hit: false };
}

function runMap(runtimeRoot, id) {
    const map = mapSnapshot(id);
    const jsonText = runtimeCompact(runtimeRoot, id, map);
    const bundle = JSON.parse(jsonText);
    const literalCount = bundle.surfaces.length;
    const before = heap();
    const prepStarted = performance.now();
    adapter.applyRenderableModulation(bundle, map.vertexShadingLayers || bundle.vertexShadingLayers || []);
    const prepMs = performance.now() - prepStarted;
    const ready = heap();
    if (!Direct.isDirectBundle(bundle) || bundle.surfaces.length !== literalCount
            || bundle.placements.some(placement => Object.prototype.hasOwnProperty.call(placement, 'positions'))) {
        throw new Error('Compatibility expansion was reintroduced into the direct path.');
    }

    const sceneStarted = performance.now();
    const built = buildProductionDirect(bundle);
    const sceneMs = performance.now() - sceneStarted;
    const afterScene = heap();
    const parity = parityAgainstExpanded(jsonText, map, bundle);
    const live = liveLightingProof(bundle, built);
    const sharedSpatialBytes = Direct.uniqueAttributeBytes(built.spatialGeometries);
    const colorStateBytes = placementStateBytes(bundle);
    const colorAttributeBytes = placementAttributeBytes(built);
    const literalBytes = literalAttributeBytes(built);
    const result = {
        map: id,
        compactMiB: mib(Buffer.byteLength(jsonText, 'utf8')),
        definitions: bundle.definitions.length,
        placements: bundle.placements.length,
        literals: bundle.surfaces.length,
        prepMs: round(prepMs),
        consumerReadyHeapDeltaMiB: mib(ready - before),
        sceneCreationMs: round(sceneMs),
        sceneHeapDeltaMiB: mib(afterScene - ready),
        totalHeapDeltaMiB: mib(afterScene - before),
        sharedSpatialMiB: mib(sharedSpatialBytes),
        placementColorStateMiB: mib(colorStateBytes),
        placementColorAttributeMiB: mib(colorAttributeBytes),
        placementOwnedColorTotalMiB: mib(colorStateBytes + colorAttributeBytes),
        literalAttributeMiB: mib(literalBytes),
        totalUniqueAttributeMiB: mib(sharedSpatialBytes + colorAttributeBytes + literalBytes),
        objectCount: built.placementMeshes.length + built.literalMeshes.length,
        geometryViewCount: built.placementMeshes.length,
        spatialDefinitionGeometryCount: built.spatialGeometries.length,
        parity,
        live,
        pick: pickProof(built),
        noCompatibilityExpansion: true,
        productionReady: parity.mismatchCount === 0 && parity.maxAbsError <= 1e-6
            && live.mismatchCount === 0 && live.maxAbsError <= 1e-6 && live.noLeak
    };
    console.log(`ISSUE765 FINAL ${JSON.stringify(result)}`);
    if (!result.productionReady || !result.pick.hit) throw new Error(`Map ${id}: final direct proof failed.`);
    return result;
}

let stageDir = null;
try {
    stageDir = projectPlay.stageProject({ installRoot, projectRoot });
    const results = [runMap(stageDir, 2), runMap(stageDir, 3)];
    console.log('ISSUE765 FINAL SUMMARY');
    console.log(JSON.stringify(results, null, 2));
} finally {
    projectPlay.cleanupLaunch(stageDir, null);
}
