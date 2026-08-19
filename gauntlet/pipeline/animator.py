# gauntlet/pipeline/animator.py
# Programmatic character animation system authoring idles, 8-direction walks, and signature gestures

import bpy
import math
from mathutils import Euler, Vector

def set_bone_rotation(pose_bone, euler_deg: tuple, frame: int):
    """Helper to set rotation in degrees (XYZ) and insert keyframe."""
    pose_bone.rotation_mode = 'XYZ'
    pose_bone.rotation_euler = Euler((
        math.radians(euler_deg[0]),
        math.radians(euler_deg[1]),
        math.radians(euler_deg[2])
    ), 'XYZ')
    pose_bone.keyframe_insert(data_path="rotation_euler", frame=frame)

def set_bone_location(pose_bone, loc: tuple, frame: int):
    """Helper to set bone location and insert keyframe."""
    pose_bone.location = Vector(loc)
    pose_bone.keyframe_insert(data_path="location", frame=frame)

# =============================================================
# 1. IDLE ANIMATIONS (16 Frames Loopable)
# =============================================================
def animate_celina_idle(arm_obj: bpy.types.Object):
    """
    Celina Idle: Restrained, deliberate, asymmetrical duelist stance.
    - Right hand posed firmly on rapier hilt at hip with elbow flared out.
    - Left hand resting on hip/waist with elbow flared out.
    - Visible 3px chest breathing, chin elevation, coat tail sway.
    """
    action = bpy.data.actions.new(name="Celina_Idle")
    arm_obj.animation_data_create()
    arm_obj.animation_data.action = action
    bones = arm_obj.pose.bones

    # Ensure character faces front
    arm_obj.rotation_euler = (0, 0, 0)
    arm_obj.keyframe_insert(data_path="rotation_euler", frame=1)

    for f in range(1, 17):
        t = (f - 1) / 16.0
        phase = math.sin(t * 2 * math.pi)

        # Clear 3.5px chest breathing & proud chin elevation
        if "chest" in bones:
            set_bone_rotation(bones["chest"], (6.0 + 4.5 * phase, 0, -4.0), f)
        if "head" in bones:
            set_bone_rotation(bones["head"], (-4.0 - 2.0 * phase, 0, 3.0), f)
        if "hips" in bones:
            set_bone_location(bones["hips"], (0.008, 0, 0.000), f) # Fixed Z anchor guarantees 0.0px ground drift
            set_bone_rotation(bones["hips"], (0, 0, 4.0 + 1.5 * phase), f)

        # Right arm: Poised on rapier hilt at hip with blade hanging down-back along thigh
        if "upper_arm.R" in bones:
            set_bone_rotation(bones["upper_arm.R"], (18.0 + 2.0 * phase, -14.0, -18.0), f)
        if "forearm.R" in bones:
            set_bone_rotation(bones["forearm.R"], (40.0 + 1.5 * phase, 0, 18.0), f)
        if "hand.R" in bones:
            set_bone_rotation(bones["hand.R"], (12.0 + 2.5 * phase, 0, -28.0), f)

        # Left arm: Tucked gracefully behind the small of the back
        if "upper_arm.L" in bones:
            set_bone_rotation(bones["upper_arm.L"], (-18.0 - 1.5 * phase, 12.0, 16.0), f)
        if "forearm.L" in bones:
            set_bone_rotation(bones["forearm.L"], (-50.0, 0, -55.0), f)

        # Coat tail secondary sway
        if "coat_tail.L" in bones:
            set_bone_rotation(bones["coat_tail.L"], (-6.0 + 4.0 * phase, 0, 0), f)
        if "coat_tail.R" in bones:
            set_bone_rotation(bones["coat_tail.R"], (-6.0 - 4.0 * phase, 0, 0), f)

