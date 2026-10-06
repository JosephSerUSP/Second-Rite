"""Create NEW B009 source assets; never overwrite adopted Blender sources.
Run through tools/blender/run.py. Re-exports use --blend and --export-only.
Original fan-study geometry; no extracted commercial models or textures.
"""
import bpy, math, sys
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"assets/authoring/environments/b009_encounter.blend"
OUT=ROOT/"assets/models/b009"
OUT.mkdir(parents=True,exist_ok=True)
def material(name,color):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1)
    m.use_nodes=True
    m.node_tree.nodes.get("Principled BSDF").inputs["Base Color"].default_value=(*color,1)
    return m
def part(name,kind,loc,scale,mat,rot=None):
    if kind=="box": bpy.ops.mesh.primitive_cube_add(size=1,location=loc)
    elif kind=="sphere": bpy.ops.mesh.primitive_uv_sphere_add(segments=12,ring_count=6,radius=1,location=loc)
    elif kind=="cylinder": bpy.ops.mesh.primitive_cylinder_add(vertices=12,radius=1,depth=1,location=loc)
    elif kind=="cone": bpy.ops.mesh.primitive_cone_add(vertices=12,radius1=1,radius2=.45,depth=1,location=loc)
    ob=bpy.context.object;ob.name=name;ob.scale=scale
    if rot: ob.rotation_euler=rot
    ob.data.materials.append(mat);return ob
def bone(name,a,b,width,mat):
    d=Vector(b)-Vector(a);ob=part(name,"cylinder",(Vector(a)+Vector(b))/2,(width,width,d.length),mat)
    ob.rotation_euler=d.to_track_quat('Z','Y').to_euler();return ob
def collection(name):
    c=bpy.data.collections.new(name);bpy.context.scene.collection.children.link(c);return c
def move_new(c,before):
    for ob in list(bpy.context.scene.objects):
        if ob.name not in before:
            for old in list(ob.users_collection): old.objects.unlink(ob)
            c.objects.link(ob)
