'use strict';

const fs = require('node:fs');
const path = require('node:path');
const contract = require('./model-contract');
const geometry = require('./static-geometry');
const { compileAppearance } = require('./compile-appearance');

function projectFile(projectRoot, relative, label) {
    const root = path.resolve(projectRoot);
    const absolute = path.resolve(root, relative);
    const rel = path.relative(root, absolute);
    if (!rel || rel === '.' || rel.startsWith(`..${path.sep}`) || path.isAbsolute(rel)) {
        throw new Error(`${label} escaped Project root: ${relative}`);
    }
    if (!fs.existsSync(absolute) || !fs.statSync(absolute).isFile()) {
        throw new Error(`${label} is missing: ${relative}`);
    }
    return absolute;
}

function accessorElement(accessor, index, fallback) {
    if (!accessor) return fallback.slice();
    return accessor.getElement(index, []);
}

function sourceMaterialNames(root) {
    const counts = new Map();
    for (const material of root.listMaterials()) {
        const name = material.getName() || '';
        counts.set(name, (counts.get(name) || 0) + 1);
    }
    for (const [name, count] of counts) {
        if (count > 1) {
            throw new Error(`glTF source material name '${name || '(unnamed)'}' is not unique; stable material-slot mapping would be ambiguous`);
        }
    }
}

function selectedScene(root) {
    const preferred = root.getDefaultScene();
    if (preferred) return preferred;
    const scenes = root.listScenes();
    if (scenes.length === 1) return scenes[0];
    if (scenes.length === 0) throw new Error('glTF static Model requires a scene');
    throw new Error('glTF static Model has multiple scenes but no default scene');
}

function gltfDiagnostics(root) {
    const diagnostics = [];
    for (const material of root.listMaterials()) {
        diagnostics.push({
            code: 'GLTF_SOURCE_MATERIAL_APPEARANCE_NOT_IMPORTED',
            severity: 'info',
            sourceMaterial: material.getName() || '',
            detail: {
                baseColorFactor: Array.from(material.getBaseColorFactor()),
                emissiveFactor: Array.from(material.getEmissiveFactor()),
                metallicFactor: material.getMetallicFactor(),
                roughnessFactor: material.getRoughnessFactor(),
            },
        });
    }
    return diagnostics;
}

async function normalizeGltf({ filePath, recipe, projectRoot }) {
    const { NodeIO, Primitive } = require('@gltf-transform/core');
    const io = new NodeIO();
    const jsonDocument = await io.readAsJSON(filePath);
    const document = await io.readJSON(jsonDocument);
    const dependencies = Object.entries(jsonDocument.resources)
        .filter(([uri]) => !uri.startsWith('@') && !uri.startsWith('data:'))
        .map(([uri, bytes]) => {
            const relative = path.posix.normalize(path.posix.join(path.posix.dirname(recipe.source.path), decodeURIComponent(uri)));
            projectFile(projectRoot, relative, 'glTF dependency');
            return { path: relative, sha256: contract.sha256(bytes) };
        }).sort((a,b) => a.path.localeCompare(b.path));
    const root = document.getRoot();
    if (root.listAnimations().length > 0) {
        throw new Error(`Model '${recipe.id}' static importer does not accept animation; animated Model compilation is a separate contract`);
    }
    sourceMaterialNames(root);
    const scene = selectedScene(root);
    const output = geometry.collector();

    function visit(node) {
        if (node.getSkin()) throw new Error(`Model '${recipe.id}' static importer found a skin on node '${node.getName() || '(unnamed)'}'`);
        const mesh = node.getMesh();
        if (!mesh) return;
        const worldMatrix = node.getWorldMatrix();
        const determinant = geometry.determinant3(worldMatrix);
        if (!Number.isFinite(determinant) || Math.abs(determinant) <= geometry.EPSILON) {
            throw new Error(`Model '${recipe.id}' node '${node.getName() || '(unnamed)'}' has non-invertible transform`);
        }
        if (determinant < 0) {
            throw new Error(`Model '${recipe.id}' node '${node.getName() || '(unnamed)'}' has mirrored transform; static bake policy is not ratified`);
        }

        mesh.listPrimitives().forEach((primitive, primitiveIndex) => {
            if (primitive.getMode() !== Primitive.Mode.TRIANGLES) {
                throw new Error(`Model '${recipe.id}' mesh '${mesh.getName() || '(unnamed)'}' primitive ${primitiveIndex} is not TRIANGLES`);
            }
            if (primitive.listTargets().length > 0) {
                throw new Error(`Model '${recipe.id}' mesh '${mesh.getName() || '(unnamed)'}' primitive ${primitiveIndex} has morph targets`);
            }
            const position = primitive.getAttribute('POSITION');
            if (!position) throw new Error(`Model '${recipe.id}' primitive ${primitiveIndex} has no POSITION`);
            const normal = primitive.getAttribute('NORMAL');
            const uv = primitive.getAttribute('TEXCOORD_0');
            const color = primitive.getAttribute('COLOR_0');
            const indices = primitive.getIndices();
            const count = indices ? indices.getCount() : position.getCount();
            if (count % 3 !== 0) throw new Error(`Model '${recipe.id}' primitive ${primitiveIndex} triangle count is malformed`);
            const sourceMaterial = primitive.getMaterial() ? (primitive.getMaterial().getName() || '') : '';
            const slot = contract.materialSlotFor(recipe, sourceMaterial);

            for (let offset = 0; offset < count; offset += 3) {
                const corners = [];
                for (let corner = 0; corner < 3; corner += 1) {
                    const index = indices
                        ? accessorElement(indices, offset + corner, [0])[0]
                        : offset + corner;
                    if (!Number.isInteger(index) || index < 0 || index >= position.getCount()) {
                        throw new Error(`Model '${recipe.id}' primitive ${primitiveIndex} contains invalid index ${index}`);
                    }
                    const sourcePosition = accessorElement(position, index, [0, 0, 0]);
                    const worldPosition = geometry.transformPosition(worldMatrix, sourcePosition);
                    const targetPosition = geometry.sourceVectorToWorld(worldPosition, recipe.sourceUnitsToMapCells);
                    let targetNormal = null;
                    if (normal) {
                        const worldNormal = geometry.transformNormal(worldMatrix, accessorElement(normal, index, [0, 1, 0]));
                        targetNormal = geometry.normalize3(geometry.sourceVectorToWorld(worldNormal), 'Thestra normal');
                    }
                    corners.push({
                        position: targetPosition,
                        normal: targetNormal,
                        uv: accessorElement(uv, index, [0, 0]),
                        color: accessorElement(color, index, [1, 1, 1, 1]),
                    });
                }
                output.appendTriangle(slot, corners);
            }
        });
    }

    for (const rootNode of scene.listChildren()) rootNode.traverse(visit);
    return { geometry: output.finish(), diagnostics: gltfDiagnostics(root), dependencies };
}

