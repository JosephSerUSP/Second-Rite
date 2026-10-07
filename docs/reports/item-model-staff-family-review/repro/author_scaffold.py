"""Six NEW sources. After first save, edit the saved document, never rerun it."""
import math,json,sys,argparse
from pathlib import Path
import bpy,bmesh
from mathutils import Matrix,Vector
sys.path.insert(0,'tools/blender')
import item_kit as kit
from path_sweep import sweep_tube
from surface_atlas import pixel_rectangle_uv,rectangle_uv,cyclic_face_parameters
P=Path('out/work/staves');batch=json.loads((P/'batch.json').read_text());cal=json.loads((P/'calibration.json').read_text())
SOURCE=Path('projects/hichaukitoden-game/assets/authoring/items');ATLAS=batch['atlas'];layout=json.loads((P/'actual-layout.json').read_text())
bounds={n:pixel_rectangle_uv(r['pixels'],layout['imageSize'],inset=layout['insetPixels']) for n,r in layout['regions'].items()}
parser=argparse.ArgumentParser();parser.add_argument('--only',nargs='+',choices=batch['stems']);args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
selected=args.only or batch['stems']
assert all(not (SOURCE/(s+'.blend')).exists() for s in selected),'Selected .blend already authoritative; edit directly'
root=None;stem=None;mats={}


def material(region):
    if region in mats:return mats[region]
    assert stem in layout['regions'][region]['users'],(stem,region)
    passes=[{'uvSource':'uv','blend':'add','strength':.16,'texture':'assets/models/items/'+ATLAS}]
    if region in ('silver','brass','iron'):
        passes.append({'uvSource':'sphere','blend':'add','strength':.10 if region=='brass' else .12,'texture':'assets/models/matcaps/'+('gold' if region=='brass' else 'steel')+'.png'})
    mat=kit.material(stem+'_'+region,color=(1,1,1),image=SOURCE/'_textures'/ATLAS,passes=passes)
    mat['sr_atlas_region']=region;mat['sr_shared_atlas']=ATLAS;mats[region]=mat;return mat


def mesh(name,v,f,uv,region,smooth):
    ob=kit.mesh_object(name,v,f,root,material(region),uvs=uv)
    bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(ob.data);bm.free()
    for p,flag in zip(ob.data.polygons,smooth):p.use_smooth=flag
    for corner in ob.data.uv_layers.active.data:corner.uv=tuple(round(c,6) for c in corner.uv)
    return ob


def tube(name,points,radii,region,segments=8,smooth=True):
    v,f,uv,sm=sweep_tube(points,radii,segments=segments)
    ob=mesh(name,v,f,[[rectangle_uv(u,t,bounds[region]) for u,t in row] for row in uv],region,[smooth and s for s in sm])
    ob['sr_path_points']=json.dumps(points);ob['sr_path_radii']=json.dumps(radii)
    ob['sr_surface_role']='closed transported sections; length/angular UV; flat cap fans'
    return ob


def lathe(name,profile,region,segments=24,axis='Z',smooth=True,loc=(0,0,0),closed_section=False):
    v,f=kit.revolve(profile,segments=segments,axis=axis,close_bottom=not closed_section,close_top=not closed_section)
    if closed_section:
        assert all(r>0 for r,h in profile)
        for i in range(segments):
            ids=((len(profile)-1)*segments+i,(len(profile)-1)*segments+(i+1)%segments,(i+1)%segments,i)
            f.append(tuple(reversed(ids)) if axis=='Y' else ids)
    ax={'X':0,'Y':1,'Z':2}[axis];rad=[i for i in range(3) if i!=ax];lo=min(p[ax] for p in v);hi=max(p[ax] for p in v);uv=[]
    for face in f:
        pts=[v[i] for i in face]
        if max(p[ax] for p in pts)-min(p[ax] for p in pts)<1e-7:
            radius=max(math.hypot(p[rad[0]],p[rad[1]]) for p in pts)
            uv.append([rectangle_uv(.5+p[rad[0]]/radius/2,.5+p[rad[1]]/radius/2,bounds[region]) for p in pts])
        else:
            turns=[math.atan2(p[rad[1]],p[rad[0]])/math.tau%1 if math.hypot(p[rad[0]],p[rad[1]])>1e-8 else None for p in pts]
            uv.append([rectangle_uv(u,(p[ax]-lo)/(hi-lo),bounds[region]) for u,p in zip(cyclic_face_parameters(turns),pts)])
    ob=mesh(name,v,f,uv,region,[smooth]*len(f));ob.location=loc;ob['sr_profile_points']=json.dumps(profile)
    for p in ob.data.polygons:
        if abs(p.normal[ax])>.99:p.use_smooth=False
    return ob


