"""Bake an authored modelled exterior into its runtime environment package.

The exterior counterpart to ``export_room_environment.py``. The two differ in
exactly three ways, and each is a property of the subject rather than a choice:

* a room .blend has no contract collections, so the interior exporter
  synthesises TH_ANCHORS and TH_COLLISION from arguments; a town .blend builds
  its own from the map, so this one reuses what is already there;
* a room bakes every mesh, while a town source also holds level-design guides,
  scale actors and preview-only rigs that must never reach the atlas -- hence
  the include filter below;
* a room needs the stager's interior fill to match its plate, a street does
  not, so this runs the pipeline's flat profile.

    blender -b -noaudio --python tools/blender/export_exterior_environment.py --         --blend projects/.../st_maria_praca_modelled.blend         --output projects/.../environments/st_maria_town/praca_3d

## Known incomplete: the atlas packs to 9%

Geometry is exact -- this reproduces the shipped package's 9,304 triangles
exactly once the off-square duplicate is filtered. The ATLAS is not: it packs
to roughly 9% non-black coverage against the shipped package's 69%, and against
41.8% for an interior room through the same pipeline. The consequence is a
mostly empty atlas and far too few texels on each surface, which reads as a
dark, muddy street.

Lighting is staged below because an unlit bake is wrong regardless, and it does
move the mean from 0.8 to 2.5. It is not the cause. The cause is the UV layout
this rebuild hands the baker -- ``smart_project`` with ``island_margin=0.0`` on
a 24-metre street -- and that is the thing to fix next. Do not tune the lights
to chase the brightness; the atlas is empty, not dark.

## Not yet generic, and not yet mirrored

The render-mesh rebuild hardcodes the ``st_maria_praca`` names, and ``--span`` now bounds which
geometry counts as this street.

More importantly this does NOT apply the engine-space conversion that
``export_room_environment.py`` documents at length: no ``engine_y = centre -
blender_y`` mirror, and anchors keep the Blender lane x rather than moving to
the action plane. The shipped Praca package shows the consequence -- its
``spawn_player`` is ``[7.8, 11.85, 0]`` where an interior package's is
``[0.0, 6.1333, 0]``. Whether the exterior needs the same reflection is an open
question (#935), and guessing a mirror centre is silently wrong when mistaken,
so the behaviour is preserved exactly as PR #998 had it and the question is
left visible rather than answered here.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "blender"))

import town_environment_pipeline as pipeline  # noqa: E402
import stage_room_model as stager  # noqa: E402


GROUND_NAMES = {"ARCH_square_ground", "ARCH_low_curb"}
GROUND_TAG_MATERIAL = "TH_GROUND_ALLOC_TAG"


def _areas(mesh, tag_index):
    """Per-face 3D area and UV area, split into ground and everything else."""
    uv = mesh.uv_layers.active.data
    ground = [0.0, 0.0]
    other = [0.0, 0.0]
    for poly in mesh.polygons:
        world = poly.area
        pts = [uv[i].uv for i in poly.loop_indices]
        acc = 0.0
        for i in range(len(pts)):
            a, b = pts[i], pts[(i + 1) % len(pts)]
            acc += a.x * b.y - b.x * a.y
        bucket = ground if poly.material_index == tag_index else other
        bucket[0] += world
        bucket[1] += abs(acc) * 0.5
    return ground, other


def cull_enclosed(target, samples, escape_ratio):
    """Delete faces that are sealed inside the geometry.

    These are what bakes black, and the reason is not the camera. The house
    grammar builds closed bodies, so every wall has an inner face, every roof
    an underside, every box a hidden back. Nothing reaches those surfaces --
    no light, and no viewer either. They are not "offscreen" or "behind the
    camera"; a free camera could orbit forever and never see them without
    clipping through the building. They bake black because black is the honest
    answer for a surface sealed in a solid.

    So the test is reachability, not facing. From each face centre, fire a
    hemisphere of rays along its own normal and ask how many escape the mesh.
    A face on the outside of a wall has open sky in most directions; a face
    sealed inside a body has none. Only faces where NO ray escapes -- or fewer
    than ``escape_ratio`` of them -- are removed.

    Facing is deliberately not used. Culling by normal direction against the
    fixed side-view camera was tried and made things worse: it removed 1,306
    faces and the baked-black fraction went UP, 35.6% to 38.9%, because the
    back of a building is not the same set as the inside of one.
    """
    import mathutils
    from mathutils.bvhtree import BVHTree
    mesh = target.data
    bvh = BVHTree.FromPolygons([v.co.copy() for v in mesh.vertices],
                               [tuple(p.vertices) for p in mesh.polygons],
                               all_triangles=False)
    directions = []
    golden = math.pi * (3.0 - math.sqrt(5.0))
    for i in range(samples):
        z = 1.0 - (i + 0.5) / samples          # hemisphere, z in (0, 1]
        r = math.sqrt(max(0.0, 1.0 - z * z))
        theta = golden * i
        directions.append(mathutils.Vector((math.cos(theta) * r,
                                            math.sin(theta) * r, z)))
    doomed = []
    for poly in mesh.polygons:
        normal = poly.normal.normalized()
        up = mathutils.Vector((0.0, 0.0, 1.0))
        rot = up.rotation_difference(normal).to_matrix()
        origin = poly.center + normal * 1e-4
        escaped = 0
        for d in directions:
            if bvh.ray_cast(origin, rot @ d, 200.0)[0] is None:
                escaped += 1
                if escaped / samples > escape_ratio:
                    break
        if escaped / samples <= escape_ratio:
            doomed.append(poly)
    if not doomed:
        return 0
    for poly in mesh.polygons:
        poly.select = False
    for poly in doomed:
        poly.select = True
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.delete(type="FACE")
    bpy.ops.object.mode_set(mode="OBJECT")
    return len(doomed)


def reallocate_ground(target, ground_share):
    """Stop a flat ground plane from spending the atlas on itself.

    ``smart_project`` allocates UV area in proportion to WORLD area, which is
    the right default when every face matters equally. It is the wrong default
    here: the Praca's ground is a single 200x200 m quad, 98.4% of the scene's
    footprint in 12 triangles, so it claimed ~98% of the atlas and left the
    forty-five buildings and trees sharing the rest. The bake then read as
    1.1% written because that 98% is flat ground with nothing on it.

    A ground plane seen at a glancing angle needs far fewer texels per metre
    than a facade seen square-on, so this scales the ground islands down to a
    fixed ``ground_share`` of the atlas and repacks the rest into the space it
    releases. It does not delete the ground -- the shipped package
    has ground, and culling is a separate decision from texel weighting.

    This is the narrow, one-surface case of the camera-aware allocator in
    docs/design/town-authoring-known-good.md. It weights by surface class
    rather than by projected screen area, and reports its numbers so the
    allocation is reviewable rather than an invisible consequence of packing.
    """
    mesh = target.data
    tag_index = next((i for i, slot in enumerate(mesh.materials)
                      if slot and slot.name.startswith(GROUND_TAG_MATERIAL)), None)
    if tag_index is None:
        return
    ground, other = _areas(mesh, tag_index)
    if ground[0] <= 0 or other[0] <= 0 or ground[1] <= 0:
        return
    share = min(max(float(ground_share), 0.001), 0.9)
    # Solve for the scale that leaves the ground occupying `share` of the atlas
    # after packing: ground_uv * s^2 / (ground_uv * s^2 + other_uv) == share.
    #
    # A density RATIO is the wrong control here and it is worth saying why. The
    # ground is 94% of this scene's world area, so even at a quarter of the
    # buildings' texel density it still takes ~80% of the atlas. Expressing the
    # budget as a share of the texture is both intuitive and self-limiting: it
    # holds whatever the ground's size happens to be, which matters because an
    # authored ground plane is routinely far larger than the lane it serves.
    scale = math.sqrt((share / (1.0 - share)) * other[1] / ground[1])
    ground_uv_pct = 100 * ground[1] / (ground[1] + other[1])
    print(f"[exterior] ground held {ground_uv_pct:.1f}% of UV area for "
          f"{100 * ground[0] / (ground[0] + other[0]):.1f}% of world area; "
          f"scaling ground UVs by {scale:.4f} toward a {100 * share:.0f}% atlas share",
          flush=True)
    if scale >= 0.999:
        return

    uv = mesh.uv_layers.active.data
    loops = [i for poly in mesh.polygons if poly.material_index == tag_index
             for i in poly.loop_indices]
    cx = sum(uv[i].uv.x for i in loops) / len(loops)
    cy = sum(uv[i].uv.y for i in loops) / len(loops)
    for i in loops:
        uv[i].uv.x = cx + (uv[i].uv.x - cx) * scale
        uv[i].uv.y = cy + (uv[i].uv.y - cy) * scale

    # Repack so the space the ground gave up is actually taken by the buildings
    # rather than left as gutter. margin=0: no bleed, because the runtime
    # samples nearest and every gutter pixel is resolution spent on nothing.
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.select_all(action="SELECT")
    try:
        bpy.ops.uv.pack_islands(margin=0.0, rotate=True)
    except TypeError:
        bpy.ops.uv.pack_islands(margin=0.0)
    bpy.ops.object.mode_set(mode="OBJECT")
    ground, other = _areas(mesh, tag_index)
    print(f"[exterior] ground now {100 * ground[1] / (ground[1] + other[1]):.1f}% of UV area",
          flush=True)


def in_square(obj, span, margin):
    """Is this object part of the authored square, or parked outside it?

    A town source accumulates spare copies. `st_maria_praca_modelled.blend`
    carries a full duplicate of the chapel keeper's home at lane y -20..-17,
    roughly 40 metres off the square, and the name filter alone cannot tell it
    from the real one -- Blender's `.001` suffix is not a contract. Baking it
    added 1,992 triangles and a second building floating beside the terrace.

    So membership is name AND place: the lane runs 0..span, and anything whose
    centre falls outside that by more than `margin` is not this street.
    """
    centre = sum((obj.matrix_world @ Vector(corner) for corner in obj.bound_box),
                 Vector()) / 8.0
    return -margin <= centre.y <= span + margin


def rebuild_render_mesh(span, margin, ground_share, cull_samples, cull_escape) -> None:
    print("[exterior] preparing render mesh", flush=True)
    source = bpy.data.collections["TH_SOURCE"]
    render = bpy.data.collections["TH_RENDER"]
    render.hide_viewport = False
    render.hide_render = False
    def reveal(layer):
        if layer.collection == render:
            layer.exclude = False
            layer.hide_viewport = False
            return True
        return any(reveal(child) for child in layer.children)
    if not reveal(bpy.context.view_layer.layer_collection):
        raise RuntimeError("TH_RENDER is not linked into the active view layer")
    bpy.ops.object.mode_set(mode="OBJECT") if bpy.context.object and bpy.context.object.mode != "OBJECT" else None
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = None
    for obj in list(render.all_objects):
        print(f"[exterior] removing {obj.name}", flush=True)
        bpy.data.objects.remove(obj, do_unlink=True)

    seed_mesh = bpy.data.meshes.new("st_maria_praca_TH_RENDER_seed")
    seed = bpy.data.objects.new("st_maria_praca_TH_RENDER_seed", seed_mesh)
    render.objects.link(seed)
    copies = [seed]
    skipped = []
    ground_tagged = []
    ground_tag = bpy.data.materials.new(GROUND_TAG_MATERIAL)
    source_objects = list(source.all_objects)
    for obj in source_objects:
        if obj.type != "MESH" or obj.hide_render:
            continue
        if not (obj.name.startswith("STUDY_") or
                obj.name in {"ARCH_square_ground", "ARCH_low_curb"} or
                obj.name.startswith("FG_")):
            continue
        if not in_square(obj, span, margin):
            print(f"[exterior] SKIPPING off-square {obj.name}", flush=True)
            skipped.append(obj.name)
            continue
        print(f"[exterior] copying {obj.name}", flush=True)
        copy = obj.copy()
        copy.data = obj.data.copy()
        copy.name = f"R_{obj.name}"
        copy.hide_viewport = False
        copy.hide_render = False
        render.objects.link(copy)
        copy.hide_set(False)
        if obj.name in GROUND_NAMES:
            # Tag with a dedicated material slot. Object identity is lost in the
            # join, but material_index survives it, so this is how the allocator
            # finds the ground faces afterwards.
            copy.data.materials.append(ground_tag)
            for polygon in copy.data.polygons:
                polygon.material_index = len(copy.data.materials) - 1
            ground_tagged.append(obj.name)
        copies.append(copy)
    if not copies:
        raise RuntimeError("TH_SOURCE contains no renderable meshes")
    if skipped:
        print(f"[exterior] skipped {len(skipped)} off-square objects: "
              f"{', '.join(sorted(skipped))}", flush=True)

    bpy.ops.object.select_all(action="DESELECT")
    print(f"[exterior] selecting {len(copies)} copies", flush=True)
    for obj in copies:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = seed
    if len(bpy.context.selected_objects) != len(copies):
        raise RuntimeError(
            f"render join selection incomplete: {len(bpy.context.selected_objects)} "
            f"selected of {len(copies)}")
    if len(copies) > 1:
        bpy.ops.object.join()
    target = bpy.context.view_layer.objects.active
    if target is None or target.type != "MESH":
        raise RuntimeError("render join produced no active mesh")
    target.name = "st_maria_praca_TH_RENDER"
    target.select_set(True)
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=0.001)
    bpy.ops.mesh.dissolve_degenerate(threshold=0.001)
    bpy.ops.object.mode_set(mode="OBJECT")
    if cull_samples:
        culled = cull_enclosed(target, cull_samples, cull_escape)
        if culled:
            print(f"[exterior] culled {culled} sealed faces nothing can reach", flush=True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(66.0), island_margin=0.0)
    bpy.ops.object.mode_set(mode="OBJECT")
    if ground_tagged:
        reallocate_ground(target, ground_share)
    target.data.calc_loop_triangles()
    if len(target.data.loop_triangles) < 100:
        raise RuntimeError(
            f"render join is implausibly small: {len(target.data.loop_triangles)} triangles")
    print(f"[exterior] joined {len(copies)} source meshes into "
          f"{len(target.data.loop_triangles)} runtime triangles")


def main() -> None:
    argv = sys.argv[sys.argv.index("--") + 1:]
    parser = argparse.ArgumentParser()
    parser.add_argument("--blend", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--span", type=float, default=23.699,
                        help="lane length; geometry beyond it is not this street")
    parser.add_argument("--ambient", type=float, default=0.35,
                        help="world fill strength for the bake")
    parser.add_argument("--sun", type=float, default=2.5,
                        help="hard key energy; exteriors get one, interiors do not")
    parser.add_argument("--ground-share", type=float, default=0.15,
                        help="fraction of the atlas the ground may occupy; the "
                             "rest goes to the buildings and foliage")
    parser.add_argument("--cull-samples", type=int, default=24,
                        help="hemisphere rays per face when testing reachability")
    parser.add_argument("--cull-escape", type=float, default=0.0,
                        help="keep a face if more than this fraction of its rays escape")
    parser.add_argument("--keep-sealed", action="store_true",
                        help="disable sealed-face culling")
    parser.add_argument("--margin", type=float, default=6.0,
                        help="how far past the lane ends geometry may still belong")
    parser.add_argument("--atlas-size", type=int, default=1024)
    parser.add_argument("--samples", type=int, default=24)
    args = parser.parse_args(argv)

    opened = Path(bpy.data.filepath).resolve() if bpy.data.filepath else None
    if opened != args.blend.resolve():
        bpy.ops.wm.open_mainfile(filepath=str(args.blend.resolve()))
    rebuild_render_mesh(args.span, args.margin, args.ground_share,
                        0 if args.keep_sealed else args.cull_samples, args.cull_escape)

    # Same reason export_room_environment.py stages lighting before baking: a
    # Cycles bake that just opens the file is lit by whatever the .blend last
    # saved, and this one saves a near-black world (0.0, 0.092, 0.119) with a
    # single sun at energy 3. Baked as-is the atlas comes out at mean RGB
    # 0.8/0.9/0.7 against the shipped package's 30.0/27.6/23.9 -- a cave. The
    # interior uses an even fill because a room is lit by what it contains; a
    # street gets the fill AND the hard key, which is what outdoor_sun is for.
    stager.base_lighting(args.ambient, (0.0, 0.0, 0.0), stager.INTERIOR_FILL)
    stager.outdoor_sun(args.sun)

    output = args.output.resolve()
    pipeline.run_pipeline_in_blender(args.blend.resolve(), output,
                                     atlas_size=args.atlas_size,
                                     bake_samples=args.samples,
                                     flat_bake=True)
    print("EXTERIOR 3D EXPORT OK")


if __name__ == "__main__":
    main()
