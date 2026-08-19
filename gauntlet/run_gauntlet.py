# gauntlet/run_gauntlet.py
# Adversarial Gauntlet Automation Driver for Second Gate

import os
import sys
import json
import glob
import subprocess
from typing import Dict, Any, List, Optional

# Enforce UTF-8 encoding for console output on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

from gauntlet.pipeline.technical_validator import validate_character_sprites
from gauntlet.pipeline.sprite_processor import measure_sprite_metrics
from gauntlet.evaluator.contact_sheets import (
    create_static_sheet,
    create_animation_strip,
    create_locomotion_grid,
    create_lineup_sheet
)
from gauntlet.evaluator.luna_harness import LunaHarness

BLENDER_EXE = r"C:\Program Files\Blender Foundation\Blender 4.1\blender.exe"
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def run_blender_render(character: str, action: str, output_dir: str, blend_out: Optional[str] = None):
    """Executes Blender in headless background mode."""
    cmd = [
        BLENDER_EXE,
        "--factory-startup",
        "-b",
        "--python", os.path.join(REPO_ROOT, "gauntlet", "pipeline", "render_runner.py"),
        "--",
        "--character", character,
        "--action", action,
        "--output-dir", output_dir
    ]
    if blend_out:
        cmd.extend(["--blend-out", blend_out])

    print(f"[Blender] Invoking: {' '.join(cmd)}")
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO_ROOT)
    if res.returncode != 0:
        print("[Blender Error Output]:", res.stderr)
        print("[Blender Standard Output]:", res.stdout)
        raise RuntimeError(f"Blender render failed with code {res.returncode}")
    print("[Blender] Render completed successfully.")

def build_character_contact_sheets(char_name: str, round_dir: str) -> Dict[str, str]:
    """Generates all diagnostic contact sheets and animated previews for a round."""
    sheets = {}

    # 1. Static Sheet
    static_file = os.path.join(round_dir, "static_front.png")
    if os.path.exists(static_file):
        from PIL import Image
        im = Image.open(static_file)
        metrics = measure_sprite_metrics(im)
        sheet_path = os.path.join(round_dir, "sheets", f"{char_name}_static_inspection.png")
        create_static_sheet(
            static_file,
            sheet_path,
            title=f"{char_name.upper()} — Static Inspection & Anchor Guide",
            standing_height_px=metrics.get("standing_height")
        )
        sheets["static_inspection"] = sheet_path

    # 2. Idle Animation Strip & GIF
    idle_files = sorted(glob.glob(os.path.join(round_dir, "idle", "*.png")))
    if idle_files:
        strip_path = os.path.join(round_dir, "sheets", f"{char_name}_idle_strip.png")
        create_animation_strip(
            idle_files,
            strip_path,
            title=f"{char_name.upper()} — Canonical Front Idle",
            fps=8,
            make_gif=True
        )
        sheets["idle_strip"] = strip_path
        sheets["idle_gif"] = os.path.splitext(strip_path)[0] + ".gif"

    # 3. 8-Direction Locomotion Grid
    walk_dirs = ["S", "SW", "W", "NW", "N", "NE", "E", "SE"]
    dir_map = {}
    for d in walk_dirs:
        dfiles = sorted(glob.glob(os.path.join(round_dir, "walk", d, "*.png")))
        if dfiles:
            dir_map[d] = dfiles
    if len(dir_map) == 8:
        grid_path = os.path.join(round_dir, "sheets", f"{char_name}_locomotion_grid.png")
        create_locomotion_grid(
            dir_map,
            grid_path,
            title=f"{char_name.upper()} — 8-Direction Locomotion Overview (64 Frames)"
        )
        sheets["locomotion_grid"] = grid_path

    # 4. Signature Gesture Strip & GIF
    gesture_files = sorted(glob.glob(os.path.join(round_dir, "gesture", "*.png")))
    if gesture_files:
        strip_path = os.path.join(round_dir, "sheets", f"{char_name}_gesture_strip.png")
        create_animation_strip(
            gesture_files,
            strip_path,
            title=f"{char_name.upper()} — Signature Gesture",
            fps=10,
            make_gif=True
        )
        sheets["gesture_strip"] = strip_path
        sheets["gesture_gif"] = os.path.splitext(strip_path)[0] + ".gif"

    return sheets

