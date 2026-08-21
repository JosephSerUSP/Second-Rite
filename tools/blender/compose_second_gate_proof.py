"""Compose native-size tracking/source-runtime evidence sheets."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw


def compose(paths, out_path, labels):
    images = [Image.open(path).convert("RGBA") for path in paths]
    width = sum(image.width for image in images)
    height = max(image.height for image in images) + 22
    sheet = Image.new("RGBA", (width, height), (12, 16, 22, 255))
    draw = ImageDraw.Draw(sheet)
    x = 0
    for image, label in zip(images, labels):
        sheet.paste(image, (x, 22))
        draw.text((x + 6, 4), label, fill=(235, 222, 184, 255))
        x += image.width
    sheet.save(out_path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    out = args.out_dir.resolve()
    compose(
        [out / "runtime_mesh_m96.png", out / "runtime_mesh_zero.png", out / "runtime_mesh_p96.png"],
        out / "runtime_tracking_mesh_strip.png",
        ["-96px", "0px", "+96px"],
    )
    compose(
        [out / "runtime_actors_m96.png", out / "runtime_actors_zero.png", out / "runtime_actors_p96.png"],
        out / "runtime_tracking_actors_strip.png",
        ["-96px + Walker", "0px + Walker", "+96px + Walker"],
    )
    compose(
        [out / "source_proof.png", out / "runtime_actors_zero.png"],
        out / "source_vs_runtime_center.png",
        ["TH_SOURCE", "TH_RENDER baked + preview"],
    )


if __name__ == "__main__":
    main()
