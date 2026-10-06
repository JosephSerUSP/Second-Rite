"""Live orthographic shadow intersections; runs inside pinned Blender.

``build_volume`` is reusable by new-source authors. The masks remain planar
meshes with live thickness; the visible object shares its front mask data.
Boolean intersections, optional cut stencils and generated UVs remain live.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
import bmesh
from mathutils import Vector

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import item_kit as kit
from shadow_volume import PLANES,validate


def _mask(name,plane,points,extent,root,material):
    axes=PLANES[plane];verts=[]
    for pair in points:
        point=[0.,0.,0.]
        for axis,value in zip(axes,pair):point[axis]=value
        verts.append(point)
    ob=kit.mesh_object(name,verts,[tuple(range(len(verts)))],root,material)
    solid=kit.solidify(ob,extent*2,offset=0)
    solid.name='Extruded shadow working depth'
    ob.hide_render=True;ob.display_type='WIRE'
    ob['sr_shadow_plane']=plane;ob['sr_construction_role']='editable 2D shadow; normal-axis thickness is a working envelope'
    ob['sr_shadow_axes']=' / '.join('XYZ'[axis] for axis in axes)
    return ob


def _surface_nodes(ob,smooth):
    """UV every resolved face with a dynamic dominant-plane box projection."""
    tree=kit.gn_tree(ob.name+'_projected_surfaces',{'Geometry':('NodeSocketGeometry',None,{})})
    inp=kit.gn_node(tree,'NodeGroupInput');out=kit.gn_node(tree,'NodeGroupOutput')
    # Boolean/bevel intersections may contain sliver triangles that collapse at
    # the runtime OBJ's six-decimal precision. Remove only near-zero area faces.
    area=kit.gn_node(tree,'GeometryNodeInputMeshFaceArea')
    tiny=kit.gn_node(tree,'ShaderNodeMath',operation='LESS_THAN');tiny.inputs[1].default_value=1e-9
    kit.gn_link(tree,area,'Area',tiny,0)
    clean=kit.gn_node(tree,'GeometryNodeDeleteGeometry',domain='FACE',mode='ALL')
    kit.gn_link(tree,inp,'Geometry',clean,'Geometry');kit.gn_link(tree,tiny,0,clean,'Selection')
    pos=kit.gn_node(tree,'GeometryNodeInputPosition');normal=kit.gn_node(tree,'GeometryNodeInputNormal')
    stats=kit.gn_node(tree,'GeometryNodeAttributeStatistic',data_type='FLOAT_VECTOR',domain='POINT')
    kit.gn_link(tree,clean,'Geometry',stats,'Geometry');kit.gn_link(tree,pos,'Position',stats,'Attribute')
    span=kit.gn_node(tree,'ShaderNodeVectorMath',operation='SUBTRACT');kit.gn_link(tree,stats,'Max',span,0);kit.gn_link(tree,stats,'Min',span,1)
    delta=kit.gn_node(tree,'ShaderNodeVectorMath',operation='SUBTRACT');kit.gn_link(tree,pos,'Position',delta,0);kit.gn_link(tree,stats,'Min',delta,1)
    uv=kit.gn_node(tree,'ShaderNodeVectorMath',operation='DIVIDE');kit.gn_link(tree,delta,0,uv,0);kit.gn_link(tree,span,0,uv,1)
    xyz=kit.gn_node(tree,'ShaderNodeSeparateXYZ');kit.gn_link(tree,uv,0,xyz,'Vector')
    absn=kit.gn_node(tree,'ShaderNodeVectorMath',operation='ABSOLUTE');kit.gn_link(tree,normal,'Normal',absn,0)
    ns=kit.gn_node(tree,'ShaderNodeSeparateXYZ');kit.gn_link(tree,absn,0,ns,'Vector')
    def compare(a,b):
        n=kit.gn_node(tree,'ShaderNodeMath',operation='GREATER_THAN');kit.gn_link(tree,ns,a,n,0);kit.gn_link(tree,ns,b,n,1);return n
    x_y=compare('X','Y');x_z=compare('X','Z');y_z=compare('Y','Z')
    xdominant=kit.gn_node(tree,'FunctionNodeBooleanMath',operation='AND');kit.gn_link(tree,x_y,0,xdominant,0);kit.gn_link(tree,x_z,0,xdominant,1)
    pairs=[]
    for first,second in (('Y','Z'),('X','Z'),('X','Y')):
        combine=kit.gn_node(tree,'ShaderNodeCombineXYZ');kit.gn_link(tree,xyz,first,combine,'X');kit.gn_link(tree,xyz,second,combine,'Y');pairs.append(combine)
    yz=kit.gn_node(tree,'GeometryNodeSwitch',input_type='VECTOR');kit.gn_link(tree,y_z,0,yz,'Switch');kit.gn_link(tree,pairs[2],'Vector',yz,'False');kit.gn_link(tree,pairs[1],'Vector',yz,'True')
    choice=kit.gn_node(tree,'GeometryNodeSwitch',input_type='VECTOR');kit.gn_link(tree,xdominant,0,choice,'Switch');kit.gn_link(tree,yz,'Output',choice,'False');kit.gn_link(tree,pairs[0],'Vector',choice,'True')
    # Force planar normals in the mapping context, then apply the desired shading.
    # This keeps a smooth bevel from changing charts halfway across a face.
    flat=kit.gn_node(tree,'GeometryNodeSetShadeSmooth',domain='FACE');flat.inputs['Shade Smooth'].default_value=False
    kit.gn_link(tree,clean,'Geometry',flat,'Geometry')
    store=kit.gn_node(tree,'GeometryNodeStoreNamedAttribute',data_type='FLOAT2',domain='CORNER');store.inputs['Name'].default_value='UVMap'
    kit.gn_link(tree,flat,'Geometry',store,'Geometry')
    kit.gn_link(tree,choice,'Output',store,'Value')
    shading=kit.gn_node(tree,'GeometryNodeSetShadeSmooth',domain='FACE');shading.inputs['Shade Smooth'].default_value=smooth
    kit.gn_link(tree,store,'Geometry',shading,'Geometry');kit.gn_link(tree,shading,'Geometry',out,'Geometry')
    kit.gn_attach(ob,tree)


def build_volume(name,spec,root,material):
    checked=validate(spec)
    extent=max(abs(v) for plane in PLANES for p in checked[plane] for v in p)*3+1
    masks={plane:_mask('SHADOW_'+name+'_'+plane,plane,checked[plane],extent,root,material) for plane in PLANES}
    body=bpy.data.objects.new(name,masks['front'].data);bpy.context.collection.objects.link(body);kit.core.parent_local(body,root)
    kit.solidify(body,extent*2,offset=0)
    for plane in ('side','top'):
        mod=kit.boolean_difference(body,masks[plane]);mod.operation='INTERSECT';mod.name='Constrain by '+plane+' shadow'
    for i,cut in enumerate(checked['cuts']):
        cutter=_mask('CUT_'+name+'_'+str(i),cut['plane'],cut['outline'],extent,root,material)
        mod=kit.boolean_difference(body,cutter);mod.name='Remove drawn opening '+str(i)
    weld=body.modifiers.new('Merge shadow intersection coincidences','WELD');weld.merge_threshold=1e-5
    if checked['bevel']:
        kit.core.add_bevel_modifier(body,checked['bevel'],segments=3,angle_degrees=25)
    weld=body.modifiers.new('Merge bevel coincidences at export precision','WELD');weld.merge_threshold=1e-5
    triangle=body.modifiers.new('Resolve collinear shadow faces','TRIANGULATE');triangle.quad_method='BEAUTY';triangle.ngon_method='BEAUTY'
    _surface_nodes(body,checked['smooth'])
    body['sr_authoring_grammar']='intersection of front/side/top shadows with optional drawn cut stencils'
    body['sr_surface_role']='rounded continuous shadow hull' if checked['smooth'] else 'flat shadow-cut planes with bevel rims'
    body['sr_shadow_working_extent']=extent
    body['sr_uv_intent']='dynamic bounded dominant-plane projection; generated Boolean/bevel faces included'
    bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();ev=body.evaluated_get(dg);mesh=ev.to_mesh()
    try:
        if not mesh.polygons:raise ValueError(name+': shadows intersect to an empty hull')
        bm=bmesh.new();bm.from_mesh(mesh);volume=abs(bm.calc_volume(signed=True));bm.free()
        if volume<1e-9:raise ValueError(name+': evaluated shadow hull has no volume')
        body['sr_initial_volume']=volume
    finally:ev.to_mesh_clear()
    return body,masks


def inspect_body(body):
    """Measure the saved graph, including generated-face UVs and linked controls."""
    bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();ev=body.evaluated_get(dg)
    data=ev.to_mesh(preserve_all_data_layers=True,depsgraph=dg)
    try:
        if not data.vertices or not data.polygons:raise ValueError(body.name+': evaluated hull is empty')
        low=[min(v.co[i] for v in data.vertices) for i in range(3)];high=[max(v.co[i] for v in data.vertices) for i in range(3)]
        bm=bmesh.new();bm.from_mesh(data);volume=abs(bm.calc_volume(signed=True));bm.free()
        layer=data.uv_layers.get('UVMap');bad=0
        for p in data.polygons:
            if layer is None:bad+=1;continue
            coords=[tuple(layer.data[li].uv) for li in p.loop_indices]
            area=abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(coords,coords[1:]+coords[:1])))/2
            if area<1e-10 or any(c<-.00001 or c>1.00001 for uv in coords for c in uv):bad+=1
        controls=[]
        front=next((ob for ob in body.parent.children if ob.hide_render and ob.type=='MESH' and ob.data==body.data),None)
        objects=([front] if front else [])+[m.object for m in body.modifiers if m.type=='BOOLEAN']
        for ob in objects:
            plane=ob.get('sr_shadow_plane');axes=PLANES[plane]
            controls.append({'name':ob.name,'plane':plane,'isCut':ob.name.startswith('CUT_'),
                'outline':[[float(v.co[a]) for a in axes] for v in ob.data.vertices]})
        return {'name':body.name,'coordinateSpace':'body local','bounds':[low,high],'volume':volume,
            'triangles':sum(len(p.vertices)-2 for p in data.polygons),'smoothFaces':sum(p.use_smooth for p in data.polygons),
            'faces':len(data.polygons),'uvFindings':bad,'modifiers':[m.type for m in body.modifiers],'controls':controls}
    finally:ev.to_mesh_clear()


def main():
    parser=argparse.ArgumentParser();mode=parser.add_mutually_exclusive_group(required=True);mode.add_argument('--spec',type=Path);mode.add_argument('--inspect-source',type=Path);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    if args.inspect_source:
        if args.output.exists():raise ValueError('Inspection output exists')
        if args.output.suffix.lower()!='.json':raise ValueError('Inspection output must be .json')
        before=hashlib.sha256(args.inspect_source.read_bytes()).hexdigest();bpy.ops.wm.open_mainfile(filepath=str(args.inspect_source))
        bodies=[o for o in bpy.data.objects if not o.hide_render and 'sr_shadow_working_extent' in o]
        if not bodies:raise ValueError('Source contains no shadow volumes')
        report={'sourceHash':before,'bodies':[inspect_body(o) for o in bodies]}
        assert before==hashlib.sha256(args.inspect_source.read_bytes()).hexdigest(),'inspection changed source'
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        print('SHADOW SOURCE INSPECTION OK: '+str(len(bodies))+' body(s)');return
    checked=validate(json.loads(args.spec.read_text(encoding='utf-8')))
    if args.output.exists():raise ValueError('Saved source exists; edit it directly')
    if args.output.stem!=checked['id'] or args.output.suffix.lower()!='.blend':raise ValueError('Source filename must match id')
    root=kit.begin(checked['id'],'drawn_shadow_intersection','Three editable orthographic silhouettes constrain a resolved 3D hull')
    material=kit.material(checked['id']+'_surface',color=checked['color'])
    raw={key:value for key,value in checked.items() if key!='projectionBounds'}
    build_volume('A_ShadowHull',raw,root,material)
    root['sr_review_status']='requires native review';kit.save_new(args.output)


if __name__=='__main__':main()
