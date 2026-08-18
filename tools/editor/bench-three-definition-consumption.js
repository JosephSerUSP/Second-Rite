'use strict';

// #765 direct-definition experiment. Run with --expose-gc on Windows with a
// LÖVE 11.5 console executable. The benchmark keeps runtime authority intact:
// LÖVE emits #761's exact mesh-definition transport; this script compares the
// current compatibility expansion against building shared Three geometry from
// those runtime-authored definitions.
const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { performance } = require('node:perf_hooks');
const THREE = require('three');
const adapter = require('./js/second-rite-editor-adapter.js');
const Contract = require('./js/thestra-viewport-contract.js');
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
    const requestDir = path.join(runtimeRoot, 'tmp', 'issue-765-benchmark');
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
    try { fs.unlinkSync(requestPath); } catch (error) { /* cleanup only */ }
    if (child.error) throw child.error;
    if (child.status !== 0) throw new Error(`LÖVE Map ${id} failed: ${child.stderr || child.stdout}`);
    const match = String(child.stdout).match(/RENDERABLE BEGIN\s*([\s\S]*?)\s*RENDERABLE END/);
    if (!match) throw new Error(`Map ${id}: no complete renderable envelope.`);
    return match[1];
}

function rgbFromRgbaTriangleStream(values, vertexCount) {
    if (!Array.isArray(values) || values.length !== vertexCount * 4) return null;
    const transformed = Contract.transformTriangleStream(values, 4);
    const colors = new Float32Array(vertexCount * 3);
    for (let src = 0, dst = 0; src + 3 < transformed.length; src += 4, dst += 3) {
        colors[dst] = transformed[src]; colors[dst + 1] = transformed[src + 1]; colors[dst + 2] = transformed[src + 2];
    }
    return colors;
}

function expandedGeometry(surface, coordinateSystem) {
    const sourcePositions = surface.positions || [];
    const positions = new Float32Array(Contract.transformTriangleStream(
        sourcePositions, 3, value => Contract.runtimePositionToThestra(value, coordinateSystem)
    ));
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    const sourceUvs = surface.uvs || [];
    if (sourceUvs.length === (positions.length / 3) * 2) {
        geometry.setAttribute('uv', new THREE.BufferAttribute(new Float32Array(Contract.transformTriangleStream(sourceUvs, 2)), 2));
    }
    const sourceNormals = surface.normals || [];
    if (sourceNormals.length === positions.length) {
        geometry.setAttribute('normal', new THREE.BufferAttribute(new Float32Array(
            Contract.transformTriangleStream(sourceNormals, 3, Contract.runtimeNormalToThestra)
        ), 3));
    } else geometry.computeVertexNormals();
    const vertexCount = positions.length / 3;
    const colors = rgbFromRgbaTriangleStream(surface.colors || [], vertexCount)
        || new Float32Array(positions.length).fill(1);
    geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    geometry.computeBoundingBox(); geometry.computeBoundingSphere();
    return geometry;
}

function semanticFromSource(source) { return direct.semanticFromSource(source); }

function buildExpandedScene(bundle) {
    const scene = new THREE.Scene();
    const material = new THREE.MeshBasicMaterial({ vertexColors: true, side: THREE.DoubleSide });
    const geometries = [];
    const meshes = [];
    for (const surface of bundle.surfaces || []) {
        if (!surface || !Array.isArray(surface.positions) || surface.positions.length < 9) continue;
        const geometry = expandedGeometry(surface, bundle.coordinateSystem || {});
        const mesh = new THREE.Mesh(geometry, material);
        mesh.userData.thestraSelection = semanticFromSource(surface.source);
        mesh.userData.thestraSource = surface.source || null;
        mesh.userData.thestraMaterialId = surface.material || null;
        scene.add(mesh); geometries.push(geometry); meshes.push(mesh);
    }
    scene.updateMatrixWorld(true);
    return {
        scene, material, geometries, meshes,
        geometryBytes: geometries.reduce((sum, geometry) => sum + direct.geometryAttributeBytes(geometry), 0),
    };
}

function disposeBuilt(built) {
    const unique = new Set(built && built.geometries || []);
    for (const geometry of unique) geometry.dispose();
    if (built && built.material) built.material.dispose();
    if (built && built.scene) built.scene.clear();
}

function pickProof(meshes) {
    for (const mesh of meshes || []) {
        if (!mesh.userData.thestraSelection) continue;
        const hit = direct.raycastFirstTriangle(mesh);
        if (!hit) continue;
        return {
            hit: true,
            name: mesh.name || null,
            semantic: mesh.userData.thestraSelection,
            source: mesh.userData.thestraSource || null,
            material: mesh.userData.thestraMaterialId || null,
            distance: round(hit.distance),
        };
    }
    return { hit: false };
}

