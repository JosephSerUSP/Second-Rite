"""Execution pipeline for blind review experimental passes.

Handles:
1. Arm C rendering & cropping (legacy control)
2. Arm A generation, rendering & cropping (composed parts)
3. Arm B generation, rendering & cropping (single profile)
4. Arm A final restoration
5. item-model-baseline.json update & corpus check
6. Blind review scoring with gpt-5.6-luna
7. Progress reporting and summary table generation
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from PIL import Image

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools" / "asset-production"))

import blind_review
import check_item_models
import item_model_corpus
import lathe
import pass_definitions

LOVE_EXE = Path("C:/Program Files/LOVE/lovec.exe")
LOVE_SAVE_DIR = Path(os.environ.get("APPDATA", "")) / "LOVE" / "SecondRite"
OUT_ITEMS = REPO_ROOT / "assets" / "models" / "items"
MTL_NAME = "item_complete_library.mtl"

BLIND_REVIEW_DIR = REPO_ROOT / "tools" / "asset-production" / "blind-review"
SHEETS_DIR = BLIND_REVIEW_DIR / "sheets"
RENDERS_DIR = BLIND_REVIEW_DIR / "renders"
MANIFESTS_DIR = BLIND_REVIEW_DIR / "manifests"
PROGRESS_MD = BLIND_REVIEW_DIR / "PROGRESS.md"
BASELINE_PATH = REPO_ROOT / "tools" / "asset-production" / "item-model-baseline.json"

CELL = 96
LABEL_HEIGHT = 12
VIEWS = 4
BLOCK_WIDTH = CELL * VIEWS  # 384
GRID_COLUMNS = 3
CELL_HEIGHT = CELL + LABEL_HEIGHT  # 108


def ensure_dirs():
    SHEETS_DIR.mkdir(parents=True, exist_ok=True)
    RENDERS_DIR.mkdir(parents=True, exist_ok=True)
    MANIFESTS_DIR.mkdir(parents=True, exist_ok=True)


def run_lovec_sheet(filter_file: Path, output_png_name: str, timeout_sec: int = 25) -> Path:
    cmd = [str(LOVE_EXE), ".", "item-sheet", filter_file.relative_to(REPO_ROOT).as_posix(), output_png_name]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=timeout_sec)
    if res.returncode != 0:
        raise RuntimeError(f"lovec item-sheet failed: {res.stderr}\n{res.stdout}")

    out_file = LOVE_SAVE_DIR / output_png_name
    if not out_file.exists():
        raise RuntimeError(f"Expected output file not found in LOVE save dir: {out_file}")
    return out_file


def crop_sheet_items(sheet_path: Path, items: list[dict[str, Any]], pass_num: int, arm: str) -> dict[str, Path]:
    sheet = Image.open(sheet_path)
    # Sort items alphabetically by name to match engine/item_model_sheet.lua collectEntries
    sorted_items = sorted(items, key=lambda x: x["name"])

    cropped_paths = {}
    for idx, item in enumerate(sorted_items):
        col = idx % GRID_COLUMNS
        row = idx // GRID_COLUMNS
        x = col * BLOCK_WIDTH
        y = row * CELL_HEIGHT
        crop = sheet.crop((x, y, x + BLOCK_WIDTH, y + CELL))
        out_name = f"pass{pass_num}_{item['stem']}_{arm}.png"
        out_path = RENDERS_DIR / out_name
        crop.save(out_path, format="PNG")
        cropped_paths[item["stem"]] = out_path

    return cropped_paths


def write_models(items: list[dict[str, Any]], arm_key: str):
    for item in items:
        mesh = item[arm_key]()
        mesh.name = item["stem"]
        obj_path = OUT_ITEMS / f"{item['stem']}.obj"
        lathe.write_obj(mesh, obj_path, mtllib=MTL_NAME, comment=f"Blind review arm {arm_key.upper()}: {item['name']}")


def update_baseline(items: list[dict[str, Any]]):
    item_names = {it["name"] for it in items}
    data = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))

    # Remove from legacyItems
    legacy = [name for name in data.get("legacyItems", []) if name not in item_names]
    data["legacyItems"] = legacy

    # Update accepted violations by collecting current violations
    models = item_model_corpus.load_item_models()
    violations = check_item_models.collect_violations(models, legacy=set(legacy))
    data["accepted"] = sorted(r["key"] for r in violations)

    counts = {}
    for r in violations:
        counts[r["kind"]] = counts.get(r["kind"], 0) + 1
    data["counts"] = dict(sorted(counts.items()))

    BASELINE_PATH.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"Updated baseline: {len(data['accepted'])} accepted violations remaining.")


def execute_pass(pass_num: int, model: str = "gpt-5.6-luna"):
    ensure_dirs()
    if pass_num < 1 or pass_num > len(pass_definitions.ALL_PASSES):
        raise ValueError(f"Invalid pass number {pass_num}")

    items = pass_definitions.ALL_PASSES[pass_num - 1]
    print(f"\n==========================================")
    print(f"EXECUTING PASS {pass_num} ({len(items)} ITEMS)")
    print(f"==========================================")

    # 1. Filter file
    filter_file = BLIND_REVIEW_DIR / f"pass-{pass_num}-items.txt"
    filter_file.write_text("\n".join(it["name"] for it in items) + "\n", encoding="utf-8")

    # 2. Render Arm C (Control)
    print(f"[Pass {pass_num}] Step 1/6: Rendering Arm C (legacy control)...")
    sheet_c_love = run_lovec_sheet(filter_file, f"pass-{pass_num}-C.png")
    sheet_c_dest = SHEETS_DIR / f"pass-{pass_num}-C.png"
    shutil.copy(sheet_c_love, sheet_c_dest)
    crops_c = crop_sheet_items(sheet_c_dest, items, pass_num, "C")

    # 3. Build & Render Arm A (Composed parts)
    print(f"[Pass {pass_num}] Step 2/6: Authoring & Rendering Arm A (composed parts)...")
    write_models(items, "arm_a")
    sheet_a_love = run_lovec_sheet(filter_file, f"pass-{pass_num}-A.png")
    sheet_a_dest = SHEETS_DIR / f"pass-{pass_num}-A.png"
    shutil.copy(sheet_a_love, sheet_a_dest)
    # Also save as canonical pass-<N>.png
    shutil.copy(sheet_a_love, SHEETS_DIR / f"pass-{pass_num}.png")
    crops_a = crop_sheet_items(sheet_a_dest, items, pass_num, "A")

    # 4. Build & Render Arm B (Single profile)
    print(f"[Pass {pass_num}] Step 3/6: Authoring & Rendering Arm B (single profile)...")
    write_models(items, "arm_b")
    sheet_b_love = run_lovec_sheet(filter_file, f"pass-{pass_num}-B.png")
    sheet_b_dest = SHEETS_DIR / f"pass-{pass_num}-B.png"
    shutil.copy(sheet_b_love, sheet_b_dest)
    crops_b = crop_sheet_items(sheet_b_dest, items, pass_num, "B")

    # 5. Restore Arm A as final state
    print(f"[Pass {pass_num}] Step 4/6: Restoring Arm A models as final state...")
    write_models(items, "arm_a")

    # 6. Update baseline & verify corpus gate
    print(f"[Pass {pass_num}] Step 5/6: Updating corpus baseline & running gate...")
    update_baseline(items)
    check_code = check_item_models.main([])
    if check_code != 0:
        raise RuntimeError(f"Corpus check failed after Pass {pass_num} with exit code {check_code}")
    print("Corpus gate PASSED (ITEM MODELS OK).")

    # 7. Build Manifest & Run Blind Review
    print(f"[Pass {pass_num}] Step 6/6: Running blind review on {len(items) * 3} images via {model}...")
    manifest = []
    for it in items:
        stem = it["stem"]
        manifest.append({
            "image_id": f"pass{pass_num}_{stem}_A",
            "item_name": it["name"],
            "arm": "A",
            "image_path": str(crops_a[stem]),
        })
        manifest.append({
            "image_id": f"pass{pass_num}_{stem}_B",
            "item_name": it["name"],
            "arm": "B",
            "image_path": str(crops_b[stem]),
        })
        manifest.append({
            "image_id": f"pass{pass_num}_{stem}_C",
            "item_name": it["name"],
            "arm": "C",
            "image_path": str(crops_c[stem]),
        })

    manifest_path = MANIFESTS_DIR / f"pass_{pass_num}_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    blind_review.run_review(manifest_path, model=model)
    summary = blind_review.compute_summary()
    score_table = blind_review.print_score_table(summary)

    # Update PROGRESS.md
    update_progress_file(pass_num, items, summary)

    print(f"\nPASS {pass_num} COMPLETED SUCCESSFULLY.")
    print(f"Contact Sheet: {SHEETS_DIR / f'pass-{pass_num}.png'}")
    return summary


def update_progress_file(pass_num: int, items: list[dict[str, Any]], summary: dict[str, Any]):
    lines = []
    lines.append("# Item Batch Blind Review Progress")
    lines.append("")
    lines.append(f"**Last updated:** Pass {pass_num} completed ({pass_num * 10}/60 items).")
    lines.append("")
    lines.append("## Latest Score Table")
    lines.append("")
    table = blind_review.print_score_table(summary)
    lines.append(table)
    lines.append("")
    lines.append("## Completed Passes")
    for p in range(1, pass_num + 1):
        p_items = pass_definitions.ALL_PASSES[p - 1]
        lines.append(f"### Pass {p}")
        lines.append(f"- **Items ({len(p_items)}):** {', '.join(it['name'] for it in p_items)}")
        lines.append(f"- **Contact Sheet:** `tools/asset-production/blind-review/sheets/pass-{p}.png`")
        lines.append("")

    PROGRESS_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pass-num", type=int, required=True, help="Pass number (1-6)")
    parser.add_argument("--model", default="gpt-5.6-luna", help="Judge model ID")
    args = parser.parse_args()
    execute_pass(args.pass_num, model=args.model)
