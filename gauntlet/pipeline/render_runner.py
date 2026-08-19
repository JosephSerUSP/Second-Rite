# gauntlet/pipeline/render_runner.py
# Headless Blender render runner script for Celina, Agnes, and The Gambler

import sys
import os
import argparse
import math

# Ensure repository root is on sys.path
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

import bpy
from gauntlet.pipeline.camera_rig import setup_drpg_camera, setup_drpg_lighting
from gauntlet.pipeline.character_builder import build_celina, build_agnes, build_gambler
from gauntlet.pipeline.animator import (
    author_celina_idle, author_agnes_idle, author_gambler_idle,
    author_walk_cycle,
    author_celina_gesture, author_agnes_gesture, author_gambler_gesture
)

def parse_args():
    # Blender passes arguments after '--'
    argv = sys.argv
    if "--" in argv:
        args_to_parse = argv[argv.index("--") + 1:]
    else:
        args_to_parse = []

    parser = argparse.ArgumentParser(description="DRPG Sprite Render Runner")
    parser.add_argument("--character", required=True, choices=["celina", "agnes", "gambler"])
    parser.add_argument("--action", default="all", choices=["all", "static", "idle", "walk", "gesture"])
    parser.add_argument("--output-dir", required=True, help="Destination directory for rendered frames")
    parser.add_argument("--blend-out", default=None, help="Optional path to save .blend file")
    return parser.parse_args(args_to_parse)

def render_frame_to_file(filepath: str):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    bpy.context.scene.render.filepath = filepath
    bpy.ops.render.render(write_still=True)

def main():
    args = parse_args()
    char_name = args.character.lower()
    action = args.action
    out_dir = os.path.abspath(args.output_dir)

    print(f"=== [RenderRunner] Starting: {char_name.upper()} | Action: {action} ===")

    # 1. Reset factory settings
    bpy.ops.wm.read_factory_settings(use_empty=True)

    # 2. Camera & Lighting Rig
    setup_drpg_camera()
    setup_drpg_lighting()

    # 3. Build Character
    if char_name == "celina":
        arm_obj, parts = build_celina()
    elif char_name == "agnes":
        arm_obj, parts = build_agnes()
    elif char_name == "gambler":
        arm_obj, parts = build_gambler()
    else:
        raise ValueError(f"Unknown character: {char_name}")

    # Set render engine
    bpy.context.scene.render.engine = 'BLENDER_EEVEE'

    # Base front facing rotation: Model geometry is authored along +Y, so 180 deg faces the camera at -Y
    FRONT_FACING_ROT = math.radians(180)

    # 4. Execute Renders
    # A. Static Render
    if action in ["all", "static"]:
        print("Rendering static front frame (Facing Camera)...")
        if char_name == "celina":
            author_celina_idle(arm_obj)
        elif char_name == "agnes":
            author_agnes_idle(arm_obj)
        elif char_name == "gambler":
            author_gambler_idle(arm_obj)

        arm_obj.rotation_euler = (0, 0, FRONT_FACING_ROT)
        bpy.context.scene.frame_set(1)
        static_path = os.path.join(out_dir, "static_front.png")
        render_frame_to_file(static_path)
        print(f"-> Saved: {static_path}")

    # B. Idle Animation (16 frames)
    if action in ["all", "idle"]:
        print("Rendering canonical Front Idle animation (16 frames)...")
        if char_name == "celina":
            author_celina_idle(arm_obj)
        elif char_name == "agnes":
            author_agnes_idle(arm_obj)
        elif char_name == "gambler":
            author_gambler_idle(arm_obj)

        arm_obj.rotation_euler = (0, 0, FRONT_FACING_ROT)
        idle_dir = os.path.join(out_dir, "idle")
        for f in range(1, 17):
            bpy.context.scene.frame_set(f)
            fpath = os.path.join(idle_dir, f"idle_{f:02d}.png")
            render_frame_to_file(fpath)
        print(f"-> Saved 16 idle frames in {idle_dir}")

    # C. Walk Cycles (8 Directions x 8 Frames = 64 frames)
    if action in ["all", "walk"]:
        print("Rendering 8-Direction Walk locomotion (64 frames)...")
        # Rotations relative to camera (S = 180 facing camera, N = 0 facing away, W = 270 facing left, E = 90 facing right)
        walk_dirs = [
            ("S", 180.0),
            ("SW", 225.0),
            ("W", 270.0),
            ("NW", 315.0),
            ("N", 0.0),
            ("NE", 45.0),
            ("E", 90.0),
            ("SE", 135.0)
        ]

        for dname, deg in walk_dirs:
            print(f"  Rendering Walk Direction {dname} ({deg} deg)...")
            dir_dir = os.path.join(out_dir, "walk", dname)
            author_walk_cycle(arm_obj, char_type=char_name)

            # Rotate root / armature facing
            arm_obj.rotation_euler = (0, 0, math.radians(deg))

            for f in range(1, 9):
                bpy.context.scene.frame_set(f)
                fpath = os.path.join(dir_dir, f"walk_{dname}_{f:02d}.png")
                render_frame_to_file(fpath)

        # Reset armature rotation to front
        arm_obj.rotation_euler = (0, 0, FRONT_FACING_ROT)
        print(f"-> Saved all 64 walk frames in {os.path.join(out_dir, 'walk')}")

    # D. Signature Gesture (24 frames)
    if action in ["all", "gesture"]:
        print("Rendering Signature Gesture (24 frames, Facing Camera)...")
        if char_name == "celina":
            author_celina_gesture(arm_obj)
        elif char_name == "agnes":
            author_agnes_gesture(arm_obj)
        elif char_name == "gambler":
            author_gambler_gesture(arm_obj)

        arm_obj.rotation_euler = (0, 0, FRONT_FACING_ROT)
        gesture_dir = os.path.join(out_dir, "gesture")
        for f in range(1, 25):
            bpy.context.scene.frame_set(f)
            fpath = os.path.join(gesture_dir, f"gesture_{f:02d}.png")
            render_frame_to_file(fpath)
        print(f"-> Saved 24 gesture frames in {gesture_dir}")

    # 5. Save .blend file if requested
    if args.blend_out:
        blend_path = os.path.abspath(args.blend_out)
        os.makedirs(os.path.dirname(blend_path), exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=blend_path)
        print(f"-> Saved Blender project: {blend_path}")

    print(f"=== [RenderRunner] Successfully Completed {char_name.upper()} ===")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        traceback.print_exc()
        sys.exit(1)
