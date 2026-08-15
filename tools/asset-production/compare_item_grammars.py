#!/usr/bin/env python3
"""Controlled comparison of two authored representations of the same item models.

The study deliberately keeps geometry production out of this script. It compares
already-authored OBJ products from two pinned repository checkouts, so neither
recipe gets regenerated under the other's assumptions.

Usage from the study branch::

    python tools/asset-production/compare_item_grammars.py \
      --blender-root ../found-object-checkout \
      --out-dir docs/reports/item-grammar-study

The Blender checkout must be the ref pinned in ``item-grammar-study.json``.
"""

from __future__ import annotations

import argparse
import ast
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
MANIFEST_PATH = HERE / "item-grammar-study.json"
sys.path.insert(0, str(HERE))

from item_model_corpus import parse_obj as corpus_parse_obj  # noqa: E402
from item_model_corpus import silhouette_iou, silhouettes  # noqa: E402


def _dotted_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _dotted_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return ""


def _is_number(node: ast.AST) -> bool:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return True
    return isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)) and _is_number(node.operand)


def recipe_metrics(path: Path, function_name: str) -> dict:
    """Measure object-specific recipe surface, excluding shared helper libraries.

    ``geometry_call_sites`` counts authored call sites, not runtime instances. A
    call inside a loop is one authoring decision even if it emits several parts.
    ``numeric_tuples`` is intentionally only a rough density proxy for authored
    coordinates/sections/aspects; it is not presented as effort or complexity.
    """
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    function = next(
        (node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name),
        None,
    )
    if function is None:
        raise RuntimeError(f"{path}: function {function_name!r} not found")

    calls: list[str] = []
    numeric_tuples = 0
    for node in ast.walk(function):
        if isinstance(node, ast.Call):
            name = _dotted_name(node.func)
            if name.startswith("sweep.") or name.startswith("base.add_") or name.startswith("add_"):
                calls.append(name)
        elif isinstance(node, ast.Tuple) and 2 <= len(node.elts) <= 5 and all(_is_number(value) for value in node.elts):
            numeric_tuples += 1

    return {
        "path": str(path),
        "function": function_name,
        "source_loc": int(function.end_lineno - function.lineno + 1),
        "geometry_call_sites": len(calls),
        "geometry_calls": calls,
        "numeric_tuples": numeric_tuples,
    }


def obj_metrics(path: Path) -> dict:
    vertices: list[tuple[float, float, float]] = []
    authored_faces = 0
    triangles = 0
    vt = 0
    vn = 0
    uv_faces = 0
    materials: set[str] = set()

    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = raw.split()
        if not parts:
            continue
        tag = parts[0]
        if tag == "v" and len(parts) >= 4:
            vertices.append(tuple(float(value) for value in parts[1:4]))
        elif tag == "vt":
            vt += 1
        elif tag == "vn":
            vn += 1
        elif tag == "usemtl" and len(parts) >= 2:
            materials.add(parts[1])
        elif tag == "f":
            corners = parts[1:]
            authored_faces += 1
            triangles += max(0, len(corners) - 2)
            if corners and all(len(corner.split("/")) >= 2 and corner.split("/")[1] for corner in corners):
                uv_faces += 1

    if not vertices:
        raise RuntimeError(f"{path}: no vertices")

    mins = [min(vertex[axis] for vertex in vertices) for axis in range(3)]
    maxs = [max(vertex[axis] for vertex in vertices) for axis in range(3)]
    extents = [maxs[axis] - mins[axis] for axis in range(3)]
    diagonal = math.sqrt(sum(value * value for value in extents))

    return {
        "path": str(path),
        "vertices": len(vertices),
        "authored_faces": authored_faces,
        "triangles": triangles,
        "uv_vertices": vt,
        "normals": vn,
        "uv_face_fraction": (uv_faces / authored_faces) if authored_faces else 0.0,
        "materials": sorted(materials),
        "material_count": len(materials),
        "bbox_extent_xyz": [round(value, 6) for value in extents],
        "bbox_diagonal": round(diagonal, 6),
    }


