"""Build a deterministic installable Blender add-on ZIP."""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FILES = ("__init__.py", "addon.py", "client.py", "protocol.py", "server.py", "README.md")
PACKAGE_NAME = "thestra_live_bridge"
VERSION = 1


def build(output: Path) -> dict:
    output = output.resolve(); output.parent.mkdir(parents=True, exist_ok=True)
    entries = [(f"{PACKAGE_NAME}/{name}", (ROOT / name).read_bytes()) for name in FILES]
    metadata = {"package": PACKAGE_NAME, "version": VERSION,
                "protocolVersion": 1, "clientVersion": 1,
                "files": [name for name, _ in entries]}
    entries.append((f"{PACKAGE_NAME}/package.json", json.dumps(metadata, indent=2, sort_keys=True).encode()))
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(entries):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data)
    return {"path": str(output), "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
            "files": [name for name, _ in entries], "version": VERSION}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    print(json.dumps(build(parser.parse_args().output), indent=2, sort_keys=True))
