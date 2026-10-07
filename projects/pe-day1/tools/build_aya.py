"""Aya Brea (Day 1 evening dress) as a posed, low-poly character source.

    python tools/blender/run.py projects/pe-day1/tools/build_aya.py              # first build + export
    python tools/blender/run.py projects/pe-day1/tools/build_aya.py --blend projects/pe-day1/assets/authoring/characters/aya.blend -- --export-only

The first run creates assets/authoring/characters/aya.blend: one collection per
pose (idle, an 8-frame walk cycle, recoil, down). After that the .blend is the
authority -- edit poses in Blender and re-export with --export-only; this
script refuses to rebuild over it.

Bodies are Skin-modifier skeletons, so limbs are continuous tapered volumes
rather than stacked primitives. Each pose is posed by forward kinematics from
one gait phase, so the walk cycle is a real cycle (contact, passing, contact)
with the planted foot on the floor. Facing is -Y, matching the B009 models.

Look (measured privately against the owner-supplied original model, which is
never copied or shipped): ankle-length black gown with a front slit, under a
long open charcoal coat with wrist-length sleeves; platform sandals; blonde
hair loose to the shoulders with side locks; handgun in the right hand. Field
locomotion is a light run, not a walk.
Original geometry; nothing extracted from the commercial game.
"""
import hashlib
import json
import math
import re
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets" / "authoring" / "characters" / "aya.blend"
OUT = ROOT / "assets" / "models" / "aya"
WALK_FRAMES = 8

THIGH, SHIN, UPPER, FORE = 0.46, 0.46, 0.29, 0.26
HIP_W, SHOULDER_W = 0.06, 0.165


def material(name, color, rough=0.6):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    return m


MATS = {}


def mats():
    MATS.update(skin=material("Aya skin", (0.88, 0.66, 0.52)),
                dress=material("Aya gown", (0.02, 0.02, 0.025), 0.35),
                coat=material("Aya coat", (0.11, 0.11, 0.12), 0.55),
                lapel=material("Aya lapel", (0.16, 0.16, 0.17), 0.45),
                hair=material("Aya blonde", (0.80, 0.60, 0.27)),
                shoe=material("Aya heels", (0.02, 0.02, 0.02), 0.25),
                eye=material("Aya eyes", (0.10, 0.12, 0.16)),
                lips=material("Aya lips", (0.55, 0.22, 0.2)),
                gun=material("Pistol steel", (0.12, 0.12, 0.13), 0.3))


# --- posing -----------------------------------------------------------------

def rot_x(v, deg):
    """Swing a downward limb vector forward (toward -Y) by deg about X."""
    a = math.radians(deg)
    x, y, z = v
    return Vector((x, y * math.cos(a) + z * math.sin(a), -y * math.sin(a) + z * math.cos(a)))


def limb(start, length, swing, out=0.0):
    return Vector(start) + rot_x(Vector((out, 0, -length)), swing)


def pose(kind, phase=0.0):
    """Joint positions for a pose. phase in [0,1) drives the walk."""
    s = math.sin(phase * math.tau)
    c = math.cos(phase * math.tau)
    legs, arms = {}, {}
    if kind == "walk":
        # A light run (the original's field gait): hip swing +-30 deg, the
        # knee folds as the leg recovers, bent arms swing against the legs.
        for side, sign in (("L", 1), ("R", -1)):
            hip = 30 * s * sign
            knee = 10 + 55 * max(0.0, c * sign)
            legs[side] = (hip, knee)
        arm = {"L": (-24 * s, 32), "R": (14 * s, 36)}
        lean = 8
    elif kind == "recoil":
        legs = {"L": (10, 8), "R": (-14, 6)}
        arm = {"L": (78, 4), "R": (84, 2)}     # both hands forward, gun kicked up
        lean = -5
    else:  # idle / ready: weight even, gun lowered in the right hand
        legs = {"L": (3, 5), "R": (-3, 5)}
        arm = {"L": (4, 10), "R": (12, 30)}
        lean = 1
    # Ground the lower ankle: pelvis height follows the legs.
    drops = []
    for side, (hip, knee) in legs.items():
        k = limb((0, 0, 0), THIGH, hip)
        a = k + rot_x(Vector((0, 0, -SHIN)), hip - knee)
        drops.append(-a.z)
    pelvis_z = 0.105 + max(drops)
    J = {"pelvis": Vector((0, 0, pelvis_z))}
    for side, sign in (("L", -1), ("R", 1)):
        hip, knee = legs[side]
        h = Vector((sign * HIP_W, 0, pelvis_z))
        k = h + rot_x(Vector((0, 0, -THIGH)), hip)
        a = k + rot_x(Vector((0, 0, -SHIN)), hip - knee)
        J["hip" + side], J["knee" + side], J["ankle" + side] = h, k, a
    chest = J["pelvis"] + rot_x(Vector((0, 0, 0.44)), -lean)
    J["waist"] = J["pelvis"] + rot_x(Vector((0, 0, 0.2)), -lean)
    J["chest"] = chest
    J["neck"] = chest + Vector((0, 0, 0.1))
    J["head"] = J["neck"] + rot_x(Vector((0, 0, 0.15)), -lean)
    for side, sign in (("L", -1), ("R", 1)):
        swing, elbow = arm[side]
        sh = chest + Vector((sign * SHOULDER_W, 0.01, -0.02))
        el = sh + rot_x(Vector((sign * 0.03, 0, -UPPER)), swing)
        wr = el + rot_x(Vector((sign * 0.0, 0, -FORE)), swing + elbow)
        if kind == "recoil":
            wr = Vector((sign * 0.05, -0.5, chest.z - 0.02))   # hands meet on the grip
            el = (sh + wr) / 2 + Vector((sign * 0.08, 0.04, -0.06))
        J["shoulder" + side], J["elbow" + side], J["wrist" + side] = sh, el, wr
    return J


