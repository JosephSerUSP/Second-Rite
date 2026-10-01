"""Acquire named assets deliberately, or verify the committed selection entirely offline.

The read-only asset_library browser remains unchanged. Only `acquire` uses HTTP.
Original files are immutable, hash-addressed and shared by selections from one file.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT = ROOT / "tools/blender/vendor-library"


def checked_path(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError(f"Asset path leaves library: {relative}")
    return path


def verify(root):
    manifest = json.loads((root / "provenance.json").read_text(encoding="utf-8"))
    for file in manifest["files"]:
        path = checked_path(root, file["localPath"])
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != file["sha256"]:
            raise ValueError(f"Missing or changed asset file: {path}")
    files = {file["localPath"]: file["sha256"] for file in manifest["files"]}
    for asset in manifest.get("assets", []):
        digest = asset["file"]["hash"].split(":", 1)[1].lower()
        if files.get(asset["localPath"]) != digest:
            raise ValueError(f"Upstream asset lacks its declared hash: {asset['asset']}")
    return manifest


def acquire(root, names):
    import asset_library
    library = asset_library.Library(asset_library.ONLINE_ESSENTIALS)
    records, files = [], {}
    root.mkdir(parents=True, exist_ok=True)
    for name in names:
        matches = library.find(name, "MATERIAL", asset_library.pinned_blender())
        if len(matches) != 1:
            raise ValueError(f"Expected one compatible material: {name}")
        record = library.provenance(matches[0])
        if record["license"] != "CC0 - Public Domain":
            raise ValueError(f"Selection requires CC0: {name}")
        remote = record["file"]
        digest = remote["hash"].split(":", 1)[1].lower()
        local = f"upstream/{digest}.blend"
        path = checked_path(root, local)
        if not path.exists():
            request = urllib.request.Request(remote["url"], headers={"User-Agent": "hichaukitoden-asset-acquisition/1"})
            with urllib.request.urlopen(request, timeout=60) as response:
                data = response.read(remote["sizeInBytes"] + 1)
            if len(data) != remote["sizeInBytes"] or hashlib.sha256(data).hexdigest() != digest:
                raise ValueError(f"Download hash/size mismatch: {name}")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        records.append({**record, "localPath": local})
        files[local] = {"localPath": local, "sha256": digest}
    (root / "provenance.json").write_text(json.dumps({"schemaVersion": 1, "assets": records,
        "files": list(files.values())}, indent=2) + "\n", encoding="utf-8")
    verify(root)


def blender_check(root, build=False):
    import blender_locator
    subprocess.run([blender_locator.blender_executable(), "-b", "--factory-startup", "--disable-autoexec",
        "--python-exit-code", "1", "-P", str(Path(__file__).with_name("offline_blender.py")),
        "--", str(Path(__file__).with_name("vendor_assets_blender.py")),
        "--", "build" if build else "check", str(root.resolve())], check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("acquire", "check"))
    parser.add_argument("--library", type=Path, default=DEFAULT)
    parser.add_argument("--asset", action="append", default=[])
    parser.add_argument("--hash-only", action="store_true")
    args = parser.parse_args()
    if args.command == "acquire":
        if not args.asset:
            parser.error("acquire requires --asset")
        acquire(args.library, args.asset)
        blender_check(args.library, build=True)
    else:
        verify(args.library)
        if not args.hash_only:
            blender_check(args.library)
    print("VENDORED ASSETS OK")


if __name__ == "__main__":
    main()
