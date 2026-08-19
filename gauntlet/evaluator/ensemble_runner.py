# gauntlet/evaluator/ensemble_runner.py
# Master Ensemble Evaluator & Final Contact Sheet Generator for Second Gate Trio

import os
import sys
import json
import glob
from typing import Dict, Any, List
from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from gauntlet.evaluator.contact_sheets import draw_checkerboard, get_font
from gauntlet.evaluator.luna_harness import LunaHarness

def generate_ensemble_sheets(output_dir: str) -> Dict[str, str]:
    """Generates the 6 required final ensemble comparison sheets across Celina, Agnes, and The Gambler."""
    os.makedirs(output_dir, exist_ok=True)
    
    # Locate latest valid round for each character
    char_rounds = {
        "celina": os.path.join(REPO_ROOT, "gauntlet", "characters", "celina", "round-24"),
        "agnes": os.path.join(REPO_ROOT, "gauntlet", "characters", "agnes", "round-04"),
        "gambler": os.path.join(REPO_ROOT, "gauntlet", "characters", "gambler", "round-07")
    }

    # 1. Native 1x Sprite Lineup & 2. 4x Nearest Neighbor Lineup
    sheet_1x_path = os.path.join(output_dir, "ensemble_lineup_1x_native.png")
    sheet_4x_path = os.path.join(output_dir, "ensemble_lineup_4x_enlarged.png")
    sheet_sil_path = os.path.join(output_dir, "ensemble_silhouette_lineup.png")

    chars = ["celina", "agnes", "gambler"]
    titles = ["1. Celina (Aristocratic Fencer)", "2. Agnes (Heavy Vanguard)", "3. The Gambler (Showman Trickster)"]
    
    # 1x Sheet
    w_1x = 192 * 3 + 40
    h_1x = 192 + 80
    im_1x = Image.new("RGBA", (w_1x, h_1x), (18, 19, 22, 255))
    draw_1x = ImageDraw.Draw(im_1x)
    draw_1x.text((20, 16), "Second Gate Trio — Native 1x Gameplay Sprite Lineup (192x192)", fill=(240, 240, 245), font=get_font(16))
    
    # 4x Sheet
    w_4x = (192 * 4) * 3 + 80
    h_4x = (192 * 4) + 100
    im_4x = Image.new("RGBA", (w_4x, h_4x), (18, 19, 22, 255))
    draw_4x = ImageDraw.Draw(im_4x)
    draw_4x.text((20, 16), "Second Gate Trio — 4x Nearest-Neighbor Scaled Inspection", fill=(240, 240, 245), font=get_font(20))

    # Silhouette Sheet
    im_sil = Image.new("RGBA", (w_1x, h_1x), (230, 235, 240, 255))
    draw_sil = ImageDraw.Draw(im_sil)
    draw_sil.text((20, 16), "Second Gate Trio — Pure Silhouette Separation (Black Mask)", fill=(20, 20, 25), font=get_font(16))

    for idx, c in enumerate(chars):
        static_p = os.path.join(char_rounds[c], "static_front.png")
        if os.path.exists(static_p):
            sp = Image.open(static_p).convert("RGBA")
            
            # 1x Dark placement
            x_1x = 20 + idx * (192 + 10)
            y_1x = 50
            bg_1x = draw_checkerboard(192, 192, tile_size=10)
            bg_1x.paste(sp, (0, 0), sp)
            im_1x.paste(bg_1x, (x_1x, y_1x))
            draw_1x.rectangle([x_1x, y_1x, x_1x + 192, y_1x + 192], outline=(55, 60, 75), width=1)
            draw_1x.text((x_1x, y_1x + 196), titles[idx], fill=(255, 215, 0), font=get_font(12))

            # 4x placement
            x_4x = 20 + idx * (192 * 4 + 20)
            y_4x = 60
            sp_4x = sp.resize((192 * 4, 192 * 4), Image.NEAREST)
            bg_4x = draw_checkerboard(192 * 4, 192 * 4, tile_size=16)
            bg_4x.paste(sp_4x, (0, 0), sp_4x)
            im_4x.paste(bg_4x, (x_4x, y_4x))
            draw_4x.rectangle([x_4x, y_4x, x_4x + 192 * 4, y_4x + 192 * 4], outline=(55, 60, 75), width=1)
            draw_4x.text((x_4x, y_4x + 192 * 4 + 8), titles[idx], fill=(255, 215, 0), font=get_font(16))

            # Silhouette placement
            alpha = sp.split()[3]
            black_shape = Image.new("RGBA", (192, 192), (0, 0, 0, 255))
            sil_box = Image.new("RGBA", (192, 192), (245, 245, 250, 255))
            sil_box.paste(black_shape, (0, 0), alpha)
            im_sil.paste(sil_box, (x_1x, y_1x))
            draw_sil.rectangle([x_1x, y_1x, x_1x + 192, y_1x + 192], outline=(180, 185, 195), width=1)
            draw_sil.text((x_1x, y_1x + 196), titles[idx], fill=(20, 20, 25), font=get_font(12))

    # Add ground line Y=176
    draw_1x.line([20, 50 + 176, w_1x - 20, 50 + 176], fill=(255, 60, 60, 180), width=1)
    draw_4x.line([20, 60 + 176 * 4, w_4x - 20, 60 + 176 * 4], fill=(255, 60, 60, 180), width=2)
    draw_sil.line([20, 50 + 176, w_1x - 20, 50 + 176], fill=(255, 60, 60, 180), width=1)

    im_1x.save(sheet_1x_path, "PNG")
    im_4x.save(sheet_4x_path, "PNG")
    im_sil.save(sheet_sil_path, "PNG")

    # 4. Idle Comparison Sheet
    sheet_idle_path = os.path.join(output_dir, "ensemble_idle_comparison.png")
    h_idle = 60 + 3 * (192 + 10) + 20
    w_idle = 20 + 16 * (192 // 2 + 4) + 20
    im_idle = Image.new("RGBA", (w_idle, h_idle), (18, 19, 22, 255))
    draw_idle = ImageDraw.Draw(im_idle)
    draw_idle.text((20, 16), "Second Gate Trio — 16-Frame Canonical Front Idle Comparison", fill=(240, 240, 245), font=get_font(18))

    for c_idx, c in enumerate(chars):
        row_y = 60 + c_idx * (192 + 10)
        draw_idle.text((20, row_y + 80), c.capitalize(), fill=(255, 215, 0), font=get_font(14))
        idle_files = sorted(glob.glob(os.path.join(char_rounds[c], "idle", "*.png")))
        for f_idx, ip in enumerate(idle_files[:16]):
            frm = Image.open(ip).convert("RGBA").resize((192 // 2, 192 // 2), Image.NEAREST)
            fx = 120 + f_idx * (192 // 2 + 4)
            bg = draw_checkerboard(192 // 2, 192 // 2, tile_size=6)
            bg.paste(frm, (0, 0), frm)
            im_idle.paste(bg, (fx, row_y))
            draw_idle.rectangle([fx, row_y, fx + 192 // 2, row_y + 192 // 2], outline=(55, 60, 75), width=1)

    im_idle.save(sheet_idle_path, "PNG")

    # 5. Locomotion Comparison Sheet (South & East profiles across all 3)
    sheet_loco_path = os.path.join(output_dir, "ensemble_locomotion_comparison.png")
    h_loco = 60 + 6 * (192 + 8) + 20
    w_loco = 120 + 8 * (192 + 4) + 20
    im_loco = Image.new("RGBA", (w_loco, h_loco), (18, 19, 22, 255))
    draw_loco = ImageDraw.Draw(im_loco)
    draw_loco.text((20, 16), "Second Gate Trio — 8-Direction Locomotion Comparison (Front S & Profile E)", fill=(240, 240, 245), font=get_font(18))

    row_count = 0
    for c in chars:
        for d in ["S", "E"]:
            row_y = 60 + row_count * (192 + 8)
            draw_loco.text((20, row_y + 80), f"{c.capitalize()} ({d})", fill=(255, 215, 0), font=get_font(13))
            walk_files = sorted(glob.glob(os.path.join(char_rounds[c], "walk", d, "*.png")))
            for f_idx, wp in enumerate(walk_files[:8]):
                frm = Image.open(wp).convert("RGBA")
                fx = 120 + f_idx * (192 + 4)
                bg = draw_checkerboard(192, 192, tile_size=10)
                bg.paste(frm, (0, 0), frm)
                im_loco.paste(bg, (fx, row_y))
                draw_loco.line([fx, row_y + 176, fx + 192, row_y + 176], fill=(255, 60, 60, 100), width=1)
                draw_loco.rectangle([fx, row_y, fx + 192, row_y + 192], outline=(55, 60, 75), width=1)
            row_count += 1

    im_loco.save(sheet_loco_path, "PNG")

    # 6. Signature Gesture Comparison Sheet
    sheet_gest_path = os.path.join(output_dir, "ensemble_gesture_comparison.png")
    h_gest = 60 + 3 * (192 // 2 + 15) + 20
    w_gest = 140 + 24 * (192 // 2 + 2) + 20
    im_gest = Image.new("RGBA", (w_gest, h_gest), (18, 19, 22, 255))
    draw_gest = ImageDraw.Draw(im_gest)
    draw_gest.text((20, 16), "Second Gate Trio — 24-Frame Signature Gesture Comparison", fill=(240, 240, 245), font=get_font(18))

    for c_idx, c in enumerate(chars):
        row_y = 60 + c_idx * (192 // 2 + 15)
        draw_gest.text((20, row_y + 35), f"{c.capitalize()} Gesture", fill=(255, 215, 0), font=get_font(13))
        gest_files = sorted(glob.glob(os.path.join(char_rounds[c], "gesture", "*.png")))
        for f_idx, gp in enumerate(gest_files[:24]):
            frm = Image.open(gp).convert("RGBA").resize((192 // 2, 192 // 2), Image.NEAREST)
            fx = 140 + f_idx * (192 // 2 + 2)
            bg = draw_checkerboard(192 // 2, 192 // 2, tile_size=6)
            bg.paste(frm, (0, 0), frm)
            im_gest.paste(bg, (fx, row_y))
            draw_gest.rectangle([fx, row_y, fx + 192 // 2, row_y + 192 // 2], outline=(55, 60, 75), width=1)

    im_gest.save(sheet_gest_path, "PNG")

    return {
        "native_1x_lineup": sheet_1x_path,
        "enlarged_4x_lineup": sheet_4x_path,
        "silhouette_lineup": sheet_sil_path,
        "idle_comparison": sheet_idle_path,
        "locomotion_comparison": sheet_loco_path,
        "gesture_comparison": sheet_gest_path
    }

def run_ensemble_evaluation():
    out_dir = os.path.join(REPO_ROOT, "gauntlet", "characters", "ensemble", "round-01")
    sheets = generate_ensemble_sheets(os.path.join(out_dir, "sheets"))
    print(f"[EnsembleRunner] Generated {len(sheets)} ensemble comparison sheets.")

    eval_images = [
        {"label": "Ensemble Native 1x Lineup (192x192)", "path": sheets["native_1x_lineup"]},
        {"label": "Ensemble 4x Nearest-Neighbor Scaled Inspection", "path": sheets["enlarged_4x_lineup"]},
        {"label": "Ensemble Pure Silhouette Lineup (Black Mask)", "path": sheets["silhouette_lineup"]},
        {"label": "Ensemble 16-Frame Idle Animation Comparison", "path": sheets["idle_comparison"]},
        {"label": "Ensemble 8-Direction Locomotion Comparison", "path": sheets["locomotion_comparison"]},
        {"label": "Ensemble 24-Frame Signature Gesture Comparison", "path": sheets["gesture_comparison"]}
    ]

    context_prompt = (
        "EVALUATING FULL ENSEMBLE ROSTER: CELINA, AGNES, AND THE GAMBLER.\n"
        "All three characters are presented side-by-side at native 1x gameplay scale (192x192) and 4x enlarged scale.\n"
        "Evaluate world cohesion, scale alignment (all <= 128px standing height), silhouette distinctness, palette separation, and kinetic personality independence.\n"
    )

    harness = LunaHarness()
    print("[LunaHarness] Submitting Ensemble Package to gpt-5.6-luna (xhigh reasoning)...")
    res = harness.evaluate_round(
        character_name="ensemble",
        round_name="round-01",
        image_paths=eval_images,
        context_prompt=context_prompt
    )

    report_p = os.path.join(out_dir, "ensemble_evaluation_report.json")
    with open(report_p, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)

    print(f"\n[Ensemble Verdict]: {res.get('verdict')}")
    print(f"[Ensemble Avg Score]: {res.get('avg_score', 0):.2f} / 10.0")
    print(f"[Ensemble Log]: {report_p}")

if __name__ == "__main__":
    run_ensemble_evaluation()
