"""Phase 1: material micro-gauntlet.

Renders every candidate material on IDENTICAL geometry, camera, lighting and
exposure, so the only variable is the material source strategy. Each sample is
rendered twice:

  * a close-up study plate, and
  * the same material at the real 426x240 town presentation scale,

because a material that is gorgeous at 2K and mush at game size has not earned
a place in the palette.

Run:
    blender --background --factory-startup --python micro_gauntlet.py
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import bpy  # noqa: E402

import materials as M  # noqa: E402
import proc_materials as P  # noqa: E402

ROOT = HERE.parents[2]
OUT = ROOT / "projects/hichaukitoden-game/assets/authoring/town/material_gauntlet"

# (sample id, surface family, strategy, factory)
SAMPLES = [
    # 1. stone wall -- all three strategies compete
    ("stone_A_proc",   "stone wall",  "procedural",
     lambda: P.proc_stone_blocks(scale=1.0, bump=0.5)),
    ("stone_B_lib",    "stone wall",  "public-library",
     lambda: M.library_material("medieval_blocks_02", scale=1.2, bump=0.4, grime=0.20)),
    ("stone_C_gen",    "stone wall",  "openai-generated",
     lambda: M.generated_material("gen_facade_ornament", scale=1.1, bump=0.5, grime=0.15)),

    # 2. plaster / stucco facade -- all three strategies compete
    ("plaster_A_proc", "plaster",     "procedural",
     lambda: P.proc_plaster(scale=1.0, bump=0.22)),
    ("plaster_B_lib",  "plaster",     "public-library",
     lambda: M.library_material("plastered_stone_wall", scale=1.1, bump=0.30, grime=0.22)),
    ("plaster_C_gen",  "plaster",     "openai-generated",
     lambda: M.generated_material("gen_plaster_patch", scale=1.0, bump=0.35, grime=0.12)),

    # 3. roof tile -- all three strategies compete
    ("roof_A_proc",    "roof tile",   "procedural",
     lambda: P.proc_roof_tile(scale=1.0, bump=0.8)),
    ("roof_B_lib",     "roof tile",   "public-library",
     lambda: M.library_material("clay_roof_tiles_02", scale=1.4, bump=0.5, grime=0.18)),
    ("roof_C_gen",     "roof tile",   "openai-generated",
     lambda: M.generated_material("gen_roof_tile", scale=1.2, bump=0.55, grime=0.12)),

    # 4. cobblestone ground
    ("cobble_A_proc",  "cobblestone", "procedural",
     lambda: P.proc_cobblestone(scale=1.0, bump=0.75)),
    ("cobble_B_lib",   "cobblestone", "public-library",
     lambda: M.library_material("cobblestone_floor_02", scale=1.3, bump=0.55, grime=0.20)),

    # 5. aged wood
    ("wood_A_proc",    "aged wood",   "procedural",
     lambda: P.proc_wood(scale=1.0, bump=0.4)),
    ("wood_B_lib",     "aged wood",   "public-library",
     lambda: M.library_material("weathered_peeling_timber", scale=1.2, bump=0.40, grime=0.15)),
    ("wood_C_gen",     "aged wood",   "openai-generated",
     lambda: M.generated_material("gen_shop_timber", scale=1.1, bump=0.45, grime=0.10)),

    # 6. metal fixture
    ("metal_A_proc",   "metal",       "procedural",
     lambda: P.proc_metal(scale=1.0, bump=0.35)),
    ("metal_B_lib",    "metal",       "public-library",
     lambda: M.library_material("rust_coarse_01", scale=1.5, bump=0.35, grime=0.0)),
]

CLOSE = (512, 512)
GAME = (426, 240)


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "GPU"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    try:
        prefs.compute_device_type = "OPTIX"
        for d in prefs.get_devices_for_type("OPTIX"):
            d.use = True
    except Exception:
        pass
    scene.cycles.samples = 96
    scene.cycles.use_denoising = True
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "Filmic"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 0.0
    return scene


def build_court(scene):
    """One tessellated test slab plus a fixed three-light rig, built once."""
    bpy.ops.mesh.primitive_plane_add(size=2.0, location=(0, 0, 0))
    slab = bpy.context.active_object
    slab.name = "TEST_SLAB"
    # subdivide so real displacement has somewhere to go
    mod = slab.modifiers.new("Subsurf", "SUBSURF")
    mod.subdivision_type = "SIMPLE"
    mod.levels = mod.render_levels = 6
    slab.rotation_euler = (math.radians(90.0), 0.0, 0.0)

    # a small chamfered block in front so relief reads against a silhouette
    bpy.ops.mesh.primitive_cube_add(size=0.34, location=(0.62, -0.30, -0.62))
    blk = bpy.context.active_object
    blk.name = "TEST_BLOCK"
    b = blk.modifiers.new("Bevel", "BEVEL")
    b.width = 0.012
    b.segments = 2

    # key / fill / bounce -- warm sun, cool sky, warm ground bounce
    key = bpy.data.lights.new("KEY", "AREA")
    key.energy = 420.0
    key.size = 2.2
    key.color = (1.0, 0.90, 0.74)
    ko = bpy.data.objects.new("KEY", key)
    ko.location = (2.6, -3.0, 2.4)
    ko.rotation_euler = (math.radians(52), 0, math.radians(41))
    scene.collection.objects.link(ko)

    fill = bpy.data.lights.new("FILL", "AREA")
    fill.energy = 90.0
    fill.size = 4.0
    fill.color = (0.62, 0.74, 1.0)
    fo = bpy.data.objects.new("FILL", fill)
    fo.location = (-3.0, -2.4, 1.4)
    fo.rotation_euler = (math.radians(70), 0, math.radians(-52))
    scene.collection.objects.link(fo)

    world = bpy.data.worlds.new("W")
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.16, 0.18, 0.23, 1.0)
    bg.inputs["Strength"].default_value = 0.55
    scene.world = world

    cam_data = bpy.data.cameras.new("CAM")
    cam_data.lens = 43.27          # the gauntlet baseline lens
    cam = bpy.data.objects.new("CAM", cam_data)
    cam.location = (0.0, -2.55, 0.0)
    cam.rotation_euler = (math.radians(90.0), 0.0, 0.0)
    scene.collection.objects.link(cam)
    scene.camera = cam
    return slab, blk


def render(scene, path, res):
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    scene = reset()
    slab, blk = build_court(scene)
    records = []
    for sid, family, strategy, factory in SAMPLES:
        mat = factory()
        for ob in (slab, blk):
            ob.data.materials.clear()
            ob.data.materials.append(mat)
        render(scene, OUT / f"close_{sid}.png", CLOSE)
        render(scene, OUT / f"game_{sid}.png", GAME)
        records.append({"id": sid, "family": family, "strategy": strategy,
                        "sourceId": mat.get("th_source_id"),
                        "close": f"close_{sid}.png", "game": f"game_{sid}.png"})
        print(f"RENDERED {sid:16s} {family:12s} {strategy:16s} {mat.get('th_source_id')}")
    (OUT / "samples.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
    print(f"MICRO_GAUNTLET OK {len(records)} samples -> {OUT}")


if __name__ == "__main__":
    main()
