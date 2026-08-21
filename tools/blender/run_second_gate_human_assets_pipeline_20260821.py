"""Run the generic source->runtime package boundary for the selected town."""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import town_environment_pipeline  # noqa: E402


def main():
    evidence = ROOT / "out" / "blender" / "second-gate-human-assets-20260821" / "evidence"
    blend = evidence / "direction-A" / "town_A.blend"
    package = evidence / "winner" / "runtime-package"
    envelope = [
        {"name": "center", "weight": 1.0, "cost": 0.0, "projectionWindowOffset": [0.0, 0.0]},
        {"name": "window-left", "weight": 0.8, "cost": 0.55, "projectionWindowOffset": [-96.0, 0.0]},
        {"name": "window-right", "weight": 0.8, "cost": 0.55, "projectionWindowOffset": [96.0, 0.0]},
        {"name": "slightly-high", "weight": 0.55, "cost": 0.65, "eyeOffset": [0.0, 0.0, 0.35]},
        {"name": "slightly-low", "weight": 0.45, "cost": 0.65, "eyeOffset": [0.0, 0.0, -0.25]},
    ]
    camera_file = evidence / "winner" / "camera-envelope.json"
    camera_file.parent.mkdir(parents=True, exist_ok=True)
    camera_file.write_text(json.dumps({"samples": envelope}, indent=2), encoding="utf-8")
    town_environment_pipeline.export_environment_package(
        blend,
        package,
        atlas_size=1024,
        bake_samples=4,
        render_profile="cycles-candidate",
        atlas_allocation="view-weighted",
        camera_envelope=envelope,
        view_policy="bounded-camera",
        margin_px=4,
    )
    print(json.dumps({"blend": str(blend), "package": str(package), "samples": len(envelope)}, indent=2))


if __name__ == "__main__":
    main()
