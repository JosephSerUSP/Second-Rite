"""Passage House from connected building volumes and architectural assemblies.

The runtime boundary remains environment OBJ/atlas. The authoring model is a
closed room shell plus openings, construction, dress and lighting, not a mesh
budget imposed on the source.
"""
from dataclasses import dataclass,asdict
from pathlib import Path
import json,math,random
import bpy
from mathutils import Vector
import second_rite_asset_core as core
import thestra_camera,render_profiles
from first_stratum.common import box
from architectural_assemblies import Window,window
from opening_families import door,box_receiver
from vendor_assets import verify

ROOT=Path(__file__).resolve().parents[3]
CANDIDATE=ROOT/'projects/hichaukitoden-game/assets/authoring/candidates/passage_house_courtyard'

@dataclass(frozen=True)
class Volume:
    name:str
    front:float
    back:float
    start:float
    end:float
    floor:float
    eave:float
    ridge:float
    start_portal:bool=False
    end_portal:bool=False

class Builder:
    def __init__(self):
        self.source=core.ensure_collection('TH_SOURCE')
        self.root=bpy.data.objects.new('Passage House arrival court',None);self.source.objects.link(self.root)
    def part(self,name,size,position,material,role='both',bevel=0):
        obj=box(name,self.root,size,position,material,core,bevel=bevel)
        core.move_to_collection(obj,self.source);obj['sr_bake_role']=role;obj['sr_bake_source']=True
        for mod in obj.modifiers:
            if mod.type=='BEVEL':mod.segments=3 if role=='source' else 1
        return obj
    def mesh(self,name,vertices,faces,material,role='both'):
        data=bpy.data.meshes.new(name+'_mesh');data.from_pydata(vertices,[],faces);data.update()
        import mesh_export_geometry
        mesh_export_geometry.prepare(data)
        if material:data.materials.append(material)
        obj=bpy.data.objects.new(name,data);self.source.objects.link(obj);obj.parent=self.root
        obj['sr_bake_role']=role;obj['sr_bake_source']=True
        return obj
    def receiver(self,name,x,y,z,width,height,material):
        obj=self.mesh(name,[(x,y-width/2,z-height/2),(x,y-width/2,z+height/2),(x,y+width/2,z+height/2),(x,y+width/2,z-height/2)],[(0,1,2,3)],material,'receiver')
        obj['sr_bake_open_surface']=True;obj.hide_render=True
        return obj
    def cylinder(self,name,a,b,r,material,role='source',sides=12):
        a,b=Vector(a),Vector(b)
        rotation=(b-a).to_track_quat('Z','Y');center=(a+b)/2;half=(b-a).length/2
        vertices=[center+rotation@Vector((r*math.cos(i*math.tau/sides),r*math.sin(i*math.tau/sides),z)) for z in [-half,half] for i in range(sides)]
        faces=[tuple(range(sides-1,-1,-1)),tuple(range(sides,sides*2))]
        faces += [(i,(i+1)%sides,(i+1)%sides+sides,i+sides) for i in range(sides)]
        return self.mesh(name,vertices,faces,material,role)

def roof(builder,volume,clay,plaster,timber):
    v=volume;x0=v.front-.43;x1=v.back+.43;xm=(x0+x1)/2;y0=v.start-.4;y1=v.end+.4
    vertices=[(x0,y0,v.eave),(x0,y1,v.eave),(xm,y0,v.ridge),(xm,y1,v.ridge),(x1,y0,v.eave),(x1,y1,v.eave)]
    vertices += [(x,y,z-.16) for x,y,z in vertices]
    builder.mesh(v.name+' roof',vertices,[(0,1,3,2),(2,3,5,4),(4,5,11,10),(10,11,9,8),(8,9,7,6),(6,7,1,0),(0,2,8,6),(2,4,10,8),(1,7,9,3),(3,9,11,5)],clay)
    for y,tag,face in [(v.start,'west',(0,1,2)),(v.end,'east',(2,1,0))]:
        builder.mesh(v.name+' '+tag+' gable',[(v.front,y,v.eave-.1),(xm,y,v.ridge-.13),(v.back,y,v.eave-.1)],[face],plaster)
    builder.part(v.name+' eave timber',(.23,y1-y0,.16),(x0+.035,(y0+y1)/2,v.eave-.15),timber)
    # Complex half-round tile source over a simple coherent runtime roof skin.
    for slope,(a,b,za,zb) in enumerate([(x0,xm,v.eave,v.ridge),(xm,x1,v.ridge,v.eave)]):
        count=max(1,math.ceil((y1-y0)/.235))
        for i in range(count):
            y=y0+(i+.5)*(y1-y0)/count
            builder.cylinder(f'{v.name} tile barrel {slope} {i}',(a,y,za+.045),(b,y,zb+.045),.052,clay,sides=10)
        for j in range(max(1,math.ceil(abs(b-a)/.34))):
            x=a+(b-a)*(j+.5)/max(1,math.ceil(abs(b-a)/.34));z=za+(zb-za)*(x-a)/(b-a)
            builder.part(f'{v.name} tile course {slope} {j}',(.055,y1-y0,.04),(x,(y0+y1)/2,z+.05),clay,'source',.008)

