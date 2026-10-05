(function(root, factory) {
    const api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    else root.ThestraModelBundleContract = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function() {
'use strict';
const BUNDLE_KIND = 'thestra-model-bundle';
const BUNDLE_VERSION = 1;
const ID_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._/-]*$/;
const SLOT_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._-]*$/;
function validateBundle(bundle) {
    if (!bundle || typeof bundle !== 'object' || Array.isArray(bundle)) throw new Error('Model Bundle must be an object');
    if (bundle.kind !== BUNDLE_KIND || bundle.version !== BUNDLE_VERSION) throw new Error('unsupported Model Bundle contract');
    if (typeof bundle.modelId !== 'string' || !ID_PATTERN.test(bundle.modelId)) throw new Error('Model Bundle has invalid modelId');
    if (!bundle.geometry || !Array.isArray(bundle.geometry.groups) || bundle.geometry.groups.length === 0) {
        throw new Error('Model Bundle geometry requires groups');
    }
    let vertexCount = 0;
    for (const [groupIndex, group] of bundle.geometry.groups.entries()) {
        if (!group || typeof group.materialSlot !== 'string' || !SLOT_PATTERN.test(group.materialSlot)) {
            throw new Error(`Model Bundle group ${groupIndex} has invalid materialSlot`);
        }
        if (!Array.isArray(group.vertices) || group.vertices.length === 0) throw new Error(`Model Bundle group ${groupIndex} requires vertices`);
        for (const [vertexIndex, vertex] of group.vertices.entries()) {
            if (!Array.isArray(vertex) || vertex.length !== 12 || vertex.some(value => !Number.isFinite(value))) {
                throw new Error(`Model Bundle group ${groupIndex} vertex ${vertexIndex} must contain 12 finite numbers`);
            }
            vertexCount += 1;
        }
    }
    if (bundle.geometry.vertexCount !== vertexCount) throw new Error('Model Bundle vertexCount disagrees with vertex rows');
    const bounds = bundle.geometry.bounds;
    for (const key of ['minX', 'minY', 'minZ', 'maxX', 'maxY', 'maxZ']) {
        if (!bounds || !Number.isFinite(bounds[key])) throw new Error(`Model Bundle bounds.${key} must be finite`);
    }
    const slots = new Set();
    for (const slot of bundle.materialSlots || []) {
        if (!slot || !SLOT_PATTERN.test(slot.id) || slots.has(slot.id)) throw new Error('Model Bundle has invalid or duplicate material slot');
        slots.add(slot.id);
        if (slot.appearance) {
            const appearance = slot.appearance;
            if (!Array.isArray(appearance.color) || appearance.color.length !== 4 || appearance.color.some(n => !Number.isFinite(n))) throw new Error('Model appearance requires finite RGBA');
            for (const texture of [appearance.texture, ...(appearance.passes || []).map(p => p.texture)].filter(Boolean)) {
                if (typeof texture !== 'string' || !texture.startsWith('assets/') || texture.split('/').includes('..') || texture.includes('\\')) throw new Error('Model texture must be Project-relative');
            }
        }
    }
    for (const group of bundle.geometry.groups) {
        if (!slots.has(group.materialSlot)) throw new Error(`Model Bundle group refers to undeclared materialSlot '${group.materialSlot}'`);
    }
    return bundle;
}

return { validateBundle };
});
