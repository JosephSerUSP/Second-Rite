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

## Atlas coverage

The atlas once packed to roughly 9% non-black coverage. That was the circular
bake-image dependency of #1023, closed by #1069: ``town_environment_pipeline.py``
keeps the bake target's image node unlinked from the shader until the bake
completes.

Measured 29.09.2026 under Blender 5.2.2 on ``st_maria_praca_modelled.blend``
with the default options: a 2048 x 2048 atlas with 43.3% of its pixels written
("written" as #1023 defines it: any non-zero channel), mean 48.5 over the
written pixels, and no ``Circular dependency`` message during the bake. The same
run joined 37 source meshes into 5,854 runtime triangles after culling 1,713
sealed faces (``--keep-sealed`` keeps them). The 9,304-triangle figure this
module once quoted was measured before that cull existed and is not repeated.

Lighting is still staged below, since an unlit bake is wrong regardless.

## The ground (#1287)

`ARCH_square_ground` is a zero-thickness sheet with a duplicate underside, 200 x 200 m. The sealed-face cull
took it for a closed solid, deleted its top and kept the underside facing down, and the Cycles bake (which casts
along the target's normal) baked that face black: the package that shipped until this was fixed had a black
ground. Three things now happen to it: `flatten_ground_sheet` keeps only the face that looks up and marks it an
open surface; `clip_ground_to_view` cuts it to what the lane cameras can see plus a margin (40,000 m2 became
4,681); and the atlas is allocated by view (`--atlas-layout view`, the default), not by a fixed 3% ground share,
because the ground is 59% of the pixels of a frame. `--keep-full-ground` and `--atlas-layout legacy` are the
old behaviour, kept for comparison.

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

import bmesh
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "blender"))

import render_profiles
import atlas_allocation  # noqa: E402
import atlas_alpha  # noqa: E402
import eevee_bake  # noqa: E402
import town_environment_pipeline as pipeline  # noqa: E402
import stage_room_model as stager  # noqa: E402
import ground_cover  # noqa: E402  (owns the bake-source marker name)


GROUND_NAMES = {"ARCH_square_ground", "ARCH_low_curb"}
# The authored ground is a zero-thickness sheet with a duplicate underside; see flatten_ground_sheet.
SHEET_THICKNESS = 1e-4
# How far past what the lane cameras can see the ground is kept, in metres (None keeps the whole plane).
GROUND_CLIP_MARGIN = 2.0
GROUND_TAG_MATERIAL = "TH_GROUND_ALLOC_TAG"
# Face attribute that survives the join: marks faces of open cards (foliage), which the sealed-face cull must
# neither delete nor count as a surface.
OPEN_FACE_ATTRIBUTE = "sr_open_surface"


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


PARITY_DIRECTIONS = ((0.9427, 0.2357, 0.2357), (-0.2357, 0.9427, 0.2357),
                     (0.2357, -0.2357, 0.9427), (-0.7071, -0.5, 0.5),
                     (0.5, -0.7071, -0.5))


def _crossings(bvh, point, direction, limit=64):
    """How many surfaces a ray pierces on its way out."""
    count = 0
    origin = point.copy()
    for _ in range(limit):
        hit = bvh.ray_cast(origin, direction, 500.0)
        if hit[0] is None:
            break
        count += 1
        origin = hit[0] + direction * 1e-4
    return count


