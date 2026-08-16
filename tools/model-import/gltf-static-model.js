'use strict';

const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const { NodeIO, Primitive } = require('@gltf-transform/core');

const BUNDLE_KIND = 'thestra-static-model-spike';
const BUNDLE_VERSION = 0;
const EPSILON = 1e-10;

function sha256(bytes) {
    return crypto.createHash('sha256').update(bytes).digest('hex');
}

function portablePath(value) {
    return String(value || '').replace(/\\/g, '/');
}

function finitePositive(value, label) {
    const number = Number(value);
    if (!Number.isFinite(number) || number <= 0) {
        throw new Error(`${label} must be a finite positive number`);
    }
    return number;
}

// glTF is right-handed, Y-up, and defines an asset's front side toward +Z.
// Thestra's current model contract is right-handed Z-up. This is the same
// +90-degree X-axis basis change already used by the OBJ adapter:
//   glTF/OBJ (x, y, z) -> Thestra (x, -z, y)
// The transform is a rotation (determinant +1), so winding is preserved.
function gltfVectorToWorld(vector, scale = 1) {
    return [vector[0] * scale, -vector[2] * scale, vector[1] * scale];
}

function transformPosition(matrix, position) {
    const x = position[0], y = position[1], z = position[2];
    return [
        matrix[0] * x + matrix[4] * y + matrix[8] * z + matrix[12],
        matrix[1] * x + matrix[5] * y + matrix[9] * z + matrix[13],
        matrix[2] * x + matrix[6] * y + matrix[10] * z + matrix[14],
    ];
}

function determinant3(matrix) {
    const a00 = matrix[0], a01 = matrix[4], a02 = matrix[8];
    const a10 = matrix[1], a11 = matrix[5], a12 = matrix[9];
    const a20 = matrix[2], a21 = matrix[6], a22 = matrix[10];
    return a00 * (a11 * a22 - a12 * a21)
        - a01 * (a10 * a22 - a12 * a20)
        + a02 * (a10 * a21 - a11 * a20);
}

function transformNormal(matrix, normal) {
    const a00 = matrix[0], a01 = matrix[4], a02 = matrix[8];
    const a10 = matrix[1], a11 = matrix[5], a12 = matrix[9];
    const a20 = matrix[2], a21 = matrix[6], a22 = matrix[10];

    const c00 = a11 * a22 - a12 * a21;
    const c01 = -(a10 * a22 - a12 * a20);
    const c02 = a10 * a21 - a11 * a20;
    const c10 = -(a01 * a22 - a02 * a21);
    const c11 = a00 * a22 - a02 * a20;
    const c12 = -(a00 * a21 - a01 * a20);
    const c20 = a01 * a12 - a02 * a11;
    const c21 = -(a00 * a12 - a02 * a10);
    const c22 = a00 * a11 - a01 * a10;

    const det = a00 * c00 + a01 * c01 + a02 * c02;
    if (!Number.isFinite(det) || Math.abs(det) <= EPSILON) {
        throw new Error('glTF node transform is non-invertible; cannot transform normals');
    }

    const x = c00 * normal[0] + c01 * normal[1] + c02 * normal[2];
    const y = c10 * normal[0] + c11 * normal[1] + c12 * normal[2];
    const z = c20 * normal[0] + c21 * normal[1] + c22 * normal[2];
    return normalizeVector([x / det, y / det, z / det], 'transformed normal');
}

function normalizeVector(vector, label) {
    const length = Math.hypot(vector[0], vector[1], vector[2]);
    if (!Number.isFinite(length) || length <= EPSILON) {
        throw new Error(`${label} has zero or invalid length`);
    }
    return [vector[0] / length, vector[1] / length, vector[2] / length];
}

function faceNormal(a, b, c) {
    const ux = b[0] - a[0], uy = b[1] - a[1], uz = b[2] - a[2];
    const vx = c[0] - a[0], vy = c[1] - a[1], vz = c[2] - a[2];
    return normalizeVector([
        uy * vz - uz * vy,
        uz * vx - ux * vz,
        ux * vy - uy * vx,
    ], 'mesh face normal');
}

function accessorElement(accessor, index, fallback) {
    if (!accessor) return fallback.slice();
    return accessor.getElement(index, []);
}

function textureFact(texture) {
    if (!texture) return null;
    const image = texture.getImage();
    const bytes = image ? Buffer.from(image) : null;
    return {
        name: texture.getName() || '',
        mimeType: texture.getMimeType() || null,
        byteLength: bytes ? bytes.byteLength : 0,
        sha256: bytes ? sha256(bytes) : null,
    };
}

function materialIds(root) {
    const materials = root.listMaterials();
    const counts = new Map();
    for (const material of materials) {
        const name = material.getName() || '';
        if (name) counts.set(name, (counts.get(name) || 0) + 1);
    }

    const ids = new Map();
    materials.forEach((material, index) => {
        const name = material.getName() || '';
        ids.set(material, name && counts.get(name) === 1 ? name : `material_${index}`);
    });
    return ids;
}

