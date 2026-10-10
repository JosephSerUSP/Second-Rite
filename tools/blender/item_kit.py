"""Scaffold helpers for authoring a NEW item ``.blend`` source (runs inside Blender).

An item source is scaffolded once and then edited directly in Blender: the
``.blend`` is the authority afterwards (see assets/authoring/items/README.md).
This module is for the scaffolding step only. It deliberately does not own the
artwork -- it owns the tedious, mistake-prone parts every scaffold repeats:

* the export root and its version-1 contract metadata;
* semantic materials with optional runtime passes and painted textures;
* meshes from raw data (vertices, faces, UVs) with deterministic ordering;
* surfaces of revolution about an arbitrary axis, and *lofts* through
  superelliptic cross-sections (the one form the lathe cannot express);
* a refuse-to-overwrite save.

Nothing here writes outside the path handed to ``save_new``.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import second_rite_asset_core as core  # noqa: E402

TAU = math.tau


# --------------------------------------------------------------------------
# root + save
# --------------------------------------------------------------------------

def begin(item_id: str, grammar: str, description: str, **extra) -> bpy.types.Object:
    """Empty scene plus a tagged export root named ``ITEM_<id>``."""
    core.reset_scene(factory=True)
    root = bpy.data.objects.new(f"ITEM_{item_id}", None)
    bpy.context.scene.collection.objects.link(root)
    root["item_export"] = True
    root["item_export_name"] = item_id
    core.tag_asset_target(
        root, asset_id=item_id, representation="full_model", role="item_display",
        authoring_space="item_display", placement_frame="item_viewport",
    )
    root["sr_source_authority"] = "blend"
    root["sr_authoring_grammar"] = grammar
    root["sr_authoring_description"] = description
    for key, value in extra.items():
        root[key if key.startswith("sr_") else f"sr_{key}"] = value
    return root


def save_new(path: Path) -> Path:
    """Save the scaffold, refusing to replace an existing (authoritative) source."""
    path = Path(path).resolve()
    if path.exists():
        raise SystemExit(
            f"{path} already exists and is the SOURCE AUTHORITY for this item; "
            "edit it in Blender instead of regenerating it."
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(path))
    return path


# --------------------------------------------------------------------------
# materials
# --------------------------------------------------------------------------

def material(name, *, semantic=None, color=(0.5, 0.5, 0.5), passes=None, image=None,
             roughness=None, metallic=None):
    """Semantic (or legacy-derived) material.

    ``passes`` is the runtime overlay list described in the item README.
    ``image`` is a path to a painted albedo PNG; it is wired into Base Color so
    the OBJ exporter writes ``map_Kd`` and COPY-mode puts the file beside the OBJ.
    """
    mat = core.make_material(name, semantic_id=semantic, color=color,
                             roughness=roughness, metallic=metallic)
    if passes:
        mat["sr_runtime_passes_json"] = json.dumps(passes)
    if image is not None:
        nodes, links = mat.node_tree.nodes, mat.node_tree.links
        tex = nodes.new("ShaderNodeTexImage")
        tex.image = bpy.data.images.load(str(Path(image).resolve()), check_existing=True)
        tex.interpolation = "Closest"
        links.new(tex.outputs["Color"], nodes["Principled BSDF"].inputs["Base Color"])
    return mat


# --------------------------------------------------------------------------
# meshes
# --------------------------------------------------------------------------

def mesh_object(name, verts, faces, root, mat=None, *, uvs=None, flat=True, loc=(0, 0, 0),
                rot=(0, 0, 0)):
    """Object from raw data. ``uvs`` is one (u, v) per face corner, or None."""
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([tuple(v) for v in verts], [], [tuple(f) for f in faces])
    mesh.update()
    if uvs is not None:
        layer = mesh.uv_layers.new(name="UVMap")
        flat_uvs = [c for face_uv in uvs for c in face_uv] if uvs and isinstance(uvs[0][0], (tuple, list)) else uvs
        for i, uv in enumerate(flat_uvs):
            layer.data[i].uv = uv
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    if mat is not None:
        obj.data.materials.append(mat)
    if flat:
        core.flat_shade(obj)
    core.parent_local(obj, root, loc=loc, rot=rot)
    return obj


def revolve(profile, *, segments=16, axis="Z", close_bottom=True, close_top=True):
    """Surface of revolution.

    ``profile`` is a list of ``(radius, height)`` from bottom to top. The profile
    axis is ``axis`` ('X', 'Y' or 'Z'); faces are wound outward for all three. Returns ``(verts, faces)``; a profile
    point at radius 0 collapses to a pole (one vertex, triangle fan).
    """
    verts, faces, rings = [], [], []
    for r, h in profile:
        if abs(r) < 1e-9:
            verts.append(_axis(axis, 0.0, 0.0, h))
            rings.append([len(verts) - 1])
            continue
        ring = []
        for i in range(segments):
            a = i / segments * TAU
            verts.append(_axis(axis, r * math.cos(a), r * math.sin(a), h))
            ring.append(len(verts) - 1)
        rings.append(ring)
    for lo, hi in zip(rings, rings[1:]):
        if len(lo) == 1 and len(hi) == 1:
            continue
        if len(lo) == 1:
            for i in range(segments):
                faces.append((lo[0], hi[(i + 1) % segments], hi[i]))
        elif len(hi) == 1:
            for i in range(segments):
                faces.append((lo[i], lo[(i + 1) % segments], hi[0]))
        else:
            for i in range(segments):
                j = (i + 1) % segments
                faces.append((lo[i], lo[j], hi[j], hi[i]))
    if close_bottom and len(rings[0]) > 1:
        faces.append(tuple(reversed(rings[0])))
    if close_top and len(rings[-1]) > 1:
        faces.append(tuple(rings[-1]))
    if axis == "Y":
        # (a, b, h) -> (a, h, b) swaps two axes: a reflection, which turns every
        # face inside out. Re-wind so normals point out for every axis.
        faces = [tuple(reversed(face)) for face in faces]
    return verts, faces


def _axis(axis, a, b, h):
    if axis == "Z":
        return (a, b, h)
    if axis == "Y":
        return (a, h, b)
    return (h, a, b)


def torus(major, minor, *, major_segments=16, minor_segments=6, axis="Y"):
    """Ring of tube radius ``minor`` on a circle of radius ``major`` about ``axis``."""
    verts, faces = [], []
    for i in range(major_segments):
        a = i / major_segments * TAU
        for j in range(minor_segments):
            b = j / minor_segments * TAU
            r = major + minor * math.cos(b)
            verts.append(_axis(axis, r * math.cos(a), r * math.sin(a), minor * math.sin(b)))
    for i in range(major_segments):
        for j in range(minor_segments):
            a0, a1 = i * minor_segments + j, i * minor_segments + (j + 1) % minor_segments
            b0 = ((i + 1) % major_segments) * minor_segments + j
            b1 = ((i + 1) % major_segments) * minor_segments + (j + 1) % minor_segments
            faces.append((a0, b0, b1, a1))
    if axis == "Y":
        faces = [tuple(reversed(face)) for face in faces]
    return verts, faces


def disc_fan(radius, z=0.0, *, segments=16, centre_z=None, axis="Z"):
    """Flat (or domed, via ``centre_z``) disc as a triangle fan facing +axis."""
    cz = z if centre_z is None else centre_z
    verts = [_axis(axis, 0.0, 0.0, cz)] + [
        _axis(axis, radius * math.cos(i / segments * TAU), radius * math.sin(i / segments * TAU), z)
        for i in range(segments)]
    faces = [(0, 1 + i, 1 + (i + 1) % segments) for i in range(segments)]
    if axis == "Y":
        faces = [tuple(reversed(face)) for face in faces]
    return verts, faces


def superellipse(a, b, n, samples, *, t0=0.0, t1=TAU, closed=True):
    """Points of |x/a|^n + |y/b|^n = 1, evenly spread by angle.

    ``closed`` samples [t0, t1) so the last point does not repeat the first;
    an open arc samples [t0, t1] inclusive.
    """
    pts = []
    count = samples if closed else samples + 1
    for i in range(count):
        t = t0 + (t1 - t0) * i / samples
        c, s = math.cos(t), math.sin(t)
        pts.append((a * math.copysign(abs(c) ** (2.0 / n), c),
                    b * math.copysign(abs(s) ** (2.0 / n), s)))
    return pts


def loft(sections, *, samples=24, arc=None, cap_bottom=True, cap_top=True):
    """Skin a stack of cross-sections: the one form the lathe cannot express.

    Each section is a dict with ``z`` plus any of ``a`` (half width, default 1),
    ``b`` (half depth), ``n`` (superellipse exponent: 2 oval, 4 rounded box),
    ``cx``/``cy`` (centre offset), ``twist`` (radians) and ``bump`` -- a function
    of the section angle returning a radial scale, used for ridges and keels.
    All sections share ``samples`` so the quad skin is exact.

    ``arc=(t0, t1)`` makes an open strip (a plate, not a tube): angles are the
    superellipse parameter, so -pi/2 is the -Y (front) point.

    Returns ``(verts, faces, uvs)``; ``uvs`` is one (u, v) per face corner, u
    along the section and v up the stack, ready for ``mesh_object(uvs=...)``.
    """
    closed = arc is None
    t0, t1 = (0.0, TAU) if closed else arc
    verts, rings = [], []
    for sec in sections:
        a, b, n = sec.get("a", 1.0), sec.get("b", 1.0), sec.get("n", 2.0)
        cx, cy, z = sec.get("cx", 0.0), sec.get("cy", 0.0), sec["z"]
        twist, bump = sec.get("twist", 0.0), sec.get("bump")
        ring = []
        for i, (x, y) in enumerate(superellipse(a, b, n, samples, t0=t0, t1=t1, closed=closed)):
            if bump is not None:
                k = bump(t0 + (t1 - t0) * i / samples)
                x, y = x * k, y * k
            if twist:
                x, y = (x * math.cos(twist) - y * math.sin(twist),
                        x * math.sin(twist) + y * math.cos(twist))
            verts.append((x + cx, y + cy, z))
            ring.append(len(verts) - 1)
        rings.append(ring)
    faces, uvs = [], []
    rows = len(sections) - 1
    columns = samples if closed else samples
    for r, (lo, hi) in enumerate(zip(rings, rings[1:])):
        for i in range(columns):
            j = (i + 1) % samples if closed else i + 1
            faces.append((lo[i], lo[j], hi[j], hi[i]))
            u0, u1 = i / samples, (i + 1) / samples
            v0, v1 = r / rows, (r + 1) / rows
            uvs.append([(u0, v0), (u1, v0), (u1, v1), (u0, v1)])
    if closed and cap_bottom:
        faces.append(tuple(reversed(rings[0])))
        uvs.append([(0.5, 0.0)] * len(rings[0]))
    if closed and cap_top:
        faces.append(tuple(rings[-1]))
        uvs.append([(0.5, 1.0)] * len(rings[-1]))
    return verts, faces, uvs


def loft_polys(sections, *, cap_bottom=True, cap_top=True, uv_axes=None):
    """Skin a stack of arbitrary closed polygons (same point count in every section).

    Where ``loft`` interpolates a superellipse, this takes the cross-section
    itself: a blade with ground edges and a fuller, a rib, a keyed bar. Each
    section is ``{"z": height, "pts": [(x, y), ...]}`` counter-clockwise.
    ``uv_axes`` is an optional ``(width, length)`` pair of extents; when given,
    UVs are planar -- u from x across ``width``, v from z along ``length`` --
    so a painted albedo registers with the form.
    """
    count = len(sections[0]["pts"])
    if any(len(sec["pts"]) != count for sec in sections):
        raise ValueError("every section needs the same number of points")
    verts, rings = [], []
    for sec in sections:
        ring = []
        for x, y in sec["pts"]:
            verts.append((x, y, sec["z"]))
            ring.append(len(verts) - 1)
        rings.append(ring)
    faces = []
    for lo, hi in zip(rings, rings[1:]):
        for i in range(count):
            j = (i + 1) % count
            faces.append((lo[i], lo[j], hi[j], hi[i]))
    if cap_bottom:
        faces.append(tuple(reversed(rings[0])))
    if cap_top:
        faces.append(tuple(rings[-1]))
    uvs = None
    if uv_axes is not None:
        width, length = uv_axes
        uvs = [[(verts[vi][0] / width + 0.5, verts[vi][2] / length) for vi in face] for face in faces]
    return verts, faces, uvs


def plate(outline, root, name, mat, thickness, *, loc=(0, 0, 0), plane="XZ", offset=0.0):
    """A planar outline kept as an editable polygon, thickened by a live SOLIDIFY.

    ``outline`` is a list of (u, v); ``plane`` maps it into X/Z (front view, the
    way a blade or guard is read) or X/Y. One n-gon face -- edit the outline in
    Blender and the thickness follows.
    """
    if plane == "XZ":
        verts = [(u, 0.0, v) for u, v in outline]
    else:
        verts = [(u, v, 0.0) for u, v in outline]
    obj = mesh_object(name, verts, [tuple(range(len(verts)))], root, mat, loc=loc)
    solidify(obj, thickness, offset=offset)
    return obj


def solidify(obj, thickness, *, offset=-1.0):
    """Live SOLIDIFY: keep the authored surface editable, evaluate thickness on export."""
    mod = obj.modifiers.new("Thickness", "SOLIDIFY")
    mod.thickness = thickness
    mod.offset = offset
    mod.use_even_offset = True
    return mod


def mirror_x(obj, root):
    """Live MIRROR across the item's own X=0 plane (the root's origin)."""
    mod = obj.modifiers.new("MirrorX", "MIRROR")
    mod.use_axis = (True, False, False)
    mod.mirror_object = root
    mod.use_clip = False
    return mod


def cutter(name, root, verts, faces, loc=(0, 0, 0), rot=(0, 0, 0)):
    """Hidden construction mesh (Boolean cutter, guide). Parented, never exported."""
    obj = mesh_object(name, verts, faces, root, None, loc=loc, rot=rot)
    obj.hide_render = True
    obj.display_type = "WIRE"
    return obj


def boolean_difference(target, cutter_obj):
    mod = target.modifiers.new(f"Cut_{cutter_obj.name}", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.object = cutter_obj
    mod.solver = "EXACT"
    return mod


# --------------------------------------------------------------------------
# Geometry Nodes helpers (tree construction only; the tree stays editable in the .blend)
# --------------------------------------------------------------------------

def gn_tree(name, inputs):
    """New node group. ``inputs`` maps name -> (socket type, default, extra attrs)."""
    old = bpy.data.node_groups.get(name)
    if old is not None:
        bpy.data.node_groups.remove(old)
    tree = bpy.data.node_groups.new(name, "GeometryNodeTree")
    for label, (kind, default, extra) in inputs.items():
        socket = tree.interface.new_socket(label, in_out="INPUT", socket_type=kind)
        if default is not None:
            socket.default_value = default
        for key, value in (extra or {}).items():
            setattr(socket, key, value)
    tree.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    return tree


def gn_node(tree, kind, **props):
    node = tree.nodes.new(kind)
    for key, value in props.items():
        setattr(node, key, value)
    return node


def gn_link(tree, source, source_name, target, target_name):
    tree.links.new(source.outputs[source_name], target.inputs[target_name])


def gn_attach(obj, tree, **inputs):
    """NODES modifier on ``obj`` with inputs set by interface *name*."""
    mod = obj.modifiers.new(tree.name, "NODES")
    mod.node_group = tree
    ids = {item.name: item.identifier for item in tree.interface.items_tree
           if getattr(item, "in_out", None) == "INPUT"}
    for key, value in inputs.items():
        getattr(mod.properties.inputs, ids[key]).value = value
    obj.update_tag()
    return mod


def point_cloud(name, points, root, *, radius=None, loc=(0, 0, 0), guide=True):
    """Vertex-only mesh used as scatter/blob seeds; optional per-point ``radius`` attribute."""
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([tuple(p) for p in points], [], [])
    if radius is not None:
        attr = mesh.attributes.new("radius", "FLOAT", "POINT")
        for i, r in enumerate(radius):
            attr.data[i].value = r
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    core.parent_local(obj, root, loc=loc)
    if guide:
        obj.hide_render = True
        obj.display_type = "WIRE"
    return obj


def evaluated_counts(obj):
    """(vertices, faces) of what the exporter will see for ``obj`` (modifiers applied)."""
    bpy.context.view_layer.update()
    mesh = obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh()
    try:
        return len(mesh.vertices), len(mesh.polygons)
    finally:
        obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh_clear()


def cylindrical_uv(verts, faces, *, axis="Z", scale=1.0):
    """Per-corner UVs wrapped about ``axis``: u = arc length (r*angle), v = height.

    The angle is unwrapped per face against its first corner, so a face that
    straddles the +/-pi seam gets continuous u instead of a smear across the
    whole texture. ``scale`` is texels' worth of UV per world unit.
    """
    uvs = []
    for face in faces:
        ref = None
        row = []
        for vi in face:
            x, y, z = verts[vi]
            a, b, h = {"Z": (x, y, z), "Y": (x, z, y), "X": (y, z, x)}[axis]
            ang = math.atan2(b, a)
            if ref is None:
                ref = ang
            while ang - ref > math.pi:
                ang -= TAU
            while ang - ref < -math.pi:
                ang += TAU
            r = math.hypot(a, b)
            row.append((ang * max(r, 1e-6) * scale, h * scale))
        uvs.append(row)
    return uvs


def curve_tube(name, points, radii, root, mat=None, *, bevel=1.0, resolution=1, cyclic=False, caps=True,
               hide=False, loc=(0, 0, 0)):
    """Editable Bezier tube: ``points`` are (x, y, z) with auto-smoothed handles, ``radii`` one per point.

    Thickness is ``bevel * radius``; per-point radius is the taper. Stays a live
    curve in the source (move points, change radius in Blender); the exporter
    evaluates it.
    """
    data = bpy.data.curves.new(name, "CURVE")
    data.dimensions = "3D"
    data.bevel_depth = bevel
    data.bevel_resolution = resolution
    data.use_fill_caps = caps
    spline = data.splines.new("BEZIER")
    spline.bezier_points.add(len(points) - 1)
    for bp, p, r in zip(spline.bezier_points, points, radii):
        bp.co = p
        bp.radius = r
        bp.handle_left_type = bp.handle_right_type = "AUTO"
    spline.use_cyclic_u = cyclic
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    if mat is not None:
        data.materials.append(mat)
    core.parent_local(obj, root, loc=loc)
    if hide:
        obj.hide_render = True
        obj.display_type = "WIRE"
    return obj


def chain_along(name, curve_obj, root, link_mesh, mat, *, count, pitch):
    """ARRAY of one link unit deformed along ``curve_obj`` (the ARRAY + CURVE composition).

    ``link_mesh`` is (verts, faces) for one repeat of length ``pitch`` along +X
    starting at x=0. The curve stays a hidden, editable guide.
    """
    verts, faces = link_mesh
    obj = mesh_object(name, verts, faces, root, mat, loc=tuple(curve_obj.location))
    arr = obj.modifiers.new("Repeat", "ARRAY")
    arr.fit_type = "FIXED_COUNT"
    arr.count = count
    arr.use_relative_offset = False
    arr.use_constant_offset = True
    arr.constant_offset_displace = (pitch, 0.0, 0.0)
    arr.use_merge_vertices = False
    cm = obj.modifiers.new("AlongCurve", "CURVE")
    cm.object = curve_obj
    cm.deform_axis = "POS_X"
    return obj


def paint_image(path, width, height, pixel):
    """Write a PNG from ``pixel(u, row) -> (r, g, b)`` (0-255, row 0 = top), inside Blender.

    Blender's Python has no PIL; this uses ``bpy.data.images`` so a painted
    albedo or overlay can be authored in the same script that scaffolds the item.
    Returns the absolute path written.
    """
    path = Path(path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    buf = [1.0] * (width * height * 4)
    for row in range(height):
        for u in range(width):
            r, g, b = pixel(u, row)
            i = ((height - 1 - row) * width + u) * 4
            buf[i:i + 4] = [r / 255.0, g / 255.0, b / 255.0, 1.0]
    img = bpy.data.images.new(path.stem + "_paint", width, height, alpha=False)
    img.pixels = buf
    img.filepath_raw = str(path)
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)
    return path


def planar_uv(verts, faces, *, axes=(0, 2), scale=1.0, offset=(0.5, 0.5)):
    """Per-corner planar projection UVs (u,v from two vertex axes)."""
    out = []
    for f in faces:
        for vi in f:
            p = verts[vi]
            out.append((p[axes[0]] * scale + offset[0], p[axes[1]] * scale + offset[1]))
    return out


def report(root, extra=None):
    """One machine-readable line, like the other recipes."""
    lo = Vector((1e9,) * 3)
    hi = Vector((-1e9,) * 3)
    count = 0
    for obj in root.children_recursive:
        if obj.type != "MESH":
            continue
        count += 1
        for corner in obj.bound_box:
            w = obj.matrix_world @ Vector(corner)
            lo = Vector((min(lo[i], w[i]) for i in range(3)))
            hi = Vector((max(hi[i], w[i]) for i in range(3)))
    payload = {"item": root["item_export_name"], "meshObjects": count,
               "min": [round(v, 3) for v in lo], "max": [round(v, 3) for v in hi]}
    payload.update(extra or {})
    print("ITEM KIT RESULT " + json.dumps(payload))