def cull_enclosed(target, samples, escape_ratio):
    """Delete faces sealed inside the geometry, by an inside/outside test.

    These are what bakes black, and the reason is not the camera. The house
    grammar builds closed bodies, so every wall has an inner face, every roof
    an underside, every box a hidden back. Nothing reaches those surfaces --
    no light, and no viewer either. A free camera could orbit forever and
    never see them without clipping through the building.

    The test is PARITY, not ray escape. Firing a hemisphere of rays and asking
    whether any escapes sounds equivalent and is not: a face visible only
    through a narrow aperture -- a window reveal, a gap between buildings --
    has most directions blocked, so finite sampling calls it sealed. That bias
    is measurable and does not converge. Culling the same mesh with an
    escaping-ray test gave 2876 faces at 24 samples, 2752 at 64, 2635 at 128,
    2569 at 256 and 2508 at 512, still falling; the owner saw the consequence
    as facade faces missing from the export. Counting how many surfaces a ray
    pierces on its way out answers the actual question -- odd means the point
    began inside a solid -- and it is unbiased and cheaper. It reports 1713
    sealed faces, so the escape test was removing about 1163 it should not.

    Five directions are polled and the majority wins, so one grazing ray along
    a coplanar seam cannot decide a face on its own.

    ``samples`` and ``escape_ratio`` are retained for the CLI but no longer
    steer the classification; the parity test has no sampling knob to turn.
    """
    import mathutils
    from mathutils.bvhtree import BVHTree
    mesh = target.data
    # Parity is only meaningful for closed bodies. An open card (a ground-cover tuft is two crossed quads) has no
    # inside: left in, it is culled for being "crossed" by its own twin, and it flips the verdict on any solid face
    # whose ray happens to pass through it. So open faces are neither candidates nor occluders.
    marks = mesh.attributes.get(OPEN_FACE_ATTRIBUTE)
    is_open = [d.value for d in marks.data] if marks else [False] * len(mesh.polygons)
    solid = [p for p in mesh.polygons if not is_open[p.index]]
    bvh = BVHTree.FromPolygons([v.co.copy() for v in mesh.vertices],
                               [tuple(p.vertices) for p in solid],
                               all_triangles=False)
    directions = [mathutils.Vector(d).normalized() for d in PARITY_DIRECTIONS]
    needed = len(directions) // 2 + 1
    doomed = []
    for poly in solid:
        # Start just OUTSIDE the face along its own normal: an outward-facing
        # skin face is then outside its body, an inward-facing one is inside.
        point = poly.center + poly.normal.normalized() * 1e-3
        votes = 0
        for direction in directions:
            if _crossings(bvh, point, direction) % 2 == 1:
                votes += 1
                if votes >= needed:
                    break
        if votes >= needed:
            doomed.append(poly)
    if not doomed:
        return 0
    # Delete through bmesh, not by flagging polygons and running mesh.delete: that operator acts on the *edit-mode*
    # selection, and vertices left selected by an earlier select_all flush every face into it. On a small mesh that
    # deleted all 574 faces when 135 were doomed; the Praca only escaped by the luck of its selection state.
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[bm.faces[poly.index] for poly in doomed], context="FACES")
    bm.to_mesh(mesh)
    bm.free()
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


def is_bake_source(obj):
    """Does this object belong in the baked render mesh?

    An explicit marker (`ground_cover.BAKE_PROPERTY`, a custom property) is the
    contract for anything added after the name filter existed; the historical
    name rule is kept only so the owner's untouched source still bakes the
    same. Names are not a contract, so new content must not rely on them.
    """
    if obj.get(ground_cover.BAKE_PROPERTY):
        return True
    return (obj.name.startswith("STUDY_") or obj.name in GROUND_NAMES
            or obj.name.startswith("FG_"))


def bake_role(obj):
    """Source detail can illuminate a simple receiver without shipping its geometry."""
    role = obj.get("sr_bake_role", "both")
    if role not in ("both", "source", "receiver"):
        raise ValueError(f"{obj.name}: unknown sr_bake_role {role!r}")
    return role


def live_modifiers(obj):
    return [m for m in obj.modifiers if m.show_render]


def evaluated(obj):
    """(evaluated object, its depsgraph), freshly updated.

    The depsgraph must be re-fetched at the point of use: the rebuild links each
    copy into the scene as it goes, which dirties an earlier depsgraph, and a
    Geometry Nodes host evaluated against a stale one comes back empty.
    """
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    return obj.evaluated_get(depsgraph), depsgraph


def realised_mesh(obj):
    """A standalone mesh holding what `obj` renders, modifiers applied.

    `obj.data.copy()` is the object's *base* mesh: a Geometry Nodes host such as
    the ground cover has an empty base mesh, so copying it bakes nothing and
    says nothing (measured: identical triangle counts with and without cover).
    An object with live modifiers is therefore evaluated; one without is copied
    exactly as before, so an unmodified source bakes byte-for-byte the same.

    Raises when a modifier-bearing object realises to nothing -- that is a
    broken node tree or a missing input, and a silent empty bake is the failure
    this exists to prevent.
    """
    if not live_modifiers(obj):
        return obj.data.copy()
    evaluated_obj, depsgraph = evaluated(obj)
    mesh = bpy.data.meshes.new_from_object(evaluated_obj, preserve_all_data_layers=True,
                                           depsgraph=depsgraph)
    if mesh is None or not len(mesh.vertices):
        raise RuntimeError(
            f"{obj.name} has live modifiers ({', '.join(m.name for m in live_modifiers(obj))}) "
            "but evaluates to an empty mesh; refusing to bake it silently as nothing")
    return mesh