def plate(name,outline,depth,front_region,side_region,back_region=None,loc=(0,0,0),bevel=.04):
    ob=kit.plate(outline,root,name,material(front_region),depth,plane='XZ');ob.location=loc
    bpy.context.view_layer.objects.active=ob;bpy.ops.object.select_all(action='DESELECT');ob.select_set(True)
    for m in list(ob.modifiers):bpy.ops.object.modifier_apply(modifier=m.name)
    m=ob.modifiers.new('ConstructionBevel','BEVEL');m.width=bevel;m.segments=1
    bpy.ops.object.modifier_apply(modifier=m.name)
    regions=[front_region,side_region,back_region or front_region]
    ob.data.materials.clear()
    for region in regions:ob.data.materials.append(material(region))
    ob.data.update();uv=ob.data.uv_layers.new(name='UVMap') if not ob.data.uv_layers else ob.data.uv_layers.active
    ranges=[(min(v.co[i] for v in ob.data.vertices),max(v.co[i] for v in ob.data.vertices)) for i in range(3)]
    for p in ob.data.polygons:
        index=0 if p.normal.y<-.98 else 2 if p.normal.y>.98 else 1;p.material_index=index;p.use_smooth=False
        axes=[0,2] if index!=1 else sorted(range(3),key=lambda i:abs(p.normal[i]))[:2]
        for li in p.loop_indices:
            co=ob.data.vertices[ob.data.loops[li].vertex_index].co
            vals=[(co[i]-ranges[i][0])/(ranges[i][1]-ranges[i][0]) for i in axes]
            uv.data[li].uv=tuple(round(c,6) for c in rectangle_uv(*vals,bounds[regions[index]]))
    ob['sr_surface_role']='closed bevelled thickness; flat cut planes; broad front/back correspondence, separately bounded edges'
    return ob


def collar(name,z,r,region,height=.12,segments=12):
    return lathe(name,[(0,z-height/2),(r*.9,z-height/2),(r,z),(r*.9,z+height/2),(0,z+height/2)],region,segments,smooth=False)


def grip(name,z0,z1,r,region,wrap=False):
    lathe(name,[(0,z0),(r*.90,z0),(r,z0+.05),(r,z1-.05),(r*.90,z1),(0,z1)],region)
    if wrap:
        turns=4;n=turns*18;pts=[]
        for i in range(n+1):
            a=i/n*turns*math.tau;pts.append(((r+.016)*math.cos(a),(r+.016)*math.sin(a),z0+.07+(z1-z0-.14)*i/n))
        tube(name+'_ActualRaisedWrap',pts,[(.035,.015)]*len(pts),region,6)


def arc_outline(rx,rz,z,a0,a1,width,samples=28):
    # One shared ellipse-outline helper for blade-like crescent constructions.
    angles=[math.radians(a0+(a1-a0)*i/samples) for i in range(samples+1)];outer=[];inner=[]
    for i,a in enumerate(angles):
        w=.025+width*math.sin(math.pi*i/samples)**.65
        outer.append(((rx+w)*math.cos(a),z+(rz+w)*math.sin(a)));inner.append(((rx-w)*math.cos(a),z+(rz-w)*math.sin(a)))
    return outer+list(reversed(inner))


def silver_rod():
    lathe('A_FlutedFacetedSilverBody',[(0,-2.40),(.20,-2.40),(.25,-2.15),(.18,-1.95),(.14,-1.73),(.15,-.42),(.20,-.30),(.25,-.15),(.20,1.02),(.15,1.20),(.24,1.40),(0,1.40)],'silver',8,smooth=False)
    grip('B_IndigoGrip',-1.75,-.38,.18,'indigo',True)
    for i,z in enumerate((-1.78,-.33,1.14)):collar('C_BrassJoin_'+str(i),z,.205,'brass',.07)
    frame=lathe('D_ClosedHexagonalSilverHead',[(.70,-.20),(.57,-.20),(.57,.22),(.70,.22),(.77,.08),(.77,-.07)],'silver',6,axis='Y',smooth=False,loc=(0,0,2.02),closed_section=True)
    frame.rotation_euler.y=math.radians(-30)
    rim=lathe('E_HexagonalBrassInsetSeat',[(.60,-.22),(.52,-.22),(.52,-.11),(.60,-.11)],'brass',6,axis='Y',smooth=False,loc=(0,0,2.02),closed_section=True);rim.rotation_euler.y=math.radians(-30)
    gem=lathe('F_ActualSapphireInset',[(0,-.39),(.51,-.27),(.51,-.10),(0,.01)],'sapphire',6,axis='Y',smooth=False,loc=(0,0,2.02));gem.rotation_euler.y=math.radians(-30)
    back=lathe('G_ClosedRearHeadPlate',[(0,.13),(.56,.13),(.56,.21),(0,.21)],'silver',6,axis='Y',smooth=False,loc=(0,0,2.02));back.rotation_euler.y=math.radians(-30)


