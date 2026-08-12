#!/usr/bin/env python3
"""Isolated Craft-space adapter, determinism, and generated-output drift tests."""

from __future__ import annotations

import pathlib
import tempfile

import build


ROOT = pathlib.Path(__file__).resolve().parents[2]


def authored_json_snapshot() -> dict[pathlib.Path, bytes]:
    return {
        path: path.read_bytes()
        for path in (ROOT / "data").rglob("*.json")
    }


def main() -> int:
    before = authored_json_snapshot()
    current_items, current_units, _ = build.load_current_storage()

    with tempfile.TemporaryDirectory(prefix="second-rite-craft-space-") as directory:
        root = pathlib.Path(directory)
        first_path = root / "first.html"
        second_path = root / "second.html"

        first_payload = build.build_payload()
        assert [item["id"] for item in first_payload["items"]] == [
            item["id"] for item in current_items
        ], "exported Item IDs drifted from current canonical Items"
        assert [unit["id"] for unit in first_payload["units"]] == [
            unit["id"] for unit in current_units
        ], "exported Unit IDs drifted from current ordered fragments"
        assert all(isinstance(unit["id"], str) and unit["id"] for unit in first_payload["units"])
        assert all("craft" in item and "disciplines" in item["craft"]
                   for item in first_payload["items"])
        assert all("craft" in unit and "reach" in unit["craft"]
                   for unit in first_payload["units"])
        assert first_payload["provenance"]["itemCount"] == len(current_items)
        assert first_payload["provenance"]["unitCount"] == len(current_units)

        build.render(first_payload, first_path)
        second_payload = build.build_payload()
        build.render(second_payload, second_path)
        assert first_payload == second_payload, "two current builds are not semantically deterministic"
        assert build.extract_payload(first_path.read_text(encoding="utf-8")) == first_payload
        assert build.extract_payload(second_path.read_text(encoding="utf-8")) == second_payload

        stale_html = first_path.read_text(encoding="utf-8")
        fingerprint = first_payload["provenance"]["dataFingerprint"]
        stale_html = stale_html.replace(fingerprint, "0" * len(fingerprint), 1)
        first_path.write_text(stale_html, encoding="utf-8")
        try:
            build.check(first_path)
        except RuntimeError as exc:
            assert "stale" in str(exc), f"wrong stale-output failure: {exc}"
        else:
            raise AssertionError("intentionally stale generated payload was accepted")

    after = authored_json_snapshot()
    assert before == after, "Craft-space adapter test modified production authored JSON"
    print("CRAFT SPACE BUILD TEST OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
