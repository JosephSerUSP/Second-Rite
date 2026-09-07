"""Compile authoritative item ``.blend`` sources without allowing source writes.

This is the host-side entry point around ``compile_item_blend.py``. It hashes
every source before and after Blender, validates the emitted OBJ against the
runtime face contract, and can compare a temporary compile against checked-in
runtime products for CI.

Examples::

    python tools/blender/compile_item_blends.py --blender /path/to/blender
    python tools/blender/compile_item_blends.py --blender /path/to/blender --check
    python tools/blender/compile_item_blends.py --blender /path/to/blender \
      --source assets/authoring/items/foo.blend --output-dir /tmp/item-compile
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
DEFAULT_PROJECT_DIR = ROOT / "projects" / "hichaukitoden-game"
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


def sources_from_args(values: list[str], source_dir: Path) -> list[Path]:
    if values:
        sources = [Path(value).resolve() for value in values]
    elif source_dir.is_dir():
        sources = sorted(path.resolve() for path in source_dir.glob("*.blend"))
    else:
        sources = []
    duplicates = {path for path in sources if sources.count(path) > 1}
    if duplicates:
        raise SystemExit(f"duplicate source arguments: {sorted(map(str, duplicates))}")
    return sources


def _format_rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def compare_bytes(actual: Path, expected: Path):
    if not expected.is_file():
        raise RuntimeError(f"compiled product is missing from repository: {_format_rel(expected)}")
    if actual.read_bytes() != expected.read_bytes():
        raise RuntimeError(
            f"compiled product is stale: {_format_rel(expected)}; "
            "recompile the authoritative .blend and commit the runtime product"
        )


def compile_one(blender: str, source: Path, output_dir: Path, *, check: bool, model_dir: Path | None = None, source_dir: Path | None = None):
    if not source.is_file():
        raise RuntimeError(f"item source does not exist: {source}")
    if model_dir is None:
        if len(source.parents) >= 3:
            model_dir = source.parents[2] / "models" / "items"
        else:
            model_dir = DEFAULT_PROJECT_DIR / "assets" / "models" / "items"
    before = digest(source)
    backup_candidates = [source.with_suffix(source.suffix + str(i)) for i in range(1, 10)]
    preexisting_backups = {path for path in backup_candidates if path.exists()}

    env = os.environ.copy()
    env["SECOND_RITE_ITEM_OUTPUT_DIR"] = str(output_dir)
    if source_dir:
        env["SECOND_RITE_ITEM_SOURCE_DIR"] = str(source_dir)
    elif len(source.parents) >= 3:
        env["SECOND_RITE_ITEM_SOURCE_DIR"] = str(source.parent)
    command = [blender, "--background", str(source), "--python", str(BLENDER_SCRIPT)]
    print("+", " ".join(command))
    subprocess.run(command, cwd=ROOT, env=env, check=True)

    after = digest(source)
    if after != before:
        raise RuntimeError(f"compiler modified source document: {_format_rel(source)}")
    new_backups = {path for path in backup_candidates if path.exists()} - preexisting_backups
    if new_backups:
        raise RuntimeError(f"compiler created Blender backup source(s): {sorted(map(str, new_backups))}")

    obj = output_dir / f"{source.stem}.obj"
    validate(obj)
    if check:
        compare_bytes(obj, model_dir / obj.name)
        mtl = output_dir / f"{source.stem}.mtl"
        canonical_mtl = model_dir / mtl.name
        if mtl.exists() or canonical_mtl.exists():
            compare_bytes(mtl, canonical_mtl)
    return obj


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blender", default=os.environ.get("BLENDER_BIN") or shutil.which("blender"))
    parser.add_argument(
        "--project-root",
        type=Path,
        default=DEFAULT_PROJECT_DIR if DEFAULT_PROJECT_DIR.is_dir() else ROOT,
        help="Root directory of the project containing assets",
    )
    parser.add_argument("--source", action="append", default=[], help="compile only this .blend; repeatable")
    parser.add_argument(
        "--output-dir",
        help="write runtime products here instead of assets/models/items; incompatible with --check",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="compile to a temporary directory and require products to match checked-in OBJ/MTL",
    )
    args = parser.parse_args(argv)
    if not args.blender:
        raise SystemExit("Blender executable not found; pass --blender or set BLENDER_BIN")
    if args.check and args.output_dir:
        raise SystemExit("--check and --output-dir are mutually exclusive")

    project_root = Path(args.project_root).resolve()
    source_dir = project_root / "assets" / "authoring" / "items"
    model_dir = project_root / "assets" / "models" / "items"

    sources = sources_from_args(args.source, source_dir)
    if not sources:
        rel = _format_rel(source_dir)
        if args.check:
            raise SystemExit(f"No authoritative item .blend sources found under {rel}; cannot verify.")
        print(f"No authoritative item .blend sources under {rel}; nothing to compile.")
        return 0

    if args.check:
        with tempfile.TemporaryDirectory(prefix="second-rite-item-compile-") as temp:
            output_dir = Path(temp)
            for source in sources:
                compile_one(args.blender, source, output_dir, check=True, model_dir=model_dir, source_dir=source_dir)
    else:
        output_dir = Path(args.output_dir).resolve() if args.output_dir else model_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        for source in sources:
            compile_one(args.blender, source, output_dir, check=False, model_dir=model_dir, source_dir=source_dir)

    print(f"ITEM BLEND COMPILE OK: {len(sources)} source(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
