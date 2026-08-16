'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');
const { Accessor, Document, NodeIO } = require('@gltf-transform/core');
const {
    extractCharacterProbe,
    gltfQuaternionToWorld,
} = require('./gltf-character-probe');

const S = Math.SQRT1_2;

function nearly(actual, expected, epsilon = 1e-6) {
    assert.equal(actual.length, expected.length);
    actual.forEach((value, index) => {
        assert.ok(Math.abs(value - expected[index]) <= epsilon,
            `component ${index}: expected ${expected[index]}, got ${value}`);
    });
}

function accessor(document, buffer, name, type, array) {
    return document.createAccessor(name)
        .setType(type)
        .setArray(array)
        .setBuffer(buffer);
}

function identityMatrices(count) {
    const values = [];
    for (let i = 0; i < count; i++) {
        values.push(
            1, 0, 0, 0,
            0, 1, 0, 0,
            0, 0, 1, 0,
            0, 0, 0, 1
        );
    }
    return new Float32Array(values);
}

function addClip(document, buffer, id, target, path, timesValues, outputValues, outputType, interpolation = 'LINEAR') {
    const times = accessor(document, buffer, `${id}-${path}-times`, Accessor.Type.SCALAR,
        new Float32Array(timesValues));
    const output = accessor(document, buffer, `${id}-${path}-values`, outputType,
        new Float32Array(outputValues));
    const sampler = document.createAnimationSampler(`${id}-${path}-sampler`)
        .setInput(times)
        .setOutput(output)
        .setInterpolation(interpolation);
    const channel = document.createAnimationChannel(`${id}-${path}-channel`)
        .setTargetNode(target)
        .setTargetPath(path)
        .setSampler(sampler);
    const animation = document.createAnimation(id)
        .addSampler(sampler)
        .addChannel(channel);
    return { animation, sampler, channel };
}

function makeCharacterFixture() {
    const document = new Document();
    const buffer = document.createBuffer('character-buffer');

    const rootBone = document.createNode('root').setTranslation([0, 1, 0]);
    const legBone = document.createNode('leg').setTranslation([0, -1, 0]);
    rootBone.addChild(legBone);

    const positions = accessor(document, buffer, 'positions', Accessor.Type.VEC3,
        new Float32Array([
            -0.5, 0, 0,
             0.5, 0, 0,
             0.0, 1, 0,
        ]));
    const joints = accessor(document, buffer, 'joints-0', Accessor.Type.VEC4,
        new Uint16Array([
            0, 1, 0, 0,
            0, 1, 0, 0,
            0, 1, 0, 0,
        ]));
    const weights = accessor(document, buffer, 'weights-0', Accessor.Type.VEC4,
        new Float32Array([
            0.75, 0.25, 0, 0,
            0.75, 0.25, 0, 0,
            0.25, 0.75, 0, 0,
        ]));
    const primitive = document.createPrimitive('body-primitive')
        .setAttribute('POSITION', positions)
        .setAttribute('JOINTS_0', joints)
        .setAttribute('WEIGHTS_0', weights);
    const mesh = document.createMesh('body').addPrimitive(primitive);

    const ibm = accessor(document, buffer, 'inverse-bind-matrices', Accessor.Type.MAT4,
        identityMatrices(2));
    const skin = document.createSkin('humanoid')
        .setSkeleton(rootBone)
        .addJoint(rootBone)
        .addJoint(legBone)
        .setInverseBindMatrices(ibm);
    const actor = document.createNode('actor').setMesh(mesh).setSkin(skin);

    const scene = document.createScene('main').addChild(rootBone).addChild(actor);
    document.getRoot().setDefaultScene(scene);

    const idle = addClip(document, buffer, 'idle', legBone, 'rotation',
        [0, 1],
        [
            0, 0, 0, 1,
            0, S, 0, S,
        ],
        Accessor.Type.VEC4);
    const walk = addClip(document, buffer, 'walk', rootBone, 'translation',
        [0, 0.5, 1],
        [
            0, 0, 0,
            0, 0, 0.5,
            0, 0, 1,
        ],
        Accessor.Type.VEC3);

    return { document, buffer, rootBone, legBone, actor, primitive, skin, idle, walk };
}

test('basis-converted quaternion preserves X rotation and maps source Y rotation to Thestra Z', () => {
    nearly(gltfQuaternionToWorld([S, 0, 0, S]), [S, 0, 0, S]);
    nearly(gltfQuaternionToWorld([0, S, 0, S]), [0, 0, S, S]);
});

