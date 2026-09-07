"""Small deterministic modeling helpers shared by First Stratum recipes."""
from __future__ import annotations


def material(core, semantic_id):
    return core.make_material(f"sr_{semantic_id}", semantic_id=semantic_id)


def box_geometry(size):
    """Return (vertices, faces) for an axis-aligned box with outward-facing CCW quad winding."""
    sx, sy, sz = (float(value) for value in size)
    vertices = [
        (-sx / 2, -sy / 2, -sz / 2), (sx / 2, -sy / 2, -sz / 2),
        (sx / 2, sy / 2, -sz / 2), (-sx / 2, sy / 2, -sz / 2),
        (-sx / 2, -sy / 2, sz / 2), (sx / 2, -sy / 2, sz / 2),
        (sx / 2, sy / 2, sz / 2), (-sx / 2, sy / 2, sz / 2),
    ]
    # Each face is ordered CCW when viewed from outside the box,
    # ensuring outward-pointing surface normals:
    # 0: bottom (-Z), 1: top (+Z), 2: front (-Y), 3: right (+X), 4: back (+Y), 5: left (-X)
    faces = [
        (0, 3, 2, 1),
        (4, 5, 6, 7),
        (0, 1, 5, 4),
        (1, 2, 6, 5),
        (2, 3, 7, 6),
        (3, 0, 4, 7),
    ]
    return vertices, faces


def box(name, parent, size, location, material_value, core, *, rotation=(0, 0, 0), bevel=0.0):
    import bpy
    vertices, faces = box_geometry(size)
    mesh = bpy.data.meshes.new(f"{name}_mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    core.parent_local(obj, parent, loc=location, rot=rotation)
    core.assign_material(obj, material_value)
    core.flat_shade(obj)
    core.add_bevel_modifier(obj, width=float(bevel), segments=1)
    return obj


def empty(name, parent, location, core, *, rotation=(0, 0, 0), socket_kind=None):
    import bpy
    obj = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(obj)
    core.parent_local(obj, parent, loc=location, rot=rotation)
    obj.empty_display_type = "PLAIN_AXES"
    obj.empty_display_size = 0.05
    if socket_kind:
        obj["sr_socket_kind"] = socket_kind
    return obj


def socket_row(name, kind, location):
    return {"name": name, "kind": kind, "location": [round(float(v), 6) for v in location]}