function diagnostic(code, material, detail) {
    return {
        code,
        severity: 'degraded',
        material,
        detail,
    };
}

function projectMaterial(material, id) {
    if (!material) return { fact: null, diagnostics: [] };

    const diagnostics = [];
    const metallicFactor = material.getMetallicFactor();
    const roughnessFactor = material.getRoughnessFactor();
    const metallicRoughnessTexture = material.getMetallicRoughnessTexture();

    // The spike deliberately does not grow Thestra into a generic PBR renderer.
    // Base color and emissive facts survive normalization; metallic/roughness is
    // named as a degradation even when glTF defaults are in effect, because
    // silently dropping those defaults would still be a semantic loss.
    diagnostics.push(diagnostic(
        'GLTF_PBR_METALLIC_ROUGHNESS_DEGRADED',
        id,
        {
            metallicFactor,
            roughnessFactor,
            texture: textureFact(metallicRoughnessTexture),
        }
    ));

    if (material.getNormalTexture()) {
        diagnostics.push(diagnostic('GLTF_NORMAL_TEXTURE_UNSUPPORTED', id, {
            texture: textureFact(material.getNormalTexture()),
            scale: material.getNormalScale(),
        }));
    }
    if (material.getOcclusionTexture()) {
        diagnostics.push(diagnostic('GLTF_OCCLUSION_TEXTURE_UNSUPPORTED', id, {
            texture: textureFact(material.getOcclusionTexture()),
            strength: material.getOcclusionStrength(),
        }));
    }
    if (material.getAlphaMode() !== 'OPAQUE') {
        diagnostics.push(diagnostic('GLTF_ALPHA_MODE_UNSUPPORTED', id, {
            alphaMode: material.getAlphaMode(),
            alphaCutoff: material.getAlphaCutoff(),
        }));
    }
    if (material.getDoubleSided()) {
        diagnostics.push(diagnostic('GLTF_DOUBLE_SIDED_UNSUPPORTED', id, { doubleSided: true }));
    }

    return {
        fact: {
            id,
            sourceName: material.getName() || '',
            baseColorFactor: Array.from(material.getBaseColorFactor()),
            baseColorTexture: textureFact(material.getBaseColorTexture()),
            emissiveFactor: Array.from(material.getEmissiveFactor()),
            emissiveTexture: textureFact(material.getEmissiveTexture()),
        },
        diagnostics,
    };
}

function selectedScene(root) {
    const defaultScene = root.getDefaultScene();
    if (defaultScene) return defaultScene;
    const scenes = root.listScenes();
    if (scenes.length === 1) return scenes[0];
    if (scenes.length === 0) throw new Error('glTF static import requires a scene');
    throw new Error('glTF static import found multiple scenes but no default scene');
}

