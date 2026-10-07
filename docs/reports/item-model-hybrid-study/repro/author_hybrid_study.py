"""Once-only six-study scaffold. Existing saved sources refuse regeneration."""
import sys,json,math,argparse
from pathlib import Path
import bpy,bmesh
from mathutils import Vector
sys.path.insert(0,'tools/blender')
import item_kit as kit
from path_sweep import sweep_tube
from shadow_volume_blender import build_volume,_surface_nodes
from surface_conform_blender import conform_panel
from surface_atlas import pixel_rectangle_uv,rectangle_uv
P=Path('out/work/hybrid');PROJECT=Path('docs/reports/item-model-hybrid-study/source-project');SOURCE=PROJECT/'assets/authoring/items'
layout=json.loads((P/'actual-layout.json').read_text());cal=json.loads((P/'calibration.json').read_text());panels=json.loads((P/'panel-meshes.json').read_text())
STEMS=[f'hybrid_{d}_{r}' for d in ['carved','salvage'] for r in ['hull','sdf','conform']]
parser=argparse.ArgumentParser();parser.add_argument('--only',nargs='+',choices=STEMS);args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
selected=args.only or STEMS;assert all(not (SOURCE/(s+'.blend')).exists() for s in selected),'Saved sources authoritative; edit directly'
bounds={k:pixel_rectangle_uv(v['pixels'],layout['imageSize'],inset=layout['insetPixels']) for k,v in layout['regions'].items()}
root=None;direction=None;stem=None;mats={}

def material(role):
    if role not in mats:
        passes=[{'uvSource':'uv','blend':'add','strength':.16,'texture':'assets/models/items/hybrid_surface_atlas.png'}]
        if direction=='salvage' and role in ['outer','spine']:passes.append({'uvSource':'sphere','blend':'add','strength':.10,'texture':'assets/models/matcaps/steel.png'})
        m=kit.material(stem+'_'+role,image=(SOURCE/'_textures/hybrid_surface_atlas.png').resolve(),passes=passes)
        m['sr_atlas_region']=direction+'_'+role;mats[role]=m
    return mats[role]

def recalc(ob):
    bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(ob.data);bm.free();ob.data.update()

def map_mesh(ob,role):
    """Bounded dominant-plane coordinates; use flat face normals for chart choice."""
    ob.data.update();uv=ob.data.uv_layers.active or ob.data.uv_layers.new(name='UVMap')
    ranges=[(min(v.co[i] for v in ob.data.vertices),max(v.co[i] for v in ob.data.vertices)) for i in range(3)]
    for face in ob.data.polygons:
        axes=sorted(range(3),key=lambda i:abs(face.normal[i]))[:2]
        for li in face.loop_indices:
            co=ob.data.vertices[ob.data.loops[li].vertex_index].co
            vals=[(co[i]-ranges[i][0])/max(1e-9,ranges[i][1]-ranges[i][0]) for i in axes]
            uv.data[li].uv=tuple(round(v,6) for v in rectangle_uv(*vals,bounds[direction+'_'+role]))

def bounded_generated(ob,role,smooth):
    _surface_nodes(ob,smooth)
    T=kit.gn_tree(ob.name+'_BoundedSharedAtlas',{'Geometry':('NodeSocketGeometry',None,{})});gi=kit.gn_node(T,'NodeGroupInput');go=kit.gn_node(T,'NodeGroupOutput')
    attr=kit.gn_node(T,'GeometryNodeInputNamedAttribute',data_type='FLOAT_VECTOR');attr.inputs['Name'].default_value='UVMap'
    mul=kit.gn_node(T,'ShaderNodeVectorMath',operation='MULTIPLY');add=kit.gn_node(T,'ShaderNodeVectorMath',operation='ADD')
    u0,v0,u1,v1=bounds[direction+'_'+role];mul.inputs[1].default_value=(u1-u0,v1-v0,1);add.inputs[1].default_value=(u0,v0,0)
    store=kit.gn_node(T,'GeometryNodeStoreNamedAttribute',data_type='FLOAT2',domain='CORNER');store.inputs['Name'].default_value='UVMap'
    kit.gn_link(T,gi,'Geometry',store,'Geometry');kit.gn_link(T,attr,'Attribute',mul,0);kit.gn_link(T,mul,'Vector',add,0);kit.gn_link(T,add,'Vector',store,'Value');kit.gn_link(T,store,'Geometry',go,'Geometry');kit.gn_attach(ob,T)

