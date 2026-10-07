"""Day 1 bosses (Melissa, Eve, the sewer alligator) as posed low-poly sources.

    python tools/blender/run.py projects/pe-day1/tools/build_bosses.py              # first build + export
    python tools/blender/run.py projects/pe-day1/tools/build_bosses.py --blend projects/pe-day1/assets/authoring/characters/bosses.blend -- --export-only

The first run creates assets/authoring/characters/bosses.blend with one
collection per pose (<boss>_idle, <boss>_windup). After that the .blend is the
authority: edit it in Blender and re-export with --export-only. This script
refuses to rebuild over it.

Look (measured privately against the owner-supplied original models, which
are never copied or shipped):
  Melissa  -- floor-length red gown with a square neckline and long sleeves,
              long dark hair down the back, hands clasped at the waist.
  Eve      -- the transformed singer: a tattered flame-red skirt over a long
              dark violet column, pale bodice, very long arms ending in claws,
              hair risen into stiff tendrils.
  Alligator-- an upright, crouching mutant: broad armoured torso, long jaw,
              clawed forelimbs held out, heavy tail.
Facing is -Y, matching Aya. Original geometry; nothing extracted from the
commercial game.
"""
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets" / "authoring" / "characters" / "bosses.blend"
OUT = ROOT / "assets" / "models" / "bosses"


def material(name, color, rough=0.6):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    return m


M = {}


def mats():
    M.update(skin=material("Boss skin", (0.86, 0.68, 0.58)),
             pale=material("Eve pale", (0.86, 0.80, 0.84)),
             gown=material("Melissa gown", (0.40, 0.03, 0.04), 0.4),
             trim=material("Melissa trim", (0.75, 0.72, 0.68), 0.5),
             hair=material("Melissa hair", (0.07, 0.04, 0.03)),
             eye=material("Boss eyes", (0.10, 0.08, 0.08)),
             lips=material("Boss lips", (0.55, 0.15, 0.15)),
             flame=material("Eve skirt", (0.70, 0.08, 0.03), 0.45),
             column=material("Eve column", (0.16, 0.18, 0.34), 0.5),
             claw=material("Eve claws", (0.30, 0.22, 0.38), 0.4),
             ehair=material("Eve hair", (0.42, 0.24, 0.14)),
             hide=material("Gator hide", (0.33, 0.29, 0.18), 0.8),
             plate=material("Gator plates", (0.62, 0.58, 0.48), 0.6),
             mouth=material("Gator mouth", (0.45, 0.10, 0.10)),
             tooth=material("Gator teeth", (0.85, 0.82, 0.74), 0.4))


def skin(name, chains, mat, subdiv=1):
    """chains: list of [(point, radius)]; each chain gets its own root."""
    v, e, r, roots = [], [], [], []
    for chain in chains:
        base = len(v)
        roots.append(base)
        for p, rad in chain:
            v.append(Vector(p))
            r.append(rad if isinstance(rad, tuple) else (rad, rad))
        e += [(base + i, base + i + 1) for i in range(len(chain) - 1)]
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(p) for p in v], e, [])
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    mod = ob.modifiers.new("skin", "SKIN")
    mod.use_smooth_shade = True
    for i, rad in enumerate(r):
        me.skin_vertices[0].data[i].radius = rad
    for i in roots:
        me.skin_vertices[0].data[i].use_root = True
    if subdiv:
        ob.modifiers.new("sub", "SUBSURF").levels = subdiv
    ob.data.materials.append(mat)
    bpy.context.view_layer.objects.active = ob
    for m in list(ob.modifiers):
        bpy.ops.object.modifier_apply(modifier=m.name)
    return ob


def blob(name, c, size, mat, segs=10, rings=7):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segs, ring_count=rings, radius=1, location=c)
    ob = bpy.context.active_object
    ob.name = name
    ob.scale = size
    bpy.ops.object.transform_apply(scale=True)
    ob.data.materials.append(mat)
    return ob


def cone(name, base, tip, r0, mat, verts=5):
    """A tapered spike from base to tip (claws, tendrils, skirt shards, teeth)."""
    base, tip = Vector(base), Vector(tip)
    d = tip - base
    bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r0, radius2=0, depth=d.length,
                                    location=(base + tip) / 2)
    ob = bpy.context.active_object
    ob.name = name
    ob.rotation_mode = "QUATERNION"
    ob.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(d.normalized())
    bpy.ops.object.transform_apply(rotation=True)
    ob.data.materials.append(mat)
    return ob


