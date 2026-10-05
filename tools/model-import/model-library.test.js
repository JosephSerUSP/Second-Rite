'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { Document, NodeIO } = require('@gltf-transform/core');
const { createModelLibrary } = require('../../studio/editor/model-library');

const source = 'mtllib paint.mtl\nusemtl Bronze\nv 0 0 0\nv 1 0 0\nv 0 0 1\nf 1 2 3\n';
function fixture(t) {
    const root=fs.mkdtempSync(path.join(os.tmpdir(),'thestra-model-library-'));
    t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
    fs.mkdirSync(path.join(root,'data'));
    fs.mkdirSync(path.join(root,'assets/models'),{recursive:true});
    fs.writeFileSync(path.join(root,'assets/models/prop.obj'),source);
    fs.writeFileSync(path.join(root,'assets/models/paint.mtl'),'newmtl Bronze\nKd 0.8 0.5 0.2\n');
    fs.writeFileSync(path.join(root,'data/models.json'),'{}\n');
    return {root,library:createModelLibrary(root)};
}
async function proposal(library) {
    const {recipe}=await library.prepare({id:'prop.proof',source:{kind:'obj',path:'assets/models/prop.obj'}});
    // Slot names and Surface bindings are authored identity, not source names.
    recipe.materialSlots={finish:{sourceMaterials:['Bronze']}};
    return {recipe,version:library.read().version,originalId:null};
}
test('source discovery and preview are read-only; reviewed creation writes only one Model record',async t=>{
    const {root,library}=fixture(t);
    const bytes=fs.readFileSync(path.join(root,'data/models.json'),'utf8');
    const request=await proposal(library);
    request.recipe.sourceUnitsToMapCells=0.125;
    const result=await library.preview(request);
    assert.equal(result.summary.bounds.maxX,0.125);
    assert.equal(result.renderable,true);
    assert.equal(result.bundle.materialSlots[0].id,'finish');
    assert.equal(fs.readFileSync(path.join(root,'data/models.json'),'utf8'),bytes);
    await assert.rejects(library.save(request),/Preview this Model/);
    const saved=await library.save({...request,token:result.token});
    assert.equal(saved.records['prop.proof'].sourceUnitsToMapCells,0.125);
    assert.deepEqual(saved.records['prop.proof'].materialSlots,request.recipe.materialSlots);
});
test('reimport reads changed bytes at the same filename and retains authored identity and slot mappings',async t=>{
    const {root,library}=fixture(t);
    const initial=await proposal(library);
    const first=await library.preview(initial);
    await library.save({...initial,token:first.token});
    const loaded=library.read();
    fs.writeFileSync(path.join(root,'assets/models/prop.obj'),source.replace('v 1 0 0','v 2 0 0'));
    const request={recipe:loaded.records['prop.proof'],originalId:'prop.proof',version:loaded.version};
    const second=await library.preview(request);
    assert.notEqual(second.token,first.token);
    assert.equal(second.summary.bounds.maxX,2);
    const saved=await library.save({...request,token:second.token});
    assert.deepEqual(saved.records['prop.proof'].materialSlots,{finish:{sourceMaterials:['Bronze']}});
    await assert.rejects(library.preview({...request,version:saved.version,recipe:{...request.recipe,id:'renamed'}}),/cannot rename/);
});
test('source, material dependency, recipe and registry changes after preview reject save without overwriting',async t=>{
    const {root,library}=fixture(t);
    const request=await proposal(library);
    const reviewed=await library.preview(request);
    const baseline=fs.readFileSync(path.join(root,'data/models.json'),'utf8');
    await assert.rejects(library.save({...request,token:reviewed.token,recipe:{...request.recipe,sourceUnitsToMapCells:2}}),/changed after preview/);
    fs.appendFileSync(path.join(root,'assets/models/prop.obj'),'# new revision\n');
    await assert.rejects(library.save({...request,token:reviewed.token}),/changed after preview/);
    fs.writeFileSync(path.join(root,'assets/models/prop.obj'),source);
    fs.appendFileSync(path.join(root,'assets/models/paint.mtl'),'Kd 0.2 0.4 0.6\n');
    await assert.rejects(library.save({...request,token:reviewed.token}),/changed after preview/);
    assert.equal(fs.readFileSync(path.join(root,'data/models.json'),'utf8'),baseline);
    fs.appendFileSync(path.join(root,'data/models.json'),'\n');
    await assert.rejects(library.save({...request,token:reviewed.token}),/registry changed/);
});
test('missing source mappings fail visibly; geometry-only Surface references remain authored without fake realization',async t=>{
    const {root,library}=fixture(t);
    const request=await proposal(library);
    fs.writeFileSync(path.join(root,'assets/models/prop.obj'),source.replace('usemtl Bronze','usemtl NewMaterial'));
    await assert.rejects(library.preview(request),/NewMaterial.*no materialSlot mapping/);
    fs.writeFileSync(path.join(root,'assets/models/prop.obj'),source);
    delete request.recipe.appearance;
    request.recipe.materialSlots.finish.surface='surfaces/bronze';
    const reviewed=await library.preview(request);
    assert.equal(reviewed.renderable,false);
    const saved=await library.save({...request,token:reviewed.token});
    assert.equal(saved.records['prop.proof'].materialSlots.finish.surface,'surfaces/bronze');
});
test('new imports cannot overwrite an existing identity or ambiguously bind an existing source',async t=>{
    const {library}=fixture(t);
    const request=await proposal(library);
    const reviewed=await library.preview(request);
    await library.save({...request,token:reviewed.token});
    await assert.rejects(proposal(library),/already exists/);
    await assert.rejects(library.prepare({id:'other',source:request.recipe.source}),/already bound/);
});
test('a Project without models.json can register its first reviewed Model',async t=>{
    const {root,library}=fixture(t);
    fs.unlinkSync(path.join(root,'data/models.json'));
    const request=await proposal(library);
    assert.equal(request.version,'absent');
    const reviewed=await library.preview(request);
    assert.equal((await library.save({...request,token:reviewed.token})).id,'prop.proof');
});
test('external glTF geometry dependencies participate in reimport review identity',async t=>{
    const {root,library}=fixture(t);
    const document=new Document();
    const buffer=document.createBuffer();
    const positions=document.createAccessor().setType('VEC3').setArray(new Float32Array([0,0,0,1,0,0,0,1,0])).setBuffer(buffer);
    const primitive=document.createPrimitive().setAttribute('POSITION',positions);
    const mesh=document.createMesh().addPrimitive(primitive);
    document.createScene().addChild(document.createNode().setMesh(mesh));
    await new NodeIO().write(path.join(root,'assets/models/prop.gltf'),document);
    const {recipe}=await library.prepare({id:'gltf.proof',source:{kind:'gltf',path:'assets/models/prop.gltf'}});
    const request={recipe,version:library.read().version};
    const reviewed=await library.preview(request);
    assert.equal(reviewed.bundle.provenance.dependencies.length,1);
    const dependency=path.join(root,reviewed.bundle.provenance.dependencies[0].path);
    const bytes=fs.readFileSync(dependency); bytes.writeFloatLE(2,12); fs.writeFileSync(dependency,bytes);
    await assert.rejects(library.save({...request,token:reviewed.token}),/changed after preview/);
});
