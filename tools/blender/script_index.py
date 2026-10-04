"""Generate/check the role index for every top-level Blender Python/JS tool.

The manifest classifies routes; source docstrings describe implementation.
History remains at its original path. New unclassified scripts fail --check.

The "Run with" column is derived from each file, not hand-written, so it cannot
drift: a Python script that imports bpy/bmesh/mathutils at module level runs
inside Blender (through run.py), any other runnable script is host Python, and
a file with no ``__main__`` guard or ``sys.argv`` use is import-only. A row may
set ``"run"`` to override the derivation when a file's imports mislead.
"""
import argparse
import ast
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "SCRIPTS.json"
DOCUMENT = HERE / "SCRIPTS.md"
ROLES = {
    "production": "Supported authoring and verification entry points",
    "library": "Implementation modules and Blender workers",
    "study": "Experiments and measurements",
    "one-shot": "Recorded source surgery and migrations",
    "legacy": "Retained historical routes",
}
LAUNCHERS = ("run.py", "python", "node", "import")
BLENDER_MODULES = {"bpy", "bmesh", "mathutils"}


def module_imports(tree):
    """Top-level module names imported outside any function or class body."""
    found = set()

    def visit(nodes):
        for node in nodes:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            if isinstance(node, ast.Import):
                found.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
                found.add(node.module.split(".")[0])
            for field in ("body", "orelse", "finalbody", "handlers"):
                children = getattr(node, field, None)
                if isinstance(children, list):
                    visit(children)

    visit(tree.body)
    return found


def launcher(path, row=None):
    """How the file is started: run.py (inside Blender), python, node or import."""
    if row and row.get("run"):
        return row["run"]
    path = Path(path)
    if path.suffix == ".js":
        return "node"
    text = path.read_text(encoding="utf-8")
    if "__main__" not in text and "sys.argv" not in text:
        return "import"
    return "run.py" if module_imports(ast.parse(text)) & BLENDER_MODULES else "python"


def entries(manifest=MANIFEST, directory=HERE):
    data = json.loads(Path(manifest).read_text(encoding="utf-8"))
    rows = data["scripts"]
    listed = [r["path"] for r in rows]
    if len(set(listed)) != len(listed):
        raise ValueError("duplicate script paths in SCRIPTS.json")
    actual = {p.name for p in Path(directory).iterdir() if p.is_file() and p.suffix in {".py", ".js"}}
    if set(listed) != actual:
        raise ValueError(f"unclassified: {sorted(actual-set(listed))}; missing: {sorted(set(listed)-actual)}")
    for row in rows:
        if row["role"] not in ROLES or not row["purpose"].strip():
            raise ValueError(f"{row['path']}: invalid role or empty purpose")
        if row.get("run", "run.py") not in LAUNCHERS:
            raise ValueError(f"{row['path']}: run must be one of {LAUNCHERS}")
    rows = [dict(row, launch=launcher(Path(directory) / row["path"], row)) for row in rows]
    return sorted(rows, key=lambda r: r["path"])


def document(rows):
    lines = ["# Blender script roles", "", "Generated from [SCRIPTS.json](SCRIPTS.json). "
             "Start with the [authoring routes](README.md) and "
             "[furnishings catalogue](recipes/FURNISHINGS.md). "
             "An experiment or source-editing migration is evidence, not a template for a fresh room.", "",
             "Run `python tools/blender/script_index.py --check`; after classifying a new top-level "
             "Python or JS file in the manifest, run `--write`. Classification preserves paths and bytes. "
             "Nested recipe, test and bridge directories have their own entry points; this manifest "
             "covers the top-level tool surface.", "",
             "**Run with** says how to start a file. `run.py` means it runs inside the pinned Blender: "
             "`python tools/blender/run.py tools/blender/<script> [--blend FILE] -- <args>` "
             "(never a hand-typed `blender --python` command, which exits 0 when the script raises). "
             "`python` and `node` mean an ordinary host command; `import` means the file is only "
             "imported or spawned by other tools."]
    for role, title in ROLES.items():
        group = [r for r in rows if r["role"] == role]
        if not group:
            continue
        lines += ["", f"## {title} ({len(group)})", "", "| Script | Run with | Purpose |", "|---|---|---|"]
        lines += [f"| [{r['path']}]({r['path']}) | `{r['launch']}` | {r['purpose']} |" for r in group]
    return "\n".join(lines) + "\n"


def check():
    rows = entries()
    if DOCUMENT.read_text(encoding="utf-8") != document(rows):
        raise ValueError("SCRIPTS.md is stale; run script_index.py --write")
    return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--check", action="store_true")
    action.add_argument("--write", action="store_true")
    args = parser.parse_args()
    try:
        rows = entries()
        if args.write:
            DOCUMENT.write_text(document(rows), encoding="utf-8")
        else:
            check()
    except (ValueError, OSError) as error:
        parser.exit(1, f"script index: {error}\n")
    print(f"BLENDER SCRIPT INDEX OK ({len(rows)} classified scripts)")
