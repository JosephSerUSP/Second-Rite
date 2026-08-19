# gauntlet/pipeline/mesh_generator.py
# Procedural 3D Mesh Generator for Celina, Agnes, and The Gambler in Blender
# Corrected front-facing orientation: Camera is at (0, -4.0, Z), so FRONT of character is on -Y side.

import os
import tempfile
import bpy
import bmesh
import math
from mathutils import Vector, Matrix
from gauntlet.pipeline.materials import get_celina_materials, get_agnes_materials, get_gambler_materials, create_textured_material
from gauntlet.pipeline.texture_builder import create_celina_face_image
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

# =============================================================
# 1. CELINA BUILDER (Slender Duelist)
# =============================================================
def build_celina() -> tuple:
    """
    Constructs Celina: Vertical, contained, deliberate, 5.5 heads tall (1.48m).
    Slender elongated silhouette (~118-120px standing height, strictly <= 128px).
    High asymmetrical collar, sharp gold epaulets, narrow hourglass obsidian corset,
    flared split coat tails, elegant duelist rapier with ornate cup hilt.
    Front faces -Y toward camera.
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

    # 1. Neck connecting head cleanly to torso
    neck = create_mesh_part("Celina_Neck", 'CYLINDER', radius=0.040, depth=0.09, location=(0, -0.005, 1.15))
    neck.data.materials.append(mats["skin"])
    assign_vertex_group(neck, "neck", 1.0)
    parts.append(neck)

    # Stylized Textured Head Sphere (23px height at native scale)
    face_img_path = os.path.join(tempfile.gettempdir(), "celina_face_tex.png")
    face_img = create_celina_face_image()
    face_img.filepath_raw = face_img_path
    face_img.file_format = 'PNG'
    face_img.save()
    
    loaded_img = bpy.data.images.load(face_img_path, check_existing=False)
    face_mat = create_textured_material("Celina_FaceTex", loaded_img)

    head = create_mesh_part("Celina_Head", 'SPHERE', radius=0.125, location=(0, -0.010, 1.275))
    head.scale = (0.80, 0.84, 1.0)
    head.rotation_euler = (0, 0, math.radians(-90)) # Align texture center with -Y front camera
    head.data.materials.append(face_mat)
    assign_vertex_group(head, "head", 1.0)
    parts.append(head)

    # 2. Rich 3D Raven Hair Volumes (Crown, Back Volume, Swept Bangs, Cascading Side Locks, High Bun & Gold Hairpin)
    # Crown & Back Hair Dome (Full 3D hair covering top, back, and sides)
    hair_crown = create_mesh_part("Celina_HairCrown", 'SPHERE', radius=0.145, location=(0, 0.035, 1.305))
    hair_crown.scale = (0.95, 0.90, 1.02)
    hair_crown.data.materials.append(mats["hair"])
    assign_vertex_group(hair_crown, "head", 1.0)
    parts.append(hair_crown)

    # Back Hair Drape (Falling over the nape of the neck)
    hair_back = create_mesh_part("Celina_HairBack", 'CONE', radius1=0.120, radius2=0.060, depth=0.18, location=(0, 0.065, 1.20))
    hair_back.rotation_euler = (math.radians(-15), 0, 0)
    hair_back.data.materials.append(mats["hair"])
    assign_vertex_group(hair_back, "head", 1.0)
    parts.append(hair_back)

    # Swept Bangs (Short 3D Forehead Fringe above eyebrows)
    for bx, bang_x in enumerate([-0.055, -0.018, 0.018, 0.055]):
        bang = create_mesh_part(f"Celina_Bang_{bx}", 'CONE', radius1=0.020, radius2=0.004, depth=0.06, location=(bang_x, -0.088, 1.365))
        bang.rotation_euler = (math.radians(-25), math.radians(bx * 5 - 8), 0)
        bang.data.materials.append(mats["hair"])
        assign_vertex_group(bang, "head", 1.0)
        parts.append(bang)

    # Cascading Side Locks framing the cheeks and jaw
    for side, sign in [("L", 1), ("R", -1)]:
        sidelock = create_mesh_part(f"Celina_SideLock_{side}", 'CONE', radius1=0.038, radius2=0.010, depth=0.28, location=(sign * 0.095, -0.045, 1.16))
        sidelock.rotation_euler = (math.radians(12), math.radians(sign * 12), 0)
        sidelock.data.materials.append(mats["hair"])
        assign_vertex_group(sidelock, "head", 1.0)
        parts.append(sidelock)

        earring = create_mesh_part(f"Celina_Earring_{side}", 'SPHERE', radius=0.014, location=(sign * 0.108, -0.015, 1.24))
        earring.data.materials.append(mats["coat_trim"])
        assign_vertex_group(earring, "head", 1.0)
        parts.append(earring)

    # High Chignon Hair Bun with Gold Hairpin & Radiant Ruby Gem
    hair_bun = create_mesh_part("Celina_HairBun", 'SPHERE', radius=0.095, location=(0, 0.135, 1.33))
    hair_bun.data.materials.append(mats["hair"])
    assign_vertex_group(hair_bun, "head", 1.0)
    parts.append(hair_bun)

    hair_pin = create_mesh_part("Celina_HairPin", 'CYLINDER', radius=0.009, depth=0.30, location=(0, 0.135, 1.33))
    hair_pin.rotation_euler = (0, math.radians(65), 0)
    hair_pin.data.materials.append(mats["coat_trim"])
    assign_vertex_group(hair_pin, "head", 1.0)
    parts.append(hair_pin)

    hair_gem = create_mesh_part("Celina_HairGem", 'SPHERE', radius=0.016, location=(0.14, 0.135, 1.33))
    hair_gem.data.materials.append(mats["gem_ruby"])
    assign_vertex_group(hair_gem, "head", 1.0)
    parts.append(hair_gem)

    # 3. Flared High Winged Victorian Collar & Cravat (Pure White with Gold Outer Trim)
    # Winged Collar (Flared trapezoid shape framing the neck)
    collar = create_mesh_part("Celina_HighCollar", 'CONE', radius1=0.095, radius2=0.052, depth=0.10, location=(0, 0.015, 1.10))
    collar.scale = (1.08, 0.85, 1.0)
    collar.data.materials.append(mats["shirt_ivory"]) # Crisp pure white collar
    assign_vertex_group(collar, "chest", 1.0)
    parts.append(collar)

    collar_trim = create_mesh_part("Celina_CollarTrim", 'TORUS', major_radius=0.095, minor_radius=0.008, location=(0, 0.015, 1.15))
    collar_trim.scale = (1.08, 0.85, 1.0)
    collar_trim.data.materials.append(mats["coat_trim"])
    assign_vertex_group(collar_trim, "chest", 1.0)
    parts.append(collar_trim)

    # Layered Cravat & Radiant Ruby Brooch
    cravat = create_mesh_part("Celina_Cravat", 'CONE', radius1=0.042, radius2=0.016, depth=0.12, location=(0, -0.050, 1.05))
    cravat.rotation_euler = (math.radians(22), 0, 0)
    cravat.data.materials.append(mats["shirt_ivory"])
    assign_vertex_group(cravat, "chest", 1.0)
    parts.append(cravat)

    brooch = create_mesh_part("Celina_RubyBrooch", 'SPHERE', radius=0.016, location=(0, -0.065, 1.09))
    brooch.data.materials.append(mats["gem_ruby"])
    assign_vertex_group(brooch, "chest", 1.0)
    parts.append(brooch)

    # 4. Tailored Frock Coat Chest (Hourglass Fencing Silhouette)
    chest = create_mesh_part("Celina_Chest", 'CYLINDER', radius=0.098, depth=0.18, location=(0, -0.01, 1.02))
    chest.scale = (1.18, 0.76, 1.0) # Broad tailored shoulders
    chest.data.materials.append(mats["coat_primary"])
    assign_vertex_group(chest, "chest", 1.0)
    parts.append(chest)

    # 5. Obsidian Velvet Corset with Gold Lacing (Pinched Waist)
    corset = create_mesh_part("Celina_Corset", 'CYLINDER', radius=0.070, depth=0.16, location=(0, -0.005, 0.89))
    corset.scale = (0.88, 0.70, 1.0) # Pinched waist taper
    corset.data.materials.append(mats["vest_corset"])
    assign_vertex_group(corset, "chest", 0.5)
    assign_vertex_group(corset, "hips", 0.5)
    parts.append(corset)

    # Gold Lacing & Buttons on Corset
    for i in range(4):
        z_pos = 0.83 + i * 0.036
        lace = create_mesh_part(f"Celina_Lace_{i}", 'CUBE', size=0.016, location=(0, -0.065, z_pos))
        lace.scale = (1.4, 0.25, 0.25)
        lace.data.materials.append(mats["coat_trim"])
        assign_vertex_group(lace, "chest", 0.5)
        assign_vertex_group(lace, "hips", 0.5)
        parts.append(lace)

    # Gold Belt & Buckle at Waist-Hip Transition
    belt = create_mesh_part("Celina_Belt", 'TORUS', major_radius=0.086, minor_radius=0.012, location=(0, 0, 0.80))
    belt.scale = (0.98, 0.76, 0.8)
    belt.data.materials.append(mats["coat_trim"])
    assign_vertex_group(belt, "hips", 1.0)
    parts.append(belt)

    buckle = create_mesh_part("Celina_Buckle", 'SPHERE', radius=0.018, location=(0, -0.078, 0.80))
    buckle.data.materials.append(mats["gem_ruby"])
    assign_vertex_group(buckle, "hips", 1.0)
    parts.append(buckle)

    # Pelvis & Flared Frock Coat Tails (Curvaceous Aristocratic Duelist Silhouette)
    hips = create_mesh_part("Celina_Hips", 'CYLINDER', radius=0.095, depth=0.14, location=(0, 0, 0.73))
    hips.scale = (1.10, 0.80, 1.0)
    hips.data.materials.append(mats["coat_primary"])
    assign_vertex_group(hips, "hips", 1.0)
    parts.append(hips)

    # Flared Split Coat Tails (Left, Right, Back) with Prominent Gold Hem Bands
    # Left Tail
    coat_l = create_mesh_part("Celina_CoatTail_L", 'CONE', radius1=0.060, radius2=0.032, depth=0.40, location=(0.125, 0.02, 0.54))
    coat_l.rotation_euler = (math.radians(6), math.radians(16), 0)
    coat_l.scale = (0.80, 1.10, 1.0)
    coat_l.data.materials.append(mats["coat_primary"])
    assign_vertex_group(coat_l, "coat_tail.L", 1.0)
    parts.append(coat_l)

    coat_hem_l = create_mesh_part("Celina_CoatHem_L", 'TORUS', major_radius=0.062, minor_radius=0.010, location=(0.155, 0.03, 0.35))
    coat_hem_l.rotation_euler = (math.radians(6), math.radians(16), 0)
    coat_hem_l.data.materials.append(mats["coat_trim"])
    assign_vertex_group(coat_hem_l, "coat_tail.L", 1.0)
    parts.append(coat_hem_l)

    # Right Tail
    coat_r = create_mesh_part("Celina_CoatTail_R", 'CONE', radius1=0.060, radius2=0.032, depth=0.40, location=(-0.125, 0.02, 0.54))
    coat_r.rotation_euler = (math.radians(6), math.radians(-16), 0)
    coat_r.scale = (0.80, 1.10, 1.0)
    coat_r.data.materials.append(mats["coat_primary"])
    assign_vertex_group(coat_r, "coat_tail.R", 1.0)
    parts.append(coat_r)

    coat_hem_r = create_mesh_part("Celina_CoatHem_R", 'TORUS', major_radius=0.062, minor_radius=0.010, location=(-0.155, 0.03, 0.35))
    coat_hem_r.rotation_euler = (math.radians(6), math.radians(-16), 0)
    coat_hem_r.data.materials.append(mats["coat_trim"])
    assign_vertex_group(coat_hem_r, "coat_tail.R", 1.0)
    parts.append(coat_hem_r)

    # Back Tail
    coat_back = create_mesh_part("Celina_CoatTail_Back", 'CONE', radius1=0.070, radius2=0.038, depth=0.42, location=(0, 0.080, 0.53))
    coat_back.rotation_euler = (math.radians(-14), 0, 0)
    coat_back.scale = (1.10, 0.75, 1.0)
    coat_back.data.materials.append(mats["coat_primary"])
    assign_vertex_group(coat_back, "hips", 1.0)
    parts.append(coat_back)

    coat_hem_back = create_mesh_part("Celina_CoatHem_Back", 'TORUS', major_radius=0.072, minor_radius=0.010, location=(0, 0.125, 0.33))
    coat_hem_back.rotation_euler = (math.radians(-14), 0, 0)
    coat_hem_back.scale = (1.10, 0.75, 1.0)
    coat_hem_back.data.materials.append(mats["coat_trim"])
    assign_vertex_group(coat_hem_back, "hips", 1.0)
    parts.append(coat_hem_back)

    # 6. Iconic Asymmetrical Duelist Fencing Arms
    # Left Arm (Tucked Gracefully Behind Small of the Back)
    epaulet_l = create_mesh_part("Celina_Epaulet_L", 'SPHERE', radius=0.045, location=(0.150, -0.01, 1.14))
    epaulet_l.scale = (1.35, 1.0, 0.60)
    epaulet_l.data.materials.append(mats["coat_trim"])
    assign_vertex_group(epaulet_l, "upper_arm.L", 1.0)
    parts.append(epaulet_l)

    uarm_l = create_mesh_part("Celina_UpperArm_L", 'CYLINDER', radius=0.034, depth=0.22, location=(0.140, 0.04, 1.00))
    uarm_l.rotation_euler = (math.radians(-18), math.radians(12), math.radians(16))
    uarm_l.data.materials.append(mats["coat_primary"])
    assign_vertex_group(uarm_l, "upper_arm.L", 1.0)
    parts.append(uarm_l)

    farm_l = create_mesh_part("Celina_Forearm_L", 'CYLINDER', radius=0.030, depth=0.20, location=(0.080, 0.08, 0.84))
    farm_l.rotation_euler = (math.radians(-50), 0, math.radians(-55))
    farm_l.data.materials.append(mats["coat_primary"])
    assign_vertex_group(farm_l, "forearm.L", 1.0)
    parts.append(farm_l)

    cuff_l = create_mesh_part("Celina_Cuff_L", 'TORUS', major_radius=0.032, minor_radius=0.008, location=(0.020, 0.08, 0.80))
    cuff_l.rotation_euler = (math.radians(-50), 0, math.radians(-55))
    cuff_l.data.materials.append(mats["shirt_ivory"])
    assign_vertex_group(cuff_l, "hand.L", 1.0)
    parts.append(cuff_l)

    hand_l = create_mesh_part("Celina_Hand_L", 'SPHERE', radius=0.030, location=(0.010, 0.08, 0.80))
    hand_l.data.materials.append(mats["shirt_ivory"]) # White duelist gloves
    assign_vertex_group(hand_l, "hand.L", 1.0)
    parts.append(hand_l)

    # Right Arm (Poised Sword Arm Gripping Golden Rapier Cup Hilt with Clear Negative Space Separation)
    epaulet_r = create_mesh_part("Celina_Epaulet_R", 'SPHERE', radius=0.045, location=(-0.150, -0.01, 1.14))
    epaulet_r.scale = (1.35, 1.0, 0.60)
    epaulet_r.data.materials.append(mats["coat_trim"])
    assign_vertex_group(epaulet_r, "upper_arm.R", 1.0)
    parts.append(epaulet_r)

    uarm_r = create_mesh_part("Celina_UpperArm_R", 'CYLINDER', radius=0.034, depth=0.22, location=(-0.185, -0.02, 1.00))
    uarm_r.rotation_euler = (math.radians(18), math.radians(-16), math.radians(-22))
    uarm_r.data.materials.append(mats["coat_primary"])
    assign_vertex_group(uarm_r, "upper_arm.R", 1.0)
    parts.append(uarm_r)

    farm_r = create_mesh_part("Celina_Forearm_R", 'CYLINDER', radius=0.030, depth=0.20, location=(-0.210, -0.05, 0.80))
    farm_r.rotation_euler = (math.radians(35), 0, math.radians(20))
    farm_r.data.materials.append(mats["coat_primary"])
    assign_vertex_group(farm_r, "forearm.R", 1.0)
    parts.append(farm_r)

    cuff_r = create_mesh_part("Celina_Cuff_R", 'TORUS', major_radius=0.032, minor_radius=0.008, location=(-0.215, -0.06, 0.70))
    cuff_r.rotation_euler = (math.radians(35), 0, math.radians(20))
    cuff_r.data.materials.append(mats["shirt_ivory"])
    assign_vertex_group(cuff_r, "hand.R", 1.0)
    parts.append(cuff_r)

    hand_r = create_mesh_part("Celina_Hand_R", 'SPHERE', radius=0.032, location=(-0.215, -0.06, 0.68))
    hand_r.data.materials.append(mats["shirt_ivory"]) # White duelist gloves
    assign_vertex_group(hand_r, "hand.R", 1.0)
    parts.append(hand_r)

    # 7. Planted Fencing Stance: White Fencing Breeches & Saddle Leather Riding Boots with Thick Ivory Soles
    # Right Leg (Forward-planted straight fencing leg)
    uleg_r = create_mesh_part("Celina_UpperLeg_R", 'CYLINDER', radius=0.048, depth=0.34, location=(-0.065, 0.01, 0.63))
    uleg_r.data.materials.append(mats["trousers"]) # White fencing breeches
    assign_vertex_group(uleg_r, "upper_leg.R", 1.0)
    parts.append(uleg_r)

    boot_r = create_mesh_part("Celina_Boot_R", 'CYLINDER', radius=0.046, depth=0.36, location=(-0.065, 0.00, 0.28))
    boot_r.data.materials.append(mats["boots"]) # Saddle leather
    assign_vertex_group(boot_r, "lower_leg.R", 1.0)
    parts.append(boot_r)

    boot_trim_r = create_mesh_part("Celina_BootTrim_R", 'TORUS', major_radius=0.050, minor_radius=0.010, location=(-0.065, 0.00, 0.44))
    boot_trim_r.data.materials.append(mats["coat_trim"])
    assign_vertex_group(boot_trim_r, "lower_leg.R", 1.0)
    parts.append(boot_trim_r)

    foot_r = create_mesh_part("Celina_Foot_R", 'CUBE', size=0.065, location=(-0.065, -0.045, 0.055))
    foot_r.scale = (1.05, 1.75, 0.70)
    foot_r.data.materials.append(mats["boots"])
    assign_vertex_group(foot_r, "foot.R", 1.0)
    parts.append(foot_r)

    sole_r = create_mesh_part("Celina_Sole_R", 'CUBE', size=0.065, location=(-0.065, -0.045, 0.015))
    sole_r.scale = (1.12, 1.80, 0.22)
    sole_r.data.materials.append(mats["boot_sole"])
    assign_vertex_group(sole_r, "foot.R", 1.0)
    parts.append(sole_r)

    # Left Leg (Back-angled support leg turned 24 degrees outward)
    uleg_l = create_mesh_part("Celina_UpperLeg_L", 'CYLINDER', radius=0.048, depth=0.34, location=(0.085, -0.01, 0.63))
    uleg_l.rotation_euler = (0, 0, math.radians(20))
    uleg_l.data.materials.append(mats["trousers"])
    assign_vertex_group(uleg_l, "upper_leg.L", 1.0)
    parts.append(uleg_l)

    boot_l = create_mesh_part("Celina_Boot_L", 'CYLINDER', radius=0.046, depth=0.36, location=(0.085, -0.02, 0.28))
    boot_l.rotation_euler = (0, 0, math.radians(20))
    boot_l.data.materials.append(mats["boots"])
    assign_vertex_group(boot_l, "lower_leg.L", 1.0)
    parts.append(boot_l)

    boot_trim_l = create_mesh_part("Celina_BootTrim_L", 'TORUS', major_radius=0.050, minor_radius=0.010, location=(0.085, -0.02, 0.44))
    boot_trim_l.rotation_euler = (0, 0, math.radians(20))
    boot_trim_l.data.materials.append(mats["coat_trim"])
    assign_vertex_group(boot_trim_l, "lower_leg.L", 1.0)
    parts.append(boot_trim_l)

    foot_l = create_mesh_part("Celina_Foot_L", 'CUBE', size=0.065, location=(0.085, -0.065, 0.055))
    foot_l.scale = (1.05, 1.75, 0.70)
    foot_l.rotation_euler = (0, 0, math.radians(20))
    foot_l.data.materials.append(mats["boots"])
    assign_vertex_group(foot_l, "foot.L", 1.0)
    parts.append(foot_l)

    sole_l = create_mesh_part("Celina_Sole_L", 'CUBE', size=0.065, location=(0.085, -0.065, 0.015))
    sole_l.scale = (1.12, 1.80, 0.22)
    sole_l.rotation_euler = (0, 0, math.radians(20))
    sole_l.data.materials.append(mats["boot_sole"])
    assign_vertex_group(sole_l, "foot.L", 1.0)
    parts.append(sole_l)

    # 8. Slender Rapier with Ornate Golden Cup Guard & Thick Polished Steel Blade
    # Prominent Golden Cup Guard at Right Flank
    rapier_guard = create_mesh_part("Celina_RapierGuard", 'SPHERE', radius=0.085, location=(-0.215, -0.06, 0.66))
    rapier_guard.scale = (1.05, 0.75, 1.05)
    rapier_guard.data.materials.append(mats["coat_trim"])
    assign_vertex_group(rapier_guard, "hand.R", 1.0)
    parts.append(rapier_guard)

    # Golden Cross Quillons
    rapier_quillons = create_mesh_part("Celina_RapierQuillons", 'CYLINDER', radius=0.015, depth=0.24, location=(-0.215, -0.06, 0.66))
    rapier_quillons.rotation_euler = (math.radians(90), 0, math.radians(45))
    rapier_quillons.data.materials.append(mats["coat_trim"])
    assign_vertex_group(rapier_quillons, "hand.R", 1.0)
    parts.append(rapier_quillons)

    # Thick Polished Steel Rapier Blade (aligned directly along bone Z axis pointing down)
    rapier_blade = create_mesh_part("Celina_RapierBlade", 'CYLINDER', radius=0.022, depth=0.94, location=(-0.215, -0.06, 0.19))
    rapier_blade.data.materials.append(mats["rapier_steel"])
    assign_vertex_group(rapier_blade, "hand.R", 1.0)
    parts.append(rapier_blade)

    for p in parts:
        bind_to_armature(p, arm_obj)

    return arm_obj, parts

# =============================================================
# 2. AGNES BUILDER (Grounded Heavy Fighter)
# =============================================================
def build_agnes() -> tuple:
    """
    Constructs Agnes: Grounded, broad, physical, 5.0 heads tall (1.38m).
    Solid center of gravity, broad shoulders, massive left bronze horned pauldron,
    quilted rust gambeson, heavy vambraces, circular iron buckler.
    Front faces -Y toward camera.
    """
    mats = get_agnes_materials()
    arm_obj = create_humanoid_armature(
        name="Agnes_Rig",
        height_scale=0.86,
        shoulder_width=0.24,
        hip_width=0.14,
        head_z=1.28,
        has_coat_bones=False,
        has_hat_bone=False,
        has_shield_bone=True
    )

    parts = []

    # 1. Broad Head & Strong Sculpted Jaw (Front is -Y)
    head = create_mesh_part("Agnes_Head", 'SPHERE', radius=0.125, location=(0, -0.015, 1.28))
    head.scale = (0.95, 0.95, 0.95)
    head.data.materials.append(mats["skin"])
    assign_vertex_group(head, "head", 1.0)
    parts.append(head)

    jaw = create_mesh_part("Agnes_Jaw", 'CUBE', size=0.085, location=(0, -0.05, 1.22))
    jaw.scale = (1.25, 0.8, 0.5)
    jaw.data.materials.append(mats["skin"])
    assign_vertex_group(jaw, "head", 1.0)
    parts.append(jaw)

    # Expressive Determined Eyes & Thick Brow (Front -Y)
    for side, sign in [("L", 1), ("R", -1)]:
        eye_base = create_mesh_part(f"Agnes_EyeBase_{side}", 'SPHERE', radius=0.024, location=(sign * 0.042, -0.110, 1.29))
        eye_base.scale = (1.0, 0.25, 0.75)
        eye_base.data.materials.append(mats["shirt_linen"])
        assign_vertex_group(eye_base, "head", 1.0)
        parts.append(eye_base)

        iris = create_mesh_part(f"Agnes_Iris_{side}", 'SPHERE', radius=0.016, location=(sign * 0.042, -0.117, 1.29))
        iris.scale = (0.85, 0.2, 0.85)
        iris.data.materials.append(mats["eye_green"])
        assign_vertex_group(iris, "head", 1.0)
        parts.append(iris)

        brow = create_mesh_part(f"Agnes_Brow_{side}", 'CUBE', size=0.024, location=(sign * 0.044, -0.113, 1.315))
        brow.scale = (1.8, 0.35, 0.4)
        brow.rotation_euler = (0, math.radians(sign * 8), 0)
        brow.data.materials.append(mats["hair"])
        assign_vertex_group(brow, "head", 1.0)
        parts.append(brow)

    nose = create_mesh_part("Agnes_Nose", 'CONE', radius1=0.022, radius2=0.008, depth=0.042, location=(0, -0.124, 1.27))
    nose.rotation_euler = (math.radians(20), 0, 0)
    nose.data.materials.append(mats["skin"])
    assign_vertex_group(nose, "head", 1.0)
    parts.append(nose)

    # 2. Fiery Auburn Braided Hair
    hair_crown = create_mesh_part("Agnes_HairCrown", 'SPHERE', radius=0.130, location=(0, 0.04, 1.30))
    hair_crown.scale = (1.05, 0.85, 0.95)
    hair_crown.data.materials.append(mats["hair"])
    assign_vertex_group(hair_crown, "head", 1.0)
    parts.append(hair_crown)

    braid = create_mesh_part("Agnes_Braid", 'CYLINDER', radius=0.040, depth=0.32, location=(0.14, -0.04, 1.15))
    braid.rotation_euler = (math.radians(-20), math.radians(-15), 0)
    braid.data.materials.append(mats["hair"])
    assign_vertex_group(braid, "head", 1.0)
    parts.append(braid)

    # 3. Heavy Quilted Gambeson Torso & Strapping
    neck = create_mesh_part("Agnes_Neck", 'CYLINDER', radius=0.055, depth=0.10, location=(0, -0.01, 1.17))
    neck.data.materials.append(mats["skin"])
    assign_vertex_group(neck, "neck", 1.0)
    parts.append(neck)

    chest = create_mesh_part("Agnes_Chest", 'CYLINDER', radius=0.150, depth=0.22, location=(0, 0, 1.04))
    chest.scale = (1.25, 0.85, 1.0)
    chest.data.materials.append(mats["gambeson_rust"])
    assign_vertex_group(chest, "chest", 1.0)
    parts.append(chest)

    strap = create_mesh_part("Agnes_ChestStrap", 'CUBE', size=0.030, location=(0, -0.11, 1.04))
    strap.scale = (4.8, 0.2, 0.5)
    strap.rotation_euler = (0, 0, math.radians(35))
    strap.data.materials.append(mats["leather_dark"])
    assign_vertex_group(strap, "chest", 1.0)
    parts.append(strap)

    waist = create_mesh_part("Agnes_Waist", 'CYLINDER', radius=0.138, depth=0.18, location=(0, 0, 0.88))
    waist.scale = (1.20, 0.85, 1.0)
    waist.data.materials.append(mats["gambeson_rust"])
    assign_vertex_group(waist, "spine", 1.0)
    parts.append(waist)

    skirt = create_mesh_part("Agnes_Skirt", 'CONE', radius1=0.175, radius2=0.140, depth=0.22, location=(0, 0, 0.74))
    skirt.scale = (1.15, 0.90, 1.0)
    skirt.data.materials.append(mats["leather_dark"])
    assign_vertex_group(skirt, "hips", 1.0)
    parts.append(skirt)

    # 4. Asymmetric Heavy Bronze Pauldron (Left Shoulder)
    pauldron_l = create_mesh_part("Agnes_Pauldron_L", 'SPHERE', radius=0.075, location=(0.25, 0, 1.13))
    pauldron_l.scale = (1.3, 1.1, 0.9)
    pauldron_l.data.materials.append(mats["bronze_armor"])
    assign_vertex_group(pauldron_l, "clavicle.L", 1.0)
    parts.append(pauldron_l)

    horn = create_mesh_part("Agnes_PauldronHorn", 'CONE', radius1=0.024, radius2=0.005, depth=0.09, location=(0.32, 0, 1.19))
    horn.rotation_euler = (0, math.radians(-50), 0)
    horn.data.materials.append(mats["bronze_armor"])
    assign_vertex_group(horn, "clavicle.L", 1.0)
    parts.append(horn)

    pauldron_r = create_mesh_part("Agnes_Pauldron_R", 'SPHERE', radius=0.052, location=(-0.23, 0, 1.12))
    pauldron_r.scale = (1.1, 1.0, 0.8)
    pauldron_r.data.materials.append(mats["leather_dark"])
    assign_vertex_group(pauldron_r, "clavicle.R", 1.0)
    parts.append(pauldron_r)

    # 5. Sturdy Arms & Heavy Vambraces
    for side, sign in [("L", 1), ("R", -1)]:
        uarm = create_mesh_part(f"Agnes_UpperArm_{side}", 'CYLINDER', radius=0.046, depth=0.22, location=(sign * 0.23, 0, 0.98))
        uarm.data.materials.append(mats["gambeson_rust"])
        assign_vertex_group(uarm, f"upper_arm.{side}", 1.0)
        parts.append(uarm)

        vambrace = create_mesh_part(f"Agnes_Vambrace_{side}", 'CYLINDER', radius=0.048, depth=0.20, location=(sign * 0.25, 0, 0.76))
        vambrace.data.materials.append(mats["iron_metal"])
        assign_vertex_group(vambrace, f"forearm.{side}", 1.0)
        parts.append(vambrace)

        hand = create_mesh_part(f"Agnes_Hand_{side}", 'SPHERE', radius=0.034, location=(sign * 0.25, 0, 0.63))
        hand.scale = (1.0, 1.1, 1.2)
        hand.data.materials.append(mats["leather_dark"])
        assign_vertex_group(hand, f"hand.{side}", 1.0)
        parts.append(hand)

    # 6. Heavy Round Spiked Bronze Buckler (Left Arm - Attached Front -Y)
    buckler = create_mesh_part("Agnes_Buckler", 'CYLINDER', radius=0.145, depth=0.030, location=(0.34, -0.08, 0.76))
    buckler.rotation_euler = (math.radians(-15), math.radians(80), 0)
    buckler.data.materials.append(mats["bronze_armor"])
    assign_vertex_group(buckler, "shield.L", 1.0)
    parts.append(buckler)

    boss = create_mesh_part("Agnes_BucklerBoss", 'SPHERE', radius=0.048, location=(0.36, -0.09, 0.76))
    boss.data.materials.append(mats["iron_metal"])
    assign_vertex_group(boss, "shield.L", 1.0)
    parts.append(boss)

    spike = create_mesh_part("Agnes_BucklerSpike", 'CONE', radius1=0.020, radius2=0.004, depth=0.08, location=(0.38, -0.09, 0.76))
    spike.rotation_euler = (0, math.radians(90), 0)
    spike.data.materials.append(mats["copper_trim"])
    assign_vertex_group(spike, "shield.L", 1.0)
    parts.append(spike)

    # 7. Massive Square Steel Warhammer in Right Hand
    shaft = create_mesh_part("Agnes_HammerShaft", 'CYLINDER', radius=0.022, depth=0.92, location=(-0.25, -0.05, 0.60))
    shaft.data.materials.append(mats["leather_dark"])
    assign_vertex_group(shaft, "hand.R", 1.0)
    parts.append(shaft)

    head_m = create_mesh_part("Agnes_HammerHead", 'CUBE', size=0.130, location=(-0.25, -0.05, 1.02))
    head_m.scale = (1.2, 0.85, 0.85)
    head_m.data.materials.append(mats["iron_metal"])
    assign_vertex_group(head_m, "hand.R", 1.0)
    parts.append(head_m)

    beak = create_mesh_part("Agnes_HammerBeak", 'CONE', radius1=0.030, radius2=0.005, depth=0.09, location=(-0.25, 0.05, 1.02))
    beak.rotation_euler = (math.radians(-90), 0, 0)
    beak.data.materials.append(mats["bronze_armor"])
    assign_vertex_group(beak, "hand.R", 1.0)
    parts.append(beak)

    # 8. Broad Grounded Legs, Heavy Iron Greaves & Thick Iron Soles
    for side, sign in [("L", 1), ("R", -1)]:
        uleg = create_mesh_part(f"Agnes_UpperLeg_{side}", 'CYLINDER', radius=0.068, depth=0.30, location=(sign * 0.110, 0, 0.56))
        uleg.data.materials.append(mats["leather_dark"])
        assign_vertex_group(uleg, f"upper_leg.{side}", 1.0)
        parts.append(uleg)

        greave = create_mesh_part(f"Agnes_Greave_{side}", 'CYLINDER', radius=0.064, depth=0.30, location=(sign * 0.110, -0.01, 0.25))
        greave.data.materials.append(mats["iron_metal"])
        assign_vertex_group(greave, f"lower_leg.{side}", 1.0)
        parts.append(greave)

        boot = create_mesh_part(f"Agnes_Boot_{side}", 'CUBE', size=0.075, location=(sign * 0.110, -0.06, 0.055))
        boot.scale = (1.15, 1.85, 0.70)
        boot.data.materials.append(mats["leather_dark"])
        assign_vertex_group(boot, f"foot.{side}", 1.0)
        parts.append(boot)

        sole = create_mesh_part(f"Agnes_Sole_{side}", 'CUBE', size=0.075, location=(sign * 0.110, -0.06, 0.015))
        sole.scale = (1.20, 1.90, 0.22)
        sole.data.materials.append(mats["iron_metal"])
        assign_vertex_group(sole, f"foot.{side}", 1.0)
        parts.append(sole)

    for p in parts:
        bind_to_armature(p, arm_obj)

    return arm_obj, parts

# =============================================================
# 3. THE GAMBLER BUILDER (Theatrical Showman)
# =============================================================
def build_gambler() -> tuple:
    """
    Constructs The Gambler: Theatrical, broken diagonals, slippery rhythm, 5.2 heads tall (1.42m).
    Tilted fedora with violet ribbon & feather, flared emerald duster coat,
    crimson velvet double-breasted vest, two-tone spats, fanned cards.
    Front faces -Y toward camera.
    """
    mats = get_gambler_materials()
    arm_obj = create_humanoid_armature(
        name="Gambler_Rig",
        height_scale=0.89,
        shoulder_width=0.22,
        hip_width=0.12,
        head_z=1.31,
        has_coat_bones=True,
        has_hat_bone=True
    )

    parts = []

    # 1. Stylized Head & Facial Features (Front -Y)
    head = create_mesh_part("Gambler_Head", 'SPHERE', radius=0.122, location=(0, -0.015, 1.31))
    head.scale = (0.88, 0.90, 1.0)
    head.data.materials.append(mats["skin"])
    assign_vertex_group(head, "head", 1.0)
    parts.append(head)

    # 2. Tilted Fedora with Deep Violet Band & Peacock Feather
    hat_brim = create_mesh_part("Gambler_HatBrim", 'CYLINDER', radius=0.185, depth=0.016, location=(0, -0.01, 1.38))
    hat_brim.rotation_euler = (math.radians(-8), math.radians(-10), math.radians(5))
    hat_brim.data.materials.append(mats["trousers_charcoal"])
    assign_vertex_group(hat_brim, "hat", 1.0)
    parts.append(hat_brim)

    hat_crown = create_mesh_part("Gambler_HatCrown", 'CONE', radius1=0.115, radius2=0.092, depth=0.12, location=(0, -0.01, 1.44))
    hat_crown.rotation_euler = (math.radians(-8), math.radians(-10), math.radians(5))
    hat_crown.data.materials.append(mats["trousers_charcoal"])
    assign_vertex_group(hat_crown, "hat", 1.0)
    parts.append(hat_crown)

    hat_ribbon = create_mesh_part("Gambler_HatRibbon", 'TORUS', major_radius=0.115, minor_radius=0.012, location=(0, -0.01, 1.39))
    hat_ribbon.rotation_euler = (math.radians(-8), math.radians(-10), math.radians(5))
    hat_ribbon.data.materials.append(mats["ribbon_violet"])
    assign_vertex_group(hat_ribbon, "hat", 1.0)
    parts.append(hat_ribbon)

    feather = create_mesh_part("Gambler_Feather", 'CONE', radius1=0.018, radius2=0.002, depth=0.18, location=(-0.11, -0.04, 1.49))
    feather.rotation_euler = (math.radians(-25), math.radians(35), math.radians(-20))
    feather.data.materials.append(mats["duster_emerald"])
    assign_vertex_group(feather, "hat", 1.0)
    parts.append(feather)

    # 3. Continuous Torso: Silk Shirt, Crimson Double-Breasted Vest, Gold Watch Chain
    neck = create_mesh_part("Gambler_Neck", 'CYLINDER', radius=0.046, depth=0.10, location=(0, -0.01, 1.20))
    neck.data.materials.append(mats["shirt_ivory"])
    assign_vertex_group(neck, "neck", 1.0)
    parts.append(neck)

    cravat = create_mesh_part("Gambler_Cravat", 'CONE', radius1=0.038, radius2=0.010, depth=0.12, location=(0, -0.06, 1.15))
    cravat.rotation_euler = (math.radians(-10), 0, 0)
    cravat.data.materials.append(mats["shirt_ivory"])
    assign_vertex_group(cravat, "chest", 1.0)
    parts.append(cravat)

    chest = create_mesh_part("Gambler_Chest", 'CYLINDER', radius=0.110, depth=0.22, location=(0, 0, 1.05))
    chest.scale = (1.15, 0.78, 1.0)
    chest.data.materials.append(mats["vest_crimson"])
    assign_vertex_group(chest, "chest", 1.0)
    parts.append(chest)

    # Gold Buttons & Watch Chain on Crimson Vest
    for i in range(3):
        btn = create_mesh_part(f"Gambler_Btn_{i}", 'SPHERE', radius=0.010, location=(0.028, -0.082, 0.98 + i * 0.042))
        btn.data.materials.append(mats["brass_trim"])
        assign_vertex_group(btn, "chest", 1.0)
        parts.append(btn)

    chain = create_mesh_part("Gambler_WatchChain", 'TORUS', major_radius=0.044, minor_radius=0.006, location=(0.042, -0.078, 0.96))
    chain.rotation_euler = (math.radians(-45), 0, 0)
    chain.data.materials.append(mats["brass_trim"])
    assign_vertex_group(chain, "chest", 1.0)
    parts.append(chain)

    # 4. Flared Emerald Velvet Duster Coat (Over Vest and Hips)
    coat_collar = create_mesh_part("Gambler_CoatCollar", 'TORUS', major_radius=0.115, minor_radius=0.016, location=(0, 0, 1.14))
    coat_collar.scale = (1.20, 0.85, 0.8)
    coat_collar.data.materials.append(mats["duster_emerald"])
    assign_vertex_group(coat_collar, "chest", 1.0)
    parts.append(coat_collar)

    # Solid Emerald Pelvis Body (Connecting Chest to Tails with zero gap)
    hips = create_mesh_part("Gambler_Hips", 'CYLINDER', radius=0.105, depth=0.20, location=(0, 0, 0.84))
    hips.scale = (1.10, 0.76, 1.0)
    hips.data.materials.append(mats["duster_emerald"])
    assign_vertex_group(hips, "hips", 1.0)
    parts.append(hips)

    # Flared Split Duster Tails (Left, Right, Back)
    coat_l = create_mesh_part("Gambler_CoatTail_L", 'CONE', radius1=0.065, radius2=0.038, depth=0.46, location=(0.130, 0.03, 0.58))
    coat_l.rotation_euler = (math.radians(6), math.radians(14), 0)
    coat_l.scale = (0.75, 1.10, 1.0)
    coat_l.data.materials.append(mats["duster_emerald"])
    assign_vertex_group(coat_l, "coat_tail.L", 1.0)
    parts.append(coat_l)

    coat_r = create_mesh_part("Gambler_CoatTail_R", 'CONE', radius1=0.065, radius2=0.038, depth=0.46, location=(-0.130, 0.03, 0.58))
    coat_r.rotation_euler = (math.radians(6), math.radians(-14), 0)
    coat_r.scale = (0.75, 1.10, 1.0)
    coat_r.data.materials.append(mats["duster_emerald"])
    assign_vertex_group(coat_r, "coat_tail.R", 1.0)
    parts.append(coat_r)

    coat_back = create_mesh_part("Gambler_CoatTail_Back", 'CONE', radius1=0.080, radius2=0.045, depth=0.48, location=(0, 0.080, 0.56))
    coat_back.rotation_euler = (math.radians(-12), 0, 0)
    coat_back.scale = (1.10, 0.70, 1.0)
    coat_back.data.materials.append(mats["duster_emerald"])
    assign_vertex_group(coat_back, "hips", 1.0)
    parts.append(coat_back)

    # 5. Asymmetrical Theatrical Arms & Ivory Gloves
    # Left Arm (Casual Hand Tucked at Waist/Vest)
    uarm_l = create_mesh_part("Gambler_UpperArm_L", 'CYLINDER', radius=0.036, depth=0.22, location=(0.165, 0.02, 1.00))
    uarm_l.rotation_euler = (math.radians(-12), math.radians(12), math.radians(14))
    uarm_l.data.materials.append(mats["duster_emerald"])
    assign_vertex_group(uarm_l, "upper_arm.L", 1.0)
    parts.append(uarm_l)

    farm_l = create_mesh_part("Gambler_Forearm_L", 'CYLINDER', radius=0.032, depth=0.20, location=(0.145, -0.03, 0.82))
    farm_l.rotation_euler = (math.radians(35), 0, math.radians(-20))
    farm_l.data.materials.append(mats["duster_emerald"])
    assign_vertex_group(farm_l, "forearm.L", 1.0)
    parts.append(farm_l)

    glove_l = create_mesh_part("Gambler_Glove_L", 'SPHERE', radius=0.030, location=(0.115, -0.05, 0.76))
    glove_l.data.materials.append(mats["shirt_ivory"])
    assign_vertex_group(glove_l, "hand.L", 1.0)
    parts.append(glove_l)

    # Right Arm (Poised Flourishing Fan of 3 Glowing Cards)
    uarm_r = create_mesh_part("Gambler_UpperArm_R", 'CYLINDER', radius=0.036, depth=0.22, location=(-0.175, -0.02, 1.00))
    uarm_r.rotation_euler = (math.radians(20), math.radians(-14), math.radians(-20))
    uarm_r.data.materials.append(mats["duster_emerald"])
    assign_vertex_group(uarm_r, "upper_arm.R", 1.0)
    parts.append(uarm_r)

    farm_r = create_mesh_part("Gambler_Forearm_R", 'CYLINDER', radius=0.032, depth=0.20, location=(-0.195, -0.05, 0.80))
    farm_r.rotation_euler = (math.radians(40), 0, math.radians(20))
    farm_r.data.materials.append(mats["duster_emerald"])
    assign_vertex_group(farm_r, "forearm.R", 1.0)
    parts.append(farm_r)

    glove_r = create_mesh_part("Gambler_Glove_R", 'SPHERE', radius=0.030, location=(-0.205, -0.06, 0.70))
    glove_r.data.materials.append(mats["shirt_ivory"])
    assign_vertex_group(glove_r, "hand.R", 1.0)
    parts.append(glove_r)

    # Glowing Fan of 3 Tarot Cards (Clear 8px x 6px prop at native 1x)
    for i, rot_z in enumerate([-25, 0, 25]):
        card = create_mesh_part(f"Gambler_Card_{i}", 'CUBE', size=0.050, location=(-0.21 + i * 0.014, -0.08, 0.72 + i * 0.010))
        card.scale = (1.3, 0.12, 1.7)
        card.rotation_euler = (math.radians(-20), math.radians(-15), math.radians(rot_z))
        card.data.materials.append(mats["card_white"] if i % 2 == 0 else mats["card_red"])
        assign_vertex_group(card, "hand.R", 1.0)
        parts.append(card)

    # 6. Charcoal Trousers, Two-Tone Ivory Spats & Patent Shoes
    # Right Leg (Weight-bearing stance leg)
    uleg_r = create_mesh_part("Gambler_UpperLeg_R", 'CYLINDER', radius=0.048, depth=0.32, location=(-0.065, 0.01, 0.63))
    uleg_r.data.materials.append(mats["trousers_charcoal"])
    assign_vertex_group(uleg_r, "upper_leg.R", 1.0)
    parts.append(uleg_r)

    boot_r = create_mesh_part("Gambler_Boot_R", 'CYLINDER', radius=0.046, depth=0.34, location=(-0.065, 0.00, 0.30))
    boot_r.data.materials.append(mats["trousers_charcoal"])
    assign_vertex_group(boot_r, "lower_leg.R", 1.0)
    parts.append(boot_r)

    spat_r = create_mesh_part("Gambler_Spat_R", 'TORUS', major_radius=0.048, minor_radius=0.010, location=(-0.065, 0.00, 0.16))
    spat_r.data.materials.append(mats["spats_ivory"])
    assign_vertex_group(spat_r, "foot.R", 1.0)
    parts.append(spat_r)

    shoe_r = create_mesh_part("Gambler_Shoe_R", 'CUBE', size=0.065, location=(-0.065, -0.045, 0.055))
    shoe_r.scale = (1.05, 1.75, 0.70)
    shoe_r.data.materials.append(mats["boots_leather"])
    assign_vertex_group(shoe_r, "foot.R", 1.0)
    parts.append(shoe_r)

    sole_r = create_mesh_part("Gambler_Sole_R", 'CUBE', size=0.065, location=(-0.065, -0.045, 0.015))
    sole_r.scale = (1.10, 1.80, 0.22)
    sole_r.data.materials.append(mats["spats_ivory"])
    assign_vertex_group(sole_r, "foot.R", 1.0)
    parts.append(sole_r)

    # Left Leg (Poised leg angled out 16 degrees)
    uleg_l = create_mesh_part("Gambler_UpperLeg_L", 'CYLINDER', radius=0.048, depth=0.32, location=(0.080, -0.01, 0.63))
    uleg_l.rotation_euler = (0, 0, math.radians(16))
    uleg_l.data.materials.append(mats["trousers_charcoal"])
    assign_vertex_group(uleg_l, "upper_leg.L", 1.0)
    parts.append(uleg_l)

    boot_l = create_mesh_part("Gambler_Boot_L", 'CYLINDER', radius=0.046, depth=0.34, location=(0.080, -0.02, 0.30))
    boot_l.rotation_euler = (0, 0, math.radians(16))
    boot_l.data.materials.append(mats["trousers_charcoal"])
    assign_vertex_group(boot_l, "lower_leg.L", 1.0)
    parts.append(boot_l)

    spat_l = create_mesh_part("Gambler_Spat_L", 'TORUS', major_radius=0.048, minor_radius=0.010, location=(0.080, -0.02, 0.16))
    spat_l.rotation_euler = (0, 0, math.radians(16))
    spat_l.data.materials.append(mats["spats_ivory"])
    assign_vertex_group(spat_l, "foot.L", 1.0)
    parts.append(spat_l)

    shoe_l = create_mesh_part("Gambler_Shoe_L", 'CUBE', size=0.065, location=(0.080, -0.065, 0.055))
    shoe_l.scale = (1.05, 1.75, 0.70)
    shoe_l.rotation_euler = (0, 0, math.radians(16))
    shoe_l.data.materials.append(mats["boots_leather"])
    assign_vertex_group(shoe_l, "foot.L", 1.0)
    parts.append(shoe_l)

    sole_l = create_mesh_part("Gambler_Sole_L", 'CUBE', size=0.065, location=(0.080, -0.065, 0.015))
    sole_l.scale = (1.10, 1.80, 0.22)
    sole_l.rotation_euler = (0, 0, math.radians(16))
    sole_l.data.materials.append(mats["spats_ivory"])
    assign_vertex_group(sole_l, "foot.L", 1.0)
    parts.append(sole_l)

    for p in parts:
        bind_to_armature(p, arm_obj)

    return arm_obj, parts