def animate_agnes_idle(arm_obj: bpy.types.Object):
    """Agnes Idle: Heavy grounded breathing, sturdy shoulder rise, braced buckler arm, scanning stance."""
    action = bpy.data.actions.new(name="Agnes_Idle")
    arm_obj.animation_data_create()
    arm_obj.animation_data.action = action
    bones = arm_obj.pose.bones

    for f in range(1, 17):
        t = (f - 1) / 16.0
        phase = math.sin(t * 2 * math.pi)

        # Heavy chest and shoulder expansion
        if "chest" in bones:
            set_bone_rotation(bones["chest"], (3.5 + 4.0 * phase, 0, 0), f)
        if "hips" in bones:
            set_bone_location(bones["hips"], (0, 0, 0.000), f) # Fixed Z anchor guarantees 0.0px ground drift
            set_bone_rotation(bones["hips"], (0, 0, 1.8 * phase), f)
        if "head" in bones:
            set_bone_rotation(bones["head"], (0.5 * phase, 2.0 * phase, 0), f)

        # Left arm holding braced buckler
        if "upper_arm.L" in bones:
            set_bone_rotation(bones["upper_arm.L"], (22.0 + 2.0 * phase, 12.0, 18.0), f)
        if "forearm.L" in bones:
            set_bone_rotation(bones["forearm.L"], (65.0, 0, -25.0), f)

        # Right arm clenched fist at hip
        if "upper_arm.R" in bones:
            set_bone_rotation(bones["upper_arm.R"], (10.0 - 1.5 * phase, -10.0, -12.0), f)
        if "forearm.R" in bones:
            set_bone_rotation(bones["forearm.R"], (28.0, 0, 10.0), f)

def animate_gambler_idle(arm_obj: bpy.types.Object):
    """The Gambler Idle: Theatrical S-curve hip sway, hat tilt nod, card fan flourish in right hand."""
    action = bpy.data.actions.new(name="Gambler_Idle")
    arm_obj.animation_data_create()
    arm_obj.animation_data.action = action
    bones = arm_obj.pose.bones

    for f in range(1, 17):
        t = (f - 1) / 16.0
        phase = math.sin(t * 2 * math.pi)

        # S-curve hip & spine sway
        if "hips" in bones:
            set_bone_location(bones["hips"], (0.008 * phase, 0, 0.000), f) # Fixed Z anchor guarantees 0.0px ground drift
            set_bone_rotation(bones["hips"], (0, 0, 2.5 * phase), f)
        if "chest" in bones:
            set_bone_rotation(bones["chest"], (2.0 + 2.5 * phase, 0, -2.0 * phase), f)
        if "head" in bones:
            set_bone_rotation(bones["head"], (-2.0 + 1.5 * phase, 0, 2.5 * phase), f)

        # Right hand flourishing glowing cards at chest level
        if "upper_arm.R" in bones:
            set_bone_rotation(bones["upper_arm.R"], (20.0 + 3.0 * phase, -14.0, -20.0), f)
        if "forearm.R" in bones:
            set_bone_rotation(bones["forearm.R"], (40.0 + 4.0 * phase, 0, 20.0), f)
        if "hand.R" in bones:
            set_bone_rotation(bones["hand.R"], (5.0 * phase, 8.0 * phase, 0), f)

        # Left hand resting casually at side/vest
        if "upper_arm.L" in bones:
            set_bone_rotation(bones["upper_arm.L"], (-12.0 - 1.0 * phase, 12.0, 14.0), f)
        if "forearm.L" in bones:
            set_bone_rotation(bones["forearm.L"], (35.0, 0, -20.0), f)

        # Flared coat tails swaying
        if "coat_tail.L" in bones:
            set_bone_rotation(bones["coat_tail.L"], (-4.0 + 3.0 * phase, 0, 0), f)
        if "coat_tail.R" in bones:
            set_bone_rotation(bones["coat_tail.R"], (-4.0 - 3.0 * phase, 0, 0), f)

# =============================================================
# 2. 8-DIRECTION WALK CYCLES (8 Frames per Direction = 64 Frames)
# =============================================================
DIRECTION_YAW_DEG = {
    "S": 0.0,
    "SW": -45.0,
    "W": -90.0,
    "NW": -135.0,
    "N": 180.0,
    "NE": 135.0,
    "E": 90.0,
    "SE": 45.0
}

