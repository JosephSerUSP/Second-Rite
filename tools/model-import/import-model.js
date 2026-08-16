'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { NodeIO, Primitive } = require('@gltf-transform/core');
const contract = require('./model-contract');
const geometry = require('./static-geometry');

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

async function normalizeGltf({ filePath, recipe }) {
    const io = new NodeIO();
    const document = await io.read(filePath);
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
    return { geometry: output.finish(), diagnostics: gltfDiagnostics(root) };
}

function materialAt(mesh, geometryValue, triangleOffset) {
    const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
    let materialIndex = 0;
    if (Array.isArray(geometryValue.groups) && geometryValue.groups.length > 0) {
        const group = geometryValue.groups.find(candidate => triangleOffset >= candidate.start
            && triangleOffset < candidate.start + candidate.count);
        if (group) materialIndex = group.materialIndex || 0;
    }
    const material = materials[materialIndex];
    return material && typeof material.name === 'string' ? material.name : '';
}

async function normalizeObj({ filePath, recipe }) {
    const [{ OBJLoader }] = await Promise.all([
        import('three/examples/jsm/loaders/OBJLoader.js'),
    ]);
    const text = fs.readFileSync(filePath, 'utf8');
    const object = new OBJLoader().parse(text);
    object.updateMatrixWorld(true);
    const output = geometry.collector();

    object.traverse(mesh => {
        if (!mesh || !mesh.isMesh || !mesh.geometry) return;
        const source = mesh.geometry;
        const position = source.getAttribute('position');
        if (!position) return;
        const normal = source.getAttribute('normal');
        const uv = source.getAttribute('uv');
        const color = source.getAttribute('color');
        const index = source.getIndex();
        const count = index ? index.count : position.count;
        if (count % 3 !== 0) throw new Error(`Model '${recipe.id}' OBJ mesh '${mesh.name || '(unnamed)'}' is not triangulated`);
        const worldMatrix = mesh.matrixWorld.elements;
        const determinant = geometry.determinant3(worldMatrix);
        if (!Number.isFinite(determinant) || Math.abs(determinant) <= geometry.EPSILON) {
            throw new Error(`Model '${recipe.id}' OBJ mesh '${mesh.name || '(unnamed)'}' has non-invertible transform`);
        }
        if (determinant < 0) throw new Error(`Model '${recipe.id}' OBJ mesh '${mesh.name || '(unnamed)'}' has mirrored transform`);

        for (let offset = 0; offset < count; offset += 3) {
            const sourceMaterial = materialAt(mesh, source, offset);
            const slot = contract.materialSlotFor(recipe, sourceMaterial);
            const corners = [];
            for (let corner = 0; corner < 3; corner += 1) {
                const vertexIndex = index ? index.getX(offset + corner) : offset + corner;
                const localPosition = [position.getX(vertexIndex), position.getY(vertexIndex), position.getZ(vertexIndex)];
                const worldPosition = geometry.transformPosition(worldMatrix, localPosition);
                let targetNormal = null;
                if (normal) {
                    const localNormal = [normal.getX(vertexIndex), normal.getY(vertexIndex), normal.getZ(vertexIndex)];
                    const worldNormal = geometry.transformNormal(worldMatrix, localNormal);
                    targetNormal = geometry.normalize3(geometry.sourceVectorToWorld(worldNormal), 'Thestra OBJ normal');
                }
                corners.push({
                    position: geometry.sourceVectorToWorld(worldPosition, recipe.sourceUnitsToMapCells),
                    normal: targetNormal,
                    // Wavefront UV origin is lower-left; Thestra's neutral model
                    // contract matches the existing runtime adapter's upper-left
                    // convention.
                    uv: uv ? [uv.getX(vertexIndex), 1 - uv.getY(vertexIndex)] : [0, 0],
                    color: color
                        ? [color.getX(vertexIndex), color.getY(vertexIndex), color.getZ(vertexIndex), 1]
                        : [1, 1, 1, 1],
                });
            }
            output.appendTriangle(slot, corners);
        }
    });

    const diagnostics = /(^|\n)\s*mtllib\s+/m.test(text)
        ? [{
            code: 'OBJ_MTL_APPEARANCE_NOT_IMPORTED',
            severity: 'info',
            detail: 'OBJ material names become stable Model materialSlots; MTL appearance remains on the legacy path until Surface projection is implemented.',
        }]
        : [];
    return { geometry: output.finish(), diagnostics };
}

async function importRecipe({ projectRoot, recipe }) {
    const validated = contract.validateRecipe(recipe.id, recipe);
    const filePath = projectFile(projectRoot, validated.source.path, `Model '${validated.id}' source`);
    const bytes = fs.readFileSync(filePath);
    const normalized = validated.source.kind === 'obj'
        ? await normalizeObj({ filePath, recipe: validated })
        : await normalizeGltf({ filePath, recipe: validated });
    const bundle = contract.makeBundle({
        recipe: validated,
        sourceSha256: contract.sha256(bytes),
        geometry: normalized.geometry,
        diagnostics: normalized.diagnostics,
    });
    return contract.validateBundle(bundle);
}

async function importModel({ projectRoot, modelId, registryPath = 'data/models.json' }) {
    const registry = contract.loadRegistry(projectRoot, registryPath);
    const recipe = registry.models[modelId];
    if (!recipe) throw new Error(`Unknown Model '${modelId}' in ${registry.registryPath}`);
    return importRecipe({ projectRoot, recipe });
}

module.exports = {
    importModel,
    importRecipe,
    normalizeGltf,
    normalizeObj,
};
