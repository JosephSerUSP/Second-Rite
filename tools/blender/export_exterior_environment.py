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

## Export contract

Geometry is exact -- this reproduces the shipped package's 9,304 triangles
exactly once the off-square duplicate is filtered. The ATLAS is not: it packs
to roughly 9% non-black coverage against the shipped package's 69%, and against
41.8% for an interior room through the same pipeline. The consequence is a
mostly empty atlas and far too few texels on each surface, which reads as a
dark, muddy street.

Lighting is staged below because an unlit bake is wrong regardless, and it does
move the mean from 0.8 to 2.5. Note that per #1023, the atlas transfer defect is
driven by a circular image dependency on the bake receiver rather than island
margin. Do not tune the lights to chase brightness until the bake graph is resolved.

Source membership and the lane adapter are explicit scene properties. A source
mesh is renderable only when it carries ``sr_export=True``; ground allocation
uses ``sr_ground=True``. The scene may set ``sr_runtime_y_mode`` to
``lane_mirror`` and ``sr_lane_center_y`` to export Blender's authored screen
space into the engine lane space. This is opt-in and cannot silently
reinterpret an older scene.
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "blender"))

import town_environment_pipeline as pipeline  # noqa: E402
import stage_room_model as stager  # noqa: E402


GROUND_TAG_MATERIAL = "TH_GROUND_ALLOC_TAG"
RUNTIME_Y_MODE = "sr_runtime_y_mode"
LANE_CENTER = "sr_lane_center_y"
FLOOR_TEXTURE_SOURCE = ROOT / "projects" / "hichaukitoden-game" / "assets" / "materials" / "old_limestone" / "albedo.png"


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
    bvh = BVHTree.FromPolygons([v.co.copy() for v in mesh.vertices],
                               [tuple(p.vertices) for p in mesh.polygons],
                               all_triangles=False)
    directions = [mathutils.Vector(d).normalized() for d in PARITY_DIRECTIONS]
    needed = len(directions) // 2 + 1
    doomed = []
    for poly in mesh.polygons:
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


def _runtime_y(obj, scene):
    """Map authored Blender Y to the explicitly declared runtime lane."""
    centre = sum((obj.matrix_world @ Vector(corner) for corner in obj.bound_box),
                 Vector()) / 8.0
    mode = scene.get(RUNTIME_Y_MODE, "direct")
    if mode == "direct":
        return centre.y
    if mode == "lane_mirror":
        if LANE_CENTER not in scene:
            raise RuntimeError("lane_mirror export requires sr_lane_center_y")
        return float(scene[LANE_CENTER]) - centre.y
    raise RuntimeError("unsupported sr_runtime_y_mode %r" % mode)


def in_lane(obj, min_y, max_y, margin, scene):
    """Is this explicitly exported object inside the authored lane?"""
    runtime_y = _runtime_y(obj, scene)
    return min_y - margin <= runtime_y <= max_y + margin


def runtime_bounds(bounds, scene):
    """Transform Blender bounds into the coordinates consumed by the engine."""
    min_x, min_y, min_z, max_x, max_y, max_z = bounds
    mode = scene.get(RUNTIME_Y_MODE, "direct")
    if mode == "direct":
        return [min_x, min_y, min_z, max_x, max_y, max_z]
    if mode == "lane_mirror":
        centre = float(scene[LANE_CENTER])
        return [min_x, centre - max_y, min_z, max_x, centre - min_y, max_z]
    raise RuntimeError("unsupported sr_runtime_y_mode %r" % mode)


