'use strict';

const { gltfVectorToWorld } = require('./gltf-static-model');

const PROBE_KIND = 'thestra-character-source-probe';
const PROBE_VERSION = 0;
const EPSILON = 1e-8;
const BASIS_QUATERNION = Object.freeze([Math.SQRT1_2, 0, 0, Math.SQRT1_2]);

function finitePositive(value, label) {
    const number = Number(value);
    if (!Number.isFinite(number) || number <= 0) {
        throw new Error(`${label} must be a finite positive number`);
    }
    return number;
}

function quaternionMultiply(a, b) {
    const ax = a[0], ay = a[1], az = a[2], aw = a[3];
    const bx = b[0], by = b[1], bz = b[2], bw = b[3];
    return [
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
        aw * bw - ax * bx - ay * by - az * bz,
    ];
}

function quaternionConjugate(q) {
    return [-q[0], -q[1], -q[2], q[3]];
}

function normalizeQuaternion(q, label = 'quaternion') {
    const length = Math.hypot(q[0], q[1], q[2], q[3]);
    if (!Number.isFinite(length) || length <= EPSILON) {
        throw new Error(`${label} has zero or invalid length`);
    }
    return [q[0] / length, q[1] / length, q[2] / length, q[3] / length];
}

// Same coordinate basis used by the static spike: +90 degrees around X,
// source glTF Y-up -> Thestra Z-up. A local rotation changes basis by
// conjugation C * R * C^-1. This keeps clip semantics local to each node;
// it does not flatten an animated hierarchy into world-space keyframes.
function gltfQuaternionToWorld(q) {
    const source = normalizeQuaternion(Array.from(q), 'glTF rotation');
    const converted = quaternionMultiply(
        quaternionMultiply(BASIS_QUATERNION, source),
        quaternionConjugate(BASIS_QUATERNION)
    );
    return normalizeQuaternion(converted, 'Thestra rotation');
}

function gltfScaleToWorld(scale) {
    return [scale[0], scale[2], scale[1]];
}

function nodeIdentity(root) {
    const nodes = root.listNodes();
    const counts = new Map();
    for (const node of nodes) {
        const name = node.getName() || '';
        if (name) counts.set(name, (counts.get(name) || 0) + 1);
    }
    const ids = new Map();
    nodes.forEach((node, index) => {
        const name = node.getName() || '';
        ids.set(node, name && counts.get(name) === 1 ? name : `node_${index}`);
    });
    return { ids, nodes };
}

function accessorElements(accessor) {
    if (!accessor) return null;
    const elements = [];
    for (let index = 0; index < accessor.getCount(); index++) {
        elements.push(Array.from(accessor.getElement(index, [])));
    }
    return elements;
}

function sourceInverseBindFacts(skin) {
    const accessor = skin.getInverseBindMatrices();
    if (!accessor) {
        return {
            space: 'gltf-y-up-meters',
            implicitIdentity: true,
            values: null,
        };
    }
    return {
        space: 'gltf-y-up-meters',
        implicitIdentity: false,
        values: accessorElements(accessor),
    };
}

function influenceSets(primitive, skin, context) {
    const position = primitive.getAttribute('POSITION');
    if (!position) throw new Error(`${context} has no POSITION attribute`);

    const sets = [];
    for (let setIndex = 0; ; setIndex++) {
        const joints = primitive.getAttribute(`JOINTS_${setIndex}`);
        const weights = primitive.getAttribute(`WEIGHTS_${setIndex}`);
        if (!joints && !weights) break;
        if (!joints || !weights) {
            throw new Error(`${context} must pair JOINTS_${setIndex} with WEIGHTS_${setIndex}`);
        }
        if (joints.getCount() !== position.getCount() || weights.getCount() !== position.getCount()) {
            throw new Error(`${context} influence accessor count disagrees with POSITION`);
        }

        const jointValues = accessorElements(joints);
        const weightValues = accessorElements(weights);
        jointValues.forEach((row, vertexIndex) => {
            for (const jointIndex of row) {
                if (!Number.isInteger(jointIndex) || jointIndex < 0 || jointIndex >= skin.listJoints().length) {
                    throw new Error(`${context} vertex ${vertexIndex} references invalid skin joint ${jointIndex}`);
                }
            }
            for (const weight of weightValues[vertexIndex]) {
                if (!Number.isFinite(weight) || weight < 0) {
                    throw new Error(`${context} vertex ${vertexIndex} contains invalid skin weight`);
                }
            }
        });

        sets.push({
            set: setIndex,
            joints: jointValues,
            weights: weightValues,
        });
    }
    if (sets.length === 0) throw new Error(`${context} has a skin but no JOINTS/WEIGHTS influence set`);
    return sets;
}

