"""Blind review sub-agent for item models across experimental arms.

Scores item model renders blind using gpt-5.6-luna vision API.
Never sends arm, filepath, or authoring recipe to the judge.
"""

from __future__ import annotations

import argparse
import base64
import datetime
import io
import json
import os
import random
import sys
import time
from pathlib import Path
from typing import Any

import requests
from PIL import Image

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parents[2]
BLIND_REVIEW_DIR = REPO_ROOT / "tools" / "asset-production" / "blind-review"
RESULTS_JSONL = BLIND_REVIEW_DIR / "results.jsonl"
SHEETS_DIR = BLIND_REVIEW_DIR / "sheets"
RENDERS_DIR = BLIND_REVIEW_DIR / "renders"

DEFAULT_MODEL = "gpt-5.6-luna"
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"

PROMPT_TEMPLATE = """You are evaluating a 3D low-poly video game item asset shown from four rotation and tilt angles on a dark background.
Target item name: "{item_name}"

Score the model on these three criteria from 1 to 5 (integer only):
1. Recognisable (1-5): Does this read as the named object ("{item_name}")? (1 = completely unrecognisable, 3 = somewhat plausible, 5 = instantly and clearly reads as {item_name})
2. Silhouette (1-5): Is the overall 3D shape distinct, clear, and readable across all viewing angles?
3. Craft (1-5): Does it look deliberately designed, cohesive, and well-proportioned rather than a generic primitive?

Respond in valid JSON matching this schema:
{{
  "recognizable": <int 1-5>,
  "recognizable_justification": "<one sentence explanation>",
  "silhouette": <int 1-5>,
  "silhouette_justification": "<one sentence explanation>",
  "craft": <int 1-5>,
  "craft_justification": "<one sentence explanation>"
}}
"""


def score_image_blind(
    image_path: Path,
    item_name: str,
    model: str = DEFAULT_MODEL,
    max_retries: int = 4,
) -> tuple[dict[str, int], dict[str, str]]:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY environment variable is missing")

    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    prompt = PROMPT_TEMPLATE.format(item_name=item_name)
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{b64}"},
                    },
                ],
            }
        ],
        "response_format": {"type": "json_object"},
        "max_completion_tokens": 1000,
    }

    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            res = requests.post(OPENAI_API_URL, headers=headers, json=payload, timeout=60)
            if res.status_code == 200:
                data = res.json()
                msg = data["choices"][0]["message"]
                content = msg.get("content") or ""
                content = content.strip()
                if "```json" in content:
                    content = content.split("```json", 1)[1].split("```", 1)[0].strip()
                elif "```" in content:
                    content = content.split("```", 1)[1].split("```", 1)[0].strip()
                elif "{" in content and "}" in content:
                    content = content[content.find("{"):content.rfind("}") + 1]

                if not content:
                    raise ValueError(f"Empty content in completion: {data}")

                parsed = json.loads(content)
                scores = {
                    "recognizable": int(parsed.get("recognizable", 3)),
                    "silhouette": int(parsed.get("silhouette", 3)),
                    "craft": int(parsed.get("craft", 3)),
                }
                # Clamp 1-5
                for k in scores:
                    scores[k] = max(1, min(5, scores[k]))
                justifications = {
                    "recognizable": str(parsed.get("recognizable_justification", "")),
                    "silhouette": str(parsed.get("silhouette_justification", "")),
                    "craft": str(parsed.get("craft_justification", "")),
                }
                return scores, justifications
            else:
                last_error = f"HTTP {res.status_code}: {res.text}"
        except Exception as e:
            last_error = str(e)
        time.sleep(2 * attempt)

    raise RuntimeError(f"Failed to score {image_path} after {max_retries} attempts: {last_error}")


