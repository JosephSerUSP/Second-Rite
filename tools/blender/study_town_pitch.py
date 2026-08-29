"""Render a small compensated-pitch study without changing an authored source.

The study keeps the camera's calibrated eye-to-action-plane relationship and
uses principal-point compensation to keep the chosen Walker feet anchor fixed
on screen. It reports, rather than masks, any remaining 1.75m height change.
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "blender"))
import thestra_camera  # noqa: E402

DEFAULT_BLEND = (ROOT / "projects" / "hichaukitoden-game" / "assets"
                 / "authoring" / "environments" / "st_maria_praca.blend")
DEFAULT_CAMERA = ROOT / "tools" / "blender" / "fixtures" / "town_sideview_camera.json"


def args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--blend", type=Path, default=DEFAULT_BLEND)
    parser.add_argument("--camera", type=Path, default=DEFAULT_CAMERA)
    parser.add_argument("--anchor", default="spawn_player")
    parser.add_argument("--output", type=Path, required=True)
    values = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    return parser.parse_args(values)


def footprint(scene, camera, point):
    feet = thestra_camera.project_world_point(scene, camera, point)
    head = thestra_camera.project_world_point(scene, camera, point + Vector((0, 0, 1.75)))
    return {"feet": [round(v, 5) for v in feet], "height": round(abs(head[1] - feet[1]), 5)}


def positioned_record(base, anchor, degrees):
    result = copy.deepcopy(base)
    result["eye"] = {
        "x": anchor.x + float(base["eye"]["x"]),
        "y": anchor.y + float(base["eye"]["y"]),
        "z": anchor.z + float(base["eye"]["z"]),
    }
    result["orientation"]["pitchRadians"] = math.radians(degrees)
    return result


def main():
    options = args()
    bpy.ops.wm.open_mainfile(filepath=str(options.blend.resolve()))
    anchor_obj = bpy.data.objects.get(options.anchor)
    if anchor_obj is None:
        raise RuntimeError(f"missing pitch-study anchor {options.anchor!r}")
    anchor = anchor_obj.location.copy()
    base = json.loads(options.camera.read_text(encoding="utf-8"))
    scene = bpy.context.scene
    options.output = options.output.resolve()
    options.output.mkdir(parents=True, exist_ok=True)
    baseline_record = positioned_record(base, anchor, 0.0)
    camera = thestra_camera.create_or_update_camera(baseline_record, scene=scene,
                                                     name="PITCH_STUDY_CAMERA", make_active=True)
    baseline = footprint(scene, camera, anchor)
    rows = []
    for degrees in (-2.5, 0.0, 2.5):
        record = positioned_record(base, anchor, degrees)
        camera = thestra_camera.create_or_update_camera(record, scene=scene,
                                                         name="PITCH_STUDY_CAMERA", make_active=True)
        before = footprint(scene, camera, anchor)
        # Principal-point compensation pins the concrete action anchor. This
        # changes framing only, not eye position, lens, actor position or scale.
        record["viewportCenterY"] += baseline["feet"][1] - before["feet"][1]
        camera = thestra_camera.create_or_update_camera(record, scene=scene,
                                                         name="PITCH_STUDY_CAMERA", make_active=True)
        after = footprint(scene, camera, anchor)
        if max(abs(after["feet"][i] - baseline["feet"][i]) for i in (0, 1)) > 1e-3:
            raise RuntimeError(f"pitch compensation failed at {degrees}: {after}")
        image = options.output / f"pitch_{degrees:+.1f}.png"
        scene.render.filepath = str(image)
        bpy.ops.render.render(write_still=True)
        rows.append({"pitchDegrees": degrees, "viewportCenterY": record["viewportCenterY"],
                     "footprint": after, "heightDeltaPx": round(after["height"] - baseline["height"], 5),
                     "image": str(image)})
    report = {"blend": str(options.blend.resolve()), "anchor": options.anchor,
              "invariant": "feet anchor via principal-point compensation", "rows": rows}
    (options.output / "pitch-study.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("TOWN PITCH STUDY OK " + json.dumps(report))


if __name__ == "__main__":
    main()