def run_character_gauntlet_round(
    char_name: str,
    round_idx: int,
    comparison_chars: Optional[List[dict]] = None
) -> Dict[str, Any]:
    """
    Executes a complete iteration round:
    1. Render 3D model & animations in Blender.
    2. Run technical validator assertions.
    3. Generate contact sheets and GIFs.
    4. Submit package to gpt-5.6-luna for adversarial critique.
    5. Save results to JSON log.
    """
    round_name = f"round-{round_idx:02d}"
    round_dir = os.path.join(REPO_ROOT, "gauntlet", "characters", char_name, round_name)
    blend_out = os.path.join(round_dir, f"{char_name}_{round_name}.blend")

    print(f"\n========================================================")
    print(f"  EXECUTING GAUNTLET: {char_name.upper()} | {round_name.upper()}")
    print(f"========================================================")

    # 1. Render in Blender
    run_blender_render(char_name, "all", round_dir, blend_out=blend_out)

    # 2. Technical Validation
    tech_val = validate_character_sprites(round_dir)
    print(f"[TechValidation] Result: {tech_val}")
    if not tech_val["valid"]:
        print(f"[TechValidation] ERRORS: {tech_val['errors']}")

    # 3. Generate Contact Sheets
    sheets = build_character_contact_sheets(char_name, round_dir)
    print(f"[ContactSheets] Generated: {list(sheets.keys())}")

    # Build evaluation package for Luna
    eval_images = []
    if "static_inspection" in sheets:
        eval_images.append({
            "label": f"{char_name.upper()} Static Inspection (Native 1x Dark, Native 1x Light, Pure Silhouette Mask, 4x Nearest-Neighbor)",
            "path": sheets["static_inspection"]
        })
    if "idle_strip" in sheets:
        eval_images.append({
            "label": f"{char_name.upper()} Canonical Idle Strip (16 Frames)",
            "path": sheets["idle_strip"]
        })
    if "locomotion_grid" in sheets:
        eval_images.append({
            "label": f"{char_name.upper()} 8-Direction Locomotion Grid (64 Frames)",
            "path": sheets["locomotion_grid"]
        })
    if "gesture_strip" in sheets:
        eval_images.append({
            "label": f"{char_name.upper()} Signature Gesture Strip (24 Frames)",
            "path": sheets["gesture_strip"]
        })

    # If comparison characters exist, create and attach comparison lineup sheet
    if comparison_chars:
        current_static = os.path.join(round_dir, "static_front.png")
        lineup_list = comparison_chars + [{"name": char_name.capitalize(), "path": current_static, "height": tech_val.get("avg_idle_height")}]
        lineup_path = os.path.join(round_dir, "sheets", f"comparison_lineup_{char_name}.png")
        create_lineup_sheet(lineup_list, lineup_path, title=f"Cross-Character Lineup & Silhouette Comparison ({char_name.upper()})")
        eval_images.append({
            "label": f"Lineup Comparison against Prior Accepted Characters",
            "path": lineup_path
        })

    context_prompt = (
        f"Evaluating candidate: {char_name.upper()}.\n"
        f"Technical Validation Status: {'PASSED' if tech_val['valid'] else 'FAILED'}\n"
        f"Measured Standing Height: {tech_val.get('avg_idle_height')}px (limit <= 128px)\n"
        f"Ground Anchor Drift: {tech_val.get('anchor_drift_px')}px\n"
        f"Total Sprite Frames Rendered: {tech_val.get('total_frames')}\n\n"
        f"Character Archetype & Intent:\n"
    )
    if char_name == "celina":
        context_prompt += "Celina is vertical, contained, deliberate, 5.5 heads tall. Midnight navy/obsidian palette, high collar, corset, brass trim, slender rapier. Controlled, restrained motion.\n"
    elif char_name == "agnes":
        context_prompt += "Agnes is grounded, broad, physical, 5.0 heads tall. Earthy ochre/rust canvas, asymmetric bronze pauldron, heavy vambraces, buckler. Solid weight transfer and heavy impacts.\n"
    elif char_name == "gambler":
        context_prompt += "The Gambler is theatrical, dynamic broken diagonals, 5.2 heads tall. Emerald duster, crimson velvet vest, tilted fedora with violet ribbon, card/coin flourish. Slippery, jaunty kinetic rhythm.\n"

    if comparison_chars:
        context_prompt += "CRITICAL COMPARATIVE CHECK: Compare this character against the previously accepted roster. Identify any body-type, silhouette, or palette convergence.\n"

    # 4. Submit to Luna
    harness = LunaHarness()
    print("[LunaHarness] Submitting evaluation package to gpt-5.6-luna...")
    luna_result = harness.evaluate_round(
        character_name=char_name,
        round_name=round_name,
        image_paths=eval_images,
        context_prompt=context_prompt,
        is_ensemble=False
    )

    # Combine report
    report = {
        "character": char_name,
        "round": round_idx,
        "round_name": round_name,
        "technical_validation": tech_val,
        "sheets": sheets,
        "luna_evaluation": luna_result
    }

    # Save report to round dir
    report_file = os.path.join(round_dir, "evaluation_report.json")
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n[Luna Verdict]: {luna_result.get('verdict')}")
    print(f"[Luna Avg Score]: {luna_result.get('computed_average')} / 10.0 (Min: {luna_result.get('computed_min')})")
    print(f"[Luna Blockers]: {luna_result.get('blockers')}")
    print(f"[Luna High Value Changes]: {luna_result.get('high_value_changes')}")
    print(f"[Luna Next Step]: {luna_result.get('single_most_important_next_change')}")

    return report

