"""Screen-space atlas allocation for a static-camera baked environment.

STATUS: the MEASUREMENT below is real and reproducible (atlas_audit.py).
This implementation is complete but has NOT yet been validated end to end in
a bake -- wiring it into town_environment_pipeline was interrupted. Treat it
as a proposal with evidence, not as proven tooling.

Why this exists
---------------
`smart_project` allocates UV area by 3D surface area. For a free camera that is
the only sane default. For Thestra's town the camera is FIXED -- eye, lens and
pitch never move, and the projection window pans by a bounded amount -- so the
exact screen footprint of every face is known before the bake. Measured on the
first baked package:

    45 of 182 triangles were ever visible
    69.5% of allocated texels went to faces the camera can never see
    texels per visible screen pixel ranged 0.57 .. 56.5 (a ~100x spread)
    the whole scene needs ~264 x 264 texels at a true 1:1

So the uniform packing was simultaneously starving the surfaces that matter and
paying full price for box interiors.

What it does
------------
1. Measures each face's projected, frame-clipped, backface-culled area, taking
   the MAXIMUM across every projection-window offset. Using offset 0 alone
   would starve anything that is only visible when the window pans.
2. Optionally deletes faces that are never visible from any offset.
3. Gives every remaining face its own UV rectangle sized so texel count is
   proportional to that screen area, and shelf-packs the rectangles.

Per-face islands rather than merged islands: with a culled mesh there are few
faces, the bake needs a bleed margin on every island anyway, and per-face rects
make the allocation exactly controllable instead of a side effect of packing.

The camera assumption is baked into the result. This is only valid because the
eye, lens and pitch are fixed and the pan range is bounded; if the window ever
widens, both the culling and the weighting must be recomputed. The offsets used
are recorded in the returned report.
"""
from __future__ import annotations

import math


def _clip(poly, w, h):
    def inside(p, e):
        return (p[0] >= 0.0) if e == 0 else (p[0] <= w) if e == 1 else \
               (p[1] >= 0.0) if e == 2 else (p[1] <= h)

    def cut(p, q, e):
        if e in (0, 1):
            xe = 0.0 if e == 0 else w
            t = (xe - p[0]) / (q[0] - p[0]) if q[0] != p[0] else 0.0
            return (xe, p[1] + t * (q[1] - p[1]))
        ye = 0.0 if e == 2 else h
        t = (ye - p[1]) / (q[1] - p[1]) if q[1] != p[1] else 0.0
        return (p[0] + t * (q[0] - p[0]), ye)

    out = list(poly)
    for e in range(4):
        if not out:
            return []
        src, out = out, []
        for i in range(len(src)):
            cur, prv = src[i], src[i - 1]
            if inside(cur, e):
                if not inside(prv, e):
                    out.append(cut(prv, cur, e))
                out.append(cur)
            elif inside(prv, e):
                out.append(cut(prv, cur, e))
    return out


def _area(poly):
    if len(poly) < 3:
        return 0.0
    return abs(sum(poly[i][0] * poly[(i + 1) % len(poly)][1]
                   - poly[(i + 1) % len(poly)][0] * poly[i][1]
                   for i in range(len(poly)))) * 0.5


def face_screen_areas(scene, cam, obj, *, offsets=(-96, 0, 96)):
    """Max frame-clipped projected area per polygon, in native pixels."""
    import bpy
    from bpy_extras.object_utils import world_to_camera_view

    w = float(scene.render.resolution_x)
    h = float(scene.render.resolution_y)
    mw = obj.matrix_world
    nm = mw.to_3x3().inverted().transposed()
    eye = cam.matrix_world.translation
    mesh = obj.data

    base_shift = cam.data.shift_x
    areas = [0.0] * len(mesh.polygons)
    try:
        for off in offsets:
            # 1.0 of shift_x is one full sensor width; the render target is
            # `w` pixels wide, so a window offset of `off` px is off/w of it.
            cam.data.shift_x = base_shift - float(off) / w
            bpy.context.view_layer.update()
            for pi, poly in enumerate(mesh.polygons):
                world = [mw @ mesh.vertices[v].co for v in poly.vertices]
                centre = sum(world, world[0] * 0.0) / len(world)
                normal = (nm @ poly.normal).normalized()
                if normal.dot(eye - centre) <= 0.0:
                    continue                      # backface
                pts = []
                behind = False
                for v in world:
                    c = world_to_camera_view(scene, cam, v)
                    if c.z <= 0.0:
                        behind = True
                        break
                    pts.append((c.x * w, (1.0 - c.y) * h))
                if behind:
                    continue
                a = _area(_clip(pts, w, h))
                if a > areas[pi]:
                    areas[pi] = a
    finally:
        cam.data.shift_x = base_shift
        bpy.context.view_layer.update()
    return areas


