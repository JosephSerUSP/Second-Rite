# gauntlet/pipeline/animator.py
# Bespoke Animation Authoring Engine for Celina, Agnes, and The Gambler in Blender

import bpy
import math
from mathutils import Euler, Vector

def clear_animation_data(arm_obj: bpy.types.Object):
    """Clears existing animation data on the armature."""
    arm_obj.animation_data_clear()
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='POSE')
    for pb in arm_obj.pose.bones:
        pb.location = (0, 0, 0)
        pb.rotation_euler = (0, 0, 0)
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.scale = (1, 1, 1)
    bpy.ops.object.mode_set(mode='OBJECT')

def set_bone_keyframe(pb: bpy.types.PoseBone, frame: int, rot_deg=(0,0,0), loc=(0,0,0), scale=(1,1,1)):
    """Sets rotation and location keyframes on a pose bone."""
    pb.rotation_mode = 'XYZ'
    pb.rotation_euler = Euler((math.radians(rot_deg[0]), math.radians(rot_deg[1]), math.radians(rot_deg[2])), 'XYZ')
    pb.location = Vector(loc)
    pb.scale = Vector(scale)
    pb.keyframe_insert(data_path="rotation_euler", frame=frame)
    pb.keyframe_insert(data_path="location", frame=frame)

# ----------------------------------------------------------------------
# 1. IDLE ANIMATIONS (16 Frames Loop - 3 Uniquely Contrasting Rhythms)
# ----------------------------------------------------------------------
def author_celina_idle(arm_obj: bpy.types.Object):
    """
    Celina Idle (16 Frames): 2-Cycle Crisp Fencing Pulse (Period = 8 frames).
    Chest breathe lift (12px relative), high fencing guard micro-correction, sharp head poise.
    """
    clear_animation_data(arm_obj)
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='POSE')
    pb = arm_obj.pose.bones

    for f in range(1, 17):
        t = (f - 1) / 8.0 # 2 full cycles in 16 frames!
        rad = t * 2 * math.pi
        sine_breath = math.sin(rad)
        cos_breath = math.cos(rad)

        if "chest" in pb:
            set_bone_keyframe(pb["chest"], f, rot_deg=(6.0 * sine_breath, 0, 3.0 * cos_breath), loc=(0, 0, sine_breath * 0.015))
        if "neck" in pb:
            set_bone_keyframe(pb["neck"], f, rot_deg=(-2.5 * sine_breath, 0, 0))
        if "head" in pb:
            set_bone_keyframe(pb["head"], f, rot_deg=(-4.0 * sine_breath, 4.0 * cos_breath, -2.0 * sine_breath))

        # Right arm on rapier hilt: sharp micro-adjustments
        if "shoulder.R" in pb:
            set_bone_keyframe(pb["shoulder.R"], f, rot_deg=(0, 0, -4.0 * sine_breath))
        if "upper_arm.R" in pb:
            set_bone_keyframe(pb["upper_arm.R"], f, rot_deg=(14 + 5.0 * sine_breath, -10, -22))
        if "forearm.R" in pb:
            set_bone_keyframe(pb["forearm.R"], f, rot_deg=(40 + 6.0 * sine_breath, 0, 24))
        if "hand.R" in pb:
            set_bone_keyframe(pb["hand.R"], f, rot_deg=(18 + 12.0 * cos_breath, 0, 12))

        if "shoulder.L" in pb:
            set_bone_keyframe(pb["shoulder.L"], f, rot_deg=(0, 0, 3.0 * sine_breath))
        if "upper_arm.L" in pb:
            set_bone_keyframe(pb["upper_arm.L"], f, rot_deg=(8 - 3.0 * sine_breath, 10, 16))
        if "forearm.L" in pb:
            set_bone_keyframe(pb["forearm.L"], f, rot_deg=(28 - 4.0 * sine_breath, 0, -16))
        if "hand.L" in pb:
            set_bone_keyframe(pb["hand.L"], f, rot_deg=(10, 0, -8))

    bpy.ops.object.mode_set(mode='OBJECT')

