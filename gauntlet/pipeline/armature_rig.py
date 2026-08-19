# gauntlet/pipeline/armature_rig.py
# Parametric Armature Builder for DRPG NPC Sprites in Blender

import bpy
import math
from mathutils import Vector

def create_humanoid_armature(
    name: str = "NPC_Armature",
    height_scale: float = 1.0,
    shoulder_width: float = 0.22,
    hip_width: float = 0.12,
    head_z: float = 1.45,
    has_coat_bones: bool = True,
    has_hat_bone: bool = False
) -> bpy.types.Object:
    """
    Constructs a clean, fully-featured humanoid skeleton configured for 5.0-5.5 heads tall characters.
    """
    arm_data = bpy.data.armatures.new(name=f"{name}_Data")
    arm_obj = bpy.data.objects.new(name, arm_data)
    bpy.context.scene.collection.objects.link(arm_obj)
    bpy.context.view_layer.objects.active = arm_obj

    bpy.ops.object.mode_set(mode='EDIT')
    eb = arm_data.edit_bones

    # Root
    root = eb.new("root")
    root.head = (0, 0, 0)
    root.tail = (0, 0, 0.1)

    # Pelvis / Hips
    hips = eb.new("hips")
    hips.head = (0, 0, 0.82 * height_scale)
    hips.tail = (0, 0, 0.95 * height_scale)
    hips.parent = root

    # Spine & Chest
    spine = eb.new("spine")
    spine.head = (0, 0, 0.95 * height_scale)
    spine.tail = (0, 0, 1.12 * height_scale)
    spine.parent = hips

    chest = eb.new("chest")
    chest.head = (0, 0, 1.12 * height_scale)
    chest.tail = (0, 0, 1.28 * height_scale)
    chest.parent = spine

    neck = eb.new("neck")
    neck.head = (0, 0, 1.28 * height_scale)
    neck.tail = (0, 0, 1.36 * height_scale)
    neck.parent = chest

    head = eb.new("head")
    head.head = (0, 0, 1.36 * height_scale)
    head.tail = (0, 0, head_z * height_scale + 0.18)
    head.parent = neck

    # Legs (Left & Right)
    for side, sign in [("L", 1), ("R", -1)]:
        thigh = eb.new(f"thigh.{side}")
        thigh.head = (sign * hip_width, 0, 0.80 * height_scale)
        thigh.tail = (sign * hip_width, 0.01, 0.44 * height_scale)
        thigh.parent = hips

        shin = eb.new(f"shin.{side}")
        shin.head = thigh.tail
        shin.tail = (sign * hip_width, -0.01, 0.08 * height_scale)
        shin.parent = thigh

        foot = eb.new(f"foot.{side}")
        foot.head = shin.tail
        foot.tail = (sign * hip_width, 0.14 * height_scale, 0.0)
        foot.parent = shin

    # Arms (Left & Right)
    for side, sign in [("L", 1), ("R", -1)]:
        shldr = eb.new(f"shoulder.{side}")
        shldr.head = (sign * 0.06, 0, 1.25 * height_scale)
        shldr.tail = (sign * shoulder_width, 0, 1.22 * height_scale)
        shldr.parent = chest

        uarm = eb.new(f"upper_arm.{side}")
        uarm.head = shldr.tail
        uarm.tail = (sign * (shoulder_width + 0.15), 0, 0.98 * height_scale)
        uarm.parent = shldr

        farm = eb.new(f"forearm.{side}")
        farm.head = uarm.tail
        farm.tail = (sign * (shoulder_width + 0.22), 0.02, 0.76 * height_scale)
        farm.parent = uarm

        hand = eb.new(f"hand.{side}")
        hand.head = farm.tail
        hand.tail = (sign * (shoulder_width + 0.26), 0.05, 0.62 * height_scale)
        hand.parent = farm

    # Secondary Garment / Accessory bones
    if has_coat_bones:
        for cside, cx, cy in [("back", 0, -0.10), ("front", 0, 0.10), ("L", 0.18, 0), ("R", -0.18, 0)]:
            b1 = eb.new(f"coat_{cside}.01")
            b1.head = (cx, cy, 0.80 * height_scale)
            b1.tail = (cx * 1.3, cy * 1.3, 0.45 * height_scale)
            b1.parent = hips

            b2 = eb.new(f"coat_{cside}.02")
            b2.head = b1.tail
            b2.tail = (cx * 1.6, cy * 1.6, 0.12 * height_scale)
            b2.parent = b1

    # Hair / Prop bones
    hair = eb.new("hair_back")
    hair.head = (0, -0.10, 1.48 * height_scale)
    hair.tail = (0, -0.18, 1.25 * height_scale)
    hair.parent = head

    prop_r = eb.new("prop_hand.R")
    prop_r.head = (-(shoulder_width + 0.26), 0.05, 0.62 * height_scale)
    prop_r.tail = (-(shoulder_width + 0.26), 0.25, 0.40 * height_scale)
    prop_r.parent = eb["hand.R"]

    if has_hat_bone:
        hat = eb.new("hat_brim")
        hat.head = (0, 0, 1.58 * height_scale)
        hat.tail = (0.08, 0.04, 1.72 * height_scale)
        hat.parent = head

    bpy.ops.object.mode_set(mode='OBJECT')
    return arm_obj
