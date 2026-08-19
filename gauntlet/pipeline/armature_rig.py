# gauntlet/pipeline/armature_rig.py
# Universal humanoid skeletal armature for DRPG sprite animation in Blender

import bpy
import math
from mathutils import Vector

def create_humanoid_armature(
    name: str = "HumanoidRig",
    height_scale: float = 1.0,
    shoulder_width: float = 0.22,
    hip_width: float = 0.12,
    head_z: float = 1.35,
    has_coat_bones: bool = True,
    has_hat_bone: bool = False,
    has_shield_bone: bool = False
) -> bpy.types.Object:
    """
    Creates a clean humanoid armature with proper bone hierarchy and roll angles.
    """
    # Remove existing armature with same name
    old_obj = bpy.data.objects.get(name)
    if old_obj:
        bpy.data.objects.remove(old_obj, do_unlink=True)

    arm_data = bpy.data.armatures.new(name=f"{name}_Data")
    arm_obj = bpy.data.objects.new(name, arm_data)
    bpy.context.scene.collection.objects.link(arm_obj)
    bpy.context.view_layer.objects.active = arm_obj

    bpy.ops.object.mode_set(mode='EDIT')
    edit_bones = arm_data.edit_bones

    # 1. Root & Spine Chain
    root = edit_bones.new("root")
    root.head = (0, 0, 0)
    root.tail = (0, 0, 0.1)

    hip_z = 0.78 * height_scale
    hips = edit_bones.new("hips")
    hips.head = (0, 0, hip_z)
    hips.tail = (0, 0, hip_z + 0.12 * height_scale)
    hips.parent = root

    spine = edit_bones.new("spine")
    spine.head = (0, 0, hip_z + 0.12 * height_scale)
    spine.tail = (0, 0, hip_z + 0.28 * height_scale)
    spine.parent = hips

    chest = edit_bones.new("chest")
    chest.head = spine.tail
    chest_top_z = head_z - 0.20 * height_scale
    chest.tail = (0, 0, chest_top_z)
    chest.parent = spine

    neck = edit_bones.new("neck")
    neck.head = chest.tail
    neck.tail = (0, 0, head_z - 0.08 * height_scale)
    neck.parent = chest

    head = edit_bones.new("head")
    head.head = neck.tail
    head.tail = (0, 0, head_z + 0.18 * height_scale)
    head.parent = neck

    if has_hat_bone:
        hat = edit_bones.new("hat")
        hat.head = head.tail
        hat.tail = (0, 0, head_z + 0.32 * height_scale)
        hat.parent = head

    # 2. Arms (Left and Right)
    for side, sign in [("L", 1), ("R", -1)]:
        clavicle = edit_bones.new(f"clavicle.{side}")
        clavicle.head = (sign * 0.04, 0, chest_top_z - 0.04 * height_scale)
        clavicle.tail = (sign * shoulder_width, 0, chest_top_z)
        clavicle.parent = chest

        upper_arm = edit_bones.new(f"upper_arm.{side}")
        upper_arm.head = clavicle.tail
        upper_arm.tail = (sign * (shoulder_width + 0.02), 0, chest_top_z - 0.32 * height_scale)
        upper_arm.parent = clavicle

        forearm = edit_bones.new(f"forearm.{side}")
        forearm.head = upper_arm.tail
        forearm.tail = (sign * (shoulder_width + 0.03), 0, chest_top_z - 0.60 * height_scale)
        forearm.parent = upper_arm

        hand = edit_bones.new(f"hand.{side}")
        hand.head = forearm.tail
        hand.tail = (sign * (shoulder_width + 0.03), 0, chest_top_z - 0.72 * height_scale)
        hand.parent = forearm

        # Prop bones
        prop = edit_bones.new(f"prop.{side}")
        prop.head = hand.tail
        prop.tail = (sign * (shoulder_width + 0.03), 0.25, chest_top_z - 0.72 * height_scale)
        prop.parent = hand

        if side == "L" and has_shield_bone:
            shield_bone = edit_bones.new("shield.L")
            shield_bone.head = forearm.head
            shield_bone.tail = (shoulder_width + 0.12, 0.10, chest_top_z - 0.45 * height_scale)
            shield_bone.parent = forearm

    # 3. Legs (Left and Right)
    for side, sign in [("L", 1), ("R", -1)]:
        upper_leg = edit_bones.new(f"upper_leg.{side}")
        upper_leg.head = (sign * hip_width, 0, hip_z)
        upper_leg.tail = (sign * hip_width, 0, hip_z * 0.52)
        upper_leg.parent = hips

        lower_leg = edit_bones.new(f"lower_leg.{side}")
        lower_leg.head = upper_leg.tail
        lower_leg.tail = (sign * hip_width, 0, 0.08 * height_scale)
        lower_leg.parent = upper_leg

        foot = edit_bones.new(f"foot.{side}")
        foot.head = lower_leg.tail
        foot.tail = (sign * hip_width, 0.16 * height_scale, 0.0)
        foot.parent = lower_leg

    # 4. Coat Tail Bones (for secondary motion)
    if has_coat_bones:
        for side, sign in [("L", 1), ("R", -1)]:
            coat_tail = edit_bones.new(f"coat_tail.{side}")
            coat_tail.head = (sign * (hip_width + 0.04), -0.04, hip_z)
            coat_tail.tail = (sign * (hip_width + 0.06), -0.06, 0.20 * height_scale)
            coat_tail.parent = hips

        coat_back = edit_bones.new("coat_tail.Back")
        coat_back.head = (0, -0.08, hip_z)
        coat_back.tail = (0, -0.12, 0.18 * height_scale)
        coat_back.parent = hips

    bpy.ops.object.mode_set(mode='OBJECT')
    return arm_obj
