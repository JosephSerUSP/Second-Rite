'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');
const { Accessor, Document, NodeIO } = require('@gltf-transform/core');
const contract = require('./model-contract');
const importer = require('./import-model');

const REPO_ROOT = path.resolve(__dirname, '..', '..');
const OBJ_FIXTURE = path.join(__dirname, 'fixtures', 'static-equivalence.obj');

function makeAccessor(document, buffer, name, type, array) {
    return document.createAccessor(name).setType(type).setArray(array).setBuffer(buffer);
}

function staticDocument({ materialName = 'source_body', mirrored = false, animated = false } = {}) {
    const document = new Document();
    const buffer = document.createBuffer('fixture-buffer');
    const positions = makeAccessor(document, buffer, 'positions', Accessor.Type.VEC3,
        new Float32Array([0, 0, 0, 1, 0, 0, 0, 1, 0]));
    const normals = makeAccessor(document, buffer, 'normals', Accessor.Type.VEC3,
        new Float32Array([0, 0, 1, 0, 0, 1, 0, 0, 1]));
    const uvs = makeAccessor(document, buffer, 'uvs', Accessor.Type.VEC2,
        new Float32Array([0, 0, 1, 0, 0, 1]));
    const indices = makeAccessor(document, buffer, 'indices', Accessor.Type.SCALAR,
        new Uint16Array([0, 1, 2]));
    const material = document.createMaterial(materialName)
        .setBaseColorFactor([0.2, 0.4, 0.6, 1])
        .setEmissiveFactor([0.1, 0.2, 0.3]);
    const primitive = document.createPrimitive('triangle')
        .setAttribute('POSITION', positions)
        .setAttribute('NORMAL', normals)
        .setAttribute('TEXCOORD_0', uvs)
        .setIndices(indices)
        .setMaterial(material);
    const mesh = document.createMesh('fixture-mesh').addPrimitive(primitive);
    const node = document.createNode('fixture-node').setMesh(mesh).setScale(mirrored ? [-1, 1, 1] : [1, 1, 1]);
    const scene = document.createScene('main').addChild(node);
    document.getRoot().setDefaultScene(scene);
    if (animated) document.createAnimation('idle');
    return document;
}

async function writeGlb(projectRoot, relativePath, options) {
    const absolute = path.join(projectRoot, relativePath);
    fs.mkdirSync(path.dirname(absolute), { recursive: true });
    const bytes = await new NodeIO().writeBinary(staticDocument(options));
    fs.writeFileSync(absolute, Buffer.from(bytes));
    return absolute;
}

function recipe({ id = 'fixture.static', kind = 'obj', sourcePath = 'assets/models/static.obj', sourceMaterial = 'source_body' } = {}) {
    return {
        id,
        source: { kind, path: sourcePath },
        sourceUnitsToMapCells: 1,
        materialSlots: {
            body: { sourceMaterials: [sourceMaterial] },
        },
    };
}

test('root Model registry gives an existing asset stable Model and material-slot identity', async () => {
    const registry = contract.loadRegistry(REPO_ROOT);
    const authored = registry.models['system.placeholder_question'];
    assert.ok(authored);
    assert.equal(authored.source.path, 'assets/models/items/placeholder_question.obj');
    assert.deepEqual(Object.keys(authored.materialSlots), ['bright_gold', 'old_gold', 'ruby']);

    const bundle = await importer.importModel({
        projectRoot: REPO_ROOT,
        modelId: 'system.placeholder_question',
    });
    assert.equal(bundle.kind, 'thestra-model-bundle');
    assert.equal(bundle.version, 1);
    assert.equal(bundle.modelId, 'system.placeholder_question');
    assert.equal(bundle.source.kind, 'obj');
    assert.equal(bundle.source.path, 'assets/models/items/placeholder_question.obj');
    assert.match(bundle.source.sha256, /^[0-9a-f]{64}$/);
    assert.ok(bundle.geometry.vertexCount > 0);
    assert.ok(bundle.geometry.groups.length >= 1);
    const groupSlots = new Set(bundle.geometry.groups.map(group => group.materialSlot));
    for (const slot of groupSlots) assert.ok(['bright_gold', 'old_gold', 'ruby'].includes(slot));
    assert.equal(groupSlots.has('MAT_BrightGold'), false, 'source material names must not become bundle identity');
    assert.ok(bundle.diagnostics.some(entry => entry.code === 'OBJ_MTL_APPEARANCE_NOT_IMPORTED'));
});