def shell(builder,volume,openings,plaster,clay,timber):
    v=volume;thick=.45
    before=set(builder.source.objects)
    record=bpy.data.objects.new(v.name+' volume',None);builder.source.objects.link(record)
    record['building_volume']=json.dumps(asdict(v));record['openings']=json.dumps(openings)
    # Tessellate an actual wall around apertures. Every opening belongs to a room.
    ys=sorted({v.start,v.end,*[edge for o in openings for edge in [o['y']-o['width']/2,o['y']+o['width']/2]]})
    zs=sorted({v.floor,v.eave,*[edge for o in openings for edge in [o['sill'],o['sill']+o['height']]]})
    for iy,(a,b) in enumerate(zip(ys,ys[1:])):
        for iz,(lo,hi) in enumerate(zip(zs,zs[1:])):
            cy,cz=(a+b)/2,(lo+hi)/2
            if any(abs(cy-o['y'])<o['width']/2 and o['sill']<cz<o['sill']+o['height'] for o in openings):continue
            if b-a>.001 and hi-lo>.001:builder.part(f'{v.name} wall {iy} {iz}',(thick,b-a,hi-lo),(v.front+thick/2,cy,cz),plaster)
    for y,tag in [(v.start,'west'),(v.end,'east')]:
        portal=v.start_portal if tag=='west' else v.end_portal
        if portal:
            center=7.10;width=1.10;head=v.floor+2.30
            for side,a,b in [('front',v.front,center-width/2),('rear',center+width/2,v.back)]:
                builder.part(v.name+' '+tag+' return '+side,(b-a,thick,v.eave-v.floor),((a+b)/2,y,(v.floor+v.eave)/2),plaster)
            builder.part(v.name+' '+tag+' portal head',(width,thick,v.eave-head),(center,y,(head+v.eave)/2),plaster)
        else:
            builder.part(v.name+' '+tag+' return',(v.back-v.front,thick,v.eave-v.floor),((v.front+v.back)/2,y,v.floor+(v.eave-v.floor)/2),plaster)
    builder.part(v.name+' rear',(thick,v.end-v.start,v.eave-v.floor),(v.back-thick/2,(v.start+v.end)/2,(v.floor+v.eave)/2),plaster)
    builder.part(v.name+' room floor',(v.back-v.front,v.end-v.start,.14),((v.front+v.back)/2,(v.start+v.end)/2,v.floor-.07),plaster)
    # A fixed level room can sit above the court's slope; its footing reaches
    # below grade without changing the map-owned traversal profile.
    if v.floor>0:
        builder.part(v.name+' continuous footing',(v.back-v.front+.10,v.end-v.start+.10,v.floor+.12),((v.front+v.back)/2,(v.start+v.end)/2,(v.floor-.12)/2),plaster)
    roof(builder,v,clay,plaster,timber)
    for obj in set(builder.source.objects)-before-{record}:
        obj.parent=record
        obj['building_owner']=v.name
        obj['construction_layer']='roof' if any(tag in obj.name for tag in ['roof','gable','tile barrel','tile course','eave timber']) else 'shell'
    record.parent=builder.root
    return record

def finish_material(name,color,roughness=.9,weather=False,grain=False):
    material=core.make_material(name,color=color,roughness=roughness)
    if weather:
        tree=material.node_tree;bsdf=tree.nodes['Principled BSDF'];geo=tree.nodes.new('ShaderNodeNewGeometry')
        noise=tree.nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=.8 if not grain else 2;noise.inputs['Detail'].default_value=3
        coordinates=geo.outputs['Position']
        if grain:
            stretch=tree.nodes.new('ShaderNodeVectorMath');stretch.operation='MULTIPLY'
            stretch.inputs[1].default_value=(15,15,.65)
            tree.links.new(coordinates,stretch.inputs[0]);coordinates=stretch.outputs['Vector']
        tree.links.new(coordinates,noise.inputs['Vector'])
        ramp=tree.nodes.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].position=.25;ramp.color_ramp.elements[1].position=.80
        ramp.color_ramp.elements[0].color=(*[c*.80 for c in color],1);ramp.color_ramp.elements[1].color=(*[min(c*1.08,1) for c in color],1)
        tree.links.new(noise.outputs['Fac'],ramp.inputs['Fac']);tree.links.new(ramp.outputs['Color'],bsdf.inputs['Base Color'])
        fine=tree.nodes.new('ShaderNodeTexNoise');fine.inputs['Scale'].default_value=95 if not grain else 9
        tree.links.new(coordinates,fine.inputs['Vector'])
        bump=tree.nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.18;bump.inputs['Distance'].default_value=.009
        tree.links.new(fine.outputs['Fac'],bump.inputs['Height']);tree.links.new(bump.outputs['Normal'],bsdf.inputs['Normal'])
    return material

