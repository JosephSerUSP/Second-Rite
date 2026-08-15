"""One-shot Phoenix Pinion organicity pressure test.

Open the authoritative phoenix_pinion.blend and replace its eight manually
repeated C-vane ribbons with a genuinely hybrid editable construction:

- C: two asymmetrical editable 3D guide curves along the rachis;
- B: one explicit thin fabricated vane source mesh per side;
- Geometry Nodes: resample guides, deliberately omit members, instance vanes,
  and vary local scale/roll deterministically by point index;
- manual B hero vanes: three deliberately placed exceptions that break the
  procedural rhythm;
- A: a tiny profile-driven gold calamus collar near the feather base.

This patch exists only to materialize the proposed authoritative .blend. It is
deleted before a migration PR can be considered final. Ordinary compilation
remains read-only.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "assets" / "authoring" / "items" / "phoenix_pinion.blend"
if Path(bpy.data.filepath).resolve() != SOURCE.resolve():
    raise RuntimeError(f"open {SOURCE} before running this patch")

roots = [obj for obj in bpy.context.scene.objects if bool(obj.get("item_export", False))]
if len(roots) != 1 or roots[0].get("item_export_name") != "phoenix_pinion":
    raise RuntimeError("expected authoritative phoenix_pinion source")
root = roots[0]

body = bpy.data.objects.get("C_Pinion_Body")
spine = bpy.data.objects.get("C_Pinion_Spine")
if body is None or spine is None:
    raise RuntimeError("expected migrated C_Pinion_Body and C_Pinion_Spine")
crystal = body.active_material
ritual_gold = spine.active_material
if crystal is None or ritual_gold is None:
    raise RuntimeError("Phoenix source materials are missing")


def c2b(point):
    x, y, z = point
    return (x, -z, y)


def parent_local(obj):
    obj.parent = root
    obj.matrix_parent_inverse = root.matrix_world.inverted()


def delete_object(obj):
    for child in list(obj.children):
        delete_object(child)
    data = obj.data
    bpy.data.objects.remove(obj, do_unlink=True)
    if data is not None and getattr(data, "users", 1) == 0:
        collection = getattr(bpy.data, data.__class__.__name__.lower() + "s", None)
        # Blender datablock collection names are not reliably derivable; orphan
        # cleanup is intentionally left to Blender save rather than guessed.


# Remove the old eight hand-authored sparse C vanes and their source profiles.
for obj in list(bpy.data.objects):
    if obj.name.startswith("C_Vane_"):
        delete_object(obj)


def make_prism_vane(name, side, *, reach=.36, rise=.15, width=.085, thickness=.018):
    """Explicit low-poly B vane in local X/Z plane, with Y thickness."""
    s = 1.0 if side > 0 else -1.0
    x0 = 0.018 * s
    x1 = reach * 0.45 * s
    x2 = reach * s
    z1 = rise * 0.42
    z2 = rise
    half = thickness * 0.5
    outline = [
        (x0, -width * .22, 0.0),
        (x1, -width * .52, z1),
        (x2, -width * .12, z2),
        (x1, width * .45, z1 * .94),
    ]
    verts = [(x, -half, z) for x, _, z in outline] + [(x, half, z) for x, _, z in outline]
    # Add the authored in-plane width as a small local-Y displacement while
    # retaining real thickness through a second, much smaller offset.
    verts = []
    for layer in (-1.0, 1.0):
        for x, lateral, z in outline:
            verts.append((x, lateral + layer * half, z))
    faces = [
        (0, 1, 2, 3), (7, 6, 5, 4),
        (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0),
    ]
    mesh = bpy.data.meshes.new(name + "Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.materials.append(crystal)
    uv = mesh.uv_layers.new(name="UVMap")
    # Unique per-corner UVs keep the source deterministic through OBJ export.
    loop_count = len(mesh.loops)
    side_len = max(1, math.ceil(math.sqrt(loop_count)))
    for i in range(loop_count):
        uv.data[i].uv = ((i % side_len + .5) / side_len, (i // side_len + .5) / side_len)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    parent_local(obj)
    obj.hide_render = True
    obj.display_type = "WIRE"
    obj["sr_authoring_role"] = "fabricated_vane_source"
    obj["sr_vane_side"] = "right" if side > 0 else "left"
    return obj


vane_left = make_prism_vane("B_Vane_Source_L", -1, reach=.34, rise=.15, width=.075)
vane_right = make_prism_vane("B_Vane_Source_R", 1, reach=.37, rise=.17, width=.082)


def make_guide(name, points, tilts):
    curve = bpy.data.curves.new(name + "Data", type="CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 1
    curve.render_resolution_u = 1
    curve.twist_mode = "MINIMUM"
    spline = curve.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for p, tilt, point in zip(points, tilts, spline.points):
        point.co = (*c2b(p), 1.0)
        point.tilt = math.radians(tilt)
    obj = bpy.data.objects.new(name, curve)
    bpy.context.scene.collection.objects.link(obj)
    parent_local(obj)
    obj["sr_authoring_role"] = "organic_vane_guide"
    return obj


left_guide = make_guide(
    "C_Vane_Guide_L",
    [(0.00,-0.50,0.035),(-0.015,-0.30,0.060),(-0.035,-0.07,0.100),
     (-0.020,0.18,0.145),(-0.060,0.43,0.180),(-0.075,0.68,0.155),
     (-0.030,0.90,0.095)],
    [-8,-3,5,14,24,36,48],
)
right_guide = make_guide(
    "C_Vane_Guide_R",
    [(0.012,-0.46,0.030),(0.042,-0.24,0.055),(0.020,0.00,0.100),
     (0.072,0.26,0.150),(0.045,0.50,0.182),(0.008,0.72,0.140),
     (0.025,0.92,0.075)],
    [7,12,18,27,38,50,61],
)


def input_socket(node, name):
    sock = node.inputs.get(name)
    if sock is None:
        raise RuntimeError(f"{node.bl_idname} has no input {name!r}; inputs={[s.name for s in node.inputs]}")
    return sock


def output_socket(node, name):
    sock = node.outputs.get(name)
    if sock is None:
        raise RuntimeError(f"{node.bl_idname} has no output {name!r}; outputs={[s.name for s in node.outputs]}")
    return sock


def math_node(nodes, op, value=None):
    n = nodes.new("ShaderNodeMath")
    n.operation = op
    if value is not None:
        n.inputs[1].default_value = value
    return n


def make_distribution(guide, source, *, count, skip_mod, side, phase):
    mod = guide.modifiers.new("Organic Vane Distribution", "NODES")
    group = bpy.data.node_groups.new(guide.name + "_OrganicDistribution", "GeometryNodeTree")
    group.interface.new_socket(name="Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    group.interface.new_socket(name="Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    mod.node_group = group
    nodes = group.nodes
    links = group.links

    g_in = nodes.new("NodeGroupInput")
    g_out = nodes.new("NodeGroupOutput")
    trim = nodes.new("GeometryNodeTrimCurve")
    trim.mode = "FACTOR"
    input_socket(trim, "Start").default_value = .08
    input_socket(trim, "End").default_value = .94
    points = nodes.new("GeometryNodeCurveToPoints")
    points.mode = "COUNT"
    input_socket(points, "Count").default_value = count
    obj_info = nodes.new("GeometryNodeObjectInfo")
    input_socket(obj_info, "Object").default_value = source
    as_instance = obj_info.inputs.get("As Instance")
    if as_instance is not None:
        as_instance.default_value = True
    index = nodes.new("GeometryNodeInputIndex")

    # Deliberately omit every Nth sampled member. Because left/right use
    # different N and point counts, the gaps never line up into a ladder.
    modulo = math_node(nodes, "MODULO", float(skip_mod))
    selected = math_node(nodes, "GREATER_THAN", .5)
    links.new(output_socket(index, "Index"), modulo.inputs[0])
    links.new(modulo.outputs[0], selected.inputs[0])

    # A deterministic quasi-random-looking scalar from point index.
    mul = math_node(nodes, "MULTIPLY", 1.731 + phase)
    add_phase = math_node(nodes, "ADD", phase * 2.17)
    wave = math_node(nodes, "SINE")
    links.new(output_socket(index, "Index"), mul.inputs[0])
    links.new(mul.outputs[0], add_phase.inputs[0])
    links.new(add_phase.outputs[0], wave.inputs[0])

    # Length envelope shrinks toward the tip, with bounded nonuniformity.
    env_mul = math_node(nodes, "MULTIPLY", -0.055 if side < 0 else -0.062)
    env_add = math_node(nodes, "ADD", 1.08 if side < 0 else 1.12)
    wiggle = math_node(nodes, "MULTIPLY", .13)
    scale_x = math_node(nodes, "ADD")
    links.new(output_socket(index, "Index"), env_mul.inputs[0])
    links.new(env_mul.outputs[0], env_add.inputs[0])
    links.new(wave.outputs[0], wiggle.inputs[0])
    links.new(env_add.outputs[0], scale_x.inputs[0])
    links.new(wiggle.outputs[0], scale_x.inputs[1])

    width_wiggle = math_node(nodes, "MULTIPLY", .10)
    width_add = math_node(nodes, "ADD", .90 if side < 0 else .84)
    links.new(wave.outputs[0], width_wiggle.inputs[0])
    links.new(width_wiggle.outputs[0], width_add.inputs[0])

    scale = nodes.new("ShaderNodeCombineXYZ")
    links.new(scale_x.outputs[0], input_socket(scale, "X"))
    links.new(width_add.outputs[0], input_socket(scale, "Y"))
    input_socket(scale, "Z").default_value = .78 if side < 0 else .86

    instance = nodes.new("GeometryNodeInstanceOnPoints")
    links.new(output_socket(points, "Points"), input_socket(instance, "Points"))
    links.new(selected.outputs[0], input_socket(instance, "Selection"))
    links.new(output_socket(obj_info, "Geometry"), input_socket(instance, "Instance"))
    links.new(output_socket(points, "Rotation"), input_socket(instance, "Rotation"))
    links.new(output_socket(scale, "Vector"), input_socket(instance, "Scale"))

    # Local roll/fan variation breaks the repeated-machine rhythm while the
    # guide still controls the coherent overall feather gesture.
    rot_wave = math_node(nodes, "MULTIPLY", .20 * side)
    links.new(wave.outputs[0], rot_wave.inputs[0])
    rot = nodes.new("ShaderNodeCombineXYZ")
    input_socket(rot, "X").default_value = .08 * side
    input_socket(rot, "Y").default_value = .16 * side
    base_roll = math_node(nodes, "ADD", .38 * side)
    links.new(rot_wave.outputs[0], base_roll.inputs[0])
    links.new(base_roll.outputs[0], input_socket(rot, "Z"))

    rotate = nodes.new("GeometryNodeRotateInstances")
    links.new(output_socket(instance, "Instances"), input_socket(rotate, "Instances"))
    links.new(output_socket(rot, "Vector"), input_socket(rotate, "Rotation"))
    local = rotate.inputs.get("Local Space")
    if local is not None:
        local.default_value = True

    realize = nodes.new("GeometryNodeRealizeInstances")
    links.new(output_socket(rotate, "Instances"), input_socket(realize, "Geometry"))

    links.new(output_socket(g_in, "Geometry"), input_socket(trim, "Curve"))
    links.new(output_socket(trim, "Curve"), input_socket(points, "Curve"))
    links.new(output_socket(realize, "Geometry"), input_socket(g_out, "Geometry"))

    guide["sr_distribution_side"] = "left" if side < 0 else "right"
    guide["sr_distribution_count"] = count
    guide["sr_distribution_skip_mod"] = skip_mod
    guide["sr_distribution_phase"] = phase
    return group


make_distribution(left_guide, vane_left, count=10, skip_mod=5, side=-1, phase=.17)
make_distribution(right_guide, vane_right, count=9, skip_mod=4, side=1, phase=.43)


def make_hero_vane(name, origin, tip, width, thickness=.020):
    """Manual B-authored hero exception in authoritative world coordinates."""
    ox, oy, oz = c2b(origin)
    tx, ty, tz = c2b(tip)
    vx, vy, vz = tx-ox, ty-oy, tz-oz
    length = math.sqrt(vx*vx + vy*vy + vz*vz)
    if length < 1e-5:
        raise ValueError(name)
    # Build a simple broad wedge around the line. Its local geometry is not
    # procedurally tied to the guide on purpose: it is a manual exception.
    perp = (-vy/length, vx/length, 0.0)
    px, py, pz = (perp[0]*width, perp[1]*width, width*.10)
    n = thickness*.5
    base = [(ox-px*.35, oy-py*.35, oz-pz*.35),
            (tx-px, ty-py, tz-pz),
            (tx+px*.40, ty+py*.40, tz+pz*.40),
            (ox+px*.35, oy+py*.35, oz+pz*.35)]
    verts = [(x,y,z-n) for x,y,z in base] + [(x,y,z+n) for x,y,z in base]
    faces=[(0,1,2,3),(7,6,5,4),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)]
    mesh=bpy.data.meshes.new(name+"Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.materials.append(crystal)
    uv=mesh.uv_layers.new(name="UVMap")
    l=len(mesh.loops); s=max(1,math.ceil(math.sqrt(l)))
    for i in range(l): uv.data[i].uv=((i%s+.5)/s,(i//s+.5)/s)
    mesh.update()
    obj=bpy.data.objects.new(name,mesh)
    bpy.context.scene.collection.objects.link(obj)
    parent_local(obj)
    obj["sr_authoring_role"]="manual_hero_vane"
    return obj


make_hero_vane("B_HeroVane_Low_R", (0.01,-0.28,0.06), (0.48,-0.17,0.18), .060)
make_hero_vane("B_HeroVane_Mid_L", (-0.01,0.28,0.15), (-0.46,0.39,0.27), .072)
make_hero_vane("B_HeroVane_Broken_R", (0.00,0.60,0.16), (0.27,0.69,0.22), .046)


def add_calamus_collar():
    curve = bpy.data.curves.new("A_Calamus_Collar_ProfileData", type="CURVE")
    curve.dimensions = "3D"
    spline = curve.splines.new("POLY")
    profile=[(-.035,.070),(-.020,.090),(.020,.090),(.035,.070)]
    spline.points.add(len(profile)-1)
    for point,(z,radius) in zip(spline.points,profile):
        point.co=(radius,0,z,1)
    obj=bpy.data.objects.new("A_Calamus_Collar",curve)
    bpy.context.scene.collection.objects.link(obj)
    parent_local(obj)
    obj.location=c2b((0.0,-0.70,0.0))
    curve.materials.append(ritual_gold)
    screw=obj.modifiers.new("Revolve","SCREW")
    screw.axis="Z"; screw.angle=math.tau; screw.steps=10; screw.render_steps=10
    screw.use_merge_vertices=True; screw.use_smooth_shade=True
    screw.use_normal_calculate=True; screw.use_stretch_u=True; screw.use_stretch_v=True
    obj["sr_authoring_role"]="semantic_calamus_collar"
    obj["sr_profile_points_json"]=json.dumps(profile)


add_calamus_collar()

root["sr_hybrid_authoring"] = "A+B+C+GeometryNodes"
root["sr_hybrid_goal"] = "procedural structure without procedural sameness"
root["sr_geometry_nodes_baseline"] = "earned_by_organic_instance_variation"

readme = bpy.data.texts.get("AUTHORING_README") or bpy.data.texts.new("AUTHORING_README")
readme.write(
    "\n\nOrganic hybrid pass:\n"
    "C_Vane_Guide_L/R are the large-scale feather gestures. Each owns a Geometry Nodes modifier that samples points and instances the hidden B_Vane_Source_L/R fabricated meshes. Point-index fields deliberately vary scale/roll and omit different members on each side. B_HeroVane_* objects are manual art-directed exceptions. A_Calamus_Collar is a tiny semantic revolve detail. Edit the guide curves and source vanes directly; do not regenerate this file from the migration patch.\n"
)

bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE), check_existing=False)
print("PHOENIX ORGANIC HYBRID SOURCE OK", SOURCE)