def run_ensemble_gauntlet_round(round_idx: int) -> Dict[str, Any]:
    """
    Phase 5: Multi-Character Ensemble Gauntlet Round.
    Evaluates Celina, Agnes, and The Gambler across 6 comparative contact sheets.
    """
    from gauntlet.evaluator.ensemble_builder import generate_ensemble_sheets
    
    round_name = f"ensemble-round-{round_idx:02d}"
    round_dir = os.path.join(REPO_ROOT, "gauntlet", "ensemble", round_name)
    os.makedirs(round_dir, exist_ok=True)
    
    print("\n" + "=" * 56)
    print(f"  EXECUTING PHASE 5 ENSEMBLE GAUNTLET: ROUND-{round_idx:02d}")
    print("=" * 56)
    
    # 1. Generate Ensemble Comparative Sheets
    print("[EnsembleBuilder] Generating multi-character comparative lineup sheets...")
    sheets = generate_ensemble_sheets(round_dir)
    print(f"[EnsembleBuilder] Generated sheets: {list(sheets.keys())}")
    
    eval_images = [
        {"label": "Ensemble Static Lineup", "path": sheets["static_lineup"]},
        {"label": "Ensemble Silhouette Lineup", "path": sheets["silhouette_lineup"]},
        {"label": "Ensemble Idle Synchronized Strip", "path": sheets["idle_strip"]},
        {"label": "Ensemble Locomotion Style Grid", "path": sheets["locomotion_grid"]},
        {"label": "Ensemble Signature Gesture Flourish Strip", "path": sheets["gesture_strip"]},
        {"label": "Ensemble Native 1x vs 2x Pixel Inspection", "path": sheets["pixel_inspection"]}
    ]
    
    context_prompt = (
        "PHASE 5: MULTI-CHARACTER ENSEMBLE EVALUATION\n"
        "Evaluate the complete three-character DRPG cast: Celina (Slender Duelist), Agnes (Grounded Heavy Fighter), "
        "and The Gambler (Theatrical Showman Rogue).\n\n"
        "Inspect across all six core criteria:\n"
        "1. Silhouette distinctness (slender vs grounded vs broken-diagonal)\n"
        "2. Height and scale budget hierarchy (all <=128px, fixed anchor at 96,176)\n"
        "3. Palette independence (Midnight Navy/Gold vs Rust/Bronze/Steel vs Emerald/Crimson/Ivory)\n"
        "4. Idle rhythm & breathing independence\n"
        "5. Locomotion style divergence (clean fencing march vs heavy combat stomp vs jaunty slippery strut)\n"
        "6. Signature gesture clash and silhouette expansion at 1x.\n"
    )
    
    # 2. Submit to Luna
    harness = LunaHarness()
    print("[LunaHarness] Submitting ensemble evaluation package to gpt-5.6-luna...")
    luna_result = harness.evaluate_round(
        character_name="Ensemble (Celina, Agnes, The Gambler)",
        round_name=round_name,
        image_paths=eval_images,
        context_prompt=context_prompt,
        is_ensemble=True
    )
    
    report = {
        "round": round_idx,
        "round_name": round_name,
        "sheets": sheets,
        "luna_evaluation": luna_result
    }
    
    report_file = os.path.join(round_dir, "evaluation_report.json")
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)
        
    print(f"\n[Luna Ensemble Verdict]: {luna_result.get('verdict')}")
    print(f"[Luna Ensemble Avg Score]: {luna_result.get('computed_average')} / 10.0 (Min: {luna_result.get('computed_min')})")
    print(f"[Luna Ensemble Blockers]: {luna_result.get('blockers')}")
    print(f"[Luna Ensemble High Value Changes]: {luna_result.get('high_value_changes')}")
    print(f"[Luna Ensemble Next Step]: {luna_result.get('single_most_important_next_change')}")
    
    return report
