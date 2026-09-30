"""Our own Blender asset library: SR_GroundCover, browsable like any remote library.

    python tools/blender/build_asset_library.py            # rebuild the library
    python tools/blender/build_asset_library.py --check    # verify what is committed

`tools/blender/asset-library/` holds one `.blend` with the `SR_GroundCover` node
group marked as an asset, a catalogue file, and the listing Blender's own generator
writes (`_asset-library-meta.json`, `_v1/`). It is read the way Blender reads a remote
library, so `tools/blender/asset_library.py --url file:///.../asset-library/` browses it
with licence, author and file hash, and Blender can add the directory as a local
library in Preferences.

This is NOT published. Nothing serves it, and it is not registered anywhere: public
serving would put our content into the online asset ecosystem, which needs stricter
criteria than an in-repo library has (see `docs/asset-pipeline/BLENDER_CORE.md`).

The node group is defined by `ground_cover.build_group()`; the library `.blend` is a
derived product of it, never edited by hand. `--check` fails when the listing no longer
describes the file, or the file no longer carries the asset the listing promises;
`tests/test_sr_asset_library.py` checks (in Blender) that the group in the file is the
one `build_group()` builds now.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "blender"))
import asset_library  # noqa: E402
import blender_locator  # noqa: E402

LIBRARY = ROOT / "tools" / "blender" / "asset-library"
BLEND_NAME = "second_rite_nodes.blend"
CATALOG_PATH = "Second Rite/Environment"
CATALOG_ID = str(uuid.uuid5(uuid.NAMESPACE_URL, "second-rite/asset-library/" + CATALOG_PATH))
LIBRARY_NAME = "Second Rite Assets"
CONTACT = {"name": "Second Rite", "url": "https://github.com/JosephSerUSP/Second-Rite"}

#: The metadata every asset in this library carries. The licence is the owner's choice
#: (CC0, 2026-09-30); a listing entry without one is not accepted by `--check`.
LICENSE = "CC0 - Public Domain"
AUTHOR = "Second Rite"
COPYRIGHT = "Second Rite"

#: name -> (id type, description, tags). One entry per asset the library must contain.
ASSETS = {
    "SR_GroundCover": (
        "NODETREE",
        "Scatters crossed-quad grass tufts over a terrain mesh: painted density, a slope "
        "limit, keep-out collections and Poisson spacing. Realise before export.",
        ["Ground Cover", "Grass", "Scatter", "Environment"]),
}


def write_catalog_file(library: Path) -> None:
    (library / "blender_assets.cats.txt").write_text(
        "# This is an Asset Catalog Definition file for Blender.\n#\n"
        "# Empty lines and lines starting with `#` will be ignored.\n"
        "# The first non-ignored line should be the version indicator.\n"
        "# Other lines are of the format \"UUID:catalog/path/for/assets:simple catalog name\"\n\n"
        "VERSION 1\n\n"
        f"{CATALOG_ID}:{CATALOG_PATH}:{CATALOG_PATH.replace('/', '-')}\n", encoding="utf-8")


def write_meta_file(library: Path) -> None:
    """The listing generator keeps the name and contact already in this file."""
    path = library / asset_library.META_NAME
    meta = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    meta["name"] = LIBRARY_NAME
    meta["contact"] = CONTACT
    meta.setdefault("api_versions", {})
    path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")


def run_blender(*arguments: str) -> None:
    # A script that raises still lets Blender exit 0 unless it is told otherwise.
    command = [blender_locator.blender_executable(), "--factory-startup",
               "--python-exit-code", "1", *arguments]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        sys.stdout.write(result.stdout[-3000:])
        sys.stderr.write(result.stderr[-3000:])
        raise SystemExit(f"Blender failed: {' '.join(arguments)}")


def build(library: Path) -> None:
    library.mkdir(parents=True, exist_ok=True)
    for stale in ("_v1",):
        if (library / stale).is_dir():
            for page in (library / stale).iterdir():
                page.unlink()
    run_blender("--background", "-noaudio", "--python",
                str(ROOT / "tools" / "blender" / "asset_library_source.py"),
                "--", "build", str(library / BLEND_NAME))
    write_catalog_file(library)
    write_meta_file(library)
    run_blender("-c", "asset_listing", "generate", str(library))
    problems = check(library)
    if problems:
        raise SystemExit("rebuilt library does not verify:\n  " + "\n  ".join(problems))


def check(library: Path) -> list[str]:
    """Pure Python: the listing describes the file, and the file carries the assets promised."""
    problems: list[str] = []
    blend = library / BLEND_NAME
    if not blend.is_file():
        return [f"{BLEND_NAME} is missing"]
    try:
        with tempfile.TemporaryDirectory(prefix="sr_asset_library_") as cache:
            listing = asset_library.Library(library.resolve().as_uri(), cache=Path(cache), refresh=True)
    except SystemExit as error:  # hash chain, counts, API version
        return [f"listing is not valid: {error}"]
    if listing.meta.get("name") != LIBRARY_NAME:
        problems.append(f"library name is {listing.meta.get('name')!r}, expected {LIBRARY_NAME!r}")
    actual = _sha(blend)
    for path, info in listing.files.items():
        if path == BLEND_NAME and info.get("hash") != actual:
            problems.append(f"{BLEND_NAME} has changed since the listing was generated "
                            f"(listing {info.get('hash')}, file {actual}); rebuild the library")
    for name, (id_type, description, tags) in ASSETS.items():
        found = listing.find(name, id_type)
        if not found:
            problems.append(f"the listing has no {id_type} asset {name!r}")
            continue
        asset = found[0]
        record = listing.record(asset)
        if record["license"] != LICENSE:
            problems.append(f"{name}: licence is {record['license']!r}, expected {LICENSE!r}")
        for field, expected in (("author", AUTHOR), ("copyright", COPYRIGHT),
                                ("catalog", CATALOG_PATH)):
            if record[field] != expected:
                problems.append(f"{name}: {field} is {record[field]!r}, expected {expected!r}")
        if not record["description"]:
            problems.append(f"{name}: no description")
        if sorted(record["tags"]) != sorted(tags):
            problems.append(f"{name}: tags are {record['tags']}, expected {tags}")
    extra = {a["name"] for a in listing.assets} - set(ASSETS)
    if extra:
        problems.append(f"the listing holds assets not declared in ASSETS: {sorted(extra)}")
    return problems


def _sha(path: Path) -> str:
    return "SHA256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(prog="build_asset_library")
    parser.add_argument("--check", action="store_true", help="verify the committed library; write nothing")
    parser.add_argument("--library", type=Path, default=LIBRARY)
    args = parser.parse_args()
    if args.check:
        problems = check(args.library)
        for problem in problems:
            print("asset-library: " + problem)
        print("asset-library: " + (f"{len(problems)} problem(s)" if problems else "OK"))
        return 1 if problems else 0
    build(args.library)
    print(f"asset-library: rebuilt {args.library}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