def build():
    bpy.ops.object.select_all(action="SELECT");bpy.ops.object.delete(use_global=False)
    wood=material("Warm walnut",(.3,.13,.065));gold=material("Aged gold",(.7,.48,.18))
    plaster=material("Ivory plaster",(.72,.64,.49));red=material("Velvet crimson",(.42,.025,.045))
    carpet=material("Deep red carpet",(.22,.035,.045));black=material("Dress black",(.035,.045,.07))
    skin=material("Aya skin",(.9,.69,.51));hair=material("Aya blonde",(.76,.55,.22))
    metal=material("Gun steel",(.25,.3,.34));eye=material("Eyes",(.03,.1,.13))
    fur=material("Rat fur",(.26,.19,.14));pink=material("Rat tail",(.53,.24,.23))
    tooth=material("Fangs",(.85,.8,.62));glow=material("Rat eyes",(.98,.11,.025))
    hall=collection("hall");before=set(bpy.data.objects.keys())
    part("Auditorium floor","box",(0,5,-.16),(19,22,.3),wood)
    part("Central aisle","box",(0,4,.012),(6.7,13,.025),carpet)
    # Stage beyond the combat aisle, framed by a proscenium.
    part("Stage","box",(0,13,.5),(16,5,1),wood)
    part("Stage rear","box",(0,15,4),(18,.35,8),black)
    for x in (-7.8,7.8):
        part("Proscenium column","box",(x,12,4),(1,1.3,8),plaster)
        part("Gold column inset","box",(x,11.28,4),(.28,.08,7.5),gold)
        for z in (1,7.5): part("Column capital","box",(x,12,z),(1.6,1.5,.3),gold)
    part("Stage arch lintel","box",(0,12,8),(17,1.2,.6),gold)
    for x in [i*.32 for i in range(-22,23)]:
        if abs(x)<4.7: continue
        part("Velvet curtain fold","cylinder",(x,12.7,4.5),(.23,.25,7),red)
    part("Curtain valance","box",(0,12.5,7.55),(14,.5,1.0),red)
    # Curved seating blocks leave a real six-metre central aisle.
    for row in range(8):
        y=-.8+row*1.35
        for sign in (-1,1):
            for seat in range(5):
                x=sign*(4.0+seat*.83);yy=y+abs(x)*.04
                part("Seat cushion","box",(x,yy,.52),(.66,.66,.22),red)
                part("Seat back","box",(x,yy-.35,.96),(.67,.18,.86),red)
                for arm in (-.38,.38):part("Seat arm","box",(x+arm,yy,.72),(.09,.65,.12),wood)
    for sign in (-1,1):
        x=sign*9.1
        part("Side wall","box",(x,6.5,4.5),(.5,21,9),plaster)
        for z in (3.5,6.3):
            part("Balcony floor","box",(sign*8.2,6.5,z),(1.7,20,.28),wood)
            part("Balcony rail","box",(sign*7.4,6.5,z+.6),(.15,20,.18),gold)
            for y in range(-3,16,2):
                part("Balcony baluster","cylinder",(sign*7.4,y,z+.35),(.08,.08,.65),gold)
        for y in range(-2,16,4):
            part("Pilaster","box",(sign*8.8,y,4.5),(.3,.45,8),gold)
    # Low chandelier silhouette overhead; camera stays below it.
    for x in (-2.8,2.8):
        bone("Chandelier chain",(x,8,6.7),(x,8,8),.04,gold)
        for i in range(8):
            a=i*math.tau/8
            bone("Chandelier arm",(x,8,6.8),(x+math.cos(a)*.9,8+math.sin(a)*.9,6.8),.045,gold)
            part("Lamp","sphere",(x+math.cos(a)*.9,8+math.sin(a)*.9,7),(.13,.13,.21),tooth)
    move_new(hall,before)
    aya=collection("aya");before=set(bpy.data.objects.keys())
    # Aya's opening evening dress, tied blonde hair and two-handed handgun.
    for x in (-.16,.16):
        bone("Leg",(x,0,.18),(x,0,.87),.075,skin)
        part("Boot","box",(x,-.065,.12),(.17,.32,.23),black)
    part("Dress skirt","cone",(0,0,.89),(.4,.25,.56),black)
    part("Dress bodice","sphere",(0,0,1.29),(.28,.18,.34),black)
    bone("Neck",(0,0,1.48),(0,0,1.64),.075,skin)
    part("Face","sphere",(0,-.01,1.78),(.15,.14,.21),skin)
    part("Hair cap","sphere",(0,.02,1.87),(.16,.15,.17),hair)
    part("Ponytail","sphere",(0,.17,1.69),(.08,.11,.24),hair)
    for x in (-.055,.055): part("Eye","sphere",(x,-.142,1.8),(.021,.015,.013),eye)
    bone("Right upper arm",(.27,0,1.43),(.32,-.27,1.31),.065,skin)
    bone("Right forearm",(.32,-.27,1.31),(.13,-.5,1.42),.052,skin)
    bone("Left upper arm",(-.27,0,1.43),(-.31,-.23,1.31),.065,skin)
    bone("Left forearm",(-.31,-.23,1.31),(.05,-.46,1.42),.052,skin)
    part("Pistol slide","box",(.12,-.61,1.47),(.095,.34,.075),metal)
    part("Pistol grip","box",(.12,-.48,1.38),(.07,.1,.17),black)
    move_new(aya,before)
    rat=collection("rat");before=set(bpy.data.objects.keys())
    part("Rat body","sphere",(0,.2,.52),(.47,.68,.38),fur)
    part("Rat shoulders","sphere",(0,-.25,.57),(.41,.37,.38),fur)
    part("Rat head","sphere",(0,-.54,.54),(.28,.34,.27),fur)
    part("Rat muzzle","cone",(0,-.82,.5),(.18,.18,.34),fur,(math.pi/2,0,0))
    part("Rat nose","sphere",(0,-1,.5),(.07,.055,.055),pink)
    for sign in (-1,1):
        part("Rat ear","sphere",(sign*.24,-.36,.85),(.15,.085,.18),pink)
        part("Rat eye","sphere",(sign*.205,-.73,.65),(.065,.04,.06),glow)
        for y in (-.27,.6):
            bone("Rat leg",(sign*.31,y,.43),(sign*.48,y-.08,.12),.075,fur)
            for claw in range(3):
                bone("Rat claw",(sign*.48+(claw-1)*.075,y-.1,.1),(sign*.48+(claw-1)*.075,y-.32,.08),.025,tooth)
        bone("Mutated fang",(sign*.1,-.86,.53),(sign*.1,-.87,.31),.04,tooth)
        for z in (.43,.5,.57):
            bone("Whisker",(sign*.13,-.87,z),(sign*.55,-.94,z+.04),.009,tooth)
    tail=[(0,.7,.48),(.3,1.1,.35),(.65,1.5,.2),(.8,1.9,.12),(.65,2.25,.09)]
    for a,b in zip(tail,tail[1:]):bone("Rat tail",a,b,.045,pink)
    move_new(rat,before)
    spark=collection("spark");before=set(bpy.data.objects.keys())
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1,radius=.15,location=(0,0,0))
    bpy.context.object.data.materials.append(material("Muzzle gold",(1,.75,.2)))
    move_new(spark,before)
    for name,col in [("range",material("Range gold",(.7,.62,.18))),("danger",material("Danger crimson",(.85,.07,.02)))]:
        c=collection(name);before=set(bpy.data.objects.keys())
        bpy.ops.mesh.primitive_torus_add(major_segments=64,minor_segments=6,location=(0,0,.035),major_radius=1,minor_radius=.022)
        bpy.context.object.data.materials.append(col);move_new(c,before)
    bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE))
def export():
    for name in ("hall","aya","rat","range","danger","spark"):
        if name not in bpy.data.collections:
            raise RuntimeError("Source collection missing: "+name)
        bpy.ops.object.select_all(action="DESELECT")
        for ob in bpy.data.collections[name].objects: ob.select_set(True)
        bpy.ops.wm.obj_export(filepath=str(OUT/(name+".obj")),export_selected_objects=True,
            forward_axis="NEGATIVE_Z",up_axis="Y",export_materials=True,export_triangulated_mesh=True)
    import hashlib, json
    files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(OUT.glob("*")) if p.suffix in (".obj",".mtl")}
    (OUT/"provenance.json").write_text(json.dumps({"source":"assets/authoring/environments/b009_encounter.blend",
        "sourceSha256":hashlib.sha256(SOURCE.read_bytes()).hexdigest(),"blenderVersion":bpy.app.version_string,
        "basis":"Original low-poly fan-study models, not commercial asset extracts","files":files},indent=2)+"\n")
if "--export-only" not in sys.argv:
    if SOURCE.exists(): raise RuntimeError("Source exists; open it and export with --export-only, never regenerate")
    SOURCE.parent.mkdir(parents=True,exist_ok=True);build()
export()
