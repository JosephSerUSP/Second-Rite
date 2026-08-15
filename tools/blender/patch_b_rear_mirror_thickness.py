"""One-shot migration fix for deterministic Rear Mirror export.

Rear Mirror's planar fabrication meshes are valid, but Blender 5.0's evaluated
Solidify surfaces can emit byte-unstable OBJ UV corner tables across identical
exports. During migration only, materialize SOLIDIFY on the mirror's source
meshes, then assign deterministic unique per-corner UVs to the explicit thin
meshes. Silhouette editing remains direct in the authoritative .blend; ordinary
compilation remains read-only. This helper is deleted before the PR is final.
"""
from __future__ import annotations

import math
import bpy

roots = [obj for obj in bpy.context.scene.objects if bool(obj.get("item_export", False))]
if len(roots) != 1 or roots[0].get("item_export_name") != "rear_mirror":
    raise RuntimeError("expected the authoritative rear_mirror source")
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
    obj["sr_fabrication_exception"] = "explicit_thickness_for_deterministic_uv_export"
    obj["sr_original_modifier"] = "SOLIDIFY"
    obj["sr_uv_strategy"] = "deterministic_unique_corner_atlas"

if not applied:
    raise RuntimeError("rear_mirror contained no SOLIDIFY modifiers to materialize")

root["sr_explicit_thickness_objects"] = ",".join(sorted(applied))
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath, check_existing=False)
print(f"B REAR MIRROR THICKNESS OK {bpy.data.filepath}: {sorted(applied)}")
