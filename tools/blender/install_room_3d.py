"""Install a baked room export as a runtime town environment package.

`export_room_environment.py` writes a pipeline manifest describing the bake.
This turns that into the package the runtime actually reads: no `preRendered`
block, so `viewport_3d` falls through to the real 3D path and submits
`renderMesh` as placed geometry.

Two fixes are applied on the way across.

The pipeline measures bounds from the joined mesh BEFORE the OBJ is mirrored
into engine space, so its Y range is still Blender's. It is reflected here with
the same `engine_y = LANE_CENTRE - blender_y` the mesh got, and the endpoints
swap places under a reflection -- min and max are recomputed, not renamed.

The pipeline's own anchors are already engine-space (the exporter authors the
empties there), so they pass through untouched.

    python tools/blender/install_room_3d.py --export <dir> --name alicias_padaria_3d

To review a package before it ships, install it outside the Project with
`--destination out/<review>/<name>`; the runtime stage then copies it in.
"""

from __future__ import annotations

import argparse
import io
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
import sys
sys.path.insert(0, str(ROOT))
from tools.shared.project_paths import project_root
PROJECT = project_root()
ENV_ROOT = (PROJECT / "assets"
            / "environments" / "st_maria_town")
LANE_CENTRE = 3.8833

ASSETS = ("environment.obj", "environment.mtl", "environment.png",
          "collision.obj")


def main() -> None:
    parser = argparse.ArgumentParser(prog="install_room_3d")
    parser.add_argument("--export", type=Path, required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--destination", type=Path, default=None,
                        help="install here instead of the shipped "
                             "st_maria_town/<name> (use out/ for review)")
    args = parser.parse_args()

    manifest = json.loads((args.export / "environment.json").read_text("utf-8"))
    destination = args.destination or ENV_ROOT / args.name
    destination.mkdir(parents=True, exist_ok=True)

    copied = []
    for asset in ASSETS:
        source = args.export / asset
        if source.exists():
            shutil.copy2(source, destination / asset)
            copied.append(asset)

    min_x, min_y, min_z, max_x, max_y, max_z = manifest["bounds"]
    # The exporter records the centre it mirrored with; older exports predate
    # the field and were all Classic-width rooms.
    centre = manifest.get("laneCentre", LANE_CENTRE)
    # A reflection swaps which endpoint is the minimum.
    lo, hi = sorted((centre - min_y, centre - max_y))

    package = {
        "contractVersion": 1,
        "renderMesh": "environment.obj",
        "materialLibrary": "environment.mtl",
        "textureAtlas": "environment.png",
        "collisionMesh": ("collision.obj" if "collision.obj" in copied
                          else "environment.obj"),
        "bounds": [round(min_x, 4), round(lo, 4), round(min_z, 4),
                   round(max_x, 4), round(hi, 4), round(max_z, 4)],
        "anchors": {name: {"position": anchor["position"]}
                    for name, anchor in manifest["anchors"].items()},
        # Which .blend this room was baked from (#1269); the export records it.
        "provenance": {"sourceBlend": manifest["provenance"]["sourceBlend"]},
    }
    io.open(destination / "environment.json", "w",
            encoding="utf-8", newline="\n").write(
        json.dumps(package, indent=2) + "\n")

    stats = manifest.get("stats", {})
    print(f"{args.name}: {stats.get('triangleCount')} tris, "
          f"atlas {stats.get('textureDimensions')}, "
          f"lane Y {package['bounds'][1]}..{package['bounds'][4]}, "
          f"assets {copied}")


if __name__ == "__main__":
    main()
