"""Compare level/pitched town cameras on an exterior and an interior.

This is a read-only camera study. It deliberately renders the same geometry
through several rigid camera poses and reports the screen drift of world
verticals. A pitched perspective camera keeps its roll at zero, but verticals
away from the optical axis can still lean because their depth changes as they
rise. Principal-point compensation only pins framing; it cannot remove that
projective effect.

Run inside Blender:

    blender --background --factory-startup --python tools/blender/study_town_perspective.py -- \
        --interior-obj projects/.../alicias_padaria_3d/environment.obj \
        --output out/camera-study/perspective
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
import stage_room_model  # noqa: E402
import thestra_camera  # noqa: E402

DEFAULT_EXTERIOR = ROOT / "projects" / "hichaukitoden-game" / "assets" / "authoring" / "environments" / "st_maria_praca.blend"
DEFAULT_INTERIOR = ROOT / "projects" / "hichaukitoden-game" / "assets" / "environments" / "st_maria_town" / "alicias_padaria_3d" / "environment.obj"
DEFAULT_CAMERA = ROOT / "tools" / "blender" / "fixtures" / "town_sideview_camera.json"


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--exterior", type=Path, default=DEFAULT_EXTERIOR)
    parser.add_argument("--interior-obj", type=Path, default=DEFAULT_INTERIOR)
    parser.add_argument("--camera", type=Path, default=DEFAULT_CAMERA)
    parser.add_argument("--output", type=Path, required=True)
    values = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    return parser.parse_args(values)


def record_for(record, *, eye_x=None, pitch=0.0, center_y=None):
    result = copy.deepcopy(record)
    if eye_x is not None:
        result["eye"]["x"] = float(eye_x)
    result["orientation"]["pitchRadians"] = math.radians(float(pitch))
    if center_y is not None:
        result["viewportCenterY"] = float(center_y)
    return result


def project(scene, camera, point):
    return thestra_camera.project_world_point(scene, camera, Vector(point))


def vertical_diagnostic(scene, camera, points):
    rows = []
    for index, (x, y, z) in enumerate(points):
        feet = project(scene, camera, (x, y, z))
        head = project(scene, camera, (x, y, z + 3.0))
        rows.append({
            "id": index,
            "world": [x, y, z],
            "feetPx": [round(feet[0], 4), round(feet[1], 4)],
            "headPx": [round(head[0], 4), round(head[1], 4)],
            "leanPx": round(head[0] - feet[0], 4),
        })
    return rows


def render_variant(scene, record, name, output, diagnostics):
    camera = thestra_camera.create_or_update_camera(
        record, scene=scene, name="PERSPECTIVE_STUDY_CAMERA", make_active=True)
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 256
    scene.render.resolution_y = 240
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str((output / f"{name}.png").resolve())
    scene.render.film_transparent = False
    scene.render.image_settings.color_mode = "RGBA"
    bpy.ops.render.render(write_still=True)
    return {
        "name": name,
        "pitchDegrees": round(math.degrees(record["orientation"]["pitchRadians"]), 3),
        "viewportCenterY": record["viewportCenterY"],
        "verticals": vertical_diagnostic(scene, camera, diagnostics),
        "image": str((output / f"{name}.png").resolve()),
    }


def exterior(options, output):
    bpy.ops.wm.open_mainfile(filepath=str(options.exterior.resolve()))
    scene = bpy.context.scene
    base = json.loads(options.camera.read_text(encoding="utf-8"))
    # The Praca source is in the local action-plane frame used by its camera.
    base["eye"]["x"] += 7.8
    base["eye"]["y"] = 11.85
    base["eye"]["z"] += -1.5
    diagnostics = [(7.8, 11.85 + y, -1.5) for y in (-3.0, 0.0, 3.0)]
    rows = []
    for name, pitch, compensate in (("level", 0.0, False), ("down_2p5", 2.5, False),
                                    ("down_2p5_pinned", 2.5, True), ("up_2p5", -2.5, False)):
        record = record_for(base, pitch=pitch)
        if compensate:
            baseline = thestra_camera.create_or_update_camera(
                record_for(base, pitch=0.0), scene=scene,
                name="PERSPECTIVE_STUDY_CAMERA", make_active=True)
            base_feet = project(scene, baseline, (7.8, 11.85, -1.5))
            pitched = thestra_camera.create_or_update_camera(
                record, scene=scene, name="PERSPECTIVE_STUDY_CAMERA", make_active=True)
            pitched_y = project(scene, pitched, (7.8, 11.85, -1.5))[1]
            record["viewportCenterY"] += base_feet[1] - pitched_y
        rows.append(render_variant(scene, record, f"exterior_{name}", output, diagnostics))
    return rows


def interior(options, output):
    # Use the runtime-exported room geometry for this study. The current
    # interior source files in this checkout are zstd-wrapped and Blender 4.1
    # cannot open them; this preserves the actual shipped room silhouette.
    bpy.ops.wm.read_factory_settings(use_empty=True)
    meshes, info = stage_room_model.import_model(options.interior_obj, 4.0)
    stage_room_model.base_lighting(0.13)
    scene = bpy.context.scene
    base = json.loads(options.camera.read_text(encoding="utf-8"))
    diagnostics = [(x, y, 0.0) for x in (0.0, 2.0) for y in (-3.0, 0.0, 3.0)]
    rows = []
    for name, pitch, compensate in (("level", 0.0, False), ("down_2p5", 2.5, False),
                                    ("down_2p5_pinned", 2.5, True), ("up_2p5", -2.5, False)):
        record = record_for(base, pitch=pitch)
        if compensate:
            # Pin the common floor anchor, as the earlier pitch study did.
            baseline = record_for(base, pitch=0.0)
            c0 = thestra_camera.create_or_update_camera(
                baseline, scene=scene, name="PERSPECTIVE_STUDY_CAMERA", make_active=True)
            base_feet = project(scene, c0, (0.0, 0.0, 0.0))
            c1 = thestra_camera.create_or_update_camera(
                record, scene=scene, name="PERSPECTIVE_STUDY_CAMERA", make_active=True)
            record["viewportCenterY"] += base_feet[1] - project(scene, c1, (0.0, 0.0, 0.0))[1]
        rows.append(render_variant(scene, record, f"interior_{name}", output, diagnostics))
    return rows


def main():
    options = parse_args()
    output = options.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    report = {
        "contract": "thestra.town-perspective-study",
        "exterior": exterior(options, output),
        "interior": interior(options, output),
        "note": "positive pitch is camera-down in the Thestra basis; leanPx is screen-x head minus feet for a 3-unit world vertical",
    }
    (output / "study.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("TOWN PERSPECTIVE STUDY OK " + json.dumps(report))


if __name__ == "__main__":
    main()