async function normalizeObj({ filePath, recipe, runtimeRoot = path.resolve(__dirname, '../../runtime') }) {
    const text = fs.readFileSync(filePath, 'utf8');
    const parsed = require('./lua-source-host').parseObj(runtimeRoot, text);
    const scale = recipe.sourceUnitsToMapCells;
    const bounds = Object.fromEntries(Object.entries(parsed.bounds).map(([key, value]) => [key, value * scale]));
    const groups = parsed.groups.map(group => ({
        materialSlot: contract.materialSlotFor(recipe, group.material),
        vertices: group.vertices.map(row => [row[0] * scale, row[1] * scale, row[2] * scale, ...row.slice(3)]),
    }));
    const diagnostics = parsed.mtllib ? [{
        code: 'OBJ_MTL_APPEARANCE_NOT_IMPORTED', severity: 'info',
        detail: 'OBJ material names become stable Model materialSlots; unbound slots require explicit appearance realization.',
    }] : [];
    return { geometry: { groups, vertexCount: parsed.vertexCount, bounds }, diagnostics };
}

async function importRecipe({ projectRoot, recipe, runtimeRoot }) {
    const validated = contract.validateRecipe(recipe.id, recipe);
    const filePath = projectFile(projectRoot, validated.source.path, `Model '${validated.id}' source`);
    const bytes = fs.readFileSync(filePath);
    const normalized = validated.source.kind === 'obj'
        ? await normalizeObj({ filePath, recipe: validated, runtimeRoot })
        : await normalizeGltf({ filePath, recipe: validated, projectRoot });
    const appearance = validated.appearance
        ? compileAppearance(projectRoot, validated, bytes.toString('utf8'), runtimeRoot) : {};
    if (validated.appearance) normalized.diagnostics = normalized.diagnostics.filter(d => d.code !== 'OBJ_MTL_APPEARANCE_NOT_IMPORTED');
    const bundle = contract.makeBundle({
        recipe: validated,
        sourceSha256: contract.sha256(bytes),
        geometry: normalized.geometry,
        diagnostics: normalized.diagnostics,
        ...appearance,
        ...(normalized.dependencies?.length ? { dependencies: normalized.dependencies } : {}),
    });
    return contract.validateBundle(bundle);
}

async function importModel({ projectRoot, modelId, registryPath = 'data/models.json' }) {
    const registry = contract.loadRegistry(projectRoot, registryPath);
    const recipe = registry.models[modelId];
    if (!recipe) throw new Error(`Unknown Model '${modelId}' in ${registry.registryPath}`);
    return importRecipe({ projectRoot, recipe });
}

// Authoring discovery uses the importer's actual source grammar. It does not
// bind or migrate an existing recipe; reimport retains its authored slots.
async function inspectSource({ projectRoot, source, runtimeRoot = path.resolve(__dirname, '../../runtime') }) {
    const filePath = projectFile(projectRoot, contract.requireRelativePath(source.path, 'Model source'), 'Model source');
    if (source.kind === 'obj') {
        const parsed = require('./lua-source-host').parseObj(runtimeRoot, fs.readFileSync(filePath, 'utf8'));
        return { materials: [...new Set(parsed.groups.map(group => group.material || ''))].sort(), mtllib: parsed.mtllib || null };
    }
    if (source.kind !== 'gltf') throw new Error('Model source.kind must be obj or gltf');
    const { NodeIO } = require('@gltf-transform/core');
    const document = await new NodeIO().read(filePath);
    const root = document.getRoot();
    sourceMaterialNames(root);
    const names = new Set();
    for (const node of selectedScene(root).listChildren()) node.traverse(child => {
        const mesh = child.getMesh();
        if (mesh) for (const primitive of mesh.listPrimitives()) names.add(primitive.getMaterial()?.getName() || '');
    });
    return { materials: [...names].sort(), mtllib: null };
}

module.exports = {
    inspectSource,
    importModel,
    importRecipe,
    normalizeGltf,
    normalizeObj,
};