def lathe(name, profile, mat, segs=16, sy=1.0, back=0.0):
    """Revolve [(z, radius)] about Z into a skirt; sy stretches depth, back pushes a train."""
    verts, faces = [], []
    for z, rad in profile:
        for i in range(segs):
            a = math.tau * i / segs
            y = math.cos(a) * rad * sy
            if y > 0:
                y += back * (1 - z / profile[-1][0])
            verts.append((math.sin(a) * rad, y, z))
    for k in range(len(profile) - 1):
        for i in range(segs):
            j = (i + 1) % segs
            faces.append((k * segs + i, k * segs + j, (k + 1) * segs + j, (k + 1) * segs + i))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.data.materials.append(mat)
    for p in me.polygons:
        p.use_smooth = True
    return ob


def face(h, skin_mat, lips=True):
    blob("head", h, (0.08, 0.09, 0.108), skin_mat)
    for s in (-1, 1):
        blob("eye", h + Vector((s * 0.03, -0.08, 0.012)), (0.014, 0.006, 0.008), M["eye"], 6, 4)
    if lips:
        blob("lips", h + Vector((0, -0.083, -0.048)), (0.019, 0.006, 0.008), M["lips"], 6, 4)


def arms(sh_l, sh_r, raise_deg, length, mat, hand_mat, reach=0.0):
    """Two arms from the shoulders. raise_deg lifts them forward/out from the body."""
    out = []
    for s, sh in ((-1, sh_l), (1, sh_r)):
        a = math.radians(raise_deg)
        el = Vector(sh) + Vector((s * 0.05, -math.sin(a) * length * 0.5, -math.cos(a) * length * 0.5))
        wr = el + Vector((s * (0.02 + reach), -math.sin(a + 0.3) * length * 0.5, -math.cos(a + 0.3) * length * 0.5))
        out.append((s, Vector(sh), el, wr))
    skin("arms", [[(sh, 0.042), (el, 0.034), (wr, 0.03)] for _, sh, el, wr in out], mat)
    return out


def melissa(kind):
    z_waist, z_chest = 1.0, 1.32
    lathe("skirt", [(0.0, 0.40), (0.25, 0.36), (0.6, 0.27), (z_waist, 0.13)], M["gown"], sy=1.0, back=0.25)
    skin("bodice", [[((0, 0, z_waist - 0.02), (0.13, 0.1)), ((0, 0, z_chest - 0.08), (0.12, 0.085)),
                     ((0, 0, z_chest + 0.04), (0.15, 0.09))]], M["gown"], subdiv=1)
    # square neckline: bare skin above a pale trim band
    blob("decollete", (0, -0.045, z_chest + 0.07), (0.11, 0.05, 0.055), M["skin"], 10, 6)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, -0.085, z_chest + 0.02))
    t = bpy.context.active_object
    t.name = "trim"
    t.scale = (0.2, 0.02, 0.018)
    bpy.ops.object.transform_apply(scale=True)
    t.data.materials.append(M["trim"])
    shl, shr = (-0.16, 0, z_chest + 0.06), (0.16, 0, z_chest + 0.06)
    for s, sh in ((-1, shl), (1, shr)):
        blob("puff", sh, (0.06, 0.06, 0.055), M["gown"], 8, 6)
    if kind == "idle":   # hands clasped at the waist, as she sings
        chains = []
        for s, sh in ((-1, shl), (1, shr)):
            el = Vector((s * 0.2, -0.02, z_waist + 0.05))
            wr = Vector((s * 0.03, -0.16, z_waist + 0.02))
            chains.append([(sh, 0.04), (el, 0.034), (wr, 0.03)])
            blob("hand", wr + Vector((0, -0.02, 0)), (0.04, 0.03, 0.028), M["skin"], 8, 5)
        skin("sleeves", chains, M["gown"])
    else:                # wind-up: arms flung wide and up, head back
        chains = []
        for s, sh in ((-1, shl), (1, shr)):
            el = Vector((s * 0.38, -0.05, z_chest + 0.2))
            wr = Vector((s * 0.58, -0.1, z_chest + 0.42))
            chains.append([(sh, 0.04), (el, 0.034), (wr, 0.03)])
            blob("hand", wr + Vector((s * 0.03, 0, 0.04)), (0.03, 0.028, 0.045), M["skin"], 8, 5)
        skin("sleeves", chains, M["gown"])
    h = Vector((0, 0.0 if kind == "idle" else 0.03, z_chest + 0.28))
    skin("neck", [[((0, 0, z_chest + 0.06), 0.04), (h - Vector((0, 0, 0.06)), 0.034)]], M["skin"])
    face(h, M["skin"])
    # long dark hair: a cap, a curtain down the back to the waist, side waves
    blob("hair_cap", h + Vector((0, 0.015, 0.035)), (0.094, 0.1, 0.1), M["hair"])
    skin("hair_back", [[(h + Vector((0, 0.05, 0)), (0.1, 0.06)), (h + Vector((0, 0.09, -0.25)), (0.13, 0.05)),
                        ((0, 0.12, z_chest - 0.15), (0.12, 0.04))]], M["hair"], subdiv=1)
    for s in (-1, 1):
        skin("wave", [[(h + Vector((s * 0.08, -0.01, 0.0)), 0.03), (h + Vector((s * 0.11, 0.0, -0.16)), 0.035),
                       (h + Vector((s * 0.12, 0.02, -0.3)), 0.025)]], M["hair"])


