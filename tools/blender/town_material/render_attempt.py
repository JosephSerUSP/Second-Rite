"""Render one town attempt through the calibrated next-gauntlet camera.

    blender --background --factory-startup --python render_attempt.py -- \
        --attempt 01 --calibration <path.json> [--offset 0] [--samples 220] \
        [--blend out.blend]
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import bpy  # noqa: E402

import thestra_camera  # noqa: E402
import town_builder as TB  # noqa: E402
import town_assembly as TA  # noqa: E402
from town_attempts import ATTEMPTS  # noqa: E402

ROOT = HERE.parents[2]
OUT = ROOT / "projects/hichaukitoden-game/assets/authoring/town/attempts_next"


def tri_count(collection_name):
    total = 0
    dg = bpy.context.evaluated_depsgraph_get()
    for ob in bpy.data.collections[collection_name].objects:
        if ob.type != "MESH":
            continue
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
        me.calc_loop_triangles()
        total += len(me.loop_triangles)
        ev.to_mesh_clear()
    return total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--attempt", required=True)
    ap.add_argument("--calibration", required=True, type=Path)
    ap.add_argument("--offset", type=float, default=0.0)
    ap.add_argument("--samples", type=int, default=220)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--blend", type=Path, default=None)
    ap.add_argument("--census", type=Path, default=None)
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    args = ap.parse_args(argv)

    spec = ATTEMPTS[args.attempt]
    record = json.loads(args.calibration.read_text(encoding="utf-8"))
    thestra_camera.validate_calibration(record)

    scene = TB.reset_scene()
    scene.cycles.samples = args.samples

    # projection-window movement: shift the window only, never the eye or lens
    if args.offset:
        record = copy.deepcopy(record)
        record["projectionWindowOffsetX"] = args.offset
        record["viewportCenterX"] = float(record["viewportCenterX"]) + args.offset

    cam = thestra_camera.create_or_update_camera(record, scene=scene, make_active=True)
    TB.put(cam, "TH_CAMERA_PREVIEW")

    # thestra_camera._set_scene_framing forces view_transform="Standard" for
    # pixel-exact calibration parity, which blows out an art render. Re-apply
    # the art transform here. This is a DISPLAY transform only -- it does not
    # touch the eye, lens, pitch or projection window.
    scene.view_settings.view_transform = "Filmic"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = float(spec.get("exposure", 0.0))

    TB.light_rig(scene, spec["lighting"])
    census = TA.build_town(scene, spec)
    TB.place_actors(scene, cam, spec)

    src_tris = tri_count("TH_SOURCE")
    rnd_tris = tri_count("TH_RENDER")
    census.update({
        "attempt": args.attempt,
        "title": spec["title"],
        "bias": spec["bias"],
        "sourceTris": src_tris,
        "renderTris": rnd_tris,
        "reductionRatio": round(src_tris / max(rnd_tris, 1), 2),
        "cameraLensMm": round(float(cam.data.lens), 4),
        "cameraEye": [round(v, 6) for v in cam.location],
        "projectionWindowOffsetX": args.offset,
    })

    OUT.mkdir(parents=True, exist_ok=True)
    target = args.out or (OUT / ("attempt_%s.png" % args.attempt))
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(target)
    bpy.ops.render.render(write_still=True)

    if args.blend:
        args.blend.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(args.blend))
    if args.census:
        args.census.write_text(json.dumps(census, indent=2), encoding="utf-8")
    print("ATTEMPT_OK " + json.dumps(census))


if __name__ == "__main__":
    main()
