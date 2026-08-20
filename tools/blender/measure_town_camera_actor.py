"""Measure a real actor footprint through the Blender camera adapter.

This is intentionally a measurement tool, not a second camera authority.  The
calibration JSON is produced by the LÖVE harness and is consumed here by the
existing ``thestra_camera`` adapter.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "blender"))


def main() -> None:
    import bpy
    import thestra_camera

    parser = argparse.ArgumentParser()
    parser.add_argument("--camera", required=True, type=Path)
    parser.add_argument("--actor", default="5.35,5.5,-1.5")
    parser.add_argument("--height", default=1.75, type=float)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else None)

    actor = tuple(float(v) for v in args.actor.split(","))
    if len(actor) != 3:
        raise ValueError("--actor must be x,y,z")
    record = json.loads(args.camera.read_text(encoding="utf-8"))
    thestra_camera.validate_calibration(record)
    scene = bpy.context.scene
    camera = thestra_camera.create_or_update_camera(record, scene=scene, make_active=True)
    feet = thestra_camera.project_world_point(scene, camera, actor)
    top = thestra_camera.project_world_point(scene, camera, (actor[0], actor[1], actor[2] + args.height))
    height_px = abs(feet[1] - top[1])
    print(
        "THESTRA_TOWN_ACTOR_MEASURE OK "
        f"heightPx={height_px:.9f} feet=({feet[0]:.9f},{feet[1]:.9f}) "
        f"top=({top[0]:.9f},{top[1]:.9f}) lens={float(camera.data.lens):.9f}"
    )


if __name__ == "__main__":
    main()
