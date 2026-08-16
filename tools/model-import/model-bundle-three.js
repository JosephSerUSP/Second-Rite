'use strict';

const THREE = require('three');
const contract = require('./model-contract');

function geometryForGroup(group) {
    const positions = [];
    const uvs = [];
    const normals = [];
    const colors = [];
    for (const row of group.vertices) {
        positions.push(row[0], row[1], row[2]);
        uvs.push(row[3], row[4]);
        normals.push(row[5], row[6], row[7]);
        colors.push(row[8], row[9], row[10], row[11]);
    }
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
    geometry.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2));
    geometry.setAttribute('normal', new THREE.Float32BufferAttribute(normals, 3));
    geometry.setAttribute('color', new THREE.Float32BufferAttribute(colors, 4));
    geometry.userData.materialSlot = group.materialSlot;
    return geometry;
}

function toThreeGeometryGroups(bundle) {
    contract.validateBundle(bundle);
    return bundle.geometry.groups.map(group => ({
        materialSlot: group.materialSlot,
        geometry: geometryForGroup(group),
    }));
}

module.exports = {
    geometryForGroup,
    toThreeGeometryGroups,
};