def build(output):
    from architectural_surfaces import adapted_material,profile_surface
    if output.exists():raise FileExistsError('Refusing to overwrite editable source: '+str(output))
    library=ROOT/'tools/blender/vendor-library';manifest=verify(library)
    map_data=json.loads((CANDIDATE/'32.json').read_text(encoding='utf-8'));profile=map_data['traversal']['lane']['groundProfile']
    upper=profile[-1]['z']
    bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene;b=Builder()
    for name in ['TH_RENDER','TH_ANCHORS','TH_COLLISION','TH_PREVIEW_ACTORS']:core.ensure_collection(name)
    with bpy.data.libraries.load(str(library/'library/selected_materials.blend'),link=False) as (available,loaded):
        loaded.materials=[r['asset'] for r in manifest['assets']]
    upstream={m.name:m for m in loaded.materials}
    clay=adapted_material(upstream['Clay'],'Court fired terracotta',(.37,.12,.055),Bump=.22,Roughness=.88)
    paving=adapted_material(upstream['Bricks - Cobblestone'],'Court granite setts',(.27,.30,.26),**{'Width':.42,'Height':.28,'Grout Width':.008,'Bump':.13,'Roughness':.95})
    linen=adapted_material(upstream['Fabric - Linen'],'Court wash linen',(.71,.66,.50),**{'Bump':.15,'Translucency':.08,'Subsurface Weight':0})
    plaster=finish_material('Court warm limewash',(.76,.74,.61),weather=True)
    stone=finish_material('Court limestone',(.55,.56,.48),weather=True)
    darkstone=finish_material('Court damp stone',(.23,.28,.25),weather=True)
    wood=finish_material('Court dark timber',(.10,.051,.026),weather=True,grain=True)
    sash=finish_material('Court bone painted sash',(.59,.64,.55),roughness=.76)
    shutter=finish_material('Court sage shutter',(.095,.22,.17),weather=True,grain=True)
    iron=finish_material('Court wrought iron',(.025,.030,.024),roughness=.75)
    glass=finish_material('Court blue reflected glass',(.16,.25,.27),roughness=.13)
    glass.node_tree.nodes['Principled BSDF'].inputs['Metallic'].default_value=.50
    glass.node_tree.nodes['Principled BSDF'].inputs['Coat Weight'].default_value=.7
    blue=finish_material('Court cobalt glazed tile',(.035,.11,.24),roughness=.35)
    mat={'sash':sash,'stone':stone,'glass':glass,'shutter':shutter,'iron':iron}
    extended=[{'y':-16,'z':profile[0]['z']},*profile,{'y':32,'z':profile[-1]['z']}]
    floor=profile_surface('COURT_profile_paving',extended,-24,19,b.source,paving,depth_step=.65);floor['sr_bake_open_surface']=True;floor['profile_map']='32.json'
    collision=bpy.data.collections['TH_COLLISION'];profile_surface('COL_profile_walk',profile,-.75,.75,collision,bake=False)
    # Three attached volumes are one lodging: bedrooms, arrival hall, service wing.
    primary=[Window('Court casement '+str(i),4.5,y,upper+.92,width=1.35,height=1.75,shutter_angles=angles) for i,(y,angles) in enumerate([(.5,(95,140)),(3.5,(125,75)),(6.8,(105,130))])]
    wing=Volume('Sleeping wing',4.5,9.5,-1.7,8.45,upper,3.80,5.05,end_portal=True)
    wing_root=shell(b,wing,[{'y':s.y,'width':s.width,'height':s.height,'sill':s.sill} for s in primary],plaster,clay,wood)
    for s in primary:window(b,s,mat).parent=wing_root
    hall=Volume('Arrival hall',4.5,10.8,8.45,14.45,upper,4.45,5.75,start_portal=True,end_portal=True)
    hall_root=shell(b,hall,[{'y':11.5,'width':2.08,'height':3.55,'sill':upper}],plaster,clay,wood)
    service=Volume('Service wing',4.5,9.5,14.45,21.0,upper,3.6,4.85,start_portal=True)
    service_root=shell(b,service,[{'y':17.1,'width':1.2,'height':1.6,'sill':1.3}],plaster,clay,wood)
    window(b,Window('Court service casement',4.5,17.1,1.3,1.2,1.6),mat).parent=service_root
    # Inner door leaf sits in a genuinely deep, enclosed entrance volume.
    host=type('DoorHost',(),{})();host.back_x=4.82;host.wood=finish_material('Court honey timber door',(.27,.115,.042),weather=True,grain=True)
    host.stone=stone;host.terracotta=clay;host.iron=iron;host.y=lambda value:value
    host.part=lambda name,size,position,material:b.part(name,size,position,material,'source',.008)
    door(host,'Court inner panelled door',11.5,width=1.42,height=2.55,panels=4,panel_material=host.wood,source=True,retain_shape=True,base_z=upper,receiver_collection=b.source)
    b.receiver('Court door leaf target',4.70,11.5,upper+2.55/2,1.42,2.55,host.wood)
    b.part('Court portal threshold',(.76,2.02,.06),(4.34,11.5,upper+.03),stone,bevel=.015)
    for sign in [-1,1]:
        b.part(f'Court portal pier {sign}',(.39,.26,2.51),(4.31,11.5+sign*1.17,upper+2.51/2),stone,bevel=.025)
        # Deep splayed reveal closes the space from masonry mouth to inner door.
        yfront=11.5+sign*1.04;yback=11.5+sign*.89
        # Finish at the front of the timber jamb, not behind it. A closed
        # thin masonry return has one aperture-facing surface, not coincident
        # opposite faces that bake the inside of the entrance onto the outside.
        front=[Vector(p) for p in [(4.50,yfront,upper),(4.50,yfront,upper+2.51),(4.62,yback,upper+2.51),(4.62,yback,upper)]]
        if sign>0: front.reverse()
        normal=(front[1]-front[0]).cross(front[2]-front[0]).normalized()
        vertices=front+[p-normal*.08 for p in front]
        b.mesh(f'Court portal splayed reveal {sign}',vertices,[(0,1,2,3),(7,6,5,4),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)],stone)

    # Segmental arch of wedge-cut masonry above the open portal.
    radius=1.04;spring=upper+2.51
    for i in range(13):
        a=math.pi*i/13;c=math.pi*(i+1)/13;outside=radius+.26
        vertices=[(x,11.5+r*math.cos(t),spring+r*math.sin(t)) for x in [4.10,4.51] for r,t in [(radius,a),(radius,c),(outside,c),(outside,a)]]
        b.mesh(f'Court stone arch {i}',vertices,[(0,1,2,3),(7,6,5,4),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)],stone)
        # Solid spandrel above the curved aperture closes the rectangular wall cut.
        ya,yc=11.5+radius*math.cos(a),11.5+radius*math.cos(c)
        za,zc=spring+radius*math.sin(a),spring+radius*math.sin(c)
        vertices=[(x,y,z) for x in [4.5,4.95] for y,z in [(ya,za),(yc,zc),(yc,3.85),(ya,3.85)]]
        b.mesh(f'Court arch masonry spandrel {i}',vertices,[(0,1,2,3),(7,6,5,4),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)],plaster)
    # Glazed fanlight closes the hall above the door; radial muntins remain source detail.
    fan_base=upper+2.93
    first_angle=math.asin((fan_base-spring)/radius)
    fan=[(4.88,11.5,fan_base)]+[(4.88,11.5+radius*math.cos(first_angle+(math.pi-2*first_angle)*i/16),spring+radius*math.sin(first_angle+(math.pi-2*first_angle)*i/16)) for i in range(17)]
    b.mesh('Court portal fanlight',fan,[(0,i+1,i) for i in range(1,17)],glass)
    chord=2*math.sqrt(radius*radius-(fan_base-spring)**2)
    b.part('Court fanlight bottom rail',(.075,chord+.045,.055),(4.84,11.5,fan_base-.012),wood,'source')
    for i in range(1,6):
        angle=first_angle+(math.pi-2*first_angle)*i/6
        b.cylinder(f'Court fanlight radial bead {i}',(4.855,11.5,fan_base),(4.855,11.5+radius*math.cos(angle),spring+radius*math.sin(angle)),.024,wood)
    # Veranda is an attached roof with pitched tiles and a legible timber structure.
    x0,x1,y0,y1=-1.55,4.66,8.08,13.78
    vertices=[(x,y,z) for x,z in [(x0,3.38),(x1,4.14),(x0,3.24),(x1,4.0)] for y in [y0,y1]]
    b.mesh('Court covered veranda roof',vertices,[(0,1,3,2),(2,3,7,6),(6,7,5,4),(4,5,1,0),(0,2,6,4),(1,5,7,3)],clay)
    for j in range(25):
        y=y0+.11+j*.225;b.cylinder(f'Veranda tile barrel {j}',(x0,y,3.42),(x1,y,4.18),.05,clay,sides=10)
    b.part('Veranda fascia',(.22,5.95,.23),(x0,10.93,3.30),wood,bevel=.018)
    for y in [8.23,13.53]:
        b.part(f'Veranda post {y}',(.21,.21,2.83),(x0,y,1.795),wood,bevel=.015)
        b.part(f'Veranda foot {y}',(.35,.35,.25),(x0,y,.425),stone,bevel=.025)
        b.cylinder(f'Veranda knee brace {y}',(x0,y,2.49),(x0+.82,y,3.22),.065,wood,'both',8)
        pitch=math.atan2(.76,x1-x0)
        rafter=b.part(f'Veranda rafter {y}',(6.1/math.cos(pitch),.13,.19),(1.555,y,3.50),wood,bevel=.008)
        rafter.rotation_euler.y=-pitch
    # The backstreet has complete two-storey volumes, rather than a detached skyline.
    for name,front,a,c,eave,ridge,color in [('West street',12.3,-16,-1.8,6.3,7.5,(.62,.37,.17)),('Rear street',13.8,-1.8,14.5,7.15,8.4,(.62,.58,.45)),('East street',12.1,14.5,32,6.6,7.8,(.50,.29,.21))]:
        wall=finish_material(name+' limewash',color,weather=True)
        spec=Volume(name,front,front+4,a,c,0,eave,ridge)
        upper=[Window(name+' window '+str(i),front,y,4.1,1.05,1.55,shutters=True) for i,y in enumerate([a+(c-a)*.28,a+(c-a)*.69])]
        street_root=shell(b,spec,[{'y':s.y,'width':s.width,'height':s.height,'sill':s.sill} for s in upper],wall,clay,wood)
        for s in upper:window(b,s,mat).parent=street_root
        b.part(name+' floor stringcourse',(.16,c-a,.17),(front-.045,(a+c)/2,3.6),stone).parent=street_root
        b.part(name+' chimney',(.64,.58,1.1),(front+2,(a+c)/2,eave+1.0),wall).parent=street_root
        b.part(name+' chimney crown',(.82,.75,.16),(front+2,(a+c)/2,eave+1.58),stone).parent=street_root
    # Court edge walls connect to buildings and enclose the yard below eye level.
    for y in [-2.1,14.4]:
        spans=[(-6.5,-1.35),(1.35,4.5)] if y<0 else [(-6.5,4.5)]
        for a,c in spans:
            b.part(f'Court enclosing wall {y} {a}',(c-a,.35,.90),((a+c)/2,y,.45),plaster)
            b.part(f'Court wall coping {y} {a}',(c-a+.10,.48,.12),((a+c)/2,y,.96),stone,bevel=.025)
    # The lower lane continues through a visible street opening, clear of the facade.
    for x in [-1.50,1.50]:
        b.part(f'Cortico passage pier {x}',(.32,.44,2.75),(x,-2.1,1.375),plaster,bevel=.025)
        b.part(f'Cortico passage pier cap {x}',(.44,.55,.16),(x,-2.1,2.83),stone,bevel=.02)
    b.part('Cortico passage lintel',(3.40,.45,.23),(0,-2.1,2.81),wood,bevel=.025)
    # Rich ceramic source decoration bakes onto the existing masonry wall.
    # The band belongs to the sleeping wing; no extra runtime tile geometry.
    band_floor=profile[-1]['z']
    ceramic=finish_material('Court chalk ceramic',(.76,.78,.70),roughness=.48)
    border=finish_material('Court muted cobalt border',(.045,.13,.23),roughness=.5)
    for i in range(38):
        yy=-1.58+i*.26;zz=band_floor+.61
        b.part(f'Court azulejo field {i}',(.018,.251,.46),(4.484,yy,zz),ceramic,'source',.004)
        # Four lobes read as a small flower rather than a high-frequency grid.
        for j in range(4):
            angle=j*math.pi/2;cy=yy+.058*math.cos(angle);cz=zz+.058*math.sin(angle)
            points=[(4.472,cy+.052*math.cos(k*math.tau/12),cz+.052*math.sin(k*math.tau/12)) for k in range(12)]
            b.mesh(f'Court azulejo petal {i} {j}',points,[tuple(range(11,-1,-1))],blue,'source')
    for zz in [band_floor+.36,band_floor+.86]:
        b.part(f'Court ceramic border {zz}',(.02,9.9,.038),(4.473,3.35,zz),border,'source')
    # A fountain niche, bench and washing implements give this arrival court a use.
    b.part('Court fountain ceramic panel',(.08,1.8,1.45),(4.38,5.0,1.1),stone)
    for row in range(5):
        for col in range(7):
            yy=4.2+col*.265;zz=.55+row*.25
            b.mesh(f'Court ceramic diamond {row} {col}',[(4.326,yy-.075,zz),(4.326,yy,zz+.075),(4.326,yy+.075,zz),(4.326,yy,zz-.075)],[(0,1,2,3)],blue,'source')
    b.part('Fountain basin',(.85,1.65,.14),(3.84,5,.33),stone,bevel=.055)
    for y in [4.2,5.8]:b.part(f'Fountain rim {y}',(.9,.14,.34),(3.84,y,.52),stone,bevel=.025)
    b.part('Fountain front rim',(.14,1.65,.34),(3.37,5,.52),stone,bevel=.025)
    b.part('Fountain water',(.7,1.42,.035),(3.82,5,.57),glass)
    b.cylinder('Fountain iron spout',(4.27,5,1.13),(3.93,5,1.13),.035,iron,'both')
    b.part('Fountain cap',(.24,1.98,.14),(4.33,5,1.89),stone,bevel=.02)
    b.part('Linen towel',(.025,.51,.73),(4.25,5.8,1.02),linen,'source')
    b.part('Court resting bench',(.64,1.62,.12),(3.36,7.99,.73),wood,bevel=.015)
    for y in [7.37,8.61]:b.part(f'Bench foot {y}',(.15,.15,.44),(3.36,y,.45),wood)
    for i,(y,r,h) in enumerate([(6.2,.25,.54),(6.7,.18,.4)]):
        rings=[(0,r*.55),(.045,r*.64),(h*.68,r),(h*.97,r*.75),(h,r*.80),(h,r*.64),(h*.77,r*.64)]
        vertices=[(2.88+radius*math.cos(k*math.tau/16),y+radius*math.sin(k*math.tau/16),.25+z) for z,radius in rings for k in range(16)]
        faces=[(row*16+k,row*16+(k+1)%16,(row+1)*16+(k+1)%16,(row+1)*16+k) for row in range(len(rings)-1) for k in range(16)]
        b.mesh(f'Court hollow pottery {i}',vertices,faces,clay)
    # Decorative stones obtain their heights from the authored paving mesh.
    pathmat=finish_material('Court worn pale stones',(.51,.51,.42),weather=True)
    for row in range(28):
        for col in range(4):
            x=-.72+col*.48;y=.17+row*.425
            hit,point,normal,index=floor.ray_cast(Vector((x,y,10)),Vector((0,0,-1)))
            if not hit:raise ValueError('Missing authored floor beneath path')
            b.part(f'Court path stone {row} {col}',(.45,.39,.012),(x,y,point.z+.008),pathmat,'source',.02)
    # The camera-side court boundary is a continuous architectural near rank.
    # Broad masonry fills the lower frame; it stays well outside the walk lane.
    # Its coping follows the map profile, rather than creating another datum.
    for start,end in [(-16,2),(2,8),(8,32)]:
        def height(y):
            return 0 if y<=2 else .30 if y>=8 else (y-2)*.05
        xa,xb=-13.8,-12.6
        verts=[(x,y,height(y)+z) for z in [0,.46] for y in [start,end] for x in [xa,xb]]
        faces=[(0,2,3,1),(4,5,7,6),(0,1,5,4),(2,6,7,3),(0,4,6,2),(1,3,7,5)]
        b.mesh(f'Court foreground boundary {start}',verts,faces,plaster)
        cap=[(x,y,height(y)+z) for z in [.46,.57] for y in [start,end] for x in [xa-.08,xb+.08]]
        b.mesh(f'Court foreground coping {start}',cap,faces,stone)
    # Short inward returns make the perimeter read as an enclosed courtyard.
    for y in [-2.1,14.4]:
        z=0 if y<2 else .30
        b.part(f'Court foreground return {y}',(6.7,.42,.46),(-9.25,y,z+.23),plaster)
        b.part(f'Court foreground return cap {y}',(6.8,.58,.11),(-9.25,y,z+.515),stone,bevel=.02)
    # A communal wash cistern belongs to the camera-side boundary. Its full
    # hollow volume is authored; only bevels and ceramic decoration bake down.
    # Horizontal water/rim levels sit above foundations sampled from the paving.
    near_x,far_x=-17.15,-14.0
    start_y,end_y=4.0,8.0
    rim_z=.78
    def foundation(x,y):
        hit,point,normal,index=floor.ray_cast(Vector((x,y,10)),Vector((0,0,-1)))
        if not hit:raise ValueError('Missing paving under wash cistern')
        return point.z
    corners=[(near_x,start_y+.48),(near_x+.48,start_y),(far_x-.48,start_y),(far_x,start_y+.48),(far_x,end_y-.48),(far_x-.48,end_y),(near_x+.48,end_y),(near_x,end_y-.48)]
    bottom=[(x,y,foundation(x,y)+.035) for x,y in corners]
    b.mesh('Court cistern foundation',bottom,[tuple(range(len(corners)))],stone)
    for label,(a,c) in enumerate(zip(corners,corners[1:]+corners[:1])):
        ax,ay=a;cx,cy=c
        base=min(foundation(ax,ay),foundation(cx,cy))
        length=math.hypot(cx-ax,cy-ay)
        angle=math.atan2(cy-ay,cx-ax)
        wall=b.part(f'Court cistern wall {label}',(length,.24,rim_z-base),((ax+cx)/2,(ay+cy)/2,(base+rim_z)/2),plaster,'source',.035)
        wall.rotation_euler.z=angle
        box_receiver(wall,b.source)
        cap=b.part(f'Court cistern coping {label}',(length+.12,.37,.10),((ax+cx)/2,(ay+cy)/2,rim_z+.015),stone,'source',.025)
        cap.rotation_euler.z=angle
        box_receiver(cap,b.source)
    water=finish_material('Court cistern still water',(.055,.12,.13),roughness=.18)
    bsdf=water.node_tree.nodes['Principled BSDF'];bsdf.inputs['Metallic'].default_value=.35
    bsdf.inputs['Coat Weight'].default_value=.6
    noise=water.node_tree.nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=3
    noise.inputs['Detail'].default_value=2
    geometry=water.node_tree.nodes.new('ShaderNodeNewGeometry')
    bump=water.node_tree.nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.18;bump.inputs['Distance'].default_value=.012
    water.node_tree.links.new(geometry.outputs['Position'],noise.inputs['Vector'])
    water.node_tree.links.new(noise.outputs['Fac'],bump.inputs['Height']);water.node_tree.links.new(bump.outputs['Normal'],bsdf.inputs['Normal'])
    centre=Vector(((near_x+far_x)/2,(start_y+end_y)/2,0))
    inside=[Vector((x,y,0))+(centre-Vector((x,y,0))).normalized()*.17 for x,y in corners]
    b.mesh('Court cistern water',[(p.x,p.y,.66) for p in inside],[tuple(range(8))],water)
    # A broad inner ceramic band and carved washboard ridges read at native size.
    for j in range(14):
        yy=start_y+.54+j*(end_y-start_y-1.08)/14
        b.part(f'Court cistern inner ceramic {j}',(.025,.198,.22),(far_x-.135,yy,.64),blue,'source',.004)
    for j in range(9):
        xx=near_x+.4+j*.12
        b.part(f'Court cistern washboard ridge {j}',(.045,.85,.025),(xx,start_y+.51,rim_z+.055),stone,'source',.01)
    # A folded wash cloth retains its broad drape silhouette; small folds bake.
    sections=[(far_x+.16,.86),(far_x-.18,.86),(far_x-.22,.82),(far_x-.22,.69)]
    cloth_vertices=[(x,y,z) for x,z in sections for y in [6.65,7.45]]
    cloth=b.mesh('Court cistern folded linen',cloth_vertices,[(2*i,2*i+1,2*i+3,2*i+2) for i in range(3)],linen)
    cloth['sr_bake_open_surface']=True
    channel=finish_material('Court drain shadow',(.10,.13,.12),roughness=1)
    for i in range(40):
        yy=-5+i*.65
        hit,point,normal,index=floor.ray_cast(Vector((-2.6,yy,10)),Vector((0,0,-1)))
        if not hit:raise ValueError('Missing paving beneath drainage')
        b.part(f'Court drainage course {i}',(.21,.61,.012),(-2.6,yy,point.z+.009),darkstone,'source',.015)
        for k in range(3):
            b.part(f'Court drain slot {i} {k}',(.11,.035,.004),(-2.6,yy+(k-1)*.15,point.z+.018),channel,'source')
    # Persist the map-owned anchors and complete camera calibration.
    anchors=bpy.data.collections['TH_ANCHORS']
    for event in map_data['events']:
        name=next(d['anchor'] for d in map_data['traversal']['doorways'] if d['eventInstanceId']==event['instanceId'])
        obj=bpy.data.objects.new(name,None);anchors.objects.link(obj);obj.location=event['worldPosition']
    spawn=bpy.data.objects.new('spawn_player',None);anchors.objects.link(spawn);spawn.location=(0,1,0)
    world=bpy.data.worlds.new('Court dusk sky');world.use_nodes=True;scene.world=world
    world.node_tree.nodes['Background'].inputs['Color'].default_value=(.14,.23,.39,1);world.node_tree.nodes['Background'].inputs['Strength'].default_value=.32
    sun_data=bpy.data.lights.new('Court western sun','SUN');sun_data.energy=2.1;sun_data.angle=math.radians(6);sun_data.color=(1,.82,.65)
    sun=bpy.data.objects.new(sun_data.name,sun_data);scene.collection.objects.link(sun);sun.rotation_euler=Vector((1,.8,-1.7)).to_track_quat('-Z','Y').to_euler()
    sky_data=bpy.data.lights.new('Court blue skylight','AREA');sky_data.energy=380;sky_data.size=18;sky_data.color=(.63,.75,1)
    sky=bpy.data.objects.new(sky_data.name,sky_data);scene.collection.objects.link(sky);sky.location=(-2,6,12);sky.rotation_euler=(Vector((4,6,1))-sky.location).to_track_quat('-Z','Y').to_euler()
    lamp=finish_material('Court lantern glass',(1,.38,.08),roughness=.4)
    lamp.node_tree.nodes['Principled BSDF'].inputs['Emission Color'].default_value=(1,.30,.05,1);lamp.node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].default_value=3
    for y in [9.7,13.3]:
        b.part(f'Lantern glass {y}',(.16,.19,.29),(4.13,y,2.65),lamp)
        for zz in [2.48,2.81]:b.part(f'Lantern cap {y} {zz}',(.25,.26,.065),(4.13,y,zz),iron)
        for side in [-1,1]:b.part(f'Lantern bar {y} {side}',(.19,.025,.29),(4.13,y+side*.095,2.65),iron)
        data=bpy.data.lights.new(f'Court lantern light {y}','POINT');data.energy=24;data.color=(1,.37,.09);data.shadow_soft_size=.15
        light=bpy.data.objects.new(data.name,data);scene.collection.objects.link(light);light.location=(3.91,y,2.65)
    # Light under the veranda is tied to a visible ceiling lantern, not exposure.
    b.part('Entry ceiling lantern glass',(.24,.26,.12),(3.0,11.5,3.67),lamp)
    b.part('Entry ceiling lantern rim',(.30,.32,.045),(3.0,11.5,3.74),iron)
    entry_data=bpy.data.lights.new('Entry ceiling lantern light','AREA');entry_data.energy=48
    entry_data.color=(1,.62,.27);entry_data.shape='DISK';entry_data.size=.35
    entry=bpy.data.objects.new(entry_data.name,entry_data);scene.collection.objects.link(entry);entry.location=(3.0,11.5,3.53)
    entry.rotation_euler=(Vector((4.8,11.5,1.6))-entry.location).to_track_quat('-Z','Y').to_euler()
    camera=thestra_camera.create_or_update_camera(thestra_camera.load_calibration(str(CANDIDATE/'camera.json')),make_active=True)
    actor=thestra_camera.create_actor_preview(ROOT/'projects/hichaukitoden-game/assets/character/walker.png',camera,anchor=(0,6,.2),world_height=1.75)
    core.move_to_collection(actor,bpy.data.collections['TH_PREVIEW_ACTORS'])
    for name in ['TH_RENDER','TH_COLLISION','TH_ANCHORS','TH_PREVIEW_ACTORS']:bpy.data.collections[name].hide_render=True
    saved_profile=render_profiles.apply(scene,render_profiles.resolve('export'),device=render_profiles.DEFAULT_DEVICE)
    scene['saved_render_profile']=json.dumps(saved_profile)
    scene['export_atlas_size']=render_profiles.DEFAULT_ATLAS_SIZE
    scene['export_atlas_view_bias']=1.0
    scene['render_settings_note']='Classic 256x240 preview, Cycles 64 render/viewport samples, OIDN, neutral exposure; export atlas 1024. Device availability belongs to the launching Blender process.'
    scene.view_settings.view_transform='AgX'
    scene.eevee.use_raytracing=True;scene.eevee.use_fast_gi=True;scene.eevee.fast_gi_method='AMBIENT_OCCLUSION_ONLY';scene.eevee.fast_gi_distance=3
    scene['courtyard_revision']=17;scene['candidate_map']=json.dumps(map_data);scene['source_profile_authority']='candidate/32.json'
    scene['authoring_paradigm']='connected closed building volumes with aperture-owned architectural assemblies; rich source / simple targets'
    bpy.context.view_layer.update()
    counts={'both':0,'source':0,'receiver':0};source_triangles=0
    graph=bpy.context.evaluated_depsgraph_get()
    for obj in b.source.all_objects:
        if obj.type!='MESH':continue
        role=obj.get('sr_bake_role','both');counts[role]+=1
        if role=='receiver':continue
        evaluated=obj.evaluated_get(graph);data=evaluated.to_mesh();data.calc_loop_triangles()
        source_triangles+=len(data.loop_triangles);evaluated.to_mesh_clear()
    scene['source_beauty_triangles']=source_triangles;scene['source_mesh_roles']=json.dumps(counts)
    bpy.ops.file.pack_all();output.parent.mkdir(parents=True,exist_ok=True);bpy.ops.wm.save_as_mainfile(filepath=str(output))
    print('COURTYARD SOURCE OK',output)
