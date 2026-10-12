"""Keep item-model textures honest: authored source, promoted product, and every MTL reference.

An item ``.blend`` may use painted images two ways, and the compile boundary
treats them differently:

* ``map_Kd`` (an image in the material's Base Color): the OBJ exporter copies it
  beside the OBJ (``path_mode=COPY``), so it is a compile product -- but
  ``compile_item_blends.py --check`` compares only OBJ and MTL bytes, so a stale
  copy is invisible to it.
* ``pass <uvSource> <blend> <strength> <path>`` (a runtime overlay such as an
  engraving multiply layer): the exporter never sees the file at all. The MTL
  just names a Project-relative path, and nothing creates or verifies it.

Authored textures live in ``assets/authoring/items/_textures/`` (the source of
truth, committed beside the ``.blend`` that references them). This tool checks
that

1. each authored texture has a byte-identical promoted copy in
   ``assets/models/items/``;
2. every ``map_Kd`` and ``pass`` path in every item MTL resolves to a file.

    python tools/blender/item_textures.py --check
    python tools/blender/item_textures.py --sync      # copy authored -> promoted

``--sync`` only ever copies *authoring -> models*; it never edits an authored
texture and never deletes anything.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parents[1]
sys.path.insert(0, str(ROOT))

AUTHORED = Path("assets") / "authoring" / "items" / "_textures"
PROMOTED = Path("assets") / "models" / "items"


def mtl_references(mtl: Path):
    """Yield ``(kind, path)`` for every texture an MTL names."""
    for raw in mtl.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        op, _, rest = line.partition(" ")
        rest = rest.strip()
        if op == "map_Kd" and rest:
            yield "map_Kd", rest
        elif op == "pass" and rest:
            parts = rest.split(None, 3)
            if len(parts) == 4:
                yield "pass", parts[3].strip()
        elif op == "refl" and rest:
            parts = rest.split(None, 2)
            if len(parts) == 3:
                yield "pass", parts[2].strip()


def check(project: Path) -> list[str]:
    problems: list[str] = []
    authored_dir, promoted_dir = project / AUTHORED, project / PROMOTED
    if authored_dir.is_dir():
        for source in sorted(authored_dir.glob("*.png")):
            promoted = promoted_dir / source.name
            if not promoted.is_file():
                problems.append(f"authored texture not promoted: {source.name} (run --sync)")
            elif promoted.read_bytes() != source.read_bytes():
                problems.append(f"promoted texture differs from authored source: {source.name} (run --sync)")
    for mtl in sorted(promoted_dir.glob("*.mtl")):
        for kind, ref in mtl_references(mtl):
            target = (mtl.parent / ref) if kind == "map_Kd" else (project / ref)
            if not target.is_file():
                problems.append(f"{mtl.name}: {kind} texture does not exist: {ref}")
    return problems


def sync(project: Path) -> list[str]:
    copied = []
    authored_dir, promoted_dir = project / AUTHORED, project / PROMOTED
    if not authored_dir.is_dir():
        return copied
    promoted_dir.mkdir(parents=True, exist_ok=True)
    for source in sorted(authored_dir.glob("*.png")):
        target = promoted_dir / source.name
        if not target.is_file() or target.read_bytes() != source.read_bytes():
            shutil.copyfile(source, target)
            copied.append(source.name)
    return copied


def main(argv=None) -> int:
    from tools.shared.project_paths import project_root

    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--project-root", type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--sync", action="store_true")
    args = parser.parse_args(argv)
    project = project_root(args.project_root)
    if args.sync:
        copied = sync(project)
        print(f"ITEM TEXTURES SYNCED: {len(copied)} copied" + (f" ({', '.join(copied)})" if copied else ""))
        return 0
    problems = check(project)
    for problem in problems:
        print(f"  {problem}")
    if problems:
        print(f"ITEM TEXTURES FAILED: {len(problems)} problem(s)")
        return 1
    print("ITEM TEXTURES OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
