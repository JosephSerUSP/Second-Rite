"""One-shot migration fix for deterministic Silver Glasses export.

Keep the useful live MIRROR authoring relationship, but materialize SOLIDIFY on
the authored-half meshes before Mirror evaluates them. Blender 5.0 otherwise
produces context-sensitive OBJ UV tables for some modifier-generated surfaces.
After applying thickness, reassign deterministic unique per-corner UVs. Mirror
remains live and offsets its generated UV set by +1 U tile.

This helper exists only during migration and is deleted before the PR is final.
Fresh-run marker: retry the same source fix on a healthy hosted runner.
"""
from __future__ import annotations

import math
import bpy

roots = [obj for obj in bpy.context.scene.objects if bool(obj.get("item_export", False))]
if len(roots) != 1 or roots[0].get("item_export_name") != "silver_glasses":
    raise RuntimeError("expected the authoritative silver_glasses source")
root = roots[0]

applied = []
for obj in list(root.children_recursive):
    if obj.type != "MESH":
        continue
    solidifies = [mod for mod in obj.modifiers if mod.type == "SOLIDIFY"]
    if not solidifies:
        continue

    bpy.ops.object.select_all(action="DESELECT")
    obj.hide_set(False)
    obj.hide_viewport = False
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    for modifier in solidifies:
        bpy.ops.object.modifier_apply(modifier=modifier.name)
    applied.append(obj.name)

    mesh = obj.data
    uv = mesh.uv_layers.get("UVMap") or mesh.uv_layers.new(name="UVMap")
    loop_count = len(mesh.loops)
    side = max(1, math.ceil(math.sqrt(loop_count)))
    for loop_index in range(loop_count):
        col = loop_index % side
        row = loop_index // side
        uv.data[loop_index].uv = ((col + 0.5) / side, (row + 0.5) / side)
    mesh.update()
    obj["sr_fabrication_exception"] = "explicit_thickness_preserve_live_mirror"
    obj["sr_original_modifier"] = "SOLIDIFY"
    obj["sr_uv_strategy"] = "deterministic_unique_corner_atlas"

    for modifier in obj.modifiers:
        if modifier.type == "MIRROR":
            modifier.offset_u = 1.0
            modifier.offset_v = 0.0
            obj["sr_mirror_uv_strategy"] = "offset_generated_copy_u_plus_1"

if not applied:
    raise RuntimeError("silver_glasses contained no SOLIDIFY modifiers to materialize")

root["sr_explicit_thickness_objects"] = ",".join(sorted(applied))
root["sr_live_symmetry"] = "MIRROR"
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath, check_existing=False)
print(f"B SILVER GLASSES THICKNESS OK {bpy.data.filepath}: {sorted(applied)}")
