"""Inspect and validate the Blender scene contract used by town exporters.

The validator is deliberately read-only.  Role assignment comes only from
explicit collection membership; object names are labels and are never used to
decide whether an object is source, render, collision, or an anchor.

The module has two entry points:

* :func:`inspect_snapshot` is Blender-independent and is the stable contract
  used by tests and a future Blender panel.
* When executed inside Blender, ``blender -b scene.blend --python
  scene_contract.py -- --output report.json`` serializes the current file and
  validates it without saving or changing the source scene.

For a plain Python process, ``--snapshot`` validates a previously serialized
scene snapshot.  The report format is versioned and intentionally contains
diagnostics rather than only a boolean so authoring tools can surface the
specific object and role that needs attention.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Mapping


REPORT_SCHEMA = "thestra.scene-contract-report"
REPORT_SCHEMA_VERSION = 1
CONTRACT_VERSION = 0

# Required roles are intentionally small.  Collision remains optional on the
# current main branch and its presence does not make a scene walkable.
ROLE_SPECS = {
    "TH_SOURCE": {"required": True, "types": {"MESH", "CURVE", "SURFACE", "LIGHT", "EMPTY"}},
    "TH_RENDER": {"required": True, "types": {"MESH"}},
    "TH_COLLISION": {"required": False, "types": {"MESH"}},
    "TH_ANCHORS": {"required": True, "types": {"EMPTY", "LOCATOR"}},
}
PREVIEW_SPECS = {
    "TH_PREVIEW_ACTORS": {"types": {"MESH", "EMPTY", "LOCATOR"}},
    "TH_PREVIEW_ONLY": {"types": {"MESH", "CURVE", "SURFACE", "EMPTY", "LOCATOR"}},
    "TH_CAMERA_PREVIEW": {"types": {"CAMERA"}},
}
EXPORT_ROLES = tuple(ROLE_SPECS)
PREVIEW_ROLES = tuple(PREVIEW_SPECS)
ALL_KNOWN_ROLES = EXPORT_ROLES + PREVIEW_ROLES
def _diag(severity: str, code: str, message: str, *, role: str | None = None,
          object_name: str | None = None, path: str | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "severity": severity,
        "code": code,
        "message": message,
    }
    if role is not None:
        result["role"] = role
    if object_name is not None:
        result["object"] = object_name
    if path is not None:
        result["path"] = path
    return result


def _flat_matrix(value: Any) -> list[float] | None:
    if isinstance(value, (str, bytes)) or value is None:
        return None
    try:
        rows = list(value)
    except TypeError:
        return None
    if len(rows) == 16 and all(not isinstance(item, (list, tuple)) for item in rows):
        try:
            return [float(item) for item in rows]
        except (TypeError, ValueError):
            return None
    if len(rows) == 4:
        flattened: list[float] = []
        for row in rows:
            if isinstance(row, (str, bytes)):
                return None
            try:
                cells = list(row)
            except TypeError:
                return None
            if len(cells) != 4:
                return None
            try:
                flattened.extend(float(item) for item in cells)
            except (TypeError, ValueError):
                return None
        return flattened
    return None


def _matrix_location(matrix: list[float]) -> list[float]:
    return [round(matrix[3], 6), round(matrix[7], 6), round(matrix[11], 6)]


def _matrix_is_valid(matrix: Any) -> tuple[bool, str | None, list[float] | None]:
    flat = _flat_matrix(matrix)
    if flat is None:
        return False, "missing_or_malformed_matrix", None
    if not all(math.isfinite(number) for number in flat):
        return False, "non_finite_matrix", flat
    determinant = (
        flat[0] * (flat[5] * flat[10] - flat[6] * flat[9])
        - flat[1] * (flat[4] * flat[10] - flat[6] * flat[8])
        + flat[2] * (flat[4] * flat[9] - flat[5] * flat[8])
    )
    if not math.isfinite(determinant) or abs(determinant) <= 1e-10:
        return False, "singular_basis", flat
    return True, None, flat


def _object_roles(record: Mapping[str, Any]) -> list[str]:
    memberships = record.get("collections", ())
    if isinstance(memberships, str):
        memberships = (memberships,)
    if not isinstance(memberships, (list, tuple, set)):
        return []
    return sorted({name for name in memberships if isinstance(name, str)
                   and name in ALL_KNOWN_ROLES})


def _collection_report(collection_name_set: set[str],
                       names_by_role: Mapping[str, list[str]],
                       counts_by_role: Mapping[str, Counter[str]]) -> dict[str, Any]:
    return {
        role: {
            "present": role in collection_name_set,
            "objectCount": len(names_by_role[role]),
            "types": dict(sorted(counts_by_role[role].items())),
            "required": ROLE_SPECS.get(role, {}).get("required", False),
            "exported": role in EXPORT_ROLES,
        }
        for role in ALL_KNOWN_ROLES
    }


def _malformed_report(code: str, message: str, path: str = "$", *, source: Mapping[str, Any] | None = None) -> dict[str, Any]:
    report: dict[str, Any] = {
        "schema": REPORT_SCHEMA,
        "schemaVersion": REPORT_SCHEMA_VERSION,
        "contractVersion": CONTRACT_VERSION,
        "ok": False,
        "summary": {"errorCount": 1, "warningCount": 0, "objectCount": 0},
        "semantics": {
            "roleAssignment": "explicit_collection_membership",
            "objectNames": "labels_only",
            "collision": "optional_export_only; does_not_claim_walkability",
            "sourceInspection": "read_only_no_save",
        },
        "collections": _collection_report(set(),
                                            {role: [] for role in ALL_KNOWN_ROLES},
                                            {role: Counter() for role in ALL_KNOWN_ROLES}),
        "objects": [],
        "anchors": [],
        "diagnostics": [_diag("error", code, message, path=path)],
    }
    if source:
        report["source"] = dict(source)
    return report


def inspect_snapshot(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a serialized Blender scene snapshot without importing Blender.

    A snapshot contains ``collections`` (names or records) and ``objects``.
    Each object has ``name``, ``type``, ``collections`` and ``matrix_world``.
    ``mesh`` metadata such as ``uvLayerCount`` is optional, but when present it
    is checked for render meshes.
    """
    if not isinstance(snapshot, Mapping):
        return _malformed_report("malformed_snapshot",
                                 "scene snapshot must be a JSON object",
                                 path="$")

    diagnostics: list[dict[str, Any]] = []
    collection_values = snapshot.get("collections", [])
    if not isinstance(collection_values, (list, tuple)):
        diagnostics.append(_diag("error", "malformed_collections",
                                 "collections must be a list of names or objects",
                                 path="collections"))
        collection_values = []
    collection_names: list[str] = []
    for index, value in enumerate(collection_values):
        if isinstance(value, Mapping):
            name = value.get("name")
            if not isinstance(name, str) or not name:
                diagnostics.append(_diag("error", "malformed_collection",
                                         "collection entry requires a non-empty string name",
                                         path=f"collections[{index}].name"))
                continue
        elif isinstance(value, str) and value:
            name = value
        else:
            diagnostics.append(_diag("error", "malformed_collection",
                                     "collection entry must be a non-empty string or object with a name",
                                     path=f"collections[{index}]"))
            continue
        collection_names.append(name)
    collection_name_set = set(collection_names)
    for name in sorted({n for n in collection_names if collection_names.count(n) > 1}):
        diagnostics.append(_diag("error", "duplicate_collection",
                                 f"collection name '{name}' appears more than once",
                                 role=name, path=f"collections.{name}"))

    objects = snapshot.get("objects", [])
    if not isinstance(objects, list):
        objects = []
        diagnostics.append(_diag("error", "malformed_objects", "objects must be a list",
                                 path="objects"))

    normalized_objects: list[dict[str, Any]] = []
    names_by_role: dict[str, list[str]] = {role: [] for role in ALL_KNOWN_ROLES}
    counts_by_role: dict[str, Counter[str]] = {role: Counter() for role in ALL_KNOWN_ROLES}
    for index, raw in enumerate(objects):
        if not isinstance(raw, Mapping):
            diagnostics.append(_diag("error", "malformed_object",
                                     "object entry must be an object",
                                     path=f"objects[{index}]"))
            continue
        name = str(raw.get("name", f"<object {index}>"))
        object_type = str(raw.get("type", "UNKNOWN")).upper()
        memberships = raw.get("collections", ())
        if memberships is None or not isinstance(memberships, (list, tuple, set, str)):
            diagnostics.append(_diag(
                "error", "malformed_memberships",
                f"object '{name}' collections must be a list of string names",
                object_name=name, path=f"objects[{index}].collections"))
        elif not isinstance(memberships, str):
            for membership_index, membership in enumerate(memberships):
                if not isinstance(membership, str):
                    diagnostics.append(_diag(
                        "error", "malformed_membership",
                        f"object '{name}' collection membership must be a string name",
                        object_name=name,
                        path=f"objects[{index}].collections[{membership_index}]"))
        roles = _object_roles(raw)
        normalized: dict[str, Any] = {"name": name, "type": object_type, "roles": roles}
        for role in roles:
            names_by_role[role].append(name)
            counts_by_role[role][object_type] += 1
        valid_transform, transform_error, matrix = _matrix_is_valid(raw.get("matrix_world"))
        if matrix is not None:
            normalized["worldLocation"] = _matrix_location(matrix)
        normalized_objects.append(normalized)

        export_memberships = [role for role in roles if role in EXPORT_ROLES]
        if len(export_memberships) > 1:
            diagnostics.append(_diag(
                "error", "ambiguous_role",
                f"object '{name}' belongs to multiple export roles: {', '.join(export_memberships)}; "
                "link it to exactly one role collection",
                object_name=name, path=f"objects[{index}].collections"))
        if not roles:
            diagnostics.append(_diag(
                "warning", "unassigned_object",
                f"object '{name}' is not in a known scene-contract collection and will not be exported",
                object_name=name, path=f"objects[{index}].collections"))
        if not valid_transform and roles:
            diagnostics.append(_diag(
                "error", "invalid_transform",
                f"object '{name}' has an invalid world transform ({transform_error})",
                object_name=name, path=f"objects[{index}].matrix_world"))

        unsupported_roles = []
        for role in roles:
            spec = ROLE_SPECS.get(role) or PREVIEW_SPECS.get(role)
            if spec and object_type not in spec["types"]:
                unsupported_roles.append(role)
                diagnostics.append(_diag(
                    "error", "unsupported_input",
                    f"object '{name}' has type {object_type}, unsupported in {role}; "
                    f"supported types: {', '.join(sorted(spec['types']))}",
                    role=role, object_name=name, path=f"objects[{index}].type"))
        if unsupported_roles:
            normalized["unsupportedRoles"] = unsupported_roles

        preview_overlap = [role for role in roles if role in PREVIEW_ROLES]
        if "TH_PREVIEW_ONLY" in preview_overlap and any(role in EXPORT_ROLES for role in roles):
            export_roles = [role for role in roles if role in EXPORT_ROLES]
            diagnostics.append(_diag(
                "error", "guide_leakage",
                f"object '{name}' is explicitly linked to TH_PREVIEW_ONLY and export role(s) "
                f"{', '.join(export_roles)}; unlink the guide from the export collection",
                object_name=name, path=f"objects[{index}].collections"))
        if any(role in {"TH_PREVIEW_ACTORS", "TH_CAMERA_PREVIEW"} for role in preview_overlap) \
                and any(role in EXPORT_ROLES for role in roles):
            diagnostics.append(_diag(
                "error", "preview_leakage",
                f"object '{name}' is linked to a preview collection and an export role; "
                "preview content must remain isolated",
                object_name=name, path=f"objects[{index}].collections"))

        if "TH_RENDER" in roles:
            mesh = raw.get("mesh")
            if isinstance(mesh, Mapping):
                uv_count = mesh.get("uvLayerCount")
                if uv_count is not None and (not isinstance(uv_count, (int, float)) or uv_count < 1):
                    diagnostics.append(_diag(
                        "error", "missing_uvs",
                        f"render mesh '{name}' has no active UV layer for the bake receiver",
                        role="TH_RENDER", object_name=name, path=f"objects[{index}].mesh.uvLayerCount"))
                for field in ("vertexCount", "polygonCount"):
                    value = mesh.get(field)
                    if value is not None and (not isinstance(value, (int, float)) or value <= 0):
                        diagnostics.append(_diag(
                            "error", "empty_mesh",
                            f"render mesh '{name}' reports non-positive {field}",
                            role="TH_RENDER", object_name=name, path=f"objects[{index}].mesh.{field}"))

    for role, spec in ROLE_SPECS.items():
        present = role in collection_name_set
        if spec["required"] and not present:
            diagnostics.append(_diag(
                "error", "missing_role",
                f"required collection {role} is missing",
                role=role, path=f"collections.{role}"))
        if present and not names_by_role[role]:
            severity = "error" if spec["required"] else "warning"
            diagnostics.append(_diag(
                severity, "empty_role",
                f"{role} contains no explicitly assigned objects",
                role=role, path=f"collections.{role}.objects"))

    # A render role must contain at least one mesh, even if it also contains an
    # unsupported object.  Collision deliberately has no equivalent required
    # check: the current contract allows it to be absent.
    if "TH_RENDER" in collection_name_set and not counts_by_role["TH_RENDER"]["MESH"]:
        diagnostics.append(_diag(
            "error", "missing_render_mesh",
            "TH_RENDER must contain at least one MESH object",
            role="TH_RENDER", path="collections.TH_RENDER.objects"))
    if "TH_SOURCE" in collection_name_set and not any(
            counts_by_role["TH_SOURCE"][object_type]
            for object_type in ("MESH", "CURVE", "SURFACE")):
        diagnostics.append(_diag(
            "error", "missing_source_geometry",
            "TH_SOURCE must contain at least one bakeable geometry object (MESH, CURVE, or SURFACE); "
            "lights alone cannot provide selected-to-active bake sources",
            role="TH_SOURCE", path="collections.TH_SOURCE.objects"))
    if "TH_ANCHORS" in collection_name_set:
        anchor_names = names_by_role["TH_ANCHORS"]
        for name in sorted({n for n in anchor_names if anchor_names.count(n) > 1}):
            diagnostics.append(_diag(
                "error", "ambiguous_anchor",
                f"anchor label '{name}' resolves to multiple objects in TH_ANCHORS",
                role="TH_ANCHORS", object_name=name, path="collections.TH_ANCHORS.objects"))

    diagnostics.sort(key=lambda item: (
        0 if item["severity"] == "error" else 1,
        item.get("path", ""), item["code"], item.get("object", ""), item["message"]))
    error_count = sum(item["severity"] == "error" for item in diagnostics)
    warning_count = sum(item["severity"] == "warning" for item in diagnostics)
    collection_report = _collection_report(collection_name_set, names_by_role, counts_by_role)

    return {
        "schema": REPORT_SCHEMA,
        "schemaVersion": REPORT_SCHEMA_VERSION,
        "contractVersion": CONTRACT_VERSION,
        "ok": error_count == 0,
        "summary": {"errorCount": error_count, "warningCount": warning_count,
                     "objectCount": len(normalized_objects)},
        "semantics": {
            "roleAssignment": "explicit_collection_membership",
            "objectNames": "labels_only",
            "collision": "optional_export_only; does_not_claim_walkability",
            "sourceInspection": "read_only_no_save",
        },
        "collections": collection_report,
        "objects": normalized_objects,
        "anchors": [item for item in normalized_objects if "TH_ANCHORS" in item["roles"]],
        "diagnostics": diagnostics,
    }