def tube(name,points,radii,role,segments=8):
    v,f,uv,smooth=sweep_tube(points,radii,segments=segments)
    ob=kit.mesh_object(name,v,f,root,material(role),uvs=[[rectangle_uv(u,t,bounds[direction+'_'+role]) for u,t in row] for row in uv]);recalc(ob)
    for p,flag in zip(ob.data.polygons,smooth):p.use_smooth=flag
    for d in ob.data.uv_layers.active.data:d.uv=tuple(round(v,6) for v in d.uv)
    ob['sr_path_controls']=json.dumps(points);return ob

LEFT={
 'carved':[(-1.23,-1.34),(-.92,-1.53),(-.56,-1.30),(-.59,-1.03),(-.87,-.63),(-.96,-.18),(-.91,.31),(-1.00,.76),(-.72,1.25),(-.28,1.57),(-.35,1.84),(-.76,1.76),(-1.19,1.37),(-1.39,.80),(-1.27,.32),(-1.37,-.37)],
 'salvage':[(-1.33,-1.34),(-.93,-1.55),(-.62,-1.30),(-.93,-.84),(-.83,-.19),(-1.06,.10),(-.96,.64),(-.82,.94),(-.39,1.25),(-.27,1.61),(-.55,1.83),(-1.12,1.53),(-1.37,1.12),(-1.43,.55),(-1.21,.18),(-1.49,-.05),(-1.35,-.70)]}
RIGHT={
 'carved':[(1.16,-1.33),(.64,-1.46),(.47,-1.15),(.78,-.98),(.96,-.52),(.91,.16),(.76,.55),(.61,.89),(.83,1.02),(1.19,.80),(1.37,.58),(1.34,.10),(1.43,-.35)],
 'salvage':[(1.11,-1.38),(.59,-1.45),(.47,-1.20),(.87,-.91),(.95,-.37),(.83,.13),(.89,.48),(.62,.72),(.60,1.01),(.99,1.08),(1.17,.78),(1.43,.62),(1.50,.08),(1.26,-.17),(1.48,-.46)]}

def guide():
    sections=[{'z':z,'a':a,'b':b,'n':2.8 if direction=='carved' else 4,'cx':-.02} for z,a,b in [(-1.8,1.43,.48),(-1.1,1.58,.64),(-.1,1.60,.68),(.8,1.58,.63),(1.95,1.5,.40)]]
    v,f,uv=kit.loft(sections,samples=32);ob=kit.mesh_object('GUIDE_ClosedConformanceBody',v,f,root,material('spine'),flat=False);recalc(ob);ob.hide_render=True;ob.display_type='WIRE';ob['sr_guide_role']='closed hidden projection target, authored not recovered';return ob

def core(sdf=False):
    sections=[]
    for z,a,b,cx in [(-1.28,.08,.08,.18),(-1.12,.44,.38,.15),(-.8,.74,.60,.15),(-.32,.86,.65,.16),(.18,.75,.59,.24),(.52,.57,.47,.23),(.85,.31,.26,.19),(.95,.08,.08,.15)]:
        sections.append({'z':z,'a':a,'b':b,'cx':cx,'cy':-.04,'n':2,'bump':lambda t,z=z:1+.055*math.cos(3*t+z*1.2)})
    v,f,uv=kit.loft(sections,samples=24);ob=kit.mesh_object('CORE_OrganicVolume',v,f,root,material('core'),flat=False);recalc(ob);map_mesh(ob,'core')
    if sdf:
        seeds=kit.point_cloud('GUIDE_CoreLobes',[(.28,-.17,-.69),(.45,-.16,-.17),(.26,-.10,.38)],root,radius=[.57,.61,.40])
        T=kit.gn_tree('Live_OrganicCore_SDF',{'Geometry':('NodeSocketGeometry',None,{}),'Lobes':('NodeSocketObject',None,{}),'Voxel':('NodeSocketFloat',.065,{'min_value':.025})})
        gi=kit.gn_node(T,'NodeGroupInput');go=kit.gn_node(T,'NodeGroupOutput');m2s=kit.gn_node(T,'GeometryNodeMeshToSDFGrid');oi=kit.gn_node(T,'GeometryNodeObjectInfo');mp=kit.gn_node(T,'GeometryNodeMeshToPoints')
        rad=kit.gn_node(T,'GeometryNodeInputNamedAttribute',data_type='FLOAT');rad.inputs['Name'].default_value='radius';p2s=kit.gn_node(T,'GeometryNodePointsToSDFGrid');union=kit.gn_node(T,'GeometryNodeSDFGridBoolean',operation='UNION');fil=kit.gn_node(T,'GeometryNodeSDFGridFillet');fil.inputs['Iterations'].default_value=1
        g2m=kit.gn_node(T,'GeometryNodeGridToMesh');g2m.inputs['Threshold'].default_value=0
        weld=kit.gn_node(T,'GeometryNodeMergeByDistance');weld.inputs['Distance'].default_value=.002;mat=kit.gn_node(T,'GeometryNodeSetMaterial');mat.inputs['Material'].default_value=material('core')
        def L(a,an,b,bn):kit.gn_link(T,a,an,b,bn)
        L(gi,'Geometry',m2s,'Mesh');L(gi,'Voxel',m2s,'Voxel Size');L(gi,'Lobes',oi,'Object');L(oi,'Geometry',mp,'Mesh');L(mp,'Points',p2s,'Points');L(rad,'Attribute',p2s,'Radius');L(gi,'Voxel',p2s,'Voxel Size')
        L(m2s,'SDF Grid',union,1);L(p2s,'SDF Grid',union,1);L(union,'Grid',fil,'Grid');L(fil,'Grid',g2m,'Grid');L(g2m,'Mesh',weld,'Geometry');L(weld,'Geometry',mat,'Geometry');L(mat,'Geometry',go,'Geometry');kit.gn_attach(ob,T,Lobes=seeds,Voxel=.065)
        bounded_generated(ob,'core',True)
    else:
        for p in ob.data.polygons:
            if abs(p.normal.z)>.95:p.use_smooth=False
    return ob

