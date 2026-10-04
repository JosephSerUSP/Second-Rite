"""Receiver association negative controls through the same sampled preflight."""
import sys,json,tempfile
from pathlib import Path
import bpy
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import bake_correspondence as check,cycles_source
bpy.ops.wm.read_factory_settings(use_empty=True)
collection=bpy.data.collections.new('TH_SOURCE');bpy.context.scene.collection.children.link(collection)
def plane(name,z,x=0):
    mesh=bpy.data.meshes.new(name)
    mesh.from_pydata([(x-1,-1,z),(x+1,-1,z),(x+1,1,z),(x-1,1,z)],[],[(0,1,2,3)]);mesh.update()
    obj=bpy.data.objects.new(name,mesh);bpy.context.scene.collection.objects.link(obj);return obj
for name,x in [('red source',0),('other source',4)]:
    obj=plane(name,0,x)
    bpy.context.scene.collection.objects.unlink(obj);collection.objects.link(obj)
batch,_=cycles_source.batch_source(collection)
target=plane('bound receiver',.02)
names=['bound receiver'];check.tag(target.data,target.name,names);target[check.OWNER_RECORD]=json.dumps(names)
with tempfile.TemporaryDirectory() as directory:
    path=Path(directory)/'binding.json'
    def contract(expected):
        path.write_text(json.dumps({'schemaVersion':1,'bindings':[{'receiver':target.name,'sources':[expected],'normal':[0,0,1]}]}))
    contract('red source')
    result=check.validate(batch,target,path,extrusion=.15,ray_distance=1)
    assert result['bindings'][0]['samples']==8 and not result['errors']
    contract('other source')
    try:check.validate(batch,target,path,extrusion=.15,ray_distance=1)
    except ValueError as error:assert 'wrong-source' in str(error) and 'red source' in str(error)
    else:raise AssertionError('wrong association passed')
    contract('red source');target.location.x=8;bpy.context.view_layer.update()
    try:check.validate(batch,target,path,extrusion=.15,ray_distance=1)
    except ValueError as error:assert 'missing' in str(error)
    else:raise AssertionError('missing receiver coverage passed')
    target.location.x=0;bpy.context.view_layer.update();target[check.OWNER_RECORD]=json.dumps(['different receiver'])
    try:check.validate(batch,target,path,extrusion=.15,ray_distance=1)
    except ValueError as error:assert 'receiver missing' in str(error)
    else:raise AssertionError('removed receiver passed')
print('BAKE CORRESPONDENCE OK')