def eve(kind):
    z_waist, z_chest = 1.0, 1.36
    # the long violet column the body narrows into, under a shredded skirt
    lathe("column", [(0.0, 0.11), (0.5, 0.12), (z_waist, 0.13)], M["column"], segs=10)
    lathe("skirt", [(0.35, 0.32), (0.7, 0.25), (z_waist + 0.02, 0.14)], M["flame"], segs=12, back=0.08)
    for i in range(14):
        a = math.tau * i / 14 + 0.3
        r0 = 0.27
        base = (math.sin(a) * r0, math.cos(a) * r0, 0.42)
        tip = (math.sin(a) * (r0 + 0.12), math.cos(a) * (r0 + 0.12), 0.08 + 0.12 * (i % 3))
        cone("shard", base, tip, 0.06, M["flame"], 4)
    skin("bodice", [[((0, 0, z_waist), (0.12, 0.09)), ((0, 0, z_chest - 0.1), (0.1, 0.075)),
                     ((0, 0, z_chest + 0.05), (0.17, 0.09))]], M["flame"])
    blob("breast_plate", (0, -0.07, z_chest - 0.04), (0.06, 0.03, 0.08), M["pale"], 8, 6)
    shl, shr = (-0.16, 0, z_chest + 0.05), (0.16, 0, z_chest + 0.05)
    chains = []
    for s, sh in ((-1, shl), (1, shr)):
        if kind == "idle":   # very long arms hanging past the skirt, claws splayed
            el = Vector((s * 0.27, 0.0, z_chest - 0.3))
            wr = Vector((s * 0.42, -0.05, z_chest - 0.75))
            claw_dir = Vector((s * 0.3, -0.2, -1)).normalized()
        else:                # wind-up: claws drawn back over the head
            el = Vector((s * 0.32, 0.05, z_chest + 0.25))
            wr = Vector((s * 0.36, 0.15, z_chest + 0.65))
            claw_dir = Vector((s * 0.2, -0.4, 1)).normalized()
        chains.append([(sh, 0.05), (el, 0.04), (wr, 0.034)])
        blob("hand", wr, (0.045, 0.035, 0.05), M["claw"], 8, 5)
        for k in (-1, 0, 1):
            off = Vector((k * 0.03, 0, 0))
            cone("claw", wr + off, wr + off + claw_dir * 0.2, 0.012, M["claw"], 4)
    skin("arms", chains, M["column"])
    h = Vector((0, 0, z_chest + 0.27))
    skin("neck", [[((0, 0, z_chest), 0.05), (h - Vector((0, 0, 0.05)), 0.034)]], M["pale"])
    face(h, M["pale"])
    blob("hair_cap", h + Vector((0, 0.015, 0.04)), (0.09, 0.098, 0.09), M["ehair"])
    for i, (dx, dz, lean) in enumerate(((-0.05, 0.02, -1.0), (0.05, 0.02, 1.0), (-0.03, 0.06, -0.4),
                                        (0.03, 0.06, 0.4), (0, 0.07, 0.0), (-0.07, 0.0, -1.6), (0.07, 0.0, 1.6))):
        base = h + Vector((dx, 0.02, dz))
        tip = base + Vector((lean * 0.18, 0.03, 0.32 - abs(lean) * 0.08))
        cone("tendril", base, tip, 0.03, M["ehair"], 5)


