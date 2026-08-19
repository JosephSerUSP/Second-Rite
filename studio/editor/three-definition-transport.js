'use strict';

// #765 experiment helper. This module consumes ONLY the explicit runtime-authored
// mesh-definition + placement schema from #761. It does not infer geometry
// identity or compile authored map/tileset rules.
const THREE = require('three');
const Contract = require('./js/thestra-viewport-contract.js');
const Core = require('./js/three-definition-consumer.js');

const INSTANCE_TRANSPORT_KIND = 'mesh-definitions-v1';

function checkedStream(definition, key, width) {
    const stream = definition && definition[key];
    if (!Array.isArray(stream) || stream.length % width !== 0) {
        throw new Error(`Renderable definition '${definition && definition.id}' has invalid ${key}.`);
    }
    return stream;
}

function semanticFromSource(source) {
    if (!source || typeof source !== 'object') return null;
    if (source.kind === 'cell' && Number.isFinite(Number(source.x)) && Number.isFinite(Number(source.y))) {
        const x = Number(source.x), y = Number(source.y);
        return { kind: 'cell', key: `cell:${x}:${y}`, cell: { x, y }, role: source.surface || null };
    }
    if (source.kind === 'event' && source.id != null) {
        return { kind: 'event', key: `event:${source.id}`, id: source.id };
    }
    return null;
}

function definitionGeometry(definition) {
    return Core.definitionGeometry(THREE, definition);
}

function placementMatrix(placement, coordinateSystem) {
    return Core.placementMatrix(THREE, placement, coordinateSystem);
}

function expandedLiteralGeometry(surface, coordinateSystem) {
    const sourcePositions = surface && surface.positions || [];
    if (!Array.isArray(sourcePositions) || sourcePositions.length < 9 || sourcePositions.length % 9 !== 0) return null;
    const transformed = Contract.transformTriangleStream(
        sourcePositions, 3, value => Contract.runtimePositionToThestra(value, coordinateSystem)
    );
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.BufferAttribute(new Float32Array(transformed), 3));
    const uvs = surface.uvs || [];
    if (uvs.length === (transformed.length / 3) * 2) {
        geometry.setAttribute('uv', new THREE.BufferAttribute(new Float32Array(Contract.transformTriangleStream(uvs, 2)), 2));
    }
    const normals = surface.normals || [];
    if (normals.length === transformed.length) {
        geometry.setAttribute('normal', new THREE.BufferAttribute(new Float32Array(
            Contract.transformTriangleStream(normals, 3, Contract.runtimeNormalToThestra)
        ), 3));
    } else {
        geometry.computeVertexNormals();
    }
    const rgba = surface.colors || [];
    if (rgba.length === (transformed.length / 3) * 4) {
        const reordered = Contract.transformTriangleStream(rgba, 4);
        const rgb = new Float32Array((reordered.length / 4) * 3);
        for (let src = 0, dst = 0; src < reordered.length; src += 4, dst += 3) {
            rgb[dst] = reordered[src]; rgb[dst + 1] = reordered[src + 1]; rgb[dst + 2] = reordered[src + 2];
        }
        geometry.setAttribute('color', new THREE.BufferAttribute(rgb, 3));
    }
    geometry.computeBoundingBox();
    geometry.computeBoundingSphere();
    return geometry;
}

function geometryAttributeBytes(geometry) {
    let bytes = 0;
    for (const attribute of Object.values(geometry.attributes || {})) {
        if (attribute && attribute.array) bytes += attribute.array.byteLength || 0;
    }
    if (geometry.index && geometry.index.array) bytes += geometry.index.array.byteLength || 0;
    return bytes;
}

