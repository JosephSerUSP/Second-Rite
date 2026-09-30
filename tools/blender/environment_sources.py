"""Which `.blend` is the source of an environment, as a record rather than a guess (#1269).

Every project keeps its environment `.blend` files in
`assets/authoring/environments/` and a machine-readable status for each one in
`environment-sources.json` beside them:

    adopted     the source authority. Edit it directly, never regenerate it.
                Shipped packages are baked from it.
    scaffold    regenerable output of a recipe. Nothing shipped is baked from it,
                and a recipe may rewrite it (`save_source_blend` still refuses to
                overwrite without `--force`).
    superseded  replaced by the file named in `supersededBy`. Tools refuse to
                write it, and a package must not cite it as its source.
    reference   a file kept for looking at. It is neither a recipe's output nor a
                package's source, and a package must not cite it.

Every shipped `environment.json` records `provenance.sourceBlend`: the name of
the `.blend` it was baked from, or `null` with `provenance.sourceBlendNote` when
no `.blend` exists (a plate authored outside Blender, an unreferenced stub).

    python tools/blender/environment_sources.py --check

Pure Python: no Blender, so it runs in the required `verify` gate.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_NAME = "environment-sources.json"
STATUSES = ("adopted", "scaffold", "superseded", "reference")
# A package may be baked from these; the others are not a package's source.
PACKAGE_SOURCE_STATUSES = ("adopted", "scaffold")
OVERRIDE_ENV = "SR_ALLOW_SUPERSEDED_ENVIRONMENT"
# An entry may carry an `eevee` record: the settings an EEVEE bake of that environment wants
# (eevee_bake.settings_from_args reads it). Each key and its type.
EEVEE_KEYS = {"exposureEV": (int, float), "probeCells": (int, float), "probeSamples": (int,),
              "emissiveLights": (bool,), "fixtureLights": (bool,), "eeveeOptions": (list,),
              "supersample": (int,), "basis": (str,)}
PROJECTS = ("hichaukitoden-game", "editor-fixture")


def authoring_dir(project_root: Path) -> Path:
    return Path(project_root) / "assets" / "authoring" / "environments"


def package_dir(project_root: Path) -> Path:
    return Path(project_root) / "assets" / "environments"


def load_sources(directory: Path) -> dict:
    """The manifest's `sources` map, or {} when the directory has none."""
    path = Path(directory) / MANIFEST_NAME
    if not path.is_file():
        return {}
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle).get("sources", {})


def entry_for(blend: Path):
    """The manifest entry for a `.blend` path, or None when it is unlisted."""
    blend = Path(blend).resolve()
    return load_sources(blend.parent).get(blend.name)


def refuse_superseded(blend: Path) -> None:
    """Raise SystemExit when `blend` is recorded as superseded.

    Call before a tool writes an environment `.blend`. Adopted and scaffold
    files pass, and so does a file nobody has listed yet (a new scaffold).
    """
    entry = entry_for(blend)
    if not entry or entry.get("status") != "superseded":
        return
    if os.environ.get(OVERRIDE_ENV):
        print(f"[environment_sources] {Path(blend).name} is superseded; "
              f"writing anyway because {OVERRIDE_ENV} is set", file=sys.stderr)
        return
    raise SystemExit(
        f"{Path(blend).name} is recorded as superseded by "
        f"{entry.get('supersededBy')} in {MANIFEST_NAME}; refusing to write it. "
        f"Target {entry.get('supersededBy')} instead, or set {OVERRIDE_ENV}=1 "
        "to override deliberately.")


def _check_eevee(where: str, record) -> list[str]:
    """The `eevee` record of an entry: known keys, right types, options as NAME=VALUE."""
    if record is None:
        return []
    if not isinstance(record, dict):
        return [f"{where} has an `eevee` record that is not an object"]
    errors = []
    for key, value in record.items():
        kinds = EEVEE_KEYS.get(key)
        if kinds is None:
            errors.append(f"{where} `eevee` has an unknown key {key!r}; expected one of {sorted(EEVEE_KEYS)}")
        elif not isinstance(value, kinds) or (bool not in kinds and isinstance(value, bool)):
            errors.append(f"{where} `eevee`.{key} is {value!r}; expected {' or '.join(k.__name__ for k in kinds)}")
    for option in record.get("eeveeOptions", []) if isinstance(record.get("eeveeOptions"), list) else []:
        if not isinstance(option, str) or "=" not in option:
            errors.append(f"{where} `eevee`.eeveeOptions has {option!r}; expected NAME=VALUE")
    if not str(record.get("basis", "")).strip():
        errors.append(f"{where} `eevee` has no `basis` (where its numbers came from)")
    return errors


