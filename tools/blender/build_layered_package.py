"""Assemble a `layered_2d` environment package from a rendered plate pair.

A pre-rendered room is two images drawn by the runtime around the live actor:
`background.png` (the complete plate) and `foreground.png` (a transparent
cutout of whatever the player walks behind, drawn after the actor). This tool
writes the package around them: the manifest, the placeholder mesh the
contract requires, and the player projection derived from the plate's own
camera record, so the two cannot disagree.

The camera record is the engine's (`presentation.world_camera_calibration`),
in ENGINE lane coordinates -- not the Blender-space copy the stager renders
from. Lane X on screen comes from the same perspective projection the runtime
uses to place the actor, so only the panning coefficient is fitted here.

    python tools/blender/build_layered_package.py \
        --background out/layers/background.png --foreground out/layers/foreground.png \
        --record out/camrec/plate_582.json --anchors out/church/export/environment.json \
        --source-blend st_maria_church.blend --output out/church/layered_pkg
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
from pathlib import Path

STUB_OBJ = ("# Placeholder geometry for a pre-rendered screen.\n"
            "# Nothing draws this; the manifest contract requires a mesh path.\n"
            "mtllib stub.mtl\no th_render_stub\n"
            "v -1 0 -1\nv 1 0 -1\nv 1 0 1\nv -1 0 1\n"
            "vt 0 0\nvt 1 0\nvt 1 1\nvt 0 1\n"
            "usemtl stub\nf 1/1 2/2 3/3 4/4\n")
STUB_MTL = "newmtl stub\nKd 1.000 1.000 1.000\nd 1.0\nillum 1\n"


def project(record, point):
    """Screen (x, y) of an engine-space world point; the runtime's own maths."""
    eye, o = record["eye"], record["orientation"]
    rx, ry, rz = (point[0] - eye["x"], point[1] - eye["y"], point[2] - eye["z"])
    depth = rx * o["forwardX"] + ry * o["forwardY"]
    horizontal = rx * o["rightX"] + ry * o["rightY"]
    cp, sp = math.cos(o["pitchRadians"]), math.sin(o["pitchRadians"])
    vertical = rz * cp + depth * sp
    depth = depth * cp - rz * sp
    tw, th = record["targetWidth"], record["targetHeight"]
    bw, bh = record["baseViewportWidth"], record["baseViewportHeight"]
    ndc_x = (2 * record["viewportCenterX"] / tw) - 1 + horizontal / (
        record["fovHalfX"] * depth) * record["projectionScale"]["x"] * (bw / tw)
    ndc_y = 1 - (2 * record["viewportCenterY"] / th) + vertical / (
        record["fovHalfY"] * depth) * record["projectionScale"]["y"] * (bh / th)
    return (ndc_x + 1) * tw / 2.0, (1 - ndc_y) * th / 2.0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--background", type=Path, required=True)
    parser.add_argument("--foreground", type=Path, required=True)
    parser.add_argument("--record", type=Path, required=True,
                        help="engine-space camera calibration record for the plate")
    parser.add_argument("--anchors", type=Path, required=True,
                        help="environment.json whose anchors to carry over")
    parser.add_argument("--source-blend", required=True)
    parser.add_argument("--lane", type=float, nargs=2, default=(0.0, 16.0),
                        metavar=("MIN_Y", "MAX_Y"))
    parser.add_argument("--slice-y", type=float, required=True,
                        help="lane Y at the plate's centre column")
    parser.add_argument("--depth-x", type=float, default=0.0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    from PIL import Image

    record = json.loads(args.record.read_text(encoding="utf-8"))
    width, height = record["targetWidth"], record["targetHeight"]
    for label, path in (("background", args.background), ("foreground", args.foreground)):
        size = Image.open(path).size
        if size != (width, height):
            raise SystemExit(f"{label} is {size}, the plate record is {(width, height)}")
    if Image.open(args.foreground).mode != "RGBA":
        raise SystemExit("the foreground must be RGBA with a transparent surround")

    anchors = json.loads(args.anchors.read_text(encoding="utf-8"))["anchors"]
    out = args.output
    if out.exists():
        raise SystemExit(f"{out} exists; write each package to a new directory")
    out.mkdir(parents=True)
    shutil.copyfile(args.background, out / "background.png")
    shutil.copyfile(args.foreground, out / "foreground.png")
    (out / "stub.obj").write_text(STUB_OBJ, encoding="utf-8", newline="\n")
    (out / "stub.mtl").write_text(STUB_MTL, encoding="utf-8", newline="\n")
    Image.new("RGBA", (4, 4), (255, 255, 255, 255)).save(out / "atlas.png")

    # Pan coefficient: least-squares px per lane metre across the walkable lane.
    steps = 33
    ys = [args.lane[0] + (args.lane[1] - args.lane[0]) * i / (steps - 1)
          for i in range(steps)]
    xs = [project(record, (args.depth_x, y, 0.0))[0] for y in ys]
    mean_y, mean_x = sum(ys) / steps, sum(xs) / steps
    slope = (sum((y - mean_y) * (x - mean_x) for y, x in zip(ys, xs))
             / sum((y - mean_y) ** 2 for y in ys))
    centre_x, feet_y = project(record, (args.depth_x, args.slice_y, 0.0))

    manifest = {
        "contractVersion": 1,
        "renderMesh": "stub.obj",
        "materialLibrary": "stub.mtl",
        "textureAtlas": "atlas.png",
        "collisionMesh": "stub.obj",
        "bounds": [args.depth_x - 2.0, args.lane[0], -0.35,
                   args.depth_x + 2.0, args.lane[1], 6.0],
        "bakedLighting": True,
        "provenance": {
            "sourceBlend": args.source_blend,
            "plateRecord": record,
        },
        "anchors": anchors,
        "preRendered": {
            "mode": "layered_2d",
            "cameraMode": "panning",
            "imageSize": [width, height],
            "slicePositions": [args.slice_y],
            "backgrounds": ["background.png"],
            "scenes": ["background.png"],
            "foregrounds": ["foreground.png"],
            "lane": {"runtimeCenterY": args.slice_y, "depthX": args.depth_x},
            "playerProjection": {
                "centerX": round(centre_x, 4),
                "screenY": round(feet_y, 4),
                "width": 24,
                "height": 48,
                "pixelsPerRuntimeY": round(slope, 6),
            },
        },
    }
    (out / "environment.json").write_text(json.dumps(manifest, indent=2) + "\n",
                                          encoding="utf-8", newline="\n")
    print(f"LAYERED PACKAGE OK {out} centerX={centre_x:.2f} screenY={feet_y:.2f} "
          f"px/m={slope:.4f}")


if __name__ == "__main__":
    sys.exit(main())
