"""Pure planning helpers for Thestra renderable-bundle -> Blender scene import.

This module deliberately has no ``bpy`` dependency so its structural contract can
be tested in ordinary Python. Blender-specific object/material creation lives in
``import_map_bundle.py``.
"""

from __future__ import annotations

import json
import math

from typing import Any, Dict, List, Mapping, Sequence, Tuple

BUNDLE_VERSION = 1


class BundleError(ValueError):
    """Raised when a renderable bundle cannot be represented safely."""


def _finite_number(value: Any, label: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise BundleError(f"{label} must be numeric")
    value = float(value)
    if not math.isfinite(value):
        raise BundleError(f"{label} must be finite")
    return value


def _flat_numbers(values: Any, stride: int, label: str) -> List[float]:
    if not isinstance(values, list):
        raise BundleError(f"{label} must be an array")
    if len(values) % stride != 0:
        raise BundleError(f"{label} length must be divisible by {stride}")
    return [_finite_number(value, f"{label}[{index}]") for index, value in enumerate(values)]


def _safe_name(value: Any, fallback: str = "unnamed") -> str:
    text = str(fallback if value is None or value == "" else value).strip()
    cleaned = []
    previous_underscore = False
    for char in text:
        keep = char.isalnum() or char in "_-."
        out = char if keep else "_"
        if out == "_" and previous_underscore:
            continue
        cleaned.append(out)
        previous_underscore = out == "_"
    result = "".join(cleaned).strip("_")
    return result or fallback


def validate_bundle(bundle: Mapping[str, Any]) -> None:
    if not isinstance(bundle, Mapping):
        raise BundleError("bundle must be an object")
    if bundle.get("version") != BUNDLE_VERSION:
        raise BundleError(
            f"renderable bundle version mismatch: expected {BUNDLE_VERSION}, got {bundle.get('version')!r}"
        )
    coordinate = bundle.get("coordinateSystem") or {}
    if coordinate.get("handedness") != "right" or coordinate.get("up") != "z":
        raise BundleError("Blender exporter expects the current right-handed Z-up bundle contract")

    material_ids = set()
    materials = bundle.get("materials") or []
    if not isinstance(materials, list):
        raise BundleError("materials must be an array")
    for index, material in enumerate(materials):
        if not isinstance(material, Mapping):
            raise BundleError(f"materials[{index}] must be an object")
        material_id = material.get("id")
        if not isinstance(material_id, str) or not material_id:
            raise BundleError(f"materials[{index}] needs a non-empty id")
        if material_id in material_ids:
            raise BundleError(f"duplicate material id: {material_id}")
        material_ids.add(material_id)

    surfaces = bundle.get("surfaces") or []
    if not isinstance(surfaces, list):
        raise BundleError("surfaces must be an array")
    for index, surface in enumerate(surfaces):
        if not isinstance(surface, Mapping):
            raise BundleError(f"surfaces[{index}] must be an object")
        positions = _flat_numbers(surface.get("positions", []), 3, f"surfaces[{index}].positions")
        vertex_count = len(positions) // 3
        if vertex_count % 3 != 0:
            raise BundleError(f"surfaces[{index}] vertex stream must contain complete triangles")
        material_id = surface.get("material")
        if material_id not in material_ids:
            raise BundleError(f"surfaces[{index}] references unknown material {material_id!r}")
        for key, stride in (("uvs", 2), ("normals", 3), ("colors", 4)):
            values = _flat_numbers(surface.get(key, []), stride, f"surfaces[{index}].{key}")
            if values and len(values) // stride != vertex_count:
                raise BundleError(f"surfaces[{index}].{key} must match the position vertex count")


def _triples(values: Sequence[float]) -> List[Tuple[float, float, float]]:
    return [tuple(values[index:index + 3]) for index in range(0, len(values), 3)]


def _pairs(values: Sequence[float]) -> List[Tuple[float, float]]:
    return [tuple(values[index:index + 2]) for index in range(0, len(values), 2)]


def _quads(values: Sequence[float]) -> List[Tuple[float, float, float, float]]:
    return [tuple(values[index:index + 4]) for index in range(0, len(values), 4)]


def _scalar_source_properties(source: Mapping[str, Any]) -> Dict[str, Any]:
    props: Dict[str, Any] = {}
    for key, value in source.items():
        if value is None or isinstance(value, (str, bool, int, float)):
            props[f"thestra_source_{_safe_name(key)}"] = value
    return props


def surface_plan(surface: Mapping[str, Any], index: int) -> Dict[str, Any]:
    positions = _flat_numbers(surface.get("positions", []), 3, f"surface[{index}].positions")
    uvs = _flat_numbers(surface.get("uvs", []), 2, f"surface[{index}].uvs")
    normals = _flat_numbers(surface.get("normals", []), 3, f"surface[{index}].normals")
    colors = _flat_numbers(surface.get("colors", []), 4, f"surface[{index}].colors")
    vertex_count = len(positions) // 3
    source = surface.get("source") if isinstance(surface.get("source"), Mapping) else {}
    source_kind = _safe_name(source.get("kind"), "unclassified")
    surface_id = str(surface.get("id") or f"surface_{index:04d}")
    name = _safe_name(surface.get("name") or surface_id, f"surface_{index:04d}")

    properties: Dict[str, Any] = {
        "thestra_surface_id": surface_id,
        "thestra_material_id": str(surface.get("material") or ""),
        "thestra_source_kind": source_kind,
        "thestra_source_json": json.dumps(source, sort_keys=True, separators=(",", ":")),
    }
    properties.update(_scalar_source_properties(source))
    source_json = properties["thestra_source_json"]
    entity_name = name
    if source_kind == "event" and source.get("id") is not None:
        entity_name = f"event_{_safe_name(source.get('id'))}"
    elif source_kind == "cell":
        entity_name = "cell_{}_{}_{}".format(
            _safe_name(source.get("x"), "x"),
            _safe_name(source.get("y"), "y"),
            _safe_name(source.get("surface"), "surface"),
        )

    return {
        "name": name,
        "collection": source_kind,
        "entity_key": source_kind + ":" + source_json,
        "entity_name": entity_name,
        "material": surface.get("material"),
        "vertices": _triples(positions),
        "faces": [(i, i + 1, i + 2) for i in range(0, vertex_count, 3)],
        "uvs": _pairs(uvs) if uvs else [],
        "normals": _triples(normals) if normals else [],
        "colors": _quads(colors) if colors else [],
        "properties": properties,
    }


def build_scene_plan(bundle: Mapping[str, Any]) -> Dict[str, Any]:
    validate_bundle(bundle)
    map_info = bundle.get("map") if isinstance(bundle.get("map"), Mapping) else {}
    surfaces = bundle.get("surfaces") or []
    materials = bundle.get("materials") or []
    objects = [surface_plan(surface, index) for index, surface in enumerate(surfaces)]
    collection_names = sorted({obj["collection"] for obj in objects})
    return {
        "version": BUNDLE_VERSION,
        "map": dict(map_info),
        "root_collection": "Thestra_Map_" + _safe_name(map_info.get("id"), "runtime"),
        "collections": collection_names,
        "materials": [dict(material) for material in materials],
        "objects": objects,
        "stats": {
            "object_count": len(objects),
            "triangle_count": sum(len(obj["faces"]) for obj in objects),
            "vertex_count": sum(len(obj["vertices"]) for obj in objects),
        },
    }
