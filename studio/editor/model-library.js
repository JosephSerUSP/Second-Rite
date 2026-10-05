'use strict';

const fs = require('node:fs');
const path = require('node:path');
const storage = require('./authored-storage');
const contract = require('../../tools/model-import/model-contract');
const importer = require('../../tools/model-import/import-model');

function conflict(message) {
    const error = new Error(message);
    error.code = 'STALE_MODEL_REVIEW';
    return error;
}

function createModelLibrary(projectRoot, runtimeRoot) {
    const dataRoot = path.join(projectRoot, 'data');
    function read() {
        const exists = fs.existsSync(path.join(dataRoot, 'models.json'));
        const records = exists ? storage.loadRegistry(dataRoot, 'models').records : {};
        // Invalid existing recipes must not disappear from a read or be
        // silently repaired merely because an author opens the library.
        return { records, version: exists ? storage.versionToken(dataRoot, 'models') : 'absent' };
    }

    function checkTarget(recipe, originalId, loaded) {
        if (originalId !== undefined && originalId !== null) {
            if (!loaded.records[originalId]) throw conflict('Selected Model was removed. Reload the library.');
            if (recipe.id !== originalId) throw new Error('Reimport cannot rename Model identity.');
        } else if (Object.hasOwn(loaded.records, recipe.id)) {
            throw conflict('Model identity already exists. Select that Model to reimport it.');
        }
        for (const [id, other] of Object.entries(loaded.records)) {
            if (id !== recipe.id && recipe.appearance && other.appearance
                    && other.source?.path === recipe.source.path) {
                throw new Error(`Source is already bound to Model '${id}'. Reimport that Model instead.`);
            }
        }
    }

    async function prepare({ id, source }) {
        if (!contract.ID_PATTERN.test(id || '')) throw new Error('Model identity is required and must use letters, numbers, dots, slashes, underscores or hyphens.');
        const info = await importer.inspectSource({ projectRoot, source, runtimeRoot });
        const slots = {};
        const used = new Set();
        let defaultSlot;
        for (const name of info.materials) {
            const stem = name.replace(/[^A-Za-z0-9._-]+/g, '_').replace(/^[^A-Za-z0-9]+/, '') || 'unassigned';
            let slot = stem;
            if (used.has(slot)) slot += '_' + contract.sha256(name).slice(0, 8);
            used.add(slot);
            slots[slot] = { sourceMaterials: name ? [name] : [] };
            if (!name) defaultSlot = slot;
        }
        const recipe = contract.validateRecipe(id, {
            id, source, sourceUnitsToMapCells: 1, materialSlots: slots,
            ...(defaultSlot ? { defaultMaterialSlot: defaultSlot } : {}),
            ...(info.mtllib && !defaultSlot ? { appearance: 'obj-mtl' } : {}),
        });
        checkTarget(recipe, null, read());
        return { recipe, sourceMaterials: info.materials };
    }

    async function preview({ recipe: proposed, originalId, version }) {
        const loaded = read();
        if (version !== loaded.version) throw conflict('Model registry changed. Reload the library before reviewing.');
        const recipe = contract.validateRecipe(proposed.id, proposed);
        checkTarget(recipe, originalId, loaded);
        const bundle = await importer.importRecipe({ projectRoot, recipe, runtimeRoot });
        const token = contract.sha256(contract.serialize(bundle));
        const info = await importer.inspectSource({ projectRoot, source: recipe.source, runtimeRoot });
        const unusedMappings = Object.entries(recipe.materialSlots).flatMap(([slot, value]) =>
            value.sourceMaterials.filter(name => !info.materials.includes(name)).map(name => ({ slot, sourceMaterial: name })));
        return { recipe, bundle, token, version: loaded.version, sourceMaterials: info.materials, unusedMappings,
            renderable: bundle.materialSlots.every(slot => !!slot.appearance),
            summary: { vertices: bundle.geometry.vertexCount, triangles: bundle.geometry.vertexCount / 3,
                bounds: bundle.geometry.bounds, sourceSha256: bundle.source.sha256 } };
    }

    async function save(request) {
        if (typeof request.token !== 'string') throw conflict('Preview this Model before saving.');
        const reviewed = await preview(request);
        if (request.token !== reviewed.token) throw conflict('Model source, material dependencies or recipe changed after preview. Preview again before saving.');
        // Compilation is asynchronous. Recheck the entire registry immediately
        // before the synchronous authored-storage transaction, including creates.
        if (read().version !== request.version) throw conflict('Model registry changed while compiling. Reload the library.');
        const existing = read().records[reviewed.recipe.id];
        const inputs = [{ path: reviewed.bundle.source.path, sha256: reviewed.bundle.source.sha256 },
            ...(reviewed.bundle.provenance.dependencies || [])];
        for (const input of inputs) {
            const current = fs.readFileSync(path.join(projectRoot, input.path));
            if (contract.sha256(current) !== input.sha256) throw conflict('Model inputs changed while compiling. Preview again.');
        }
        const record = Object.assign({}, existing || {}, reviewed.recipe);
        // Appearance/default-slot are optional semantics, not legacy dual reads.
        if (!reviewed.recipe.appearance) delete record.appearance;
        if (!reviewed.recipe.defaultMaterialSlot) delete record.defaultMaterialSlot;
        if (request.version === 'absent') storage.writeResource(dataRoot, 'models', { [record.id]: record });
        else storage.writeRegistryRecord(dataRoot, 'models', record, request.version);
        return { ...read(), id: record.id, token: reviewed.token };
    }

    return { read, prepare, preview, save };
}

module.exports = { createModelLibrary };
