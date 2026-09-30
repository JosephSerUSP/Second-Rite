"""Blender-side probe for the exterior bake's render-mesh join (#1257 bake path).

Run by ``test_exterior_bake_source.py`` through the pinned headless Blender.  It
builds a tiny town source (a closed body plus, optionally, a Geometry Nodes ground
cover host), runs the real ``rebuild_render_mesh`` and reports what reached the
joined render mesh.  Prints one JSON object per scenario.
"""
import contextlib
import io
import json
import sys
import traceback
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "blender"))

import export_exterior_environment as exporter  # noqa: E402
import ground_cover  # noqa: E402

SPAN, MARGIN = 23.699, 6.0
VERTS_PER_TUFT = 8
TRIS_PER_TUFT = 4


def add_ground_sheet(source):
    """The authored ground: a 200 x 200 m sheet of zero thickness with a duplicate underside.

    8 vertices and 6 faces all in z = 0: a top facing up, an underside facing down, and four sides of
    no area. This is `ARCH_square_ground` as the Praca source holds it (#1287).
    """
    cx, cy, half = 2.5, 11.85, 100.0
    verts = [(cx + (half if xi else -half), cy + (half if yi else -half), 0.0)
             for xi in (0, 1) for yi in (0, 1) for _ in (0, 1)]
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    mesh = bpy.data.meshes.new("ARCH_square_ground")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    mesh.materials.append(bpy.data.materials.new("ground_stone"))
    ground = bpy.data.objects.new("ARCH_square_ground", mesh)
    source.objects.link(ground)
    return ground


