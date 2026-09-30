"""Atlas layout for a room: packed tight, and optionally spent where the camera looks (#877).

`smart_project(island_margin=0.02)` leaves a room's atlas about 77% empty gutter
(docs/reports/st-maria-shops-walkable-2026-08-27.md measured 23% carrying texels), and it
spends what is left in proportion to WORLD area: a ceiling the camera sees edge-on gets the
same texels per metre as the counter it looks straight at. This module replaces both:

  * ``pack``: unwrap with no island margin, then Blender's own concave packer with a
    gutter of a couple of texels (the runtime samples nearest, so a gutter wider than the
    bake's dilation is resolution spent on nothing). The exterior exporter already packs
    this way.
  * ``allocate_by_view``: measure what a bounded camera actually needs, then scale each
    island to it before packing. Demand comes from rendering the room's own mesh from the
    lane cameras with each face painted with its index and counting pixels per face, so the
    numbers are the screen the player will see rather than a guess at it.

The policy is the one docs/design/town-authoring-known-good.md sets out, in its first
useful form: density = lerp(world-uniform, view-demand, view_bias), never below a floor, so
a face no camera reaches keeps a few texels rather than none, and culling stays a separate
decision. It reports what it assumed and what it produced.

Runs inside Blender. `bpy` and `bmesh` are imported at call time only where needed so the
arithmetic can be read without them.
"""
from __future__ import annotations

import collections
import json
import math
from pathlib import Path

import bpy
import numpy as np

CAMERA_RECORD = Path(__file__).resolve().parent / "fixtures" / "town_sideview_camera.json"
VIEW_WIDTH = 426
VIEW_HEIGHT = 240
FACE_ATTRIBUTE = "sr_face_id"


def lane_camera(scene, lane_y: float):
    """The town side-view camera, widened to the 426 px view, standing at `lane_y`."""
    import stage_room_model as stager
    import thestra_camera

    record = thestra_camera.load_calibration(str(CAMERA_RECORD))
    record = stager.widen_record(record, VIEW_WIDTH)
    camera = thestra_camera.create_or_update_camera(record, scene=scene, make_active=True)
    camera.location.y = lane_y
    bpy.context.view_layer.update()
    return camera


def pack(target, atlas_size: int, gutter_texels: float = 2.0) -> None:
    """Unwrap `target` with no island margin and pack it tight."""
    bpy.ops.object.select_all(action="DESELECT")
    target.select_set(True)
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(66.0), island_margin=0.0)
    repack(gutter_texels / atlas_size)
    bpy.ops.object.mode_set(mode="OBJECT")


def repack(margin: float) -> None:
    """Concave-shape pack of every selected island, scaled to fill the atlas. Edit mode."""
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.select_all(action="SELECT")
    bpy.ops.uv.pack_islands(rotate=True, rotate_method="ANY", scale=True, margin_method="SCALED",
                            margin=margin, shape_method="CONCAVE")