def author_agnes_idle(arm_obj: bpy.types.Object):
    """
    Agnes Idle (16 Frames): 1-Cycle Heavy Combat Compression (Period = 16 frames).
    Deep torso & hip compression (-0.035m) on frames 1-8, delayed heavy pauldron settle on frames 9-16.
    """
    clear_animation_data(arm_obj)
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='POSE')
    pb = arm_obj.pose.bones

    for f in range(1, 17):
        t = (f - 1) / 16.0
        rad = t * 2 * math.pi
        sine_drop = math.sin(rad)
        cos_lag = math.cos(rad - 0.5)

        if "hips" in pb:
            set_bone_keyframe(pb["hips"], f, loc=(0, 0, -0.030 * max(0, sine_drop)))
        if "chest" in pb:
            set_bone_keyframe(pb["chest"], f, rot_deg=(-8.0 * sine_drop, 0, 0), loc=(0, 0, -0.015 * sine_drop))
        if "head" in pb:
            set_bone_keyframe(pb["head"], f, rot_deg=(6.0 * sine_drop, 0, 0))

        # Heavy arms: right mace drags slightly, left buckler braces
        if "shoulder.R" in pb:
            set_bone_keyframe(pb["shoulder.R"], f, rot_deg=(-4.0 * cos_lag, 0, -6.0 * sine_drop))
        if "upper_arm.R" in pb:
            set_bone_keyframe(pb["upper_arm.R"], f, rot_deg=(18 + 8.0 * sine_drop, -12, -18))
        if "forearm.R" in pb:
            set_bone_keyframe(pb["forearm.R"], f, rot_deg=(35 + 10.0 * sine_drop, 0, 15))
        if "hand.R" in pb:
            set_bone_keyframe(pb["hand.R"], f, rot_deg=(15, 0, 10))

        if "shoulder.L" in pb:
            set_bone_keyframe(pb["shoulder.L"], f, rot_deg=(3.0 * cos_lag, 0, 5.0 * sine_drop))
        if "upper_arm.L" in pb:
            set_bone_keyframe(pb["upper_arm.L"], f, rot_deg=(12 - 6.0 * sine_drop, 15, 20))
        if "forearm.L" in pb:
            set_bone_keyframe(pb["forearm.L"], f, rot_deg=(42 - 8.0 * sine_drop, 0, -22))
        if "hand.L" in pb:
            set_bone_keyframe(pb["hand.L"], f, rot_deg=(12, 0, -10))

    bpy.ops.object.mode_set(mode='OBJECT')

def author_gambler_idle(arm_obj: bpy.types.Object):
    """
    The Gambler Idle (16 Frames): Buoyant Off-Axis Sway & Card Fan Flutter (Period = 16 frames).
    Asymmetric lateral sway (X=+-0.035m), hat counter-bob, card fan fluttering in open negative space.
    """
    clear_animation_data(arm_obj)
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='POSE')
    pb = arm_obj.pose.bones

    for f in range(1, 17):
        t = (f - 1) / 16.0
        rad = t * 2 * math.pi
        sine_sway = math.sin(rad)
        cos_sway = math.cos(rad)

        if "hips" in pb:
            set_bone_keyframe(pb["hips"], f, loc=(0.035 * sine_sway, 0, 0.012 * abs(sine_sway)), rot_deg=(0, 0, 8.0 * sine_sway))
        if "chest" in pb:
            set_bone_keyframe(pb["chest"], f, rot_deg=(4.0 * cos_sway, 0, -6.0 * sine_sway), loc=(0, 0, 0.012 * cos_sway))
        if "head" in pb:
            set_bone_keyframe(pb["head"], f, rot_deg=(-3.0 * cos_sway, 12.0 * sine_sway, 8.0 * sine_sway))

        # Hat counter-tilt
        if "hat" in pb:
            set_bone_keyframe(pb["hat"], f, rot_deg=(-6.0 * cos_sway, -10.0 * sine_sway, 0))

        # Left hand: Giant Card Fan extended into negative space with dynamic flutter
        if "shoulder.L" in pb:
            set_bone_keyframe(pb["shoulder.L"], f, rot_deg=(0, 0, 6.0 * sine_sway))
        if "upper_arm.L" in pb:
            set_bone_keyframe(pb["upper_arm.L"], f, rot_deg=(-15 - 5.0 * cos_sway, 20, 35 + 8.0 * sine_sway))
        if "forearm.L" in pb:
            set_bone_keyframe(pb["forearm.L"], f, rot_deg=(65 + 10.0 * cos_sway, 0, -30))
        if "hand.L" in pb:
            set_bone_keyframe(pb["hand.L"], f, rot_deg=(25 + 18.0 * sine_sway, 15 * cos_sway, -20))

        # Right hand poised on vest / hip
        if "upper_arm.R" in pb:
            set_bone_keyframe(pb["upper_arm.R"], f, rot_deg=(15 + 4.0 * cos_sway, -15, -20))
        if "forearm.R" in pb:
            set_bone_keyframe(pb["forearm.R"], f, rot_deg=(45 + 6.0 * sine_sway, 0, 25))
        if "hand.R" in pb:
            set_bone_keyframe(pb["hand.R"], f, rot_deg=(15, 0, 10))

    bpy.ops.object.mode_set(mode='OBJECT')

