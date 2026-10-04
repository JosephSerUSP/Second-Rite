"""Generate/check the furnishing catalogue without importing bpy on the host.

python tools/blender/furnishings_catalogue.py --build
python tools/blender/furnishings_catalogue.py --check
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE = HERE / "recipes/furnishings.py"
FIXTURES = HERE / "recipes/catalogue-fixtures.json"
OUTPUT = HERE / "recipes/catalogue"
DOCUMENT = HERE / "recipes/FURNISHINGS.md"
DEPENDENCIES = [SOURCE, FIXTURES, HERE / "recipes/interior.py",
                HERE / "second_rite_asset_core.py", HERE / "recipes/first_stratum/common.py",
                ROOT / "tools/asset-language/materials.json", Path(__file__),
                HERE / "render_furnishings_catalogue.py", HERE / "blender-pin.json",
                HERE / "fixtures/town_sideview_camera.json", HERE / "recipes/shell_geometry.py",
                HERE / "furnishing_geometry.py"]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fingerprint():
    # Git may check text out as CRLF on Windows and LF on hosted Linux.
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(
        p.read_text(encoding="utf-8").encode("utf-8")).hexdigest() for p in DEPENDENCIES}


def inventory(source=SOURCE, fixtures=FIXTURES):
    """AST-derived public API; preview metadata may override inputs, never builders."""
    tree = ast.parse(Path(source).read_text(encoding="utf-8"))
    metadata = json.loads(Path(fixtures).read_text(encoding="utf-8"))
    rows = []
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef) or node.name.startswith("_"):
            continue
        doc = ast.get_docstring(node)
        if not doc:
            raise ValueError(f"{node.name}: public builder needs a docstring")
        args = node.args
        parameters = []
        positional = args.posonlyargs + args.args
        defaults = [None] * (len(positional) - len(args.defaults)) + list(args.defaults)
        for arg, default, keyword in [(a, d, False) for a, d in zip(positional, defaults)] + [
                (a, d, True) for a, d in zip(args.kwonlyargs, args.kw_defaults)]:
            parameters.append({"name": arg.arg, "keywordOnly": keyword,
                               "required": default is None,
                               "default": None if default is None else ast.unparse(default)})
        names = {p["name"] for p in parameters}
        overrides = metadata["overrides"].get(node.name, {})
        unknown = set(overrides) - names
        if unknown:
            raise ValueError(f"{node.name}: unknown fixture parameters {sorted(unknown)}")
        missing = [p["name"] for p in parameters if p["required"] and
                   p["name"] not in {"room", "name", "at"} and p["name"] not in overrides]
        if missing:
            raise ValueError(f"{node.name}: missing preview inputs {missing}")
        rows.append({"id": node.name, "signature": f"{node.name}({ast.unparse(args)})",
                     "description": doc, "parameters": parameters,
                     "fixture": overrides,
                     "placement": metadata["placement"].get(node.name,
                         "Floor at=(x,y), or use room.surface(z) for a support. "
                         "+X is room depth, -Y is screen right; inspect the measured bounds.")})
    public = {r["id"] for r in rows}
    for field in ("overrides", "placement"):
        stale = set(metadata[field]) - public
        if stale:
            raise ValueError(f"{field}: unknown builders {sorted(stale)}")
    return rows


def document(rows):
    lines = ["# Furnishings catalogue", "",
             "Generated from the public builders in [furnishings.py](furnishings.py). "
             "Regenerate with `python tools/blender/furnishings_catalogue.py --build`; "
             "check without Blender with `--check`.", "",
             "These flat-colour orthographic illustrations show isolated construction, "
             "not native camera composition or baked lighting. Each image is fitted separately; "
             "compare the measured metres, not apparent image size. Pale context is excluded "
             "from measurements. Materials use the canonical semantic palette; custom "
             "bindings in fixtures are examples. Adopted .blend documents remain source authority.", "",
             "![All public furnishing builders](catalogue/contact-sheet.png)", "",
             "| Builder | Measured X × Y × Z (m) | Placement |", "|---|---|---|"]
    for row in rows:
        size = " × ".join(f"{v:.3f}" for v in row["dimensions"])
        lines.append(f"| [{row['id']}](#{row['id'].replace('_', '-')}) | {size} | {row['placement']} |")
    for row in rows:
        lines += ["", f"## {row['id']}", "", f"![{row['id']}](catalogue/{row['id']}.png)", "",
                  row["description"], "", f"`{row['signature']}`", "", row["placement"], "",
                  f"Measured bounds: `{row['bounds']}` metres. "
                  f"Built meshes: {row['meshCount']}; lights: {row['lightCount']}.", "",
                  "Materials: " + ", ".join(f"`{m}`" for m in row["materials"]) + ".", "",
                  "| Parameter | Default / required |", "|---|---|"]
        for p in row["parameters"]:
            if p["name"] not in {"room", "name"}:
                value = "required" if p["required"] else p["default"]
                lines.append(f"| `{p['name']}` | `{value}` |")
        if row["fixture"]:
            lines += ["", "Preview bindings: `" + json.dumps(row["fixture"], sort_keys=True) + "`. "
                      "All other values use builder defaults."]
        editable = [p["name"] for p in row["parameters"] if not p["required"]]
        lines += ["", "Variation handles: " + (", ".join(f"`{n}`" for n in editable)
                    if editable else "placement and material bindings") +
                  ". These are inputs to the same builder; review any changed proportions in context."]
    return "\n".join(lines) + "\n"


def check(output=OUTPUT, doc_path=DOCUMENT):
    data = json.loads((output / "index.json").read_text(encoding="utf-8"))
    if data["fingerprint"] != fingerprint():
        raise ValueError("catalogue inputs changed; regenerate with --build")
    expected = inventory()
    rows = data["entries"]
    if [r["id"] for r in rows] != [r["id"] for r in expected]:
        raise ValueError("catalogue does not cover every public builder in source order")
    for row, api in zip(rows, expected):
        if any(row.get(k) != v for k, v in api.items()):
            raise ValueError(f"{api['id']}: stale API/fixture metadata")
        lo, hi = row["bounds"]
        if len(lo) != 3 or len(hi) != 3 or any(not math.isfinite(v) for v in lo + hi):
            raise ValueError(f"{api['id']}: invalid measured bounds")
        if any(b <= a for a, b in zip(lo, hi)) or row["dimensions"] != [round(b-a, 6) for a,b in zip(lo,hi)]:
            raise ValueError(f"{api['id']}: inconsistent measured dimensions")
        if row["meshCount"] < 1 or not row["materials"]:
            raise ValueError(f"{api['id']}: empty preview geometry/materials")
    wanted = {f"{r['id']}.png" for r in rows} | {"contact-sheet.png"}
    if {p.name for p in output.glob("*.png")} != wanted or set(data["images"]) != wanted:
        raise ValueError("missing or orphaned catalogue images")
    for name, sha in data["images"].items():
        if digest(output / name) != sha:
            raise ValueError(f"{name}: thumbnail hash mismatch")
    if Path(doc_path).read_text(encoding="utf-8") != document(rows):
        raise ValueError("FURNISHINGS.md differs from generated catalogue")
    return rows


def search(rows, query):
    words = query.casefold().split()
    if not words:
        raise ValueError("--find needs a builder name or descriptive words")
    def matches(row):
        text = " ".join((row["id"], row["description"], row["placement"],
                         " ".join(row["materials"]))).casefold()
        return all(word in text for word in words)
    return sorted((row for row in rows if matches(row)),
                  key=lambda row: (not all(w in row["id"] for w in words), row["id"]))


PREVIEW_FIELDS = ("id", "fixture", "bounds", "dimensions", "materials", "meshCount", "lightCount")


def build(output=OUTPUT, doc_path=DOCUMENT):
    from blender_locator import blender_executable
    from PIL import Image, ImageDraw
    output.mkdir(parents=True, exist_ok=True)
    # Previews are not byte-stable across GPU/driver hosts, so a rebuild would
    # otherwise rewrite every committed PNG when one builder is added. Keep a
    # committed preview whose drawn content (measured geometry and materials) is
    # unchanged; a docstring or signature edit does not change the picture.
    previous = {}
    if (output / "index.json").is_file():
        old = json.loads((output / "index.json").read_text(encoding="utf-8"))
        for entry in old["entries"]:
            image = output / f"{entry['id']}.png"
            if image.is_file() and digest(image) == old["images"].get(image.name):
                previous[entry["id"]] = (entry, image.read_bytes())
    subprocess.run([blender_executable(), "--background", "--factory-startup", "--python-exit-code", "1",
                    "--python", str(HERE / "render_furnishings_catalogue.py"), "--", str(output)],
                   check=True)
    rows = json.loads((output / "measurements.json").read_text(encoding="utf-8"))
    for row in rows:
        kept = previous.get(row["id"])
        if kept and all(kept[0].get(k) == row.get(k) for k in PREVIEW_FIELDS):
            (output / f"{row['id']}.png").write_bytes(kept[1])
    cols, cell_w, cell_h = 5, 256, 250
    sheet = Image.new("RGB", (cols*cell_w, math.ceil(len(rows)/cols)*cell_h), "#e8e6e1")
    draw = ImageDraw.Draw(sheet)
    for i, row in enumerate(rows):
        x, y = (i % cols)*cell_w, (i//cols)*cell_h
        with Image.open(output / f"{row['id']}.png") as im:
            sheet.paste(im.convert("RGB"), (x, y))
        draw.text((x+8, y+228), row["id"], fill="#252525")
    sheet.save(output / "contact-sheet.png")
    data = {"version": 1, "fingerprint": fingerprint(), "entries": rows,
            "images": {p.name: digest(p) for p in sorted(output.glob("*.png"))}}
    (output / "index.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    (output / "measurements.json").unlink()
    Path(doc_path).write_text(document(rows), encoding="utf-8")
    check(output, doc_path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--build", action="store_true")
    action.add_argument("--check", action="store_true")
    action.add_argument("--find", metavar="WORDS", help="search measured builders without Blender")
    args = parser.parse_args()
    try:
        if args.find is not None:
            found = search(check(), args.find)
            if not found:
                parser.exit(2, "No catalogue entry matches those words.\n")
            words = args.find.casefold().split()
            for row in found:
                how = ("name" if all(w in row["id"] for w in words)
                       else "description only - check it is really what you want")
                print(f"{row['id']}: XYZ metres {row['dimensions']}  [matched: {how}]")
                print(row['signature'])
                print(row['placement'])
                print(f"tools/blender/recipes/FURNISHINGS.md#{row['id'].replace('_', '-')}\n")
            return
        build() if args.build else check()
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"catalogue: {error}\n")
    print(f"FURNISHINGS CATALOGUE OK ({len(inventory())} public builders)")


if __name__ == "__main__":
    main()
