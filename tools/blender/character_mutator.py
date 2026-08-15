"""In-place Blender document mutator for character gauntlet rounds.

Modifies authoritative .blend character documents in place to address specific visual failures
identified during the 24x24 pixel gauntlet.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

try:
    import bpy
    import bmesh
    from mathutils import Vector, Euler
except ImportError:
    bpy = None
    bmesh = None

ROOT = Path(__file__).resolve().parents[2]
AUTHORING_DIR = ROOT / "assets" / "authoring" / "characters"


def apply_round_2_contrast_mutations():
    """Round 2: Increase local value contrast, visor/eye gleams, and rim separation in .blend sources."""
    print("=== APPLYING ROUND 2 MUTATIONS (CONTRAST & VALUE GROUPING) ===")

    # 1. Knight
    knight_p = AUTHORING_DIR / "knight_volumetric.blend"
    bpy.ops.wm.open_mainfile(filepath=str(knight_p))
    
    mat_visor = bpy.data.materials.get("Mat_VisorGleam")
    if mat_visor and mat_visor.node_tree:
        bsdf = mat_visor.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            if "Emission Strength" in bsdf.inputs:
                bsdf.inputs["Emission Strength"].default_value = 2.8
            if "Emission Color" in bsdf.inputs:
                bsdf.inputs["Emission Color"].default_value = (0.5, 0.85, 1.0, 1.0)
            bsdf.inputs["Base Color"].default_value = (0.02, 0.04, 0.08, 1.0)

    mat_tunic = bpy.data.materials.get("Mat_NavyTunic")
    if mat_tunic and mat_tunic.node_tree:
        bsdf = mat_tunic.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs["Base Color"].default_value = (0.06, 0.08, 0.16, 1.0)
            bsdf.inputs["Roughness"].default_value = 0.95

    mat_gold = bpy.data.materials.get("Mat_Gold")
    if mat_gold and mat_gold.node_tree:
        bsdf = mat_gold.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs["Base Color"].default_value = (0.95, 0.78, 0.22, 1.0)
            bsdf.inputs["Roughness"].default_value = 0.18

    bpy.ops.wm.save_as_mainfile(filepath=str(knight_p))
    print("Saved Knight Round 2 mutations")

    # 2. Rogue
    rogue_p = AUTHORING_DIR / "rogue_faceted.blend"
    bpy.ops.wm.open_mainfile(filepath=str(rogue_p))

    mat_skin = bpy.data.materials.get("Mat_FaceSkin")
    if mat_skin and mat_skin.node_tree:
        bsdf = mat_skin.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs["Base Color"].default_value = (0.96, 0.82, 0.72, 1.0)
            bsdf.inputs["Roughness"].default_value = 0.35

    mat_eye = bpy.data.materials.get("Mat_EyeGlow")
    if mat_eye and mat_eye.node_tree:
        bsdf = mat_eye.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            if "Emission Strength" in bsdf.inputs:
                bsdf.inputs["Emission Strength"].default_value = 3.5

    mat_cloak = bpy.data.materials.get("Mat_ShadowCloak")
    if mat_cloak and mat_cloak.node_tree:
        bsdf = mat_cloak.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs["Base Color"].default_value = (0.05, 0.04, 0.08, 1.0)

    bpy.ops.wm.save_as_mainfile(filepath=str(rogue_p))
    print("Saved Rogue Round 2 mutations")

    # 3. Mage
    mage_p = AUTHORING_DIR / "mage_planar.blend"
    bpy.ops.wm.open_mainfile(filepath=str(mage_p))

    mat_orb = bpy.data.materials.get("Mat_OrbGlow")
    if mat_orb and mat_orb.node_tree:
        bsdf = mat_orb.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            if "Emission Strength" in bsdf.inputs:
                bsdf.inputs["Emission Strength"].default_value = 4.0
            if "Emission Color" in bsdf.inputs:
                bsdf.inputs["Emission Color"].default_value = (0.2, 0.95, 1.0, 1.0)

    mat_trim = bpy.data.materials.get("Mat_MageGold")
    if mat_trim and mat_trim.node_tree:
        bsdf = mat_trim.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs["Base Color"].default_value = (0.98, 0.82, 0.25, 1.0)
            bsdf.inputs["Roughness"].default_value = 0.15

    bpy.ops.wm.save_as_mainfile(filepath=str(mage_p))
    print("Saved Mage Round 2 mutations")


def apply_round_3_proportional_mutations():
    """Round 3: Exaggerate chibi proportions (head, weapons, pauldrons, brim) for 24x24 readability."""
    print("=== APPLYING ROUND 3 MUTATIONS (CHIBI PROPORTIONS & SILHOUETTES) ===")

    # 1. Knight
    knight_p = AUTHORING_DIR / "knight_volumetric.blend"
    bpy.ops.wm.open_mainfile(filepath=str(knight_p))

    helm = bpy.data.objects.get("Helmet_Dome")
    if helm:
        helm.scale = (1.15, 1.20, 1.18)

    pauldron_l = bpy.data.objects.get("Pauldron_L_Mesh")
    pauldron_r = bpy.data.objects.get("Pauldron_R_Mesh")
    if pauldron_l:
        pauldron_l.scale = (1.30, 1.30, 1.05)
    if pauldron_r:
        pauldron_r.scale = (1.30, 1.30, 1.05)

    sword_blade = bpy.data.objects.get("Sword_Blade")
    if sword_blade:
        sword_blade.scale = (1.45, 1.40, 1.15)

    shield = bpy.data.objects.get("Shield_Mesh")
    if shield:
        shield.scale = (1.20, 1.20, 1.10)

    bpy.ops.wm.save_as_mainfile(filepath=str(knight_p))
    print("Saved Knight Round 3 proportional mutations")

    # 2. Rogue
    rogue_p = AUTHORING_DIR / "rogue_faceted.blend"
    bpy.ops.wm.open_mainfile(filepath=str(rogue_p))

    hood = bpy.data.objects.get("Hood_Peaked")
    if hood:
        hood.scale = (1.18, 1.18, 1.25)

    collar_l = bpy.data.objects.get("Collar_Wing_L")
    if collar_l:
        collar_l.scale = (1.25, 1.30, 1.20)
        collar_l.location = (-0.28, -0.06, 0.08)

    dagger = bpy.data.objects.get("Dagger_Blade_L")
    if dagger:
        dagger.scale = (1.60, 1.40, 1.25)

    cape = bpy.data.objects.get("Cape_Panel")
    if cape:
        cape.scale = (1.25, 1.10, 1.15)

    bpy.ops.wm.save_as_mainfile(filepath=str(rogue_p))
    print("Saved Rogue Round 3 proportional mutations")

    # 3. Mage
    mage_p = AUTHORING_DIR / "mage_planar.blend"
    bpy.ops.wm.open_mainfile(filepath=str(mage_p))

    hat_brim = bpy.data.objects.get("Hat_Brim")
    if hat_brim:
        hat_brim.scale = (1.22, 1.22, 1.0)

    orb = bpy.data.objects.get("Orb_Core")
    if orb:
        orb.scale = (1.35, 1.35, 1.35)

    sleeve_l = bpy.data.objects.get("Sleeve_L")
    sleeve_r = bpy.data.objects.get("Sleeve_R")
    if sleeve_l:
        sleeve_l.scale = (1.25, 1.25, 1.25)
    if sleeve_r:
        sleeve_r.scale = (1.25, 1.25, 1.25)

    staff_crystal = bpy.data.objects.get("Staff_Crystal")
    if staff_crystal:
        staff_crystal.scale = (1.30, 1.30, 1.30)

    bpy.ops.wm.save_as_mainfile(filepath=str(mage_p))
    print("Saved Mage Round 3 proportional mutations")


def apply_round_5_lighting_polish_mutations():
    """Round 5: Adjust studio lighting (key/fill/rim balance) for clean pixel highlights across all directions."""
    print("=== APPLYING ROUND 5 MUTATIONS (STUDIO LIGHTING & NORMAL POLISH) ===")
    
    for blend_name in ("knight_volumetric.blend", "rogue_faceted.blend", "mage_planar.blend"):
        p = AUTHORING_DIR / blend_name
        bpy.ops.wm.open_mainfile(filepath=str(p))

        key = bpy.data.objects.get("Key_Light")
        if key:
            key.data.energy = 2.6
            key.data.color = (1.0, 0.97, 0.92)

        fill = bpy.data.objects.get("Fill_Light")
        if fill:
            fill.data.energy = 0.95
            fill.data.color = (0.70, 0.80, 0.98)

        rim = bpy.data.objects.get("Rim_Light")
        if rim:
            rim.data.energy = 2.0

        bpy.ops.wm.save_as_mainfile(filepath=str(p))
        print(f"Updated studio lighting in {blend_name}")


def apply_round_6_animation_dynamics_mutations():
    """Round 6: Exaggerate walk strides, body bounce, and limb swings for dynamic readability in motion."""
    print("=== APPLYING ROUND 6 MUTATIONS (ANIMATION DYNAMICS & SILHOUETTE FLUTTER) ===")

    # 1. Knight
    knight_p = AUTHORING_DIR / "knight_volumetric.blend"
    bpy.ops.wm.open_mainfile(filepath=str(knight_p))
    act = bpy.data.actions.get("Knight_Walk")
    if act:
        hips = bpy.data.objects.get("Hips")
        leg_l = bpy.data.objects.get("Leg_L")
        leg_r = bpy.data.objects.get("Leg_R")
        sh_l = bpy.data.objects.get("Shoulder_L")
        sh_r = bpy.data.objects.get("Shoulder_R")

        for obj in (hips, leg_l, leg_r, sh_l, sh_r):
            if obj and obj.animation_data:
                obj.animation_data.action = act

        if leg_l:
            leg_l.rotation_euler = (math.radians(38), 0.0, 0.0)
            leg_l.keyframe_insert(data_path="rotation_euler", frame=1)
            leg_l.rotation_euler = (math.radians(-38), 0.0, 0.0)
            leg_l.keyframe_insert(data_path="rotation_euler", frame=9)
            leg_l.rotation_euler = (math.radians(38), 0.0, 0.0)
            leg_l.keyframe_insert(data_path="rotation_euler", frame=17)
        if leg_r:
            leg_r.rotation_euler = (math.radians(-38), 0.0, 0.0)
            leg_r.keyframe_insert(data_path="rotation_euler", frame=1)
            leg_r.rotation_euler = (math.radians(38), 0.0, 0.0)
            leg_r.keyframe_insert(data_path="rotation_euler", frame=9)
            leg_r.rotation_euler = (math.radians(-38), 0.0, 0.0)
            leg_r.keyframe_insert(data_path="rotation_euler", frame=17)
        if hips:
            hips.location = (0.0, 0.0, 0.50)
            hips.keyframe_insert(data_path="location", frame=1)
            hips.location = (0.0, 0.0, 0.57)
            hips.keyframe_insert(data_path="location", frame=5)
            hips.location = (0.0, 0.0, 0.50)
            hips.keyframe_insert(data_path="location", frame=9)
            hips.location = (0.0, 0.0, 0.57)
            hips.keyframe_insert(data_path="location", frame=13)
            hips.location = (0.0, 0.0, 0.50)
            hips.keyframe_insert(data_path="location", frame=17)

    bpy.ops.wm.save_as_mainfile(filepath=str(knight_p))
    print("Saved Knight Round 6 animation mutations")

    # 2. Rogue
    rogue_p = AUTHORING_DIR / "rogue_faceted.blend"
    bpy.ops.wm.open_mainfile(filepath=str(rogue_p))
    act = bpy.data.actions.get("Rogue_Walk")
    if act:
        cape = bpy.data.objects.get("Cape_Root")
        leg_l = bpy.data.objects.get("Leg_L")
        leg_r = bpy.data.objects.get("Leg_R")
        for obj in (cape, leg_l, leg_r):
            if obj and obj.animation_data:
                obj.animation_data.action = act

        if cape:
            cape.rotation_euler = (math.radians(25), math.radians(-18), 0.0)
            cape.keyframe_insert(data_path="rotation_euler", frame=1)
            cape.rotation_euler = (math.radians(32), math.radians(18), 0.0)
            cape.keyframe_insert(data_path="rotation_euler", frame=9)
            cape.rotation_euler = (math.radians(25), math.radians(-18), 0.0)
            cape.keyframe_insert(data_path="rotation_euler", frame=17)

    bpy.ops.wm.save_as_mainfile(filepath=str(rogue_p))
    print("Saved Rogue Round 6 animation mutations")

    # 3. Mage
    mage_p = AUTHORING_DIR / "mage_planar.blend"
    bpy.ops.wm.open_mainfile(filepath=str(mage_p))
    act = bpy.data.actions.get("Mage_Walk")
    if act:
        orb = bpy.data.objects.get("Orb_Joint")
        skirt = bpy.data.objects.get("Robe_Skirt")
        hips = bpy.data.objects.get("Hips")
        for obj in (orb, skirt, hips):
            if obj and obj.animation_data:
                obj.animation_data.action = act

        if orb:
            orb.location = (-0.06, -0.14, 0.12)
            orb.keyframe_insert(data_path="location", frame=1)
            orb.location = (-0.06, -0.14, 0.28)
            orb.keyframe_insert(data_path="location", frame=9)
            orb.location = (-0.06, -0.14, 0.12)
            orb.keyframe_insert(data_path="location", frame=17)

        if skirt:
            skirt.rotation_euler = (math.radians(-10), 0.0, math.radians(-12))
            skirt.keyframe_insert(data_path="rotation_euler", frame=1)
            skirt.rotation_euler = (math.radians(10), 0.0, math.radians(12))
            skirt.keyframe_insert(data_path="rotation_euler", frame=9)
            skirt.rotation_euler = (math.radians(-10), 0.0, math.radians(-12))
            skirt.keyframe_insert(data_path="rotation_euler", frame=17)

    bpy.ops.wm.save_as_mainfile(filepath=str(mage_p))
    print("Saved Mage Round 6 animation mutations")


if __name__ == "__main__":
    if "--round-2" in sys.argv:
        apply_round_2_contrast_mutations()
    elif "--round-3" in sys.argv:
        apply_round_3_proportional_mutations()
    elif "--round-5" in sys.argv:
        apply_round_5_lighting_polish_mutations()
    elif "--round-6" in sys.argv:
        apply_round_6_animation_dynamics_mutations()
