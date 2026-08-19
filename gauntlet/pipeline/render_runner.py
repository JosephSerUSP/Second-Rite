# gauntlet/pipeline/render_runner.py
# Blender headless runner script to build, animate, and render characters

import sys
import os
import argparse
import bpy

# Add repository root and gauntlet to sys.path
script_dir = os.path.dirname(os.path.abspath(__file__))
repo_root = os.path.abspath(os.path.join(script_dir, "..", ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from gauntlet.pipeline.camera_rig import setup_drpg_camera, setup_drpg_lighting
from gauntlet.pipeline.mesh_generator import build_celina, build_agnes, build_gambler
from gauntlet.pipeline.animator import (
    animate_celina_idle, animate_agnes_idle, animate_gambler_idle,
    animate_walk_cycle,
    animate_celina_gesture, animate_agnes_gesture, animate_gambler_gesture
)

def clear_scene():
    """Removes all objects, meshes, materials, and armatures."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for block in bpy.data.meshes:
        bpy.data.meshes.remove(block)
    for block in bpy.data.materials:
        bpy.data.materials.remove(block)
    for block in bpy.data.armatures:
        bpy.data.armatures.remove(block)
    for block in bpy.data.actions:
        bpy.data.actions.remove(block)

def render_frame(output_path: str, stabilize_anchor: bool = True):
    """Renders the current frame and applies automatic 176px ground-anchor alignment."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    bpy.context.scene.render.filepath = output_path
    bpy.ops.render.render(write_still=True)
    
    if stabilize_anchor and os.path.exists(output_path):
        try:
            from PIL import Image
            import numpy as np
            with Image.open(output_path) as im:
                img = im.convert("RGBA")
            arr = np.array(img)
            alpha = arr[:, :, 3]
            mask = alpha > 40
            if np.any(mask):
                y_indices, _ = np.where(mask)
                max_y = int(np.max(y_indices))
                shift_y = 176 - max_y
                if shift_y != 0 and abs(shift_y) <= 8:
                    shifted = np.zeros_like(arr)
                    if shift_y > 0:
                        shifted[shift_y:, :, :] = arr[:-shift_y, :, :]
                    else:
                        shifted[:shift_y, :, :] = arr[-shift_y:, :, :]
                    out_im = Image.fromarray(shifted, "RGBA")
                    out_im.save(output_path)
        except Exception as e:
            print(f"[RenderRunner] Warning: Anchor stabilization skipped: {e}")

def main():
    # Parse CLI args after '--'
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []

    parser = argparse.ArgumentParser(description="DRPG Character Render Runner")
    parser.add_argument("--character", type=str, required=True, choices=["celina", "agnes", "gambler"])
    parser.add_argument("--action", type=str, default="all", choices=["static", "idle", "walk", "gesture", "all"])
    parser.add_argument("--output-dir", type=str, required=True)
    parser.add_argument("--blend-out", type=str, default=None)
    args = parser.parse_args(argv)
    args.output_dir = os.path.abspath(args.output_dir)
    if args.blend_out:
        args.blend_out = os.path.abspath(args.blend_out)

    print(f"[RenderRunner] Initializing render for {args.character} (Action: {args.action})")
    clear_scene()

    # 1. Setup Camera and Lighting
    setup_drpg_camera()
    setup_drpg_lighting()

    # 2. Build Character 3D Model
    if args.character == "celina":
        arm_obj, parts = build_celina()
    elif args.character == "agnes":
        arm_obj, parts = build_agnes()
    elif args.character == "gambler":
        arm_obj, parts = build_gambler()
    else:
        raise ValueError(f"Unknown character {args.character}")

    os.makedirs(args.output_dir, exist_ok=True)

    # 3. Render Static Front Pose
    if args.action in ["static", "all"]:
        print("[RenderRunner] Rendering static front view...")
        if args.character == "celina":
            animate_celina_idle(arm_obj)
        elif args.character == "agnes":
            animate_agnes_idle(arm_obj)
        else:
            animate_gambler_idle(arm_obj)
        
        bpy.context.scene.frame_set(1)
        bpy.context.view_layer.update()
        render_frame(os.path.join(args.output_dir, "static_front.png"))

    # 4. Render Idle Animation (16 Frames)
    if args.action in ["idle", "all"]:
        print("[RenderRunner] Rendering 16-frame idle animation...")
        if args.character == "celina":
            animate_celina_idle(arm_obj)
        elif args.character == "agnes":
            animate_agnes_idle(arm_obj)
        else:
            animate_gambler_idle(arm_obj)

        idle_dir = os.path.join(args.output_dir, "idle")
        for f in range(1, 17):
            bpy.context.scene.frame_set(f)
            render_frame(os.path.join(idle_dir, f"idle_{f:02d}.png"))

    # 5. Render 8-Direction Walk Cycles (64 Frames Total)
    if args.action in ["walk", "all"]:
        print("[RenderRunner] Rendering 8-direction walk cycles (64 frames)...")
        walk_dirs = ["S", "SW", "W", "NW", "N", "NE", "E", "SE"]
        for d in walk_dirs:
            animate_walk_cycle(arm_obj, args.character, d)
            dir_dir = os.path.join(args.output_dir, "walk", d)
            for f in range(1, 9):
                bpy.context.scene.frame_set(f)
                render_frame(os.path.join(dir_dir, f"walk_{f:02d}.png"))

    # 6. Render Signature Gesture (24 Frames)
    if args.action in ["gesture", "all"]:
        print("[RenderRunner] Rendering 24-frame signature gesture...")
        if args.character == "celina":
            animate_celina_gesture(arm_obj)
        elif args.character == "agnes":
            animate_agnes_gesture(arm_obj)
        else:
            animate_gambler_gesture(arm_obj)

        gesture_dir = os.path.join(args.output_dir, "gesture")
        for f in range(1, 25):
            bpy.context.scene.frame_set(f)
            render_frame(os.path.join(gesture_dir, f"gesture_{f:02d}.png"))

    # 7. Save .blend file if requested
    if args.blend_out:
        os.makedirs(os.path.dirname(args.blend_out), exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=args.blend_out)
        print(f"[RenderRunner] Saved Blender source file to {args.blend_out}")

    print("[RenderRunner] All render operations completed successfully.")

if __name__ == "__main__":
    main()