def animate_walk_cycle(arm_obj: bpy.types.Object, character_name: str, direction: str):
    """
    Authors an 8-frame walk cycle facing the specified direction with explicit 4-phase weighted kinetics:
    - F1: Contact (R forward, L back, pelvis Z=0, torso yaw=+12 deg)
    - F2: Down/Recoil (R planted with -28 deg knee compression, pelvis Z=-4px drop, pelvis sway X=-2.5px over planted foot)
    - F3: Passing (R supports straight, L bends -55 deg knee swinging forward, pelvis Z=+3px rise)
    - F4: Extension (L leg extends forward, preparing for strike)
    - F5: Contact (L forward, R back, pelvis Z=0, torso yaw=-12 deg)
    - F6: Down/Recoil (L planted with -28 deg knee compression, pelvis Z=-4px drop, pelvis sway X=+2.5px over planted foot)
    - F7: Passing (L supports straight, R bends -55 deg knee swinging forward, pelvis Z=+3px rise)
    - F8: Extension (R leg extends forward, preparing for strike)
    """
    yaw = DIRECTION_YAW_DEG.get(direction, 0.0)
    action = bpy.data.actions.new(name=f"{character_name}_Walk_{direction}")
    arm_obj.animation_data_create()
    arm_obj.animation_data.action = action
    bones = arm_obj.pose.bones

    # Kinetic tuning
    stride_angle = 32.0 if character_name == "celina" else 36.0
    arm_swing = 24.0 if character_name == "celina" else 30.0
    hip_drop = 0.046
    hip_rise = 0.028
    sway_x = 0.024
    torso_twist = 14.0

    # Keyframe lookup per frame (1-indexed, 8 frames)
    # [pelvis_x, pelvis_z, hip_yaw, chest_yaw, uleg_r, lleg_r, foot_r, uleg_l, lleg_l, foot_l, uarm_r, farm_r, uarm_l, farm_l, tail_l, tail_r]
    walk_keys = {
        1: ( 0.000,  0.000,   8.0, -torso_twist,  stride_angle,   -4.0,  18.0, -stride_angle,  -14.0, -22.0, -arm_swing,  25.0,  arm_swing,  45.0,  -14.0,   14.0), # R Contact / L Push-off
        2: (-sway_x, -hip_drop, 10.0, -torso_twist*0.8, stride_angle*0.6, -34.0,   0.0, -stride_angle*0.8, -40.0, -10.0, -arm_swing*0.6, 20.0, arm_swing*0.6, 40.0, -20.0, 20.0), # R Down Recoil (Planted)
        3: (-sway_x*0.4, hip_rise, 0.0, 0.0,      -4.0,   -2.0,   0.0,  stride_angle*0.3, -62.0,  10.0,   0.0,  30.0,   0.0,  35.0,    0.0,    0.0), # L Passing/Peak
        4: ( 0.000,  0.010,  -5.0,  torso_twist*0.5, -stride_angle*0.5, -10.0, -12.0, stride_angle*0.8, -12.0,  15.0,  arm_swing*0.5, 38.0, -arm_swing*0.5, 25.0, 10.0, -10.0), # L Extension
        5: ( 0.000,  0.000,  -8.0,  torso_twist, -stride_angle,  -14.0, -22.0,  stride_angle,   -4.0,  18.0,  arm_swing,  45.0, -arm_swing,  25.0,   14.0,  -14.0), # L Contact / R Push-off
        6: ( sway_x, -hip_drop, -10.0, torso_twist*0.8, -stride_angle*0.8, -40.0, -10.0, stride_angle*0.6, -34.0,   0.0, arm_swing*0.6, 40.0, -arm_swing*0.6, 20.0, 20.0, -20.0), # L Down Recoil (Planted)
        7: ( sway_x*0.4, hip_rise, 0.0, 0.0,       stride_angle*0.3, -62.0,  10.0,  -4.0,   -2.0,   0.0,   0.0,  35.0,   0.0,  30.0,    0.0,    0.0), # R Passing/Peak
        8: ( 0.000,  0.010,   5.0, -torso_twist*0.5, stride_angle*0.8, -12.0,  15.0, -stride_angle*0.5, -10.0, -12.0, -arm_swing*0.5, 25.0,  arm_swing*0.5, 38.0, -10.0, 10.0), # R Extension
    }

    for f in range(1, 9):
        px, pz, hy, cy, ur, lr, ftr, ul, ll, ftl, ar, fr, al, fl, tl, tr = walk_keys[f]

        # Root direction rotation
        arm_obj.rotation_euler = (0, 0, math.radians(yaw))
        arm_obj.keyframe_insert(data_path="rotation_euler", frame=f)

        # Hips weight transfer & counter-rotation
        if "hips" in bones:
            set_bone_location(bones["hips"], (px, 0, pz), f)
            set_bone_rotation(bones["hips"], (2.0, 0, hy), f)

        # Chest counter-rotation
        if "chest" in bones:
            set_bone_rotation(bones["chest"], (4.0, 0, cy), f)

        # Legs (Explicit contact, down recoil, passing knee flexion, foot roll)
        if "upper_leg.R" in bones:
            set_bone_rotation(bones["upper_leg.R"], (ur, 0, 0), f)
        if "lower_leg.R" in bones:
            set_bone_rotation(bones["lower_leg.R"], (lr, 0, 0), f)
        if "foot.R" in bones:
            set_bone_rotation(bones["foot.R"], (ftr, 0, 0), f)

        if "upper_leg.L" in bones:
            set_bone_rotation(bones["upper_leg.L"], (ul, 0, 0), f)
        if "lower_leg.L" in bones:
            set_bone_rotation(bones["lower_leg.L"], (ll, 0, 0), f)
        if "foot.L" in bones:
            set_bone_rotation(bones["foot.L"], (ftl, 0, 0), f)

        # Arms (Reciprocal counter-swing with sword balance)
        if "upper_arm.R" in bones:
            set_bone_rotation(bones["upper_arm.R"], (ar + 18.0, -14.0, -20.0), f)
        if "forearm.R" in bones:
            set_bone_rotation(bones["forearm.R"], (fr, 0, 18.0), f)

        if "upper_arm.L" in bones:
            set_bone_rotation(bones["upper_arm.L"], (al + 14.0, 12.0, 18.0), f)
        if "forearm.L" in bones:
            set_bone_rotation(bones["forearm.L"], (fl, 0, -14.0), f)

        # Secondary Coat Tail Momentum
        if "coat_tail.L" in bones:
            set_bone_rotation(bones["coat_tail.L"], (tl, 0, 0), f)
        if "coat_tail.R" in bones:
            set_bone_rotation(bones["coat_tail.R"], (tr, 0, 0), f)

