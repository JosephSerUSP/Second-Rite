"""Phase 9: the projection-window strip.

The camera EYE, LENS and PITCH must not move. A projection window pans the
view by moving the principal point (the optical axis's landing position on the
target), which Blender expresses as a lens shift. Nothing else changes.

Authority is preserved: the offset is applied to the authoring study input's
canonical centre, that spec is resolved through LOVE/Thestra exactly as the
zero-offset calibration was, and Blender consumes the resolved record. Blender
never authors a camera value.

Sign convention recorded explicitly: a NEGATIVE projection-window offset moves
the window toward screen-left, which is expressed as
`canonicalCenterX = 213 - offset` so that the principal point moves right and
more of the left-hand world enters the frame.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "blender"))

SPEC = (ROOT / "projects" / "hichaukitoden-game" / "assets" / "authoring"
        / "town" / "town-camera-next.json")
OFFSETS = (-96, 0, 96)


def calibrations(out_dir, offsets=OFFSETS):
    """Resolve one calibration per offset through LOVE."""
    from generate_town_camera_calibration import generate
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    base = json.loads(SPEC.read_text(encoding="utf-8"))
    made = {}
    for off in offsets:
        spec = json.loads(json.dumps(base))
        spec["projectionFrame"]["canonicalCenterX"] = (
            float(base["projectionFrame"]["canonicalCenterX"]) - float(off))
        spec_path = out_dir / ("spec_%+d.json" % off)
        spec_path.write_text(json.dumps(spec, indent=2), encoding="utf-8")
        cal = generate(out_dir / ("calibration_%+d.json" % off), spec_path)
        record = json.loads(Path(cal).read_text(encoding="utf-8"))
        record["projectionWindowOffsetX"] = float(off)
        Path(cal).write_text(json.dumps(record), encoding="utf-8")
        made[off] = str(cal)
    return made


BLENDER_SNIPPET = '''
import bpy, json, sys
sys.path.insert(0, {tools!r})
import thestra_camera as tc
from cleanroom import scene as cr_scene

record = json.loads(open({cal!r}, encoding="utf-8").read())
cam = bpy.data.objects.get("TH_CAMERA_PREVIEW")
scene = bpy.context.scene
cam = tc.create_or_update_camera(record, scene=scene, name="TH_CAMERA_PREVIEW",
                                 make_active=True)
for col in (bpy.data.collections.get("TH_RENDER"),
            bpy.data.collections.get("TH_COLLISION"),
            bpy.data.collections.get("TH_ANCHORS")):
    cr_scene.hide_render(col, True)
bpy.context.view_layer.update()
state = {{"lens": float(cam.data.lens),
          "eye": [round(v, 6) for v in cam.location],
          "shift_x": float(cam.data.shift_x),
          "shift_y": float(cam.data.shift_y),
          "offset": record["projectionWindowOffsetX"]}}
print("CAMSTATE " + json.dumps(state))
cr_scene.render({png!r}, samples={samples}, exposure=0.0)
'''


def render_strip(blend, calibration_paths, out_dir, *, samples=128,
                 blender=None):
    from town_environment_pipeline import blender_executable
    blender = blender or blender_executable()
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    frames, states = {}, {}
    for off, cal in calibration_paths.items():
        png = out_dir / ("window_%+d.png" % off)
        script = tempfile.NamedTemporaryFile(prefix="cr_proj_", suffix=".py",
                                             delete=False, mode="w",
                                             encoding="utf-8")
        script.write(BLENDER_SNIPPET.format(
            tools=str(ROOT / "tools" / "blender"), cal=str(cal),
            png=str(png), samples=samples))
        script.close()
        res = subprocess.run([blender, "--background", str(blend),
                              "--python", script.name],
                             capture_output=True, text=True)
        Path(script.name).unlink(missing_ok=True)
        line = [l for l in res.stdout.splitlines() if l.startswith("CAMSTATE ")]
        if res.returncode != 0 or not line:
            raise SystemExit("projection render failed for offset %s\n%s\n%s"
                             % (off, res.stdout[-3000:], res.stderr[-2000:]))
        states[off] = json.loads(line[-1][len("CAMSTATE "):])
        frames[off] = str(png)
        print("[projection] %+d lens=%.6f eye=%s shift_x=%.6f"
              % (off, states[off]["lens"], states[off]["eye"],
                 states[off]["shift_x"]))

    # The assertion that makes this a proof rather than three pictures.
    ref = states[0]
    for off, st in states.items():
        if abs(st["lens"] - ref["lens"]) > 1e-4:
            raise SystemExit("lens moved with the projection window: %s vs %s"
                             % (st["lens"], ref["lens"]))
        if st["eye"] != ref["eye"]:
            raise SystemExit("camera eye moved with the projection window: %s vs %s"
                             % (st["eye"], ref["eye"]))
    if abs(states[-96]["shift_x"] - states[96]["shift_x"]) < 1e-6:
        raise SystemExit("projection window did not actually move the frustum")
    print("[projection] PROJECTION_OK eye and lens invariant across %s"
          % list(states))
    return frames, states
