# gauntlet/pipeline/character_builder.py
# Procedural 3D Character Generator for Celina, Agnes, and The Gambler in Blender

import bpy
import bmesh
import math
from mathutils import Vector, Matrix
from gauntlet.pipeline.materials import get_celina_materials, get_agnes_materials, get_gambler_materials
from gauntlet.pipeline.armature_rig import create_humanoid_armature

def assign_vertex_group(obj: bpy.types.Object, group_name: str, weight: float = 1.0, indices=None):
    """Assigns vertices to a named vertex group for armature deformation."""
    vg = obj.vertex_groups.get(group_name)
    if vg is None:
        vg = obj.vertex_groups.new(name=group_name)
    if indices is None:
        indices = [v.index for v in obj.data.vertices]
    vg.add(indices, weight, 'REPLACE')

def create_mesh_part(name: str, primitive_type: str = 'CYLINDER', **kwargs) -> bpy.types.Object:
    """Helper to create a primitive mesh object, link it, and set smooth shading."""
    if primitive_type == 'CYLINDER':
        bpy.ops.mesh.primitive_cylinder_add(**kwargs)
    elif primitive_type == 'SPHERE':
        bpy.ops.mesh.primitive_uv_sphere_add(**kwargs)
    elif primitive_type == 'CUBE':
        bpy.ops.mesh.primitive_cube_add(**kwargs)
    elif primitive_type == 'CONE':
        bpy.ops.mesh.primitive_cone_add(**kwargs)
    elif primitive_type == 'TORUS':
        bpy.ops.mesh.primitive_torus_add(**kwargs)

    obj = bpy.context.active_object
    obj.name = name
    for poly in obj.data.polygons:
        poly.use_smooth = True
    return obj

def bind_to_armature(mesh_obj: bpy.types.Object, arm_obj: bpy.types.Object):
    """Adds Armature modifier to mesh object."""
    mod = mesh_obj.modifiers.new(name="Armature", type='ARMATURE')
    mod.object = arm_obj
    mesh_obj.parent = arm_obj