test('equivalent OBJ and glTF normalize to identical Thestra static geometry', async () => {
    const projectRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'thestra-model-equivalence-'));
    try {
        const objPath = 'assets/models/static.obj';
        fs.mkdirSync(path.dirname(path.join(projectRoot, objPath)), { recursive: true });
        fs.copyFileSync(OBJ_FIXTURE, path.join(projectRoot, objPath));
        const glbPath = 'assets/models/static.glb';
        await writeGlb(projectRoot, glbPath);

        const fromObj = await importer.importRecipe({
            projectRoot,
            recipe: recipe({ kind: 'obj', sourcePath: objPath }),
        });
        const fromGltf = await importer.importRecipe({
            projectRoot,
            recipe: recipe({ kind: 'gltf', sourcePath: glbPath }),
        });

        assert.deepEqual(fromObj.geometry, fromGltf.geometry);
        assert.deepEqual(fromObj.materialSlots, [{ id: 'body' }]);
        assert.deepEqual(fromGltf.materialSlots, [{ id: 'body' }]);
        assert.equal(fromObj.geometry.groups[0].materialSlot, 'body');
        assert.equal(fromGltf.geometry.groups[0].materialSlot, 'body');
    } finally {
        fs.rmSync(projectRoot, { recursive: true, force: true });
    }
});

test('source material renames are repaired by the import recipe without changing Model semantics', async () => {
    const projectRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'thestra-model-slot-'));
    try {
        const sourcePath = 'assets/models/Árvore renamed fixture.glb';
        await writeGlb(projectRoot, sourcePath, { materialName: 'BlenderMaterial.042' });
        const bundle = await importer.importRecipe({
            projectRoot,
            recipe: recipe({
                id: 'fixture.renamed',
                kind: 'gltf',
                sourcePath,
                sourceMaterial: 'BlenderMaterial.042',
            }),
        });
        assert.equal(bundle.modelId, 'fixture.renamed');
        assert.equal(bundle.geometry.groups[0].materialSlot, 'body');
        assert.equal(bundle.materialSlots[0].id, 'body');
        assert.equal(JSON.stringify(bundle.materialSlots).includes('BlenderMaterial.042'), false);
        assert.equal(bundle.source.path, sourcePath);
        assert.equal(bundle.source.path.includes(projectRoot), false, 'bundle provenance must never serialize absolute machine paths');
    } finally {
        fs.rmSync(projectRoot, { recursive: true, force: true });
    }
});

test('static Model import is deterministic for source bytes + recipe', async () => {
    const projectRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'thestra-model-determinism-'));
    try {
        const sourcePath = 'assets/models/static.glb';
        await writeGlb(projectRoot, sourcePath);
        const authored = recipe({ kind: 'gltf', sourcePath });
        const first = await importer.importRecipe({ projectRoot, recipe: authored });
        const second = await importer.importRecipe({ projectRoot, recipe: authored });
        assert.equal(contract.serialize(first), contract.serialize(second));
        assert.match(first.provenance.recipeSha256, /^[0-9a-f]{64}$/);
    } finally {
        fs.rmSync(projectRoot, { recursive: true, force: true });
    }
});

test('unsupported source semantics fail at the import boundary instead of leaking to consumers', async () => {
    const projectRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'thestra-model-negative-'));
    try {
        const animated = 'assets/models/animated.glb';
        await writeGlb(projectRoot, animated, { animated: true });
        await assert.rejects(
            importer.importRecipe({ projectRoot, recipe: recipe({ kind: 'gltf', sourcePath: animated }) }),
            /does not accept animation/,
        );

        const mirrored = 'assets/models/mirrored.glb';
        await writeGlb(projectRoot, mirrored, { mirrored: true });
        await assert.rejects(
            importer.importRecipe({ projectRoot, recipe: recipe({ kind: 'gltf', sourcePath: mirrored }) }),
            /mirrored transform/,
        );

        const unmapped = 'assets/models/unmapped.glb';
        await writeGlb(projectRoot, unmapped, { materialName: 'unexpected' });
        await assert.rejects(
            importer.importRecipe({ projectRoot, recipe: recipe({ kind: 'gltf', sourcePath: unmapped }) }),
            /has no materialSlot mapping/,
        );
    } finally {
        fs.rmSync(projectRoot, { recursive: true, force: true });
    }
});

test('recipe validation rejects unstable or ambiguous source vocabulary', () => {
    assert.throws(() => contract.validateRecipe('fixture.bad', {
        id: 'fixture.bad',
        source: { kind: 'obj', path: '../escape.obj' },
        sourceUnitsToMapCells: 1,
        materialSlots: { body: { sourceMaterials: ['body'] } },
    }), /must not escape/);

    assert.throws(() => contract.validateRecipe('fixture.bad', {
        id: 'fixture.bad',
        source: { kind: 'obj', path: 'assets/a.obj' },
        sourceUnitsToMapCells: 1,
        materialSlots: {
            one: { sourceMaterials: ['same'] },
            two: { sourceMaterials: ['same'] },
        },
    }), /maps to both/);
});