# =============================================================
# 3. SIGNATURE GESTURES (24 Frames)
# =============================================================
def animate_celina_gesture(arm_obj: bpy.types.Object):
    """
    Celina Signature Gesture: 'The Duelist's Salute' (24 Frames)
    - F01-F04: Anticipation — Drops into deep en garde crouch (-5px hips), coils body away (-28 deg).
    - F05-F09: Action — Explosive fencing lunge (+4px forward drive) & horizontal flourish cut across chest.
    - F10-F14: Follow-through — Snaps blade straight up to chin in crisp vertical duelist salute with overshoot (+96 deg).
    - F15-F20: Held Pose — Dignified vertical salute held with proud chin elevation (-16 deg).
    - F21-F24: Settle — Smooth disciplined recovery to resting duelist guard.
    """
    action = bpy.data.actions.new(name="Celina_Gesture")
    arm_obj.animation_data_create()
    arm_obj.animation_data.action = action
    bones = arm_obj.pose.bones

    arm_obj.rotation_euler = (0, 0, 0)
    arm_obj.keyframe_insert(data_path="rotation_euler", frame=1)

    keyframes = {
        1:  {"chest": (6,0,-2.5),  "arm_r": (18,-14,-20), "farm_r": (45,0,18),  "hand_r": (15,0,-32), "arm_l": (14,16,22),  "farm_l": (36,0,-18), "head": (-4,0,2),   "hips_z": 0.000},
        4:  {"chest": (-16,0,-28), "arm_r": (8,-32,-45),  "farm_r": (92,0,30),  "hand_r": (25,0,-45), "arm_l": (28,24,38),  "farm_l": (60,0,-25), "head": (10,0,-14), "hips_z": -0.050}, # Deep Crouch & Coil
        8:  {"chest": (18,0,36),   "arm_r": (65,24,-55),  "farm_r": (12,0,10),  "hand_r": (0,0,-10),  "arm_l": (-26,18,-30), "farm_l": (15,0,0),   "head": (-10,0,18), "hips_z": 0.025},  # Explosive Lunge & Cut
        12: {"chest": (16,0,0),    "arm_r": (88,0,0),     "farm_r": (98,0,0),   "hand_r": (0,0,0),    "arm_l": (10,10,12),   "farm_l": (25,0,-10), "head": (-16,0,0), "hips_z": 0.015},  # Vertical Chin Salute
        17: {"chest": (16,0,0),    "arm_r": (88,0,0),     "farm_r": (98,0,0),   "hand_r": (0,0,0),    "arm_l": (10,10,12),   "farm_l": (25,0,-10), "head": (-16,0,0), "hips_z": 0.015},  # Held Salute
        24: {"chest": (6,0,-2.5),  "arm_r": (18,-14,-20), "farm_r": (45,0,18),  "hand_r": (15,0,-32), "arm_l": (14,16,22),  "farm_l": (36,0,-18), "head": (-4,0,2),   "hips_z": 0.000}   # Settle
    }

    _apply_gesture_keyframes(bones, keyframes, total_frames=24)