# ----------------------------------------------------------------------
# 2. 8-DIRECTION WALK LOCOMOTION (8 Frames per Direction = 64 Frames)
# ----------------------------------------------------------------------
def author_walk_cycle(arm_obj: bpy.types.Object, char_type: str = "celina"):
    """
    Constructs an authentic 8-frame walk cycle with hip roll, shoulder counter-rotation,
    proper contact / passing / push-off poses, and firm foot ground contact.
    """
    clear_animation_data(arm_obj)
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='POSE')
    pb = arm_obj.pose.bones

    if char_type == "agnes":
        stride_len = 24.0
        hip_drop = 0.022
        arm_swing = 28.0
        sway = 3.8
        pass_lift = 38.0
    elif char_type == "gambler":
        stride_len = 28.0
        hip_drop = 0.020
        arm_swing = 34.0
        sway = 4.5
        pass_lift = 45.0
    else: # Celina
        stride_len = 30.0
        hip_drop = 0.018
        arm_swing = 26.0
        sway = 3.2
        pass_lift = 48.0

    for f in range(1, 9):
        phase = (f - 1) / 8.0
        rad = phase * 2 * math.pi
        sine_leg = math.sin(rad)
        cos_leg = math.cos(rad)

        bounce = -abs(sine_leg) * hip_drop
        hip_sway = sine_leg * sway

        if "hips" in pb:
            set_bone_keyframe(pb["hips"], f, rot_deg=(0, hip_sway, -hip_sway * 0.8), loc=(0, 0, bounce))

        if "chest" in pb:
            set_bone_keyframe(pb["chest"], f, rot_deg=(3, -hip_sway * 1.4, hip_sway * 1.0))
        if "head" in pb:
            set_bone_keyframe(pb["head"], f, rot_deg=(-2, hip_sway * 0.6, 0))

        if sine_leg >= 0:
            thigh_l_rot = -sine_leg * stride_len
            shin_l_rot = max(0, -cos_leg * pass_lift)
            foot_l_rot = sine_leg * 12.0

            thigh_r_rot = sine_leg * stride_len * 0.85
            shin_r_rot = max(0, cos_leg * 15.0)
            foot_r_rot = -sine_leg * 15.0
        else:
            thigh_l_rot = -sine_leg * stride_len * 0.85
            shin_l_rot = max(0, -cos_leg * 15.0)
            foot_l_rot = sine_leg * 15.0

            thigh_r_rot = sine_leg * stride_len
            shin_r_rot = max(0, cos_leg * pass_lift)
            foot_r_rot = -sine_leg * 12.0

        if "thigh.L" in pb:
            set_bone_keyframe(pb["thigh.L"], f, rot_deg=(thigh_l_rot, 0, 0))
        if "shin.L" in pb:
            set_bone_keyframe(pb["shin.L"], f, rot_deg=(shin_l_rot, 0, 0))
        if "foot.L" in pb:
            set_bone_keyframe(pb["foot.L"], f, rot_deg=(foot_l_rot, 0, 0))

        if "thigh.R" in pb:
            set_bone_keyframe(pb["thigh.R"], f, rot_deg=(thigh_r_rot, 0, 0))
        if "shin.R" in pb:
            set_bone_keyframe(pb["shin.R"], f, rot_deg=(shin_r_rot, 0, 0))
        if "foot.R" in pb:
            set_bone_keyframe(pb["foot.R"], f, rot_deg=(foot_r_rot, 0, 0))

        if "upper_arm.L" in pb:
            set_bone_keyframe(pb["upper_arm.L"], f, rot_deg=(sine_leg * arm_swing, 0, 10))
        if "forearm.L" in pb:
            set_bone_keyframe(pb["forearm.L"], f, rot_deg=(20 + abs(sine_leg) * 18.0, 0, -8))

        if "upper_arm.R" in pb:
            set_bone_keyframe(pb["upper_arm.R"], f, rot_deg=(-sine_leg * arm_swing, 0, -10))
        if "forearm.R" in pb:
            set_bone_keyframe(pb["forearm.R"], f, rot_deg=(20 + abs(sine_leg) * 18.0, 0, 8))

    bpy.ops.object.mode_set(mode='OBJECT')