# --- building ------------------------------------------------------------------

def skin_object(name, verts, edges, radii, mat, subdiv=1, roots=(0,)):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], edges, [])
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    mod = ob.modifiers.new("skin", "SKIN")
    mod.use_smooth_shade = True
    for i, r in enumerate(radii):
        me.skin_vertices[0].data[i].radius = r
    # The Skin modifier only grows chains that contain a root vertex.
    for i in roots:
        me.skin_vertices[0].data[i].use_root = True
    if subdiv:
        ob.modifiers.new("sub", "SUBSURF").levels = subdiv
    ob.data.materials.append(mat)
    bpy.context.view_layer.objects.active = ob
    for m in list(ob.modifiers):
        bpy.ops.object.modifier_apply(modifier=m.name)
    return ob


def blob(name, center, size, mat, segs=10, rings=7):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segs, ring_count=rings, radius=1, location=center)
    ob = bpy.context.active_object
    ob.name = name
    ob.scale = size
    bpy.ops.object.transform_apply(scale=True)
    ob.data.materials.append(mat)
    return ob


def block(name, center, size, mat, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=center, rotation=rot)
    ob = bpy.context.active_object
    ob.name = name
    ob.scale = size
    bpy.ops.object.transform_apply(scale=True)
    ob.data.materials.append(mat)
    return ob