def animate_agnes_gesture(arm_obj: bpy.types.Object):
    """
    Agnes Signature Gesture (24 frames):
    Heavy Vanguard Warhammer Ground Slam & War Cry:
    - F01-F05: Anticipation — Deep wide crouch, raises heavy warhammer overhead +75 deg, draws buckler tight to chest
    - F06-F10: Earthshaking Ground Slam — Hips surge down, driving the massive warhammer down in a thunderous arc
    - F11-F16: Held Vanguard War-Cry Stance — Roars with chin high, hammer planted in ground, buckler flared forward
    - F17-F24: Weighted recovery back to grounded combat-ready vanguard stance
    """
    action = bpy.data.actions.new(name="Agnes_Gesture")
    arm_obj.animation_data_create()
    arm_obj.animation_data.action = action
    bones = arm_obj.pose.bones

    keyframes = {
        1:  {"chest": (0,0,0), "arm_r": (10,-10,-12), "farm_r": (28,0,10), "arm_l": (22,12,18), "farm_l": (65,0,-25), "head": (0,0,0), "hips_z": 0.0},
        5:  {"chest": (-14,0,18), "arm_r": (65,-20,-30), "farm_r": (45,0,15), "arm_l": (-15,20,25), "farm_l": (75,0,-35), "head": (10,0,-8), "hips_z": -0.050}, # Deep Crouch & Raise Hammer
        10: {"chest": (18,0,-20), "arm_r": (-35,-10,-15), "farm_r": (15,0,5), "arm_l": (35,10,40), "farm_l": (55,0,-20), "head": (-14,0,10), "hips_z": -0.020}, # Ground Slam Impact
        16: {"chest": (16,0,-10), "arm_r": (-30,-10,-15), "farm_r": (15,0,5), "arm_l": (30,10,40), "farm_l": (55,0,-20), "head": (-16,0,4), "hips_z": 0.000}, # Roar & Planted Pose
        24: {"chest": (0,0,0), "arm_r": (10,-10,-12), "farm_r": (28,0,10), "arm_l": (22,12,18), "farm_l": (65,0,-25), "head": (0,0,0), "hips_z": 0.0}  # Settle
    }

    _apply_gesture_keyframes(bones, keyframes, total_frames=24)

