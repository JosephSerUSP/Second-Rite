"""Reusable Blender binding for NEW painted silhouette scaffolds; never resaves a source."""
from pathlib import Path
import sys,json
import bmesh
import bpy

HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import item_kit as kit


def create_relief(name,mesh,root,front_material,edge_material):
    """Bind host-produced mesh data; Blender requires no Pillow dependency."""
    ob=kit.mesh_object(name,mesh['vertices'],mesh['faces'],root,front_material,uvs=mesh['uvs'])
    ob.data.materials.append(edge_material)
    bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(ob.data);bm.free()
    for face,index in zip(ob.data.polygons,mesh['materials']):
        face.material_index=index;face.use_smooth=index==0
    ob.data.set_sharp_from_angle(angle=.7)
    ob['sr_painted_relief_evidence_json']=json.dumps(mesh['report'])
    ob['sr_authoring_grammar']='sampled image-alpha silhouette, authored curved thickness and shallow painted relief'
    ob['sr_uv_intent']='unchanged full-image front UVs; plain material on back and thickness'
    ob['sr_surface_role']='smooth painted face, flat thickness and backing boundaries'
    return ob


def add_boundary_finish(body, *, iterations=3, ratio=.45):
    """Live perimeter relaxation and reduction; original UVs remain editable."""
    if not isinstance(iterations,int) or isinstance(iterations,bool) or not 0<=iterations<=20:
        raise ValueError('boundary iterations must be an integer in 0..20')
    if isinstance(ratio,bool) or not 0<ratio<=1:raise ValueError('ratio must be in 0..1')
    if body.vertex_groups.get('Painted silhouette boundary'):
        raise ValueError('painted boundary finish already exists; edit its modifiers')
    edges={}
    for p in body.data.polygons:
        if p.material_index!=0:continue
        ids=tuple(p.vertices)
        for a,b in zip(ids,ids[1:]+ids[:1]):edges[tuple(sorted((a,b)))]=edges.get(tuple(sorted((a,b))),0)+1
    front={v for edge,count in edges.items() if count==1 for v in edge}
    halfway=len(body.data.vertices)//2
    group=body.vertex_groups.new(name='Painted silhouette boundary')
    group.add(sorted(front|{v+halfway for v in front}),1,'REPLACE')
    smooth=body.modifiers.new('Relax sampled silhouette steps','SMOOTH')
    smooth.vertex_group=group.name;smooth.factor=.5;smooth.iterations=iterations
    decimate=body.modifiers.new('Reduce curved painted surface','DECIMATE');decimate.ratio=ratio
    body['sr_boundary_finish']='live perimeter relaxation and decimation; review silhouette and UVs after edits'
