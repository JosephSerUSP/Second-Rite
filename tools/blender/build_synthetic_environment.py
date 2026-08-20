"""Build a synthetic Blender environment fixture conforming to the Second Rite V0 contract.

Collections created:
- TH_SOURCE: High-detail meshes, materials, and lighting (shrine, arch, lights).
- TH_RENDER: Lightweight coarse render/depth geometry with unwrapped UVs for baking,
             including a foreground occluder pillar/arch.
- TH_COLLISION: Simplified collision volumes.
- TH_ANCHORS: Named spatial empties with orientation (spawn_player, npc_elder, etc.).
- TH_PREVIEW_ACTORS: Preview walker actor quad using walker.png.
- TH_PREVIEW_ONLY: Visual grid guides.
- TH_CAMERA_PREVIEW: Camera object framing the scene.
"""

from __future__ import annotations

import math
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BLENDER_SEARCH = [
    os.environ.get("BLENDER"),
    r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender 4.2\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender 4.1\blender.exe",
    "blender",
]


def blender_executable():
    for candidate in BLENDER_SEARCH:
        if candidate and (candidate == "blender" or Path(candidate).is_file()):
            return candidate
    raise SystemExit("Blender not found; set BLENDER or install Blender")


def build_synthetic_scene_in_blender(blend_output_path: Path):
    import bpy

    # Clear everything
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for col in list(bpy.data.collections):
        bpy.data.collections.remove(col)
    for mat in list(bpy.data.materials):
        bpy.data.materials.remove(mat)
    for mesh in list(bpy.data.meshes):
        bpy.data.meshes.remove(mesh)

    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 1.0

    # Create root collections
    root_col = scene.collection
    col_source = bpy.data.collections.new("TH_SOURCE")
    col_render = bpy.data.collections.new("TH_RENDER")
    col_collision = bpy.data.collections.new("TH_COLLISION")
    col_anchors = bpy.data.collections.new("TH_ANCHORS")
    col_preview_actors = bpy.data.collections.new("TH_PREVIEW_ACTORS")
    col_preview_only = bpy.data.collections.new("TH_PREVIEW_ONLY")
    col_camera = bpy.data.collections.new("TH_CAMERA_PREVIEW")

    for c in (col_source, col_render, col_collision, col_anchors, col_preview_actors, col_preview_only, col_camera):
        root_col.children.link(c)

    # 1. Materials for TH_SOURCE
    mat_stone = bpy.data.materials.new("DetailedOldStone")
    mat_stone.use_nodes = True
    bsdf = mat_stone.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (0.55, 0.52, 0.48, 1.0)
        bsdf.inputs["Roughness"].default_value = 0.85

    mat_gold = bpy.data.materials.new("AltarRelicGold")
    mat_gold.use_nodes = True
    bsdf_gold = mat_gold.node_tree.nodes.get("Principled BSDF")
    if bsdf_gold:
        bsdf_gold.inputs["Base Color"].default_value = (0.85, 0.65, 0.15, 1.0)
        bsdf_gold.inputs["Metallic"].default_value = 0.9
        bsdf_gold.inputs["Roughness"].default_value = 0.3

    mat_wood = bpy.data.materials.new("ShopOakWood")
    mat_wood.use_nodes = True
    bsdf_wood = mat_wood.node_tree.nodes.get("Principled BSDF")
    if bsdf_wood:
        bsdf_wood.inputs["Base Color"].default_value = (0.35, 0.22, 0.12, 1.0)
        bsdf_wood.inputs["Roughness"].default_value = 0.7

    # 2. Geometry in TH_SOURCE (Rich source details: high-poly bevels, reliefs, altar bowl)
    # Ground floor slab
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 2.5, -0.1))
    src_floor = bpy.context.active_object
    src_floor.name = "SRC_Ground_Cobblestone"
    src_floor.scale = (6.0, 6.0, 0.2)
    src_floor.data.materials.append(mat_stone)
    col_source.objects.link(src_floor)
    root_col.objects.unlink(src_floor)

    # Detailed Town Altar / Fountain (High-detail source with subsurf)
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=0.9, depth=0.8, location=(0, 3.5, 0.4))
    src_altar = bpy.context.active_object
    src_altar.name = "SRC_TownAltar_Base"
    src_altar.data.materials.append(mat_stone)
    col_source.objects.link(src_altar)
    root_col.objects.unlink(src_altar)

    # Altar gold relic on top
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=0.3, location=(0, 3.5, 1.0))
    src_relic = bpy.context.active_object
    src_relic.name = "SRC_Altar_RelicSphere"
    src_relic.data.materials.append(mat_gold)
    col_source.objects.link(src_relic)
    root_col.objects.unlink(src_relic)

    # Detailed Back Wall
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 5.0, 1.5))
    src_wall = bpy.context.active_object
    src_wall.name = "SRC_BackWall"
    src_wall.scale = (6.0, 0.6, 3.0)
    src_wall.data.materials.append(mat_stone)
    col_source.objects.link(src_wall)
    root_col.objects.unlink(src_wall)

    # Detailed Foreground Archway Pillar (Occluder)
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.35, depth=3.0, location=(-1.8, 1.0, 1.5))
    src_pillar = bpy.context.active_object
    src_pillar.name = "SRC_ForegroundPillar"
    src_pillar.data.materials.append(mat_stone)
    col_source.objects.link(src_pillar)
    root_col.objects.unlink(src_pillar)

    # Lighting in TH_SOURCE
    # Warm Point Light near Altar
    bpy.ops.object.light_add(type='POINT', radius=0.25, location=(0, 3.0, 2.0))
    light_altar = bpy.context.active_object
    light_altar.name = "SRC_AltarWarmLight"
    light_altar.data.energy = 80.0
    light_altar.data.color = (1.0, 0.75, 0.45)
    col_source.objects.link(light_altar)
    root_col.objects.unlink(light_altar)

    # Sun Light for directional cast shadows
    bpy.ops.object.light_add(type='SUN', location=(4.0, -2.0, 6.0))
    light_sun = bpy.context.active_object
    light_sun.name = "SRC_SunLight"
    light_sun.data.energy = 2.5
    light_sun.data.color = (0.9, 0.95, 1.0)
    light_sun.rotation_euler = (math.radians(45), math.radians(20), math.radians(-30))
    col_source.objects.link(light_sun)
    root_col.objects.unlink(light_sun)

    # 3. Geometry in TH_RENDER (Coarse render & depth proxy mesh)
    # Coarse Floor
    bpy.ops.mesh.primitive_plane_add(size=6.0, location=(0, 2.5, 0.0))
    rnd_floor = bpy.context.active_object
    rnd_floor.name = "RND_Floor"
    col_render.objects.link(rnd_floor)
    root_col.objects.unlink(rnd_floor)

    # Coarse Back Wall
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 5.0, 1.5))
    rnd_wall = bpy.context.active_object
    rnd_wall.name = "RND_Wall"
    rnd_wall.scale = (6.0, 0.6, 3.0)
    col_render.objects.link(rnd_wall)
    root_col.objects.unlink(rnd_wall)

    # Coarse Altar Box / Octagon (deliberately 8-sided coarse cylinder)
    bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.9, depth=1.2, location=(0, 3.5, 0.6))
    rnd_altar = bpy.context.active_object
    rnd_altar.name = "RND_Altar"
    col_render.objects.link(rnd_altar)
    root_col.objects.unlink(rnd_altar)

    # Foreground Occluder Pillar in TH_RENDER (Square column)
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(-1.8, 1.0, 1.5))
    rnd_pillar = bpy.context.active_object
    rnd_pillar.name = "RND_ForegroundPillar"
    rnd_pillar.scale = (0.6, 0.6, 3.0)
    col_render.objects.link(rnd_pillar)
    root_col.objects.unlink(rnd_pillar)

    # Join TH_RENDER objects into a single clean combined render mesh with unwrapped UVs
    bpy.ops.object.select_all(action='DESELECT')
    for obj in [rnd_floor, rnd_wall, rnd_altar, rnd_pillar]:
        obj.select_set(True)
    scene.view_layers[0].objects.active = rnd_floor
    bpy.ops.object.join()
    render_mesh_obj = bpy.context.active_object
    render_mesh_obj.name = "RND_Environment_Mesh"

    # Unwrap UVs with Smart Project
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=66.0, island_margin=0.04)
    bpy.ops.object.mode_set(mode='OBJECT')

    # Assign bake target material
    mat_baked = bpy.data.materials.new("EnvironmentBakedAtlas")
    mat_baked.use_nodes = True
    render_mesh_obj.data.materials.clear()
    render_mesh_obj.data.materials.append(mat_baked)

    # 4. Geometry in TH_COLLISION (Simplified collision bounds)
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 2.5, -0.1))
    col_ground = bpy.context.active_object
    col_ground.name = "COL_Ground_Bounds"
    col_ground.scale = (6.0, 6.0, 0.2)
    col_collision.objects.link(col_ground)
    root_col.objects.unlink(col_ground)

    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 3.5, 0.5))
    col_altar = bpy.context.active_object
    col_altar.name = "COL_Altar_Blocking"
    col_altar.scale = (1.8, 1.8, 1.0)
    col_collision.objects.link(col_altar)
    root_col.objects.unlink(col_altar)

    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(-1.8, 1.0, 1.5))
    col_pillar = bpy.context.active_object
    col_pillar.name = "COL_Pillar_Blocking"
    col_pillar.scale = (0.7, 0.7, 3.0)
    col_collision.objects.link(col_pillar)
    root_col.objects.unlink(col_pillar)

    # 5. Anchors in TH_ANCHORS (Spatial markers)
    def create_anchor(name, location, rotation_z_deg):
        empty = bpy.data.objects.new(name, None)
        empty.empty_display_type = 'ARROWS'
        empty.empty_display_size = 0.5
        empty.location = location
        empty.rotation_euler = (0, 0, math.radians(rotation_z_deg))
        col_anchors.objects.link(empty)
        return empty

    create_anchor("spawn_player", (0.0, 0.5, 0.0), 0.0)
    create_anchor("npc_elder", (-0.8, 2.2, 0.0), 45.0)
    create_anchor("torch_mount", (-1.8, 1.0, 1.8), 90.0)
    create_anchor("shop_counter", (1.5, 2.0, 0.0), -45.0)

    # 6. Preview Actors in TH_PREVIEW_ACTORS (Excluded from bake/export)
    # Billboard quad for walker preview
    bpy.ops.mesh.primitive_plane_add(size=1.0, location=(-0.8, 2.2, 0.75))
    actor_quad = bpy.context.active_object
    actor_quad.name = "ACTOR_Walker_Billboard"
    actor_quad.scale = (0.8, 1.0, 1.5)
    actor_quad.rotation_euler = (math.radians(90), 0, 0)
    col_preview_actors.objects.link(actor_quad)
    root_col.objects.unlink(actor_quad)

    # Preview actor material referencing walker.png if present
    walker_path = ROOT / "projects" / "hichaukitoden-game" / "assets" / "character" / "walker.png"
    if walker_path.is_file():
        mat_walker = bpy.data.materials.new("WalkerPreview")
        mat_walker.use_nodes = True
        img_node = mat_walker.node_tree.nodes.new("ShaderNodeTexImage")
        img_node.image = bpy.data.images.load(str(walker_path))
        bsdf_w = mat_walker.node_tree.nodes.get("Principled BSDF")
        if bsdf_w:
            mat_walker.node_tree.links.new(img_node.outputs["Color"], bsdf_w.inputs["Base Color"])
            mat_walker.node_tree.links.new(img_node.outputs["Alpha"], bsdf_w.inputs["Alpha"])
        mat_walker.blend_method = 'CLIP'
        actor_quad.data.materials.append(mat_walker)

    # 7. Preview Only guides
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=6, y_subdivisions=6, size=6.0, location=(0, 2.5, 0.01))
    grid_guide = bpy.context.active_object
    grid_guide.name = "GUIDE_GroundGrid"
    col_preview_only.objects.link(grid_guide)
    root_col.objects.unlink(grid_guide)

    # 8. Camera in TH_CAMERA_PREVIEW
    cam_data = bpy.data.cameras.new("TH_Camera")
    cam_data.lens = 35
    cam_obj = bpy.data.objects.new("TH_Camera_Preview", cam_data)
    cam_obj.location = (0.0, -2.5, 2.0)
    cam_obj.rotation_euler = (math.radians(72), 0, 0)
    col_camera.objects.link(cam_obj)
    scene.camera = cam_obj

    # Save out the blend file
    blend_output_path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_output_path))
    print(f"Synthetic fixture written to {blend_output_path}")