def run_review(manifest_path: Path, model: str = DEFAULT_MODEL) -> list[dict[str, Any]]:
    BLIND_REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    # Read already scored image_ids from RESULTS_JSONL for idempotency
    existing_ids = set()
    if RESULTS_JSONL.exists():
        with open(RESULTS_JSONL, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                if line.strip():
                    try:
                        record = json.loads(line)
                        existing_ids.add(record.get("image_id"))
                    except Exception:
                        pass

    entries = list(manifest)
    random.shuffle(entries)

    results = []
    for idx, entry in enumerate(entries, 1):
        image_path = Path(entry["image_path"])
        item_name = entry["item_name"]
        arm = entry["arm"]
        image_id = entry["image_id"]

        if image_id in existing_ids:
            print(f"[{idx}/{len(entries)}] Image '{image_id}' already scored, skipping.")
            continue

        print(f"[{idx}/{len(entries)}] Blind scoring item '{item_name}' (ID: {image_id})...")
        scores, justifications = score_image_blind(image_path, item_name, model=model)

        record = {
            "image_id": image_id,
            "item_name": item_name,
            "arm": arm,
            "scores": scores,
            "justification": justifications,
            "model_id": model,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        results.append(record)
        existing_ids.add(image_id)

        # Append to results.jsonl immediately
        with open(RESULTS_JSONL, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

    return results


def compute_summary(jsonl_path: Path = RESULTS_JSONL) -> dict[str, Any]:
    if not jsonl_path.exists():
        return {}

    records = []
    with open(jsonl_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except Exception:
                    pass

    by_arm: dict[str, list[dict[str, Any]]] = {"A": [], "B": [], "C": []}
    for r in records:
        arm = r.get("arm")
        if arm in by_arm:
            by_arm[arm].append(r)

    summary = {}
    for arm, arm_records in by_arm.items():
        count = len(arm_records)
        if count == 0:
            summary[arm] = {
                "count": 0,
                "recognizable": 0.0,
                "silhouette": 0.0,
                "craft": 0.0,
                "overall": 0.0,
            }
            continue

        rec_avg = sum(r["scores"]["recognizable"] for r in arm_records) / count
        sil_avg = sum(r["scores"]["silhouette"] for r in arm_records) / count
        crf_avg = sum(r["scores"]["craft"] for r in arm_records) / count
        overall = (rec_avg + sil_avg + crf_avg) / 3.0

        summary[arm] = {
            "count": count,
            "recognizable": rec_avg,
            "silhouette": sil_avg,
            "craft": crf_avg,
            "overall": overall,
        }

    return {"total_records": len(records), "by_arm": summary}


def print_score_table(summary: dict[str, Any] | None = None) -> str:
    if summary is None:
        summary = compute_summary()

    by_arm = summary.get("by_arm", {})
    total = summary.get("total_records", 0)

    lines = []
    lines.append("### Running Per-Arm Blind Review Scores")
    lines.append(f"*Total evaluated images: {total}*")
    lines.append("")
    lines.append("| Arm | Description | Count | Recognisable | Silhouette | Craft | Overall Mean |")
    lines.append("|---|---|---|---|---|---|---|")

    arm_desc = {
        "A": "Composed (`parts.py` 3+ parts)",
        "B": "Single Profile (`lathe.lathe()`)",
        "C": "Hidden Control (legacy batch)",
    }

    for arm in ["A", "B", "C"]:
        stats = by_arm.get(arm, {"count": 0, "recognizable": 0.0, "silhouette": 0.0, "craft": 0.0, "overall": 0.0})
        count = stats["count"]
        rec = f"{stats['recognizable']:.2f}" if count > 0 else "N/A"
        sil = f"{stats['silhouette']:.2f}" if count > 0 else "N/A"
        crf = f"{stats['craft']:.2f}" if count > 0 else "N/A"
        ovr = f"{stats['overall']:.2f}" if count > 0 else "N/A"
        lines.append(f"| **{arm}** | {arm_desc[arm]} | {count} | {rec} | {sil} | {crf} | **{ovr}** |")

    table_text = "\n".join(lines)
    print(table_text)
    return table_text


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Blind review runner and reporter")
    parser.add_argument("--manifest", type=Path, help="Path to review manifest JSON")
    parser.add_argument("--report", action="store_true", help="Print current score table")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Model ID for review")
    args = parser.parse_args()

    if args.manifest:
        run_review(args.manifest, model=args.model)
        print_score_table()
    elif args.report:
        print_score_table()
    else:
        print_score_table()