# ----------------------------------------------------------------------
# 3. SIGNATURE GESTURES (24 Frames)
# ----------------------------------------------------------------------
def author_celina_gesture(arm_obj: bpy.types.Object):
    """
    Celina Signature Gesture (24 Frames): Decisive fencing salute flourish.
    """
    clear_animation_data(arm_obj)
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='POSE')
    pb = arm_obj.pose.bones

    for f in range(1, 25):
        if f <= 6:
            p = (f - 1) / 5.0
            r_arm = (20 + p * 35, -p * 25, -15 - p * 20)
            r_fore = (30 + p * 55, 0, 20 + p * 25)
            chest_rot = (p * 6, -p * 8, p * 6)
            head_rot = (-p * 4, p * 10, -p * 6)
            l_arm = (4 - p * 8, 6 + p * 10, 12 + p * 15)
        elif f <= 11:
            p = (f - 6) / 5.0
            r_arm = (55 - p * 30, -25 + p * 45, -35 + p * 65)
            r_fore = (85 - p * 50, 0, 45 - p * 35)
            chest_rot = (6 - p * 10, -8 + p * 16, 6 - p * 10)
            head_rot = (-4 + p * 8, 10 - p * 18, -6 + p * 10)
            l_arm = (-4 - p * 12, 16 - p * 8, 27 - p * 12)
        elif f <= 17:
            p = (f - 11) / 6.0
            decay = math.sin(p * math.pi) * 2.0
            r_arm = (25 + decay, 20, 30)
            r_fore = (35, 0, 10)
            chest_rot = (-4, 8, -4)
            head_rot = (4, -8, 4)
            l_arm = (-16, 8, 15)
        else:
            p = (f - 17) / 7.0
            r_arm = (25 - p * 17, 20 - p * 28, 30 - p * 46)
            r_fore = (35 - p * 3, 0, 10 + p * 8)
            chest_rot = (-4 + p * 4, 8 - p * 8, -4 + p * 4)
            head_rot = (4 - p * 4, -8 + p * 8, 4 - p * 4)
            l_arm = (-16 + p * 20, 8 - p * 2, 15 - p * 3)

        if "chest" in pb: set_bone_keyframe(pb["chest"], f, rot_deg=chest_rot)
        if "head" in pb: set_bone_keyframe(pb["head"], f, rot_deg=head_rot)
        if "upper_arm.R" in pb: set_bone_keyframe(pb["upper_arm.R"], f, rot_deg=r_arm)
        if "forearm.R" in pb: set_bone_keyframe(pb["forearm.R"], f, rot_deg=r_fore)
        if "upper_arm.L" in pb: set_bone_keyframe(pb["upper_arm.L"], f, rot_deg=l_arm)

    bpy.ops.object.mode_set(mode='OBJECT')