def silhouette_metrics(left_path: Path, right_path: Path) -> dict:
    left = silhouettes(corpus_parse_obj(left_path))
    right = silhouettes(corpus_parse_obj(right_path))
    per_axis = []
    for a, b in zip(left, right):
        union = int((a | b).sum())
        score = 1.0 if union == 0 else float((a & b).sum() / union)
        per_axis.append(score)
    return {
        "mean_iou": silhouette_iou(left, right),
        "axis_iou_xy_xz_yz": per_axis,
    }


def ratio(numerator: float, denominator: float) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator


def fmt_ratio(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.2f}x"


def write_report(result: dict, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "metrics.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Controlled item-grammar study: spatial sweep vs Blender-native",
        "",
        "This study compares **the same three item identities** authored independently by the C spatial-sweep grammar and by the unrestricted Blender-native found-object lane. It does not regenerate either side and it does not change canonical gameplay data.",
        "",
        "## Presentation controls",
        "",
        "The primary visual comparison is the **neutral-material four-angle sheet**. Both variants are temporarily assigned the same neutral material and rendered through the real `item_model_sheet.lua` / `presentation.item_model_view` path, at the same four yaw/tilt pairs. The as-authored material sheet is retained separately because material language is itself a useful pipeline finding, but it is not the geometry-only control.",
        "",
        "![Neutral geometry comparison](neutral-comparison.png)",
        "",
        "![As-authored comparison](authored-comparison.png)",
        "",
        "## Measurements",
        "",
        "`source LOC` and `geometry calls` measure only each object's recipe function. Shared helper libraries are excluded. A call inside a loop counts once, so these are authoring-surface proxies rather than runtime primitive counts or human-effort estimates.",
        "",
        "| item | sweep vtx | Blender vtx | B/C vtx | sweep faces | Blender faces | B/C faces | sweep recipe LOC | Blender recipe LOC | sweep geom calls | Blender geom calls | silhouette IoU |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for item in result["items"]:
        c = item["sweep"]
        b = item["blender"]
        lines.append(
            "| {name} | {cv} | {bv} | {vr} | {cf} | {bf} | {fr} | {cl} | {bl} | {cc} | {bc} | {iou:.3f} |".format(
                name=item["name"],
                cv=c["mesh"]["vertices"], bv=b["mesh"]["vertices"],
                vr=fmt_ratio(item["ratios"]["blender_over_sweep_vertices"]),
                cf=c["mesh"]["authored_faces"], bf=b["mesh"]["authored_faces"],
                fr=fmt_ratio(item["ratios"]["blender_over_sweep_faces"]),
                cl=c["recipe"]["source_loc"], bl=b["recipe"]["source_loc"],
                cc=c["recipe"]["geometry_call_sites"], bc=b["recipe"]["geometry_call_sites"],
                iou=item["silhouette"]["mean_iou"],
            )
        )

    totals = result["totals"]
    lines.extend([
        "",
        "### Cohort totals",
        "",
        f"- Sweep: **{totals['sweep']['vertices']} vertices / {totals['sweep']['authored_faces']} authored faces / {totals['sweep']['recipe_loc']} object-recipe LOC**.",
        f"- Blender: **{totals['blender']['vertices']} vertices / {totals['blender']['authored_faces']} authored faces / {totals['blender']['recipe_loc']} object-recipe LOC**.",
        f"- Blender/sweep ratio: **{fmt_ratio(totals['ratios']['vertices'])} vertices, {fmt_ratio(totals['ratios']['authored_faces'])} authored faces, {fmt_ratio(totals['ratios']['recipe_loc'])} object-recipe LOC**.",
        "",
        "## How to read the silhouette score",
        "",
        "The IoU score is the repository's normalized 64px three-axis silhouette comparison applied **between the two representations of the same item**. A low score means the grammars made materially different shape decisions; a high score means they converged on a similar gross form. It is deliberately **not** a quality score.",
        "",
        "## Review prompts",
        "",
        "1. Which representation communicates the item's identity fastest at the normal item-view size?",
        "2. Which representation retains meaningful information in the side, top and underside views instead of spending detail only on the hero angle?",
        "3. Where does Blender's unrestricted topology create visible value that the sweep grammar cannot express cleanly?",
        "4. Where does the sweep grammar reach the same perceptual result with a smaller or more legible recipe?",
        "5. Which differences are geometry, and which only appear in the as-authored sheet because the material vocabularies differ?",
        "",
        "## Reproduction",
        "",
        f"Sweep source ref: `{result['refs']['sweep']}`  ",
        f"Blender source ref: `{result['refs']['blender']}`",
        "",
        "Check out the pinned Blender ref beside this checkout and run:",
        "",
        "```text",
        "python tools/asset-production/compare_item_grammars.py --blender-root <path-to-blender-checkout> --out-dir docs/reports/item-grammar-study",
        "```",
        "",
        "The four-angle PNGs are generated by the temporary CI materialization used for this experiment; the workflow itself is intentionally removed after the evidence is committed.",
        "",
    ])
    (out_dir / "README.md").write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--blender-root", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args(argv)

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    blender_root = args.blender_root.resolve()
    result = {
        "study": manifest["study"],
        "question": manifest["question"],
        "refs": {"sweep": manifest["sweep"]["ref"], "blender": manifest["blender"]["ref"]},
        "presentation": manifest["presentation"],
        "items": [],
    }

    for spec in manifest["items"]:
        slug = spec["slug"]
        sweep_model = REPO_ROOT / manifest["sweep"]["model_root"] / f"{slug}.obj"
        blender_model = blender_root / manifest["blender"]["model_root"] / f"{slug}.obj"
        sweep_source = REPO_ROOT / spec["sweep_source"]["path"]
        blender_source = blender_root / spec["blender_source"]["path"]

        c_mesh = obj_metrics(sweep_model)
        b_mesh = obj_metrics(blender_model)
        c_recipe = recipe_metrics(sweep_source, spec["sweep_source"]["function"])
        b_recipe = recipe_metrics(blender_source, spec["blender_source"]["function"])
        silhouettes_result = silhouette_metrics(sweep_model, blender_model)

        result["items"].append({
            "name": spec["name"],
            "slug": slug,
            "sweep": {"mesh": c_mesh, "recipe": c_recipe},
            "blender": {"mesh": b_mesh, "recipe": b_recipe},
            "silhouette": silhouettes_result,
            "ratios": {
                "blender_over_sweep_vertices": ratio(b_mesh["vertices"], c_mesh["vertices"]),
                "blender_over_sweep_faces": ratio(b_mesh["authored_faces"], c_mesh["authored_faces"]),
                "blender_over_sweep_recipe_loc": ratio(b_recipe["source_loc"], c_recipe["source_loc"]),
            },
        })

    totals = {
        "sweep": {
            "vertices": sum(item["sweep"]["mesh"]["vertices"] for item in result["items"]),
            "authored_faces": sum(item["sweep"]["mesh"]["authored_faces"] for item in result["items"]),
            "recipe_loc": sum(item["sweep"]["recipe"]["source_loc"] for item in result["items"]),
        },
        "blender": {
            "vertices": sum(item["blender"]["mesh"]["vertices"] for item in result["items"]),
            "authored_faces": sum(item["blender"]["mesh"]["authored_faces"] for item in result["items"]),
            "recipe_loc": sum(item["blender"]["recipe"]["source_loc"] for item in result["items"]),
        },
    }
    totals["ratios"] = {
        "vertices": ratio(totals["blender"]["vertices"], totals["sweep"]["vertices"]),
        "authored_faces": ratio(totals["blender"]["authored_faces"], totals["sweep"]["authored_faces"]),
        "recipe_loc": ratio(totals["blender"]["recipe_loc"], totals["sweep"]["recipe_loc"]),
    }
    result["totals"] = totals

    write_report(result, args.out_dir)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
