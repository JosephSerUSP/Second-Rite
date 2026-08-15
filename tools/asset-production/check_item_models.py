"""Gate: the item model corpus must not contain items that are the same item.

Run it:

    python tools/asset-production/check_item_models.py            # gate
    python tools/asset-production/check_item_models.py --report   # full listing
    python tools/asset-production/check_item_models.py --write-baseline

The library shipped by the 2026-08 batch production is known-bad: 112 distinct
shapes across 208 files, and 155 models with no UVs. Those violations are
recorded in ``item-model-baseline.json`` so this gate fails on *new* ones while
the existing set is replaced cohort by cohort. The baseline is only ever
allowed to shrink; a run that no longer reproduces a baselined violation says
so and asks for the baseline to be rewritten.

Writing the baseline is an owner-signed action, exactly as recapturing a golden
is. It is the one way to make this gate green without improving a model.
"""

from __future__ import annotations

import argparse
import itertools
import json
import sys
from collections import defaultdict
from pathlib import Path

from item_model_corpus import (
    ItemModelError,
    SILHOUETTE_IOU_LIMIT,
    geometry_hash,
    load_item_models,
    parse_obj,
    silhouette_iou,
    silhouettes,
)

BASELINE_PATH = Path(__file__).resolve().parent / "item-model-baseline.json"


def violation_key(kind: str, members: list[str]) -> str:
    return f"{kind}:{'|'.join(sorted(members))}"


def collect_violations(models: dict[str, Path]) -> list[dict]:
    """Every corpus-level defect, as sorted, stable, keyable records."""
    meshes = {name: parse_obj(path) for name, path in models.items()}

    violations: list[dict] = []

    # --- shared file: two items literally pointing at one model ---------------
    by_file: dict[Path, list[str]] = defaultdict(list)
    for name, path in models.items():
        by_file[path].append(name)
    for path, names in sorted(by_file.items()):
        if len(names) > 1:
            violations.append(
                {
                    "kind": "shared_file",
                    "members": sorted(names),
                    "detail": str(path.relative_to(path.parents[3])),
                }
            )

    # --- identical geometry under a different name ---------------------------
    by_geometry: dict[str, list[str]] = defaultdict(list)
    for name, mesh in meshes.items():
        by_geometry[geometry_hash(mesh)].append(name)
    duplicate_geometry: set[frozenset[str]] = set()
    for _, names in sorted(by_geometry.items()):
        unique_files = {models[n] for n in names}
        if len(unique_files) > 1:
            violations.append({"kind": "duplicate_geometry", "members": sorted(names)})
            duplicate_geometry.add(frozenset(names))

    # --- indistinguishable at display size -----------------------------------
    # Skipped for pairs already reported as duplicate geometry: one defect
    # reported twice trains people to ignore the gate.
    masks = {name: silhouettes(mesh) for name, mesh in meshes.items()}
    already = {pair for group in duplicate_geometry for pair in itertools.combinations(sorted(group), 2)}
    for left, right in itertools.combinations(sorted(masks), 2):
        if (left, right) in already or models[left] == models[right]:
            continue
        score = silhouette_iou(masks[left], masks[right])
        if score >= SILHOUETTE_IOU_LIMIT:
            violations.append(
                {
                    "kind": "indistinct_silhouette",
                    "members": [left, right],
                    "detail": f"iou={score:.4f}",
                }
            )

    # --- no UVs: nothing for the texturing track to paint onto ---------------
    for name in sorted(meshes):
        mesh = meshes[name]
        if mesh.faces_with_uv == 0:
            violations.append({"kind": "no_uvs", "members": [name]})

    for record in violations:
        record["key"] = violation_key(record["kind"], record["members"])
    return violations


def load_baseline() -> set[str]:
    if not BASELINE_PATH.exists():
        return set()
    data = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    return set(data.get("accepted", []))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", action="store_true", help="list every violation, baselined or not")
    parser.add_argument(
        "--write-baseline",
        action="store_true",
        help="record the current violations as accepted (owner-signed)",
    )
    args = parser.parse_args(argv)

    # Item names include non-ASCII (Pao de Queijo, Feijoada); the Windows
    # console default is cp932 here and would abort the report mid-listing.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    try:
        models = load_item_models()
        violations = collect_violations(models)
    except ItemModelError as exc:
        print(f"ITEM MODELS FAILED: {exc}")
        return 2

    counts: dict[str, int] = defaultdict(int)
    for record in violations:
        counts[record["kind"]] += 1

    if args.write_baseline:
        BASELINE_PATH.write_text(
            json.dumps(
                {
                    "note": (
                        "Corpus violations accepted as pre-existing. Owner-signed. "
                        "This list may only shrink."
                    ),
                    "counts": dict(sorted(counts.items())),
                    "accepted": sorted(r["key"] for r in violations),
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"baseline written: {len(violations)} violations across {len(models)} items")
        return 0

    baseline = load_baseline()
    keys = {r["key"] for r in violations}
    new = [r for r in violations if r["key"] not in baseline]
    stale = sorted(baseline - keys)

    if args.report:
        for record in sorted(violations, key=lambda r: (r["kind"], r["members"])):
            status = "NEW" if record["key"] not in baseline else "baselined"
            detail = f" ({record['detail']})" if record.get("detail") else ""
            print(f"[{status}] {record['kind']}: {', '.join(record['members'])}{detail}")
        print()

    print(f"items with models: {len(models)}")
    for kind, count in sorted(counts.items()):
        print(f"  {kind}: {count}")

    if stale:
        print()
        print(f"{len(stale)} baselined violation(s) no longer reproduce — rewrite the baseline:")
        for key in stale[:10]:
            print(f"  fixed: {key}")
        if len(stale) > 10:
            print(f"  ... and {len(stale) - 10} more")
        print("  python tools/asset-production/check_item_models.py --write-baseline")
        return 1

    if new:
        print()
        print(f"ITEM MODELS FAILED: {len(new)} new corpus violation(s)")
        for record in new[:20]:
            detail = f" ({record['detail']})" if record.get("detail") else ""
            print(f"  {record['kind']}: {', '.join(record['members'])}{detail}")
        if len(new) > 20:
            print(f"  ... and {len(new) - 20} more")
        return 1

    print()
    print("ITEM MODELS OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