def build_scene(*, cover=False, bake_marker=True, open_marker=True, max_tufts=2500, ground=False):
    """TH_SOURCE holds a closed body; the terrain lives outside it, as guides do."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene.collection
    source = bpy.data.collections.new("TH_SOURCE")
    render = bpy.data.collections.new("TH_RENDER")
    guides = bpy.data.collections.new("GUIDES")
    for collection in (source, render, guides):
        scene.children.link(collection)

    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=1.0, location=(0.0, 20.0, 1.5))
    body = bpy.context.object
    body.name = "STUDY_body"
    for owner in list(body.users_collection):
        owner.objects.unlink(body)
    source.objects.link(body)

    if ground:
        add_ground_sheet(source)
    host = None
    if cover:
        bpy.ops.mesh.primitive_grid_add(x_subdivisions=10, y_subdivisions=10, size=6.0,
                                        location=(0.0, 8.0, 0.0))
        terrain = bpy.context.object
        terrain.name = "TERRAIN"
        for owner in list(terrain.users_collection):
            owner.objects.unlink(terrain)
        guides.objects.link(terrain)
        host = ground_cover.add(terrain, parent_collection=source,
                                **{"Density": 4.0, "Max Tufts": max_tufts, "Seed": 1})
        if not bake_marker:
            del host[ground_cover.BAKE_PROPERTY]
        if not open_marker:
            del host[ground_cover.OPEN_SURFACE_PROPERTY]
    return host


def join(clip_ground=None, layout="legacy", **scene):
    """Run the real join. Returns triangles, the tuft count the cover realises, and the log.

    The ground is left whole and the atlas legacy unless a scenario asks, so the older scenarios measure
    only what they always did.
    """
    host = build_scene(**scene)
    tufts = 0
    if host is not None:
        tufts = len(ground_cover.evaluated_mesh(host).vertices) // VERTS_PER_TUFT
    log = io.StringIO()
    with contextlib.redirect_stdout(log):
        exporter.rebuild_render_mesh(SPAN, MARGIN, 0.03, 24, 0.0, clip_ground=clip_ground, layout=layout)
    target = bpy.data.objects["st_maria_praca_TH_RENDER"]
    target.data.calc_loop_triangles()
    return len(target.data.loop_triangles), tufts, log.getvalue()


def ground_report():
    """What the joined mesh holds for the ground: faces, their normals, area, and its share of the UVs."""
    target = bpy.data.objects["st_maria_praca_TH_RENDER"]
    mesh = target.data
    tag = next(i for i, m in enumerate(mesh.materials) if m and m.name.startswith(exporter.GROUND_TAG_MATERIAL))
    uv = mesh.uv_layers.active.data
    ground_uv, total_uv, area, normals, xs, ys = 0.0, 0.0, 0.0, [], [], []
    for poly in mesh.polygons:
        pts = [uv[i].uv for i in poly.loop_indices]
        uv_area = 0.5 * abs(sum(pts[k].x * pts[(k + 1) % len(pts)].y - pts[(k + 1) % len(pts)].x * pts[k].y
                                for k in range(len(pts))))
        total_uv += uv_area
        if poly.material_index == tag:
            ground_uv += uv_area
            area += poly.area
            normals.append(round(poly.normal.z, 3))
            xs += [mesh.vertices[v].co.x for v in poly.vertices]
            ys += [mesh.vertices[v].co.y for v in poly.vertices]
    return {"faces": len(normals), "normalsZ": sorted(set(normals)), "area": round(area, 1),
            "uvShare": round(ground_uv / total_uv, 4) if total_uv else 0.0,
            "bounds": [min(xs), max(xs), min(ys), max(ys)] if xs else None}


def ground_bake(flatten):
    """Bake the ground with the real pipeline (Cycles, flat, 256 px) and report how much of its island is lit.

    `flatten` replaces `flatten_ground_sheet`: the real one, or a half-fix that flattens only the copy
    joined into the render mesh, so the target faces up but the source is still a top and an underside.
    """
    import stage_room_model as stager
    import town_environment_pipeline as pipeline
    import numpy as np
    import tempfile
    build_scene(ground=True)
    bpy.data.collections.new("TH_ANCHORS")
    bpy.context.scene.collection.children.link(bpy.data.collections["TH_ANCHORS"])
    kept = exporter.flatten_ground_sheet
    exporter.flatten_ground_sheet = flatten
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            exporter.rebuild_render_mesh(SPAN, MARGIN, 0.03, 24, 0.0, clip_ground=exporter.GROUND_CLIP_MARGIN,
                                         layout="legacy")
            stager.base_lighting(0.35, (0.0, 0.0, 0.0), stager.INTERIOR_FILL)
            stager.outdoor_sun(2.5)
            pipeline.run_pipeline_in_blender(Path("ground_bake.blend"), Path(tempfile.mkdtemp()), atlas_size=256,
                                             bake_samples=4, flat_bake=True)
    finally:
        exporter.flatten_ground_sheet = kept
    size = 256
    pixels = np.array(bpy.data.images["environment_atlas"].pixels[:]).reshape(size, size, 4)[..., :3]
    mesh = bpy.data.objects["st_maria_praca_TH_RENDER"].data
    uv = mesh.uv_layers.active.data
    island = [(uv[i].uv.x, uv[i].uv.y) for poly in mesh.polygons if poly.normal.z > 0.99 and poly.area > 100
              for i in poly.loop_indices]
    if not island:
        return {"faces": 0}
    island = np.array(island)
    x0, x1 = int(island[:, 0].min() * size), max(int(island[:, 0].max() * size), int(island[:, 0].min() * size) + 1)
    y0, y1 = int(island[:, 1].min() * size), max(int(island[:, 1].max() * size), int(island[:, 1].min() * size) + 1)
    region = pixels[y0:y1, x0:x1]
    return {"faces": 1, "litFraction": float((region.max(axis=2) > 0).mean()), "mean": float(region.mean())}


def main():
    out = {"ok": False}
    try:
        base, _, _ = join()
        with_cover, tufts, _ = join(cover=True)
        unmarked, _, unmarked_log = join(cover=True, bake_marker=False)
        closed_as_solid, _, _ = join(cover=True, open_marker=False)

        refused = ""
        try:
            join(cover=True, max_tufts=0)
        except RuntimeError as error:
            refused = str(error)

        ground = {}
        join(ground=True)
        ground["whole"] = ground_report()
        # the negative control: with the sheet handling off, the cull keeps the underside (#1287)
        kept = exporter.flatten_ground_sheet
        exporter.flatten_ground_sheet = lambda obj: None
        try:
            join(ground=True)
            ground["unflattened"] = ground_report()
        finally:
            exporter.flatten_ground_sheet = kept
        join(ground=True, clip_ground=exporter.GROUND_CLIP_MARGIN)
        ground["clipped"] = ground_report()
        join(ground=True, layout="legacy")
        ground["legacyLayout"] = ground_report()
        join(ground=True, clip_ground=exporter.GROUND_CLIP_MARGIN, layout="view")
        ground["viewLayout"] = ground_report()
        real = exporter.flatten_ground_sheet
        ground["bakedWhole"] = ground_bake(real)
        ground["bakedCopyOnly"] = ground_bake(lambda obj: real(obj) if obj.name.startswith("R_") else None)
        out.update(ok=True, base=base, ground=ground, with_cover=with_cover, tufts=tufts,
                   tris_per_tuft=TRIS_PER_TUFT, unmarked=unmarked,
                   unmarked_warned="carry modifiers but are not bake sources" in unmarked_log
                   and "GROUND_COVER" in unmarked_log,
                   closed_as_solid=closed_as_solid, refused=refused)
    except Exception:
        out["error"] = traceback.format_exc()
    print("EXTERIOR_BAKE_PROBE " + json.dumps(out))


main()
