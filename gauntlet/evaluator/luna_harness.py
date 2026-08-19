# gauntlet/evaluator/luna_harness.py
# Adversarial evaluation harness calling OpenAI GPT-5.6 Luna on xhigh reasoning

import os
import json
import base64
import time
import requests
from typing import List, Dict, Any, Optional
from gauntlet.evaluator.rubric import (
    RUBRIC_CATEGORIES,
    ENSEMBLE_EXTRA_CATEGORIES,
    LUNA_SYSTEM_PROMPT,
    LUNA_ENSEMBLE_SYSTEM_PROMPT
)

class LunaHarness:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is missing.")
        self.endpoint = "https://api.openai.com/v1/chat/completions"
        self.model = "gpt-5.6-luna"
        self.reasoning_effort = "xhigh"

    def _encode_image(self, image_path: str) -> str:
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def evaluate_round(
        self,
        character_name: str,
        round_name: str,
        image_paths: List[Dict[str, str]], # List of {"label": str, "path": str}
        context_prompt: str,
        is_ensemble: bool = False,
        retries: int = 3
    ) -> Dict[str, Any]:
        """
        Submits an evaluation package to gpt-5.6-luna with xhigh reasoning effort.
        """
        system_prompt = LUNA_ENSEMBLE_SYSTEM_PROMPT if is_ensemble else LUNA_SYSTEM_PROMPT
        
        content_items = [
            {
                "type": "text",
                "text": f"Evaluation Target: {character_name.upper()} | Round: {round_name}\n\n"
                        f"Context & Character Archetype:\n{context_prompt}\n\n"
                        f"Attached Visual Evaluation Sheets ({len(image_paths)} sheets):"
            }
        ]

        for item in image_paths:
            label = item.get("label", "Image")
            path = item.get("path")
            if not os.path.exists(path):
                raise FileNotFoundError(f"Image not found for evaluation: {path}")
            b64_data = self._encode_image(path)
            content_items.append({
                "type": "text",
                "text": f"\n=== SHEET: {label} ({os.path.basename(path)}) ==="
            })
            content_items.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{b64_data}",
                    "detail": "high"
                }
            })

        payload = {
            "model": self.model,
            "reasoning_effort": self.reasoning_effort,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content_items}
            ],
            "response_format": {"type": "json_object"}
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        for attempt in range(retries):
            try:
                t0 = time.time()
                resp = requests.post(self.endpoint, headers=headers, json=payload, timeout=180)
                elapsed = time.time() - t0
                if resp.status_code != 200:
                    print(f"[LunaHarness] Attempt {attempt+1} HTTP error {resp.status_code}: {resp.text[:300]}")
                    time.sleep(3)
                    continue

                res_json = resp.json()
                raw_content = res_json["choices"][0]["message"]["content"]
                parsed = json.loads(raw_content)

                # Validate scores
                scores = parsed.get("scores", {})
                applicable_cats = RUBRIC_CATEGORIES + (ENSEMBLE_EXTRA_CATEGORIES if is_ensemble else [])
                
                # Check for category coverage and numerical extraction
                numeric_scores = []
                for cat in applicable_cats:
                    if cat in scores:
                        try:
                            numeric_scores.append(float(scores[cat]))
                        except (ValueError, TypeError):
                            pass

                avg_score = sum(numeric_scores) / len(numeric_scores) if numeric_scores else 0.0
                min_score = min(numeric_scores) if numeric_scores else 0.0
                blockers = parsed.get("blockers", [])

                passed = (
                    avg_score >= 8.5 and
                    min_score >= 8.0 and
                    len(blockers) == 0 and
                    parsed.get("verdict", "").upper() == "PASS"
                )

                parsed["computed_average"] = round(avg_score, 2)
                parsed["computed_min"] = round(min_score, 2)
                parsed["computed_pass"] = passed
                parsed["eval_duration_sec"] = round(elapsed, 2)
                if not passed:
                    parsed["verdict"] = "FAIL"

                return parsed
            except Exception as e:
                print(f"[LunaHarness] Attempt {attempt+1} exception: {e}")
                time.sleep(3)

        raise RuntimeError(f"Failed to obtain valid evaluation from {self.model} after {retries} attempts.")