def _snapshot_from_blender() -> dict[str, Any]:
    """Serialize the currently opened Blender file without mutating it."""
    import bpy  # type: ignore

    collections = sorted(bpy.data.collections, key=lambda collection: collection.name)
    membership: dict[str, set[str]] = {obj.name: set() for obj in bpy.data.objects}
    for collection in collections:
        for obj in collection.all_objects:
            membership.setdefault(obj.name, set()).add(collection.name)

    objects: list[dict[str, Any]] = []
    for obj in sorted(bpy.data.objects, key=lambda value: (value.name, value.type)):
        matrix = [[float(obj.matrix_world[row][column]) for column in range(4)]
                  for row in range(4)]
        record: dict[str, Any] = {
            "name": obj.name,
            "type": obj.type,
            "collections": sorted(membership.get(obj.name, set())),
            "matrix_world": matrix,
        }
        if obj.type == "MESH":
            record["mesh"] = {
                "vertexCount": len(obj.data.vertices),
                "polygonCount": len(obj.data.polygons),
                "uvLayerCount": len(obj.data.uv_layers),
            }
        objects.append(record)
    return {"collections": [{"name": collection.name} for collection in collections],
            "objects": objects,
            "source": {"blendPath": bpy.data.filepath}}


def _write_report(report: Mapping[str, Any], output: Path | None, pretty: bool) -> None:
    text = json.dumps(report, indent=2 if pretty else None, sort_keys=pretty) + "\n"
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