function normalizeDocument(document, options = {}) {
    const metersToMapCells = finitePositive(options.metersToMapCells, 'metersToMapCells');
    const root = document.getRoot();
    const scene = selectedScene(root);
    if (root.listAnimations().length > 0) {
        throw new Error('glTF static import does not accept animation; use the future rig/clip normalizer');
    }

    const ids = materialIds(root);
    const materialFacts = new Map();
    const diagnostics = [];
    const groupsByMaterial = new Map();
    const groups = [];
    const bounds = {
        minX: Infinity, minY: Infinity, minZ: Infinity,
        maxX: -Infinity, maxY: -Infinity, maxZ: -Infinity,
    };
    let vertexCount = 0;

    function groupFor(material) {
        const id = material ? ids.get(material) : '';
        if (material && !materialFacts.has(id)) {
            const projected = projectMaterial(material, id);
            materialFacts.set(id, projected.fact);
            diagnostics.push(...projected.diagnostics);
        }
        if (groupsByMaterial.has(id)) return groupsByMaterial.get(id);
        const group = { material: id, vertices: [] };
        groupsByMaterial.set(id, group);
        groups.push(group);
        return group;
    }

    function appendVertex(group, position, uv, normal, color) {
        bounds.minX = Math.min(bounds.minX, position[0]);
        bounds.minY = Math.min(bounds.minY, position[1]);
        bounds.minZ = Math.min(bounds.minZ, position[2]);
        bounds.maxX = Math.max(bounds.maxX, position[0]);
        bounds.maxY = Math.max(bounds.maxY, position[1]);
        bounds.maxZ = Math.max(bounds.maxZ, position[2]);
        group.vertices.push([
            position[0], position[1], position[2],
            uv[0], uv[1],
            normal[0], normal[1], normal[2],
            color[0], color[1], color[2], color.length > 3 ? color[3] : 1,
        ]);
        vertexCount += 1;
    }

    function visit(node) {
        if (node.getSkin()) {
            throw new Error(`glTF static import found skin on node '${node.getName() || '(unnamed)'}'`);
        }
        const mesh = node.getMesh();
        if (!mesh) return;

        const worldMatrix = node.getWorldMatrix();
        const det = determinant3(worldMatrix);
        if (!Number.isFinite(det) || Math.abs(det) <= EPSILON) {
            throw new Error(`glTF node '${node.getName() || '(unnamed)'}' has non-invertible transform`);
        }
        if (det < 0) {
            throw new Error(`glTF node '${node.getName() || '(unnamed)'}' has mirrored transform; static bake policy is not decided`);
        }

        mesh.listPrimitives().forEach((primitive, primitiveIndex) => {
            if (primitive.getMode() !== Primitive.Mode.TRIANGLES) {
                throw new Error(`glTF mesh '${mesh.getName() || '(unnamed)'}' primitive ${primitiveIndex} is not TRIANGLES`);
            }
            if (primitive.listTargets().length > 0) {
                throw new Error(`glTF mesh '${mesh.getName() || '(unnamed)'}' primitive ${primitiveIndex} has morph targets`);
            }

            const positions = primitive.getAttribute('POSITION');
            if (!positions) {
                throw new Error(`glTF mesh '${mesh.getName() || '(unnamed)'}' primitive ${primitiveIndex} has no POSITION`);
            }
            const normals = primitive.getAttribute('NORMAL');
            const uvs = primitive.getAttribute('TEXCOORD_0');
            const colors = primitive.getAttribute('COLOR_0');
            const indices = primitive.getIndices();
            const indexCount = indices ? indices.getCount() : positions.getCount();
            if (indexCount % 3 !== 0) {
                throw new Error(`glTF mesh '${mesh.getName() || '(unnamed)'}' primitive ${primitiveIndex} triangle index count is not divisible by 3`);
            }

            const group = groupFor(primitive.getMaterial());
            for (let triangleOffset = 0; triangleOffset < indexCount; triangleOffset += 3) {
                const triangle = [];
                for (let corner = 0; corner < 3; corner++) {
                    const index = indices
                        ? accessorElement(indices, triangleOffset + corner, [0])[0]
                        : triangleOffset + corner;
                    if (!Number.isInteger(index) || index < 0 || index >= positions.getCount()) {
                        throw new Error(`glTF primitive contains invalid vertex index ${index}`);
                    }

                    const sourcePosition = accessorElement(positions, index, [0, 0, 0]);
                    const gltfPosition = transformPosition(worldMatrix, sourcePosition);
                    const position = gltfVectorToWorld(gltfPosition, metersToMapCells);
                    const uv = accessorElement(uvs, index, [0, 0]);
                    const color = accessorElement(colors, index, [1, 1, 1, 1]);
                    let normal = null;
                    if (normals) {
                        const gltfNormal = transformNormal(worldMatrix, accessorElement(normals, index, [0, 1, 0]));
                        normal = normalizeVector(gltfVectorToWorld(gltfNormal), 'Thestra normal');
                    }
                    triangle.push({ position, uv, color, normal });
                }

                const generated = faceNormal(
                    triangle[0].position,
                    triangle[1].position,
                    triangle[2].position
                );
                for (const corner of triangle) {
                    appendVertex(group, corner.position, corner.uv, corner.normal || generated, corner.color);
                }
            }
        });
    }

    for (const rootNode of scene.listChildren()) rootNode.traverse(visit);
    if (vertexCount === 0) throw new Error('glTF static import produced no triangle geometry');

    return {
        kind: BUNDLE_KIND,
        version: BUNDLE_VERSION,
        source: {
            kind: 'gltf',
            path: portablePath(options.sourcePath || ''),
            sha256: options.sourceSha256 || null,
        },
        normalization: {
            sourceUp: 'y',
            targetUp: 'z',
            metersToMapCells,
            uvOrigin: 'upper-left',
        },
        model: {
            groups,
            vertexCount,
            bounds,
        },
        materials: Array.from(materialFacts.values()),
        diagnostics,
    };
}

async function normalizeFile(filePath, options = {}) {
    const bytes = fs.readFileSync(filePath);
    const io = options.io || new NodeIO();
    const document = await io.read(filePath);
    const sourcePath = options.sourcePath === undefined ? path.basename(filePath) : options.sourcePath;
    return normalizeDocument(document, {
        ...options,
        sourcePath,
        sourceSha256: sha256(bytes),
    });
}

function serializeBundle(bundle) {
    return JSON.stringify(bundle, null, 2) + '\n';
}

function hashBundle(bundle) {
    return sha256(Buffer.from(serializeBundle(bundle), 'utf8'));
}

module.exports = {
    BUNDLE_KIND,
    BUNDLE_VERSION,
    gltfVectorToWorld,
    hashBundle,
    normalizeDocument,
    normalizeFile,
    serializeBundle,
    transformNormal,
    transformPosition,
};