# -------------------------------------------------------------
# 1. CELINA BUILDER
# -------------------------------------------------------------
def build_celina() -> tuple:
    """
    Constructs Celina: Vertical, contained, deliberate, 5.5 heads tall (1.48m).
    Slender elongated silhouette (height_scale=0.92 -> 120px standing height, strictly <= 128px).
    High standing collar, sharp epaulets, narrow hourglass obsidian corset, split coat tails, rapier.
    """
    mats = get_celina_materials()
    arm_obj = create_humanoid_armature(
        name="Celina_Rig",
        height_scale=0.92,
        shoulder_width=0.18,
        hip_width=0.08,
        head_z=1.35,
        has_coat_bones=True,
        has_hat_bone=False
    )

    parts = []

    # 1. Slender Head & Sculpted Porcelain Face
    head = create_mesh_part("Celina_Head", 'SPHERE', radius=0.118, location=(0, 0.020, 1.37))
    head.scale = (0.80, 0.90, 1.05)
    head.data.materials.append(mats["skin"])
    assign_vertex_group(head, "head", 1.0)
    parts.append(head)

    chin = create_mesh_part("Celina_Chin", 'CONE', radius1=0.052, radius2=0.014, depth=0.068, location=(0, 0.055, 1.30))
    chin.rotation_euler = (math.radians(15), 0, 0)
    chin.data.materials.append(mats["skin"])
    assign_vertex_group(chin, "head", 1.0)
    parts.append(chin)

    # Stylized Eyes & Sharp Eyelash Wings on Front Face Plane
    for side, sign in [("L", 1), ("R", -1)]:
        eye_base = create_mesh_part(f"Celina_EyeBase_{side}", 'SPHERE', radius=0.026, location=(sign * 0.038, 0.112, 1.385))
        eye_base.scale = (1.1, 0.25, 0.80)
        eye_base.data.materials.append(mats["shirt_ivory"])
        assign_vertex_group(eye_base, "head", 1.0)
        parts.append(eye_base)

        iris = create_mesh_part(f"Celina_Iris_{side}", 'SPHERE', radius=0.018, location=(sign * 0.038, 0.120, 1.385))
        iris.scale = (0.85, 0.2, 0.85)
        iris.data.materials.append(mats["eye_cyan"])
        assign_vertex_group(iris, "head", 1.0)
        parts.append(iris)

        lash = create_mesh_part(f"Celina_Lash_{side}", 'CUBE', size=0.022, location=(sign * 0.040, 0.118, 1.405))
        lash.scale = (2.0, 0.3, 0.4)
        lash.rotation_euler = (0, math.radians(sign * -12), 0)
        lash.data.materials.append(mats["hair"])
        assign_vertex_group(lash, "head", 1.0)
        parts.append(lash)

        earring = create_mesh_part(f"Celina_Earring_{side}", 'SPHERE', radius=0.012, location=(sign * 0.098, 0.02, 1.35))
        earring.data.materials.append(mats["coat_trim"])
        assign_vertex_group(earring, "head", 1.0)
        parts.append(earring)

    nose = create_mesh_part("Celina_Nose", 'CONE', radius1=0.016, radius2=0.005, depth=0.040, location=(0, 0.132, 1.365))
    nose.rotation_euler = (math.radians(-25), 0, 0)
    nose.data.materials.append(mats["skin"])
    assign_vertex_group(nose, "head", 1.0)
    parts.append(nose)

    lips = create_mesh_part("Celina_Lips", 'CUBE', size=0.022, location=(0, 0.122, 1.330))
    lips.scale = (1.2, 0.3, 0.3)
    lips.data.materials.append(mats["gem_ruby"])
    assign_vertex_group(lips, "head", 1.0)
    parts.append(lips)

    # 2. Sleek Raven Hair Bun (Back of Head) & Framing Bangs
    hair_crown = create_mesh_part("Celina_HairCrown", 'SPHERE', radius=0.118, location=(0, -0.055, 1.39))
    hair_crown.scale = (0.90, 0.70, 0.95)
    hair_crown.data.materials.append(mats["hair"])
    assign_vertex_group(hair_crown, "head", 1.0)
    parts.append(hair_crown)

    hair_bun = create_mesh_part("Celina_HairBun", 'SPHERE', radius=0.075, location=(0, -0.15, 1.41))
    hair_bun.data.materials.append(mats["hair"])
    assign_vertex_group(hair_bun, "head", 1.0)
    parts.append(hair_bun)

    hairpin = create_mesh_part("Celina_Hairpin", 'CYLINDER', radius=0.007, depth=0.22, location=(0, -0.15, 1.43))
    hairpin.rotation_euler = (math.radians(20), math.radians(45), 0)
    hairpin.data.materials.append(mats["coat_trim"])
    assign_vertex_group(hairpin, "head", 1.0)
    parts.append(hairpin)

    # Framing Forehead & Side Bangs (Breaking the blank face oval)
    forehead_bang = create_mesh_part("Celina_ForeheadBang", 'CUBE', size=0.055, location=(0, 0.090, 1.435))
    forehead_bang.scale = (1.4, 0.3, 0.5)
    forehead_bang.rotation_euler = (math.radians(-10), 0, 0)
    forehead_bang.data.materials.append(mats["hair"])
    assign_vertex_group(forehead_bang, "head", 1.0)
    parts.append(forehead_bang)

    bang_l = create_mesh_part("Celina_BangL", 'CUBE', size=0.035, location=(0.075, 0.065, 1.38))
    bang_l.scale = (0.6, 0.4, 1.8)
    bang_l.rotation_euler = (0, math.radians(-10), math.radians(15))
    bang_l.data.materials.append(mats["hair"])
    assign_vertex_group(bang_l, "head", 1.0)
    parts.append(bang_l)

    bang_r = create_mesh_part("Celina_BangR", 'CUBE', size=0.035, location=(-0.075, 0.065, 1.38))
    bang_r.scale = (0.6, 0.4, 1.8)
    bang_r.rotation_euler = (0, math.radians(10), math.radians(-15))
    bang_r.data.materials.append(mats["hair"])
    assign_vertex_group(bang_r, "head", 1.0)
    parts.append(bang_r)

    # 3. Flared High Standing Fan Collar & Cravat
    collar = create_mesh_part("Celina_StandingCollar", 'CONE', radius1=0.145, radius2=0.185, depth=0.16, location=(0, -0.015, 1.25))
    collar.scale = (0.95, 0.72, 1.0)
    collar.data.materials.append(mats["coat_primary"])
    assign_vertex_group(collar, "chest", 1.0)
    parts.append(collar)

    cravat = create_mesh_part("Celina_Cravat", 'CUBE', size=0.055, location=(0, 0.070, 1.21))
    cravat.scale = (1.1, 0.35, 1.4)
    cravat.data.materials.append(mats["shirt_ivory"])
    assign_vertex_group(cravat, "chest", 1.0)
    parts.append(cravat)

    brooch = create_mesh_part("Celina_Brooch", 'SPHERE', radius=0.018, location=(0, 0.088, 1.23))
    brooch.data.materials.append(mats["gem_ruby"])
    assign_vertex_group(brooch, "chest", 1.0)
    parts.append(brooch)

    # 4. Sharp Epaulets on Shoulders (Broad distinct silhouette profile)
    for side, sign in [("L", 1), ("R", -1)]:
        epaulet = create_mesh_part(f"Celina_Epaulet_{side}", 'CUBE', size=0.058, location=(sign * 0.22, 0, 1.21))
        epaulet.scale = (1.5, 0.8, 0.4)
        epaulet.rotation_euler = (0, math.radians(sign * -15), 0)
        epaulet.data.materials.append(mats["coat_trim"])
        assign_vertex_group(epaulet, f"shoulder.{side}", 1.0)
        parts.append(epaulet)

    # 5. Slender Midnight Torso & Hourglass Obsidian Corset
    torso = create_mesh_part("Celina_ChestCoat", 'CYLINDER', radius=0.115, depth=0.22, location=(0, 0, 1.14))
    torso.scale = (1.05, 0.75, 1.0)
    torso.data.materials.append(mats["coat_primary"])
    assign_vertex_group(torso, "chest", 1.0)
    parts.append(torso)

    corset = create_mesh_part("Celina_Corset", 'CYLINDER', radius=0.095, depth=0.19, location=(0, 0, 0.97))
    corset.scale = (0.92, 0.70, 1.0)
    corset.data.materials.append(mats["vest_corset"])
    assign_vertex_group(corset, "hips", 1.0)
    parts.append(corset)

    # Gold buttons down corset
    for b_i, b_z in enumerate([1.03, 0.98, 0.93]):
        btn = create_mesh_part(f"Celina_Btn_{b_i}", 'SPHERE', radius=0.009, location=(0, 0.075, b_z))
        btn.data.materials.append(mats["coat_trim"])
        assign_vertex_group(btn, "hips", 1.0)
        parts.append(btn)

    # 6. Slender Split Coat Tails (Falling neatly behind legs)
    for side, sign in [("L", 1), ("R", -1)]:
        panel = create_mesh_part(f"Celina_CoatPanel_{side}", 'CYLINDER', radius=0.075, depth=0.55, location=(sign * 0.065, -0.04, 0.62))
        panel.scale = (0.85, 0.65, 1.0)
        panel.rotation_euler = (math.radians(6), math.radians(sign * 8), math.radians(sign * -4))
        panel.data.materials.append(mats["coat_primary"])
        assign_vertex_group(panel, f"coat_{side}.01", 0.7)
        assign_vertex_group(panel, f"coat_{side}.02", 0.3)
        parts.append(panel)

    # 7. Slender Arms & Articulated Gloves (Angled outward for clear negative space)
    for side, sign in [("L", 1), ("R", -1)]:
        uarm = create_mesh_part(f"Celina_UpperArm_{side}", 'CYLINDER', radius=0.034, depth=0.24, location=(sign * 0.21, 0, 1.07))
        uarm.rotation_euler = (0, math.radians(sign * 8), 0)
        uarm.data.materials.append(mats["coat_primary"])
        assign_vertex_group(uarm, f"upper_arm.{side}", 1.0)
        parts.append(uarm)

        farm = create_mesh_part(f"Celina_Forearm_{side}", 'CYLINDER', radius=0.030, depth=0.23, location=(sign * 0.24, 0, 0.86))
        farm.rotation_euler = (0, math.radians(sign * 10), 0)
        farm.data.materials.append(mats["coat_primary"])
        assign_vertex_group(farm, f"forearm.{side}", 1.0)
        parts.append(farm)

        cuff = create_mesh_part(f"Celina_Cuff_{side}", 'CONE', radius1=0.045, radius2=0.032, depth=0.045, location=(sign * 0.26, 0, 0.77))
        cuff.data.materials.append(mats["shirt_ivory"])
        assign_vertex_group(cuff, f"forearm.{side}", 1.0)
        parts.append(cuff)

        palm = create_mesh_part(f"Celina_Palm_{side}", 'CUBE', size=0.030, location=(sign * 0.27, 0.015, 0.72))
        palm.scale = (0.7, 1.0, 1.2)
        palm.data.materials.append(mats["vest_corset"])
        assign_vertex_group(palm, f"hand.{side}", 1.0)
        parts.append(palm)

    # 8. Slender Tapered Legs & Tall Brown Leather Riding Boots (Clear negative space)
    for side, sign in [("L", 1), ("R", -1)]:
        thigh = create_mesh_part(f"Celina_Thigh_{side}", 'CYLINDER', radius=0.038, depth=0.35, location=(sign * 0.080, 0, 0.65))
        thigh.data.materials.append(mats["vest_corset"])
        assign_vertex_group(thigh, f"thigh.{side}", 1.0)
        parts.append(thigh)

        shin = create_mesh_part(f"Celina_Shin_{side}", 'CYLINDER', radius=0.034, depth=0.35, location=(sign * 0.080, 0, 0.30))
        shin.data.materials.append(mats["boots"])
        assign_vertex_group(shin, f"shin.{side}", 1.0)
        parts.append(shin)

        boot = create_mesh_part(f"Celina_Foot_{side}", 'CUBE', size=0.085, location=(sign * 0.080, 0.04, 0.05))
        boot.scale = (0.75, 1.8, 0.85)
        boot.data.materials.append(mats["boots"])
        assign_vertex_group(boot, f"foot.{side}", 1.0)
        parts.append(boot)

    # 9. Golden Cup-Hilt Rapier (Scabbard at hip, Thick 0.012 Blade & Basket attached to Hand, offset for negative space)
    scabbard = create_mesh_part("Celina_Scabbard", 'CYLINDER', radius=0.016, depth=0.75, location=(-0.25, 0.04, 0.60))
    scabbard.rotation_euler = (math.radians(10), math.radians(-38), math.radians(20))
    scabbard.data.materials.append(mats["vest_corset"])
    assign_vertex_group(scabbard, "hips", 1.0)
    parts.append(scabbard)

    blade = create_mesh_part("Celina_RapierBlade", 'CYLINDER', radius=0.012, depth=0.72, location=(-0.26, 0.05, 0.60))
    blade.rotation_euler = (math.radians(10), math.radians(-38), math.radians(20))
    blade.data.materials.append(mats["rapier_steel"])
    assign_vertex_group(blade, "hand.R", 1.0)
    parts.append(blade)

    basket = create_mesh_part("Celina_RapierBasket", 'SPHERE', radius=0.055, location=(-0.20, 0.06, 0.88))
    basket.scale = (1.1, 1.2, 0.9)
    basket.data.materials.append(mats["coat_trim"])
    assign_vertex_group(basket, "hand.R", 1.0)
    parts.append(basket)

    hilt = create_mesh_part("Celina_RapierHilt", 'CYLINDER', radius=0.012, depth=0.14, location=(-0.19, 0.07, 0.96))
    hilt.rotation_euler = (math.radians(10), math.radians(-38), math.radians(20))
    hilt.data.materials.append(mats["gem_ruby"])
    assign_vertex_group(hilt, "hand.R", 1.0)
    parts.append(hilt)

    # Bind all parts to armature
    for p in parts:
        bind_to_armature(p, arm_obj)

    return arm_obj, parts