def mage_staff():
    pts=[(0,0,-3),(.07,0,-2.3),(.08,.04,-1.3),(.01,.04,-.5),(-.10,.02,.25),(-.32,.08,.68),(-.62,.12,1.10),(-.76,.10,1.59),(-.69,.06,2.05),(-.40,.03,2.43),(0,0,2.64),(.43,0,2.65),(.76,.02,2.40),(.82,.04,2.09),(.71,.03,1.97)]
    rs=[(.14,.15),(.14,.15),(.15,.15),(.16,.16),(.17,.17),(.18,.19),(.20,.21),(.22,.23),(.21,.22),(.20,.21),(.20,.21),(.20,.20),(.18,.18),(.16,.17),(.10,.12)]
    tube('A_WholeCrookedWoodAndOpenHook',pts,rs,'dark_wood',12)
    grip('B_IndigoClothGrip',-1.47,-.44,.19,'indigo',True)
    for i,z in enumerate((-2.38,-1.53,-.39,.26)):collar('C_CopperBinding_'+str(i),z,.22,'brass',.15)
    ring=lathe('D_SuspensionLink',[(.070,-.028),(.038,-.028),(.038,.028),(.070,.028)],'brass',16,axis='Y',loc=(.10,-.01,2.35),closed_section=True)
    tube('E_ShortSuspensionStem',[(.10,0,2.28),(.10,-.02,2.07)],[(.025,.025)]*2,'brass',8)
    lathe('F_LanternGemCap',[(0,1.86),(.13,1.86),(.09,2.04),(0,2.04)],'brass',12,loc=(.10,-.02,0))
    lathe('G_FacetedBlueSuspendedStone',[(0,.69),(.29,1.15),(.37,1.46),(.13,1.86),(0,1.89)],'sapphire',6,smooth=False,loc=(.10,-.02,0))
    tube('H_BroadTrailingCloth',[(.16,-.02,-.75),(.31,-.03,-1.15),(.45,.04,-1.65),(.60,.02,-2.15)],[(.018,.12),(.020,.14),(.020,.16),(.015,.035)],'indigo',8,smooth=False)
    lathe('I_BulbousTimberButt',[(0,-3.02),(.12,-3.0),(.19,-2.83),(.15,-2.63),(0,-2.60)],'dark_wood',16)


def sage_staff():
    lathe('A_PaleAshShaft',[(0,-3),(.14,-3),(.16,-2.2),(.15,.93),(0,.93)],'ash_wood',20)
    grip('B_IndigoStudyGrip',-1.89,-.91,.20,'indigo',True)
    for i,z in enumerate((-1.94,-.88,.44)):collar('C_BrassJoin_'+str(i),z,.23,'brass',.14)
    lathe('D_SubstantialTabletSocket',[(0,.68),(.25,.68),(.29,.79),(.29,1.12),(.22,1.20),(0,1.20)],'brass',12,smooth=False)
    for sign in (-1,1):
        tube('E_ActualForkShoulder_'+str(sign),[(0,.02,.98),(sign*.52,.03,1.20),(sign*1.15,.06,1.59),(sign*1.15,.06,1.96)],[(.10,.12),(.11,.12),(.11,.12),(.11,.11)],'brass',8,smooth=False)
        plate('F_StoneSupportLug_'+str(sign),[(-.15,-.14),(.15,-.14),(.15,.14),(-.15,.14)],.45,'brass','brass',loc=(sign*1.17,0,1.90),bevel=.035)
        lathe('G_TasselCap_'+str(sign),[(0,.94),(.115,.94),(.125,1.03),(.07,1.21),(0,1.21)],'brass',12,loc=(sign*1.28,0,0))
        lathe('H_BlueTasselBead_'+str(sign),[(0,1.18),(.10,1.21),(.13,1.32),(.10,1.43),(0,1.46)],'indigo',12,loc=(sign*1.28,0,0))
        tube('I_TasselStem_'+str(sign),[(sign*1.28,0,1.43),(sign*1.28,0,1.78)],[(.022,.024)]*2,'brass',8)
        tassel=lathe('J_ThickFlutedBlueTassel_'+str(sign),[(0,.20),(.18,.20),(.18,.29),(.11,.88),(0,.94)],'indigo',16,loc=(sign*1.28,0,0),smooth=False)
    outline=[(-.84,-.71),(.84,-.71),(.84,-.48),(1.15,-.48),(1.15,.34),(.85,.34),(.85,.61),(.45,.61),(.45,.80),(-.45,.80),(-.45,.61),(-.85,.61),(-.85,.34),(-1.15,.34),(-1.15,-.48),(-.84,-.48)]
    plate('K_SteppedIvoryTabletAndLargeMark',outline,.43,'sage_front','ivory','sage_back',loc=(0,0,2.20),bevel=.055)
    lathe('L_FacetedBrassButt',[(0,-3.02),(.21,-2.85),(.25,-2.61),(.18,-2.47),(0,-2.47)],'brass',8,smooth=False)