def generate_synthetic_blend(output_path: Path):
    if "bpy" in sys.modules:
        build_synthetic_scene_in_blender(Path(output_path))
        return

    import subprocess
    import tempfile

    blender = blender_executable()
    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    script_path = Path(__file__).resolve()
    temp_runner = tempfile.NamedTemporaryFile(prefix="build_env_", suffix=".py", delete=False, mode="w", encoding="utf-8")
    temp_runner.write(
        f"import sys\n"
        f"sys.path.insert(0, {repr(str(script_path.parent))})\n"
        f"from build_synthetic_environment import build_synthetic_scene_in_blender\n"
        f"from pathlib import Path\n"
        f"build_synthetic_scene_in_blender(Path({repr(str(output_path))}))\n"
    )
    temp_runner.close()

    try:
        cmd = [blender, "--background", "--factory-startup", "--python", temp_runner.name]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            print(res.stdout)
            print(res.stderr, file=sys.stderr)
            raise SystemExit(f"Blender failed with code {res.returncode}")
        print(f"SUCCESS: Built {output_path}")
    finally:
        if os.path.exists(temp_runner.name):
            os.unlink(temp_runner.name)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Generate synthetic Blender environment fixture.")
    parser.add_argument("--output", "-o", default=str(ROOT / "tools" / "blender" / "fixtures" / "town_slice_synthetic.blend"),
                        help="Output .blend path")
    args = parser.parse_args()
    generate_synthetic_blend(Path(args.output))


if __name__ == "__main__":
    if "bpy" in sys.modules:
        pass
    else:
        main()