function buildDirectScene(bundle) {
    if (!bundle || !bundle.encoding || bundle.encoding.kind !== INSTANCE_TRANSPORT_KIND) {
        throw new Error(`Direct Three experiment requires ${INSTANCE_TRANSPORT_KIND}.`);
    }
    if (!Array.isArray(bundle.definitions) || !Array.isArray(bundle.placements) || !Array.isArray(bundle.surfaces)) {
        throw new Error('Direct Three experiment requires definitions, placements and literal surfaces.');
    }

    const scene = new THREE.Scene();
    const material = new THREE.MeshBasicMaterial({ vertexColors: true, side: THREE.DoubleSide });
    const definitions = new Map();
    const geometries = [];
    for (const definition of bundle.definitions) {
        if (!definition || typeof definition.id !== 'string' || definitions.has(definition.id)) {
            throw new Error('Direct Three experiment found an invalid or duplicate definition id.');
        }
        const geometry = definitionGeometry(definition);
        definitions.set(definition.id, geometry);
        geometries.push(geometry);
    }

    const placementMeshes = [];
    for (const placement of bundle.placements) {
        const geometry = definitions.get(placement && placement.definition);
        if (!geometry) throw new Error(`Placement '${placement && placement.id}' references unknown definition.`);
        const mesh = new THREE.Mesh(geometry, material);
        mesh.name = placement.name || placement.id || 'runtime-placement';
        mesh.matrixAutoUpdate = false;
        mesh.matrix.copy(placementMatrix(placement, bundle.coordinateSystem || {}));
        mesh.matrixWorld.copy(mesh.matrix);
        mesh.userData.thestraSource = placement.source || null;
        mesh.userData.thestraSelection = semanticFromSource(placement.source);
        mesh.userData.thestraMaterialId = placement.material || null;
        mesh.userData.thestraTransportOrder = placement.order;
        scene.add(mesh);
        placementMeshes.push(mesh);
    }

    const literalMeshes = [];
    for (const surface of bundle.surfaces) {
        const geometry = expandedLiteralGeometry(surface, bundle.coordinateSystem || {});
        if (!geometry) continue;
        geometries.push(geometry);
        const mesh = new THREE.Mesh(geometry, material);
        mesh.name = surface.name || surface.id || 'runtime-literal-surface';
        mesh.userData.thestraSource = surface.source || null;
        mesh.userData.thestraSelection = semanticFromSource(surface.source);
        mesh.userData.thestraMaterialId = surface.material || null;
        mesh.userData.thestraTransportOrder = surface.transportOrder;
        scene.add(mesh);
        literalMeshes.push(mesh);
    }
    scene.updateMatrixWorld(true);

    return {
        scene,
        definitions,
        placementMeshes,
        literalMeshes,
        geometries,
        geometryBytes: geometries.reduce((sum, geometry) => sum + geometryAttributeBytes(geometry), 0),
        material,
    };
}

function raycastFirstTriangle(mesh) {
    const geometry = mesh && mesh.geometry;
    const positions = geometry && geometry.getAttribute('position');
    if (!positions || positions.count < 3) return null;
    const index = geometry.index;
    const ia = index ? index.getX(0) : 0;
    const ib = index ? index.getX(1) : 1;
    const ic = index ? index.getX(2) : 2;
    const a = new THREE.Vector3().fromBufferAttribute(positions, ia).applyMatrix4(mesh.matrixWorld);
    const b = new THREE.Vector3().fromBufferAttribute(positions, ib).applyMatrix4(mesh.matrixWorld);
    const c = new THREE.Vector3().fromBufferAttribute(positions, ic).applyMatrix4(mesh.matrixWorld);
    const center = a.clone().add(b).add(c).multiplyScalar(1 / 3);
    const normal = b.clone().sub(a).cross(c.clone().sub(a)).normalize();
    if (!Number.isFinite(normal.x) || normal.lengthSq() < 1e-10) return null;
    const raycaster = new THREE.Raycaster(center.clone().addScaledVector(normal, 0.1), normal.clone().negate(), 0, 1);
    const hits = raycaster.intersectObject(mesh, false);
    return hits[0] || null;
}

module.exports = {
    INSTANCE_TRANSPORT_KIND,
    semanticFromSource,
    definitionGeometry,
    placementMatrix,
    geometryAttributeBytes,
    buildDirectScene,
    raycastFirstTriangle,
};