def animate_gambler_gesture(arm_obj: bpy.types.Object):
    """
    The Gambler Signature Gesture: 'The Card Trick & Theatrical Bow' (24 Frames)
    - F01-F06: Anticipation — Theatrical bow with left hand on hat brim.
    - F07-F14: Action — Snaps right wrist, spreads a glowing fan of 3 cards in an arc.
    - F15-F19: Follow-through — Spins card in fingers, tosses and catches it.
    - F20-F24: Settle — Smug hat tip and settle with a grin.
    """
    action = bpy.data.actions.new(name="Gambler_Gesture")
    arm_obj.animation_data_create()
    arm_obj.animation_data.action = action
    bones = arm_obj.pose.bones

    keyframes = {
        1:  {"chest": (0,0,0), "arm_r": (20,-10,-15), "farm_r": (40,0,20), "arm_l": (15,10,10), "farm_l": (30,0,-15), "head": (0,0,0), "hips_z": 0.0},
        6:  {"chest": (18,0,0), "arm_r": (-10,0,-10), "farm_r": (20,0,10), "arm_l": (65,15,-20), "farm_l": (90,0,-10), "head": (15,0,0), "hips_z": -0.02}, # Bow & Hat Tip
        12: {"chest": (-6,0,10), "arm_r": (45,20,35), "farm_r": (75,0,30), "arm_l": (20,10,10), "farm_l": (40,0,-10), "head": (-8,0,-5), "hips_z": 0.01}, # Card Arc Flourish
        17: {"chest": (-2,0,5), "arm_r": (65,10,15), "farm_r": (85,0,10), "arm_l": (15,10,10), "farm_l": (30,0,-15), "head": (-4,0,5), "hips_z": 0.0},  # Card Toss/Spin
        24: {"chest": (0,0,0), "arm_r": (20,-10,-15), "farm_r": (40,0,20), "arm_l": (15,10,10), "farm_l": (30,0,-15), "head": (0,0,0), "hips_z": 0.0}
    }

    _apply_gesture_keyframes(bones, keyframes, total_frames=24)

def _apply_gesture_keyframes(bones, keyframes: dict, total_frames: int = 24):
    """Interpolates and applies gesture keyframes across the sequence."""
    sorted_kf = sorted(keyframes.keys())
    for f in range(1, total_frames + 1):
        # Find bracketing keyframes
        prev_k = sorted_kf[0]
        next_k = sorted_kf[-1]
        for k in sorted_kf:
            if k <= f:
                prev_k = k
            if k >= f:
                next_k = k
                break
        
        factor = (f - prev_k) / float(next_k - prev_k) if next_k > prev_k else 0.0
        # Smooth cosine interpolation
        blend = 0.5 * (1.0 - math.cos(factor * math.pi))

        d_prev = keyframes[prev_k]
        d_next = keyframes[next_k]

        def lerp_tuple(k_name):
            v1 = d_prev.get(k_name, (0,0,0))
            v2 = d_next.get(k_name, (0,0,0))
            return (
                v1[0] + (v2[0] - v1[0]) * blend,
                v1[1] + (v2[1] - v1[1]) * blend,
                v1[2] + (v2[2] - v1[2]) * blend
            )

        if "chest" in bones:
            set_bone_rotation(bones["chest"], lerp_tuple("chest"), f)
        if "head" in bones:
            set_bone_rotation(bones["head"], lerp_tuple("head"), f)
        if "upper_arm.R" in bones:
            set_bone_rotation(bones["upper_arm.R"], lerp_tuple("arm_r"), f)
        if "forearm.R" in bones:
            set_bone_rotation(bones["forearm.R"], lerp_tuple("farm_r"), f)
        if "upper_arm.L" in bones:
            set_bone_rotation(bones["upper_arm.L"], lerp_tuple("arm_l"), f)
        if "forearm.L" in bones:
            set_bone_rotation(bones["forearm.L"], lerp_tuple("farm_l"), f)

        if "hips" in bones and ("hips_z" in d_prev or "hips_z" in d_next):
            z1 = d_prev.get("hips_z", 0.0)
            z2 = d_next.get("hips_z", 0.0)
            cur_z = z1 + (z2 - z1) * blend
            set_bone_location(bones["hips"], (0, 0, cur_z), f)
