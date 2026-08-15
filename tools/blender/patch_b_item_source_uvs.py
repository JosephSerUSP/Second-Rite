"""One-shot migration helper: give Batch-B source meshes deterministic UVs.

Blender 5.0's OBJ exporter may deduplicate coincident UV corners differently
between otherwise identical exports. Batch B currently uses material shading
rather than painted image textures, so the migration assigns every source mesh
loop a unique deterministic atlas coordinate.

For live Mirror modifiers, the mirrored copy is shifted by one UV tile on U.
That preserves the useful edit-one-side authoring modifier while preventing its
copied UVs from overlapping the source side during OBJ export.

Rear Mirror additionally materializes its Solidify thickness once during this
migration because modifier-generated side UVs remain byte-unstable. Its planar
silhouette meshes remain authoritative and directly editable.

If an asset later needs painted textures, author proper UVs directly in its
committed .blend; this helper exists only for initial migration and is deleted
before the migration PR is finalized.
"""
from __future__ import annotations

import math
import runpy
from pathlib import Path
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
    obj["sr_uv_strategy"] = "deterministic_unique_corner_atlas"

    for modifier in obj.modifiers:
        if modifier.type != "MIRROR":
            continue
        # Blender's Mirror modifier offsets only the generated mirrored UVs,
        # keeping the live authoring symmetry while making both UV sets unique.
        modifier.offset_u = 1.0
        modifier.offset_v = 0.0
        obj["sr_mirror_uv_strategy"] = "offset_generated_copy_u_plus_1"

bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath, check_existing=False)

if root.get("item_export_name") == "rear_mirror":
    runpy.run_path(str(Path(__file__).with_name("patch_b_rear_mirror_thickness.py")), run_name="__main__")
else:
    print(f"B SOURCE UV OK {bpy.data.filepath}")
