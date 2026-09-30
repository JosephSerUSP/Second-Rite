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


def build_scene(*, cover=False, bake_marker=True, open_marker=True, max_tufts=2500):
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


def join(**scene):
    """Run the real join. Returns triangles, the tuft count the cover realises, and the log."""
    host = build_scene(**scene)
    tufts = 0
    if host is not None:
        tufts = len(ground_cover.evaluated_mesh(host).vertices) // VERTS_PER_TUFT
    log = io.StringIO()
    with contextlib.redirect_stdout(log):
        exporter.rebuild_render_mesh(SPAN, MARGIN, 0.03, 24, 0.0)
    target = bpy.data.objects["st_maria_praca_TH_RENDER"]
    target.data.calc_loop_triangles()
    return len(target.data.loop_triangles), tufts, log.getvalue()


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

        out.update(ok=True, base=base, with_cover=with_cover, tufts=tufts,
                   tris_per_tuft=TRIS_PER_TUFT, unmarked=unmarked,
                   unmarked_warned="carry modifiers but are not bake sources" in unmarked_log
                   and "GROUND_COVER" in unmarked_log,
                   closed_as_solid=closed_as_solid, refused=refused)
    except Exception:
        out["error"] = traceback.format_exc()
    print("EXTERIOR_BAKE_PROBE " + json.dumps(out))


main()
