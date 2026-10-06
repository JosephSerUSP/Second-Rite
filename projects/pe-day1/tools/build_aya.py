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

Look: short black slip dress with thin straps, bare arms and legs, black
heels, blonde hair tied back with a ponytail, handgun in the right hand.
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
HIP_W, SHOULDER_W = 0.095, 0.185


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
                dress=material("Aya dress", (0.035, 0.035, 0.045), 0.35),
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
        # Hip swing +-27 deg; the knee flexes while the leg swings forward.
        for side, sign in (("L", 1), ("R", -1)):
            hip = 27 * s * sign
            knee = 6 + 42 * max(0.0, c * sign)
            legs[side] = (hip, knee)
        arm = {"L": (-20 * s, 12), "R": (8 * s, 28)}
        lean = 4
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
            [(0.072, 0.075), (0.045, 0.048), (0.030, 0.032)])
        add([J["shoulder" + side], J["elbow" + side], J["wrist" + side]],
            [(0.038, 0.038), (0.030, 0.030), (0.024, 0.022)])
    add([J["chest"] + Vector((0, 0, 0.04)), J["neck"] + Vector((0, 0, 0.05))], [(0.042, 0.042), (0.036, 0.036)])
    # Clavicles join the bare shoulders to the neck base.
    top = J["chest"] + Vector((0, 0.005, 0.03))
    add([J["shoulderL"], top, J["shoulderR"]], [(0.04, 0.036), (0.05, 0.04), (0.04, 0.036)])
    skin_object("limbs", v, e, r, MATS["skin"], roots=roots)
    # Dress: torso skeleton (bust, waist, hips) in black, plus an A-line skirt.
    p, w, ch = J["pelvis"], J["waist"], J["chest"]
    # One continuous dress: hips -> waist -> bust, flaring below the hips
    # into a short skirt that ends above the knee.
    hem = p + Vector((0, (J["kneeL"].y + J["kneeR"].y) / 4, -0.30))
    skin_object("dress", [hem, p + Vector((0, 0, -0.1)), p + Vector((0, 0, 0.02)), w,
                          ch - Vector((0, 0.01, 0.04)), ch + Vector((0, 0, 0.025))],
                [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5)],
                [(0.215, 0.17), (0.165, 0.125), (0.135, 0.098), (0.105, 0.075), (0.128, 0.098), (0.115, 0.08)],
                MATS["dress"])
    for side, sign in (("L", -1), ("R", 1)):
        a, b = ch + Vector((sign * 0.08, 0, 0.0)), J["shoulder" + side] + Vector((0, 0, 0.02))
        mid = (a + b) / 2
        block("strap" + side, mid, (0.012, 0.012, (b - a).length), MATS["dress"],
              rot=(0, math.atan2(b.x - a.x, b.z - a.z), 0))
    # Heels: a wedge under each ankle, toe pointing -Y.
    for side in ("L", "R"):
        a = J["ankle" + side]
        block("shoe" + side, a + Vector((0, -0.07, -0.045)), (0.06, 0.17, 0.04), MATS["shoe"], rot=(math.radians(-14), 0, 0))
        block("instep" + side, a + Vector((0, -0.01, -0.01)), (0.062, 0.07, 0.05), MATS["shoe"])
        block("spike" + side, a + Vector((0, 0.035, -0.06)), (0.018, 0.018, 0.08), MATS["shoe"])
    # Head, face, hair (tied back with a ponytail and side fringe).
    h = J["head"]
    blob("head", h, (0.088, 0.098, 0.115), MATS["skin"])
    for sign in (-1, 1):
        blob("eye", h + Vector((sign * 0.033, -0.086, 0.012)), (0.014, 0.006, 0.008), MATS["eye"], 6, 4)
    blob("lips", h + Vector((0, -0.088, -0.05)), (0.022, 0.006, 0.008), MATS["lips"], 6, 4)
    blob("hair_cap", h + Vector((0, 0.012, 0.03)), (0.098, 0.104, 0.11), MATS["hair"])
    for sign in (-1, 1):
        blob("fringe", h + Vector((sign * 0.07, -0.05, -0.01)), (0.03, 0.035, 0.08), MATS["hair"], 6, 5)
    blob("bun", h + Vector((0, 0.1, 0.02)), (0.05, 0.05, 0.05), MATS["hair"], 8, 5)
    blob("ponytail", h + Vector((0, 0.125, -0.12)), (0.04, 0.035, 0.12), MATS["hair"], 8, 5)
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
