"""Generic mesh primitives for the clean-room town gauntlet.

These are *primitive constructors only*. No function here encodes a building,
a facade rhythm, a layout or a coordinate from any previous work. Every
attempt supplies its own numbers.

World frame (from the measured calibration):
    +X = away from the camera (depth)   +Y = screen right   +Z = screen up
"""
from __future__ import annotations

import math

import bmesh
import bpy


# --------------------------------------------------------------------------
# low level
# --------------------------------------------------------------------------

def new_mesh_object(name, verts, faces, collection):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([tuple(v) for v in verts], [], [tuple(f) for f in faces])
    mesh.validate()
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    return obj


def recalc_outward(obj):
    """Force consistent outward normals.

    Selected-to-active baking casts rays along the *target* normal, so inward
    winding silently destroys atlas coverage even when the beauty render looks
    fine. This is called on every solid this package builds.
    """
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    return obj


def box(name, collection, *, center=(0, 0, 0), size=(1, 1, 1)):
    """Axis-aligned box with outward-wound faces."""
    cx, cy, cz = center
    hx, hy, hz = size[0] * 0.5, size[1] * 0.5, size[2] * 0.5
    v = [
        (cx - hx, cy - hy, cz - hz), (cx + hx, cy - hy, cz - hz),
        (cx + hx, cy + hy, cz - hz), (cx - hx, cy + hy, cz - hz),
        (cx - hx, cy - hy, cz + hz), (cx + hx, cy - hy, cz + hz),
        (cx + hx, cy + hy, cz + hz), (cx - hx, cy + hy, cz + hz),
    ]
    f = [
        (0, 3, 2, 1),
        (4, 5, 6, 7),
        (0, 1, 5, 4),
        (2, 3, 7, 6),
        (1, 2, 6, 5),
        (0, 4, 7, 3),
    ]
    return recalc_outward(new_mesh_object(name, v, f, collection))


def slab(name, collection, *, x0, x1, y0, y1, z0, z1):
    return box(name, collection,
               center=((x0 + x1) * 0.5, (y0 + y1) * 0.5, (z0 + z1) * 0.5),
               size=(abs(x1 - x0), abs(y1 - y0), abs(z1 - z0)))


def panel(name, collection, *, x, y0, y1, z0, z1, cuts_y=48, cuts_z=48):
    """Flat camera-facing (-X normal) subdivided quad.

    Displacement is applied to *flat panels*, never to closed boxes: a
    displaced box tears along its shared edges and throws floating debris.
    """
    ny, nz = int(cuts_y) + 1, int(cuts_z) + 1
    verts, faces = [], []
    for iz in range(nz):
        tz = iz / (nz - 1)
        for iy in range(ny):
            ty = iy / (ny - 1)
            verts.append((x, y0 + (y1 - y0) * ty, z0 + (z1 - z0) * tz))
    for iz in range(nz - 1):
        for iy in range(ny - 1):
            a = iz * ny + iy
            faces.append((a, a + ny, a + ny + 1, a + 1))
    obj = new_mesh_object(name, verts, faces, collection)
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    for face in bm.faces:
        if face.normal.x > 0:
            face.normal_flip()
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    return obj


def ground(name, collection, *, x0, x1, y0, y1, z=0.0, cuts=32):
    n = int(cuts) + 1
    verts, faces = [], []
    for ix in range(n):
        tx = ix / (n - 1)
        for iy in range(n):
            ty = iy / (n - 1)
            verts.append((x0 + (x1 - x0) * tx, y0 + (y1 - y0) * ty, z))
    for ix in range(n - 1):
        for iy in range(n - 1):
            a = ix * n + iy
            faces.append((a, a + 1, a + n + 1, a + n))
    return recalc_outward(new_mesh_object(name, verts, faces, collection))