def build_pose(col_name, J, kind):
    col = bpy.data.collections.new(col_name)
    bpy.context.scene.collection.children.link(col)
    before = set(bpy.data.objects.keys())
    # Limbs: bare skin, one skeleton (legs, arms, neck).
    v, e, r, roots = [], [], [], []

    def add(chain, radii):
        base = len(v)
        roots.append(base)
        for p, rad in zip(chain, radii):
            v.append(p)
            r.append(rad)
        for i in range(len(chain) - 1):
            e.append((base + i, base + i + 1))
    for side in ("L", "R"):
        add([J["hip" + side], J["knee" + side], J["ankle" + side]],
            [(0.062, 0.064), (0.04, 0.042), (0.027, 0.029)])
    add([J["chest"] + Vector((0, 0, 0.04)), J["neck"] + Vector((0, 0, 0.05))], [(0.04, 0.04), (0.034, 0.034)])
    skin_object("legs_neck", v, e, r, MATS["skin"], roots=roots)
    p, w, ch = J["pelvis"], J["waist"], J["chest"]
    coat = MATS["coat"]
    # Coat sleeves to the wrist, hands bare.
    v, e, r, roots = [], [], [], []
    top = ch + Vector((0, 0.005, 0.03))
    add([J["shoulderL"], top, J["shoulderR"]], [(0.045, 0.042), (0.05, 0.045), (0.045, 0.042)])
    for side in ("L", "R"):
        add([J["shoulder" + side], J["elbow" + side], J["wrist" + side]],
            [(0.042, 0.04), (0.035, 0.034), (0.036, 0.034)])
    skin_object("coat_sleeves", v, e, r, coat, roots=roots)
    for side in ("L", "R"):
        d = (J["wrist" + side] - J["elbow" + side]).normalized()
        blob("hand" + side, J["wrist" + side] + d * 0.06, (0.028, 0.03, 0.05), MATS["skin"], 8, 5)
    # Coat body: shoulders -> waist -> hem just above the ankles, following
    # the legs so the long hem swings with the stride.
    feet = (J["ankleL"] + J["ankleR"]) / 2
    knees = (J["kneeL"] + J["kneeR"]) / 2
    hem = Vector((0, feet.y * 0.6, 0.13))
    skin_object("coat", [hem, Vector((0, knees.y * 0.7, knees.z)), p + Vector((0, 0, -0.02)), w,
                         ch - Vector((0, 0, 0.03)), ch + Vector((0, 0, 0.03))],
                [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5)],
                [(0.19, 0.14), (0.17, 0.125), (0.155, 0.112), (0.12, 0.088), (0.14, 0.1), (0.15, 0.09)], coat, subdiv=0)
    # The open front: the black gown shows in a V from the neckline to the
    # waist, and down the slit to the hem.
    dress = MATS["dress"]
    front = lambda q, depth: q + Vector((0, -depth, 0))
    block("gown_v", front(ch + Vector((0, 0, -0.05)), 0.09), (0.07, 0.015, 0.14), dress)
    for side, sign in (("L", -1), ("R", 1)):
        block("lapel" + side, front(ch + Vector((sign * 0.05, 0, -0.03)), 0.095), (0.03, 0.015, 0.2),
              MATS["lapel"], rot=(0, math.radians(sign * 14), 0))
    # Platform sandals.
    for side in ("L", "R"):
        a = J["ankle" + side]
        block("sole" + side, a + Vector((0, -0.05, -0.07)), (0.07, 0.19, 0.045), MATS["shoe"])
        block("strap" + side, a + Vector((0, -0.08, -0.035)), (0.072, 0.05, 0.03), MATS["shoe"])
        block("ankle_strap" + side, a + Vector((0, 0, -0.01)), (0.066, 0.066, 0.02), MATS["shoe"])
    # Head and loose shoulder-length hair with side locks and swept bangs.
    h = J["head"]
    blob("head", h, (0.085, 0.095, 0.112), MATS["skin"])
    for sign in (-1, 1):
        blob("eye", h + Vector((sign * 0.032, -0.084, 0.012)), (0.015, 0.006, 0.009), MATS["eye"], 6, 4)
    blob("lips", h + Vector((0, -0.086, -0.05)), (0.02, 0.006, 0.008), MATS["lips"], 6, 4)
    hair = MATS["hair"]
    blob("hair_cap", h + Vector((0, 0.015, 0.035)), (0.097, 0.103, 0.105), hair)
    blob("hair_back", h + Vector((0, 0.055, -0.08)), (0.088, 0.055, 0.15), hair)
    for sign in (-1, 1):
        blob("lock", h + Vector((sign * 0.08, -0.01, -0.09)), (0.022, 0.03, 0.12), hair, 6, 5)
    blob("bangs", h + Vector((0.025, -0.075, 0.065)), (0.065, 0.03, 0.035), hair, 8, 5)
    # Handgun in the right hand, aligned with the forearm.
    wr, el = J["wristR"], J["elbowR"]
    if kind == "recoil":
        d = Vector((0, -1, 0.25)).normalized()
    else:
        d = (wr - el).normalized()
    grip = wr + d * 0.05
    yaw = math.atan2(d.x, -d.y)
    pitch = math.asin(max(-1, min(1, d.z)))
    block("pistol", grip + d * 0.07, (0.03, 0.17, 0.045), MATS["gun"], rot=(pitch, 0, -yaw))
    block("grip", grip + Vector((0, 0, -0.03)), (0.026, 0.04, 0.07), MATS["gun"])
    for name in set(bpy.data.objects.keys()) - before:
        ob = bpy.data.objects[name]
        for c in list(ob.users_collection):
            c.objects.unlink(ob)
        col.objects.link(ob)
    return col


def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    mats()
    build_pose("aya_idle", pose("idle"), "idle")
    for i in range(WALK_FRAMES):
        build_pose("aya_walk_%d" % i, pose("walk", i / WALK_FRAMES), "walk")
    build_pose("aya_recoil", pose("recoil"), "recoil")
    down = build_pose("aya_down", pose("idle"), "idle")
    for ob in down.objects:   # fallen on her side, facing the camera's left
        ob.select_set(True)
    bpy.context.view_layer.objects.active = next(iter(down.objects))
    bpy.ops.transform.rotate(value=math.radians(-88), orient_axis="Y", center_override=(0, 0, 0))
    bpy.ops.transform.translate(value=(0.85, 0, 0.12))
    bpy.ops.object.select_all(action="DESELECT")
    SOURCE.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE))


def export():
    OUT.mkdir(parents=True, exist_ok=True)
    names = [c.name for c in bpy.data.collections if c.name.startswith("aya_")]
    for name in sorted(names):
        bpy.ops.object.select_all(action="DESELECT")
        for ob in bpy.data.collections[name].objects:
            ob.select_set(True)
        bpy.ops.wm.obj_export(filepath=str(OUT / (name + ".obj")), export_selected_objects=True,
                              forward_axis="NEGATIVE_Z", up_axis="Y", export_materials=True,
                              export_triangulated_mesh=True, path_mode="STRIP")
    files = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(OUT.glob("*")) if p.suffix in (".obj", ".mtl")}
    (OUT / "provenance.json").write_text(json.dumps({
        "source": "assets/authoring/characters/aya.blend",
        "sourceSha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "blenderVersion": bpy.app.version_string,
        "basis": "Original low-poly character study; no commercial asset extracts", "files": files}, indent=2) + "\n")
    print("EXPORTED", len(names), "poses to", OUT)


if "--export-only" not in sys.argv:
    if SOURCE.exists():
        raise RuntimeError("aya.blend exists and is the authority; edit it and re-export with --export-only")
    build()
export()