def _check_sources(directory: Path, label: str) -> list[str]:
    errors = []
    blends = sorted(p.name for p in directory.glob("*.blend"))
    manifest_path = directory / MANIFEST_NAME
    if not manifest_path.is_file():
        if blends:
            errors.append(f"{label}: {MANIFEST_NAME} is missing "
                          f"(there are {len(blends)} .blend files)")
        return errors
    sources = load_sources(directory)
    for name in blends:
        if name not in sources:
            errors.append(f"{label}: {name} has no entry in {MANIFEST_NAME}")
    for name, entry in sorted(sources.items()):
        where = f"{label}: {MANIFEST_NAME} entry {name}"
        if name not in blends:
            errors.append(f"{where} names a file that does not exist")
        status = entry.get("status")
        if status not in STATUSES:
            errors.append(f"{where} has status {status!r}; expected one of {STATUSES}")
            continue
        if not str(entry.get("basis", "")).strip():
            errors.append(f"{where} has no `basis` (the evidence for its status)")
        errors.extend(_check_eevee(where, entry.get("eevee")))
        if status == "superseded":
            successor = entry.get("supersededBy")
            if not successor or successor == name or successor not in sources:
                errors.append(f"{where} is superseded by {successor!r}, "
                              "which is not another listed file")
            elif sources[successor].get("status") == "superseded":
                errors.append(f"{where} is superseded by {successor}, "
                              "which is itself superseded")
    return errors


def _check_packages(project_root: Path, label: str) -> list[str]:
    errors = []
    sources = load_sources(authoring_dir(project_root))
    for manifest in sorted(package_dir(project_root).rglob("environment.json")):
        rel = manifest.relative_to(project_root).as_posix()
        with open(manifest, "r", encoding="utf-8") as handle:
            provenance = json.load(handle).get("provenance")
        if not isinstance(provenance, dict) or "sourceBlend" not in provenance:
            errors.append(f"{label}: {rel} records no provenance.sourceBlend")
            continue
        source = provenance["sourceBlend"]
        if source is None:
            if not str(provenance.get("sourceBlendNote", "")).strip():
                errors.append(f"{label}: {rel} has sourceBlend null and no "
                              "sourceBlendNote saying why there is no source")
            continue
        if not (authoring_dir(project_root) / str(source)).is_file():
            errors.append(f"{label}: {rel} names sourceBlend {source!r}, "
                          "which does not exist")
        elif sources.get(source, {}).get("status") not in PACKAGE_SOURCE_STATUSES:
            errors.append(
                f"{label}: {rel} names sourceBlend {source!r} whose status is "
                f"{sources.get(source, {}).get('status')!r}; a package is baked "
                f"from {' or '.join(PACKAGE_SOURCE_STATUSES)} files")
    return errors


def check_project(project_root: Path) -> list[str]:
    project_root = Path(project_root)
    label = project_root.name
    return (_check_sources(authoring_dir(project_root), label)
            + _check_packages(project_root, label))


def main() -> int:
    parser = argparse.ArgumentParser(prog="environment_sources")
    parser.add_argument("--check", action="store_true", required=True)
    parser.add_argument("--root", type=Path, action="append",
                        help="a project root; default: the repository's projects")
    args = parser.parse_args()
    roots = args.root or [ROOT / "projects" / name for name in PROJECTS]
    errors = []
    for root in roots:
        errors.extend(check_project(root))
    for error in errors:
        print("environment_sources: " + error)
    if errors:
        print(f"environment_sources: {len(errors)} problem(s)")
        return 1
    print("environment_sources: OK (" + ", ".join(r.name for r in roots) + ")")
    return 0


if __name__ == "__main__":
    sys.exit(main())
