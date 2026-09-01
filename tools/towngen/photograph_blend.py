"""Photograph an authored town .blend and measure the invariants it produces.

    blender --background <file.blend> --python tools/towngen/photograph_blend.py -- \
        --out out/towngen/praca --width 256

`st_maria_praca.blend` already carries the answer this tool exists to check: its
camera is pitched 17.5 degrees down (rot X = 107.5, where level is 90), with the
principal point moved by shift_y to compensate, at the contract's eye height and
horizontal distance. So the first job is not to impose a camera but to REPORT
the authored one, and measure where a 1.75 m actor actually lands.

Traps obeyed:
  * `TH_RENDER`, `TH_COLLISION`, `TH_ANCHORS` and the preview collections are
    authoring scaffolding and are already hide_render; nothing here un-hides
    them.
  * `SCALE_*` guides ARE renderable in the file, and would appear as boxes in a
    plate, so they are hidden for the photograph and measured separately.
  * a relative render path resolves against the drive root, so paths are made
    absolute.
  * the blend is authored under AgX; the runtime contract is Standard. Both are
    rendered, because which one the shipped plates match is a real question.
"""

import argparse
import math
import os
import sys

import bpy

SCAFFOLD_PREFIXES = ("SCALE_", "LD_", "COL_", "RT_")


def argv():
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="out/towngen/praca")
    p.add_argument("--width", type=int, default=256)
    p.add_argument("--height", type=int, default=240)
    p.add_argument("--correct", action="store_true",
                   help="re-solve the camera so BOTH invariants hold, instead of "
                        "photographing the authored one")
    p.add_argument("--horizon-y", type=float, default=66.0)
    return p.parse_args(a)


def report_camera(cam, width, height):
    d = cam.data
    rx = math.degrees(cam.rotation_euler[0])
    larger = float(max(width, height))
    print("AUTHORED CAMERA")
    print("  location        (%.4f, %.4f, %.4f)" % tuple(cam.matrix_world.translation))
    print("  rotation x      %.3f deg  -> pitch %.3f deg below level"
          % (rx, rx - 90.0))
    print("  lens            %.4f mm on %.1f sensor -> %.4f deg horizontal"
          % (d.lens, d.sensor_width, math.degrees(d.angle_x)))
    print("  shift           x %.5f  y %.5f  (%.1f px of %d at this width)"
          % (d.shift_x, d.shift_y, d.shift_y * larger, width))
    return rx - 90.0


def measure_actor(scene, cam, width, height):
    """Where does the authored 1.75 m actor guide actually land?"""
    from bpy_extras.object_utils import world_to_camera_view
    guide = bpy.data.objects.get("SCALE_actor_1.75m")
    if guide is None:
        print("  (no SCALE_actor_1.75m guide in this file)")
        return
    base = guide.matrix_world.translation.copy()
    half = guide.dimensions.z / 2.0
    feet, head = base.copy(), base.copy()
    feet.z -= half
    head.z += half
    fx, fy, _ = world_to_camera_view(scene, cam, feet)
    hx, hy, _ = world_to_camera_view(scene, cam, head)
    # world_to_camera_view is 0..1 with +y UP; native screen y is +down.
    feet_px = (1.0 - fy) * height
    head_px = (1.0 - hy) * height
    print("MEASURED, from the authored SCALE_actor_1.75m guide")
    print("  feet native y   %.2f      (contract: 128)" % feet_px)
    print("  head native y   %.2f" % head_px)
    print("  sprite height   %.2f px   (contract: 48)" % (feet_px - head_px))
    print("  centre x        %.2f px of %d" % (fx * width, width))


def apply_corrected(cam, width, height, horizon_y):
    """Re-solve so a view-aligned actor is 1:1 AND its feet land at base y.

    The authored camera solves base y and not pixel scale. Keeping the authored
    pitch and the actor plane where it is, this moves the eye and the principal
    point until both invariants hold at once.
    """
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import camera_modes as cm
    theta = math.radians(17.5)
    dist, height_units, principal = cm.solve_billboard(theta, horizon_y)

    actor = bpy.data.objects.get("SCALE_actor_1.75m")
    plane_x = actor.matrix_world.translation.x if actor else 7.8
    lane_y = actor.matrix_world.translation.y if actor else 11.85

    d = cam.data
    # The lens is not sacred - the two invariants are - but it does have to be
    # the one the solve assumed, or the pixel scale it computed is not the one
    # the render produces.
    d.angle_x = 2.0 * math.atan((width / 2.0) / cm.K)
    d.shift_y = (principal - height / 2.0) / float(max(width, height))
    cam.rotation_euler = (math.radians(107.5), 0.0, math.radians(-90.0))
    cam.location = (plane_x - dist, lane_y, height_units)
    print("CORRECTED CAMERA")
    print("  distance        %.4f   eye %.4f   principal %.2f"
          % (dist, height_units, principal))
    print("  lens            %.4f deg horizontal (K = %.2f px)"
          % (math.degrees(d.angle_x), cm.K))


def render(scene, path, transform, width, height):
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = transform
    scene.render.filepath = os.path.abspath(path)
    bpy.ops.render.render(write_still=True)
    return os.path.abspath(path)


def main():
    a = argv()
    scene = bpy.context.scene
    cam = scene.camera or bpy.data.objects.get("TH_CAMERA_PREVIEW")
    scene.camera = cam
    pitch = report_camera(cam, a.width, a.height)
    measure_actor(scene, cam, a.width, a.height)
    if a.correct:
        apply_corrected(cam, a.width, a.height, a.horizon_y)
        measure_actor(scene, cam, a.width, a.height)

    # Scale guides and lane markers are authoring aids, not architecture.
    hidden = []
    for o in bpy.data.objects:
        if o.type == "MESH" and o.name.startswith(SCAFFOLD_PREFIXES) and not o.hide_render:
            o.hide_render = True
            hidden.append(o.name)
    if hidden:
        print("  hidden for the photograph: %s" % ", ".join(hidden))

    os.makedirs(os.path.abspath(a.out), exist_ok=True)
    for transform in ("Standard", "AgX"):
        p = render(scene, os.path.join(a.out, "praca_%s%s.png" % ("corrected_" if a.correct else "", transform.lower())),
                   transform, a.width, a.height)
        print("wrote %s" % p)
    print("PHOTOGRAPH OK  pitch %.2f deg" % pitch)


if __name__ == "__main__":
    main()