def cheeks(route):
    if route=='conform':
        target=guide()
        for side,x,z in [('left',-.91,.13),('right',1.02,-.12)]:
            mesh=json.loads(json.dumps(panels[direction+'_'+side]))
            # Image controls the outline only. Same atlas palette as other routes.
            mesh['vertices']=[(vx+x,-1.3,vz+z) for vx,vy,vz in mesh['vertices']]
            for row in mesh['uvs']:
                for i,(u,v) in enumerate(row):row[i]=rectangle_uv(.5,.5,bounds[direction+'_outer'])
            ob=conform_panel('PANEL_'+side,mesh,root,target,material('outer'),material('spine'),thickness=.14,offset=.035,smooth=direction=='carved')
            # Assign real panel coordinates; colour is from the shared flat atlas.
            map_mesh(ob,'outer')
            if direction=='carved':
                T=kit.gn_tree('Keep_'+side+'_CutRimsFlat',{'Geometry':('NodeSocketGeometry',None,{})});gi=kit.gn_node(T,'NodeGroupInput');go=kit.gn_node(T,'NodeGroupOutput')
                flat=kit.gn_node(T,'GeometryNodeSetShadeSmooth',domain='FACE');flat.inputs['Shade Smooth'].default_value=False
                index=kit.gn_node(T,'GeometryNodeInputMaterialIndex');eq=kit.gn_node(T,'FunctionNodeCompare',data_type='INT',operation='EQUAL');eq.inputs['B'].default_value=0
                shade=kit.gn_node(T,'GeometryNodeSetShadeSmooth',domain='FACE');shade.inputs['Shade Smooth'].default_value=True
                kit.gn_link(T,gi,'Geometry',flat,'Geometry');kit.gn_link(T,index,'Material Index',eq,'A');kit.gn_link(T,eq,'Result',shade,'Selection');kit.gn_link(T,flat,'Geometry',shade,'Geometry');kit.gn_link(T,shade,'Geometry',go,'Geometry');kit.gn_attach(ob,T)
        return
    for side,outline in [('left',LEFT[direction]),('right',RIGHT[direction])]:
        if route=='hull':
            spec={'version':1,'id':stem,'front':outline,'side':[(-.85,-1.8),(-.92,-.9),(-.76,.9),(-.6,2.0),(-.38,2.0),(-.39,.9),(-.52,-1.8)],'top':[(-1.7,-.94),(1.7,-.94),(1.7,-.37),(-1.7,-.37)],'bevel':.06 if direction=='carved' else .035,'smooth':False,'color':[.7,.7,.7]}
            ob,masks=build_volume('HULL_'+side,spec,root,material('outer'));bounded_generated(ob,'outer',False)
        else:
            ob=kit.plate(outline,root,'FABRICATED_'+side,material('outer'),.28,loc=(0,-.66,0),plane='XZ')
            bpy.context.view_layer.objects.active=ob;bpy.ops.object.select_all(action='DESELECT');ob.select_set(True)
            for mod in list(ob.modifiers):bpy.ops.object.modifier_apply(modifier=mod.name)
            mod=ob.modifiers.new('FabricatedPlateBevel','BEVEL');mod.width=.055 if direction=='carved' else .035;mod.segments=2 if direction=='carved' else 1;bpy.ops.object.modifier_apply(modifier=mod.name)
            recalc(ob);map_mesh(ob,'outer')

