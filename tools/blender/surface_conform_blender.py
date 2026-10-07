"""Live panel conformance for NEW source scaffolds. Saved documents own edits."""
import json
import math
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import bpy
import item_kit as kit


def conform_panel(name, mesh, root, target, front_material, edge_material, *,
                  thickness=.10, offset=.025, projection_limit=3.0, smooth=True,
                  boundary_iterations=0):
    """Keep alpha-supported front faces, project +local Y, then add thickness.

    The caller places the panel in front of a closed body guide. The guide must
    be a root-owned mesh; missed projections/UV stretching require inspection.
    A thick input is intentionally reduced to its front surface before wrapping
    so front/back vertices cannot collapse onto the same target surface.
    """
    if name in bpy.data.objects:
        raise ValueError('panel already exists; edit its saved mesh and modifiers directly')
    for value in (thickness,projection_limit):
        if isinstance(value,bool) or not math.isfinite(value) or value<=0:
            raise ValueError('positive finite thickness and projection limit required')
    if isinstance(offset,bool) or not math.isfinite(offset) or offset<0:
        raise ValueError('nonnegative finite offset required')
    if isinstance(boundary_iterations,bool) or not isinstance(boundary_iterations,int) or not 0<=boundary_iterations<=20:
        raise ValueError('boundary iterations must be an integer in 0..20')
    if target.type!='MESH' or target not in list(root.children_recursive):
        raise ValueError('target must be a mesh owned by the same export root')
    if edge_material.use_nodes and any(n.type=='TEX_IMAGE' for n in edge_material.node_tree.nodes):
        raise ValueError('edge material must be plain: generated thickness has no independent UV chart')
    passes=json.loads(edge_material.get('sr_runtime_passes_json','[]'))
    if any(p.get('uvSource')=='uv' for p in passes):
        raise ValueError('edge material cannot use a UV overlay on generated thickness')
    front=[(face,uv) for face,uv,index in zip(mesh['faces'],mesh['uvs'],mesh['materials']) if index==0]
    if not front:raise ValueError('no front surface faces')
    used=sorted({i for face,_ in front for i in face});indices={old:i for i,old in enumerate(used)}
    ob=kit.mesh_object(name,[mesh['vertices'][i] for i in used],
        [tuple(indices[i] for i in face) for face,_ in front],root,front_material,
        uvs=[uv for _,uv in front],flat=not smooth)
    ob.data.materials.append(edge_material)
    if boundary_iterations:
        counts={}
        for face in ob.data.polygons:
            ids=tuple(face.vertices)
            for a,b in zip(ids,ids[1:]+ids[:1]):
                key=tuple(sorted((a,b)));counts[key]=counts.get(key,0)+1
        group=ob.vertex_groups.new(name='Conformed silhouette boundary')
        group.add(sorted({v for edge,count in counts.items() if count==1 for v in edge}),1,'REPLACE')
        relax=ob.modifiers.new('Relax sampled panel boundary','SMOOTH')
        relax.vertex_group=group.name;relax.factor=.5;relax.iterations=boundary_iterations
    wrap=ob.modifiers.new('Conform panel to body guide','SHRINKWRAP')
    wrap.target=target;wrap.wrap_method='PROJECT';wrap.wrap_mode='ON_SURFACE'
    wrap.use_project_y=True;wrap.use_positive_direction=True;wrap.use_negative_direction=False
    wrap.project_limit=projection_limit;wrap.offset=offset
    solid=kit.solidify(ob,thickness,offset=1.0);solid.material_offset=1;solid.material_offset_rim=1
    # Solidify copies front UVs/normals into generated surfaces. The plain
    # secondary material owns both back and cut rims; only the front is smooth.
    tree=kit.gn_tree(name+'_PanelShading',{'Geometry':('NodeSocketGeometry',None,{})})
    inp=kit.gn_node(tree,'NodeGroupInput');out=kit.gn_node(tree,'NodeGroupOutput')
    flat=kit.gn_node(tree,'GeometryNodeSetShadeSmooth',domain='FACE');flat.inputs['Shade Smooth'].default_value=False
    kit.gn_link(tree,inp,'Geometry',flat,'Geometry')
    if smooth:
        index=kit.gn_node(tree,'GeometryNodeInputMaterialIndex')
        front=kit.gn_node(tree,'FunctionNodeCompare',data_type='INT',operation='EQUAL');front.inputs['B'].default_value=0
        shade=kit.gn_node(tree,'GeometryNodeSetShadeSmooth',domain='FACE');shade.inputs['Shade Smooth'].default_value=True
        kit.gn_link(tree,index,'Material Index',front,'A');kit.gn_link(tree,front,'Result',shade,'Selection')
        kit.gn_link(tree,flat,'Geometry',shade,'Geometry');kit.gn_link(tree,shade,'Geometry',out,'Geometry')
    else:kit.gn_link(tree,flat,'Geometry',out,'Geometry')
    kit.gn_attach(ob,tree)
    ob['sr_authoring_grammar']='clipped image-alpha panel + live projected surface conformance + thickness'
    ob['sr_conformance_target']=target.name
    ob['sr_painted_relief_evidence_json']=json.dumps(mesh['report'])
    ob['sr_conformance_boundary']='projection +local Y; source UVs preserved; inspect missed rays and stretched density'
    return ob