def alligator(kind):
    gape = 0.0 if kind == "idle" else 1.0
    # crouched legs
    for s in (-1, 1):
        skin("leg", [[((s * 0.22, 0.05, 0.7), 0.13), ((s * 0.38, -0.1, 0.38), 0.1), ((s * 0.32, -0.05, 0.08), 0.07)]], M["hide"])
        for k in (-1, 0, 1):
            cone("toe", (s * 0.32 + k * 0.05, -0.12, 0.04), (s * 0.32 + k * 0.08, -0.32, 0.0), 0.025, M["tooth"], 4)
    # armoured upright torso leaning forward
    skin("torso", [[((0, 0.1, 0.65), (0.3, 0.26)), ((0, 0.0, 1.1), (0.3, 0.25)), ((0, -0.06, 1.45), (0.2, 0.18))]], M["hide"])
    for i in range(4):
        blob("plate", (0, -0.2 + i * 0.01, 0.75 + i * 0.18), (0.18, 0.06, 0.08), M["plate"], 8, 4)
    for i in range(5):
        cone("spine", (0, 0.24 - i * 0.03, 0.8 + i * 0.16), (0, 0.38 - i * 0.03, 0.88 + i * 0.16), 0.04, M["plate"], 4)
    # tail curling behind
    skin("tail", [[((0, 0.25, 0.6), 0.2), ((0.1, 0.7, 0.35), 0.14), ((0.3, 1.1, 0.15), 0.08), ((0.6, 1.3, 0.08), 0.03)]], M["hide"])
    # forelimbs held out, claws open
    for s in (-1, 1):
        reach = 0.1 + 0.2 * gape
        el = Vector((s * 0.42, -0.15 - reach, 1.15))
        wr = Vector((s * 0.55, -0.35 - reach, 1.15 + 0.2 * gape))
        skin("arm", [[((s * 0.25, -0.02, 1.3), 0.08), (el, 0.06), (wr, 0.045)]], M["hide"])
        for k in (-1, 0, 1):
            cone("claw", wr, wr + Vector((s * 0.06 + k * 0.05, -0.18, -0.08)), 0.02, M["tooth"], 4)
    # long head and jaw; the jaw drops when it winds up to bite
    hb = Vector((0, -0.15, 1.55))
    skin("snout", [[(hb, (0.13, 0.12)), (hb + Vector((0, -0.45, 0.02)), (0.07, 0.06))]], M["hide"])
    jaw_tip = hb + Vector((0, -0.42, -0.08 - 0.22 * gape))
    skin("jaw", [[(hb + Vector((0, 0, -0.08)), (0.11, 0.08)), (jaw_tip, (0.06, 0.04))]], M["hide"])
    blob("maw", hb + Vector((0, -0.2, -0.06 - 0.08 * gape)), (0.07, 0.18, 0.03 + 0.05 * gape), M["mouth"], 8, 5)
    for i in range(5):
        y = -0.08 - i * 0.08
        for s in (-1, 1):
            cone("tooth", hb + Vector((s * 0.06, y, -0.05)), hb + Vector((s * 0.06, y, -0.12)), 0.012, M["tooth"], 4)
    for s in (-1, 1):
        blob("eye", hb + Vector((s * 0.09, -0.05, 0.1)), (0.025, 0.025, 0.02), M["mouth"], 6, 4)
        cone("horn", hb + Vector((s * 0.05, 0.05, 0.1)), hb + Vector((s * 0.07, 0.15, 0.25)), 0.025, M["plate"], 4)


BOSSES = {"melissa": melissa, "eve": eve, "alligator": alligator}


def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    mats()
    for boss, fn in BOSSES.items():
        for kind in ("idle", "windup"):
            before = set(bpy.data.objects.keys())
            fn(kind)
            col = bpy.data.collections.new("%s_%s" % (boss, kind))
            bpy.context.scene.collection.children.link(col)
            for name in set(bpy.data.objects.keys()) - before:
                ob = bpy.data.objects[name]
                for c in list(ob.users_collection):
                    c.objects.unlink(ob)
                col.objects.link(ob)
    SOURCE.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE))


def export():
    OUT.mkdir(parents=True, exist_ok=True)
    names = sorted(c.name for c in bpy.data.collections if c.name.split("_")[0] in BOSSES)
    for name in names:
        bpy.ops.object.select_all(action="DESELECT")
        for ob in bpy.data.collections[name].objects:
            ob.select_set(True)
        bpy.ops.wm.obj_export(filepath=str(OUT / (name + ".obj")), export_selected_objects=True,
                              forward_axis="NEGATIVE_Z", up_axis="Y", export_materials=True,
                              export_triangulated_mesh=True, path_mode="STRIP")
    files = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(OUT.glob("*")) if p.suffix in (".obj", ".mtl")}
    (OUT / "provenance.json").write_text(json.dumps({
        "source": "assets/authoring/characters/bosses.blend",
        "sourceSha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "blenderVersion": bpy.app.version_string,
        "basis": "Original low-poly character studies; no commercial asset extracts", "files": files}, indent=2) + "\n")
    print("EXPORTED", len(names), "poses to", OUT)


if "--export-only" not in sys.argv:
    if SOURCE.exists():
        raise RuntimeError("bosses.blend exists and is the authority; edit it and re-export with --export-only")
    build()
export()
