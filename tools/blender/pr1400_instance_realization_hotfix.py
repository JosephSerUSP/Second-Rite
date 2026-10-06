#!/usr/bin/env python3
"""One-shot correction for PR #1400 collection-instance realization."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "tools/blender/second_rite_asset_core.py"

text = CORE.read_text(encoding="utf-8")
pattern = r'def _realize_export_instances\(context, objects\):.*?\n\ndef _select_export_geometry'
replacement = '''def _realize_export_instances(context, objects):
    """Realize collection-instance Empties inside the temporary export graph.

    Blender's ``duplicates_make_real`` operator was deliberately not used here:
    under the pinned Blender 5.2.2 stress fixture it produced the referenced
    geometry but lost the instance Empty's offset/scale. Runtime export needs a
    deterministic transform composition, not merely visible geometry.
    """
    bpy = _bpy()
    from mathutils import Matrix

    instancers = [
        obj for obj in objects
        if not obj.hide_render and getattr(obj, "instance_type", "NONE") != "NONE"
    ]
    unsupported = [obj for obj in instancers if obj.instance_type != "COLLECTION"]
    if unsupported:
        details = ", ".join(f"{obj.name}:{obj.instance_type}" for obj in unsupported)
        raise RuntimeError(
            "item export currently guarantees COLLECTION instances only; "
            f"unsupported instance carriers: {details}"
        )

    realized = []
    for instancer in instancers:
        source_collection = instancer.instance_collection
        if source_collection is None:
            raise RuntimeError(f"{instancer.name} has COLLECTION instance type without a collection")
        nested = [
            obj for obj in source_collection.all_objects
            if getattr(obj, "instance_type", "NONE") != "NONE"
        ]
        if nested:
            details = ", ".join(f"{obj.name}:{obj.instance_type}" for obj in nested)
            raise RuntimeError(
                f"nested instances inside collection {source_collection.name} are not yet guaranteed: {details}"
            )

        target_collection = next(
            (collection for collection in instancer.users_collection
             if collection.name == "__SECOND_RITE_ITEM_EXPORT_TEMP__"),
            None,
        )
        if target_collection is None:
            raise RuntimeError(f"scratch instance {instancer.name} is not in the item export temp collection")

        sources = list(source_collection.all_objects)
        mapping = {}
        for source in sources:
            duplicate = source.copy()
            if source.data is not None:
                duplicate.data = source.data.copy()
            duplicate.animation_data_clear()
            target_collection.objects.link(duplicate)
            mapping[source] = duplicate

        # Collection instances are evaluated as the instance carrier transform,
        # then the collection's negative instance offset, then each source
        # object's collection-space world matrix.
        instance_matrix = (
            instancer.matrix_world
            @ Matrix.Translation(-source_collection.instance_offset)
        )
        for source, duplicate in mapping.items():
            duplicate.parent = mapping.get(source.parent)
            duplicate.matrix_parent_inverse = source.matrix_parent_inverse.copy()
            duplicate.matrix_world = instance_matrix @ source.matrix_world

        _remap_duplicate_dependencies(mapping)
        realized.extend(mapping.values())

    return realized


def _select_export_geometry'''
updated, count = re.subn(pattern, replacement, text, count=1, flags=re.S)
if count != 1:
    raise SystemExit(f"instance realization hotfix expected one replacement, got {count}")

# Authoring scripts and Blender UI edits can leave child matrix_world values
# pending until the next dependency-graph evaluation. Snapshotting a hierarchy
# for export must therefore synchronize explicitly rather than relying on an
# earlier redraw/save/open cycle to have happened.
needle = '''def duplicate_hierarchy(context, root, collection_name="__SECOND_RITE_ITEM_EXPORT_TEMP__"):
    bpy = _bpy()
    from mathutils import Matrix
'''
replacement_sync = '''def duplicate_hierarchy(context, root, collection_name="__SECOND_RITE_ITEM_EXPORT_TEMP__"):
    bpy = _bpy()
    from mathutils import Matrix
    context.view_layer.update()
'''
if updated.count(needle) != 1:
    raise SystemExit("duplicate_hierarchy synchronization insertion point drifted")
updated = updated.replace(needle, replacement_sync, 1)

CORE.write_text(updated, encoding="utf-8")
print("PR1400 INSTANCE REALIZATION HOTFIX PATCHED")
