"""Refine both gauntlet environments into candidate-quality TH_SOURCE scenes.

Combines:
- Projected/baked whole-facade architectural imagery
- Fine physical geometry for openings, bay windows, corbels, buttresses, flues
- Procedural / image-derived normal and roughness maps
- Dramatic cinematic lighting with atmospheric depth
- Calibrated Thestra camera and Walker preview
"""

from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WALKER_PATH = ROOT / "projects" / "hichaukitoden-game" / "assets" / "character" / "walker.png"

if str(ROOT / "tools" / "blender") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools" / "blender"))

import build_gauntlet_environments


def setup_image_material(name, img_path: Path, roughness_val=0.75, normal_map_path: Path | None = None, emission_img_path: Path | None = None, emission_strength=1.0):
    import bpy
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    if img_path and img_path.is_file():
        img = bpy.data.images.load(str(img_path.resolve()), check_existing=True)
        tex_node = nodes.new("ShaderNodeTexImage")
        tex_node.image = img
        links.new(tex_node.outputs["Color"], bsdf.inputs["Base Color"])

    bsdf.inputs["Roughness"].default_value = roughness_val

    if emission_img_path and emission_img_path.is_file():
        em_img = bpy.data.images.load(str(emission_img_path.resolve()), check_existing=True)
        em_node = nodes.new("ShaderNodeTexImage")
        em_node.image = em_img
        if "Emission Color" in bsdf.inputs:
            links.new(em_node.outputs["Color"], bsdf.inputs["Emission Color"])
            bsdf.inputs["Emission Strength"].default_value = emission_strength
        elif "Emission" in bsdf.inputs:
            links.new(em_node.outputs["Color"], bsdf.inputs["Emission"])

    return mat


def build_refined_cinder_quay(blend_path: Path):
    """Refined Direction A: Cinder-Quay Apothecary."""
    import bpy
    import thestra_camera
    import second_gate_render

    # Start from base scene
    build_gauntlet_environments.build_cinder_quay_scene(blend_path)
    bpy.ops.wm.open_mainfile(filepath=str(blend_path))
    scene = bpy.context.scene
    cols = build_gauntlet_environments.ensure_collections()

    # Load baked facade images from projection
    proj_dir = ROOT / "projects" / "hichaukitoden-game" / "assets" / "authoring" / "second_gate_gauntlet" / "projections" / "direction_a_A1"
    tex_2f = proj_dir / "SRC_Apothecary_2F_Mass_facade_baked.png"
    tex_3f = proj_dir / "SRC_Apothecary_3F_Mass_facade_baked.png"
    facade_img = proj_dir / "baked_result.png"

    # Refine Apothecary materials
    mat_apothecary_facade = setup_image_material("MAT_Apothecary_Facade", tex_2f if tex_2f.exists() else facade_img, roughness_val=0.72)
    mat_apothecary_attic = setup_image_material("MAT_Apothecary_Attic", tex_3f if tex_3f.exists() else facade_img, roughness_val=0.75)

    obj_2f = bpy.data.objects.get("SRC_Apothecary_2F_Mass")
    if obj_2f:
        obj_2f.data.materials.clear()
        obj_2f.data.materials.append(mat_apothecary_facade)

    obj_3f = bpy.data.objects.get("SRC_Apothecary_3F_Mass")
    if obj_3f:
        obj_3f.data.materials.clear()
        obj_3f.data.materials.append(mat_apothecary_attic)

    # Add extra physical details:
    # 1. Quayside details: stone curb edging, drainage grating, iron ring mooring cleats
    mat_stone = bpy.data.materials.get("MAT_StoneQuay")
    mat_iron = bpy.data.materials.get("MAT_Iron")
    mat_wood = bpy.data.materials.get("MAT_WoodBeams")
    mat_window = bpy.data.materials.get("MAT_WindowGlass")

    build_gauntlet_environments.create_box("SRC_QuayCurb", (0.0, -0.75, 0.05), (14.0, 0.15, 0.1), cols["TH_SOURCE"], mat_stone)
    build_gauntlet_environments.create_box("SRC_QuayPavingPuddles", (-1.5, 0.4, 0.01), (2.5, 1.2, 0.02), cols["TH_SOURCE"], bpy.data.materials.get("MAT_CanalWater"))

    # 2. Doorway stone arch surround (promoting facade door opening to real geometry)
    build_gauntlet_environments.create_box("SRC_DoorArchLeft", (-0.45, 1.8, 1.1), (0.25, 0.4, 2.2), cols["TH_SOURCE"], mat_stone)
    build_gauntlet_environments.create_box("SRC_DoorArchRight", (0.85, 1.8, 1.1), (0.25, 0.4, 2.2), cols["TH_SOURCE"], mat_stone)
    build_gauntlet_environments.create_box("SRC_DoorArchTop", (0.2, 1.8, 2.25), (1.55, 0.4, 0.35), cols["TH_SOURCE"], mat_stone)

    # 3. Hanging herb bundles under jetty
    for x_herb in (-1.6, -0.2, 0.9, 1.8):
        build_gauntlet_environments.create_cylinder(f"SRC_HerbBundle_{x_herb}", (x_herb, 0.6, 2.5), radius=0.08, depth=0.4, col=cols["TH_SOURCE"], mat=mat_wood)

    # 4. Iron street lamp bracket on alley pillar
    build_gauntlet_environments.create_box("SRC_LampBracket", (-2.6, 1.0, 2.2), (0.06, 0.6, 0.06), cols["TH_SOURCE"], mat_iron)
    build_gauntlet_environments.create_cylinder("SRC_LampLantern", (-2.6, 0.7, 2.0), radius=0.14, depth=0.32, col=cols["TH_SOURCE"], mat=mat_window)

    # Apply cycles-candidate profile
    second_gate_render.apply(scene, "cycles-candidate")

    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    print(f"[refine] Refined Direction A saved to {blend_path}")