function extractSkins(root, ids) {
    const skinIds = new Map();
    root.listSkins().forEach((skin, index) => {
        const name = skin.getName() || '';
        skinIds.set(skin, name || `skin_${index}`);
    });

    const skins = root.listSkins().map(skin => ({
        id: skinIds.get(skin),
        sourceName: skin.getName() || '',
        skeleton: skin.getSkeleton() ? ids.get(skin.getSkeleton()) : null,
        joints: skin.listJoints().map(joint => ids.get(joint)),
        inverseBindMatrices: sourceInverseBindFacts(skin),
    }));

    const bindings = [];
    for (const node of root.listNodes()) {
        const skin = node.getSkin();
        if (!skin) continue;
        const mesh = node.getMesh();
        if (!mesh) throw new Error(`skinned node '${ids.get(node)}' has no mesh`);
        mesh.listPrimitives().forEach((primitive, primitiveIndex) => {
            bindings.push({
                node: ids.get(node),
                skin: skinIds.get(skin),
                primitive: primitiveIndex,
                vertexCount: primitive.getAttribute('POSITION')
                    ? primitive.getAttribute('POSITION').getCount()
                    : 0,
                influenceSets: influenceSets(
                    primitive,
                    skin,
                    `skinned node '${ids.get(node)}' primitive ${primitiveIndex}`
                ),
            });
        });
    }
    return { skins, bindings };
}

function channelValues(path, accessor, metersToMapCells) {
    const values = accessorElements(accessor) || [];
    if (path === 'translation') {
        return values.map(value => gltfVectorToWorld(value, metersToMapCells));
    }
    if (path === 'rotation') {
        return values.map(gltfQuaternionToWorld);
    }
    if (path === 'scale') {
        return values.map(gltfScaleToWorld);
    }
    throw new Error(`unsupported animation target path '${path}'`);
}

function extractClips(root, ids, metersToMapCells) {
    const seen = new Set();
    return root.listAnimations().map((animation, animationIndex) => {
        const id = animation.getName() || '';
        if (!id) throw new Error(`animation ${animationIndex} requires a non-empty semantic clip name`);
        if (seen.has(id)) throw new Error(`duplicate semantic clip name '${id}'`);
        seen.add(id);

        let duration = 0;
        const channels = animation.listChannels().map((channel, channelIndex) => {
            const target = channel.getTargetNode();
            if (!target || !ids.has(target)) {
                throw new Error(`clip '${id}' channel ${channelIndex} has no target node`);
            }
            const path = channel.getTargetPath();
            if (!['translation', 'rotation', 'scale'].includes(path)) {
                throw new Error(`clip '${id}' channel ${channelIndex} targets unsupported '${path}'`);
            }
            const sampler = channel.getSampler();
            if (!sampler) throw new Error(`clip '${id}' channel ${channelIndex} has no sampler`);
            const interpolation = sampler.getInterpolation();
            if (interpolation === 'CUBICSPLINE') {
                throw new Error(`clip '${id}' channel ${channelIndex} uses CUBICSPLINE; tangent policy is not decided`);
            }
            if (!['LINEAR', 'STEP'].includes(interpolation)) {
                throw new Error(`clip '${id}' channel ${channelIndex} uses unsupported interpolation '${interpolation}'`);
            }
            const input = sampler.getInput();
            const output = sampler.getOutput();
            if (!input || !output) throw new Error(`clip '${id}' channel ${channelIndex} is missing keyframe accessors`);
            const times = Array.from(input.getArray() || []);
            if (times.length !== input.getCount()) {
                throw new Error(`clip '${id}' channel ${channelIndex} time accessor is not scalar`);
            }
            if (output.getCount() !== times.length) {
                throw new Error(`clip '${id}' channel ${channelIndex} key/value count mismatch`);
            }
            for (let index = 0; index < times.length; index++) {
                const time = times[index];
                if (!Number.isFinite(time) || time < 0 || (index > 0 && time <= times[index - 1])) {
                    throw new Error(`clip '${id}' channel ${channelIndex} has invalid keyframe times`);
                }
                duration = Math.max(duration, time);
            }
            return {
                target: ids.get(target),
                path,
                interpolation,
                times,
                values: channelValues(path, output, metersToMapCells),
            };
        });

        return { id, duration, channels };
    });
}

function extractCharacterProbe(document, options = {}) {
    const metersToMapCells = finitePositive(options.metersToMapCells, 'metersToMapCells');
    const root = document.getRoot();
    const { ids, nodes } = nodeIdentity(root);
    if (root.listSkins().length === 0) throw new Error('character probe requires at least one skin');
    if (root.listAnimations().length === 0) throw new Error('character probe requires named animation clips');

    const nodeFacts = nodes.map(node => ({
        id: ids.get(node),
        sourceName: node.getName() || '',
        parent: node.getParentNode() ? ids.get(node.getParentNode()) : null,
        sourceLocal: {
            translation: Array.from(node.getTranslation()),
            rotation: Array.from(node.getRotation()),
            scale: Array.from(node.getScale()),
        },
        thestraLocal: {
            translation: gltfVectorToWorld(node.getTranslation(), metersToMapCells),
            rotation: gltfQuaternionToWorld(node.getRotation()),
            scale: gltfScaleToWorld(node.getScale()),
        },
    }));

    const { skins, bindings } = extractSkins(root, ids);
    const clips = extractClips(root, ids, metersToMapCells);

    return {
        kind: PROBE_KIND,
        version: PROBE_VERSION,
        normalization: {
            sourceUp: 'y',
            targetUp: 'z',
            metersToMapCells,
            rotationBasis: '+90deg-x',
        },
        nodes: nodeFacts,
        skins,
        skinBindings: bindings,
        clips,
    };
}

module.exports = {
    BASIS_QUATERNION,
    PROBE_KIND,
    PROBE_VERSION,
    extractCharacterProbe,
    gltfQuaternionToWorld,
    gltfScaleToWorld,
    normalizeQuaternion,
    quaternionMultiply,
};
