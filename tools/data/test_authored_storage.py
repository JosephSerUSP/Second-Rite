#!/usr/bin/env python3
"""Conformance tests for the repository-tool authored-storage adapter.

These tests exist because authored storage is consumed in three implementation
languages. Python must not infer a different authority from the same Project
layout, and its compound version token must remain byte-identical to Studio's
physical JavaScript storage layer.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TOOLS_DATA = ROOT / "tools" / "data"
if str(TOOLS_DATA) not in sys.path:
    sys.path.insert(0, str(TOOLS_DATA))

import authored_storage as storage  # noqa: E402


NODE_STORAGE = ROOT / "tools" / "editor" / "authored-storage-physical.js"
DATA = ROOT / "data"


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def node_version_token(root: Path, stem: str, spec: dict[str, object]) -> str:
    with tempfile.TemporaryDirectory(prefix="thestra-storage-node-") as tmp:
        script = Path(tmp) / "version-token.js"
        script.write_text(
            "const storage = require(process.argv[2]);\n"
            "const root = process.argv[3];\n"
            "const stem = process.argv[4];\n"
            "const spec = JSON.parse(process.argv[5]);\n"
            "process.stdout.write(storage.versionToken(root, stem, spec));\n",
            encoding="utf-8",
        )
        result = subprocess.run(
            [
                "node",
                str(script),
                str(NODE_STORAGE),
                str(root),
                stem,
                json.dumps(spec, separators=(",", ":")),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()


def test_manifest_authority() -> None:
    manifest = storage.load_manifest()
    assert storage.resource_spec("scenes", manifest)["representation"] == "fragments"
    assert storage.resource_spec("maps", manifest)["kind"] == "ordered_collection"
    assert storage.resource_spec("tilesets", manifest)["kind"] == "keyed_registry"
    assert storage.resource_spec("items", manifest)["representation"] == "monolith"
    assert "scenes" in storage.bulk_editable_resources(manifest)
    assert "tilesets" not in storage.bulk_editable_resources(manifest)


def test_declared_representation_wins() -> None:
    with tempfile.TemporaryDirectory(prefix="thestra-storage-python-") as tmp:
        root = Path(tmp)
        monolith = {"kind": "document", "representation": "monolith"}
        ordered = {"kind": "ordered_collection", "representation": "fragments"}

        write_json(root / "system.json", {"title": "Monolith authority"})
        write_json(root / "system" / "ignored.json", {"title": "Not authority"})
        value, representation = storage.load_resource(root, "system", monolith)
        assert representation == "monolith"
        assert value == {"title": "Monolith authority"}
        assert storage.authoritative_files(root, "system", monolith) == [root / "system.json"]

        write_json(root / "scenes" / "index.json", {"files": ["one.json"]})
        write_json(root / "scenes" / "one.json", {"id": "one", "name": "One"})
        value, representation = storage.load_resource(root, "scenes", ordered)
        assert representation == "fragments"
        assert [entry["id"] for entry in value] == ["one"]

        write_json(root / "scenes.json", [{"id": "legacy"}])
        try:
            storage.load_resource(root, "scenes", ordered)
        except ValueError as exc:
            assert "both fragment storage and legacy monolith" in str(exc)
        else:
            raise AssertionError("fragment-backed resource accepted a legacy monolith")


def test_order_registry_and_semantic_config() -> None:
    with tempfile.TemporaryDirectory(prefix="thestra-storage-python-") as tmp:
        root = Path(tmp)
        ordered = {"kind": "ordered_collection", "representation": "fragments"}
        registry = {"kind": "keyed_registry", "representation": "fragments"}
        semantic = {
            "kind": "semantic_config",
            "representation": "fragments",
            "modules": ["battle", "quest"],
        }

        write_json(root / "units" / "index.json", {"files": ["b.json", "a.json"]})
        write_json(root / "units" / "a.json", {"id": "a"})
        write_json(root / "units" / "b.json", {"id": "b"})
        units, representation = storage.load_ordered_collection(root, "units", ordered)
        assert representation == "fragments"
        assert [unit["id"] for unit in units] == ["b", "a"]

        write_json(root / "tilesets" / "wrong-name.json", {"id": "alpha", "name": "A"})
        write_json(root / "tilesets" / "beta.json", {"id": "beta", "name": "B"})
        tilesets, representation = storage.load_registry(root, "tilesets", registry)
        assert representation == "fragments"
        assert set(tilesets) == {"alpha", "beta"}

        write_json(root / "flows" / "battle.json", {"round_start": []})
        write_json(root / "flows" / "quest.json", {"offer": []})
        flows, representation = storage.load_resource(root, "flows", semantic)
        assert representation == "fragments"
        assert flows == {"battle": {"round_start": []}, "quest": {"offer": []}}

        write_json(root / "flows" / "undeclared.json", {})
        try:
            storage.authoritative_files(root, "flows", semantic)
        except ValueError as exc:
            assert "undeclared module" in str(exc)
        else:
            raise AssertionError("semantic config accepted an undeclared JSON module")


def test_fragment_filename_algorithm() -> None:
    records = {
        "alpha": {"id": "alpha"},
        "boss room": {"id": "boss room"},
        "Index": {"id": "Index"},
    }
    names = storage.registry_fragment_names(records)
    assert names["alpha"] == "alpha.json"
    assert names["boss room"] == "boss-room--626f737320726f6f6d.json"
    assert names["Index"] == "index--496e646578.json"


def test_compound_version_token_matches_node() -> None:
    with tempfile.TemporaryDirectory(prefix="thestra-storage-token-") as tmp:
        root = Path(tmp)
        ordered = {"kind": "ordered_collection", "representation": "fragments"}
        registry = {"kind": "keyed_registry", "representation": "fragments"}
        monolith = {"kind": "document", "representation": "monolith"}

        write_json(root / "scenes" / "index.json", {"files": ["one.json", "two.json"]})
        write_json(root / "scenes" / "one.json", {"id": "one", "name": "Å"})
        write_json(root / "scenes" / "two.json", {"id": "two", "name": "Two"})
        assert storage.version_token(root, "scenes", ordered) == node_version_token(
            root, "scenes", ordered
        )

        # A keyed registry has no authored ordering, so every implementation
        # must impose the same locale-independent physical ordering before it
        # hashes source paths. These names deliberately cross ASCII/Unicode
        # collation boundaries that localeCompare() and Windows Path sorting
        # can otherwise order differently.
        write_json(root / "tilesets" / "z.json", {"id": "z"})
        write_json(root / "tilesets" / "A.json", {"id": "A"})
        write_json(root / "tilesets" / "é.json", {"id": "accent"})
        write_json(root / "tilesets" / "Ω.json", {"id": "omega"})
        assert storage.version_token(root, "tilesets", registry) == node_version_token(
            root, "tilesets", registry
        )

        write_json(root / "system.json", {"title": "Fixture", "unicode": "テスト"})
        assert storage.version_token(root, "system", monolith) == node_version_token(
            root, "system", monolith
        )


def test_current_project_storage_is_readable() -> None:
    items, item_storage = storage.load_resource(DATA, "items")
    units, unit_storage = storage.load_ordered_collection(DATA, "units")
    assert item_storage == "monolith" and isinstance(items, list) and items
    assert unit_storage == "fragments" and isinstance(units, list) and units
    assert (DATA / "items.json") in storage.authoritative_files(DATA, "items")
    unit_sources = storage.authoritative_files(DATA, "units")
    assert unit_sources[0] == DATA / "units" / "index.json"
    assert len(unit_sources) == len(units) + 1


def main() -> int:
    tests = [
        test_manifest_authority,
        test_declared_representation_wins,
        test_order_registry_and_semantic_config,
        test_fragment_filename_algorithm,
        test_compound_version_token_matches_node,
        test_current_project_storage_is_readable,
    ]
    for test in tests:
        test()
    print(f"authored-storage python conformance: OK ({len(tests)} tests)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
