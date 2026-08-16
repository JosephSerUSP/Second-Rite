'use strict';

const BUNDLE_KIND = 'thestra-static-model-spike';
const BUNDLE_VERSION = 0;

function finiteNumber(value, label) {
    if (typeof value !== 'number' || !Number.isFinite(value)) {
        throw new Error(`${label} must be a finite number`);
    }
    return value;
}

function validateBundle(bundle) {
    if (!bundle || typeof bundle !== 'object') throw new Error('static bundle must be an object');
    if (bundle.kind !== BUNDLE_KIND || bundle.version !== BUNDLE_VERSION) {
        throw new Error(`unsupported static bundle contract: ${String(bundle.kind)} v${String(bundle.version)}`);
    }
    const model = bundle.model;
    if (!model || !Array.isArray(model.groups) || model.groups.length === 0) {
        throw new Error('static bundle model requires material groups');
    }

    let vertexCount = 0;
    model.groups.forEach((group, groupIndex) => {
        if (!group || typeof group.material !== 'string' || !Array.isArray(group.vertices)) {
            throw new Error(`static bundle group ${groupIndex} is malformed`);
        }
        group.vertices.forEach((vertex, vertexIndex) => {
            if (!Array.isArray(vertex) || vertex.length !== 12) {
                throw new Error(`static bundle group ${groupIndex} vertex ${vertexIndex} must have 12 floats`);
            }
            vertex.forEach((value, component) => finiteNumber(
                value,
                `static bundle group ${groupIndex} vertex ${vertexIndex} component ${component}`
            ));
            vertexCount += 1;
        });
    });
    if (model.vertexCount !== vertexCount) {
        throw new Error(`static bundle vertexCount ${model.vertexCount} disagrees with ${vertexCount} rows`);
    }
    for (const key of ['minX', 'minY', 'minZ', 'maxX', 'maxY', 'maxZ']) {
        finiteNumber(model.bounds && model.bounds[key], `static bundle bounds.${key}`);
    }
    return bundle;
}

function createThreeGeometryGroups(bundle, THREE) {
    validateBundle(bundle);
    if (!THREE || typeof THREE.BufferGeometry !== 'function' || typeof THREE.Float32BufferAttribute !== 'function') {
        throw new Error('Three geometry adapter requires BufferGeometry and Float32BufferAttribute');
    }

    return bundle.model.groups.map(group => {
        const positions = [];
        const uvs = [];
        const normals = [];
        const colors = [];
        for (const vertex of group.vertices) {
            positions.push(vertex[0], vertex[1], vertex[2]);
            uvs.push(vertex[3], vertex[4]);
            normals.push(vertex[5], vertex[6], vertex[7]);
            colors.push(vertex[8], vertex[9], vertex[10], vertex[11]);
        }

        const geometry = new THREE.BufferGeometry();
        geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
        geometry.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2));
        geometry.setAttribute('normal', new THREE.Float32BufferAttribute(normals, 3));
        geometry.setAttribute('color', new THREE.Float32BufferAttribute(colors, 4));
        geometry.userData.thestraMaterial = group.material;
        geometry.computeBoundingBox();
        geometry.computeBoundingSphere();
        return { material: group.material, geometry };
    });
}

module.exports = {
    BUNDLE_KIND,
    BUNDLE_VERSION,
    createThreeGeometryGroups,
    validateBundle,
};
