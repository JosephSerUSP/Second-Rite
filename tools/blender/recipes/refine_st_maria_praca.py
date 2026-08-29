"""Apply the first hand-authoring pass to the adopted St. Maria Praca source.

This is deliberately an edit script, not a generator: it opens the existing
authoritative .blend, makes named, reviewable changes, and saves it in place.
Future spatial authors should edit the same document directly in Blender.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "blender"))
import thestra_camera  # noqa: E402

DEFAULT_BLEND = (ROOT / "projects" / "hichaukitoden-game" / "assets"
                 / "authoring" / "environments" / "st_maria_praca.blend")
CAMERA = ROOT / "tools" / "blender" / "fixtures" / "town_sideview_camera.json"
LANE_X, LANE_Y, GROUND_Z = 7.8, 11.85, -1.5


def coll(name):
    result = bpy.data.collections.get(name)
    if result is None:
        raise RuntimeError(f"source is missing required collection {name}")
    return result


def box(name, size, location, collection, color):
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.color = (*color, 1.0)
    for old in list(obj.users_collection):
        old.objects.unlink(obj)
    collection.objects.link(obj)
    return obj


def icosphere(name, radius, location, collection, color):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=radius, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.color = (*color, 1.0)
    for old in list(obj.users_collection):
        old.objects.unlink(obj)
    collection.objects.link(obj)
    return obj


def set_calibrated_camera():
    for old in list(bpy.data.objects):
        if old.type == "CAMERA" and old.name.startswith("CAMERA_town_sideview"):
            bpy.data.objects.remove(old, do_unlink=True)
    record = json.loads(CAMERA.read_text(encoding="utf-8"))
    # Translate the authoritative local side-view calibration into the Praca's
    # runtime action-plane frame. The optical relation (actor ↔ camera) is
    # unchanged; only its world origin moves.
    record["eye"]["x"] = LANE_X + float(record["eye"]["x"])
    record["eye"]["y"] = LANE_Y
    record["eye"]["z"] = GROUND_Z + float(record["eye"]["z"])
    camera = thestra_camera.create_or_update_camera(
        record, scene=bpy.context.scene, name="CAMERA_town_sideview", make_active=True)
    camera.name = "CAMERA_town_sideview_calibrated"
    for old_coll in list(camera.users_collection):
        old_coll.objects.unlink(camera)
    coll("TH_CAMERA_PREVIEW").objects.link(camera)
    return camera


def apply(blend):
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    architecture, foreground = coll("20_ARCHITECTURE"), coll("21_FOREGROUND")
    ground = bpy.data.objects.get("ARCH_square_ground")
    if ground is None:
        raise RuntimeError("source is missing ARCH_square_ground")
    # The floor is environmental continuity, not character terrain. It reaches
    # past the camera's bottom-of-frame intersection, beneath the translucent HUD.
    ground.dimensions = (22.0, 34.0, 0.35)
    ground.location = (2.5, LANE_Y, GROUND_Z - 0.2)
    bpy.context.view_layer.update()

    stone, roof, leaf = (0.42, 0.40, 0.35), (0.30, 0.12, 0.08), (0.08, 0.24, 0.10)
    for name in ("FG_near_roof_eave", "FG_near_roof_post", "FG_bougainvillea_trunk",
                 "FG_bougainvillea_crown", "ARCH_low_curb"):
        obj = bpy.data.objects.get(name)
        if obj:
            bpy.data.objects.remove(obj, do_unlink=True)
    # An actual near building eave, rather than a border slab, establishes a
    # depth layer and still leaves the action plane readable.
    box("FG_near_roof_eave", (3.4, 7.2, 0.55), (-3.0, 3.0, 4.85), foreground, roof)
    box("FG_near_roof_post", (0.45, 0.45, 4.3), (-2.55, 5.9, 2.15), foreground, stone)
    box("FG_bougainvillea_trunk", (0.32, 0.45, 3.1), (-1.7, 20.5, 0.05), foreground, stone)
    icosphere("FG_bougainvillea_crown", 1.9, (-1.65, 20.5, 3.15), foreground, leaf)
    box("ARCH_low_curb", (0.5, 24.5, 0.32), (6.15, LANE_Y, GROUND_Z + 0.15), architecture, stone)
    camera = set_calibrated_camera()

    bpy.context.scene["sr_refinement_01"] = (
        "Calibrated source camera; HUD-continuous ground; near roof and vegetation. "
        "Still clay massing: do not promote to runtime."
    )
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    print("PRACA REFINEMENT OK " + json.dumps({
        "blend": str(blend), "camera": camera.name,
        "groundMinX": -8.5, "groundMaxX": 13.5
    }))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--blend", type=Path, default=DEFAULT_BLEND)
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    args = parser.parse_args(argv)
    apply(args.blend.resolve())


if __name__ == "__main__":
    main()
