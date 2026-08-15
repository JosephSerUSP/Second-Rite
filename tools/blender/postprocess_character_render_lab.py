#!/usr/bin/env python3
"""Resolve oversampled character-lab renders into exact 24px sprite products.

Blender produces transparent 192x192 frames. This host-side step performs an
8x premultiplied-alpha Lanczos resolve, then emits representation-neutral sprite
sheets and enlarged nearest-neighbour inspection media.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageEnhance

FINAL = 24
DIRECTIONS = ("south", "east", "north", "west")
ACTION_ORDER = ("Idle", "Walk", "Talk")


def resolve_rgba(source: Path) -> Image.Image:
    image = Image.open(source).convert("RGBA")
    rgba = np.asarray(image, dtype=np.float32) / 255.0
    alpha = rgba[..., 3:4]
    premult = rgba[..., :3] * alpha

    rgb8 = np.clip(premult * 255.0 + 0.5, 0, 255).astype(np.uint8)
    a8 = np.clip(alpha[..., 0] * 255.0 + 0.5, 0, 255).astype(np.uint8)
    rgb_small = Image.fromarray(rgb8, "RGB").resize((FINAL, FINAL), Image.Resampling.LANCZOS)
    a_small = Image.fromarray(a8, "L").resize((FINAL, FINAL), Image.Resampling.LANCZOS)

    rgb = np.asarray(rgb_small, dtype=np.float32) / 255.0
    a = np.asarray(a_small, dtype=np.float32)[..., None] / 255.0
    unpremult = np.zeros_like(rgb)
    np.divide(rgb, np.maximum(a, 1.0 / 255.0), out=unpremult, where=a > (0.5 / 255.0))
    # A tiny local contrast lift is useful after an eightfold resolve, but keep
    # it deliberately subtle so this remains a renderer test rather than a
    # post-effect-driven sprite style.
    out = np.concatenate([np.clip(unpremult, 0, 1), a], axis=2)
    small = Image.fromarray(np.clip(out * 255.0 + 0.5, 0, 255).astype(np.uint8), "RGBA")
    rgb_only = ImageEnhance.Contrast(small.convert("RGB")).enhance(1.045)
    small = Image.merge("RGBA", (*rgb_only.split(), small.getchannel("A")))
    return small


def checker(size, cell=12):
    arr = np.zeros((size[1], size[0], 4), dtype=np.uint8)
    for y in range(size[1]):
        for x in range(size[0]):
            value = 34 if ((x // cell) + (y // cell)) % 2 == 0 else 47
            arr[y, x] = (value, value, value + 4, 255)
    return Image.fromarray(arr, "RGBA")


def inspection(sprite: Image.Image, scale=8):
    enlarged = sprite.resize((sprite.width * scale, sprite.height * scale), Image.Resampling.NEAREST)
    bg = checker(enlarged.size, max(4, scale * 2))
    bg.alpha_composite(enlarged)
    return bg.convert("RGB")


def transparent_sheet(frames, columns, rows):
    sheet = Image.new("RGBA", (columns * FINAL, rows * FINAL), (0, 0, 0, 0))
    for frame, x, y in frames:
        sheet.alpha_composite(frame, (x * FINAL, y * FINAL))
    return sheet


def save_gif(images, path, duration=105, scale=8):
    frames = []
    for image in images:
        if scale != 1:
            frame = inspection(image, scale=scale)
        else:
            frame = image.convert("RGBA")
        frames.append(frame)
    path.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        path,
        save_all=True,
        append_images=frames[1:],
        duration=duration,
        loop=0,
        disposal=2,
    )


def load_manifest(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "thestra.character-render-lab/v0":
        raise ValueError(f"unexpected manifest schema: {path}")
    return data


def resolve_character(render_root, review_root, manifest):
    char_id = manifest["characterId"]
    samples = manifest["samples"]
    resolved_root = review_root / "resolved" / char_id
    sheet_root = review_root / "spritesheets" / char_id
    gif_root = review_root / "gifs"
    resolved_root.mkdir(parents=True, exist_ok=True)
    sheet_root.mkdir(parents=True, exist_ok=True)

    resolved = {}
    for action in ACTION_ORDER:
        resolved[action] = {}
        for direction in DIRECTIONS:
            frames = []
            for frame in samples[action]:
                source = render_root / "raw" / char_id / action.lower() / direction / f"{frame:03d}.png"
                if not source.is_file():
                    raise FileNotFoundError(source)
                sprite = resolve_rgba(source)
                out = resolved_root / action.lower() / direction / f"{frame:03d}.png"
                out.parent.mkdir(parents=True, exist_ok=True)
                sprite.save(out)
                frames.append(sprite)
            resolved[action][direction] = frames

        columns = max(len(resolved[action][d]) for d in DIRECTIONS)
        entries = []
        for row, direction in enumerate(DIRECTIONS):
            for col, image in enumerate(resolved[action][direction]):
                entries.append((image, col, row))
        sheet = transparent_sheet(entries, columns, len(DIRECTIONS))
        sheet.save(sheet_root / f"{action.lower()}_4dir_24.png")
        inspection(sheet, scale=8).save(sheet_root / f"{action.lower()}_4dir_inspection.png")

    # Per-direction walk GIFs expose animation/facing without hiding native pixels.
    for direction in DIRECTIONS:
        save_gif(
            resolved["Walk"][direction],
            gif_root / f"{char_id}_walk_{direction}_24px.gif",
            duration=95,
            scale=8,
        )
        save_gif(
            resolved["Walk"][direction],
            gif_root / f"{char_id}_walk_{direction}_native_24px.gif",
            duration=95,
            scale=1,
        )
    save_gif(
        resolved["Talk"]["south"],
        gif_root / f"{char_id}_talk_south_24px.gif",
        duration=110,
        scale=8,
    )

    return resolved


def composite_reviews(review_root, all_resolved):
    ids = list(all_resolved)

    # Native 24px comparison and an enlarged inspection twin.
    comp = Image.new("RGBA", (FINAL * len(ids), FINAL), (0, 0, 0, 0))
    for col, char_id in enumerate(ids):
        comp.alpha_composite(all_resolved[char_id]["Idle"]["south"][0], (col * FINAL, 0))
    comp.save(review_root / "comparison_native_24px.png")
    inspection(comp, scale=8).save(review_root / "comparison_24px.png")

    # All four facings, one row per authored approach.
    facing = Image.new("RGBA", (FINAL * 4, FINAL * len(ids)), (0, 0, 0, 0))
    for row, char_id in enumerate(ids):
        for col, direction in enumerate(DIRECTIONS):
            facing.alpha_composite(all_resolved[char_id]["Idle"][direction][0], (col * FINAL, row * FINAL))
    facing.save(review_root / "direction_readability_native_24px.png")
    inspection(facing, scale=8).save(review_root / "direction_readability_24px.png")

    # Six south-facing walk samples, deliberately matching the original proof's
    # contact-sheet comparison while using the new Blender lighting pipeline.
    walk = Image.new("RGBA", (FINAL * 6, FINAL * len(ids)), (0, 0, 0, 0))
    for row, char_id in enumerate(ids):
        frames = all_resolved[char_id]["Walk"]["south"]
        for col, image in enumerate(frames[:6]):
            walk.alpha_composite(image, (col * FINAL, row * FINAL))
    walk.save(review_root / "walk_cycle_contact_sheet_native_24px.png")
    inspection(walk, scale=8).save(review_root / "walk_cycle_contact_sheet.png")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--render-root", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    render_root = Path(args.render_root).resolve()
    review_root = Path(args.out).resolve()
    review_root.mkdir(parents=True, exist_ok=True)

    manifests = sorted(render_root.glob("*.render-manifest.json"))
    if not manifests:
        raise SystemExit(f"no render manifests found in {render_root}")

    all_resolved = {}
    records = []
    for manifest_path in manifests:
        manifest = load_manifest(manifest_path)
        resolved = resolve_character(render_root, review_root, manifest)
        all_resolved[manifest["characterId"]] = resolved
        records.append({
            "characterId": manifest["characterId"],
            "sourceSha256": manifest["sourceSha256"],
            "sourceUnchanged": manifest["sourceUnchanged"],
            "realtime": manifest.get("realtime"),
            "actions": list(manifest["samples"]),
            "directions": list(DIRECTIONS),
        })

    composite_reviews(review_root, all_resolved)
    summary = {
        "schema": "thestra.character-render-lab-review/v0",
        "finalRaster": [FINAL, FINAL],
        "resolve": "8x premultiplied-alpha Lanczos",
        "characters": records,
    }
    (review_root / "manifest.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print("CHARACTER_LAB_POSTPROCESS " + json.dumps(summary, separators=(",", ":")))


if __name__ == "__main__":
    main()