def configure_ground_tag(tag, source_material):
    """Preserve the authored ground appearance on the allocation tag.

    Ground faces temporarily use a semantic tag so the atlas allocator can
    identify them after the source meshes are joined.  The tag is still a
    real bake material, however: an empty material makes Cycles bake those
    faces black.  Copy the source Principled surface values into the tag
    before baking; the tag remains a semantic classifier without becoming an
    appearance override.
    """
    tag.use_nodes = True
    nodes = tag.node_tree.nodes
    links = tag.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
    source_bsdf = None
    if source_material and source_material.use_nodes:
        source_bsdf = source_material.node_tree.nodes.get("Principled BSDF")
    if source_bsdf:
        for name in ("Base Color", "Roughness", "Metallic", "IOR",
                     "Specular IOR Level", "Emission Color",
                     "Emission Strength"):
            src = source_bsdf.inputs.get(name)
            dst = bsdf.inputs.get(name)
            if src is not None and dst is not None and not src.is_linked:
                try:
                    dst.default_value = src.default_value
                except (TypeError, ValueError):
                    pass
    elif source_material:
        bsdf.inputs["Base Color"].default_value = source_material.diffuse_color
    tag.diffuse_color = (source_material.diffuse_color
                         if source_material else (0.5, 0.5, 0.5, 1.0))


def mirror_obj_file(path, centre):
    """Reflect the OBJ lane axis while preserving outward normals."""
    lines = path.read_text(encoding="utf-8").splitlines()
    out, flipped = [], 0
    for line in lines:
        if line.startswith("v "):
            parts = line.split()
            # Blender OBJ export is x, z, -y; the lane is the third component.
            parts[3] = f"{-float(parts[3]) - centre:.6f}"
            out.append(" ".join(parts))
        elif line.startswith("vn "):
            parts = line.split()
            parts[3] = f"{-float(parts[3]):.6f}"
            out.append(" ".join(parts))
        elif line.startswith("f "):
            parts = line.split()
            out.append(" ".join([parts[0]] + list(reversed(parts[1:]))))
            flipped += 1
        else:
            out.append(line)
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return flipped


def export_floor_mesh(output, scene):
    """Export the walkable slab as a small, independently textured mesh.

    The beauty atlas is for facades, roofs, foliage and props. A broad floor
    plane consumes most of that UV space and its glancing-angle bake is not a
    stable runtime surface. Keep the editable slab in the adopted blend, but
    ship it as a separate tiled OBJ with the authored limestone albedo.
    """
    source = bpy.data.collections.get("TH_SOURCE")
    grounds = [obj for obj in (source.all_objects if source else bpy.data.objects)
               if obj.type == "MESH" and bool(obj.get("sr_ground", False))]
    if not grounds:
        raise RuntimeError("floor export requires an sr_ground mesh")
    corners = [obj.matrix_world @ Vector(corner)
               for obj in grounds for corner in obj.bound_box]
    min_x = min(point.x for point in corners)
    max_x = max(point.x for point in corners)
    min_y = min(point.y for point in corners)
    max_y = max(point.y for point in corners)
    floor_z = max(point.z for point in corners) + 0.006
    mode = scene.get(RUNTIME_Y_MODE, "direct")
    if mode == "direct":
        runtime_min_y, runtime_max_y = min_y, max_y
    elif mode == "lane_mirror":
        centre = float(scene[LANE_CENTER])
        runtime_min_y, runtime_max_y = centre - max_y, centre - min_y
    else:
        raise RuntimeError("unsupported sr_runtime_y_mode %r" % mode)

    # The OBJ reader consumes (x, -z, y) and converts it to runtime (x, y, z).
    vertices = [
        (min_x, floor_z, -runtime_min_y),
        (max_x, floor_z, -runtime_min_y),
        (max_x, floor_z, -runtime_max_y),
        (min_x, floor_z, -runtime_max_y),
    ]
    uvs = [
        (0.0, 0.0), ((max_x - min_x) / 2.0, 0.0),
        ((max_x - min_x) / 2.0, (runtime_max_y - runtime_min_y) / 2.0),
        (0.0, (runtime_max_y - runtime_min_y) / 2.0),
    ]
    obj_lines = ["# Cortico walkable floor; generated from the adopted blend",
                 "mtllib floor.mtl", "usemtl CorticoFloor"]
    obj_lines.extend("v %.6f %.6f %.6f" % vertex for vertex in vertices)
    obj_lines.extend("vt %.6f %.6f" % uv for uv in uvs)
    # Blender's OBJ coordinates are x, z, -y.  A Blender +Z normal therefore
    # becomes OBJ +Y, which the runtime reader maps back to world +Z.
    obj_lines.extend(("vn 0.000000 1.000000 0.000000",
                      "f 1/1/1 2/2/1 3/3/1",
                      "f 1/1/1 3/3/1 4/4/1"))
    (output / "floor.obj").write_text("\n".join(obj_lines) + "\n",
                                      encoding="utf-8")
    (output / "floor.mtl").write_text(
        "newmtl CorticoFloor\n"
        "Ka 1.000 1.000 1.000\n"
        "Kd 1.000 1.000 1.000\n"
        "map_Kd floor.png\n", encoding="utf-8")
    if not FLOOR_TEXTURE_SOURCE.exists():
        raise RuntimeError("floor texture source missing: %s" % FLOOR_TEXTURE_SOURCE)
    shutil.copyfile(FLOOR_TEXTURE_SOURCE, output / "floor.png")
    return {
        "mesh": "floor.obj", "material": "floor.mtl", "texture": "floor.png",
        "bounds": [round(min_x, 4), round(runtime_min_y, 4), round(floor_z, 4),
                   round(max_x, 4), round(runtime_max_y, 4), round(floor_z, 4)],
        "textureSource": str(FLOOR_TEXTURE_SOURCE.relative_to(ROOT)),
    }