def flatten_ground_sheet(obj):
    """Make a zero-thickness ground sheet one upward-facing, open surface.

    `ARCH_square_ground` is 8 vertices and 6 faces that all lie in one plane: a top, an underside facing
    the other way, and four sides of no area. To the parity cull (see `cull_enclosed`) that is a closed
    solid, so it judged the TOP face sealed and deleted it, leaving the 200 x 200 m underside facing down
    (#1287). Cycles' selected-to-active bake casts along the target's normal, so a face pointing down
    casts away from its source, hits nothing and bakes black: the shipped Praca package has a black ground.

    A sheet has no inside. Keep only the faces that face up and have an area, and mark them as open
    surfaces (the cull neither tests them nor counts them as occluders). Returns what was dropped, or None
    when `obj` is not a sheet and is left exactly as it was.

    The SOURCE sheet needs it too, not only the copy that is joined into the render mesh. The Cycles bake
    casts at the source, and with a top and an underside at the same height the ray can land on the
    underside: measured on a small scene, a correctly facing target over the unflattened source bakes
    mean 0.0 and over the flattened one mean 0.82. The exporter never saves the document, so the source is
    flattened in memory; the `.blend` on disk is untouched.
    """
    if obj.dimensions.z >= SHEET_THICKNESS:
        return None
    rotation = obj.matrix_world.to_3x3()
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.faces.ensure_lookup_table()
    doomed = [f for f in bm.faces if f.calc_area() <= 1e-9 or (rotation @ f.normal).z <= 0.0]
    total = len(bm.faces)
    bmesh.ops.delete(bm, geom=doomed, context="FACES")
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    marks = mesh.attributes.get(OPEN_FACE_ATTRIBUTE) or mesh.attributes.new(OPEN_FACE_ATTRIBUTE, "BOOLEAN", "FACE")
    marks.data.foreach_set("value", [True] * len(mesh.polygons))
    return {"object": obj.name, "faces": total, "dropped": len(doomed), "kept": total - len(doomed)}


def visible_ground_bounds(target, tag_index, span, columns=48, rows=27):
    """(xmin, xmax, ymin, ymax, hits): where the ground is actually seen from the lane cameras.

    Casts a grid of rays through each lane camera's frame at the joined render mesh, so a ground point
    that a building hides is not counted. The camera is the game's side-view camera, widened to the
    426 px view, at both ends of the walkable lane and eight places between.
    """
    from mathutils.bvhtree import BVHTree
    mesh = target.data
    bvh = BVHTree.FromPolygons([v.co.copy() for v in mesh.vertices],
                               [tuple(p.vertices) for p in mesh.polygons], all_triangles=False)
    scene = bpy.context.scene
    positions = lane_positions(span)
    points = []
    for lane_y in positions:
        camera = atlas_allocation.lane_camera(scene, lane_y, mirrored=False)
        corners = camera.data.view_frame(scene=scene)
        xs, ys, z = [c.x for c in corners], [c.y for c in corners], corners[0].z
        rotation = camera.matrix_world.to_3x3()
        origin = camera.matrix_world.translation
        for i in range(columns):
            for j in range(rows):
                x = min(xs) + (max(xs) - min(xs)) * (i + 0.5) / columns
                y = min(ys) + (max(ys) - min(ys)) * (j + 0.5) / rows
                hit = bvh.ray_cast(origin, (rotation @ Vector((x, y, z))).normalized(), 1000.0)
                if hit[0] is not None and mesh.polygons[hit[2]].material_index == tag_index:
                    points.append(hit[0])
    if not points:
        return None
    return (min(p.x for p in points), max(p.x for p in points),
            min(p.y for p in points), max(p.y for p in points), len(points))


