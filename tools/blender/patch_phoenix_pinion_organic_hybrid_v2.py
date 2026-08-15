"""Second Phoenix organic-hybrid pass: make the hybrid visible in silhouette.

V1 proved that A+B+C+Geometry Nodes compiles reproducibly, but viewer review
rejected it as an art result: most generated vanes lived inside the continuous
body and read as extra ribbing. V2 keeps the same editable architecture while:

- narrowing the continuous C body slightly;
- moving left/right C distribution guides a little outward;
- reducing generated member counts;
- lengthening the B-authored source vanes;
- increasing local fan/roll variation.

The goal is fewer, clearer, asymmetrical silhouette-owning vanes rather than a
more complicated internal pattern. This script is migration-only.
"""
from __future__ import annotations

from pathlib import Path
import bpy

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "assets" / "authoring" / "items" / "phoenix_pinion.blend"
if Path(bpy.data.filepath).resolve() != SOURCE.resolve():
    raise RuntimeError(f"open {SOURCE} before running this patch")

roots = [o for o in bpy.context.scene.objects if bool(o.get("item_export", False))]
if len(roots) != 1 or roots[0].get("item_export_name") != "phoenix_pinion":
    raise RuntimeError("expected authoritative phoenix_pinion source")
root = roots[0]

body = bpy.data.objects.get("C_Pinion_Body")
left = bpy.data.objects.get("C_Vane_Guide_L")
right = bpy.data.objects.get("C_Vane_Guide_R")
source_l = bpy.data.objects.get("B_Vane_Source_L")
source_r = bpy.data.objects.get("B_Vane_Source_R")
if None in (body, left, right, source_l, source_r):
    raise RuntimeError("V1 organic-hybrid source objects are missing")

# Let authored vanes contribute to the contour instead of hiding under the
# continuous almond-shaped body. This is an ordinary source transform, not an
# export-only optimization.
body.scale.x = 0.84
body["sr_hybrid_body_width_scale"] = 0.84

# Separate the two distribution gestures slightly so their roots do not form a
# mechanically centered ladder.
left.location.x = -0.035
right.location.x = 0.028

# Make the B vane vocabulary more silhouette-capable without increasing node
# complexity. The hidden source objects remain directly editable.
for source, x_scale, z_scale in ((source_l, 1.52, 1.16), (source_r, 1.46, 1.22)):
    for vertex in source.data.vertices:
        vertex.co.x *= x_scale
        vertex.co.z *= z_scale
        vertex.co.y *= 0.92
    source.data.update()
    source["sr_v2_length_scale"] = x_scale
    source["sr_v2_sweep_scale"] = z_scale


def tune_distribution(guide, count, fan_scale, base_roll):
    mods = [m for m in guide.modifiers if m.type == "NODES" and m.node_group]
    if len(mods) != 1:
        raise RuntimeError(f"{guide.name}: expected one Geometry Nodes modifier")
    group = mods[0].node_group

    point_nodes = [n for n in group.nodes if n.bl_idname == "GeometryNodeCurveToPoints"]
    if len(point_nodes) != 1:
        raise RuntimeError(f"{guide.name}: expected one Curve to Points node")
    point_nodes[0].inputs["Count"].default_value = count

    rotate_nodes = [n for n in group.nodes if n.bl_idname == "GeometryNodeRotateInstances"]
    if len(rotate_nodes) != 1:
        raise RuntimeError(f"{guide.name}: expected one Rotate Instances node")
    rotate = rotate_nodes[0]
    incoming = [l for l in group.links if l.to_node == rotate and l.to_socket == rotate.inputs.get("Rotation")]
    if len(incoming) != 1 or incoming[0].from_node.bl_idname != "ShaderNodeCombineXYZ":
        raise RuntimeError(f"{guide.name}: rotation field shape changed")
    combine = incoming[0].from_node
    combine.inputs["X"].default_value *= 1.45
    combine.inputs["Y"].default_value *= 1.35

    z_links = [l for l in group.links if l.to_node == combine and l.to_socket == combine.inputs.get("Z")]
    if len(z_links) != 1 or z_links[0].from_node.bl_idname != "ShaderNodeMath":
        raise RuntimeError(f"{guide.name}: roll field shape changed")
    roll_add = z_links[0].from_node
    if roll_add.operation != "ADD":
        raise RuntimeError(f"{guide.name}: expected ADD roll node")
    sign = -1.0 if guide.get("sr_distribution_side") == "left" else 1.0
    roll_add.inputs[1].default_value = base_roll * sign

    wave_links = [l for l in group.links if l.to_node == roll_add and l.to_socket == roll_add.inputs[0]]
    if len(wave_links) == 1 and wave_links[0].from_node.bl_idname == "ShaderNodeMath":
        wave_scale = wave_links[0].from_node
        if wave_scale.operation == "MULTIPLY":
            wave_scale.inputs[1].default_value = fan_scale * sign

    guide["sr_distribution_count_v2"] = count
    guide["sr_fan_scale_v2"] = fan_scale
    guide["sr_base_roll_v2"] = base_roll


tune_distribution(left, count=7, fan_scale=.31, base_roll=.54)
tune_distribution(right, count=6, fan_scale=.27, base_roll=.62)

# Hero exceptions should remain rare but clearly win against the continuous
# body. Give the long left/right authored exceptions a little more presence.
for name, factor in (("B_HeroVane_Low_R", 1.10), ("B_HeroVane_Mid_L", 1.12), ("B_HeroVane_Broken_R", .96)):
    obj = bpy.data.objects.get(name)
    if obj is None:
        raise RuntimeError(f"missing {name}")
    # The hero mesh stores authoritative world-ish coordinates under a root at
    # the origin. Scale X around the mean X so its attachment point does not
    # wander dramatically.
    xs = [v.co.x for v in obj.data.vertices]
    centre = sum(xs) / len(xs)
    for v in obj.data.vertices:
        v.co.x = centre + (v.co.x - centre) * factor
    obj.data.update()
    obj["sr_v2_silhouette_factor"] = factor

root["sr_hybrid_visual_pass"] = "v2_silhouette_owned_vanes"
readme = bpy.data.texts.get("AUTHORING_README")
if readme:
    readme.write(
        "\nV2 viewer correction: the first hybrid graph compiled cleanly but kept too many generated vanes inside the body silhouette. The accepted-direction pass narrows C_Pinion_Body, lengthens the two B source vanes, reduces counts, offsets the two guides and increases local fan variation so authored vanes own meaningful contour.\n"
    )

bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE), check_existing=False)
print("PHOENIX ORGANIC HYBRID V2 SOURCE OK", SOURCE)