def prism(name, collection, *, profile, extrude_axis="y", start=0.0, end=1.0,
          offset=(0.0, 0.0)):
    """Extrude a 2D profile.

    extrude_axis 'y' -> profile is (x, z), extruded along Y
    extrude_axis 'x' -> profile is (y, z), extruded along X
    """
    n = len(profile)
    oa, ob = offset
    verts = []
    for s in (start, end):
        for (a, b) in profile:
            if extrude_axis == "y":
                verts.append((a + oa, s, b + ob))
            else:
                verts.append((s, a + oa, b + ob))
    faces = [tuple(range(n - 1, -1, -1)), tuple(range(n, 2 * n))]
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, j + n, i + n))
    return recalc_outward(new_mesh_object(name, verts, faces, collection))


def cylinder(name, collection, *, center=(0, 0, 0), radius=0.2, height=1.0,
             segments=12, axis="z"):
    cx, cy, cz = center
    verts, faces = [], []
    for k in (0, 1):
        for i in range(segments):
            a = 2 * math.pi * i / segments
            u, w = radius * math.cos(a), radius * math.sin(a)
            if axis == "z":
                verts.append((cx + u, cy + w, cz + k * height))
            elif axis == "y":
                verts.append((cx + u, cy + k * height, cz + w))
            else:
                verts.append((cx + k * height, cy + u, cz + w))
    faces.append(tuple(range(segments - 1, -1, -1)))
    faces.append(tuple(range(segments, 2 * segments)))
    for i in range(segments):
        j = (i + 1) % segments
        faces.append((i, j, j + segments, i + segments))
    return recalc_outward(new_mesh_object(name, verts, faces, collection))


def arched_opening_profile(width, straight_h, rise, segments=14):
    """(y, z) profile of a round-headed opening, origin at sill centre."""
    hw = width * 0.5
    pts = [(-hw, 0.0), (hw, 0.0), (hw, straight_h)]
    for i in range(1, segments):
        a = math.pi * i / segments
        pts.append((hw * math.cos(a), straight_h + rise * math.sin(a)))
    pts.append((-hw, straight_h))
    return pts


def _cutter_from_profile(name, collection, prof, x, thickness, cy, z0):
    cutter = bmesh.new()
    ring_a, ring_b = [], []
    for (py, pz) in prof:
        ring_a.append(cutter.verts.new((x - 0.08, cy + py, z0 + pz)))
        ring_b.append(cutter.verts.new((x + thickness + 0.08, cy + py, z0 + pz)))
    cutter.faces.new(list(reversed(ring_a)))
    cutter.faces.new(ring_b)
    for i in range(len(ring_a)):
        j = (i + 1) % len(ring_a)
        cutter.faces.new([ring_a[i], ring_a[j], ring_b[j], ring_b[i]])
    cutter.normal_update()
    tmp = bpy.data.meshes.new(name)
    cutter.to_mesh(tmp)
    cutter.free()
    obj = bpy.data.objects.new(name, tmp)
    collection.objects.link(obj)
    return obj


def wall_with_openings(name, collection, *, x, thickness, y0, y1, z0, z1,
                       openings=()):
    """A wall slab pierced by rectangular or round-headed openings."""
    obj = box(name, collection,
              center=(x + thickness * 0.5, (y0 + y1) * 0.5, (z0 + z1) * 0.5),
              size=(thickness, y1 - y0, z1 - z0))
    for idx, op in enumerate(openings):
        rise = op.get("arch", 0.0)
        w = op["y1"] - op["y0"]
        h = op["z1"] - op["z0"]
        if rise > 0:
            prof = arched_opening_profile(w, max(0.05, h - rise), rise)
        else:
            prof = [(-w * 0.5, 0.0), (w * 0.5, 0.0), (w * 0.5, h), (-w * 0.5, h)]
        cy = (op["y0"] + op["y1"]) * 0.5
        cut_obj = _cutter_from_profile("%s_cut%d" % (name, idx), collection,
                                       prof, x, thickness, cy, op["z0"])
        mod = obj.modifiers.new("cut%d" % idx, "BOOLEAN")
        mod.operation = "DIFFERENCE"
        mod.object = cut_obj
        mod.solver = "EXACT"
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=mod.name)
        mesh_data = cut_obj.data
        bpy.data.objects.remove(cut_obj, do_unlink=True)
        bpy.data.meshes.remove(mesh_data)
    return recalc_outward(obj)


