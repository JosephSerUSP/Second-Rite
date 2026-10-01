"""Cull proof: inverted closed bodies and untagged open doorway sheets."""
import sys
from pathlib import Path
import bpy, bmesh
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import mesh_export_geometry as geometry
import export_exterior_environment as exporter

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_cube_add()
mesh = bpy.context.object.data
bm = bmesh.new(); bm.from_mesh(mesh)
bmesh.ops.reverse_faces(bm, faces=list(bm.faces)); bm.to_mesh(mesh); bm.free()
assert not geometry.prepare(mesh)
bm = bmesh.new(); bm.from_mesh(mesh)
assert bm.calc_volume(signed=True) > 0; bm.free()
assert exporter.cull_enclosed(bpy.context.object, 24, 0) == 0
for faces in ([(0,1,2,3)], [(0,1,2,3),(3,2,1,0)]):
    sheet = bpy.data.meshes.new('untagged portal sheet')
    sheet.from_pydata([(4,0,0),(4,0,2),(4,2,2),(4,2,0)], [], faces)
    assert geometry.prepare(sheet), 'open/zero-volume surface classified as a closed body'
    obj = bpy.data.objects.new('portal sheet', sheet); bpy.context.scene.collection.objects.link(obj)
    marks = sheet.attributes.new(exporter.OPEN_FACE_ATTRIBUTE, 'BOOLEAN', 'FACE')
    marks.data.foreach_set('value', [True]*len(sheet.polygons))
    assert exporter.cull_enclosed(obj, 24, 0) == 0
    assert len(sheet.polygons) == len(faces)
print('EXPORT GEOMETRY OK')

# A source batch must preserve placement and named UVs, and explicitly replace
# object-local shader coordinates rather than stretching textures across town.
import cycles_source
collection=bpy.data.collections.new('TH_SOURCE');bpy.context.scene.collection.children.link(collection)
source=bpy.context.scene.objects[0]
for owner in list(source.users_collection): owner.objects.unlink(source)
collection.objects.link(source)
source.location=(3,4,5)
uv=source.data.uv_layers.new(name='UpstreamUV')
uv.data.foreach_set('uv',[0.25,0.75]*len(source.data.loops))
material=bpy.data.materials.new('local coordinates');material.use_nodes=True
coords=material.node_tree.nodes.new('ShaderNodeTexCoord')
noise=material.node_tree.nodes.new('ShaderNodeTexNoise')
material.node_tree.links.new(coords.outputs['Generated'],noise.inputs['Vector'])
source.data.materials.append(material)
bpy.context.view_layer.update()
expected=[tuple(source.matrix_world@v.co) for v in source.data.vertices]
batch,count=cycles_source.batch_source(collection)
assert count==1 and [tuple(v.co) for v in batch.data.vertices]==expected
assert 'UpstreamUV' in batch.data.uv_layers
assert all(abs(v.uv.x-.25)<1e-6 and abs(v.uv.y-.75)<1e-6 for v in batch.data.uv_layers['UpstreamUV'].data)
vector=batch.data.materials[0].node_tree.nodes.get(noise.name).inputs['Vector']
assert vector.links[0].from_node.attribute_name=='sr_source_generated'
print('SOURCE COORDINATES OK')

# Explicit structural receivers survive the optimization even when embedded
# in overlapping masonry. They remain closed occluders, not fake open sheets.
bm=bmesh.new();bmesh.ops.create_cube(bm,size=4);bmesh.ops.create_cube(bm,size=2)
embedded=bpy.data.meshes.new('nested boxes');bm.to_mesh(embedded);bm.free()
obj=bpy.data.objects.new('nested structural control',embedded);bpy.context.scene.collection.objects.link(obj)
control=obj.copy();control.data=embedded.copy();bpy.context.scene.collection.objects.link(control)
assert exporter.cull_enclosed(control,24,0)==6
keep=embedded.attributes.new('sr_bake_preserve_face','BOOLEAN','FACE')
keep.data.foreach_set('value',[False]*6+[True]*6)
assert exporter.cull_enclosed(obj,24,0)==0 and len(embedded.polygons)==12
print('STRUCTURAL RECEIVER PRESERVED')

# A roof whose own centre is outside the envelope belongs with its admitted wall.
from recipes.first_stratum.common import box
import second_rite_asset_core as core
bpy.ops.wm.read_factory_settings(use_empty=True)
root=bpy.data.objects.new('Building volume',None);bpy.context.scene.collection.objects.link(root);root['building_volume']='{}'
wall=box('Near wall',root,(1,2,3),(0,17,1.5),None,core)
roof=box('Connected roof',root,(3,8,.2),(0,20,3.1),None,core)
for obj in [wall,roof]:obj['sr_bake_source']=True
far=bpy.data.objects.new('Parked volume',None);bpy.context.scene.collection.objects.link(far);far['building_volume']='{}'
spare=box('Parked wall',far,(1,2,3),(0,-30,1.5),None,core);spare['sr_bake_source']=True
bpy.context.view_layer.update()
assert not exporter.in_square(roof,12,6), 'Negative control must reproduce per-object rejection'
admitted=exporter.admitted_names([wall,roof,spare],12,6)
assert wall.name in admitted and roof.name in admitted, 'Building was admitted as a fragment'
assert spare.name not in admitted, 'Unrelated off-range volume entered the package'

# A small intersecting box covers the face centre but not the exterior corners.
from recipes.first_stratum.common import box_geometry
import bake_correspondence
outer_v,outer_f=box_geometry((4,4,4));small_v,small_f=box_geometry((.4,.5,.5))
small_v=[(x-2,y,z) for x,y,z in small_v]
data=bpy.data.meshes.new('Partly covered exterior');data.from_pydata(outer_v+small_v,[],outer_f+[tuple(i+8 for i in f) for f in small_f]);data.update()
tag=data.attributes.new(bake_correspondence.OWNER_ATTRIBUTE,'INT','FACE');tag.data.foreach_set('value',[0]*6+[1]*6)
obj=bpy.data.objects.new('Partly covered exterior',data);bpy.context.scene.collection.objects.link(obj)
exporter.cull_enclosed(obj,24,0)
assert any(face.normal.x<-.99 and abs(face.center.x+2)<1e-5 and face.area>15 for face in data.polygons), 'A partially covered exterior face was deleted'
print('ASSEMBLY AND PARTIAL COVERAGE PROOF OK')

long=box('Loose boundary crossing view',None,(1,18,.5),(0,-8,.25),None,core)
long['sr_bake_source']=True
bpy.context.view_layer.update()
assert not exporter.in_square(long,12,6)
assert long.name in exporter.admitted_names([long,spare],12,6)
assert spare.name not in exporter.admitted_names([long,spare],12,6)
print('LOOSE BOUNDARY INTERSECTION OK')