def build_refined_bell_weir(blend_path: Path):
    """Refined Direction B: Bell-Weir Cloister & Copper Foundry."""
    import bpy
    import thestra_camera
    import second_gate_render

    build_gauntlet_environments.build_bell_weir_scene(blend_path)
    bpy.ops.wm.open_mainfile(filepath=str(blend_path))
    scene = bpy.context.scene
    cols = build_gauntlet_environments.ensure_collections()

    proj_dir = ROOT / "projects" / "hichaukitoden-game" / "assets" / "authoring" / "second_gate_gauntlet" / "projections" / "direction_b_B1"
    tex_fl = proj_dir / "SRC_Foundry_Base_Left_facade_baked.png"
    tex_fr = proj_dir / "SRC_Foundry_Base_Right_facade_baked.png"
    tex_cd = proj_dir / "SRC_Foundry_CupolaDrum_facade_baked.png"
    facade_img = proj_dir / "baked_result.png"

    mat_foundry_facade = setup_image_material("MAT_Foundry_Facade", tex_fl if tex_fl.exists() else facade_img, roughness_val=0.78)
    mat_cupola_facade = setup_image_material("MAT_Cupola_Facade", tex_cd if tex_cd.exists() else facade_img, roughness_val=0.65)

    for name, mat in [
        ("SRC_Foundry_Base_Left", mat_foundry_facade),
        ("SRC_Foundry_Base_Right", mat_foundry_facade),
        ("SRC_Foundry_CupolaDrum", mat_cupola_facade),
    ]:
        obj = bpy.data.objects.get(name)
        if obj:
            obj.data.materials.clear()
            obj.data.materials.append(mat)

    mat_soot = bpy.data.materials.get("MAT_SootStone")
    mat_brick = bpy.data.materials.get("MAT_FoundryBrick")
    mat_iron = bpy.data.materials.get("MAT_IronRivet")
    mat_copper = bpy.data.materials.get("MAT_VerdigrisCopper")
    mat_glow = bpy.data.materials.get("MAT_FurnaceGlow")

    # Extra physical details:
    # 1. Stepped archivolt portal surround (promoting kiln opening to heavy stone portal)
    build_gauntlet_environments.create_box("SRC_KilnArchOuter", (3.1, 2.2, 4.4), (2.2, 0.4, 0.45), cols["TH_SOURCE"], mat_brick)
    build_gauntlet_environments.create_box("SRC_KilnArchJambL", (1.9, 2.2, 2.4), (0.4, 0.4, 3.6), cols["TH_SOURCE"], mat_brick)
    build_gauntlet_environments.create_box("SRC_KilnArchJambR", (4.3, 2.2, 2.4), (0.4, 0.4, 3.6), cols["TH_SOURCE"], mat_brick)

    # 2. Slag runoff trough / crucible channel along upper terrace
    build_gauntlet_environments.create_box("SRC_SlagChannel", (3.1, 1.1, 0.58), (0.5, 2.2, 0.1), cols["TH_SOURCE"], mat_iron)
    build_gauntlet_environments.create_box("SRC_MoltenSlag", (3.1, 1.1, 0.61), (0.35, 2.0, 0.05), cols["TH_SOURCE"], mat_glow)

    # 3. Flying buttress carved gothic pinnacles
    build_gauntlet_environments.create_box("SRC_Pinnacle_1", (-4.5, 1.4, 4.8), (0.45, 0.45, 1.2), cols["TH_SOURCE"], mat_soot)
    build_gauntlet_environments.create_box("SRC_Pinnacle_2", (-1.5, 1.4, 4.8), (0.45, 0.45, 1.2), cols["TH_SOURCE"], mat_soot)

    # 4. Iron flue support struts
    build_gauntlet_environments.create_box("SRC_FlueStrut_1", (4.4, 3.5, 6.0), (1.4, 0.1, 0.1), cols["TH_SOURCE"], mat_iron)
    build_gauntlet_environments.create_box("SRC_FlueStrut_2", (4.4, 3.5, 8.5), (1.4, 0.1, 0.1), cols["TH_SOURCE"], mat_iron)

    second_gate_render.apply(scene, "cycles-candidate")

    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    print(f"[refine] Refined Direction B saved to {blend_path}")


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--direction", choices=["a", "b", "all"], default="all")
    parser.add_argument("--outdir", type=Path, default=ROOT / "projects" / "hichaukitoden-game" / "assets" / "authoring" / "second_gate_gauntlet")
    
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    args = parser.parse_args(argv)

    outdir = args.outdir.resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    if args.direction in ("a", "all"):
        build_refined_cinder_quay(outdir / "direction_a_cinder_quay_refined.blend")
    if args.direction in ("b", "all"):
        build_refined_bell_weir(outdir / "direction_b_bell_weir_refined.blend")


if __name__ == "__main__":
    main()
