"""One-shot migration helper: give newly scaffolded Batch-B source meshes planar UVs.

Run inside Blender with one authoritative source loaded. This exists only during
initial materialization and is deleted before the migration PR is finalized.
"""
from __future__ import annotations

import bpy

roots = [obj for obj in bpy.context.scene.objects if bool(obj.get("item_export", False))]
if len(roots) != 1:
    raise RuntimeError(f"expected one item_export root, got {[obj.name for obj in roots]}")
root = roots[0]

for obj in root.children_recursive:
    if obj.type != "MESH":
        continue
    mesh = obj.data
    if not mesh.vertices or not mesh.polygons:
        continue
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

bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath, check_existing=False)
print(f"B SOURCE UV OK {bpy.data.filepath}")