# -------------------------------------------------------------
# 2. AGNES BUILDER
# -------------------------------------------------------------
def build_agnes() -> tuple:
    """
    Constructs Agnes: Grounded, broad, physical, heavy brawler, 5.0 heads tall (1.20m, ~110px).
    Auburn braided hair with copper bands, thick quilted rust gambeson, asymmetric bronze pauldron on right,
    stout steel-bossed buckler on left forearm, iron spiked mace, heavy dark boots.
    """
    mats = get_agnes_materials()
    arm_obj = create_humanoid_armature(
        name="Agnes_Rig",
        height_scale=0.82,
        shoulder_width=0.26,
        hip_width=0.16,
        head_z=1.18,
        has_coat_bones=False,
        has_hat_bone=False
    )
    parts = []

    # 1. Grounded Head & Sculpted Auburn Hair (Framing face at Z=1.18m)
    head = create_mesh_part("Agnes_Head", 'SPHERE', radius=0.115, location=(0, 0.015, 1.18))
    head.scale = (0.90, 0.92, 1.0)
    head.data.materials.append(mats["skin"])
    assign_vertex_group(head, "head", 1.0)
    parts.append(head)

    chin = create_mesh_part("Agnes_Jaw", 'CUBE', size=0.060, location=(0, 0.055, 1.12))
    chin.scale = (1.1, 0.8, 0.6)
    chin.data.materials.append(mats["skin"])
    assign_vertex_group(chin, "head", 1.0)
    parts.append(chin)

    # Auburn Hair Crown positioned forward covering top of skull & temples
    hair_crown = create_mesh_part("Agnes_HairCrown", 'SPHERE', radius=0.125, location=(0, 0.010, 1.21))
    hair_crown.scale = (0.96, 0.95, 0.95)
    hair_crown.data.materials.append(mats["hair"])
    assign_vertex_group(hair_crown, "head", 1.0)
    parts.append(hair_crown)

    # Thick Auburn Swept Forehead Bangs & Side Locks (Framing eyes and face)
    bang_mid = create_mesh_part("Agnes_BangMid", 'CUBE', size=0.060, location=(0, 0.085, 1.23))
    bang_mid.scale = (1.5, 0.5, 0.6)
    bang_mid.rotation_euler = (math.radians(-18), 0, 0)
    bang_mid.data.materials.append(mats["hair"])
    assign_vertex_group(bang_mid, "head", 1.0)
    parts.append(bang_mid)

    for side, sign in [("L", 1), ("R", -1)]:
        lock = create_mesh_part(f"Agnes_SideLock_{side}", 'CUBE', size=0.042, location=(sign * 0.082, 0.055, 1.17))
        lock.scale = (0.6, 0.5, 1.9)
        lock.rotation_euler = (0, math.radians(sign * -10), math.radians(sign * 15))
        lock.data.materials.append(mats["hair"])
        assign_vertex_group(lock, "head", 1.0)
        parts.append(lock)

    # Thick Auburn Braid (Back) with Copper Bands
    for b_i, b_z in enumerate([1.10, 1.01, 0.92, 0.83]):
        braid_seg = create_mesh_part(f"Agnes_Braid_{b_i}", 'SPHERE', radius=0.044 - b_i * 0.005, location=(0, -0.11, b_z))
        braid_seg.data.materials.append(mats["hair"])
        assign_vertex_group(braid_seg, "head", 1.0)
        parts.append(braid_seg)

        band = create_mesh_part(f"Agnes_CopperBand_{b_i}", 'CYLINDER', radius=0.035 - b_i * 0.004, depth=0.018, location=(0, -0.11, b_z - 0.030))
        band.data.materials.append(mats["copper_trim"])
        assign_vertex_group(band, "head", 1.0)
        parts.append(band)

    # Stylized Eyes with Dark Brows & Hazel Irises
    for side, sign in [("L", 1), ("R", -1)]:
        eye_base = create_mesh_part(f"Agnes_EyeBase_{side}", 'SPHERE', radius=0.024, location=(sign * 0.038, 0.102, 1.185))
        eye_base.scale = (1.1, 0.25, 0.80)
        eye_base.data.materials.append(mats["shirt_linen"])
        assign_vertex_group(eye_base, "head", 1.0)
        parts.append(eye_base)

        iris = create_mesh_part(f"Agnes_Iris_{side}", 'SPHERE', radius=0.016, location=(sign * 0.038, 0.109, 1.185))
        iris.scale = (0.85, 0.2, 0.85)
        iris.data.materials.append(mats["eye_hazel"])
        assign_vertex_group(iris, "head", 1.0)
        parts.append(iris)

        brow = create_mesh_part(f"Agnes_Brow_{side}", 'CUBE', size=0.022, location=(sign * 0.040, 0.108, 1.205))
        brow.scale = (1.8, 0.3, 0.4)
        brow.rotation_euler = (0, math.radians(sign * -10), 0)
        brow.data.materials.append(mats["hair"])
        assign_vertex_group(brow, "head", 1.0)
        parts.append(brow)

    nose = create_mesh_part("Agnes_Nose", 'CONE', radius1=0.016, radius2=0.005, depth=0.035, location=(0, 0.120, 1.168))
    nose.rotation_euler = (math.radians(-25), 0, 0)
    nose.data.materials.append(mats["skin"])
    assign_vertex_group(nose, "head", 1.0)
    parts.append(nose)

    # 2. Broad Rust Quilted Gambeson Torso
    chest = create_mesh_part("Agnes_Chest", 'CYLINDER', radius=0.155, depth=0.22, location=(0, 0, 0.98))
    chest.scale = (1.25, 0.90, 1.0)
    chest.data.materials.append(mats["gambeson_rust"])
    assign_vertex_group(chest, "chest", 1.0)
    parts.append(chest)

    # Heavy Leather Belt & Bronze Buckle
    belt = create_mesh_part("Agnes_Belt", 'CYLINDER', radius=0.145, depth=0.045, location=(0, 0, 0.86))
    belt.data.materials.append(mats["leather_dark"])
    assign_vertex_group(belt, "hips", 1.0)
    parts.append(belt)

    buckle = create_mesh_part("Agnes_Buckle", 'CUBE', size=0.040, location=(0, 0.125, 0.86))
    buckle.scale = (1.2, 0.4, 1.0)
    buckle.data.materials.append(mats["bronze_armor"])
    assign_vertex_group(buckle, "hips", 1.0)
    parts.append(buckle)

    # 3. Asymmetric Bronze Pauldron on Right Shoulder
    pauldron_r = create_mesh_part("Agnes_PauldronR", 'SPHERE', radius=0.095, location=(-0.25, -0.02, 1.05))
    pauldron_r.scale = (1.25, 1.0, 0.85)
    pauldron_r.rotation_euler = (0, math.radians(20), math.radians(-15))
    pauldron_r.data.materials.append(mats["bronze_armor"])
    assign_vertex_group(pauldron_r, "shoulder.R", 1.0)
    parts.append(pauldron_r)

    # 4. Arms, Leather Vambraces, and Reinforced Buckler
    # Left Arm: Heavy Vambrace & Reinforced Round Buckler (Offset for negative space)
    uarm_l = create_mesh_part("Agnes_UpperArm_L", 'CYLINDER', radius=0.045, depth=0.24, location=(0.23, 0, 0.95))
    uarm_l.rotation_euler = (0, math.radians(12), 0)
    uarm_l.data.materials.append(mats["gambeson_rust"])
    assign_vertex_group(uarm_l, "upper_arm.L", 1.0)
    parts.append(uarm_l)

    farm_l = create_mesh_part("Agnes_Forearm_L", 'CYLINDER', radius=0.042, depth=0.23, location=(0.27, 0, 0.76))
    farm_l.rotation_euler = (0, math.radians(15), 0)
    farm_l.data.materials.append(mats["leather_dark"])
    assign_vertex_group(farm_l, "forearm.L", 1.0)
    parts.append(farm_l)

    buckler_rim = create_mesh_part("Agnes_BucklerRim", 'CYLINDER', radius=0.140, depth=0.030, location=(0.34, 0.08, 0.74))
    buckler_rim.rotation_euler = (math.radians(15), math.radians(35), 0)
    buckler_rim.data.materials.append(mats["bronze_armor"])
    assign_vertex_group(buckler_rim, "forearm.L", 1.0)
    parts.append(buckler_rim)

    buckler_boss = create_mesh_part("Agnes_BucklerBoss", 'SPHERE', radius=0.060, location=(0.35, 0.10, 0.74))
    buckler_boss.scale = (1.0, 0.6, 1.0)
    buckler_boss.data.materials.append(mats["iron_metal"])
    assign_vertex_group(buckler_boss, "forearm.L", 1.0)
    parts.append(buckler_boss)

    # Right Arm: Heavy Vambrace & Spiked Iron Mace
    uarm_r = create_mesh_part("Agnes_UpperArm_R", 'CYLINDER', radius=0.045, depth=0.24, location=(-0.23, 0, 0.95))
    uarm_r.rotation_euler = (0, math.radians(-12), 0)
    uarm_r.data.materials.append(mats["gambeson_rust"])
    assign_vertex_group(uarm_r, "upper_arm.R", 1.0)
    parts.append(uarm_r)

    farm_r = create_mesh_part("Agnes_Forearm_R", 'CYLINDER', radius=0.042, depth=0.23, location=(-0.27, 0, 0.76))
    farm_r.rotation_euler = (0, math.radians(-15), 0)
    farm_r.data.materials.append(mats["leather_dark"])
    assign_vertex_group(farm_r, "forearm.R", 1.0)
    parts.append(farm_r)

    mace_handle = create_mesh_part("Agnes_MaceHandle", 'CYLINDER', radius=0.018, depth=0.55, location=(-0.30, 0.05, 0.60))
    mace_handle.rotation_euler = (math.radians(15), math.radians(-25), 0)
    mace_handle.data.materials.append(mats["leather_dark"])
    assign_vertex_group(mace_handle, "hand.R", 1.0)
    parts.append(mace_handle)

    mace_head = create_mesh_part("Agnes_MaceHead", 'SPHERE', radius=0.065, location=(-0.35, 0.08, 0.80))
    mace_head.data.materials.append(mats["iron_metal"])
    assign_vertex_group(mace_head, "hand.R", 1.0)
    parts.append(mace_head)

    # 5. Wide Grounded Stance Legs & Heavy Iron-Toed Boots (Substantial mass supporting broad torso)
    for side, sign in [("L", 1), ("R", -1)]:
        thigh = create_mesh_part(f"Agnes_Thigh_{side}", 'CYLINDER', radius=0.082, depth=0.34, location=(sign * 0.120, 0, 0.62))
        thigh.rotation_euler = (0, math.radians(sign * 8), 0)
        thigh.data.materials.append(mats["gambeson_rust"])
        assign_vertex_group(thigh, f"thigh.{side}", 1.0)
        parts.append(thigh)

        shin = create_mesh_part(f"Agnes_Shin_{side}", 'CYLINDER', radius=0.075, depth=0.34, location=(sign * 0.135, 0, 0.28))
        shin.data.materials.append(mats["leather_dark"])
        assign_vertex_group(shin, f"shin.{side}", 1.0)
        parts.append(shin)

        boot = create_mesh_part(f"Agnes_Boot_{side}", 'CUBE', size=0.130, location=(sign * 0.140, 0.06, 0.06))
        boot.scale = (1.1, 1.85, 0.95)
        boot.data.materials.append(mats["iron_metal"])
        assign_vertex_group(boot, f"foot.{side}", 1.0)
        parts.append(boot)

    for p in parts:
        bind_to_armature(p, arm_obj)

    return arm_obj, parts