def clip_ground_to_view(target, span, margin):
    """Cut the ground down to what the lane cameras can see, plus `margin` metres.

    The authored ground is 200 x 200 m for a street 23.7 m long that only ever looks at a strip of it.
    Left whole, it gets a few per cent of the atlas spread over 40,000 m2, about 2 texels per m2 and a
    hundredth of a texel per screen pixel. Returns a report, or None when there is nothing to clip.
    """
    mesh = target.data
    tag_index = next((i for i, slot in enumerate(mesh.materials)
                      if slot and slot.name.startswith(GROUND_TAG_MATERIAL)), None)
    if tag_index is None:
        return None
    bounds = visible_ground_bounds(target, tag_index, span)
    if bounds is None:
        print("[exterior] no ground is visible from the lane cameras; leaving it whole", flush=True)
        return None
    xmin, xmax, ymin, ymax, hits = bounds
    bm = bmesh.new()
    bm.from_mesh(mesh)
    before = sum(f.calc_area() for f in bm.faces if f.material_index == tag_index)
    for plane_co, plane_no in ((Vector((xmin - margin, 0, 0)), Vector((-1, 0, 0))),
                               (Vector((xmax + margin, 0, 0)), Vector((1, 0, 0))),
                               (Vector((0, ymin - margin, 0)), Vector((0, -1, 0))),
                               (Vector((0, ymax + margin, 0)), Vector((0, 1, 0)))):
        faces = [f for f in bm.faces if f.material_index == tag_index]
        geom = list(faces) + list({e for f in faces for e in f.edges}) + list({v for f in faces for v in f.verts})
        bmesh.ops.bisect_plane(bm, geom=geom, plane_co=plane_co, plane_no=plane_no, clear_outer=True)
    bm.faces.ensure_lookup_table()
    after = sum(f.calc_area() for f in bm.faces if f.material_index == tag_index)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    report = {"hits": hits, "areaBefore": round(before, 1), "areaAfter": round(after, 1),
              "bounds": [round(v, 2) for v in (xmin - margin, xmax + margin, ymin - margin, ymax + margin)]}
    print(f"[exterior] ground clipped to what the lane cameras see: {before:.0f} m2 -> {after:.0f} m2 "
          f"(x {report['bounds'][0]}..{report['bounds'][1]}, y {report['bounds'][2]}..{report['bounds'][3]})", flush=True)
    return report


def lane_positions(span):
    """Where the game's camera can stand: both ends of the walkable lane and eight places between."""
    return [0.35] + [0.6 + i * (span - 1.2) / 8 for i in range(9)] + [span - 0.35]


def allocate_atlas_by_view(target, span, atlas_size):
    """Unwrap, and spend the atlas where the lane cameras look (#877). Returns the allocator's report.

    The ground is 59% of the pixels of a Praca frame and used to get a fixed 3% of the atlas, chosen when
    the ground was a 200 m quad measured at 0.00 texels per screen pixel. Measuring what each camera sees
    replaces that constant. The measuring pass renders the joined mesh alone, so every other mesh in the
    document is hidden from it for the moment.
    """
    hidden = [o for o in bpy.data.objects if o.type == "MESH" and o != target and not o.hide_render]
    for obj in hidden:
        obj.hide_render = True
    try:
        # exterior sources are in engine space already: no mirror (see the module docstring)
        return atlas_allocation.allocate_by_view(target, lane_positions(span), atlas_size, mirrored=False)
    finally:
        for obj in hidden:
            obj.hide_render = False


def bake_source_members(source, span, margin):
    """Beauty source meshes, including detail that is baked onto separate receivers.

    The rest of TH_SOURCE (level-design guides, scale actors, preview rigs) must never reach the atlas.
    """
    members = []
    for obj in source.all_objects:
        if not obj or obj.type != "MESH" or obj.hide_render or not is_bake_source(obj):
            continue
        if bake_role(obj) == "receiver":
            continue
        if in_square(evaluated(obj)[0] if live_modifiers(obj) else obj, span, margin):
            members.append(obj)
    return members