def uv_islands(mesh) -> list[int]:
    """Island id per polygon: faces are one island when a shared edge has the same UVs in both."""
    uv = mesh.uv_layers.active.data
    parent = list(range(len(mesh.polygons)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    corner = {}
    edge_faces = collections.defaultdict(list)
    for poly in mesh.polygons:
        loops = list(poly.loop_indices)
        corner[poly.index] = {mesh.loops[i].vertex_index: tuple(uv[i].uv) for i in loops}
        for n, i in enumerate(loops):
            edge_faces[mesh.loops[i].edge_index].append(poly.index)
    for edge_index, faces in edge_faces.items():
        if len(faces) != 2:
            continue
        a, b = faces
        v1, v2 = mesh.edges[edge_index].vertices
        same = all(math.dist(corner[a][v], corner[b][v]) < 1e-6 for v in (v1, v2))
        if same:
            parent[find(a)] = find(b)
    roots = {}
    return [roots.setdefault(find(p.index), len(roots)) for p in mesh.polygons]


def face_pixels(target, cameras: list[float], out: Path) -> np.ndarray:
    """Pixels each polygon covers, per camera: shape (cameras, polygons). Renders the mesh alone."""
    scene = bpy.context.scene
    mesh = target.data
    if FACE_ATTRIBUTE in mesh.attributes:
        mesh.attributes.remove(mesh.attributes[FACE_ATTRIBUTE])
    attribute = mesh.attributes.new(FACE_ATTRIBUTE, "FLOAT", "FACE")
    attribute.data.foreach_set("value", np.arange(len(mesh.polygons), dtype=np.float32))
    material = bpy.data.materials.new("SR_FACE_ID_PASS")
    material.use_nodes = True
    tree = material.node_tree
    tree.nodes.clear()
    read = tree.nodes.new("ShaderNodeAttribute")
    read.attribute_name = FACE_ATTRIBUTE
    emission = tree.nodes.new("ShaderNodeEmission")
    output = tree.nodes.new("ShaderNodeOutputMaterial")
    tree.links.new(read.outputs["Fac"], emission.inputs["Color"])
    tree.links.new(emission.outputs["Emission"], output.inputs["Surface"])

    saved = (scene.render.engine, scene.render.resolution_x, scene.render.resolution_y,
             scene.render.resolution_percentage, scene.render.filter_size,
             scene.view_settings.view_transform)
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 1
    scene.render.filter_size = 0.0
    scene.render.resolution_x, scene.render.resolution_y = VIEW_WIDTH, VIEW_HEIGHT
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True
    scene.view_settings.view_transform = "Raw"
    scene.render.image_settings.file_format = "OPEN_EXR"
    scene.render.image_settings.color_depth = "32"
    scene.render.image_settings.color_mode = "RGBA"
    counts = np.zeros((len(cameras), len(mesh.polygons)), dtype=np.float64)
    bpy.context.view_layer.material_override = material
    try:
        for number, lane_y in enumerate(cameras):
            lane_camera(scene, float(lane_y))
            path = out / "tmp_face_id.exr"
            scene.render.filepath = str(path)
            bpy.ops.render.render(write_still=True)
            image = bpy.data.images.load(str(path))
            try:
                width, height = image.size
                buffer = np.empty(width * height * 4, dtype=np.float32)
                image.pixels.foreach_get(buffer)
            finally:
                bpy.data.images.remove(image)
            buffer = buffer.reshape(height, width, 4)
            hit = buffer[..., 3] > 0.5
            ids = np.rint(buffer[..., 0][hit]).astype(np.int64)
            ids = ids[(ids >= 0) & (ids < len(mesh.polygons))]
            counts[number] = np.bincount(ids, minlength=len(mesh.polygons))
    finally:
        bpy.context.view_layer.material_override = None
        (scene.render.engine, scene.render.resolution_x, scene.render.resolution_y,
         scene.render.resolution_percentage, scene.render.filter_size,
         scene.view_settings.view_transform) = saved
        (out / "tmp_face_id.exr").unlink(missing_ok=True)
    return counts


def allocate_by_view(target, cameras: list[float], atlas_size: int, view_bias: float = 0.85,
                     floor: float = 0.04, gutter_texels: float = 2.0, out: Path | None = None) -> dict:
    """Unwrap, measure what the cameras need, scale each island to it, pack. Returns a report.

    `view_bias` 0 keeps world-uniform density (every surface equal); 1 follows the cameras.
    `floor` is the least density, as a fraction of the mean visible density, an island keeps,
    so surfaces no camera reaches are shrunk but never removed.
    """
    out = Path(out) if out else Path(bpy.app.tempdir)
    pack(target, atlas_size, gutter_texels)
    mesh = target.data
    counts = face_pixels(target, cameras, out)
    peak = counts.max(axis=0)                                # pixels a face covers in its best view
    island_of = uv_islands(mesh)
    islands = max(island_of) + 1
    uv = mesh.uv_layers.active.data
    world = np.zeros(islands)
    uv_area = np.zeros(islands)
    demand = np.zeros(islands)
    for poly in mesh.polygons:
        i = island_of[poly.index]
        world[i] += poly.area
        pts = [np.array(uv[k].uv) for k in poly.loop_indices]
        uv_area[i] += 0.5 * abs(sum(pts[n][0] * pts[(n + 1) % len(pts)][1] - pts[(n + 1) % len(pts)][0] * pts[n][1]
                                    for n in range(len(pts))))
        demand[i] += peak[poly.index]
    visible = demand > 0
    if not visible.any():
        raise SystemExit("no camera sees any face; refusing to allocate the atlas by view")
    view_density = np.where(world > 0, demand / np.maximum(world, 1e-12), 0.0)          # pixels per m^2
    mean_visible = float((demand[visible].sum()) / world[visible].sum())
    world_density = np.full(islands, mean_visible)
    density = (1.0 - view_bias) * world_density + view_bias * view_density
    density = np.maximum(density, floor * mean_visible)
    # Scale each island's UVs about its centre so its area becomes proportional to
    # density x world area; the packer then scales the whole set to fill the atlas.
    current_density = uv_area / np.maximum(world, 1e-12)
    scale = np.sqrt(density / np.maximum(current_density, 1e-12))
    scale = scale / np.median(scale[visible])                # only ratios matter; keep numbers tame
    centres = np.zeros((islands, 2))
    members = collections.defaultdict(list)
    for poly in mesh.polygons:
        members[island_of[poly.index]].append(poly)
    for i, polys in members.items():
        pts = np.array([uv[k].uv for poly in polys for k in poly.loop_indices])
        centres[i] = (pts.min(axis=0) + pts.max(axis=0)) / 2
        for poly in polys:
            for k in poly.loop_indices:
                uv[k].uv = centres[i] + (np.array(uv[k].uv) - centres[i]) * scale[i]
    bpy.ops.object.select_all(action="DESELECT")
    target.select_set(True)
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.mode_set(mode="EDIT")
    repack(gutter_texels / atlas_size)
    bpy.ops.object.mode_set(mode="OBJECT")
    return {
        "atlasSize": atlas_size, "viewBias": view_bias, "floor": floor, "gutterTexels": gutter_texels,
        "cameras": [round(float(c), 3) for c in cameras], "islands": int(islands),
        "visibleIslands": int(visible.sum()), "polygons": len(mesh.polygons),
        "visiblePolygons": int((peak > 0).sum()),
        "meanVisiblePixelsPerSquareMetre": round(mean_visible, 2),
    }


def triangle_mask(mesh, size: int) -> np.ndarray:
    """Texels whose centre lies inside any triangle of the UV layout: what the atlas must hold."""
    mesh.calc_loop_triangles()
    layer = mesh.uv_layers.active.data
    mask = np.zeros((size, size), dtype=bool)
    for tri in mesh.loop_triangles:
        pts = np.array([layer[i].uv[:] for i in tri.loops]) * size
        x0, y0 = np.floor(pts.min(axis=0)).astype(int)
        x1, y1 = np.ceil(pts.max(axis=0)).astype(int)
        x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, size - 1), min(y1, size - 1)
        if x1 < x0 or y1 < y0:
            continue
        gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        a, b, c = pts
        d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(d) < 1e-12:
            continue
        w1 = ((b[1] - c[1]) * (gx - c[0]) + (c[0] - b[0]) * (gy - c[1])) / d
        w2 = ((c[1] - a[1]) * (gx - c[0]) + (a[0] - c[0]) * (gy - c[1])) / d
        inside = (w1 >= 0) & (w2 >= 0) & (w1 + w2 <= 1)
        mask[y0:y1 + 1, x0:x1 + 1] |= inside
    return mask


def layout_report(target, atlas_size: int) -> dict:
    """What the finished layout holds: how much of the atlas the islands cover."""
    mask = triangle_mask(target.data, atlas_size)
    return {"islandCoverage": round(float(mask.mean()), 4), "islandTexels": int(mask.sum())}


def report_json(report: dict) -> str:
    return json.dumps(report, indent=1)
