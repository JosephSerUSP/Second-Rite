#!/usr/bin/env python3
"""Build the standalone Craft-space analysis page from current engine data.

The authoritative analysis facts come from ``engine.craft`` through the
``lovec . craft-space-export`` read-only CLI mode. This script owns only the
HTML projection, provenance, deterministic serialization, and drift check.

Examples::

    python tools/craft-space/build.py
    python tools/craft-space/build.py --check
    python tools/craft-space/build.py --output path/to/fixture.html
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import subprocess
import sys
from typing import Any


HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
DATA = ROOT / "data"
TEMPLATE = HERE / "template.html"
MARKER = "/*__DATA__*/{}"
EXPORT_BEGIN = "CRAFT_SPACE_EXPORT_BEGIN\n"
EXPORT_END = "\nCRAFT_SPACE_EXPORT_END"


def read_json(path: pathlib.Path) -> Any:
    if not path.is_file():
        raise RuntimeError(f"required Craft-space source is missing: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"invalid JSON in Craft-space source {path}: {exc}") from exc


def load_current_storage() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[pathlib.Path]]:
    """Read the current monolith/ordered-fragment storage contract.

    This deliberately mirrors the repository's authored-storage boundary for
    the two resources Craft-space needs. It never consults or creates the
    retired ``data/actors.json`` representation.
    """

    manifest = read_json(DATA / "authored_storage_manifest.json")
    resources = manifest.get("resources", {})
    items_spec = resources.get("items")
    units_spec = resources.get("units")
    if items_spec != {"kind": "document", "representation": "monolith", "bulkEditable": True}:
        raise RuntimeError("Craft-space requires the current monolithic items storage contract")
    if units_spec != {"kind": "ordered_collection", "representation": "fragments", "bulkEditable": True}:
        raise RuntimeError("Craft-space requires the current fragmented ordered Units storage contract")

    legacy = DATA / "actors.json"
    if legacy.exists():
        raise RuntimeError(f"retired compatibility source must not exist: {legacy}")

    items_path = DATA / "items.json"
    items = read_json(items_path)
    if not isinstance(items, list) or not items:
        raise RuntimeError("data/items.json must be a non-empty array")

    units_dir = DATA / "units"
    index_path = units_dir / "index.json"
    index = read_json(index_path)
    files = index.get("files") if isinstance(index, dict) else index
    if not isinstance(files, list) or not files:
        raise RuntimeError("data/units/index.json must contain a non-empty files array")

    seen: set[str] = set()
    units: list[dict[str, Any]] = []
    authoritative = [DATA / "authored_storage_manifest.json", items_path,
                     DATA / "elements.json", DATA / "engine.json", index_path]
    for filename in files:
        if not isinstance(filename, str) or not filename or pathlib.PurePath(filename).name != filename:
            raise RuntimeError(f"unsafe Unit fragment name in data/units/index.json: {filename!r}")
        folded = filename.casefold()
        if folded in seen:
            raise RuntimeError(f"duplicate Unit fragment in data/units/index.json: {filename}")
        seen.add(folded)
        fragment = units_dir / filename
        if not fragment.is_file():
            raise RuntimeError(f"data/units/index.json references missing fragment: {fragment}")
        unit = read_json(fragment)
        if not isinstance(unit, dict) or not isinstance(unit.get("id"), str) or not unit["id"]:
            raise RuntimeError(f"Unit fragment has no symbolic id: {fragment}")
        units.append(unit)
        authoritative.append(fragment)

    return items, units, authoritative


def data_fingerprint(paths: list[pathlib.Path]) -> str:
    hasher = hashlib.sha256()
    for path in paths:
        rel = path.relative_to(ROOT).as_posix().encode("utf-8")
        content = path.read_bytes()
        hasher.update(len(rel).to_bytes(8, "big"))
        hasher.update(rel)
        hasher.update(len(content).to_bytes(8, "big"))
        hasher.update(content)
    return hasher.hexdigest()


def source_revision() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
            text=True, check=True,
        )
        return result.stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RuntimeError("unable to determine source revision for Craft-space provenance") from exc


def love_command() -> pathlib.Path:
    configured = os.environ.get("CRAFT_SPACE_LOVE")
    path = pathlib.Path(configured) if configured else pathlib.Path(r"C:\Program Files\LOVE\lovec.exe")
    if not path.is_file():
        raise RuntimeError(f"LOVE console binary is required for the Craft-space export: {path}")
    return path


def engine_export() -> dict[str, Any]:
    result = subprocess.run(
        [str(love_command()), ".", "craft-space-export"],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if result.returncode != 0:
        output = (result.stdout + "\n" + result.stderr).strip()
        raise RuntimeError(f"engine Craft-space export failed (exit {result.returncode}):\n{output}")
    output = result.stdout
    if EXPORT_BEGIN not in output or EXPORT_END not in output:
        raise RuntimeError("engine Craft-space export did not emit its complete contract")
    encoded = output.split(EXPORT_BEGIN, 1)[1].split(EXPORT_END, 1)[0]
    try:
        contract = json.loads(encoded)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"engine Craft-space export emitted invalid JSON: {exc}") from exc
    if not isinstance(contract, dict):
        raise RuntimeError("engine Craft-space export must be an object")
    return contract


def validate_contract(contract: dict[str, Any], items: list[dict[str, Any]],
                      units: list[dict[str, Any]]) -> None:
    exported_items = contract.get("items")
    exported_units = contract.get("units")
    if not isinstance(exported_items, list) or not isinstance(exported_units, list):
        raise RuntimeError("engine Craft-space export is missing items or units")
    item_ids = [item.get("id") for item in exported_items]
    expected_item_ids = [item.get("id") for item in items]
    unit_ids = [unit.get("id") for unit in exported_units]
    expected_unit_ids = [unit.get("id") for unit in units]
    if item_ids != expected_item_ids:
        raise RuntimeError("engine Craft-space export item order/IDs differ from current data/items.json")
    if unit_ids != expected_unit_ids:
        raise RuntimeError("engine Craft-space export Unit order/IDs differ from data/units/index.json")
    if len(set(item_ids)) != len(item_ids):
        raise RuntimeError("current Items contain duplicate canonical IDs")
    if len(set(unit_ids)) != len(unit_ids):
        raise RuntimeError("current Units contain duplicate symbolic IDs")
    if any(not isinstance(item_id, int) for item_id in item_ids):
        raise RuntimeError("current Item canonical IDs must remain numeric for Craft-space")
    if any(not isinstance(unit_id, str) or not unit_id for unit_id in unit_ids):
        raise RuntimeError("current Unit canonical IDs must remain non-empty symbolic strings")

    disciplines = {entry.get("kind") for entry in contract.get("disciplines", [])}
    if not disciplines:
        raise RuntimeError("engine Craft-space export has no discipline registry")
    for item in exported_items:
        craft = item.get("craft") or {}
        # The engine's compact JSON encoder represents an empty Lua table as
        # [], while a populated element-weight map is an object. Both are the
        # same empty/non-empty map contract to the browser.
        if not isinstance(craft.get("el"), (dict, list)) or not isinstance(craft.get("disciplines"), list):
            raise RuntimeError(f"Item {item.get('id')} is missing engine-derived craft facts")
    for unit in exported_units:
        craft = unit.get("craft") or {}
        if not isinstance(craft.get("reach"), (int, float)):
            raise RuntimeError(f"Unit {unit.get('id')} is missing engine-derived craft reach")


def build_payload() -> dict[str, Any]:
    items, units, authoritative = load_current_storage()
    contract = engine_export()
    validate_contract(contract, items, units)
    revision = source_revision()
    fingerprint = data_fingerprint(authoritative)
    return {
        "schemaVersion": 2,
        "provenance": {
            "sourceRevision": revision,
            "dataFingerprint": fingerprint,
            "itemCount": len(items),
            "unitCount": len(units),
            "deterministic": True,
        },
        "items": contract["items"],
        "units": contract["units"],
        "disciplines": contract["disciplines"],
        "intensityGrades": contract["intensityGrades"],
        "craftRules": contract["craftRules"],
        "craftElementSources": contract["craftElementSources"],
        "craftLexicon": contract["craftLexicon"],
        "disciplineDefaults": contract["disciplineDefaults"],
        "elementRules": contract["elementRules"],
        "elements": contract["elements"],
    }


def render(payload: dict[str, Any], output: pathlib.Path) -> None:
    template = TEMPLATE.read_text(encoding="utf-8")
    if MARKER not in template:
        raise RuntimeError(f"template.html lost its {MARKER} marker")
    blob = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(template.replace(MARKER, "/*__DATA__*/" + blob), encoding="utf-8")


def extract_payload(html: str) -> dict[str, Any]:
    prefix = "const DATA = /*__DATA__*/"
    if prefix not in html:
        raise RuntimeError("generated Craft-space HTML has no embedded DATA payload")
    start = html.index(prefix) + len(prefix)
    depth = 0
    in_string = False
    escaped = False
    end = None
    for index in range(start, len(html)):
        char = html[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                end = index + 1
                break
    if end is None:
        raise RuntimeError("generated Craft-space DATA payload is unterminated")
    try:
        value = json.loads(html[start:end])
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"generated Craft-space DATA payload is invalid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise RuntimeError("generated Craft-space DATA payload must be an object")
    return value


def check(output: pathlib.Path) -> None:
    if not output.is_file():
        raise RuntimeError(f"generated Craft-space output is missing: {output}")
    expected = build_payload()
    actual = extract_payload(output.read_text(encoding="utf-8"))
    comparable = json.loads(json.dumps(actual))
    # A generated page is a projection of canonical data. Committing the page
    # itself necessarily advances HEAD, so the informational source revision
    # may differ after the build commit; the data fingerprint and semantic
    # payload remain the drift contract.
    comparable.setdefault("provenance", {})["sourceRevision"] = expected["provenance"]["sourceRevision"]
    if comparable != expected:
        actual_prov = actual.get("provenance", {})
        expected_prov = expected["provenance"]
        raise RuntimeError(
            "generated Craft-space output is stale or semantically different "
            f"(actual revision/fingerprint {actual_prov.get('sourceRevision')}/"
            f"{actual_prov.get('dataFingerprint')}, expected "
            f"{expected_prov['sourceRevision']}/{expected_prov['dataFingerprint']})"
        )
    print(f"CRAFT SPACE DRIFT OK ({expected['provenance']['itemCount']} items, "
          f"{expected['provenance']['unitCount']} units)")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail if generated output is stale")
    parser.add_argument("--output", type=pathlib.Path, default=HERE / "craft-space.html")
    args = parser.parse_args(argv)
    output = args.output if args.output.is_absolute() else ROOT / args.output
    try:
        if args.check:
            check(output)
        else:
            payload = build_payload()
            render(payload, output)
            print(f"wrote {output.relative_to(ROOT) if output.is_relative_to(ROOT) else output} "
                  f"({output.stat().st_size // 1024} KB)")
            print(f"  {len(payload['items'])} items, {len(payload['units'])} units")
            print(f"  source revision: {payload['provenance']['sourceRevision']}")
            print(f"  data fingerprint: {payload['provenance']['dataFingerprint']}")
    except RuntimeError as exc:
        print(f"CRAFT SPACE BUILD FAIL: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