def author_agnes_gesture(arm_obj: bpy.types.Object):
    """
    Agnes Signature Gesture (24 Frames): Heavy 2-handed overhead smash & ground slam.
    """
    clear_animation_data(arm_obj)
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='POSE')
    pb = arm_obj.pose.bones

    for f in range(1, 25):
        if f <= 6:
            p = (f - 1) / 5.0
            hips_loc = (0, 0, -p * 0.025)
            chest_rot = (-p * 18, p * 12, -p * 15)
            l_arm = (p * 45, p * 20, p * 35)
            l_fore = (35 + p * 55, 0, -20 - p * 20)
            r_arm = (-p * 65, -p * 25, -p * 40)
            r_fore = (20 + p * 60, 0, 25)
        elif f <= 12:
            p = (f - 6) / 6.0
            hips_loc = (0, 0, -0.025 - p * 0.035)
            chest_rot = (-18 + p * 45, 12 - p * 24, -15 + p * 25)
            l_arm = (45 - p * 65, 20 - p * 35, 35 - p * 45)
            l_fore = (90 - p * 60, 0, -40 + p * 30)
            r_arm = (-65 + p * 120, -25 + p * 35, -40 + p * 55)
            r_fore = (80 - p * 55, 0, 25)
        elif f <= 17:
            p = (f - 12) / 5.0
            decay = math.sin(p * math.pi * 3) * (1.0 - p)
            hips_loc = (0, 0, -0.055 + decay * 0.015)
            chest_rot = (27 + decay * 6, -12, 10)
            l_arm = (-20 + decay * 5, -15, -10)
            l_fore = (30 + decay * 6, 0, -10)
            r_arm = (55 + decay * 6, 10, 15)
            r_fore = (25 + decay * 6, 0, 25)
        else:
            p = (f - 17) / 7.0
            hips_loc = (0, 0, -0.055 + p * 0.055)
            chest_rot = (27 - p * 27, -12 + p * 12, 10 - p * 10)
            l_arm = (-20 + p * 32, -15 + p * 25, -10 + p * 32)
            l_fore = (30 + p * 15, 0, -10 - p * 15)
            r_arm = (55 - p * 47, 10 - p * 18, 15 - p * 33)
            r_fore = (25 + p * 3, 0, 15)

        if "hips" in pb: set_bone_keyframe(pb["hips"], f, loc=hips_loc)
        if "chest" in pb: set_bone_keyframe(pb["chest"], f, rot_deg=chest_rot)
        if "upper_arm.L" in pb: set_bone_keyframe(pb["upper_arm.L"], f, rot_deg=l_arm)
        if "forearm.L" in pb: set_bone_keyframe(pb["forearm.L"], f, rot_deg=l_fore)
        if "upper_arm.R" in pb: set_bone_keyframe(pb["upper_arm.R"], f, rot_deg=r_arm)
        if "forearm.R" in pb: set_bone_keyframe(pb["forearm.R"], f, rot_deg=r_fore)

    bpy.ops.object.mode_set(mode='OBJECT')

def author_gambler_gesture(arm_obj: bpy.types.Object):
    """
    The Gambler Signature Gesture (24 Frames): Flamboyant 3-card fan snap & showstopper bow.
    """
    clear_animation_data(arm_obj)
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='POSE')
    pb = arm_obj.pose.bones

    for f in range(1, 25):
        if f <= 6:
            p = (f - 1) / 5.0
            chest_rot = (p * 10, -p * 15, p * 8)
            head_rot = (-p * 8, p * 12, -p * 6)
            l_arm = (-p * 25, p * 20, 10 + p * 25)
            l_fore = (40 + p * 40, 0, -15 - p * 25)
            l_hand = (10 + p * 25, 0, -10 - p * 20)
        elif f <= 12:
            p = (f - 6) / 6.0
            chest_rot = (10 - p * 22, -15 + p * 30, 8 - p * 16)
            head_rot = (-8 + p * 16, 12 - p * 24, -6 + p * 12)
            l_arm = (-25 - p * 40, 20 - p * 35, 35 + p * 45)
            l_fore = (80 - p * 45, 0, -40 - p * 30)
            l_hand = (35 + p * 35, p * 25, -30 - p * 25)
        elif f <= 18:
            p = (f - 12) / 6.0
            decay = math.sin(p * math.pi) * 3.0
            chest_rot = (-12 + decay, 15, -8)
            head_rot = (8, -12, 6)
            l_arm = (-65 + decay, -15, 80)
            l_fore = (35, 0, -70)
            l_hand = (70 + decay * 2, 25, -55)
        else:
            p = (f - 18) / 6.0
            chest_rot = (-12 + p * 12, 15 - p * 15, -8 + p * 8)
            head_rot = (8 - p * 8, -12 + p * 12, 6 - p * 6)
            l_arm = (-65 + p * 50, -15 + p * 25, 80 - p * 60)
            l_fore = (35 + p * 15, 0, -70 + p * 55)
            l_hand = (70 - p * 55, 25 - p * 25, -55 + p * 45)

        if "chest" in pb: set_bone_keyframe(pb["chest"], f, rot_deg=chest_rot)
        if "head" in pb: set_bone_keyframe(pb["head"], f, rot_deg=head_rot)
        if "upper_arm.L" in pb: set_bone_keyframe(pb["upper_arm.L"], f, rot_deg=l_arm)
        if "forearm.L" in pb: set_bone_keyframe(pb["forearm.L"], f, rot_deg=l_fore)
        if "hand.L" in pb: set_bone_keyframe(pb["hand.L"], f, rot_deg=l_hand)

    bpy.ops.object.mode_set(mode='OBJECT')