def rebuild_render_mesh(span, margin, ground_share, cull_samples, cull_escape,
                        lane_min=None, lane_max=None) -> None:
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
    scene = bpy.context.scene
    lane_min = float(scene.get("sr_lane_min_y", 0.0) if lane_min is None else lane_min)
    lane_max = float(scene.get("sr_lane_max_y", span) if lane_max is None else lane_max)
    source_objects = list(source.all_objects)
    for obj in source_objects:
        if obj.type != "MESH" or obj.hide_render:
            continue
        if not bool(obj.get("sr_export", False)):
            continue
        if not in_lane(obj, lane_min, lane_max, margin, scene):
            print(f"[exterior] SKIPPING off-lane {obj.name}", flush=True)
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
        if bool(obj.get("sr_ground", False)):
            source_material = next((slot.material for slot in obj.material_slots
                                    if slot.material), None)
            configure_ground_tag(ground_tag, source_material)
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
        print(f"[exterior] skipped {len(skipped)} off-lane objects: "
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
    target.name = "st_maria_exterior_TH_RENDER"
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
    bpy.ops.object.select_all(action="DESELECT")
    target.select_set(True)
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    if not target.data.uv_layers:
        bpy.ops.mesh.uv_texture_add()
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
    parser.add_argument("--keep-sealed", action="store_true",
                        help="disable sealed-face culling")
    parser.add_argument("--margin", type=float, default=6.0,
                        help="how far past the lane ends geometry may still belong")
    parser.add_argument("--atlas-size", type=int, default=2048,
                        help="2048 because the buildings measured 0.66 texels "
                             "per screen pixel at 1024, against the 1-3 a "
                             "backdrop wants; they need ~983k texels for 1.0 "
                             "and a 1024 atlas holds 1,049k in total")
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
    scene = bpy.context.scene
    floor_report = export_floor_mesh(output, scene)
    if scene.get(RUNTIME_Y_MODE, "direct") == "lane_mirror":
        centre = float(scene[LANE_CENTER])
        obj_path = output / "environment.obj"
        flipped = mirror_obj_file(obj_path, centre)
        manifest_path = output / "environment.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["bounds"] = [round(value, 4) for value in runtime_bounds(
            manifest["bounds"], scene)]
        manifest.setdefault("provenance", {})["runtimeAdapter"] = {
            "mode": "lane_mirror",
            "laneCenterY": centre,
            "objFacesReversed": flipped,
        }
        manifest["floorMesh"] = floor_report["mesh"]
        manifest.setdefault("provenance", {})["floor"] = floor_report
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n",
                                encoding="utf-8")
        print(f"[exterior] mirrored {flipped} OBJ faces into engine lane space",
              flush=True)
    else:
        manifest_path = output / "environment.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["floorMesh"] = floor_report["mesh"]
        manifest.setdefault("provenance", {})["floor"] = floor_report
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n",
                                encoding="utf-8")
    print("EXTERIOR 3D EXPORT OK")


if __name__ == "__main__":
    main()