function benchmarkCurrent(jsonText, map) {
    const before = heap();
    const parseStarted = performance.now();
    const bundle = JSON.parse(jsonText);
    const parseMs = performance.now() - parseStarted;
    const adapterStarted = performance.now();
    adapter.decodeTransport(bundle);
    adapter.applyVertexModulation(bundle, map.vertexShadingLayers || bundle.vertexShadingLayers || []);
    const adapterMs = performance.now() - adapterStarted;
    const readyHeap = process.memoryUsage().heapUsed;
    const sceneStarted = performance.now();
    const built = buildExpandedScene(bundle);
    const sceneMs = performance.now() - sceneStarted;
    const sceneHeap = process.memoryUsage().heapUsed;
    const pick = pickProof(built.meshes);
    const result = {
        parseMs: round(parseMs), adapterMs: round(adapterMs),
        consumerReadyHeapDeltaMiB: mib(readyHeap - before),
        sceneCreationMs: round(sceneMs),
        sceneHeapDeltaMiB: mib(sceneHeap - readyHeap),
        totalHeapDeltaMiB: mib(sceneHeap - before),
        geometryCount: built.geometries.length,
        geometryAttributeMiB: mib(built.geometryBytes),
        objectCount: built.meshes.length,
        pick,
    };
    disposeBuilt(built);
    return result;
}

function validateDirectVisualConstraint(bundle) {
    const hasResolvedLight = Array.isArray(bundle.light);
    const hasVertexShading = Array.isArray(bundle.vertexShadingLayers) && bundle.vertexShadingLayers.length > 0;
    return {
        exactSharedGeometryVisualReady: !hasResolvedLight && !hasVertexShading,
        hasResolvedLight,
        hasVertexShading,
        note: hasResolvedLight || hasVertexShading
            ? 'Current Studio modulation is placement/world-position dependent; direct scene intentionally measures representation/picking without claiming final color parity.'
            : 'No placement-dependent Studio modulation present in this bundle.'
    };
}

function benchmarkDirect(jsonText) {
    const before = heap();
    const parseStarted = performance.now();
    const bundle = JSON.parse(jsonText);
    const parseMs = performance.now() - parseStarted;
    const adapterStarted = performance.now();
    if (!bundle.encoding || bundle.encoding.kind !== direct.INSTANCE_TRANSPORT_KIND) {
        throw new Error('Direct benchmark expected mesh-definitions-v1 transport.');
    }
    // Consumer-ready means schema is preserved, not expanded. `buildDirectScene`
    // performs strict definition/placement validation while constructing Three.
    const adapterMs = performance.now() - adapterStarted;
    const readyHeap = process.memoryUsage().heapUsed;
    const sceneStarted = performance.now();
    const built = direct.buildDirectScene(bundle);
    const sceneMs = performance.now() - sceneStarted;
    const sceneHeap = process.memoryUsage().heapUsed;
    const pick = pickProof(built.placementMeshes.concat(built.literalMeshes));
    const uniquePlacementGeometries = new Set(built.placementMeshes.map(mesh => mesh.geometry));
    if (uniquePlacementGeometries.size !== bundle.definitions.length) {
        throw new Error(`Direct scene created ${uniquePlacementGeometries.size} placement geometries for ${bundle.definitions.length} definitions.`);
    }
    const result = {
        parseMs: round(parseMs), adapterMs: round(adapterMs),
        consumerReadyHeapDeltaMiB: mib(readyHeap - before),
        sceneCreationMs: round(sceneMs),
        sceneHeapDeltaMiB: mib(sceneHeap - readyHeap),
        totalHeapDeltaMiB: mib(sceneHeap - before),
        definitionCount: bundle.definitions.length,
        placementCount: bundle.placements.length,
        literalSurfaceCount: bundle.surfaces.length,
        placementGeometryCount: uniquePlacementGeometries.size,
        totalGeometryCount: built.geometries.length,
        geometryAttributeMiB: mib(built.geometryBytes),
        objectCount: built.placementMeshes.length + built.literalMeshes.length,
        pick,
        visualConstraint: validateDirectVisualConstraint(bundle),
    };
    disposeBuilt(built);
    return result;
}

function runMap(runtimeRoot, id) {
    const map = mapSnapshot(id);
    const jsonText = runtimeCompact(runtimeRoot, id, map);
    const compactMiB = mib(Buffer.byteLength(jsonText, 'utf8'));
    const current = benchmarkCurrent(jsonText, map);
    const directResult = benchmarkDirect(jsonText);
    const result = {
        map: id,
        compactMiB,
        current,
        direct: directResult,
        deletedConsumerReadyHeapMiB: round(current.consumerReadyHeapDeltaMiB - directResult.consumerReadyHeapDeltaMiB),
        deletedTotalHeapMiB: round(current.totalHeapDeltaMiB - directResult.totalHeapDeltaMiB),
        geometryAttributeReductionMiB: round(current.geometryAttributeMiB - directResult.geometryAttributeMiB),
    };
    console.log(`ISSUE765 ${JSON.stringify(result)}`);
    return result;
}

let stageDir = null;
try {
    stageDir = projectPlay.stageProject({ installRoot, projectRoot });
    const results = [runMap(stageDir, 2), runMap(stageDir, 3)];
    console.log('ISSUE765 SUMMARY');
    console.log(JSON.stringify(results, null, 2));
} finally {
    projectPlay.cleanupLaunch(stageDir, null);
}
