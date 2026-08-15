"""Validate that a generated study .blend retained meaningful editable structure.

Run with Blender:
    blender --background path/to/file.blend --python tools/blender/check_editable_item_blend.py
"""

from __future__ import annotations

import sys

import bpy

EXPECTED = {
    "study_screw_reliquary": {"modifiers": {"SCREW"}, "curves": 0},
    "study_fabricated_mask": {"modifiers": {"SOLIDIFY", "BOOLEAN", "BEVEL"}, "curves": 0},
    "study_curve_fang": {"modifiers": set(), "curves": 2},
    "study_segmented_spine": {"modifiers": {"SOLIDIFY", "ARRAY", "CURVE", "SIMPLE_DEFORM"}, "curves": 2},
    "study_phoenix_pinion": {"modifiers": {"SCREW", "SOLIDIFY", "ARRAY", "CURVE", "SIMPLE_DEFORM"}, "curves": 2},
}


def fail(message):
    print(f"EDITABLE BLEND INVALID: {message}", file=sys.stderr)
    raise SystemExit(1)


roots = [obj for obj in bpy.context.scene.objects if bool(obj.get("item_export", False))]
if len(roots) != 1:
    fail(f"expected exactly one marked export root, got {[obj.name for obj in roots]}")

root = roots[0]
item_id = root.get("item_export_name")
if item_id not in EXPECTED:
    fail(f"unexpected study item id {item_id!r}")
if root.get("sr_source_authority") != "blend":
    fail(f"{item_id}: source authority marker is not blend")
if not bool(root.get("sr_study_only", False)):
    fail(f"{item_id}: missing study-only marker")
if bpy.data.texts.get("AUTHORING_README") is None:
    fail(f"{item_id}: missing embedded AUTHORING_README")

children = list(root.children_recursive)
modifier_types = {modifier.type for obj in children for modifier in getattr(obj, "modifiers", [])}
curve_count = sum(1 for obj in children if obj.type == "CURVE")
mesh_count = sum(1 for obj in children if obj.type == "MESH")
expectation = EXPECTED[item_id]
missing = expectation["modifiers"] - modifier_types
if missing:
    fail(f"{item_id}: missing live modifiers {sorted(missing)}; found {sorted(modifier_types)}")
if curve_count < expectation["curves"]:
    fail(f"{item_id}: expected >= {expectation['curves']} editable curves, got {curve_count}")
if mesh_count == 0 and curve_count == 0:
    fail(f"{item_id}: no editable mesh or curve source objects")

print(
    f"EDITABLE BLEND OK {item_id}: objects={len(children)} meshes={mesh_count} "
    f"curves={curve_count} modifiers={sorted(modifier_types)}"
)
