"""One-shot migration of six established Second Gate relics into editable Blender sources.

This file exists only to materialize the first authoritative .blend documents on the
migration branch. It must be deleted after visual acceptance. Once saved, the .blend
files themselves are source authority; ordinary compilation is read-only.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import bpy

import second_rite_asset_core as core

ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = ROOT / "assets" / "authoring" / "items"
SOURCE_DIR.mkdir(parents=True, exist_ok=True)

MATERIAL_IDS = (
    "bone",
    "crystal",
    "oxidized_bronze",
    "ritual_gold",
    "rough_limestone",
    "smoked_glass",
    "wrought_iron",
)

GOLD = "assets/models/matcaps/gold.png"
RUBY = "assets/models/matcaps/ruby.png"

PASSES = {
    "black_hinge": {
        "ritual_gold": [{"uvSource": "sphere", "blend": "screen", "strength": 0.62, "texture": GOLD}],
        "crystal": [{"uvSource": "sphere", "blend": "add", "strength": 0.65, "texture": RUBY}],
    },
    "chrysalis_sigil": {
        "ritual_gold": [{"uvSource": "sphere", "blend": "screen", "strength": 0.66, "texture": GOLD}],
        "crystal": [
            {"uvSource": "sphere", "blend": "screen", "strength": 0.48, "texture": GOLD},
            {"uvSource": "sphere", "blend": "add", "strength": 0.30, "texture": RUBY},
        ],
    },
    "qilin_bell": {
        "ritual_gold": [{"uvSource": "sphere", "blend": "screen", "strength": 0.62, "texture": GOLD}],
        "crystal": [{"uvSource": "sphere", "blend": "screen", "strength": 0.35, "texture": GOLD}],
    },
    "vial_of_second_breath": {
        "ritual_gold": [{"uvSource": "sphere", "blend": "screen", "strength": 0.62, "texture": GOLD}],
        "smoked_glass": [{"uvSource": "sphere", "blend": "add", "strength": 0.12, "texture": GOLD}],
        "crystal": [{"uvSource": "sphere", "blend": "screen", "strength": 0.55, "texture": GOLD}],
    },
    "meteorite_plate": {
        "ritual_gold": [{"uvSource": "sphere", "blend": "screen", "strength": 0.58, "texture": GOLD}],
        "crystal": [{"uvSource": "sphere", "blend": "add", "strength": 0.55, "texture": RUBY}],
    },
    "philosophers_stone": {
        "ritual_gold": [{"uvSource": "sphere", "blend": "screen", "strength": 0.64, "texture": GOLD}],
        "crystal": [
            {"uvSource": "sphere", "blend": "add", "strength": 0.82, "texture": RUBY},
            {"uvSource": "sphere", "blend": "screen", "strength": 0.32, "texture": GOLD},
        ],
    },
}


def reset():
    core.reset_scene(factory=True)


def materials(item_id: str):
    mats = {mid: core.make_material(mid, semantic_id=mid) for mid in MATERIAL_IDS}
    for mid, stack in PASSES.get(item_id, {}).items():
        mats[mid]["sr_runtime_passes_json"] = json.dumps(stack, separators=(",", ":"), sort_keys=True)
    return mats


def root_for(item_id: str, description: str):
    root = bpy.data.objects.new(f"ITEM_{item_id}", None)
    root.empty_display_type = "PLAIN_AXES"
    root.empty_display_size = 0.22
    bpy.context.scene.collection.objects.link(root)
    root["item_export"] = True
    root["item_export_name"] = item_id
    root["sr_source_authority"] = "blend"
    root["sr_authoring_description"] = description
    core.tag_asset_target(
        root,
        asset_id=item_id,
        representation="full_model",
        role="item_display",
        authoring_space="item_display",
        placement_frame="item_viewport",
        states=["default"],
        default_state="default",
        variants=[],
        extra={"sr_source_authority": "blend"},
    )
    return root


def mesh_object(name, vertices, *, edges=(), faces=(), parent=None, material=None):
    mesh = bpy.data.meshes.new(name + "Mesh")
    mesh.from_pydata(vertices, edges, faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    if parent is not None:
        core.parent_local(obj, parent)
    if material is not None:
        core.assign_material(obj, material)
    return obj


def screw_profile(name, profile, *, parent, material, steps=14, location=(0, 0, 0), rotation=(0, 0, 0), scale=(1, 1, 1)):
    verts = [(r, 0.0, z) for r, z in profile]
    edges = [(i, i + 1) for i in range(len(verts) - 1)]
    obj = mesh_object(name, verts, edges=edges, parent=parent, material=material)
    mod = obj.modifiers.new("A_ProfileRevolve", "SCREW")
    mod.axis = "Z"
    mod.angle = math.tau
    mod.steps = steps
    mod.render_steps = steps
    mod.use_merge_vertices = True
    mod.merge_threshold = 0.0001
    mod.use_smooth_shade = True
    if hasattr(mod, "use_stretch_u"):
        mod.use_stretch_u = True
    if hasattr(mod, "use_stretch_v"):
        mod.use_stretch_v = True
    obj.location = location
    obj.rotation_euler = tuple(math.radians(v) for v in rotation)
    obj.scale = scale
    return obj


def teardrop(name, radius, height, *, parent, material, location=(0, 0, 0), rotation=(0, 0, 0), scale=(1, 1, 1), steps=10):
    h = height * 0.5
    p = [(0.0, -h), (radius * 0.78, -h * 0.72), (radius, -h * 0.10), (radius * 0.72, h * 0.42), (radius * 0.32, h * 0.78), (0.0, h)]
    return screw_profile(name, p, parent=parent, material=material, steps=steps, location=location, rotation=rotation, scale=scale)


def shallow_disc(name, radius, depth, *, parent, material, location=(0, 0, 0), rotation=(90, 0, 0), scale=(1, 1, 1), steps=14):
    d = depth * 0.5
    p = [(0.0, -d), (radius * 0.88, -d), (radius, -d * 0.35), (radius, d * 0.35), (radius * 0.88, d), (0.0, d)]
    return screw_profile(name, p, parent=parent, material=material, steps=steps, location=location, rotation=rotation, scale=scale)


def cylinder(name, radius, height, *, parent, material, location=(0, 0, 0), rotation=(0, 0, 0), scale=(1, 1, 1), steps=12):
    h = height * 0.5
    p = [(0.0, -h), (radius, -h), (radius, h), (0.0, h)]
    return screw_profile(name, p, parent=parent, material=material, steps=steps, location=location, rotation=rotation, scale=scale)


def path_curve(name, points, *, parent, material, bevel_depth=0.04, radii=None, cyclic=False, hide_render=False):
    curve = bpy.data.curves.new(name + "Curve", type="CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 1
    curve.resolution_v = 0
    curve.bevel_resolution = 0
    curve.bevel_depth = bevel_depth
    curve.fill_mode = "FULL"
    if hasattr(curve, "use_fill_caps"):
        curve.use_fill_caps = True
    spline = curve.splines.new("POLY")
    spline.points.add(len(points) - 1)
    radii = radii or [1.0] * len(points)
    for co, radius, point in zip(points, radii, spline.points):
        point.co = (*co, 1.0)
        point.radius = radius
    spline.use_cyclic_u = cyclic
    obj = bpy.data.objects.new(name, curve)
    bpy.context.scene.collection.objects.link(obj)
    core.parent_local(obj, parent)
    core.assign_material(obj, material)
    obj.hide_render = hide_render
    return obj


def circle_xz(name, rx, rz, *, parent, material, center=(0.0, 0.0, 0.0), bevel_depth=0.04, points=20, cyclic=True):
    cx, cy, cz = center
    coords = [(cx + rx * math.cos(math.tau * i / points), cy, cz + rz * math.sin(math.tau * i / points)) for i in range(points)]
    return path_curve(name, coords, parent=parent, material=material, bevel_depth=bevel_depth, cyclic=cyclic)


def circle_xy(name, radius, *, parent, material, center=(0.0, 0.0, 0.0), bevel_depth=0.04, points=20, rotation=(0, 0, 0)):
    cx, cy, cz = center
    coords = [(cx + radius * math.cos(math.tau * i / points), cy + radius * math.sin(math.tau * i / points), cz) for i in range(points)]
    obj = path_curve(name, coords, parent=parent, material=material, bevel_depth=bevel_depth, cyclic=True)
    obj.rotation_euler = tuple(math.radians(v) for v in rotation)
    return obj


def arc_xz(name, center, rx, rz, start_deg, end_deg, *, parent, material, bevel_depth=0.04, points=10, radii=None, depth=0.0):
    cx, _, cz = center
    coords = []
    for i in range(points):
        t = i / (points - 1)
        angle = math.radians(start_deg + (end_deg - start_deg) * t)
        coords.append((cx + rx * math.cos(angle), depth, cz + rz * math.sin(angle)))
    return path_curve(name, coords, parent=parent, material=material, bevel_depth=bevel_depth, radii=radii)


def sphere(name, radius, *, parent, material, location=(0, 0, 0), scale=(1, 1, 1)):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=10, ring_count=6, radius=radius, location=location)
    obj = bpy.context.object
    obj.name = name
    core.parent_local(obj, parent)
    core.assign_material(obj, material)
    obj.scale = scale
    return obj


def note(item_id: str, text: str):
    block = bpy.data.texts.get("AUTHORING_README") or bpy.data.texts.new("AUTHORING_README")
    block.clear()
    block.write(
        f"Second Gate authoritative item source: {item_id}\n\n{text}\n\n"
        "This .blend is the source authority. Edit the named profiles, Curves and semantic objects directly.\n"
        "Compile read-only with tools/blender/compile_item_blends.py; do not regenerate this file from the migration script.\n"
    )


def save(item_id: str):
    path = SOURCE_DIR / f"{item_id}.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(path))
    print("SAVED RELIC SOURCE", path)


def build_black_hinge():
    reset(); mat = materials("black_hinge")
    root = root_for("black_hinge", "Paired occult gate leaves around an editable ceremonial hinge pin")
    shallow_disc("A_Leaf_L", 0.72, 0.18, parent=root, material=mat["wrought_iron"], location=(-0.58, -0.01, 0.0), scale=(0.78, 1.0, 1.12))
    shallow_disc("A_Leaf_R", 0.72, 0.18, parent=root, material=mat["wrought_iron"], location=(0.58, -0.01, 0.0), scale=(0.78, 1.0, 1.12))
    cylinder("A_CeremonialPin", 0.11, 2.05, parent=root, material=mat["wrought_iron"], location=(0, 0.02, 0))
    for z in (-0.68, 0.0, 0.68):
        cylinder(f"A_GoldCollar_{z:+.2f}", 0.17, 0.10, parent=root, material=mat["ritual_gold"], location=(0, 0.0, z))
    arc_xz("C_Halo_L", (-0.58, 0, 0), 0.52, 0.62, 52, 286, parent=root, material=mat["ritual_gold"], bevel_depth=0.038, points=12, depth=-0.14)
    arc_xz("C_Halo_R", (0.58, 0, 0), 0.52, 0.62, -106, 128, parent=root, material=mat["ritual_gold"], bevel_depth=0.038, points=12, depth=-0.14)
    for x in (-0.58, 0.58):
        for z in (-0.48, 0.48):
            sphere(f"A_Rivet_{x:+.2f}_{z:+.2f}", 0.075, parent=root, material=mat["ritual_gold"], location=(x, -0.16, z), scale=(1, 0.55, 1))
    teardrop("A_CrystalHeart", 0.16, 0.38, parent=root, material=mat["crystal"], location=(0, -0.21, 0), scale=(1.0, 0.52, 1.15))
    note("black_hinge", "The two leaves, central pin, three collars, halo arcs, rivets and crystal heart remain separately selectable. The source is intentionally a ceremonial object rather than anonymous merged geometry.")
    save("black_hinge")


def build_chrysalis_sigil():
    reset(); mat = materials("chrysalis_sigil")
    root = root_for("chrysalis_sigil", "Crystal cocoon suspended inside asymmetric ritual ribs and wing-petals")
    teardrop("A_CrystalCocoon", 0.46, 1.55, parent=root, material=mat["crystal"], location=(0, 0, -0.05), scale=(0.82, 0.55, 1.0), steps=12)
    circle_xz("C_OuterHalo", 0.78, 0.92, parent=root, material=mat["ritual_gold"], center=(0, 0.09, 0.03), bevel_depth=0.04, points=22)
    for idx, bend in enumerate((-0.22, 0.0, 0.22)):
        points=[(-0.40 + bend, -0.06, -0.60), (-0.50 + bend*0.4, -0.05, -0.08), (-0.34 - bend*0.2, -0.06, 0.50), (0.0 + bend*0.3, -0.07, 0.78), (0.34 + bend*0.1, -0.06, 0.50), (0.50 + bend*0.4, -0.05, -0.08), (0.40 + bend, -0.06, -0.60)]
        path_curve(f"C_RitualRib_{idx}", points, parent=root, material=mat["ritual_gold"], bevel_depth=0.027, radii=[0.65,0.9,1,0.8,1,0.9,0.65])
    for side in (-1, 1):
        for idx, (z, angle, size) in enumerate(((0.28, 32, 1.0), (-0.24, 58, 0.78))):
            obj = teardrop(f"A_WingPetal_{'R' if side>0 else 'L'}_{idx}", 0.23, 0.70*size, parent=root, material=mat["oxidized_bronze"], location=(side*0.52, 0.02, z), scale=(0.62, 0.20, 1.0))
            obj.rotation_euler[1] = math.radians(side * angle)
    circle_xz("C_TopLoop", 0.20, 0.23, parent=root, material=mat["ritual_gold"], center=(0, 0, 1.00), bevel_depth=0.04, points=14)
    sphere("A_FrontGem", 0.12, parent=root, material=mat["crystal"], location=(0, -0.40, 0.38), scale=(1,0.55,1))
    note("chrysalis_sigil", "The cocoon is one editable revolve profile; the halo/ribs are Curve gestures; the verdigris petals remain individual solids. The asymmetry is authored, not noise-driven.")
    save("chrysalis_sigil")


def build_qilin_bell():
    reset(); mat = materials("qilin_bell")
    root = root_for("qilin_bell", "Genuinely hollow temple bell with horned shoulders and crystal clapper")
    wall=[(0.66,-0.78),(0.62,-0.50),(0.53,0.06),(0.36,0.46),(0.18,0.66),(0.12,0.70),(0.09,0.60),(0.18,0.52),(0.42,0.08),(0.54,-0.48),(0.58,-0.75)]
    screw_profile("A_HollowBellWall", wall, parent=root, material=mat["ritual_gold"], steps=16)
    circle_xy("C_BronzeRim", 0.64, parent=root, material=mat["oxidized_bronze"], center=(0,0,-0.76), bevel_depth=0.055, points=18)
    shallow_disc("A_CrownCap", 0.30, 0.16, parent=root, material=mat["ritual_gold"], location=(0,0,0.66), rotation=(0,0,0), scale=(1,1,0.7))
    circle_xz("C_HangingLoop", 0.22, 0.28, parent=root, material=mat["wrought_iron"], center=(0,0,0.93), bevel_depth=0.045, points=16)
    teardrop("A_CrystalClapper", 0.14, 0.42, parent=root, material=mat["crystal"], location=(0,0,-0.88), scale=(0.9,0.9,1.0), steps=9)
    path_curve("C_Horn_L", [(-0.16,0,0.52),(-0.40,0,0.62),(-0.58,0,0.82),(-0.66,0,1.02)], parent=root, material=mat["wrought_iron"], bevel_depth=0.05, radii=[1,0.9,0.65,0.20])
    path_curve("C_Horn_R", [(0.16,0,0.52),(0.40,0,0.62),(0.58,0,0.82),(0.66,0,1.02)], parent=root, material=mat["wrought_iron"], bevel_depth=0.05, radii=[1,0.9,0.65,0.20])
    for i, angle in enumerate((35,145,215,325)):
        a=math.radians(angle)
        sphere(f"A_CrystalStud_{i}",0.05,parent=root,material=mat["crystal"],location=(0.46*math.cos(a),0.46*math.sin(a),-0.42),scale=(1,1,0.8))
    note("qilin_bell", "The bell is now authored as one outside→rim→inside wall section, so opening the .blend exposes a genuinely hollow bell rather than a solid silhouette. Horns and hanging loop are editable Curves.")
    save("qilin_bell")


def build_vial_of_second_breath():
    reset(); mat = materials("vial_of_second_breath")
    root = root_for("vial_of_second_breath", "Smoked ritual vial embraced by six dry breath-feather gestures")
    body=[(0.0,-0.90),(0.30,-0.90),(0.40,-0.72),(0.43,-0.24),(0.38,0.28),(0.26,0.48),(0.18,0.54),(0.18,0.72),(0.0,0.72)]
    screw_profile("A_SmokedVialBody", body, parent=root, material=mat["smoked_glass"], steps=16)
    circle_xy("C_GoldFoot",0.34,parent=root,material=mat["ritual_gold"],center=(0,0,-0.86),bevel_depth=0.045,points=16)
    circle_xy("C_GoldNeck",0.21,parent=root,material=mat["ritual_gold"],center=(0,0,0.62),bevel_depth=0.04,points=14)
    teardrop("A_CrystalStopper",0.18,0.40,parent=root,material=mat["crystal"],location=(0,0,0.88),scale=(0.95,0.95,1.0),steps=10)
    for side in (-1,1):
        for idx,(z,reach,lift) in enumerate(((0.24,0.70,0.34),(-0.02,0.64,0.18),(-0.30,0.54,0.03))):
            x0=side*0.30; x1=side*0.54; x2=side*reach
            pts=[(x0,0.02,z-0.10),(x1,-0.01,z+lift*0.35),(x2,-0.03,z+lift)]
            path_curve(f"C_BreathFeather_{'R' if side>0 else 'L'}_{idx}",pts,parent=root,material=mat["bone"],bevel_depth=0.038,radii=[1,0.72,0.12])
    arc_xz("C_BrokenHalo",(0,0,0.12),0.54,0.72,-62,218,parent=root,material=mat["oxidized_bronze"],bevel_depth=0.028,points=16,depth=0.12)
    sphere("A_BreathBead",0.09,parent=root,material=mat["crystal"],location=(0,-0.43,-0.26),scale=(1,0.55,1))
    note("vial_of_second_breath", "The vial body is a compact live revolve profile. The six bone 'breaths' are independent tapered Curve gestures, so their fan can be art-directed directly instead of reconstructed from arc parameters.")
    save("vial_of_second_breath")


def build_meteorite_plate():
    reset(); mat = materials("meteorite_plate")
    root = root_for("meteorite_plate", "Layered meteor cuirass plate with crater, crystal heart and radial splinters")
    shallow_disc("A_IronMass",0.86,0.22,parent=root,material=mat["wrought_iron"],location=(0,0,0),scale=(0.95,1.0,1.12),steps=16)
    shallow_disc("A_BronzeLobe_L",0.52,0.18,parent=root,material=mat["oxidized_bronze"],location=(-0.54,0.03,-0.02),scale=(0.72,1.0,0.84),steps=14)
    shallow_disc("A_BronzeLobe_R",0.52,0.18,parent=root,material=mat["oxidized_bronze"],location=(0.54,0.03,-0.02),scale=(0.72,1.0,0.84),steps=14)
    circle_xz("C_GoldRim",0.76,0.92,parent=root,material=mat["ritual_gold"],center=(0,-0.16,0),bevel_depth=0.045,points=20)
    circle_xz("C_CraterRing",0.29,0.25,parent=root,material=mat["rough_limestone"],center=(0,-0.22,0.02),bevel_depth=0.052,points=14)
    teardrop("A_MeteorHeart",0.17,0.38,parent=root,material=mat["crystal"],location=(0,-0.28,0.02),scale=(1.0,0.48,0.82),steps=9)
    arc_xz("C_Crest",(0,0,0.67),0.40,0.28,18,162,parent=root,material=mat["ritual_gold"],bevel_depth=0.04,points=10,depth=-0.13)
    spikes=[(-0.72,0.50,58),(0.72,0.50,-58),(-0.70,-0.56,122),(0.70,-0.56,-122),(0,0.95,0),(0,-0.95,180)]
    for idx,(x,z,angle) in enumerate(spikes):
        obj=teardrop(f"A_MeteorSplinter_{idx}",0.09,0.42,parent=root,material=mat["bone"],location=(x,0.02,z),scale=(0.75,0.55,1.0),steps=7)
        obj.rotation_euler[1]=math.radians(angle)
    note("meteorite_plate", "Main mass, bronze lobes, crater ring, heart, crest and six splinters remain separately art-directable. The radial gold/crater contours are Curves rather than baked torus fragments.")
    save("meteorite_plate")


def build_philosophers_stone():
    reset(); mat = materials("philosophers_stone")
    root = root_for("philosophers_stone", "Cold alchemical stone suspended in three independently oriented orbit rings")
    teardrop("A_Stone",0.38,1.12,parent=root,material=mat["crystal"],location=(0,0,-0.05),scale=(0.86,0.70,1.0),steps=11)
    circle_xy("C_OrbitEquator",0.62,parent=root,material=mat["ritual_gold"],bevel_depth=0.038,points=20,rotation=(90,0,0))
    circle_xy("C_OrbitTiltA",0.64,parent=root,material=mat["ritual_gold"],bevel_depth=0.038,points=20,rotation=(36,22,18))
    circle_xy("C_OrbitTiltB",0.66,parent=root,material=mat["oxidized_bronze"],bevel_depth=0.038,points=20,rotation=(-42,-18,-24))
    arc_xz("C_IronCrown",(0,0,0.72),0.30,0.24,12,168,parent=root,material=mat["wrought_iron"],bevel_depth=0.042,points=10,depth=0.02)
    cylinder("A_Pedestal",0.20,0.34,parent=root,material=mat["wrought_iron"],location=(0,0,-0.78),steps=10)
    shallow_disc("A_GoldBase",0.40,0.12,parent=root,material=mat["ritual_gold"],location=(0,0,-0.96),rotation=(0,0,0),scale=(1,1,0.8),steps=12)
    for i,angle in enumerate((16,138,260)):
        a=math.radians(angle)
        sphere(f"A_Satellite_{i}",0.075,parent=root,material=mat["crystal"],location=(0.73*math.cos(a),0.20*math.sin(a),0.73*math.sin(a)),scale=(1,0.8,1))
    note("philosophers_stone", "The three orbit rings are real independent Curve objects with ordinary transforms. The stone, crown, pedestal, base and satellites remain semantic pieces; there is no external orbit recipe after this migration.")
    save("philosophers_stone")


for builder in (
    build_black_hinge,
    build_chrysalis_sigil,
    build_qilin_bell,
    build_vial_of_second_breath,
    build_meteorite_plate,
    build_philosophers_stone,
):
    builder()