def cull_invisible(obj, areas, *, threshold=0.25):
    """Delete polygons never visible from any offset. Returns (kept, removed)."""
    import bmesh
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.faces.ensure_lookup_table()
    doomed = [bm.faces[i] for i, a in enumerate(areas)
              if i < len(bm.faces) and a <= threshold]
    kept = [a for a in areas if a > threshold]
    if doomed:
        bmesh.ops.delete(bm, geom=doomed, context="FACES")
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    return kept, len(doomed)


def _face_frame(mesh, poly):
    """Local 2D basis for a polygon plus its extents in that basis."""
    from mathutils import Vector
    verts = [mesh.vertices[v].co for v in poly.vertices]
    n = poly.normal.normalized()
    ref = Vector((0.0, 0.0, 1.0))
    if abs(n.dot(ref)) > 0.9:
        ref = Vector((1.0, 0.0, 0.0))
    u = (ref - n * ref.dot(n)).normalized()
    v = n.cross(u).normalized()
    o = verts[0]
    pts = [((p - o).dot(u), (p - o).dot(v)) for p in verts]
    us = [p[0] for p in pts]
    vs = [p[1] for p in pts]
    return u, v, o, min(us), min(vs), max(us) - min(us), max(vs) - min(vs), pts


def pack_by_screen_area(obj, areas, *, atlas_size=1024, margin_px=4,
                        supersample=1.0, min_px=4.0):
    """Give each face a UV rect with texels proportional to its screen area."""
    mesh = obj.data
    uv = mesh.uv_layers.get("UVMap") or mesh.uv_layers.new(name="UVMap")
    mesh.uv_layers.active = uv

    rects = []
    for pi, poly in enumerate(mesh.polygons):
        screen = max(float(areas[pi]) if pi < len(areas) else 0.0, min_px)
        u, v, o, u0, v0, du, dv, pts = _face_frame(mesh, poly)
        aspect = (du / dv) if dv > 1e-9 else 1.0
        aspect = min(max(aspect, 0.05), 20.0)
        target = screen * supersample
        hpx = math.sqrt(target / aspect)
        wpx = aspect * hpx
        rects.append({"poly": pi, "w": wpx, "h": hpx, "screen": screen,
                      "basis": (u, v, o, u0, v0, du, dv, pts)})

    # shelf pack, tallest first, shrinking globally until everything fits
    scale = 1.0
    for _ in range(48):
        placed, x, y, shelf_h, ok = [], float(margin_px), float(margin_px), 0.0, True
        for r in sorted(rects, key=lambda r: -r["h"] * scale):
            w = max(1.0, r["w"] * scale)
            h = max(1.0, r["h"] * scale)
            if x + w + margin_px > atlas_size:
                x = float(margin_px)
                y += shelf_h + margin_px
                shelf_h = 0.0
            if y + h + margin_px > atlas_size:
                ok = False
                break
            placed.append((r, x, y, w, h))
            x += w + margin_px
            shelf_h = max(shelf_h, h)
        if ok:
            break
        scale *= 0.88
    if not ok:
        raise RuntimeError("screen-space atlas packing failed to converge")

    for r, px, py, pw, ph in placed:
        poly = mesh.polygons[r["poly"]]
        u, v, o, u0, v0, du, dv, pts = r["basis"]
        for li, vi in zip(poly.loop_indices, poly.vertices):
            su = (pts[list(poly.vertices).index(vi)][0] - u0) / du if du > 1e-9 else 0.5
            sv = (pts[list(poly.vertices).index(vi)][1] - v0) / dv if dv > 1e-9 else 0.5
            uv.data[li].uv = ((px + su * pw) / atlas_size,
                              1.0 - (py + sv * ph) / atlas_size)
    mesh.update()

    used = sum(pw * ph for _, _, _, pw, ph in placed)
    return {
        "faces": len(placed),
        "globalScale": round(scale, 5),
        "atlasSize": atlas_size,
        "packedTexels": int(used),
        "packedFraction": round(used / float(atlas_size * atlas_size), 4),
        "supersample": supersample,
        "texelsPerScreenPixel": round(
            used / max(1.0, sum(r["screen"] for r in rects)), 3),
    }


def allocate(scene, cam, obj, *, offsets=(-96, 0, 96), atlas_size=1024,
             margin_px=4, supersample=1.0, cull=True):
    """Full screen-space allocation. Returns a report dict."""
    areas = face_screen_areas(scene, cam, obj, offsets=offsets)
    total_faces = len(areas)
    visible = sum(1 for a in areas if a > 0.25)
    screen_px = sum(a for a in areas if a > 0.25)
    removed = 0
    if cull:
        areas, removed = cull_invisible(obj, areas)
    stats = pack_by_screen_area(obj, areas, atlas_size=atlas_size,
                                margin_px=margin_px, supersample=supersample)
    stats.update({
        "projectionWindowOffsets": list(offsets),
        "facesBefore": total_faces,
        "facesVisible": visible,
        "facesCulled": removed,
        "visibleScreenPixels": int(screen_px),
        "idealAtlasEdgeAt1to1": int(math.sqrt(max(1.0, screen_px))),
    })
    return stats
