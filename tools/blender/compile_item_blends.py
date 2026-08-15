"""Compile authoritative item ``.blend`` sources without allowing source writes.

This is the host-side entry point around ``compile_item_blend.py``. It hashes
every source before and after Blender, validates the emitted OBJ against the
runtime face contract, and can compare a temporary compile against checked-in
runtime products for CI.

Examples::

    python tools/blender/compile_item_blends.py --blender /path/to/blender
    python tools/blender/compile_item_blends.py --blender /path/to/blender --check
    python tools/blender/compile_item_blends.py --blender /path/to/blender --source assets/authoring/items/foo.blend
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parents[1]
SOURCE_DIR = ROOT / "assets" / "authoring" / "items"
MODEL_DIR = ROOT / "assets" / "models" / "items"
BLENDER_SCRIPT = SCRIPT_DIR / "compile_item_blend.py"

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
from validate_item_obj_runtime import validate


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def sources_from_args(values: list[str]) -> list[Path]:
    if values:
        sources = [Path(value).resolve() for value in values]
    elif SOURCE_DIR.is_dir():
        sources = sorted(path.resolve() for path in SOURCE_DIR.glob("*.blend"))
    else:
        sources = []
    duplicates = {path for path in sources if sources.count(path) > 1}
    if duplicates:
        raise SystemExit(f"duplicate source arguments: {sorted(map(str, duplicates))}")
    return sources


def compare_bytes(actual: Path, expected: Path):
    if not expected.is_file():
        raise RuntimeError(f"compiled product is missing from repository: {expected.relative_to(ROOT)}")
    if actual.read_bytes() != expected.read_bytes():
        raise RuntimeError(
            f"compiled product is stale: {expected.relative_to(ROOT)}; "
            "recompile the authoritative .blend and commit the runtime product"
        )


def compile_one(blender: str, source: Path, output_dir: Path, *, check: bool):
    if not source.is_file():
        raise RuntimeError(f"item source does not exist: {source}")
    before = digest(source)
    backup_candidates = [source.with_suffix(source.suffix + str(i)) for i in range(1, 10)]
    preexisting_backups = {path for path in backup_candidates if path.exists()}

    env = os.environ.copy()
    env["SECOND_RITE_ITEM_OUTPUT_DIR"] = str(output_dir)
    command = [blender, "--background", str(source), "--python", str(BLENDER_SCRIPT)]
    print("+", " ".join(command))
    subprocess.run(command, cwd=ROOT, env=env, check=True)

    after = digest(source)
    if after != before:
        raise RuntimeError(f"compiler modified source document: {source.relative_to(ROOT)}")
    new_backups = {path for path in backup_candidates if path.exists()} - preexisting_backups
    if new_backups:
        raise RuntimeError(f"compiler created Blender backup source(s): {sorted(map(str, new_backups))}")

    obj = output_dir / f"{source.stem}.obj"
    validate(obj)
    if check:
        compare_bytes(obj, MODEL_DIR / obj.name)
        mtl = output_dir / f"{source.stem}.mtl"
        canonical_mtl = MODEL_DIR / mtl.name
        if mtl.exists() or canonical_mtl.exists():
            compare_bytes(mtl, canonical_mtl)
    return obj


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blender", default=os.environ.get("BLENDER_BIN") or shutil.which("blender"))
    parser.add_argument("--source", action="append", default=[], help="compile only this .blend; repeatable")
    parser.add_argument(
        "--check",
        action="store_true",
        help="compile to a temporary directory and require products to match checked-in OBJ/MTL",
    )
    args = parser.parse_args(argv)
    if not args.blender:
        raise SystemExit("Blender executable not found; pass --blender or set BLENDER_BIN")

    sources = sources_from_args(args.source)
    if not sources:
        print(f"No authoritative item .blend sources under {SOURCE_DIR.relative_to(ROOT)}; nothing to compile.")
        return 0

    if args.check:
        with tempfile.TemporaryDirectory(prefix="second-rite-item-compile-") as temp:
            output_dir = Path(temp)
            for source in sources:
                compile_one(args.blender, source, output_dir, check=True)
    else:
        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        for source in sources:
            compile_one(args.blender, source, MODEL_DIR, check=False)

    print(f"ITEM BLEND COMPILE OK: {len(sources)} source(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
