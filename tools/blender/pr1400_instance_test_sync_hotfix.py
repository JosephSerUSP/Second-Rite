#!/usr/bin/env python3
"""One-shot fix: compare instance source state from an evaluated baseline."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEST = ROOT / "tools/blender/tests/item_instance_export_blender.py"
text = TEST.read_text(encoding="utf-8")
needle = '''    source_object_count = len(bpy.data.objects)
    source_collection_count = len(bpy.data.collections)
'''
replacement = '''    # Establish an evaluated baseline before the exporter performs its own
    # defensive view-layer synchronization. A dependency-graph refresh is not
    # an authoritative transform mutation.
    bpy.context.view_layer.update()
    source_object_count = len(bpy.data.objects)
    source_collection_count = len(bpy.data.collections)
'''
if text.count(needle) != 1:
    raise SystemExit("instance test baseline insertion point drifted")
TEST.write_text(text.replace(needle, replacement, 1), encoding="utf-8")
print("PR1400 INSTANCE TEST SYNC HOTFIX PATCHED")