# -------------------------------------------------------------
# 3. THE GAMBLER BUILDER
# -------------------------------------------------------------
def build_gambler() -> tuple:
    """
    Constructs The Gambler: Broken diagonals, theatrical, slippery, 5.2 heads tall (1.54m).
    Tilted fedora with violet ribbon, emerald duster coat with open peaked lapels, crimson velvet vest,
    stark white ruffled cuffs, fan of cards, jaunty posture.
    """
    mats = get_gambler_materials()
    arm_obj = create_humanoid_armature(
        name="Gambler_Rig",
        height_scale=0.90,
        shoulder_width=0.22,
        hip_width=0.12,
        head_z=1.35,
        has_coat_bones=True,
        has_hat_bone=True
    )

    parts = []

    # 1. Sculpted Head & Crisp Facial Landmarks (Equalized Eyes, Centered Mustache, Clean Hat Shadow)
    head = create_mesh_part("Gambler_Head", 'SPHERE', radius=0.115, location=(0, 0.015, 1.35))
    head.scale = (0.84, 0.90, 1.02)
    head.data.materials.append(mats["skin"])
    assign_vertex_group(head, "head", 1.0)
    parts.append(head)

    chin = create_mesh_part("Gambler_Chin", 'CONE', radius1=0.048, radius2=0.012, depth=0.055, location=(0, 0.048, 1.28))
    chin.rotation_euler = (math.radians(15), 0, 0)
    chin.data.materials.append(mats["skin"])
    assign_vertex_group(chin, "head", 1.0)
    parts.append(chin)

    # Stylized Clean Eyes with Centered Geometry
    for side, sign in [("L", 1), ("R", -1)]:
        eye_base = create_mesh_part(f"Gambler_EyeBase_{side}", 'SPHERE', radius=0.024, location=(sign * 0.036, 0.105, 1.365))
        eye_base.scale = (1.0, 0.25, 0.80)
        eye_base.data.materials.append(mats["shirt_ivory"])
        assign_vertex_group(eye_base, "head", 1.0)
        parts.append(eye_base)

        iris = create_mesh_part(f"Gambler_Iris_{side}", 'SPHERE', radius=0.016, location=(sign * 0.036, 0.112, 1.365))
        iris.scale = (0.85, 0.2, 0.85)
        iris.data.materials.append(mats["hair"])
        assign_vertex_group(iris, "head", 1.0)
        parts.append(iris)

    mustache = create_mesh_part("Gambler_Mustache", 'CUBE', size=0.022, location=(0, 0.118, 1.325))
    mustache.scale = (1.7, 0.3, 0.4)
    mustache.rotation_euler = (0, 0, 0)
    mustache.data.materials.append(mats["hair"])
    assign_vertex_group(mustache, "head", 1.0)
    parts.append(mustache)

    # 2. Tilted Fedora with Violet Silk Ribbon & Radiant Brass Feather Pin
    hat_crown = create_mesh_part("Gambler_HatCrown", 'CYLINDER', radius=0.118, depth=0.12, location=(0.015, 0.01, 1.47))
    hat_crown.rotation_euler = (math.radians(6), math.radians(12), math.radians(-4))
    hat_crown.data.materials.append(mats["trousers_charcoal"])
    assign_vertex_group(hat_crown, "hat_brim", 1.0)
    parts.append(hat_crown)

    hat_brim = create_mesh_part("Gambler_HatBrim", 'CYLINDER', radius=0.205, depth=0.015, location=(0.015, 0.01, 1.42))
    hat_brim.rotation_euler = (math.radians(6), math.radians(12), math.radians(-4))
    hat_brim.data.materials.append(mats["trousers_charcoal"])
    assign_vertex_group(hat_brim, "hat_brim", 1.0)
    parts.append(hat_brim)

    hat_ribbon = create_mesh_part("Gambler_HatRibbon", 'TORUS', major_radius=0.120, minor_radius=0.014, location=(0.015, 0.01, 1.44))
    hat_ribbon.rotation_euler = (math.radians(6), math.radians(12), math.radians(-4))
    hat_ribbon.data.materials.append(mats["ribbon_violet"])
    assign_vertex_group(hat_ribbon, "hat_brim", 1.0)
    parts.append(hat_ribbon)

    feather = create_mesh_part("Gambler_Feather", 'CONE', radius1=0.016, radius2=0.005, depth=0.17, location=(0.11, 0.04, 1.50))
    feather.rotation_euler = (math.radians(-20), math.radians(35), math.radians(-25))
    feather.data.materials.append(mats["brass_trim"])
    assign_vertex_group(feather, "hat_brim", 1.0)
    parts.append(feather)

    # 3. Crimson Velvet Waistcoat & Gold Buckled Belt (Broader torso mass)
    torso_upper = create_mesh_part("Gambler_Chest", 'CYLINDER', radius=0.140, depth=0.24, location=(0, 0, 1.13))
    torso_upper.scale = (1.10, 0.85, 1.0)
    torso_upper.data.materials.append(mats["vest_crimson"])
    assign_vertex_group(torso_upper, "chest", 1.0)
    parts.append(torso_upper)

    shirt_cravat = create_mesh_part("Gambler_ShirtCravat", 'CUBE', size=0.060, location=(0, 0.08, 1.17))
    shirt_cravat.scale = (1.3, 0.4, 1.4)
    shirt_cravat.data.materials.append(mats["shirt_ivory"])
    assign_vertex_group(shirt_cravat, "chest", 1.0)
    parts.append(shirt_cravat)

    # Brass Vest Buttons
    for b_idx, b_z in enumerate([1.14, 1.09, 1.04]):
        btn = create_mesh_part(f"Gambler_Btn_{b_idx}", 'SPHERE', radius=0.011, location=(0, 0.096, b_z))
        btn.data.materials.append(mats["brass_trim"])
        assign_vertex_group(btn, "chest", 1.0)
        parts.append(btn)

    # Gold Buckled Leather Belt (Unifies torso-to-pelvis transition)
    belt = create_mesh_part("Gambler_Belt", 'CYLINDER', radius=0.132, depth=0.035, location=(0, 0, 1.00))
    belt.data.materials.append(mats["boots_leather"])
    assign_vertex_group(belt, "pelvis", 1.0)
    parts.append(belt)

    buckle = create_mesh_part("Gambler_Buckle", 'CUBE', size=0.032, location=(0, 0.105, 1.00))
    buckle.scale = (1.2, 0.4, 0.9)
    buckle.data.materials.append(mats["brass_trim"])
    assign_vertex_group(buckle, "pelvis", 1.0)
    parts.append(buckle)

    # 4. Asymmetric Open-Split Emerald Duster (Flared Showman Hem with Clean Trouser Negative Space)
    lapel_l = create_mesh_part("Gambler_Lapel_L", 'CUBE', size=0.080, location=(0.10, 0.08, 1.11))
    lapel_l.scale = (0.7, 0.3, 2.4)
    lapel_l.rotation_euler = (0, math.radians(-16), math.radians(10))
    lapel_l.data.materials.append(mats["duster_emerald"])
    assign_vertex_group(lapel_l, "chest", 1.0)
    parts.append(lapel_l)

    lapel_r = create_mesh_part("Gambler_Lapel_R", 'CUBE', size=0.085, location=(-0.11, 0.09, 1.11))
    lapel_r.scale = (0.8, 0.3, 2.6)
    lapel_r.rotation_euler = (math.radians(5), math.radians(20), math.radians(-15))
    lapel_r.data.materials.append(mats["duster_emerald"])
    assign_vertex_group(lapel_r, "chest", 1.0)
    parts.append(lapel_r)

    # Flared Duster Panels (Swept outward to sides, leaving open front showing trousers & spats)
    tail_l = create_mesh_part("Gambler_Tail_L", 'CYLINDER', radius=0.085, depth=0.55, location=(0.14, -0.05, 0.62))
    tail_l.scale = (0.85, 0.60, 1.0)
    tail_l.rotation_euler = (math.radians(8), math.radians(22), math.radians(-10))
    tail_l.data.materials.append(mats["duster_emerald"])
    assign_vertex_group(tail_l, "coat_L.01", 0.7)
    assign_vertex_group(tail_l, "coat_L.02", 0.3)
    parts.append(tail_l)

    tail_r = create_mesh_part("Gambler_Tail_R", 'CYLINDER', radius=0.095, depth=0.58, location=(-0.16, -0.06, 0.60))
    tail_r.scale = (1.0, 0.65, 1.0)
    tail_r.rotation_euler = (math.radians(14), math.radians(-30), math.radians(18))
    tail_r.data.materials.append(mats["duster_emerald"])
    assign_vertex_group(tail_r, "coat_R.01", 0.6)
    assign_vertex_group(tail_r, "coat_R.02", 0.4)
    parts.append(tail_r)

    # 5. Arms, Flared Cuffs & Unmistakable Giant Playing Cards
    for side, sign in [("L", 1), ("R", -1)]:
        uarm = create_mesh_part(f"Gambler_UpperArm_{side}", 'CYLINDER', radius=0.040, depth=0.24, location=(sign * 0.20, 0, 1.05))
        uarm.rotation_euler = (0, math.radians(sign * 10), 0)
        uarm.data.materials.append(mats["duster_emerald"])
        assign_vertex_group(uarm, f"upper_arm.{side}", 1.0)
        parts.append(uarm)

        farm = create_mesh_part(f"Gambler_Forearm_{side}", 'CYLINDER', radius=0.035, depth=0.23, location=(sign * 0.23, 0, 0.84))
        farm.rotation_euler = (0, math.radians(sign * 12), 0)
        farm.data.materials.append(mats["duster_emerald"])
        assign_vertex_group(farm, f"forearm.{side}", 1.0)
        parts.append(farm)

        cuff = create_mesh_part(f"Gambler_Cuff_{side}", 'CONE', radius1=0.055, radius2=0.038, depth=0.048, location=(sign * 0.25, 0, 0.75))
        cuff.data.materials.append(mats["shirt_ivory"])
        assign_vertex_group(cuff, f"forearm.{side}", 1.0)
        parts.append(cuff)

        hand = create_mesh_part(f"Gambler_Hand_{side}", 'CUBE', size=0.035, location=(sign * 0.26, 0.02, 0.69))
        hand.scale = (0.7, 1.0, 1.2)
        hand.data.materials.append(mats["skin"])
        assign_vertex_group(hand, f"hand.{side}", 1.0)
        parts.append(hand)

    # Conspicuous High-Contrast Fan of 3 Giant Cards in Right Hand (0.110m width)
    for c_i, c_angle in enumerate([-26, 0, 26]):
        card = create_mesh_part(f"Gambler_Card_{c_i}", 'CUBE', size=0.110, location=(-0.30, 0.11, 0.76))
        card.scale = (1.5, 0.08, 1.1)
        card.rotation_euler = (math.radians(25), math.radians(-32 + c_angle), math.radians(45))
        card.data.materials.append(mats["card_white"] if c_i % 2 == 0 else mats["card_red"])
        assign_vertex_group(card, "hand.R", 1.0)
        parts.append(card)

    # 6. Slender Charcoal Trousers & Polished Ivory Spat Boots (Firm grounded stance)
    for side, sign in [("L", 1), ("R", -1)]:
        thigh = create_mesh_part(f"Gambler_Thigh_{side}", 'CYLINDER', radius=0.046, depth=0.35, location=(sign * 0.080, 0, 0.64))
        thigh.data.materials.append(mats["trousers_charcoal"])
        assign_vertex_group(thigh, f"thigh.{side}", 1.0)
        parts.append(thigh)

        shin = create_mesh_part(f"Gambler_Shin_{side}", 'CYLINDER', radius=0.040, depth=0.35, location=(sign * 0.080, 0, 0.29))
        shin.data.materials.append(mats["trousers_charcoal"])
        assign_vertex_group(shin, f"shin.{side}", 1.0)
        parts.append(shin)

        # Ivory Spat over Boot
        spat = create_mesh_part(f"Gambler_Spat_{side}", 'CONE', radius1=0.052, radius2=0.042, depth=0.10, location=(sign * 0.080, 0.02, 0.15))
        spat.data.materials.append(mats["spats_ivory"])
        assign_vertex_group(spat, f"shin.{side}", 1.0)
        parts.append(spat)

        boot = create_mesh_part(f"Gambler_Boot_{side}", 'CUBE', size=0.090, location=(sign * 0.080, 0.05, 0.05))
        boot.scale = (0.80, 1.8, 0.85)
        boot.data.materials.append(mats["boots_leather"])
        assign_vertex_group(boot, f"foot.{side}", 1.0)
        parts.append(boot)

    for p in parts:
        bind_to_armature(p, arm_obj)

    return arm_obj, parts