def bevel(obj, width=0.02, segments=2, angle_limit=math.radians(35)):
    mod = obj.modifiers.new("bevel", "BEVEL")
    mod.width = width
    mod.segments = segments
    mod.limit_method = "ANGLE"
    mod.angle_limit = angle_limit
    return obj


def solidify(obj, thickness=0.06):
    mod = obj.modifiers.new("solidify", "SOLIDIFY")
    mod.thickness = thickness
    return obj


def displace(obj, texture, *, strength=0.12, mid_level=0.5):
    mod = obj.modifiers.new("relief", "DISPLACE")
    mod.texture = texture
    mod.strength = strength
    mod.mid_level = mid_level
    mod.texture_coords = "UV"
    mod.direction = "NORMAL"
    return obj


def triangles(objs, depsgraph=None):
    """Evaluated triangle count (modifiers applied)."""
    depsgraph = depsgraph or bpy.context.evaluated_depsgraph_get()
    total = 0
    for obj in objs:
        if obj.type != "MESH":
            continue
        ev = obj.evaluated_get(depsgraph)
        try:
            mesh = ev.to_mesh()
        except RuntimeError:
            continue
        mesh.calc_loop_triangles()
        total += len(mesh.loop_triangles)
        ev.to_mesh_clear()
    return total


def slotted_panel(name, collection, *, x, y0, y1, z0, z1, holes=(),
                  cuts_per_m=9.0):
    """A camera-facing displaceable surface pierced by rectangular holes.

    Displacement must go on FLAT panels -- a displaced closed box tears along
    its shared edges. But a single unbroken panel cannot show a recess, so the
    wall is instead tiled as a set of independent flat panels laid out around
    the holes. Each piece stays flat and displaceable, and the gaps are real
    openings you can put a dark reveal behind.

    Returns the list of panel objects.
    """
    holes = list(holes)
    ys = sorted({y0, y1} | {h["y0"] for h in holes} | {h["y1"] for h in holes})
    pieces = []
    for a, b in zip(ys[:-1], ys[1:]):
        if b - a < 1e-6:
            continue
        mid = 0.5 * (a + b)
        spanning = [h for h in holes if h["y0"] <= mid <= h["y1"]]
        if not spanning:
            bands = [(z0, z1)]
        else:
            cuts = sorted({z0, z1} | {h["z0"] for h in spanning}
                          | {h["z1"] for h in spanning})
            bands = []
            for c, d in zip(cuts[:-1], cuts[1:]):
                if d - c < 1e-6:
                    continue
                zm = 0.5 * (c + d)
                if any(h["z0"] <= zm <= h["z1"] for h in spanning):
                    continue
                bands.append((c, d))
        for (c, d) in bands:
            cy = max(2, int(round((b - a) * cuts_per_m)))
            cz = max(2, int(round((d - c) * cuts_per_m)))
            pieces.append(panel("%s_%d" % (name, len(pieces)), collection,
                                x=x, y0=a, y1=b, z0=c, z1=d,
                                cuts_y=cy, cuts_z=cz))
    return pieces


def catenary(name, collection, *, y0, y1, x, z_ends, sag, width=0.035,
             segments=24, axis_thickness=0.035):
    """A sagging line (rope, laundry cord, cable) as a thin ribbon.

    Real slack matters: a straight horizontal bar between two points reads as
    engineering, a catenary reads as something someone tied up.
    """
    verts, faces = [], []
    for i in range(segments + 1):
        t = i / segments
        yy = y0 + (y1 - y0) * t
        drop = sag * 4.0 * t * (1.0 - t)
        zz = z_ends - drop
        verts.append((x - axis_thickness * 0.5, yy, zz))
        verts.append((x + axis_thickness * 0.5, yy, zz))
        verts.append((x - axis_thickness * 0.5, yy, zz - width))
        verts.append((x + axis_thickness * 0.5, yy, zz - width))
    for i in range(segments):
        a = i * 4
        b = a + 4
        faces.append((a, b, b + 1, a + 1))
        faces.append((a + 2, a + 3, b + 3, b + 2))
        faces.append((a, a + 2, b + 2, b))
        faces.append((a + 1, b + 1, b + 3, a + 3))
    return recalc_outward(new_mesh_object(name, verts, faces, collection))