test('character probe extracts stable hierarchy, skin order, influences and idle/walk clips', () => {
    const { document } = makeCharacterFixture();
    const probe = extractCharacterProbe(document, { metersToMapCells: 2 });

    assert.equal(probe.kind, 'thestra-character-source-probe');
    assert.equal(probe.version, 0);
    assert.deepEqual(probe.normalization, {
        sourceUp: 'y',
        targetUp: 'z',
        metersToMapCells: 2,
        rotationBasis: '+90deg-x',
    });

    const root = probe.nodes.find(node => node.id === 'root');
    const leg = probe.nodes.find(node => node.id === 'leg');
    const actor = probe.nodes.find(node => node.id === 'actor');
    assert.ok(root && leg && actor);
    assert.equal(root.parent, null);
    assert.equal(leg.parent, 'root');
    nearly(root.sourceLocal.translation, [0, 1, 0]);
    nearly(root.thestraLocal.translation, [0, 0, 2]);
    nearly(leg.thestraLocal.translation, [0, 0, -2]);
    nearly(root.thestraLocal.rotation, [0, 0, 0, 1]);
    nearly(root.thestraLocal.scale, [1, 1, 1]);

    assert.equal(probe.skins.length, 1);
    assert.deepEqual(probe.skins[0].joints, ['root', 'leg']);
    assert.equal(probe.skins[0].skeleton, 'root');
    assert.equal(probe.skins[0].inverseBindMatrices.space, 'gltf-y-up-meters');
    assert.equal(probe.skins[0].inverseBindMatrices.implicitIdentity, false);
    assert.equal(probe.skins[0].inverseBindMatrices.values.length, 2);
    nearly(probe.skins[0].inverseBindMatrices.values[0], [
        1, 0, 0, 0,
        0, 1, 0, 0,
        0, 0, 1, 0,
        0, 0, 0, 1,
    ]);

    assert.equal(probe.skinBindings.length, 1);
    const binding = probe.skinBindings[0];
    assert.equal(binding.node, 'actor');
    assert.equal(binding.skin, 'humanoid');
    assert.equal(binding.vertexCount, 3);
    assert.equal(binding.influenceSets.length, 1);
    assert.deepEqual(binding.influenceSets[0].joints[0], [0, 1, 0, 0]);
    nearly(binding.influenceSets[0].weights[0], [0.75, 0.25, 0, 0]);

    assert.deepEqual(probe.clips.map(clip => clip.id), ['idle', 'walk']);
    const idle = probe.clips[0];
    assert.equal(idle.duration, 1);
    assert.equal(idle.channels.length, 1);
    assert.equal(idle.channels[0].target, 'leg');
    assert.equal(idle.channels[0].path, 'rotation');
    assert.equal(idle.channels[0].interpolation, 'LINEAR');
    nearly(idle.channels[0].values[0], [0, 0, 0, 1]);
    nearly(idle.channels[0].values[1], [0, 0, S, S]);

    const walk = probe.clips[1];
    assert.equal(walk.duration, 1);
    assert.equal(walk.channels[0].target, 'root');
    assert.equal(walk.channels[0].path, 'translation');
    nearly(walk.channels[0].values[0], [0, 0, 0]);
    nearly(walk.channels[0].values[1], [0, -1, 0]);
    nearly(walk.channels[0].values[2], [0, -2, 0]);
});

test('character probe survives GLB round-trip without depending on a renderer scene graph', async () => {
    const { document } = makeCharacterFixture();
    const io = new NodeIO();
    const bytes = await io.writeBinary(document);
    const reread = await io.readBinary(bytes);

    const first = extractCharacterProbe(document, { metersToMapCells: 1 });
    const second = extractCharacterProbe(reread, { metersToMapCells: 1 });
    assert.deepEqual(second, first);
});

test('character probe supports multiple influence sets without ratifying a four-influence runtime limit', () => {
    const fixture = makeCharacterFixture();
    const extraJoints = accessor(fixture.document, fixture.buffer, 'joints-1', Accessor.Type.VEC4,
        new Uint16Array([
            1, 0, 0, 0,
            1, 0, 0, 0,
            1, 0, 0, 0,
        ]));
    const extraWeights = accessor(fixture.document, fixture.buffer, 'weights-1', Accessor.Type.VEC4,
        new Float32Array([
            0, 0, 0, 0,
            0, 0, 0, 0,
            0, 0, 0, 0,
        ]));
    fixture.primitive.setAttribute('JOINTS_1', extraJoints).setAttribute('WEIGHTS_1', extraWeights);

    const probe = extractCharacterProbe(fixture.document, { metersToMapCells: 1 });
    assert.equal(probe.skinBindings[0].influenceSets.length, 2);
    assert.equal(probe.skinBindings[0].influenceSets[1].set, 1);
});

test('character probe refuses unnamed/duplicate clips and undecided animation semantics', () => {
    const unnamed = makeCharacterFixture();
    unnamed.idle.animation.setName('');
    assert.throws(() => extractCharacterProbe(unnamed.document, { metersToMapCells: 1 }),
        /requires a non-empty semantic clip name/);

    const duplicate = makeCharacterFixture();
    duplicate.walk.animation.setName('idle');
    assert.throws(() => extractCharacterProbe(duplicate.document, { metersToMapCells: 1 }),
        /duplicate semantic clip name 'idle'/);

    const cubic = makeCharacterFixture();
    cubic.idle.sampler.setInterpolation('CUBICSPLINE');
    assert.throws(() => extractCharacterProbe(cubic.document, { metersToMapCells: 1 }),
        /CUBICSPLINE; tangent policy is not decided/);

    const morph = makeCharacterFixture();
    morph.walk.channel.setTargetPath('weights');
    assert.throws(() => extractCharacterProbe(morph.document, { metersToMapCells: 1 }),
        /targets unsupported 'weights'/);
});

test('character probe fails loud on malformed skin bindings and missing scale policy', () => {
    const fixture = makeCharacterFixture();
    fixture.primitive.setAttribute('WEIGHTS_0', null);
    assert.throws(() => extractCharacterProbe(fixture.document, { metersToMapCells: 1 }),
        /must pair JOINTS_0 with WEIGHTS_0/);

    const unscaled = makeCharacterFixture();
    assert.throws(() => extractCharacterProbe(unscaled.document, {}),
        /metersToMapCells must be a finite positive number/);
});