def ether_staff():
    lathe('A_TaperedSilverStem',[(0,-3),(.17,-2.89),(.15,-2.63),(.13,-2.25),(.14,.41),(.21,.72),(.23,1.0),(0,1.10)],'silver',16)
    grip('B_PlumGrip',-1.87,-.45,.18,'plum')
    for i,z in enumerate((-2.43,-1.97,-.37,.37,.87)):collar('C_SilverCollar_'+str(i),z,.24 if i<4 else .30,'silver',.14)
    pts=[]
    for i in range(73):
        a=i/72*3*math.tau;pts.append((.192*math.cos(a),.192*math.sin(a),-1.89+1.43*i/72))
    tube('D_ActualBroadSilverGripSpiral',pts,[(.047,.018)]*len(pts),'silver',6)
    plate('E_OuterCrescentWithBrassDepth',arc_outline(.87,.91,1.99,55,282,.16),.24,'silver','brass',bevel=.025)
    plate('F_InnerOpposingCrescent',arc_outline(.81,.77,1.89,-102,122,.13),.25,'silver','brass',bevel=.025)
    # A long prism with diagonal display pose; hidden mounts authored explicitly.
    gem=lathe('G_DiagonalAmethystPrism',[(0,-.59),(.14,-.48),(.24,-.32),(.24,.32),(.14,.48),(0,.59)],'amethyst',6,smooth=False,loc=(0,-.02,1.95));gem.rotation_euler.y=math.radians(-38)
    direction=Vector((math.sin(math.radians(-38)),0,math.cos(math.radians(-38))))
    for side in (-1,1):
        centre=Vector((0,-.02,1.95))+direction*(side*.54)
        ob=lathe('H_PrismEndMount_'+str(side),[(0,-.09),(.16,-.09),(.18,.01),(.10,.17),(0,.17)],'brass',12,smooth=False);ob.rotation_euler.y=math.radians(-38);ob.location=centre
        endpoint=Vector((-side*.47,.02,1.95+side*.64))
        tube('I_ActualMountBridge_'+str(side),[tuple(centre),tuple(endpoint)],[(.040,.045)]*2,'brass',8)


def war_staff():
    lathe('A_StoutAshwoodPole',[(0,-3),(.15,-3),(.17,1.30),(0,1.30)],'ash_wood',16)
    grip('B_BrownFightingGrip',-1.91,-.37,.23,'brown',True)
    for i,z in enumerate((-2.01,-.29,.74,1.17)):
        collar('C_BoltedIronCollar_'+str(i),z,.29,'iron',.23)
        for k in range(4):
            a=k*math.pi/2;ob=lathe('D_RealCollarBolt_'+str(i)+'_'+str(k),[(0,0),(.045,0),(.055,.02),(.04,.065),(0,.07)],'iron',8,smooth=False)
            ob.rotation_euler=Vector((math.cos(a),math.sin(a),0)).to_track_quat('Z','Y').to_euler();ob.location=(.285*math.cos(a),.285*math.sin(a),z)
    lathe('E_HeavyFourSidedCore',[(0,1.20),(.30,1.20),(.46,1.48),(.46,2.54),(0,2.93)],'iron',4,smooth=False)
    for k in range(4):
        length=.98 if k%2==0 else .76
        outline=[(.25,1.45),(length,1.30),(length,2.42),(length-.15,2.53),(.27,2.25)]
        ob=plate('F_ThickHammerFlange_'+str(k),outline,.27,'iron','iron',bevel=.05);ob.rotation_euler.z=k*math.pi/2
        # Each plate meets the core rather than merely hovering nearby.
    lathe('G_BluntFacetedIronButt',[(0,-3.03),(.19,-3.03),(.25,-2.76),(.17,-2.45),(0,-2.45)],'iron',8,smooth=False)


