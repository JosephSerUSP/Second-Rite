'use strict';

const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');

const BUNDLE_KIND = 'thestra-model-bundle';
const BUNDLE_VERSION = 1;
const COMPILER_ID = 'thestra-model-import';
const COMPILER_VERSION = 1;
const SOURCE_KINDS = new Set(['obj', 'gltf']);
const ID_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._/-]*$/;
const SLOT_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._-]*$/;

function sha256(value) {
    return crypto.createHash('sha256').update(value).digest('hex');
}

function portable(value) {
    return String(value || '').replace(/\\/g, '/');
}

function requireRelativePath(value, label) {
    if (typeof value !== 'string' || !value || path.isAbsolute(value)) {
        throw new Error(`${label} must be a non-empty Project-relative path`);
    }
    const portableValue = portable(value);
    if (portableValue.startsWith('/') || portableValue.split('/').includes('..')) {
        throw new Error(`${label} must not escape the Project root`);
    }
    return portableValue;
}

function finitePositive(value, label) {
    const number = Number(value);
    if (!Number.isFinite(number) || number <= 0) {
        throw new Error(`${label} must be a finite positive number`);
    }
    return number;
}

function stableJson(value) {
    if (Array.isArray(value)) return value.map(stableJson);
    if (!value || typeof value !== 'object') return value;
    const out = {};
    for (const key of Object.keys(value).sort()) out[key] = stableJson(value[key]);
    return out;
}

function serialize(value) {
    return JSON.stringify(stableJson(value), null, 2) + '\n';
}

function validateRecipe(id, recipe) {
    if (typeof id !== 'string' || !ID_PATTERN.test(id)) {
        throw new Error(`Model id '${id}' must match ${ID_PATTERN}`);
    }
    if (!recipe || typeof recipe !== 'object' || Array.isArray(recipe)) {
        throw new Error(`Model '${id}' recipe must be an object`);
    }
    if (recipe.id !== id) throw new Error(`Model registry key '${id}' disagrees with recipe id '${recipe.id}'`);
    if (!recipe.source || typeof recipe.source !== 'object' || Array.isArray(recipe.source)) {
        throw new Error(`Model '${id}' requires source`);
    }
    if (!SOURCE_KINDS.has(recipe.source.kind)) {
        throw new Error(`Model '${id}' source.kind must be obj or gltf`);
    }
    const sourcePath = requireRelativePath(recipe.source.path, `Model '${id}' source.path`);
    const lower = sourcePath.toLowerCase();
    if (recipe.source.kind === 'obj' && !lower.endsWith('.obj')) {
        throw new Error(`Model '${id}' OBJ source must end in .obj`);
    }
    if (recipe.source.kind === 'gltf' && !(lower.endsWith('.glb') || lower.endsWith('.gltf'))) {
        throw new Error(`Model '${id}' glTF source must end in .glb or .gltf`);
    }
    const sourceUnitsToMapCells = finitePositive(recipe.sourceUnitsToMapCells, `Model '${id}' sourceUnitsToMapCells`);

    const slots = recipe.materialSlots;
    if (!slots || typeof slots !== 'object' || Array.isArray(slots) || Object.keys(slots).length === 0) {
        throw new Error(`Model '${id}' requires at least one materialSlot`);
    }
    const seenSourceMaterials = new Map();
    const normalizedSlots = {};
    for (const slotId of Object.keys(slots).sort()) {
        if (!SLOT_PATTERN.test(slotId)) throw new Error(`Model '${id}' materialSlot '${slotId}' has invalid id`);
        const slot = slots[slotId];
        if (!slot || typeof slot !== 'object' || Array.isArray(slot)) {
            throw new Error(`Model '${id}' materialSlot '${slotId}' must be an object`);
        }
        if (!Array.isArray(slot.sourceMaterials)) {
            throw new Error(`Model '${id}' materialSlot '${slotId}' requires sourceMaterials[]`);
        }
        const names = [];
        for (const raw of slot.sourceMaterials) {
            if (typeof raw !== 'string' || !raw) {
                throw new Error(`Model '${id}' materialSlot '${slotId}' sourceMaterials must be non-empty strings`);
            }
            if (seenSourceMaterials.has(raw)) {
                throw new Error(`Model '${id}' source material '${raw}' maps to both '${seenSourceMaterials.get(raw)}' and '${slotId}'`);
            }
            seenSourceMaterials.set(raw, slotId);
            names.push(raw);
        }
        const normalized = { sourceMaterials: [...names].sort() };
        if (slot.surface !== undefined) {
            if (typeof slot.surface !== 'string' || !slot.surface) {
                throw new Error(`Model '${id}' materialSlot '${slotId}' surface must be a non-empty string when authored`);
            }
            normalized.surface = slot.surface;
        }
        normalizedSlots[slotId] = normalized;
    }
    if (recipe.defaultMaterialSlot !== undefined) {
        if (typeof recipe.defaultMaterialSlot !== 'string' || !normalizedSlots[recipe.defaultMaterialSlot]) {
            throw new Error(`Model '${id}' defaultMaterialSlot must name an authored materialSlot`);
        }
    }

    return {
        id,
        source: { kind: recipe.source.kind, path: sourcePath },
        sourceUnitsToMapCells,
        materialSlots: normalizedSlots,
        ...(recipe.defaultMaterialSlot === undefined ? {} : { defaultMaterialSlot: recipe.defaultMaterialSlot }),
    };
}

