"""Receiver-only Cycles regression with immutable source image negative control."""
import bpy,sys,tempfile,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools/blender'))
import town_environment_pipeline as pipeline
bpy.ops.wm.read_factory_settings(use_empty=True)
for name in ['TH_SOURCE','TH_RENDER','TH_ANCHORS']:
    collection=bpy.data.collections.new(name);bpy.context.scene.collection.children.link(collection)
def plane(name,z,collection):
    data=bpy.data.meshes.new(name);data.from_pydata([(-1,-1,z),(1,-1,z),(1,1,z),(-1,1,z)],[],[(0,1,2,3)]);data.update()
    uv=data.uv_layers.new(name='UVMap');uv.data.foreach_set('uv',[0,0,1,0,1,1,0,1])
    obj=bpy.data.objects.new(name,data);bpy.data.collections[collection].objects.link(obj);return obj
source=plane('Red source',0,'TH_SOURCE')
material=bpy.data.materials.new('Source');material.use_nodes=True
nodes=material.node_tree.nodes;nodes.clear();emission=nodes.new('ShaderNodeEmission');emission.inputs['Color'].default_value=(1,0,0,1)
output=nodes.new('ShaderNodeOutputMaterial');material.node_tree.links.new(emission.outputs[0],output.inputs['Surface'])
image=bpy.data.images.new('Upstream sentinel',4,4);image.generated_color=(0,0,1,1)
texture=nodes.new('ShaderNodeTexImage');texture.image=image;nodes.active=texture
source.data.materials.append(material);before=list(image.pixels)
receiver=plane('Proxy must never be baked as source',.01,'TH_SOURCE');receiver['sr_bake_role']='receiver'
green=material.copy();green.node_tree.nodes.get(emission.name).inputs['Color'].default_value=(0,1,0,1);receiver.data.materials.append(green)
target=plane('Actual receiver',.02,'TH_RENDER')
with tempfile.TemporaryDirectory() as directory:
    pipeline.run_pipeline_in_blender(Path('test.blend'),Path(directory),atlas_size=32,bake_samples=1,backend='cycles',cycles_device='CPU')
    assert (Path(directory)/'environment.png').is_file()
    manifest=json.loads((Path(directory)/'environment.json').read_text())
    assert manifest['provenance']['bake']=={'backend':'cycles','device':'CPU','samples':1,'selectedToActive':True}
    atlas=bpy.data.images['environment_atlas'];pixels=list(atlas.pixels);index=(16*32+16)*4
    assert pixels[index]>.8 and pixels[index+1]<.1,'Receiver proxies contaminated the red source bake'
    assert list(image.pixels)==before,'Baking overwrote an upstream source image'
print('CYCLES SURFACE BAKE OK')
