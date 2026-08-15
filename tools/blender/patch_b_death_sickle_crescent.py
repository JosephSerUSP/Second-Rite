"""One-shot migration fix for deterministic Death Sickle crescent export.

Blender 5.0's OBJ exporter produces byte-unstable UV corner indexing when the
hollow crescent band is left as a planar mesh with a live Solidify modifier.
Geometry is stable; only generated UV indices differ between identical exports.

For this one source object, apply Solidify once during migration, then author a
deterministic planar UV layer on the resulting explicit thin mesh. The .blend
remains authoritative and editable; ordinary compilation stays read-only.
This helper is deleted before the migration PR is finalized.
"""
from __future__ import annotations

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
xs = [v.co.x for v in mesh.vertices]
zs = [v.co.z for v in mesh.vertices]
min_x, max_x = min(xs), max(xs)
min_z, max_z = min(zs), max(zs)
span_x = max(max_x - min_x, 1e-6)
span_z = max(max_z - min_z, 1e-6)
for poly in mesh.polygons:
    for loop_index in poly.loop_indices:
        vertex = mesh.vertices[mesh.loops[loop_index].vertex_index]
        uv.data[loop_index].uv = (
            (vertex.co.x - min_x) / span_x,
            (vertex.co.z - min_z) / span_z,
        )
mesh.update()

obj["sr_fabrication_exception"] = "explicit_thickness_for_deterministic_uv_export"
obj["sr_original_modifier"] = "SOLIDIFY"

bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath, check_existing=False)
print(f"B DEATH SICKLE CRESCENT OK {bpy.data.filepath}")