def shared_assembly():
    tube('BACK_SupportSpine',[(-.62,.45,-1.43),(-.47,.65,-.88),(-.39,.67,-.12),(-.47,.58,.72),(-.62,.42,1.60)],[(.23,.13)]*5,'spine')
    tube('BASE_Cradle',[(-1.10,.04,-1.13),(-.62,.35,-1.46),(.12,.43,-1.53),(.70,.35,-1.44),(1.12,.03,-1.18)],[(.15,.12)]*5,'spine')
    front=[(-1.06,-.84,.84),(-.67,-.88,.49),(-.10,-.95,.05),(.48,-.92,-.40),(1.13,-.77,-.85)]
    back=[(1.10,.52,-.85),(.52,.79,-.39),(-.08,.83,.10),(-.66,.70,.57),(-1.10,.37,.84)]
    tube('BINDING_FrontDiagonal',front,[(.036,.24)]*5,'binding',8)
    tube('BINDING_BackDiagonal',back,[(.036,.24)]*5,'binding',8)
    tube('BINDING_RightReturn',[(1.11,-.77,-.85),(1.28,-.42,-.85),(1.3,.08,-.85),(1.1,.52,-.85)],[(.036,.24)]*4,'binding',8)
    tube('BINDING_LeftReturn',[(-1.1,.37,.84),(-1.30,.0,.84),(-1.32,-.43,.84),(-1.06,-.84,.84)],[(.036,.24)]*4,'binding',8)
    tube('BINDING_FoldedTail',[(-1.10,-.69,-.52),(-1.31,-.75,-1.03),(-1.23,-.85,-1.61),(-1.40,-.69,-1.75)],[(.028,.18)]*4,'binding',8)
    for i,(x,z) in enumerate([(-1.1,.73),(-1.13,-.6),(1.13,.4),(1.06,-1.19)]):
        v,f=kit.revolve([(0,-.05),(.09,-.05),(.11,.0),(.085,.06),(0,.08)],segments=10,axis='Y')
        ob=kit.mesh_object('FASTENER_'+str(i),v,f,root,material('outer' if direction=='salvage' else 'spine'),loc=(x,-.87,z));recalc(ob);map_mesh(ob,'outer' if direction=='salvage' else 'spine')

for stem in selected:
    _,direction,route=stem.split('_');mats={}
    root=kit.begin(stem,'hybrid_'+route,'Nonshipping containment capsule study: '+direction+' direction, '+route+' construction',study_only=True,art_direction=direction,hybrid_route=route)
    core(route=='sdf');cheeks(route);shared_assembly();bpy.context.view_layer.update()
    dg=bpy.context.evaluated_depsgraph_get();points=[]
    for ob in root.children_recursive:
        if ob.hide_render or ob.type not in ['MESH','CURVE']:continue
        ev=ob.evaluated_get(dg);data=ev.to_mesh();points.extend([ob.matrix_world@v.co for v in data.vertices]);ev.to_mesh_clear()
    spans=[max(p[i] for p in points)-min(p[i] for p in points) for i in range(3)]
    root.scale=tuple(target/span for target,span in zip(cal[direction]['targetDimensions'],spans))
    root['sr_reference_calibration']=json.dumps(cal[direction]);root['sr_shared_atlas_regions']=json.dumps(layout)
    root['sr_comparison_contract']='Same direction reference, global dimensions, atlas palette, camera and common binding/back assembly; route changes cheek/core construction. Shape similarity is measured, not presumed.'
    root['sr_hidden_geometry']='Rear support/fasteners, core shape, body guide and conformance thickness are authored; references are inconsistent drawings, not scans.'
    root['sr_visual_acceptance']='study only; open'
    for image in bpy.data.images:
        if image.filepath and image.source=='FILE':image.filepath='//_textures/hybrid_surface_atlas.png'
    bpy.context.preferences.filepaths.save_version=0;kit.report(root);kit.save_new(SOURCE/(stem+'.blend'))
print('SIX HYBRID SOURCES CREATED ONCE')