def hanging_sheet(name, collection, *, x, y0, y1, z_top, drop, cuts_y=12,
                  cuts_z=12, sway=0.06):
    """A cloth hung from a line: sags along its top edge and drifts forward."""
    ny, nz = int(cuts_y) + 1, int(cuts_z) + 1
    verts, faces = [], []
    for iz in range(nz):
        tz = iz / (nz - 1)
        for iy in range(ny):
            ty = iy / (ny - 1)
            yy = y0 + (y1 - y0) * ty
            hang = 0.10 * (y1 - y0) * 4.0 * ty * (1.0 - ty)
            zz = z_top - hang - drop * tz
            xx = x + sway * math.sin(3.1 * ty + 1.7 * tz) * (0.4 + tz)
            verts.append((xx, yy, zz))
    for iz in range(nz - 1):
        for iy in range(ny - 1):
            a = iz * ny + iy
            faces.append((a, a + ny, a + ny + 1, a + 1))
    obj = new_mesh_object(name, verts, faces, collection)
    mesh = obj.data
    bm = bmesh.new(); bm.from_mesh(mesh)
    for face in bm.faces:
        if face.normal.x > 0:
            face.normal_flip()
    bm.to_mesh(mesh); bm.free(); mesh.update()
    return obj


def ladder(name, collection, *, x, y, z0, z1, width=0.42, rungs=8, stock=0.045):
    parts = []
    for side in (-1, 1):
        rail = slab("%s_R%d" % (name, side), collection,
                    x0=x - stock, x1=x + stock,
                    y0=y + side * width * 0.5 - stock,
                    y1=y + side * width * 0.5 + stock, z0=z0, z1=z1)
        parts.append(rail)
    for i in range(rungs):
        zz = z0 + (z1 - z0) * (i + 0.5) / rungs
        parts.append(slab("%s_S%d" % (name, i), collection,
                          x0=x - stock * 0.7, x1=x + stock * 0.7,
                          y0=y - width * 0.5, y1=y + width * 0.5,
                          z0=zz - stock * 0.7, z1=zz + stock * 0.7))
    return parts


def niche_wall(name, collection, *, x, depth, cells, cell_w, cell_h, gap):
    """A grid of small recesses. Returns (surrounds, cavities).

    This is the one place a repeated module is honest: a votive wall IS a
    repeated module, and the repetition is the architectural point.
    """
    surrounds, cavities = [], []
    for (cy, cz, cols, rows, jitter) in cells:
        for r in range(rows):
            for c in range(cols):
                yy = cy + (c - (cols - 1) * 0.5) * (cell_w + gap)
                zz = cz + r * (cell_h + gap)
                yy += jitter * ((c * 7 + r * 13) % 5 - 2) * 0.01
                cav = slab("%s_C%d_%d_%d" % (name, int(cy * 10), r, c),
                           collection, x0=x + 0.01, x1=x + depth,
                           y0=yy - cell_w * 0.5, y1=yy + cell_w * 0.5,
                           z0=zz, z1=zz + cell_h)
                cavities.append(cav)
                sur = slab("%s_S%d_%d_%d" % (name, int(cy * 10), r, c),
                           collection, x0=x - 0.045, x1=x + 0.012,
                           y0=yy - cell_w * 0.5 - 0.035,
                           y1=yy + cell_w * 0.5 + 0.035,
                           z0=zz - 0.035, z1=zz + cell_h + 0.035)
                bevel(sur, 0.012, 2)
                surrounds.append(sur)
    return surrounds, cavities