function loadRegistry(projectRoot, registryPath = 'data/models.json') {
    const filePath = path.join(projectRoot, registryPath);
    const value = JSON.parse(fs.readFileSync(filePath, 'utf8'));
    if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('models.json must be an object registry');
    const out = {};
    for (const id of Object.keys(value).sort()) out[id] = validateRecipe(id, value[id]);
    return { registryPath: portable(registryPath), models: out };
}

function sourceMaterialMap(recipe) {
    const map = new Map();
    for (const [slotId, slot] of Object.entries(recipe.materialSlots)) {
        for (const name of slot.sourceMaterials) map.set(name, slotId);
    }
    return map;
}

function materialSlotFor(recipe, sourceMaterial) {
    const mapped = sourceMaterialMap(recipe).get(sourceMaterial || '');
    if (mapped) return mapped;
    if ((!sourceMaterial || sourceMaterial === '') && recipe.defaultMaterialSlot) return recipe.defaultMaterialSlot;
    throw new Error(`Model '${recipe.id}' source material '${sourceMaterial || '(none)'}' has no materialSlot mapping`);
}

function materialSlotFacts(recipe) {
    return Object.keys(recipe.materialSlots).sort().map(id => ({
        id,
        ...(recipe.materialSlots[id].surface ? { surface: recipe.materialSlots[id].surface } : {}),
    }));
}

function makeBundle({ recipe, sourceSha256, geometry, diagnostics = [] }) {
    const recipeCanonical = validateRecipe(recipe.id, recipe);
    return {
        kind: BUNDLE_KIND,
        version: BUNDLE_VERSION,
        modelId: recipeCanonical.id,
        compiler: { id: COMPILER_ID, version: COMPILER_VERSION },
        source: {
            kind: recipeCanonical.source.kind,
            path: recipeCanonical.source.path,
            sha256: sourceSha256,
        },
        normalization: {
            up: 'z',
            unit: 'mapCell',
            sourceUnitsToMapCells: recipeCanonical.sourceUnitsToMapCells,
        },
        geometry,
        materialSlots: materialSlotFacts(recipeCanonical),
        provenance: {
            recipeSha256: sha256(Buffer.from(serialize(recipeCanonical), 'utf8')),
        },
        diagnostics,
    };
}

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
    const slots = new Set((bundle.materialSlots || []).map(slot => slot && slot.id));
    for (const group of bundle.geometry.groups) {
        if (!slots.has(group.materialSlot)) throw new Error(`Model Bundle group refers to undeclared materialSlot '${group.materialSlot}'`);
    }
    return bundle;
}

module.exports = {
    BUNDLE_KIND,
    BUNDLE_VERSION,
    COMPILER_ID,
    COMPILER_VERSION,
    ID_PATTERN,
    SLOT_PATTERN,
    loadRegistry,
    makeBundle,
    materialSlotFor,
    serialize,
    sha256,
    validateBundle,
    validateRecipe,
};
