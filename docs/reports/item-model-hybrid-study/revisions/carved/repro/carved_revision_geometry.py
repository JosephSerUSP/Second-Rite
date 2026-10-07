"""Derive a study revision by editing the saved hull, not regenerating it."""
import bpy,bmesh,json,sys,hashlib,math,shutil
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,'tools/blender');import item_kit as kit
from path_sweep import sweep_tube,transported_frames
from surface_atlas import pixel_rectangle_uv,rectangle_uv
BASE=Path('docs/reports/item-model-hybrid-study').resolve();OUT=BASE/'revisions/carved';PROJECT=OUT/'source-project';SOURCE=PROJECT/'assets/authoring/items';SOURCE.mkdir(parents=True,exist_ok=True);(SOURCE/'_textures').mkdir(exist_ok=True);(PROJECT/'data').mkdir(exist_ok=True)
(PROJECT/'data/README.md').write_text('Compile-only study revision, no shipping gameplay data.\n')
path=BASE/'source-project/assets/authoring/items/hybrid_carved_hull.blend';before=hashlib.sha256(path.read_bytes()).hexdigest()
geometry_path=SOURCE/'carved_capsule_geometry.blend';baked_path=SOURCE/'carved_capsule_baked.blend'
assert not baked_path.exists(),'Saved bake revisions require direct edits'
assert '--edit-saved' in sys.argv and geometry_path.exists(),'Resume explicitly from saved source'
bpy.ops.wm.open_mainfile(filepath=str(geometry_path));root=bpy.data.objects['ITEM_carved_capsule_geometry']
assert 'sr_geometry_revision' not in root,'Geometry revision already applied'
changes=[];layout=json.loads((BASE/'actual-layout.json').read_text());bounds={k:pixel_rectangle_uv(v['pixels'],layout['imageSize'],inset=layout['insetPixels']) for k,v in layout['regions'].items()}
materials={role:bpy.data.materials['hybrid_carved_hull_'+role] for role in ['outer','core','binding','spine']}

def apply_mods(ob):
 if ob.data.users>1:ob.data=ob.data.copy()
 bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
 for m in list(ob.modifiers):bpy.ops.object.modifier_apply(modifier=m.name)

def recalc(ob):
 bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(ob.data);bm.free();ob.data.update()

def tube(name,points,radius,mat,role=None,segments=8):
 v,f,uv,smooth=sweep_tube(points,[radius]*len(points),segments=segments)
 if role:uv=[[rectangle_uv(u,t,bounds['carved_'+role]) for u,t in row] for row in uv]
 ob=kit.mesh_object(name,v,f,root,mat,uvs=uv);recalc(ob)
 for p,flag in zip(ob.data.polygons,smooth):p.use_smooth=flag
 return ob

# Edit existing front masks and depth envelopes. They remain saved in the
# original source; this finalized revision resolves them to editable meshes.
left=[(-1.20,-1.27),(-.96,-1.56),(-.58,-1.24),(-.55,-1.01),(-.85,-.62),(-.97,-.13),(-.90,.32),(-.97,.84),(-.75,1.25),(-.37,1.52),(-.41,1.89),(-.91,1.83),(-1.28,1.49),(-1.48,.88),(-1.33,.38),(-1.48,-.33)]
front=bpy.data.objects['SHADOW_HULL_left_front'];assert len(front.data.vertices)==len(left)
for v,(x,z) in zip(front.data.vertices,left):v.co.x=x;v.co.z=z
for side in ['left','right']:
 mask=bpy.data.objects['SHADOW_HULL_'+side+'_side'];ys=[-.98,-1.0,-.97,-.92,.08,.53,.51] if side=='left' else [-.91,-.93,-.87,-.8,.16,.5,.54]
 assert len(mask.data.vertices)==len(ys)
 for v,y in zip(mask.data.vertices,ys):v.co.y=y
 top=bpy.data.objects['SHADOW_HULL_'+side+'_top']
 for i,v in enumerate(top.data.vertices):v.co.y=-1.08 if i<2 else .64
 for m in bpy.data.objects['HULL_'+side].modifiers:
  if m.type=='BEVEL':m.width=.105;m.segments=4
 for control in [front,mask,top]:control.data.update();control.update_tag()
bpy.context.view_layer.update()
for side in ['left','right']:
 ob=bpy.data.objects['HULL_'+side];apply_mods(ob)
 xs=[v.co.x for v in ob.data.vertices];cx=(max(xs)+min(xs))/2;half=(max(xs)-min(xs))/2
 for v in ob.data.vertices:
  crown=max(0,1-((v.co.x-cx)/half)**2)
  v.co.y+=(-.12 if v.co.y<-.2 else .07)*crown
 recalc(ob)
 for p in ob.data.polygons:p.use_smooth=True
 ob.data.set_sharp_from_angle(angle=.8)
 changes.append(ob.name+': deeper 3D envelope, convex crown and rounder cut edges')

