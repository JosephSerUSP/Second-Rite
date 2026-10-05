'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');
const { importRecipe } = require('./import-model');
const contract = require('./model-contract');
const { compileModels } = require('./compile-models');

test('an empty Model registry stages a valid empty manifest', async () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'thestra-empty-model-test-'));
    try {
        fs.mkdirSync(path.join(root, 'data'));
        fs.writeFileSync(path.join(root, 'data/models.json'), '{}');
        const manifest = await compileModels(root);
        assert.deepEqual(manifest, { version: 1, models: {}, sourcePaths: {} });
        assert.deepEqual(JSON.parse(fs.readFileSync(path.join(root, 'assets/generated/models/manifest.json'))), manifest);
    } finally { fs.rmSync(root, { recursive: true, force: true }); }
});

test('native MTL source projection is deterministic and invalidates when an appearance dependency changes', async () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(),'thestra-appearance-test-'));
    try {
        fs.mkdirSync(path.join(root,'assets'),{recursive:true});
        fs.writeFileSync(path.join(root,'assets/source.obj'), 'mtllib source.mtl\nv 0 0 0\nv 1 0 0\nv 0 1 0\nusemtl source\nf 1 2 3\n');
        fs.writeFileSync(path.join(root,'assets/source.mtl'), 'newmtl source\nKd 0.2 0.4 0.6\npass sphere screen 0.5 overlay.png\n');
        fs.writeFileSync(path.join(root,'assets/overlay.png'), 'dependency bytes');
        const recipe = {id:'fixture.bound',source:{kind:'obj',path:'assets/source.obj'},sourceUnitsToMapCells:1,
            appearance:'obj-mtl',materialSlots:{body:{sourceMaterials:['source']}}};
        const a = await importRecipe({projectRoot:root,recipe});
        const b = await importRecipe({projectRoot:root,recipe});
        assert.equal(contract.serialize(a),contract.serialize(b));
        assert.deepEqual(a.materialSlots[0].appearance.color,[0.2,0.4,0.6,1]);
        assert.equal(a.materialSlots[0].appearance.passes[0].texture,'assets/overlay.png');
        assert.equal(a.materialSlots[0].appearance.passes[0].blendId,3);
        fs.writeFileSync(path.join(root,'assets/source.mtl'), 'newmtl source\nKd 0.6 0.4 0.2\n');
        const changed = await importRecipe({projectRoot:root,recipe});
        assert.deepEqual(a.geometry,changed.geometry);
        assert.equal(a.source.sha256,changed.source.sha256);
        assert.notDeepEqual(a.provenance.dependencies,changed.provenance.dependencies);
        assert.notEqual(contract.serialize(a),contract.serialize(changed));
        fs.writeFileSync(path.join(root,'assets/source.mtl'), 'newmtl other\nKd 1 1 1\n');
        await assert.rejects(importRecipe({projectRoot:root,recipe}),/no source material/);
    } finally { fs.rmSync(root,{recursive:true,force:true}); }
});
