"""Generate/check the role index for every top-level Blender Python/JS tool.

The manifest classifies routes; source docstrings describe implementation.
History remains at its original path. New unclassified scripts fail --check.
"""
import argparse
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
    return sorted(rows, key=lambda r: r["path"])


def document(rows):
    lines = ["# Blender script roles", "", "Generated from [SCRIPTS.json](SCRIPTS.json). "
             "Start with the [authoring routes](README.md) and "
             "[furnishings catalogue](recipes/FURNISHINGS.md). "
             "An experiment or source-editing migration is evidence, not a template for a fresh room.", "",
             "Run `python tools/blender/script_index.py --check`; after classifying a new top-level "
             "Python or JS file in the manifest, run `--write`. Classification preserves paths and bytes. "
             "Nested recipe, test and bridge directories have their own entry points; this manifest "
             "covers the top-level tool surface."]
    for role, title in ROLES.items():
        group = [r for r in rows if r["role"] == role]
        if not group:
            continue
        lines += ["", f"## {title} ({len(group)})", "", "| Script | Purpose |", "|---|---|"]
        lines += [f"| [{r['path']}]({r['path']}) | {r['purpose']} |" for r in group]
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