def _inside_blender() -> bool:
    try:
        import bpy  # noqa: F401  # type: ignore
        return True
    except ImportError:
        return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blend", type=Path,
                        help="open this .blend in Blender and validate it read-only")
    parser.add_argument("--snapshot", type=Path,
                        help="validate a JSON snapshot in a plain Python process")
    parser.add_argument("--output", type=Path,
                        help="write the versioned report to this JSON file")
    parser.add_argument("--pretty", action="store_true", help="indent JSON output")
    parser.add_argument("--strict", action="store_true",
                        help="exit non-zero when validation reports an error")
    args = parser.parse_args(argv)

    if args.blend and args.snapshot:
        parser.error("--blend and --snapshot are mutually exclusive")
    if args.blend:
        if _inside_blender():
            parser.error("--blend is only an external-process option")
        blend_path = args.blend.resolve()
        if not blend_path.is_file():
            parser.error(f"blend file does not exist: {blend_path}")
        blender = os.environ.get("BLENDER") or shutil.which("blender")
        if not blender:
            parser.error("Blender not found; set BLENDER or put blender on PATH")
        command = [blender, "--background", str(blend_path), "--python-exit-code", "1",
                   "--python", str(Path(__file__).resolve()), "--"]
        if args.output:
            command.extend(["--output", str(args.output.resolve())])
        if args.pretty:
            command.append("--pretty")
        if args.strict:
            command.append("--strict")
        return subprocess.run(command, check=False).returncode
    if args.snapshot:
        try:
            snapshot = json.loads(args.snapshot.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            report = _malformed_report(
                "malformed_snapshot_json",
                f"snapshot is not valid JSON: {error.msg}",
                path=f"{args.snapshot}:line {error.lineno}, column {error.colno}")
            _write_report(report, args.output, args.pretty)
            return 1 if args.strict else 0
    elif _inside_blender():
        snapshot = _snapshot_from_blender()
    else:
        parser.error("use --snapshot outside Blender, or run this script with Blender --python")
        return 2

    report = inspect_snapshot(snapshot)
    if isinstance(snapshot.get("source"), Mapping):
        report["source"] = dict(snapshot["source"])
    _write_report(report, args.output, args.pretty)
    if args.strict and not report["ok"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else None))
