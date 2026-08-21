"""Build the final winning Second Gate Cinder-Quay town environment.

Constructs the comprehensive master .blend with rich TH_SOURCE, optimized TH_RENDER,
collision volumes, spatial anchors, preview actors, and calibrated camera.
"""

from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WALKER_PATH = ROOT / "projects" / "hichaukitoden-game" / "assets" / "character" / "walker.png"
NPC_PATH = ROOT / "projects" / "hichaukitoden-game" / "assets" / "character" / "npc_female_redhead_dress.png"

if str(ROOT / "tools" / "blender") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools" / "blender"))

import build_gauntlet_environments
import refine_gauntlet_environments


def build_winner_master(blend_path: Path):
    import bpy
    import thestra_camera
    import second_gate_render

    blend_path = Path(blend_path).resolve()
    blend_path.parent.mkdir(parents=True, exist_ok=True)

    # Base build
    build_gauntlet_environments.build_cinder_quay_scene(blend_path)
    bpy.ops.wm.open_mainfile(filepath=str(blend_path))
    scene = bpy.context.scene
    cols = build_gauntlet_environments.ensure_collections()

    # Load baked facade images
    proj_dir = ROOT / "projects" / "hichaukitoden-game" / "assets" / "authoring" / "second_gate_gauntlet" / "projections" / "direction_a_A1"
    tex_2f = proj_dir / "SRC_Apothecary_2F_Mass_facade_baked.png"
    tex_3f = proj_dir / "SRC_Apothecary_3F_Mass_facade_baked.png"
    facade_img = proj_dir / "baked_result.png"

    mat_apothecary_facade = refine_gauntlet_environments.setup_image_material(
        "MAT_Apothecary_Facade", tex_2f if tex_2f.exists() else facade_img, roughness_val=0.72
    )
    mat_apothecary_attic = refine_gauntlet_environments.setup_image_material(
        "MAT_Apothecary_Attic", tex_3f if tex_3f.exists() else facade_img, roughness_val=0.75
    )

    obj_2f = bpy.data.objects.get("SRC_Apothecary_2F_Mass")
    if obj_2f:
        obj_2f.data.materials.clear()
        obj_2f.data.materials.append(mat_apothecary_facade)

    obj_3f = bpy.data.objects.get("SRC_Apothecary_3F_Mass")
    if obj_3f:
        obj_3f.data.materials.clear()
        obj_3f.data.materials.append(mat_apothecary_attic)

    mat_stone = bpy.data.materials.get("MAT_StoneQuay")
    mat_iron = bpy.data.materials.get("MAT_Iron")
    mat_wood = bpy.data.materials.get("MAT_WoodBeams")
    mat_window = bpy.data.materials.get("MAT_WindowGlass")
    mat_water = bpy.data.materials.get("MAT_CanalWater")

    # Extra rich TH_SOURCE details
    build_gauntlet_environments.create_box("SRC_QuayCurb", (0.0, -0.75, 0.05), (14.0, 0.15, 0.1), cols["TH_SOURCE"], mat_stone)
    build_gauntlet_environments.create_box("SRC_QuayPavingPuddles", (-1.5, 0.4, 0.01), (2.5, 1.2, 0.02), cols["TH_SOURCE"], mat_water)

    # Real recessed doorway arch surround & steps
    build_gauntlet_environments.create_box("SRC_DoorStep", (0.2, 1.6, 0.05), (1.5, 0.5, 0.1), cols["TH_SOURCE"], mat_stone)
    build_gauntlet_environments.create_box("SRC_DoorArchLeft", (-0.45, 1.8, 1.1), (0.25, 0.4, 2.2), cols["TH_SOURCE"], mat_stone)
    build_gauntlet_environments.create_box("SRC_DoorArchRight", (0.85, 1.8, 1.1), (0.25, 0.4, 2.2), cols["TH_SOURCE"], mat_stone)
    build_gauntlet_environments.create_box("SRC_DoorArchTop", (0.2, 1.8, 2.25), (1.55, 0.4, 0.35), cols["TH_SOURCE"], mat_stone)

    # Hanging herb bundles & market clutter
    for x_herb in (-1.6, -0.2, 0.9, 1.8):
        build_gauntlet_environments.create_cylinder(f"SRC_HerbBundle_{x_herb}", (x_herb, 0.6, 2.5), radius=0.08, depth=0.4, col=cols["TH_SOURCE"], mat=mat_wood)

    build_gauntlet_environments.create_box("SRC_LampBracket", (-2.6, 1.0, 2.2), (0.06, 0.6, 0.06), cols["TH_SOURCE"], mat_iron)
    build_gauntlet_environments.create_cylinder("SRC_LampLantern", (-2.6, 0.7, 2.0), radius=0.14, depth=0.32, col=cols["TH_SOURCE"], mat=mat_window)

    # Clear and rebuild TH_RENDER for optimal baking & real-3D silhouette coverage
    col_rnd = cols["TH_RENDER"]
    for obj in list(col_rnd.objects):
        bpy.data.objects.remove(obj, do_unlink=True)

    r_promenade = build_gauntlet_environments.create_box("RND_Quay", (0.0, 0.6, -0.4), (14.0, 2.8, 0.8), col_rnd)
    r_dockwall = build_gauntlet_environments.create_box("RND_DockWall", (0.0, -1.0, -0.75), (14.0, 0.4, 1.5), col_rnd)
    r_post_l = build_gauntlet_environments.create_box("RND_Post_L", (-3.6, -1.1, 0.35), (0.45, 0.45, 0.9), col_rnd)
    r_post_r = build_gauntlet_environments.create_box("RND_Post_R", (3.2, -1.1, 0.35), (0.45, 0.45, 0.9), col_rnd)
    r_apothecary_gf = build_gauntlet_environments.create_box("RND_Apothecary_GF", (0.2, 2.4, 1.4), (5.2, 2.4, 2.8), col_rnd)
    r_apothecary_2f = build_gauntlet_environments.create_box("RND_Apothecary_2F", (0.2, 2.2, 4.2), (5.0, 3.2, 2.8), col_rnd)
    r_bay = build_gauntlet_environments.create_box("RND_BayWindow", (0.2, 0.4, 4.0), (1.8, 0.6, 1.6), col_rnd)
    r_apothecary_3f = build_gauntlet_environments.create_box("RND_Apothecary_3F", (0.2, 2.05, 6.9), (4.8, 3.5, 2.6), col_rnd)
    r_roof = build_gauntlet_environments.create_box("RND_Roof", (0.2, 2.2, 9.4), (5.2, 3.8, 2.4), col_rnd)
    r_chimney = build_gauntlet_environments.create_box("RND_Chimney", (2.2, 2.4, 9.6), (0.8, 0.8, 3.2), col_rnd)
    r_alley = build_gauntlet_environments.create_box("RND_Alley", (-4.0, 2.4, 4.8), (3.2, 2.8, 7.5), col_rnd)
    r_annex = build_gauntlet_environments.create_box("RND_Annex", (4.5, 2.6, 2.2), (3.2, 2.6, 4.4), col_rnd)
    r_bg = build_gauntlet_environments.create_box("RND_BG", (0.0, 12.0, 6.0), (16.0, 4.0, 12.0), col_rnd)

    rnd_parts = [
        r_promenade, r_dockwall, r_post_l, r_post_r,
        r_apothecary_gf, r_apothecary_2f, r_bay, r_apothecary_3f, r_roof, r_chimney,
        r_alley, r_annex, r_bg
    ]
    bpy.ops.object.select_all(action='DESELECT')
    for p in rnd_parts:
        p.select_set(True)
    scene.view_layers[0].objects.active = r_promenade
    bpy.ops.object.join()
    r_final = bpy.context.active_object
    r_final.name = "TH_RENDER_Environment"
    if not r_final.data.uv_layers:
        r_final.data.uv_layers.new(name="UVMap")

    # Rebuild TH_COLLISION
    col_col = cols["TH_COLLISION"]
    for obj in list(col_col.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    build_gauntlet_environments.create_box("COL_Walkway", (0.0, 0.6, -0.2), (13.5, 2.2, 0.4), col_col)
    build_gauntlet_environments.create_box("COL_BuildingWall", (0.0, 2.0, 1.5), (14.0, 0.6, 3.0), col_col)
    build_gauntlet_environments.create_box("COL_QuayEdge", (0.0, -0.85, 0.5), (14.0, 0.3, 1.2), col_col)
    build_gauntlet_environments.create_box("COL_Post_L", (-3.6, -1.1, 0.4), (0.5, 0.5, 1.0), col_col)
    build_gauntlet_environments.create_box("COL_Post_R", (3.2, -1.1, 0.4), (0.5, 0.5, 1.0), col_col)

    # Rebuild TH_ANCHORS
    col_anc = cols["TH_ANCHORS"]
    for obj in list(col_anc.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    build_gauntlet_environments.create_anchor("spawn_player", (-4.5, 0.2, 0.0), forward=(1.0, 0.0, 0.0), col=col_anc)
    build_gauntlet_environments.create_anchor("walk_start", (-5.5, 0.2, 0.0), forward=(1.0, 0.0, 0.0), col=col_anc)
    build_gauntlet_environments.create_anchor("walk_end", (5.5, 0.2, 0.0), forward=(-1.0, 0.0, 0.0), col=col_anc)
    build_gauntlet_environments.create_anchor("doorway_apothecary", (0.2, 1.8, 0.0), forward=(0.0, 1.0, 0.0), col=col_anc)
    build_gauntlet_environments.create_anchor("doorway_annex", (3.8, 1.2, 0.0), forward=(0.0, 1.0, 0.0), col=col_anc)
    build_gauntlet_environments.create_anchor("npc_herbalist", (1.2, 0.5, 0.0), forward=(-0.7, -0.7, 0.0), col=col_anc)
    build_gauntlet_environments.create_anchor("npc_dockhand", (-2.2, -0.3, 0.0), forward=(0.7, 0.7, 0.0), col=col_anc)

    # Add second preview actor (redhead NPC) if available
    cam_obj = bpy.data.objects.get("TH_CAMERA_CALIBRATED")
    if cam_obj and NPC_PATH.is_file():
        npc = thestra_camera.create_actor_preview(NPC_PATH, cam_obj, anchor=(1.2, 0.5, 0.0), name="TH_NPC_HERBALIST_PREVIEW")
        build_gauntlet_environments.move_to(npc, cols["TH_PREVIEW_ACTORS"])

    second_gate_render.apply(scene, "cycles-candidate")
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    print(f"[winner] Saved winning master environment to {blend_path}")


def main():
    target = ROOT / "projects" / "hichaukitoden-game" / "assets" / "authoring" / "town" / "second_gate_cinder_quay" / "second_gate_cinder_quay.blend"
    build_winner_master(target)


if __name__ == "__main__":
    main()
