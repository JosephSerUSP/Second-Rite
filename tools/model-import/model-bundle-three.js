(function(root, factory) {
    if (typeof module === 'object' && module.exports) module.exports = factory(require('three'), require('./model-bundle-contract'));
    else root.ThestraModelBundleThree = factory(null, root.ThestraModelBundleContract);
})(typeof globalThis !== 'undefined' ? globalThis : this, function(defaultThree, contract) {
'use strict';

function geometryForGroup(group, THREE = defaultThree) {
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

function toThreeGeometryGroups(bundle, THREE = defaultThree) {
    contract.validateBundle(bundle);
    return bundle.geometry.groups.map(group => ({
        materialSlot: group.materialSlot,
        geometry: geometryForGroup(group, THREE),
    }));
}

function toThreeObject(bundle, THREE = defaultThree) {
    contract.validateBundle(bundle);
    const object = new THREE.Group();
    const slots = new Map(bundle.materialSlots.map(slot => [slot.id, slot]));
    for (const group of bundle.geometry.groups) {
        const slot = slots.get(group.materialSlot);
        if (!slot.appearance) throw new Error(`Model '${bundle.modelId}' slot '${slot.id}' has no compiled appearance binding`);
        if (slot.appearance.passes?.length) throw new Error(`Model '${bundle.modelId}' overlay preview requires native runtime rendering`);
    }
    for (const entry of toThreeGeometryGroups(bundle, THREE)) {
        const slot = slots.get(entry.materialSlot);
        const appearance = slot.appearance;
        const material = new THREE.MeshPhongMaterial({ vertexColors: true, side: THREE.DoubleSide });
        material.name = slot.id;
        material.color.setRGB(...appearance.color.slice(0, 3));
        material.opacity = appearance.color[3];
        material.transparent = material.opacity < 1;
        if (appearance.texture) {
            material.map = new THREE.TextureLoader().load('/' + appearance.texture);
            material.map.flipY = false;
            material.map.magFilter = THREE.NearestFilter;
            material.map.minFilter = THREE.NearestFilter;
        }
        object.add(new THREE.Mesh(entry.geometry, material));
    }
    object.userData.modelId = bundle.modelId;
    object.userData.materialSlots = bundle.materialSlots;
    return object;
}

return {
    geometryForGroup,
    toThreeGeometryGroups,
    toThreeObject,
};

});
