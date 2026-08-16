"""Blender script to execute all modeling, posing, rendering and .blend saving for the gauntlet.
Invoked via: blender.exe -b -P render_all_stages.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add script directory to sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parents[2]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import character_builder as cb

AUTHORING_DIR = ROOT / "assets" / "authoring" / "characters"
EXPERIMENT_DIR = ROOT / "experiments" / "frontview-town-character-gauntlet"
RAW_DIR = EXPERIMENT_DIR / "renders" / "raw_blender_passes"


def run():
    AUTHORING_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    print("=== GAUNTLET PIPELINE: BLENDER AUTHORING & RENDERING ===")

    # 1. Registrar Celina Poses
    print("Authoring Registrar Celina...")
    for pose in ["idle", "request_seal", "dry_warning"]:
        cb.build_registrar_celina(pose=pose)
        if pose == "idle":
            cb.save_blend_file(AUTHORING_DIR / "registrar_celina.blend")
        cb.render_scene_to_file(RAW_DIR / f"celina_{pose}_raw256.png", resolution=256)
        cb.render_scene_to_file(RAW_DIR / f"celina_{pose}_raw128.png", resolution=128)
        cb.render_scene_to_file(RAW_DIR / f"celina_{pose}_raw512.png", resolution=512)

    # 2. Sister Agnes Poses
    print("Authoring Sister Agnes...")
    for pose in ["idle_working", "brush_dust", "quiet_welcome"]:
        cb.build_sister_agnes(pose=pose)
        if pose == "idle_working":
            cb.save_blend_file(AUTHORING_DIR / "sister_agnes.blend")
        cb.render_scene_to_file(RAW_DIR / f"agnes_{pose}_raw256.png", resolution=256)
        cb.render_scene_to_file(RAW_DIR / f"agnes_{pose}_raw128.png", resolution=128)
        cb.render_scene_to_file(RAW_DIR / f"agnes_{pose}_raw512.png", resolution=512)

    # 3. The Gambler Concepts
    print("Authoring The Gambler Concept 1 (Local Regular)...")
    cb.build_gambler_concept_1(pose="idle")
    cb.save_blend_file(AUTHORING_DIR / "the_gambler_c1_local.blend")
    cb.render_scene_to_file(RAW_DIR / "gambler_c1_local_raw256.png", resolution=256)

    print("Authoring The Gambler Concept 2 (Wiry Counter)...")
    cb.build_gambler_concept_2(pose="idle")
    cb.save_blend_file(AUTHORING_DIR / "the_gambler_c2_wiry.blend")
    cb.save_blend_file(AUTHORING_DIR / "the_gambler.blend") # Champion design
    cb.render_scene_to_file(RAW_DIR / "gambler_c2_wiry_raw256.png", resolution=256)

    print("Authoring The Gambler Concept 3 (Sleight-of-Hand Deceiver)...")
    cb.build_gambler_concept_3(pose="idle")
    cb.save_blend_file(AUTHORING_DIR / "the_gambler_c3_sleight.blend")
    cb.render_scene_to_file(RAW_DIR / "gambler_c3_sleight_raw256.png", resolution=256)

    # 4. Champion Gambler (Concept 2) Poses
    print("Authoring Champion Gambler Poses...")
    for pose in ["idle", "offer_game", "win_or_reveal"]:
        cb.build_gambler_concept_2(pose=pose)
        cb.render_scene_to_file(RAW_DIR / f"gambler_{pose}_raw256.png", resolution=256)
        cb.render_scene_to_file(RAW_DIR / f"gambler_{pose}_raw128.png", resolution=128)
        cb.render_scene_to_file(RAW_DIR / f"gambler_{pose}_raw512.png", resolution=512)

    # 5. Motion / Animation Frame Sequences
    print("Authoring Gesture Motion Keyframes...")

    # Celina request_seal animation frames (5 frames: idle -> reach_start -> reach_mid -> hold_seal -> return)
    # We interpolate arm and torso positions
    for f_idx in range(6):
        # f0: idle, f1: lift, f2: extend, f3: hold_open, f4: hold_open, f5: settle
        if f_idx == 0:
            cb.build_registrar_celina(pose="idle")
        elif f_idx in (1, 5):
            cb.build_registrar_celina(pose="dry_warning") # intermediate height
        else:
            cb.build_registrar_celina(pose="request_seal")
        cb.render_scene_to_file(RAW_DIR / f"anim_celina_frame_{f_idx}.png", resolution=256)

    # Agnes brush_dust animation frames (6 frames)
    for f_idx in range(6):
        if f_idx in (0, 5):
            cb.build_sister_agnes(pose="idle_working")
        elif f_idx in (1, 4):
            cb.build_sister_agnes(pose="quiet_welcome")
        else:
            cb.build_sister_agnes(pose="brush_dust")
        cb.render_scene_to_file(RAW_DIR / f"anim_agnes_frame_{f_idx}.png", resolution=256)

    # Gambler offer_game animation frames (6 frames)
    for f_idx in range(6):
        if f_idx in (0, 5):
            cb.build_gambler_concept_2(pose="idle")
        elif f_idx in (1, 4):
            cb.build_gambler_concept_2(pose="win_or_reveal")
        else:
            cb.build_gambler_concept_2(pose="offer_game")
        cb.render_scene_to_file(RAW_DIR / f"anim_gambler_frame_{f_idx}.png", resolution=256)

    print("=== BLENDER RENDERING COMPLETE ===")


if __name__ == "__main__":
    run()
