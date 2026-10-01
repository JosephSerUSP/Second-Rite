"""Inspect receiver admission/culling and geometric source correspondence without saving.

This is a bounded diagnostic study, not an exhaustive bake acceptance gate.
"""
import bpy,json,sys,collections,argparse,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'tools/blender'))
parser=argparse.ArgumentParser(description='Read-only courtyard-style receiver admission, culling and centroid ray study. Legacy atlas layout.')
parser.add_argument('--source',type=Path,required=True);parser.add_argument('--package',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
parser.add_argument('--span',type=float,default=12);parser.add_argument('--margin',type=float,default=6)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:]);args.out.mkdir(parents=True,exist_ok=True)
before=hashlib.sha256(args.source.read_bytes()).hexdigest()
import export_exterior_environment as exporter,bake_correspondence,mesh_export_geometry
bpy.ops.wm.open_mainfile(filepath=str(args.source.resolve()))
source=list(bpy.data.collections['TH_SOURCE'].all_objects);graph=bpy.context.evaluated_depsgraph_get();verts=[];faces=[];owners=[]
for obj in source:
 if obj.type!='MESH' or obj.get('sr_bake_role')=='receiver':continue
 evaluated=obj.evaluated_get(graph);mesh=evaluated.to_mesh();mesh_export_geometry.prepare(mesh);mesh.calc_loop_triangles();offset=len(verts)
 verts.extend(obj.matrix_world@v.co for v in mesh.vertices);faces.extend(tuple(offset+i for i in tri.vertices) for tri in mesh.loop_triangles);owners.extend([obj.name]*len(mesh.loop_triangles));evaluated.to_mesh_clear()
bvh=BVHTree.FromPolygons(verts,faces,all_triangles=True)
admitted=exporter.admitted_names(source,args.span,args.margin)
result={'excludedByAdmission':[o.name for o in source if o.type=='MESH' and o.get('sr_bake_role')!='source' and o.name not in admitted], 'objectCentreRejected':[o.name for o in source if o.type=='MESH' and o.get('sr_bake_role')!='source' and not exporter.in_square(o,args.span,args.margin)]}
original=exporter.cull_enclosed
names=[]
def snapshot(target):
 names=json.loads(target[bake_correspondence.OWNER_RECORD]);attr=target.data.attributes[bake_correspondence.OWNER_ATTRIBUTE]
 counter=collections.Counter();front=collections.Counter()
 for face in target.data.polygons:
  owner=names[attr.data[face.index].value];counter[owner]+=1
  if face.normal.x<-.7:front[owner]+=1
 return {'faces':dict(counter),'frontFaces':dict(front)}
def counted(target,*args):
 result['beforeCull']=snapshot(target);count=original(target,*args);result['afterCull']=snapshot(target);return count
exporter.cull_enclosed=counted
manifest=json.loads((args.package/'environment.json').read_text(encoding='utf-8'))
size=manifest['stats']['textureDimensions'][0]
exporter.rebuild_render_mesh(args.span,args.margin,.03,24,0,clip_ground=None,layout='legacy',atlas_size=size)
if manifest['provenance']['bake'].get('texelAlignment',{}).get('method','none')!='none':
 import atlas_denoise
 result['texelAlignment']=atlas_denoise.snap_to_texels(bpy.context.view_layer.objects.active.data,size)
target=bpy.context.view_layer.objects.active;names=json.loads(target[bake_correspondence.OWNER_RECORD]);attr=target.data.attributes[bake_correspondence.OWNER_ATTRIBUTE];target.data.calc_loop_triangles();rows={}
for tri in target.data.loop_triangles:
 face=target.data.polygons[tri.polygon_index];name=names[attr.data[tri.polygon_index].value]
 if not any(token in name for token in ['street','casement','portal']):continue
 point=sum((target.data.vertices[i].co for i in tri.vertices),Vector())/3;normal=face.normal
 hit,_,index,distance=bvh.ray_cast(point+normal*.15,-normal,1)
 row=rows.setdefault(name,{'triangles':0,'missing':0,'hits':collections.Counter(),'examples':[]});row['triangles']+=1
 if index is None:row['missing']+=1
 else:row['hits'][owners[index]]+=1
 if index is None or owners[index]!=name:
  if len(row['examples'])<3:row['examples'].append({'point':list(point),'normal':list(normal),'hit':owners[index] if index is not None else None})
for row in rows.values():row['hits']=dict(row['hits'])
result['rays']=rows
image=bpy.data.images.load(str(args.package.resolve()/'environment.png'));pixels=list(image.pixels);width,height=image.size;uv=target.data.uv_layers.active.data;dark=[]
for tri in target.data.loop_triangles:
 texture=sum((uv[i].uv for i in tri.loops),Vector((0,0)))/3
 x=min(width-1,max(0,int(texture.x*width)));y=min(height-1,max(0,int(texture.y*height)));rgb=pixels[(y*width+x)*4:(y*width+x)*4+3]
 if max(rgb)>.004:continue
 face=target.data.polygons[tri.polygon_index];name=names[attr.data[tri.polygon_index].value];point=sum((target.data.vertices[i].co for i in tri.vertices),Vector())/3
 _,hitnormal,index,distance=bvh.ray_cast(point+face.normal*.15,-face.normal,1)
 dark.append({'owner':name,'point':list(point),'normal':list(face.normal),'rgb':rgb,'hit':owners[index] if index is not None else None,'normalAgreement':face.normal.dot(hitnormal) if hitnormal else None})
result['darkSamples']=dark
import atlas_allocation
result['rasterizedUVCoverage']=float(atlas_allocation.triangle_mask(target.data,width).mean())
result['sourceSHA256']=before
result['interpretation']='Centroid probes on a legacy-layout reconstructed receiver mesh; geometric hits are not Cycles texel-shading proof. Some dark samples are legitimate undersides/interiors. Package atlas values are useful only with the same source, layout and export settings.'
assert hashlib.sha256(args.source.read_bytes()).hexdigest()==before
(args.out/'receivers.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print('RECEIVER AUDIT OK')
