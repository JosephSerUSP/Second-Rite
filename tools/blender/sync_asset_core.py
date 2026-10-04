#!/usr/bin/env python3
"""Synchronize canonical Blender contract sources into the portable toolkit."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CANONICAL = {
    "second_rite_asset_core.py": ROOT / "tools" / "blender" / "second_rite_asset_core.py",
    "contract.json": ROOT / "tools" / "asset-language" / "contract.json",
    "materials.json": ROOT / "tools" / "asset-language" / "materials.json",
}
TOOLKIT = ROOT / "tools" / "blender" / "second-rite-item-model-toolkit"
VENDOR = TOOLKIT / "vendor"


def expected_pairs(canonical=None, vendor=None):
    canonical = CANONICAL if canonical is None else canonical
    vendor = VENDOR if vendor is None else Path(vendor)
    return [(Path(source), vendor / name) for name, source in canonical.items()]


def check_pairs(pairs):
    mismatches = []
    for source, target in pairs:
        if not source.is_file():
            mismatches.append(f"missing canonical file: {source}")
        elif not target.is_file():
            mismatches.append(f"missing vendor file: {target}")
        elif source.read_bytes() != target.read_bytes():
            mismatches.append(f"vendor differs: {target}")
    return mismatches


def sync_pairs(pairs):
    pairs = list(pairs)
    for source, target in pairs:
        if not source.is_file():
            raise SystemExit(f"missing canonical file: {source}")
    pairs[0][1].parent.mkdir(parents=True, exist_ok=True)
    for source, target in pairs:
        shutil.copyfile(source, target)


def refresh_integrity(toolkit=TOOLKIT, targets=None):
    """Re-record the vendored files' bytes and hashes in the toolkit's manifests.

    The toolkit ships an integrity manifest (TOOLCHAIN_MANIFEST.json) and a
    SHA256SUMS.txt; a synced vendor file that is not re-recorded there fails
    test_asset_core_host. Only vendor/ entries are rewritten.
    """
    toolkit = Path(toolkit)
    targets = [Path(t) for t in (targets or [target for _, target in expected_pairs()])]
    records = {t.relative_to(toolkit).as_posix(): t.read_bytes() for t in targets}
    manifest_path = toolkit / "TOOLCHAIN_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for entry in manifest["files"]:
        if entry["path"] in records:
            data = records[entry["path"]]
            entry["bytes"] = len(data)
            entry["sha256"] = hashlib.sha256(data).hexdigest()
    newline = "\n"
    manifest_path.write_text(json.dumps(manifest, indent=2) + newline, encoding="utf-8", newline=newline)
    sums_path = toolkit / "SHA256SUMS.txt"
    lines = []
    for line in sums_path.read_text(encoding="utf-8").splitlines():
        parts = line.split(maxsplit=1)
        if len(parts) == 2:
            key = parts[1].lstrip("*").replace("\\", "/")
            if key in records:
                line = f"{hashlib.sha256(records[key]).hexdigest()}  {parts[1]}"
        lines.append(line)
    sums_path.write_text(newline.join(lines) + newline, encoding="utf-8", newline=newline)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="check byte parity without writing")
    args = parser.parse_args(argv)
    pairs = expected_pairs()
    mismatches = check_pairs(pairs)
    if args.check:
        if mismatches:
            for mismatch in mismatches:
                print(mismatch)
            return 1
        print("vendor synchronization: passed")
        return 0
    sync_pairs(pairs)
    refresh_integrity()
    print("synchronized: " + ", ".join(target.name for _, target in pairs)
          + "; toolkit integrity manifest refreshed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
