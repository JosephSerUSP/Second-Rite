"""One-shot migration fix for deterministic Death Sickle crescent export.

Blender 5.0's OBJ exporter is byte-unstable when coincident UV corners on this
hollow crescent are deduplicated during export: identical source documents can
produce different vt counts/indices while geometry stays identical.

For this one source object, apply Solidify once during migration, then give each
source mesh loop a deterministic unique UV coordinate. That removes ambiguous
UV deduplication entirely. The item currently uses material shading rather than
a painted texture, so this source-authoring exception has no visual cost.
Ordinary compilation remains read-only. This helper is deleted before the
migration PR is finalized.
"""
from __future__ import annotations

import math
import bpy

obj = bpy.data.objects.get("B_Crescent")
if obj is None or obj.type != "MESH":
    raise RuntimeError("expected Death Sickle mesh object 'B_Crescent'")

solidify = next((mod for mod in obj.modifiers if mod.type == "SOLIDIFY"), None)
if solidify is None:
    raise RuntimeError("B_Crescent has no SOLIDIFY modifier to materialize")

bpy.ops.object.select_all(action="DESELECT")
obj.hide_set(False)
obj.hide_viewport = False
obj.select_set(True)
bpy.context.view_layer.objects.active = obj
bpy.ops.object.modifier_apply(modifier=solidify.name)

mesh = obj.data
uv = mesh.uv_layers.get("UVMap") or mesh.uv_layers.new(name="UVMap")
loop_count = len(mesh.loops)
side = max(1, math.ceil(math.sqrt(loop_count)))
for loop_index in range(loop_count):
    col = loop_index % side
    row = loop_index // side
    uv.data[loop_index].uv = (
        (col + 0.5) / side,
        (row + 0.5) / side,
    )
mesh.update()

obj["sr_fabrication_exception"] = "explicit_thickness_for_deterministic_uv_export"
obj["sr_original_modifier"] = "SOLIDIFY"
obj["sr_uv_strategy"] = "deterministic_unique_corner_atlas"

bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath, check_existing=False)
print(f"B DEATH SICKLE CRESCENT OK {bpy.data.filepath}")
