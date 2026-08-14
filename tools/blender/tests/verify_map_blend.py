"""Headless structural verification for a saved Thestra map .blend.

Run through Blender, not ordinary Python::

    blender --background --factory-startup --python verify_map_blend.py -- \
        exports/maps/ci-map8.blend 8

This intentionally checks portable authoring structure rather than rendered pixels.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import bpy


def _args():
    if "--" not in sys.argv:
        return []
    return sys.argv[sys.argv.index("--") + 1:]


def _fail(message: str) -> None:
    raise RuntimeError("structured .blend verification failed: " + message)


def _is_identity_transform(obj) -> bool:
    eps = 1e-8
    return (
        all(abs(value) <= eps for value in obj.location)
        and all(abs(value) <= eps for value in obj.rotation_euler)
        and all(abs(value - 1.0) <= eps for value in obj.scale)
    )


def verify(path: Path, expected_map_id: str) -> dict:
    if not path.is_file():
        _fail(f"missing .blend file: {path}")

    bpy.ops.wm.open_mainfile(filepath=str(path.resolve()))

    root_name = f"Thestra_Map_{expected_map_id}"
    root = bpy.data.collections.get(root_name)
    if root is None:
        _fail(f"missing root collection {root_name!r}")
    if str(root.get("thestra_map_id", "")) != expected_map_id:
        _fail("root collection map identity does not match requested map")
    if int(root.get("thestra_bundle_version", 0)) != 1:
        _fail("unexpected/missing renderable bundle version metadata")

    meshes = [
        obj for obj in bpy.data.objects
        if obj.type == "MESH" and obj.get("thestra_surface_id")
    ]
    if not meshes:
        _fail("no authoritative surface mesh objects were created")

    expected_object_count = int(root.get("thestra_object_count", 0))
    if expected_object_count != len(meshes):
        _fail(
            f"root object count says {expected_object_count}, but file contains {len(meshes)} surfaces"
        )

    triangle_count = sum(len(obj.data.polygons) for obj in meshes)
    expected_triangles = int(root.get("thestra_triangle_count", 0))
    if expected_triangles != triangle_count or triangle_count <= 0:
        _fail(
            f"triangle count mismatch: metadata={expected_triangles}, actual={triangle_count}"
        )

    source_kinds = set()
    entity_parents = set()
    material_ids = set()
    for obj in meshes:
        if not _is_identity_transform(obj):
            _fail(f"surface {obj.name!r} unexpectedly uses object transforms")
        parent = obj.parent
        if parent is None or parent.type != "EMPTY":
            _fail(f"surface {obj.name!r} has no semantic source parent empty")
        if not _is_identity_transform(parent):
            _fail(f"semantic parent {parent.name!r} unexpectedly uses transforms")

        source_kind = str(obj.get("thestra_source_kind", ""))
        if not source_kind:
            _fail(f"surface {obj.name!r} has no source-kind provenance")
        if str(parent.get("thestra_source_kind", "")) != source_kind:
            _fail(f"surface {obj.name!r} and its parent disagree on source kind")
        source_kinds.add(source_kind)
        entity_parents.add(parent.name)

        source_json = obj.get("thestra_source_json")
        if not isinstance(source_json, str):
            _fail(f"surface {obj.name!r} has no serialized source provenance")
        try:
            source = json.loads(source_json)
        except Exception as exc:  # Blender reports this cleanly in Actions output.
            _fail(f"surface {obj.name!r} has invalid source JSON: {exc}")
        if str(source.get("kind", "")) != source_kind:
            _fail(f"surface {obj.name!r} source JSON disagrees with source kind")

        if "Thestra UV" not in obj.data.uv_layers:
            _fail(f"surface {obj.name!r} lost authored UVs")
        light = obj.data.color_attributes.get("Thestra Light")
        if light is None or light.domain != "CORNER":
            _fail(f"surface {obj.name!r} has no corner Thestra Light color attribute")
        if len(light.data) != len(obj.data.loops):
            _fail(f"surface {obj.name!r} light colors do not match mesh loops")

        material_id = str(obj.get("thestra_material_id", ""))
        if not material_id:
            _fail(f"surface {obj.name!r} lost material identity")
        if not obj.material_slots or obj.material_slots[0].material is None:
            _fail(f"surface {obj.name!r} has no Blender material")
        material = obj.material_slots[0].material
        if str(material.get("thestra_material_id", "")) != material_id:
            _fail(f"surface {obj.name!r} material metadata disagrees with its source material")
        material_ids.add(material_id)

    provenance_children = {
        child.name for child in root.children
        if child.name.startswith("Thestra_")
    }
    for source_kind in source_kinds:
        expected = "Thestra_" + source_kind
        if expected not in provenance_children:
            _fail(f"missing provenance collection {expected!r}")

    images = set()
    for material in bpy.data.materials:
        if not material.get("thestra_material_id") or not material.use_nodes:
            continue
        material_json = material.get("thestra_material_json")
        if not isinstance(material_json, str):
            _fail(f"material {material.name!r} has no portable source metadata")
        try:
            json.loads(material_json)
        except Exception as exc:
            _fail(f"material {material.name!r} has invalid source metadata: {exc}")
        for node in material.node_tree.nodes:
            if node.type == "TEX_IMAGE" and node.image is not None:
                images.add(node.image)

    if not images:
        _fail("representative Map 8 export contains no material images")
    unpacked = []
    for image in images:
        packed_file = getattr(image, "packed_file", None)
        packed_files = getattr(image, "packed_files", None)
        if packed_file is None and not packed_files:
            unpacked.append(image.name)
    if unpacked:
        _fail("material images are not packed: " + ", ".join(sorted(unpacked)))

    return {
        "map_id": expected_map_id,
        "map_name": str(root.get("thestra_map_name", "")),
        "surface_objects": len(meshes),
        "semantic_parents": len(entity_parents),
        "triangles": triangle_count,
        "materials": len(material_ids),
        "packed_images": len(images),
        "source_kinds": sorted(source_kinds),
    }


def main() -> None:
    args = _args()
    if len(args) != 2:
        raise SystemExit(
            "usage: blender --background --python verify_map_blend.py -- <file.blend> <map-id>"
        )
    summary = verify(Path(args[0]), str(args[1]))
    print("THESTRA BLEND SMOKE OK " + json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