def rebuild_render_mesh(span, margin, ground_share, cull_samples, cull_escape,
                        clip_ground=GROUND_CLIP_MARGIN, layout="view", atlas_size=2048) -> None:
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
    unbaked_modifiers = []
    for obj in source_objects:
        if obj.type != "MESH":
            continue
        role = bake_role(obj)
        if role == "source" or (obj.hide_render and role != "receiver"):
            continue
        if not is_bake_source(obj):
            if live_modifiers(obj):
                unbaked_modifiers.append(obj.name)
            continue
        if not in_square(evaluated(obj)[0] if live_modifiers(obj) else obj, span, margin):
            print(f"[exterior] SKIPPING off-square {obj.name}", flush=True)
            skipped.append(obj.name)
            continue
        print(f"[exterior] copying {obj.name}", flush=True)
        if obj.name in GROUND_NAMES:
            flatten_ground_sheet(obj)       # in memory, for the Cycles bake: see its docstring
        copy = obj.copy()
        # A derived render proxy belongs to the render collection, not the
        # authored assembly hierarchy. Preserve placement before detaching:
        # moved assembly roots need world space, and the source hierarchy must
        # not acquire temporary children belonging to the render export.
        copy.parent = None
        copy.matrix_world = obj.matrix_world.copy()
        copy.data = realised_mesh(obj)
        atlas_alpha.preserve_uv(copy.data)
        copy.modifiers.clear()      # already applied above; join must not see them
        import mesh_export_geometry
        is_open = mesh_export_geometry.prepare(copy.data)
        if obj.get(ground_cover.OPEN_SURFACE_PROPERTY) or is_open:
            marks = copy.data.attributes.get(OPEN_FACE_ATTRIBUTE) or copy.data.attributes.new(OPEN_FACE_ATTRIBUTE, "BOOLEAN", "FACE")
            marks.data.foreach_set("value", [True] * len(copy.data.polygons))
        copy.name = f"R_{obj.name}"
        copy.hide_viewport = False
        copy.hide_render = False
        render.objects.link(copy)
        copy.hide_set(False)
        if obj.name in GROUND_NAMES:
            flattened = flatten_ground_sheet(copy)
            if flattened:
                print(f"[exterior] {flattened['object']} is a zero-thickness sheet: kept {flattened['kept']} of "
                      f"{flattened['faces']} faces (the ones facing up)", flush=True)
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
    if unbaked_modifiers:
        # Not an error: the owner's source has such objects (mirrored houses) and
        # has always baked without them. It is loud so nobody has to discover it.
        print(f"[exterior] WARNING {len(unbaked_modifiers)} renderable objects carry modifiers "
              f"but are not bake sources and are left out: {', '.join(sorted(unbaked_modifiers))}",
              flush=True)
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
    if target and target.data.uv_layers.get(atlas_alpha.ATLAS_UV):
        target.data.uv_layers.active = target.data.uv_layers[atlas_alpha.ATLAS_UV]
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
    if ground_tagged and clip_ground is not None:
        clip_ground_to_view(target, span, clip_ground)
    if layout == "view":
        report = allocate_atlas_by_view(target, span, atlas_size)
        print(f"[exterior] atlas allocated by view: {report['visiblePolygons']} of {report['polygons']} faces "
              f"are seen, {report['visibleIslands']} of {report['islands']} islands", flush=True)
    else:
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.smart_project(angle_limit=math.radians(66.0), island_margin=0.0)
        bpy.ops.object.mode_set(mode="OBJECT")
        if ground_tagged:
            reallocate_ground(target, ground_share)
    target.data.calc_loop_triangles()
    bpy.context.view_layer.update()
    if len(target.data.loop_triangles) < 100:
        raise RuntimeError(
            f"render join is implausibly small: {len(target.data.loop_triangles)} triangles")
    print(f"[exterior] joined {len(copies)} source meshes into "
          f"{len(target.data.loop_triangles)} runtime triangles")


def camera_provenance(path):
    """Carry the actual serialized resolver output, without a second camera schema."""
    path=Path(path).resolve()
    source=path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else path.name
    return {"source":source,"record":json.loads(path.read_text(encoding="utf-8"))}