# Round the saved loft rather than substitute a new primitive.
core=bpy.data.objects['CORE_OrganicVolume']
for v in core.data.vertices:v.co.z=(v.co.z+.16)*.76-.14;v.co.x=(v.co.x-.19)*1.09+.15;v.co.y=(v.co.y+.04)*1.16-.03
sub=core.modifiers.new('Round existing organic loft','SUBSURF');sub.levels=1;sub.render_levels=1;apply_mods(core)
for p in core.data.polygons:p.use_smooth=True
changes.append('CORE_OrganicVolume: shorter, rounder saved loft with subdivision')
for ob in list(root.children_recursive):
 if ob.name.startswith('FASTENER_'):bpy.data.objects.remove(ob,do_unlink=True)
changes.append('Removed four invented screw-like fasteners from bone assembly')

# A real shallow channel over the exposed crest adds contour and a recess
# which will cast directionless cavity/contact shading in the bake.
left_body=bpy.data.objects['HULL_left']
cut=tube('CONTROL_CrestChannel',[(-1.35,-1.10,.89),(-1.20,-1.14,1.23),(-.89,-1.14,1.57),(-.60,-1.09,1.72)],(.04,.04),materials['outer'],segments=10)
mod=kit.boolean_difference(left_body,cut);mod.name='Incised upper crest channel';apply_mods(left_body);cut.hide_render=True;cut.display_type='WIRE';recalc(left_body)
changes.append('Upper crest carries an actual shallow carved channel')

# Cloth should have sewn edges and rounded relief instead of a featureless slab.
front_binding=bpy.data.objects['BINDING_FrontDiagonal'];points=json.loads(front_binding['sr_path_controls']);frames=transported_frames(points)
for side,sign in [('A',-1),('B',1)]:
 edge=[tuple(Vector(p)+Vector(b)*(.205*sign)-Vector(n)*.046) for p,(t,n,b) in zip(points,frames)]
 tube('BINDING_Selvage_'+side,edge, (.024,.024),materials['binding'],'binding',8)
thread=kit.material('carved_revision_thread',color=(.7,.66,.44));thread['sr_finish_role']='thread'
for segment,(a,b) in enumerate(zip(points,points[1:])):
 for frac in [.22,.65]:
  p=Vector(a).lerp(Vector(b),frac);t,n,binormal=frames[segment];p-=Vector(n)*.06
  for sign in [-1,1]:
   centre=p+Vector(binormal)*(.185*sign);tube(f'STITCH_{segment}_{frac}_{sign}',[tuple(centre-Vector(binormal)*.045),tuple(centre+Vector(binormal)*.045)],(.012,.012),thread,segments=6)
changes.append('Raised cloth selvages and 16 physical edge stitches')

# Match overall front height/width while retaining the thicker side construction.
bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();pts=[]
for ob in root.children_recursive:
 if ob.hide_render or ob.type!='MESH':continue
 ev=ob.evaluated_get(dg);m=ev.to_mesh();pts.extend(ev.matrix_world@v.co for v in m.vertices);ev.to_mesh_clear()
spans=[max(p[i] for p in pts)-min(p[i] for p in pts) for i in range(3)];target=json.loads((BASE/'calibration.json').read_text())['carved']['targetDimensions']
root.scale=tuple(root.scale[i]*target[i]/spans[i] for i in range(3));root['sr_geometry_revision']=json.dumps(changes);root['sr_visual_acceptance']='owner review open; no technical pass establishes art approval'
for image in bpy.data.images:
 if image.source=='FILE':image.filepath='//_textures/hybrid_surface_atlas.png'
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(geometry_path))
geometry_hash=hashlib.sha256(geometry_path.read_bytes()).hexdigest()
# Separate authored bake revision from the recorded geometry-only control.
root.name='ITEM_carved_capsule_baked';root['item_export_name']='carved_capsule_baked';kit.core.tag_asset_target(root,asset_id='carved_capsule_baked',representation='full_model',role='item_display',authoring_space='item_display',placement_frame='item_viewport')
root['sr_geometry_control_sha256']=geometry_hash;bpy.ops.wm.save_as_mainfile(filepath=str(baked_path))
assert before==hashlib.sha256(path.read_bytes()).hexdigest()
(OUT/'geometry-revision.json').write_text(json.dumps({'baseSourceSHA256':before,'geometryControlSHA256':geometry_hash,'changes':changes,'bakedSourceBeforeSurfaceBakeSHA256':hashlib.sha256(baked_path.read_bytes()).hexdigest(),'boundary':'Derived by opening and editing saved hull geometry; original six study sources unchanged. Overall envelope matched, individual components deliberately changed.'},indent=2)+'\n')
print('CARVED GEOMETRY REVISION SAVED; original source unchanged')
