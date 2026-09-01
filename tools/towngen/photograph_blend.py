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
    p.add_argument("--stitch", type=int, default=0, metavar="TILE",
                   help="render the plate as panned windows TILE px wide and "
                        "composite them, instead of widening the lens")
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


def probe(scene, cam, width, height):
    """Feet native y and actor pixel height, straight from the renderer."""
    from bpy_extras.object_utils import world_to_camera_view
    g = bpy.data.objects["SCALE_actor_1.75m"]
    base = g.matrix_world.translation.copy()
    half = g.dimensions.z / 2.0
    feet, head = base.copy(), base.copy()
    feet.z -= half
    head.z += half
    _fx, fy, _ = world_to_camera_view(scene, cam, feet)
    _hx, hy, _ = world_to_camera_view(scene, cam, head)
    return (1.0 - fy) * height, ((1.0 - fy) - (1.0 - hy)) * height


def apply_corrected(scene, cam, width, height, horizon_y, tile_width=None):
    """Calibrate the camera against the RENDERER until both invariants hold.

    An analytic solve has to model the rig's conventions exactly, and this file's
    rig is Euler (107.5, 0, -90) - a pitch plus a roll, whose sensor axes do not
    match a basis built from forward/right/up. Two sign errors came out of
    hand-deriving that today.

    So this does not model the renderer, it MEASURES it. Actor pixel height
    depends on camera distance and feet position on the principal point; the two
    are near-independent and each is monotonic, so alternating secant steps
    converge in a few passes and cannot be wrong about a convention.
    """
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import camera_modes as cm
    tile_width = tile_width or width

    g = bpy.data.objects["SCALE_actor_1.75m"]
    plane_x = g.matrix_world.translation.x
    lane_y = g.matrix_world.translation.y
    cam.rotation_euler = (math.radians(107.5), 0.0, math.radians(-90.0))
    # The TILE sets the lens, not the plate: a stitched plate keeps the
    # contract lens and pans the window.
    cam.data.angle_x = 2.0 * math.atan((tile_width / 2.0) / cm.K)

    # The SCALE_actor guide is a world-vertical BOX and keystones; the actor is
    # a view-aligned billboard and does not. Calibrating pixel height against
    # the box therefore targets the wrong thing - it lands the box on 48px and
    # the billboard on 42.5px.
    #
    # A billboard's height depends only on the SLANT distance to its ground
    # point, so that half is analytic and exact: slant must equal DISTANCE.
    # Only the principal point needs measuring, because only its mapping to
    # shift_y depends on the rig's conventions.
    eye = 2.2604166666666665
    theta = math.radians(17.5)
    dist = (cm.DISTANCE - eye * math.sin(theta)) / math.cos(theta)
    shift = cam.data.shift_y

    def place(sh):
        cam.location = (plane_x - dist, lane_y, eye)
        cam.data.shift_y = sh
        bpy.context.view_layer.update()

    for _ in range(40):
        place(shift)
        feet, _px = probe(scene, cam, width, height)
        if abs(feet - 128.0) < 0.01:
            break
        place(shift + 0.05)
        feet2, _ = probe(scene, cam, width, height)
        grad = (feet2 - feet) / 0.05
        if abs(grad) < 1e-9:
            break
        shift += (128.0 - feet) / grad
    place(shift)

    v = (dist, -eye)
    f = (math.cos(theta), -math.sin(theta))
    slant = v[0] * f[0] + v[1] * f[1]
    billboard_px = cm.WALKER_UNITS * cm.K / slant

    feet, px = probe(scene, cam, width, height)
    print("CORRECTED CAMERA (calibrated against the renderer)")
    print("  distance        %.4f   eye %.4f   shift_y %.5f" % (dist, eye, shift))
    print("  lens            %.4f deg horizontal"
          % math.degrees(cam.data.angle_x))
    print("  slant to actor  %.4f   (contract: %.4f)" % (slant, cm.DISTANCE))
    print("  -> feet %.2f (want 128)" % feet)
    print("  -> view-aligned billboard %.2f px (want %d)"
          % (billboard_px, cm.WALKER_PX))
    print("  -> world-vertical guide   %.2f px (keystones; NOT the invariant)" % px)


def render_stitched(scene, cam, path, transform, width, height, tile):
    """Render the plate as panned projection windows and composite them.

    A wide plate cannot be photographed in one shot. Keeping pixel scale
    constant while widening the frame means widening the LENS - 730px at the
    contract scale needs 71.5 degrees - and a plate shot that wide has correct
    perspective only at its centre.

    The engine's own answer is the projection window: it tracks horizontally by
    moving the window, not the camera. A window offset is a principal-point
    shift, which is a SHEAR of the projection rather than a rotation, so
    consecutive windows share one eye and one lens and stitch exactly. Rendering
    the plate the same way is not a workaround; it is what the runtime does.
    """
    base_shift_x = cam.data.shift_x
    larger = float(max(tile, height))
    n = int(math.ceil(width / float(tile)))
    out_dir = os.path.dirname(os.path.abspath(path))
    for i in range(n):
        centre_px = (i + 0.5) * tile - (n * tile) / 2.0
        # Same -90 roll that inverts shift_y: the pan runs the other way.
        cam.data.shift_x = base_shift_x + centre_px / larger
        render(scene, os.path.join(out_dir, "_tile_%02d.png" % i),
               transform, tile, height)
    cam.data.shift_x = base_shift_x
    print("  TILES %d %d %d %s" % (n, tile, width, out_dir))
    print("  stitched %d windows of %dpx at the contract lens" % (n, tile))
    return os.path.abspath(path)


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
        apply_corrected(scene, cam, a.width, a.height, a.horizon_y,
                        a.stitch or None)

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
        dest = os.path.join(a.out, "praca_%s%s.png"
                            % ("corrected_" if a.correct else "", transform.lower()))
        if a.stitch:
            p = render_stitched(scene, cam, dest, transform, a.width, a.height, a.stitch)
        else:
            p = render(scene, dest, transform, a.width, a.height)
        print("wrote %s" % p)
    print("PHOTOGRAPH OK  pitch %.2f deg" % pitch)


if __name__ == "__main__":
    main()