def main() -> None:
    argv = sys.argv[sys.argv.index("--") + 1:]
    parser = argparse.ArgumentParser()
    parser.add_argument("--blend", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--camera", type=Path, default=atlas_allocation.CAMERA_RECORD,
                        help="resolved WorldCamera calibration used for atlas projection")
    parser.add_argument("--span", type=float, default=23.699,
                        help="lane length; geometry beyond it is not this street")
    parser.add_argument("--ambient", type=float, default=0.35,
                        help="world fill strength for the bake")
    parser.add_argument("--sun", type=float, default=2.5,
                        help="hard key energy; exteriors get one, interiors do not")
    parser.add_argument("--ground-share", type=float, default=0.03,
                        help="fraction of the atlas the ground may occupy; the "
                             "rest goes to the buildings and foliage. 3%% because "
                             "at 15%% the ground took 114,747 texels and still "
                             "measured 0.00 texels per screen pixel -- it is so "
                             "large that six figures of texture buy it nothing, "
                             "while the buildings were short by about that much")
    parser.add_argument("--cull-samples", type=int, default=24,
                        help="hemisphere rays per face when testing reachability")
    parser.add_argument("--cull-escape", type=float, default=0.0,
                        help="keep a face if more than this fraction of its rays escape")
    parser.add_argument("--ground-clip-margin", type=float, default=GROUND_CLIP_MARGIN,
                        help="keep the ground this many metres past what the lane cameras can see; "
                             "the authored ground is 200 x 200 m for a 24 m street")
    parser.add_argument("--keep-full-ground", action="store_true",
                        help="do not clip the ground to the lane cameras' view")
    parser.add_argument("--atlas-layout", choices=("view", "legacy"), default="view",
                        help="view spends the atlas where the lane cameras look (#877); legacy is the "
                             "original smart_project with a fixed --ground-share")
    parser.add_argument("--keep-sealed", action="store_true",
                        help="disable sealed-face culling")
    parser.add_argument("--margin", type=float, default=6.0,
                        help="how far past the lane ends geometry may still belong")
    parser.add_argument("--atlas-size", type=int, default=render_profiles.DEFAULT_ATLAS_SIZE,
                        help="2048 because the buildings measured 0.66 texels "
                             "per screen pixel at 1024, against the 1-3 a "
                             "backdrop wants; they need ~983k texels for 1.0 "
                             "and a 1024 atlas holds 1,049k in total")
    parser.add_argument("--samples", type=int, default=None)
    parser.add_argument("--source-lighting", action="store_true",
                        help="preserve authored world and lamps rather than staging the legacy exterior rig")
    eevee_bake.add_arguments(parser)
    args = parser.parse_args(argv)
    atlas_allocation.CAMERA_RECORD = args.camera.resolve()

    opened = Path(bpy.data.filepath).resolve() if bpy.data.filepath else None
    if opened != args.blend.resolve():
        bpy.ops.wm.open_mainfile(filepath=str(args.blend.resolve()))
    rebuild_render_mesh(args.span, args.margin, args.ground_share,
                        0 if args.keep_sealed else args.cull_samples, args.cull_escape,
                        clip_ground=None if args.keep_full_ground else args.ground_clip_margin,
                        layout=args.atlas_layout, atlas_size=args.atlas_size)

    # Same reason export_room_environment.py stages lighting before baking: a
    # Cycles bake that just opens the file is lit by whatever the .blend last
    # saved, and this one saves a near-black world (0.0, 0.092, 0.119) with a
    # single sun at energy 3. Baked as-is the atlas comes out at mean RGB
    # 0.8/0.9/0.7 against the shipped package's 30.0/27.6/23.9 -- a cave. The
    # interior uses an even fill because a room is lit by what it contains; a
    # street gets the fill AND the hard key, which is what outdoor_sun is for.
    if not args.source_lighting:
        stager.base_lighting(args.ambient, (0.0, 0.0, 0.0), stager.INTERIOR_FILL)
        stager.outdoor_sun(args.sun)

    # An EEVEE bake photographs the source meshes that were joined, from 16 places along the lane. A town
    # source is in engine space already, so the lane cameras are not mirrored.
    eevee = eevee_bake.settings_from_args(
        args, args.blend, [0.6 + i * (args.span - 1.2) / 15 for i in range(16)],
        lambda scene, lane_y: atlas_allocation.lane_camera(scene, lane_y, mirrored=False),
        sources=bake_source_members(bpy.data.collections["TH_SOURCE"], args.span, args.margin)
        if args.bake_backend == "eevee" else None)

    output = args.output.resolve()
    pipeline.run_pipeline_in_blender(args.blend.resolve(), output,
                                     atlas_size=args.atlas_size,
                                     bake_samples=args.samples,
                                     flat_bake=False,
                                     backend=args.bake_backend, eevee=eevee,
                                     cycles_device=args.cycles_device, render_profile=args.render_profile)
    manifest_path = output / "environment.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["provenance"]["lightingPolicy"] = "source" if args.source_lighting else "staged-exterior"
    manifest["provenance"]["cameraCalibration"] = camera_provenance(args.camera)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8", newline="\n")
    print("EXTERIOR 3D EXPORT OK")


if __name__ == "__main__":
    main()