def healing_staff():
    lathe('A_HoneyWoodShaft',[(0,-3),(.18,-3),(.15,-2.53),(.14,.73),(0,.90)],'ash_wood',24)
    grip('B_SageGreenClothGrip',-1.99,-.66,.18,'green_cloth',True)
    for i,z in enumerate((-2.07,-.59,.62)):collar('C_WarmBrassJoin_'+str(i),z,.21,'brass',.13)
    for sign in (-1,1):
        tube('D_BranchingWoodShoulder_'+str(sign),[(0,0,.62),(sign*.17,0,.92),(sign*.43,.03,1.20),(sign*.59,.02,1.40)],[(.12,.13),(.11,.11),(.11,.11),(.09,.10)],'ash_wood',10)
    # Generated reference has five visible petals, despite six requested. Preserve
    # that observed silhouette; the lower jade/cup is the sixth visual mass.
    angles=[-14,38,90,142,194]
    for i,angle in enumerate(angles):
        a=math.radians(angle);r=.85;centre=(r*math.cos(a),0,2.02+r*math.sin(a))
        outline=[(-.33,-.20),(.33,-.20),(.37,.12),(0,.43),(-.37,.12)]
        ob=plate('E_ChunkyCeramicPetal_'+str(i),outline,.37,'ivory','ivory',loc=centre,bevel=.055);ob.rotation_euler.y=math.radians(90-angle)
    # Visible clips bridge the five petal joins; a hidden curved brass support
    # gives them actual attachment without filling the halo window.
    pts=[(.82*math.cos(math.radians(-38+256*i/32)),.14,2.02+.82*math.sin(math.radians(-38+256*i/32))) for i in range(33)]
    tube('F_RearBrassHaloSupport',pts,[(.070,.075)]*len(pts),'brass',8)
    for i,angle in enumerate((12,64,116,168)):
        a=math.radians(angle);ob=plate('G_ActualPetalClip_'+str(i),[(-.075,-.25),(.075,-.25),(.075,.25),(-.075,.25)],.44,'brass','brass',loc=(.85*math.cos(a),0,2.02+.85*math.sin(a)),bevel=.025);ob.rotation_euler.y=math.radians(90-angle)
    lathe('H_JadeSeatRim',[(.36,-.24),(.28,-.24),(.28,.11),(.36,.11),(.41,-.08)],'brass',24,axis='Y',loc=(0,0,1.59),closed_section=True)
    lathe('I_ConvexJadeMedallion',[(0,-.36),(.17,-.33),(.29,-.25),(.30,-.16),(.24,-.05),(0,-.05)],'jade',24,axis='Y',loc=(0,0,1.59))
    lathe('J_JadeSupportCup',[(0,1.12),(.17,1.12),(.25,1.27),(.20,1.45),(0,1.45)],'brass',16,smooth=False)
    tube('K_BroadGreenTrailingCloth',[(.15,-.02,-.82),(.30,0,-1.18),(.40,.04,-1.62),(.61,.07,-2.13)],[(.018,.12),(.02,.18),(.02,.20),(.016,.045)],'green_cloth',8,smooth=False)
    lathe('L_CarvedBulbousWoodButt',[(0,-3),(.17,-3),(.25,-2.73),(.18,-2.43),(0,-2.36)],'ash_wood',20)
    collar('M_BrassButtCap',-2.99,.20,'brass',.11)


for stem in selected:
    mats={};root=kit.begin(stem,'ritual_staff_family_direction',batch['direction'])
    globals()[stem]()
    root['sr_shared_atlas']=ATLAS;root['sr_atlas_allocations']=json.dumps(layout)
    root['sr_reference_measurements']=json.dumps(cal['items'][stem]);root['sr_direction_criteria']=json.dumps(batch['nativeCriteria'])
    root['sr_generation_method']='one family direction, two triple multiview sheets, one original shared atlas for six independent constructions'
    root['sr_visual_acceptance']='open; native checks are not owner acceptance'
    for im in bpy.data.images:
        if im.source=='FILE' and im.filepath:im.filepath='//_textures/'+ATLAS
    kit.report(root);kit.save_new(SOURCE/(stem+'.blend'))
