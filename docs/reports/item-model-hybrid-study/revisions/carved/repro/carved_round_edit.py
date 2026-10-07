import bpy,bmesh,sys,json,math
from pathlib import Path
sys.path.insert(0,'tools/blender')
from surface_atlas import pixel_rectangle_uv,rectangle_uv
base=Path('docs/reports/item-model-hybrid-study').resolve();source=base/'revisions/carved/source-project/assets/authoring/items'
layout=json.loads((base/'actual-layout.json').read_text());bounds=pixel_rectangle_uv(layout['regions']['carved_outer']['pixels'],layout['imageSize'],inset=layout['insetPixels'])
for path in sorted(source.glob('*.blend')):
 bpy.ops.wm.open_mainfile(filepath=str(path));root=bpy.data.objects['ITEM_'+path.stem];assert not root.get('sr_rounding_revision')
 for side in ['left','right']:
  ob=bpy.data.objects['HULL_'+side];bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
  # Voxel remesh and relaxation resolve the saved angular intersections into
  # rounded bone masses. Original study controls remain preserved elsewhere.
  rem=ob.modifiers.new('Round saved carved cheek','REMESH');rem.mode='VOXEL';rem.voxel_size=.025;rem.use_smooth_shade=True;bpy.ops.object.modifier_apply(modifier=rem.name)
  sm=ob.modifiers.new('Relax carved cheeks','SMOOTH');sm.factor=.9;sm.iterations=14;bpy.ops.object.modifier_apply(modifier=sm.name)
  dec=ob.modifiers.new('Reduce rounded shell','DECIMATE');dec.ratio=.18;bpy.ops.object.modifier_apply(modifier=dec.name)
  bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(ob.data);bm.free();ob.data.update()
  for p in ob.data.polygons:p.use_smooth=True
  ranges=[(min(v.co[i] for v in ob.data.vertices),max(v.co[i] for v in ob.data.vertices)) for i in range(3)]
  uv=ob.data.uv_layers.new(name='UVMap')
  for p in ob.data.polygons:
   axes=sorted(range(3),key=lambda i:abs(p.normal[i]))[:2]
   for li in p.loop_indices:
    co=ob.data.vertices[ob.data.loops[li].vertex_index].co;vals=[(co[i]-ranges[i][0])/(ranges[i][1]-ranges[i][0]) for i in axes];uv.data[li].uv=rectangle_uv(*vals,bounds)
 root['sr_rounding_revision']='Voxelized saved cheek meshes at 0.025, 14 relaxation steps, 18 percent decimation; original silhouettes retained as historical study.'
 bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(path))
print('ROUNDING SAVED')
