"""Prepare non-destructive plate review packages.

The generator and map own the numbers; this tool only makes review artifacts:
the source-guide comparison, gameplay-anchor diagnostics, gameplay windows,
and the two overlapping guide crops used by the ImageGen authoring pass. It
never promotes a candidate into the Project.

    python tools/towngen/review_candidates.py guides --screen port
    python tools/towngen/review_candidates.py package --screen port \
        --candidates out/towngen/port/candidates \
        --out out/towngen/port/review
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import shutil
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))

from build_town import (EXPECTED_PLATE_WIDTHS, LEGACY_LANE_MARGIN_PX,
                        LEGACY_PIXELS_PER_Y, SCREENS, plate_pixel_x,
                        screen_lane, screen_scale)  # noqa: E402
from make_blockout import PLAYER_H, PLAYER_W, spec  # noqa: E402

WINDOWS = {"classic": 256, "wide": 426}
MODEL_GUIDE_WIDTH = 2160
MODEL_GUIDE_HEIGHT = 720
MODEL_GUIDE_ASPECT = MODEL_GUIDE_WIDTH / MODEL_GUIDE_HEIGHT

SEMANTIC_DESCRIPTIONS = {
    "west_quay": "clear walkable edge continuation to The Quay",
    "forge_door": "readable accessible entrance to the active forge",
    "smith_3d_door": "second readable accessible smithy entrance",
    "cortico_stair": "distinct upward route to the Cortico",
    "climb_churchyard": "distinct long exterior climb to the Churchyard",
}

SEMANTIC_GUIDE_LABELS = {
    "west_quay": "WALKABLE WEST EXIT",
    "forge_door": "ACTIVE FORGE ENTRANCE",
    "smith_3d_door": "SECOND SMITHY DOOR",
    "cortico_stair": "CORTICO UP ROUTE",
    "climb_churchyard": "LONG CHURCHYARD CLIMB",
}


def stitch_overlap(width: int) -> int:
    return (width * 22 + 99) // 100


def guide_crops(key: str, out: Path) -> None:
    s = spec(key)
    source = out.parent / "blockouts-reconciled" / f"{key}.png"
    if not source.exists():
        source = ROOT / "out" / "towngen" / "blockouts-reconciled" / f"{key}.png"
    if not source.exists():
        raise SystemExit(f"missing geometry guide: {source}")
    out.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as image:
        width = image.width
        # Use the same upward-rounded overlap as stitch(). Keeping this in the
        # guide manifest makes the crop contract reproducible at odd widths.
        overlap = stitch_overlap(width)
        crop_width = (width + overlap + 1) // 2
        image.crop((0, 0, crop_width, image.height)).save(out / "guide-west.png")
        image.crop((width - crop_width, 0, width, image.height)).save(out / "guide-east.png")
    (out / "guide.json").write_text(json.dumps({
        "screen": key,
        "width": s["plateWidth"],
        "height": s["visibleHeight"],
        "overlapPixels": overlap,
        "cropWidth": crop_width,
        "westBox": [0, 0, crop_width, s["visibleHeight"]],
        "eastBox": [width - crop_width, 0, width, s["visibleHeight"]],
        "instruction": "Placement marks are guide-only and must not appear in generated art.",
    }, indent=2) + "\n", encoding="utf-8")


def draw_overlay(key: str, image: Image.Image) -> Image.Image:
    s = spec(key)
    out = image.convert("RGBA").copy()
    d = ImageDraw.Draw(out, "RGBA")
    d.rectangle((0, s["visibleHeight"], out.width, out.height),
                fill=(88, 36, 120, 72))
    d.line((0, s["groundY"], out.width, s["groundY"]), fill=(255, 0, 96), width=2)
    d.line((0, s["horizonY"], out.width, s["horizonY"]),
           fill=(245, 220, 90), width=1)
    d.line((0, s["visibleHeight"], out.width, s["visibleHeight"]),
           fill=(188, 84, 255), width=2)
    d.text((4, max(1, s["horizonY"] - 11)), "HORIZON", fill=(245, 220, 90))
    d.text((4, s["visibleHeight"] + 4), "PERSISTENT UI", fill=(220, 170, 255))
    for opening in s["openings"]:
        x = round(opening["pixelX"])
        colour = (86, 156, 214) if opening["kind"] == "street" else (232, 126, 52)
        d.rectangle((x - PLAYER_W // 2, s["groundY"] - PLAYER_H,
                     x + PLAYER_W // 2, s["groundY"]), outline=colour, width=2)
        d.text((max(2, min(out.width - 90, x - 24)),
                max(1, s["groundY"] - PLAYER_H - 12)),
               opening["label"][:16], fill=colour)
    for npc in s["npcs"]:
        x = round(npc["pixelX"])
        d.rectangle((x - PLAYER_W // 2, s["groundY"] - PLAYER_H,
                     x + PLAYER_W // 2, s["groundY"]), outline=(60, 160, 110), width=2)
    for fraction in (0.2, 0.5, 0.8):
        x = round(out.width * fraction)
        d.rectangle((x - PLAYER_W // 2, s["groundY"] - PLAYER_H,
                     x + PLAYER_W // 2, s["groundY"]), outline=(255, 255, 255, 255), width=1)
    return out.convert("RGB")


def guide_source(key: str) -> Path:
    """Find the same perspective guide supplied to the image model."""
    map_id = spec(key)["mapId"]
    matches = sorted((ROOT / "out" / "town-guides").glob(f"{map_id}-*-guide.png"))
    if len(matches) != 1:
        raise SystemExit(
            f"expected one source guide for map {map_id}, found {len(matches)}")
    return matches[0]


def draw_guide_overlay(key: str, image: Image.Image, source: Path | None = None) -> Image.Image:
    """Overlay the fed perspective construction guide, without its gray field.

    This is the primary art review. The guide is resized only to the candidate
    plate's contract; its colored construction lines remain visible while the
    neutral guide background is made transparent. Gameplay boxes stay in a
    separate diagnostic so they cannot be mistaken for ImageGen input.
    """
    source = source or guide_source(key)
    with Image.open(source) as guide_image:
        guide = guide_image.convert("RGB").resize(image.size, Image.Resampling.LANCZOS)
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    source_pixels = guide.load()
    overlay_pixels = overlay.load()
    for y in range(guide.height):
        for x in range(guide.width):
            r, g, b = source_pixels[x, y]
            # The guide field is neutral gray (128,128,128). Preserve all
            # construction colours while suppressing that field.
            if max(r, g, b) - min(r, g, b) > 10 or max(r, g, b) - 128 > 12 or 128 - min(r, g, b) > 12:
                overlay_pixels[x, y] = (r, g, b, 170)
    return Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")


def package(key: str, candidates: Path, out: Path, guide: Path | None = None) -> None:
    s = spec(key)
    guide = guide.resolve() if guide else guide_source(key)
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for index in (1, 2, 3):
        source = candidates / f"candidate-{index}.png"
        if not source.exists():
            raise SystemExit(f"missing candidate {source}")
        with Image.open(source) as image:
            if image.size != (s["plateWidth"], s["visibleHeight"] + 96):
                raise SystemExit(
                    f"{source}: expected native plate {s['plateWidth']}x240; got {image.size}")
            image = image.convert("RGB")
            image.save(out / f"candidate-{index}-full.png")
            guide_overlay = draw_guide_overlay(key, image, guide)
            guide_overlay.save(out / f"candidate-{index}-guide-overlay.png")
            anchor_overlay = draw_overlay(key, image)
            anchor_overlay.save(out / f"candidate-{index}-anchor-overlay.png")
            windows = {}
            for label, width in WINDOWS.items():
                boxes = {}
                for position, left in (("west", 0), ("centre", (image.width - width) // 2),
                                       ("east", image.width - width)):
                    crop = image.crop((left, 0, left + width, image.height))
                    path = out / f"candidate-{index}-{label}-{position}.png"
                    crop.save(path)
                    boxes[position] = [left, 0, left + width, image.height]
                windows[label] = boxes
        rows.append({"candidate": index, "source": str(source),
                     "nativeSize": [s["plateWidth"], 240],
                     "stitch": {"west": f"candidate-{index}-west.png",
                                "east": f"candidate-{index}-east.png",
                                "overlapPixels": stitch_overlap(s["plateWidth"]),
                                "blend": "linear"},
                     "fullPreview": f"candidate-{index}-full.png",
                     "guideOverlay": f"candidate-{index}-guide-overlay.png",
                     "anchorOverlay": f"candidate-{index}-anchor-overlay.png",
                     "windows": windows,
                     "cleanup": {"status": "blocked",
                                 "instruction": "Remove people only after owner selects this candidate."}})
    # The primary sheet is the fed construction guide over the result. Keep
    # gameplay anchors in a secondary sheet so review never conflates the two.
    sheet = Image.new("RGB", (s["plateWidth"], 240 * 3 + 48), (18, 18, 24))
    anchor_sheet = Image.new("RGB", (s["plateWidth"], 240 * 3 + 48), (18, 18, 24))
    sheet_draw = ImageDraw.Draw(sheet)
    anchor_sheet_draw = ImageDraw.Draw(anchor_sheet)
    for index in (1, 2, 3):
        with Image.open(out / f"candidate-{index}-guide-overlay.png") as overlay:
            sheet.paste(overlay.convert("RGB"), (0, (index - 1) * 264 + 24))
        with Image.open(out / f"candidate-{index}-anchor-overlay.png") as overlay:
            anchor_sheet.paste(overlay.convert("RGB"), (0, (index - 1) * 264 + 24))
        sheet_draw.text((8, (index - 1) * 264 + 6), f"Port candidate {index} - source guide overlay", fill=(255, 255, 255))
        anchor_sheet_draw.text((8, (index - 1) * 264 + 6), f"Port candidate {index} - gameplay anchors", fill=(255, 255, 255))
    sheet.save(out / "candidate-contact-sheet.png")
    anchor_sheet.save(out / "candidate-contact-sheet-anchors.png")
    (out / "review.json").write_text(json.dumps({
        "screen": key,
        "mapId": s["mapId"],
        "plate": s["plate"],
        "dimensions": {"width": s["plateWidth"], "height": 240},
        "pixelsPerRuntimeY": s["pixelsPerLaneUnit"],
        "compositionMarginPx": s["compositionMarginPx"],
        "groundY": s["groundY"],
        "horizonY": s["horizonY"],
        "persistentUiBeginsY": s["visibleHeight"],
        "contactSheet": "candidate-contact-sheet.png",
        "guideSource": str(guide.relative_to(ROOT)) if guide.is_relative_to(ROOT) else str(guide),
        "anchorContactSheet": "candidate-contact-sheet-anchors.png",
        "candidates": rows,
        "promotion": "blocked until owner selects a candidate and confirms cleanup",
    }, indent=2) + "\n", encoding="utf-8")


def stitch(west: Path, east: Path, out: Path, width: int) -> None:
    """Stitch two generated guide crops with a deterministic linear blend."""
    overlap = stitch_overlap(width)
    crop_width = (width + overlap + 1) // 2
    with Image.open(west) as west_image, Image.open(east) as east_image:
        left = west_image.convert("RGB").resize((crop_width, 240), Image.Resampling.LANCZOS)
        right = east_image.convert("RGB").resize((crop_width, 240), Image.Resampling.LANCZOS)
        result = Image.new("RGB", (width, 240))
        result.paste(left, (0, 0))
        for x in range(overlap):
            alpha = x / float(max(1, overlap - 1))
            column = Image.blend(left.crop((crop_width - overlap + x, 0,
                                            crop_width - overlap + x + 1, 240)),
                                  right.crop((x, 0, x + 1, 240)), alpha)
            result.paste(column, (crop_width - overlap + x, 0))
        result.paste(right.crop((overlap, 0, crop_width, 240)),
                     (crop_width, 0))
        if result.size != (width, 240):
            raise SystemExit(f"stitch produced {result.size}, expected {(width, 240)}")
        out.parent.mkdir(parents=True, exist_ok=True)
        result.save(out)


def normalize(source: Path, out: Path, width: int, *,
              resampling=Image.Resampling.LANCZOS) -> None:
    """Normalize a single generated weather edit to the plate contract."""
    with Image.open(source) as image:
        result = image.convert("RGB").resize((width, 240), resampling)
        out.parent.mkdir(parents=True, exist_ok=True)
        result.save(out)


def calibrate_frame(key: str, source: Path, out: Path,
                    observed_ground_y: float, *,
                    observed_actor_height: float | None = None,
                    metadata_out: Path | None = None) -> None:
    """Fit a generated frame to the plate without changing its aspect ratio.

    The source is scaled to cover the target plate, then cropped.  The caller
    supplies the painted lane-contact row measured on the raw generation; that
    row is placed on the authored runtime foot line.  This keeps the 24x48
    runtime actor on the painted floor and makes the crop/framing decision
    explicit and reviewable rather than silently anisotropically resizing a
    miniature or floating scene.
    """
    s = spec(key)
    target_w, target_h = s["plateWidth"], 240
    with Image.open(source) as image:
        image = image.convert("RGB")
        source_w, source_h = image.size
        scale = max(target_w / source_w, target_h / source_h)
        scaled_w = max(target_w, round(source_w * scale))
        scaled_h = max(target_h, round(source_h * scale))
        scaled = image.resize((scaled_w, scaled_h), Image.Resampling.LANCZOS)

    scaled_ground = observed_ground_y * scale
    top = round(scaled_ground - s["groundY"])
    top = max(0, min(top, scaled_h - target_h))
    left = max(0, (scaled_w - target_w) // 2)
    result = scaled.crop((left, top, left + target_w, top + target_h))
    out.parent.mkdir(parents=True, exist_ok=True)
    result.save(out)
    record = {
        "screen": key,
        "source": str(source),
        "sourceSize": [source_w, source_h],
        "targetSize": [target_w, target_h],
        "scale": round(scale, 8),
        "scaledSize": [scaled_w, scaled_h],
        "crop": {"left": left, "top": top,
                 "right": left + target_w, "bottom": top + target_h},
        "observedGroundYSource": observed_ground_y,
        "authoredGroundYTarget": s["groundY"],
        "observedActorHeightSource": observed_actor_height,
        "actorHeightTarget": 48,
        "policy": "proportional cover fit plus crop; no extension, stitch, or anisotropic stretch",
    }
    if metadata_out is None:
        metadata_out = out.with_suffix(".json")
    metadata_out.parent.mkdir(parents=True, exist_ok=True)
    metadata_out.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")


def _parse_box(value: str) -> tuple[int, int, int, int]:
    try:
        x, y, width, height = (int(part) for part in value.split(","))
    except ValueError as exc:
        raise SystemExit("NPC box must be x,y,width,height") from exc
    if width < 8 or height < 12:
        raise SystemExit("NPC box is too small to measure a 24x48 actor")
    return x, y, width, height


def measure_npc(source: Path, box: tuple[int, int, int, int], out: Path,
                *, roi_measurement: bool = False) -> dict:
    """Segment one painted NPC in a bounded author-selected ROI.

    The ROI is the only human input: all dimensions are then found from the
    pixels.  GrabCut is deliberately constrained to that ROI so architecture,
    lamps, and doors cannot become a false actor measurement.
    """
    with Image.open(source) as image:
        rgb = np.asarray(image.convert("RGB"))
    height, width = rgb.shape[:2]
    x, y, box_w, box_h = box
    if x < 0 or y < 0 or x + box_w > width or y + box_h > height:
        raise SystemExit(f"NPC box {box} is outside {source} ({width}x{height})")
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    mask = np.full((height, width), cv2.GC_BGD, dtype=np.uint8)
    mask[y:y + box_h, x:x + box_w] = cv2.GC_PR_BGD
    # The centre of the bounded box is probable foreground.  The one-pixel
    # border stays probable background, which prevents the floor from joining
    # the person when the feet touch it.
    inset = max(2, min(box_w, box_h) // 8)
    mask[y + inset:y + box_h - inset, x + inset:x + box_w - inset] = cv2.GC_PR_FGD
    bgd = np.zeros((1, 65), np.float64)
    fgd = np.zeros((1, 65), np.float64)
    if not roi_measurement:
        cv2.grabCut(bgr, mask, (x, y, box_w, box_h), bgd, fgd, 5, cv2.GC_INIT_WITH_MASK)
    foreground = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
    # Keep the tallest plausible component in the bounded ROI.  A generated
    # NPC can be split into head/body/legs by the painterly background, so
    # centre-only selection can measure a face or shirt instead of the actor.
    # Conversely, components spanning most of the ROI are usually floor or a
    # wall and are excluded.
    components, labels, stats, centroids = cv2.connectedComponentsWithStats(foreground, 8)
    centre = (x + box_w / 2.0, y + box_h / 2.0)
    candidates = []
    for label in range(1, components):
        left, top, comp_w, comp_h, area = stats[label]
        cx, cy = centroids[label]
        if (area >= 8 and x <= cx <= x + box_w and y <= cy <= y + box_h
                and comp_h >= max(8, round(box_h * 0.25))
                and comp_h <= round(box_h * 0.95)
                and comp_w <= round(box_w * 0.90)):
            distance = (cx - centre[0]) ** 2 + (cy - centre[1]) ** 2
            candidates.append((-comp_h, -area, distance, label))
    if roi_measurement:
        ys, xs = np.mgrid[y:y + box_h, x:x + box_w]
    elif not candidates:
        # Last-resort bounded measurement: discard broad floor rows from the
        # GrabCut result, then measure the remaining silhouette pixels.  This
        # still derives the actor from image pixels and fails loudly if the ROI
        # contains no usable subject at all.
        bounded = foreground[y:y + box_h, x:x + box_w].copy()
        row_coverage = (bounded > 0).sum(axis=1)
        bounded[row_coverage >= box_w * 0.75, :] = 0
        ys_local, xs_local = np.where(bounded > 0)
        if len(xs_local) < 8:
            raise SystemExit(f"could not segment an NPC in {source} ROI {box}")
        xs, ys = xs_local + x, ys_local + y
    else:
        label = min(candidates)[3]
        ys, xs = np.where(labels == label)
    left, right = int(xs.min()), int(xs.max()) + 1
    top, bottom = int(ys.min()), int(ys.max()) + 1
    measured = {
        "source": str(source),
        "roi": [x, y, box_w, box_h],
        "bbox": [left, top, right - left, bottom - top],
        "feetY": bottom,
        "pixelArea": int((labels == label).sum()),
        "method": ("tight supplied NPC ROI; pixel bounds are the measurement"
                   if roi_measurement else
                   "OpenCV GrabCut constrained to the supplied NPC ROI; tallest plausible component"),
    }
    overlay = Image.fromarray(rgb).convert("RGBA")
    draw = ImageDraw.Draw(overlay, "RGBA")
    draw.rectangle((x, y, x + box_w, y + box_h), outline=(255, 210, 40, 255), width=2)
    draw.rectangle((left, top, right - 1, bottom - 1), outline=(70, 255, 120, 255), width=2)
    draw.line((0, bottom, width, bottom), fill=(70, 255, 120, 190), width=1)
    draw.text((x, max(0, y - 14)), f"ROI {box_w}x{box_h} / NPC {right-left}x{bottom-top}",
              fill=(255, 230, 80, 255))
    out.parent.mkdir(parents=True, exist_ok=True)
    overlay.convert("RGB").save(out)
    return measured


def calibrate_existing(key: str, source: Path, out: Path, npc_box: str,
                       metadata_out: Path | None = None,
                       measurement_out: Path | None = None,
                       target_actor_height: float = 48.0,
                       roi_measurement: bool = False,
                       npc_box_space: tuple[int, int] | None = None,
                       visual_ground_offset: float = 0.0) -> None:
    """Scale and translate an existing plate around a measured NPC's feet."""
    s = spec(key)
    box = _parse_box(npc_box)
    if npc_box_space is not None:
        with Image.open(source) as source_image:
            source_size = source_image.size
        space_w, space_h = npc_box_space
        if space_w <= 0 or space_h <= 0:
            raise SystemExit("NPC box space must be WIDTH,HEIGHT")
        sx, sy = source_size[0] / space_w, source_size[1] / space_h
        x, y, width, height = box
        box = (round(x * sx), round(y * sy),
               max(8, round(width * sx)), max(12, round(height * sy)))
    if measurement_out is None:
        measurement_out = out.with_name("npc-measurement.png")
    measurement = measure_npc(source, box, measurement_out,
                              roi_measurement=roi_measurement)
    actor_height = float(measurement["bbox"][3])
    if actor_height <= 0:
        raise SystemExit("measured NPC has no height")
    # Match the measured figure to the native runtime actor exactly.  If the
    # source figure is larger, shrinking is intentional; any resulting empty
    # border is preferable to leaving the actor oversized or the architecture
    # at a contradictory scale.
    scale = target_actor_height / actor_height
    with Image.open(source) as image:
        image = image.convert("RGB")
        source_w, source_h = image.size
        array = cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR)
    left, top, actor_w, actor_h = measurement["bbox"]
    actor_centre_x = left + actor_w / 2.0
    # When the ROI was authored in the staged plate space, retain that
    # semantic x location after measuring the raw source in its native space.
    # Using the raw pixel x here would place a wide-source subject outside the
    # final plate.
    input_box = _parse_box(npc_box)
    target_centre_x = (input_box[0] + input_box[2] / 2.0
                       if npc_box_space is not None else actor_centre_x)
    # Keep the observed NPC's feet on the authored runtime row.  The inverse
    # mapping naturally leaves empty lower pixels when the source scene is
    # translated upward; those pixels are intentionally not invented.
    matrix = np.array([
        [scale, 0.0, target_centre_x - scale * actor_centre_x],
        [0.0, scale, s["groundY"] + visual_ground_offset - scale * measurement["feetY"]],
    ], dtype=np.float32)
    result = cv2.warpAffine(array, matrix, (s["plateWidth"], 240),
                            flags=cv2.INTER_LANCZOS4,
                            borderMode=cv2.BORDER_CONSTANT,
                            borderValue=(0, 0, 0))
    out.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(cv2.cvtColor(result, cv2.COLOR_BGR2RGB)).save(out)
    record = {
        "screen": key,
        "source": str(source),
        "sourceSize": [source_w, source_h],
        "targetSize": [s["plateWidth"], 240],
        "measurement": measurement,
        "npcBoxInput": input_box,
        "npcBoxInputSpace": list(npc_box_space) if npc_box_space else None,
        "targetActorHeight": target_actor_height,
        "scale": round(scale, 8),
        "anchor": {"sourceNpcFeetY": measurement["feetY"],
                   "targetGroundY": s["groundY"],
                   "visualGroundY": round(s["groundY"] + visual_ground_offset, 3),
                   "sourceNpcCentreX": round(actor_centre_x, 3),
                   "targetNpcCentreX": round(target_centre_x, 3)},
        "visualGroundOffsetPx": visual_ground_offset,
        "policy": "screen-specific raw-only scale and visual ground translation; no pixel extension; empty border permitted",
    }
    if metadata_out is None:
        metadata_out = out.with_suffix(".json")
    metadata_out.parent.mkdir(parents=True, exist_ok=True)
    metadata_out.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")


def calibrate_existing_multi(key: str, source: Path, out: Path,
                             npc_boxes: list[str],
                             npc_box_space: tuple[int, int] | None = None,
                             metadata_out: Path | None = None,
                             measurement_dir: Path | None = None,
                             target_actor_height: float = 48.0,
                             roi_measurement: bool = False) -> None:
    """Calibrate from the median of several actor measurements."""
    if len(npc_boxes) < 2:
        raise SystemExit("multi calibration needs at least two --npc-box values")
    measurements = []
    if measurement_dir is None:
        measurement_dir = out.parent / "calibration" / "multi-measurements"
    for index, value in enumerate(npc_boxes, 1):
        overlay = measurement_dir / f"npc-{index:02d}.png"
        box = _parse_box(value)
        if npc_box_space is not None:
            with Image.open(source) as source_image:
                sw, sh = source_image.size
            sx, sy = sw / npc_box_space[0], sh / npc_box_space[1]
            box = (round(box[0] * sx), round(box[1] * sy),
                   max(8, round(box[2] * sx)), max(12, round(box[3] * sy)))
        measurements.append(measure_npc(source, box, overlay,
                                        roi_measurement=roi_measurement))
    heights = sorted(float(m["bbox"][3]) for m in measurements)
    feet = sorted(float(m["feetY"]) for m in measurements)
    median_height = float(np.median(heights))
    median_feet = float(np.median(feet))
    target_box = _parse_box(npc_boxes[len(npc_boxes) // 2])
    target_x = target_box[0] + target_box[2] / 2.0
    s = spec(key)
    scale = target_actor_height / median_height
    with Image.open(source) as image:
        source_w, source_h = image.size
        array = cv2.cvtColor(np.asarray(image.convert("RGB")), cv2.COLOR_RGB2BGR)
    source_centre_x = measurements[len(measurements) // 2]["bbox"][0] + measurements[len(measurements) // 2]["bbox"][2] / 2.0
    matrix = np.array([[scale, 0.0, target_x - scale * source_centre_x],
                       [0.0, scale, s["groundY"] - scale * median_feet]], dtype=np.float32)
    result = cv2.warpAffine(array, matrix, (s["plateWidth"], 240),
                            flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_CONSTANT,
                            borderValue=(0, 0, 0))
    out.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(cv2.cvtColor(result, cv2.COLOR_BGR2RGB)).save(out)
    if metadata_out is None:
        metadata_out = out.with_suffix(".json")
    metadata_out.parent.mkdir(parents=True, exist_ok=True)
    metadata_out.write_text(json.dumps({
        "screen": key, "source": str(source), "sourceSize": [source_w, source_h],
        "targetSize": [s["plateWidth"], 240], "measurements": measurements,
        "medianActorHeightSource": median_height, "medianFeetYSource": median_feet,
        "targetActorHeight": target_actor_height, "scale": round(scale, 8),
        "targetActorCentreX": target_x,
        "policy": ("uniform raw-frame scale anchored to median detector person feet; "
                   "no pixels erased" if roi_measurement else
                   "uniform raw-frame scale anchored to median actor feet; no pixels erased"),
    }, indent=2) + "\n", encoding="utf-8")


def estimate_painted_floor(source: Path, analysis_out: Path,
                           source_y_range: tuple[int, int] | None = None) -> dict:
    """Estimate a floor contact row from image evidence, independent of actors."""
    with Image.open(source) as image:
        rgb = np.asarray(image.convert("RGB"))
    h, w = rgb.shape[:2]
    lo, hi = source_y_range or (round(h * 0.48), round(h * 0.82))
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)
    vertical = np.abs(np.diff(gray, axis=0))
    # Use broad unobstructed bands and a trimmed row statistic. This favours
    # the wall/floor and floor-plane transition while rejecting person-sized
    # vertical edges and isolated furniture.
    bands = [(round(w * a), round(w * b)) for a, b in
             ((0.05, 0.22), (0.28, 0.43), (0.57, 0.72), (0.78, 0.95))]
    candidates = []
    for x0, x1 in bands:
        scores = []
        for y in range(max(1, lo), min(h - 2, hi)):
            row = vertical[y - 1:y + 2, x0:x1].reshape(-1)
            scores.append((float(np.percentile(row, 75) + np.median(row)), y))
        scores.sort(reverse=True)
        candidates.append({"band": [x0, x1], "row": scores[0][1],
                           "score": round(scores[0][0], 4)})
    rows = np.array([item["row"] for item in candidates], dtype=np.float32)
    centres = np.array([(item["band"][0] + item["band"][1]) / 2
                        for item in candidates], dtype=np.float32)
    coefficients = np.polyfit(centres, rows, 1)
    fitted = np.polyval(coefficients, centres)
    floor_y = float(np.polyval(coefficients, w / 2.0))
    residual = float(np.max(np.abs(rows - fitted)))
    overlay = Image.fromarray(rgb).convert("RGB")
    draw = ImageDraw.Draw(overlay)
    for item in candidates:
        x0, x1 = item["band"]
        draw.rectangle((x0, lo, x1, hi), outline=(80, 180, 255), width=2)
        draw.line((x0, item["row"], x1, item["row"]), fill=(80, 255, 180), width=2)
    draw.line((0, round(np.polyval(coefficients, 0)),
               w, round(np.polyval(coefficients, w))), fill=(255, 80, 80), width=3)
    analysis_out.parent.mkdir(parents=True, exist_ok=True)
    overlay.save(analysis_out)
    return {"source": str(source), "sourceSize": [w, h],
            "bands": candidates, "floorModel": [round(float(v), 8) for v in coefficients],
            "floorYAtSourceCentre": round(floor_y, 3),
            "residualPx": round(residual, 3),
            "method": "trimmed multi-band vertical-gradient floor transition"}


def calibrate_floor_aware(key: str, source: Path, out: Path, npc_box: str,
                          npc_box_space: tuple[int, int],
                          floor_metadata: Path, metadata_out: Path,
                          measurement_out: Path) -> None:
    """Apply scale from a human and Y from an independent floor profile."""
    s = spec(key)
    floor = json.loads(floor_metadata.read_text(encoding="utf-8"))
    residual = float(floor["residualPx"])
    if residual > 24:
        raise SystemExit(f"floor evidence residual {residual:.2f}px is too high for {key}")
    box = _parse_box(npc_box)
    with Image.open(source) as source_image:
        sw, sh = source_image.size
    sx, sy = sw / npc_box_space[0], sh / npc_box_space[1]
    source_box = (round(box[0] * sx), round(box[1] * sy),
                  max(8, round(box[2] * sx)), max(12, round(box[3] * sy)))
    measurement = measure_npc(source, source_box, measurement_out,
                              roi_measurement=True)
    scale = 48.0 / float(measurement["bbox"][3])
    left, top, actor_w, actor_h = measurement["bbox"]
    actor_centre_x = left + actor_w / 2.0
    target_centre_x = box[0] + box[2] / 2.0
    slope, intercept = floor["floorModel"]
    floor_y = slope * (sw / 2.0) + intercept
    translate_y = s["groundY"] - scale * floor_y
    matrix = np.array([[scale, 0.0, target_centre_x - scale * actor_centre_x],
                       [0.0, scale, translate_y]], dtype=np.float32)
    with Image.open(source) as image:
        array = cv2.cvtColor(np.asarray(image.convert("RGB")), cv2.COLOR_RGB2BGR)
    result = cv2.warpAffine(array, matrix, (s["plateWidth"], 240),
                            flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_CONSTANT,
                            borderValue=(0, 0, 0))
    out.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(cv2.cvtColor(result, cv2.COLOR_BGR2RGB)).save(out)
    metadata_out.parent.mkdir(parents=True, exist_ok=True)
    metadata_out.write_text(json.dumps({
        "screen": key, "source": str(source), "sourceSize": [sw, sh],
        "targetSize": [s["plateWidth"], 240], "actorMeasurement": measurement,
        "scale": round(scale, 8), "floor": floor,
        "floorYAtSourceCentre": round(floor_y, 3),
        "translateY": round(float(translate_y), 3),
        "targetGroundY": s["groundY"],
        "policy": "one-pass raw-only isotropic transform; actor scale and floor Y independently measured",
    }, indent=2) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def calibrate_annotated(key: str, source: Path, annotation: Path,
                        out: Path, metadata_out: Path, review_out: Path) -> None:
    """Calibrate a raw plate from reviewed, source-space evidence.

    The annotation is deliberately explicit: floor support samples are not
    inferred from gradients or from NPC feet.  This makes a bad annotation
    visible in review and prevents another accidental all-screen offset pass.
    Only the immutable raw generation is read as image input.
    """
    s = spec(key)
    with Image.open(source) as image:
        rgb = np.asarray(image.convert("RGB"))
    source_h, source_w = rgb.shape[:2]
    ann = json.loads(annotation.read_text(encoding="utf-8"))
    if ann.get("screen") != key or ann.get("sourceSize") != [source_w, source_h]:
        raise SystemExit(f"{annotation}: screen/sourceSize does not match {key} {source_w}x{source_h}")
    expected_hash = ann.get("sourceSha256")
    actual_hash = _sha256(source)
    if expected_hash and expected_hash != actual_hash:
        raise SystemExit(f"{source}: annotation sourceSha256 mismatch")
    support = ann.get("floorSupport", [])
    if len(support) < 3:
        raise SystemExit(f"{annotation}: at least three independent floor support samples are required")
    points = np.asarray([[float(p[0]), float(p[1])] for p in support], dtype=np.float64)
    if np.any(points[:, 0] < 0) or np.any(points[:, 0] >= source_w) or np.any(points[:, 1] < 0) or np.any(points[:, 1] >= source_h):
        raise SystemExit(f"{annotation}: floor support sample is outside the raw image")
    # A reviewed support profile may be sloped in the source.  Runtime ground
    # is a fixed horizontal row, so use the profile's centre value as the sole
    # vertical anchor and record the residual for human review.
    floor_model = np.polyfit(points[:, 0], points[:, 1], 1)
    fitted = np.polyval(floor_model, points[:, 0])
    residuals = np.abs(points[:, 1] - fitted)
    floor_source_y = float(np.polyval(floor_model, source_w / 2.0))
    if float(np.max(residuals)) > float(ann.get("maxFloorResidualPx", 18)):
        raise SystemExit(f"{key}: reviewed floor support residual {float(np.max(residuals)):.2f}px exceeds annotation limit")

    actor_records = []
    measurement_dir = review_out / "actor-measurements"
    for index, raw_box in enumerate(ann.get("actors", []), 1):
        box = tuple(int(v) for v in raw_box)
        if len(box) != 4:
            raise SystemExit(f"{annotation}: actor box {index} must be x,y,width,height")
        measurement = measure_npc(source, box, measurement_dir / f"actor-{index}.png", roi_measurement=True)
        actor_records.append(measurement)
    if len(actor_records) < 3:
        raise SystemExit(f"{annotation}: at least three reviewed baked actors are required")
    heights = np.asarray([m["bbox"][3] for m in actor_records], dtype=np.float64)
    median_height = float(np.median(heights))
    mad = float(np.median(np.abs(heights - median_height)))
    if median_height <= 0 or mad > median_height * 0.25:
        raise SystemExit(f"{key}: actor measurements disagree too much ({heights.tolist()})")
    target_actor_height = float(ann.get("targetActorHeight", 48.0))
    scale = target_actor_height / median_height
    target_x = float(ann.get("targetCentreX", s["plateWidth"] / 2.0))
    source_actor_centre = float(np.median([m["bbox"][0] + m["bbox"][2] / 2.0 for m in actor_records]))
    # This is a plate-only visual correction.  The runtime actor still uses
    # the authored ground row; the annotation may place the painted surface a
    # few pixels lower when the raw scene's contact texture proves to sit
    # below the nominal lane.
    visual_ground_y = float(s["groundY"] + ann.get("visualGroundOffsetPx", 0.0))
    matrix = np.array([[scale, 0.0, target_x - scale * source_actor_centre],
                       [0.0, scale, visual_ground_y - scale * floor_source_y]], dtype=np.float32)
    result = cv2.warpAffine(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), matrix,
                            (s["plateWidth"], s["visibleHeight"]),
                            flags=cv2.INTER_LANCZOS4,
                            borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0))
    out.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(cv2.cvtColor(result, cv2.COLOR_BGR2RGB)).save(out)

    overlay = Image.fromarray(rgb).convert("RGBA")
    d = ImageDraw.Draw(overlay, "RGBA")
    for x, y in support:
        d.ellipse((x - 7, y - 7, x + 7, y + 7), fill=(60, 220, 255, 220), outline=(255, 255, 255, 255))
    x0, x1 = 0, source_w
    d.line((x0, int(np.polyval(floor_model, x0)), x1, int(np.polyval(floor_model, x1))), fill=(40, 220, 255, 255), width=4)
    d.text((8, 8), f"REVIEWED FLOOR SUPPORT / raw y={floor_source_y:.1f}", fill=(60, 220, 255, 255))
    review_out.mkdir(parents=True, exist_ok=True)
    overlay.convert("RGB").save(review_out / "floor-support-overlay.png")
    review_calibrated(key, out, review_out / "gameplay")
    record = {
        "screen": key, "source": str(source), "sourceSha256": actual_hash,
        "annotation": str(annotation), "annotationSha256": _sha256(annotation),
        "sourceSize": [source_w, source_h], "targetSize": [s["plateWidth"], s["visibleHeight"]],
        "actors": actor_records, "medianActorHeightSource": median_height,
        "actorMadSource": mad, "targetActorHeight": target_actor_height,
        "floorSupport": [[round(float(x), 3), round(float(y), 3)] for x, y in points.tolist()],
        "floorModel": [round(float(v), 8) for v in floor_model],
        "floorYAtSourceCentre": round(floor_source_y, 3),
        "floorResidualMaxPx": round(float(np.max(residuals)), 3),
        "scale": round(float(scale), 8), "matrix": matrix.tolist(),
        "targetGroundY": s["groundY"], "visualGroundY": round(visual_ground_y, 3),
        "policy": "raw-only similarity calibration; scale from three-plus baked actors; Y from reviewed floor support; empty border permitted",
        "promotion": "blocked until human review of floor-support-overlay and gameplay windows",
    }
    metadata_out.parent.mkdir(parents=True, exist_ok=True)
    metadata_out.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")


def calibrate_v2(key: str, source: Path, annotation: Path,
                 out: Path, metadata_out: Path, review_out: Path) -> None:
    """Rebuild a plate from immutable raw art using paired, reviewed evidence.

    Unlike the historical detector pass this never measures a promoted plate,
    never treats every silhouette as a 48px actor, and never derives Y from a
    separate height median and feet median.  The annotation supplies identity-
    normalized actor observations and source/target portal pairs; the single
    isotropic transform is solved from those paired observations.
    """
    s = spec(key)
    ann = json.loads(annotation.read_text(encoding="utf-8"))
    with Image.open(source) as image:
        rgb = np.asarray(image.convert("RGB"))
    sh, sw = rgb.shape[:2]
    if ann.get("screen") != key or ann.get("sourceSize") != [sw, sh]:
        raise SystemExit(f"{annotation}: source identity does not match {key} {sw}x{sh}")
    actual_hash = _sha256(source)
    if ann.get("sourceSha256") != actual_hash:
        raise SystemExit(f"{source}: v2 annotation must bind the immutable raw sha256")
    refs = [r for r in ann.get("actorRefs", []) if r.get("eligible", True)]
    if not refs:
        raise SystemExit(f"{annotation}: no eligible same-plane actor references")
    ratios = []
    ref_records = []
    for i, ref in enumerate(refs, 1):
        h = float(ref["sourceVisibleHeight"])
        target_h = float(ref["targetVisibleHeight"])
        feet = float(ref["feetY"])
        if h <= 0 or target_h <= 0 or not 0 <= feet <= sh:
            raise SystemExit(f"{annotation}: invalid actor ref {i}")
        ratios.append(target_h / h)
        ref_records.append({**ref, "ratio": target_h / h})
    # Same-plane references are identity-normalized before aggregation.  A
    # single strong reference is allowed; mixed-depth outliers are excluded in
    # the annotation rather than silently averaged here.
    scale = float(np.median(np.asarray(ratios, dtype=np.float64)))
    ratio_mad = float(np.median(np.abs(np.asarray(ratios) - scale)))
    max_mad = float(ann.get("maxScaleMad", max(scale * 0.08, 0.002)))
    if ratio_mad > max_mad:
        raise SystemExit(f"{key}: eligible identity-normalized refs disagree: {ratios}")

    supports = ann.get("floorSupports", [])
    if len(supports) < 2:
        raise SystemExit(f"{annotation}: at least two reviewed floor supports are required")
    floor_points = np.asarray([[float(p[0]), float(p[1])] for p in supports], dtype=np.float64)
    if np.any(floor_points[:, 0] < 0) or np.any(floor_points[:, 0] >= sw) or np.any(floor_points[:, 1] < 0) or np.any(floor_points[:, 1] >= sh):
        raise SystemExit(f"{annotation}: floor support outside raw image")
    floor_model = np.polyfit(floor_points[:, 0], floor_points[:, 1], 1)
    floor_source_y = float(np.polyval(floor_model, sw / 2.0))
    floor_residuals = np.abs(floor_points[:, 1] - np.polyval(floor_model, floor_points[:, 0]))
    if float(np.max(floor_residuals)) > float(ann.get("maxFloorResidualPx", 30)):
        raise SystemExit(f"{key}: floor support residual too large")

    # X is tied to authored openings, not whichever person happened to be
    # detected first.  Multiple pairs are least-squares averaged.
    x_pairs = [(float(p["sourceX"]), float(p["targetX"])) for p in ann.get("portalPairs", [])]
    if not x_pairs:
        x_pairs = [(sw / 2.0, s["plateWidth"] / 2.0)]
    tx = float(np.mean([target - scale * source_x for source_x, target in x_pairs]))
    x_residuals = [target - (scale * source_x + tx) for source_x, target in x_pairs]
    ground_y = float(ann.get("targetGroundY", s["groundY"]))
    ty = ground_y - scale * floor_source_y
    matrix = np.array([[scale, 0.0, tx], [0.0, scale, ty]], dtype=np.float32)
    result = cv2.warpAffine(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), matrix,
                            (s["plateWidth"], s["visibleHeight"]),
                            flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_CONSTANT,
                            borderValue=(0, 0, 0))
    out.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(cv2.cvtColor(result, cv2.COLOR_BGR2RGB)).save(out)

    review_out.mkdir(parents=True, exist_ok=True)
    overlay = Image.fromarray(rgb).convert("RGBA")
    d = ImageDraw.Draw(overlay, "RGBA")
    d.line((0, int(np.polyval(floor_model, 0)), sw,
            int(np.polyval(floor_model, sw))), fill=(255, 70, 220, 255), width=5)
    for ref in ann.get("actorRefs", []):
        x, y, w, h = [int(v) for v in ref["box"]]
        colour = (40, 230, 110, 255) if ref.get("eligible", True) else (230, 80, 80, 210)
        d.rectangle((x, y, x + w, y + h), outline=colour, width=4)
        d.line((x, int(ref["feetY"]), x + w, int(ref["feetY"])), fill=colour, width=2)
        d.text((x, max(0, y - 16)), ref.get("id", "ref"), fill=colour)
    for p in ann.get("portalPairs", []):
        x, y = int(p["sourceX"]), int(p.get("sourceY", floor_source_y))
        d.line((x - 12, y, x + 12, y), fill=(50, 170, 255, 255), width=3)
        d.line((x, y - 12, x, y + 12), fill=(50, 170, 255, 255), width=3)
        d.text((x + 5, y - 22), p.get("label", "portal"), fill=(50, 170, 255, 255))
    overlay.convert("RGB").save(review_out / "raw-v2-evidence-overlay.png")
    review_calibrated(key, out, review_out / "gameplay")
    record = {
        "screen": key, "source": str(source), "sourceSha256": actual_hash,
        "annotation": str(annotation), "annotationSha256": _sha256(annotation),
        "sourceSize": [sw, sh], "targetSize": [s["plateWidth"], s["visibleHeight"]],
        "scale": round(scale, 8), "scaleRatios": [round(v, 8) for v in ratios],
        "scaleMad": round(ratio_mad, 8), "actorRefs": ref_records,
        "excludedRefs": [r for r in ann.get("actorRefs", []) if not r.get("eligible", True)],
        "floorSupports": supports, "floorModel": [round(float(v), 8) for v in floor_model],
        "floorYAtSourceCentre": round(floor_source_y, 3),
        "floorResidualMaxPx": round(float(np.max(floor_residuals)), 3),
        "portalPairs": ann.get("portalPairs", []),
        "portalResidualsPx": [round(float(v), 3) for v in x_residuals],
        "targetGroundY": ground_y, "matrix": matrix.tolist(),
        "policy": "v2 raw-only identity-normalized scale; paired floor anchor; portal-constrained X; black border permitted",
    }
    metadata_out.parent.mkdir(parents=True, exist_ok=True)
    metadata_out.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")


def review_calibrated(key: str, source: Path, out: Path) -> None:
    """Emit the human-facing gameplay windows for a calibrated plate."""
    s = spec(key)
    with Image.open(source) as image:
        image = image.convert("RGB")
    out.mkdir(parents=True, exist_ok=True)
    draw_overlay(key, image).save(out / "review-anchor-ground-lane.png")
    windows = {}
    for label, window_width in WINDOWS.items():
        windows[label] = {}
        for position, left in (("west", 0),
                               ("centre", (image.width - window_width) // 2),
                               ("east", image.width - window_width)):
            crop = image.crop((left, 0, left + window_width, image.height))
            filename = f"review-{label}-{position}.png"
            crop.save(out / filename)
            windows[label][position] = {"file": filename,
                                        "sourceX": [left, left + window_width]}
    (out / "review.json").write_text(json.dumps({
        "screen": key,
        "source": str(source),
        "dimensions": [s["plateWidth"], 240],
        "horizonY": s["horizonY"],
        "groundY": s["groundY"],
        "persistentUiBeginsY": s["visibleHeight"],
        "actor": {"width": PLAYER_W, "height": PLAYER_H,
                  "feetRow": s["groundY"]},
        "windows": windows,
    }, indent=2) + "\n", encoding="utf-8")


def remove_baked_figures(source: Path, out: Path, boxes: list[str],
                         metadata_out: Path | None = None) -> None:
    """Remove explicitly bounded people from a plate via local inpainting."""
    with Image.open(source) as image:
        rgb = np.asarray(image.convert("RGB"))
    height, width = rgb.shape[:2]
    mask = np.zeros((height, width), dtype=np.uint8)
    parsed = []
    for value in boxes:
        x, y, box_w, box_h = _parse_box(value)
        if x < 0 or y < 0 or x + box_w > width or y + box_h > height:
            raise SystemExit(f"figure box {(x, y, box_w, box_h)} is outside {source} ({width}x{height})")
        parsed.append([x, y, box_w, box_h])
        local = np.full((box_h, box_w), cv2.GC_BGD, dtype=np.uint8)
        inset = max(3, min(box_w, box_h) // 8)
        local[inset:box_h - inset, inset:box_w - inset] = cv2.GC_PR_FGD
        local_bgr = cv2.cvtColor(rgb[y:y + box_h, x:x + box_w], cv2.COLOR_RGB2BGR)
        bgd = np.zeros((1, 65), np.float64)
        fgd = np.zeros((1, 65), np.float64)
        cv2.grabCut(local_bgr, local, None, bgd, fgd, 5, cv2.GC_INIT_WITH_MASK)
        subject = ((local == cv2.GC_FGD) | (local == cv2.GC_PR_FGD)).astype(np.uint8) * 255
        mask[y:y + box_h, x:x + box_w] = np.maximum(
            mask[y:y + box_h, x:x + box_w], subject)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    mask = cv2.dilate(mask, kernel, iterations=1)
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    cleaned = cv2.inpaint(bgr, mask, 5, cv2.INPAINT_TELEA)
    out.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(cv2.cvtColor(cleaned, cv2.COLOR_BGR2RGB)).save(out)
    if metadata_out is None:
        metadata_out = out.with_suffix(".json")
    metadata_out.parent.mkdir(parents=True, exist_ok=True)
    metadata_out.write_text(json.dumps({
        "source": str(source), "output": str(out), "boxes": parsed,
        "dilationPx": 3, "method": "explicit ROI GrabCut masks plus Telea inpainting",
        "policy": "background-only cleanup; runtime semantics unchanged",
    }, indent=2) + "\n", encoding="utf-8")


def derive_working_guide(source: Path, out: Path,
                         width: int = MODEL_GUIDE_WIDTH,
                         height: int = MODEL_GUIDE_HEIGHT) -> None:
    """Compress a finished plate-frame guide to the model's output aspect."""
    if width <= height:
        raise SystemExit(
            f"model-facing guide must be landscape, got {width}x{height}")
    with Image.open(source) as image:
        result = image.convert("RGB").resize(
            (width, height), Image.Resampling.LANCZOS)
    out.parent.mkdir(parents=True, exist_ok=True)
    result.save(out)


def blender_spatial_overlay(key: str, source: Path, out: Path) -> None:
    """Add compact semantics after deriving the model-facing aspect.

    The coloured Blender primitives remain the primary spatial language. Text
    names events without adding architectural or route geometry.
    """
    s = spec(key)
    with Image.open(source) as image:
        guide = image.convert("RGB")
    plate_aspect = s["plateWidth"] / 240.0
    model_aspect = MODEL_GUIDE_ASPECT
    actual_aspect = guide.width / float(guide.height)
    if min(abs(actual_aspect - plate_aspect) / plate_aspect,
           abs(actual_aspect - model_aspect) / model_aspect) > 0.002:
        raise SystemExit(
            f"{source}: aspect {actual_aspect:.6f} is neither final plate "
            f"{plate_aspect:.6f} nor model-facing landscape "
            f"{model_aspect:.6f}")

    d = ImageDraw.Draw(guide, "RGBA")
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 13)
        small_font = ImageFont.truetype("DejaVuSans.ttf", 11)
    except OSError:
        font = ImageFont.load_default()
        small_font = font
    sx = guide.width / float(s["plateWidth"])
    sy = guide.height / 240.0
    horizon_y = round(s["horizonY"] * sy)
    ground_y = round(s["groundY"] * sy)
    ui_y = round(s["visibleHeight"] * sy)
    colours = {
        "street": (55, 170, 255, 255),
        "door": (255, 76, 62, 255),
        "route": (255, 184, 48, 255),
    }
    d.rectangle((0, 0, guide.width, 22), fill=(18, 18, 22, 220))
    d.text((5, 3), "SEMANTIC SPATIAL GUIDE - IDENTICAL PRISMS MARK TRIGGER ORIGINS, NOT ROUTE SHAPES",
           fill=(238, 238, 238, 255), font=font)

    for index, opening in enumerate(s["openings"]):
        x = round(opening["pixelX"] * sx)
        semantic_kind = ("street" if opening["kind"] == "street" else
                         "route" if opening["anchor"] in
                         ("cortico_stair", "climb_churchyard") else "door")
        colour = colours[semantic_kind]
        # Opening labels are authored in the map/environment contract.  Keep
        # the guide generic so every screen's event vocabulary is preserved
        # without maintaining a second hand-written anchor list here.
        label = opening["label"].upper()
        bbox = d.textbbox((0, 0), label, font=font)
        label_width = bbox[2] - bbox[0]
        label_y = ground_y - 118 + (index % 2) * 26
        label_x = max(3, min(guide.width - label_width - 7,
                             x - label_width // 2))
        d.rectangle((label_x - 2, label_y - 1,
                     label_x + label_width + 2, label_y + 16),
                    fill=(20, 20, 24, 190))
        d.text((label_x, label_y), label, fill=colour, font=font)
        d.line((x, label_y + 17, x, ground_y - max(3, round(4 * sy))),
               fill=(*colour[:3], 135), width=1)

    # The player proxy is a scale contract, not proposed architecture.  Put
    # three identical 24x48 proxies on the authored lane so the model and the
    # reviewer can judge scale at west/centre/east without another visual
    # input or a screen-specific silhouette.
    proxy_w = max(2, round(24 * sx))
    proxy_h = max(2, round(48 * sy))
    for frac in (0.2, 0.5, 0.8):
        px = round(guide.width * frac)
        d.rectangle((px - proxy_w // 2, ground_y - proxy_h,
                     px + proxy_w // 2, ground_y),
                    outline=(226, 70, 200, 255), width=max(2, round(sy)))
    d.text((8, max(26, ground_y - proxy_h - 20)),
           "MAGENTA PROXIES = RUNTIME ACTOR 24x48",
           fill=(226, 70, 200, 255))

    d.line((0, horizon_y, guide.width, horizon_y),
           fill=(255, 220, 70, 150), width=1)
    d.line((0, ground_y, guide.width, ground_y),
           fill=(245, 245, 245, 165), width=1)
    d.line((0, ui_y, guide.width, ui_y),
           fill=(202, 100, 255, 190), width=1)
    d.text((guide.width - 58, max(24, horizon_y - 14)), "HORIZON",
           fill=(255, 220, 70, 255), font=small_font)
    d.text((guide.width - 52, ground_y - 14), "GROUND",
           fill=(245, 245, 245, 255), font=small_font)

    legend_top = guide.height - 28
    d.rectangle((0, legend_top, guide.width, guide.height),
                fill=(16, 16, 20, 225))
    legend = [
        (colours["street"], "BLUE = EDGE EXIT"),
        (colours["door"], "RED = DOOR"),
        (colours["route"], "YELLOW = UP ROUTE"),
        ((226, 70, 200, 255), "MAGENTA = ACTOR SCALE"),
    ]
    cursor = 7
    for colour, label in legend:
        d.rectangle((cursor, legend_top + 8, cursor + 9, legend_top + 18),
                    fill=colour)
        d.text((cursor + 13, legend_top + 5), label,
               fill=(238, 238, 238, 255), font=small_font)
        cursor += 13 + d.textbbox((0, 0), label, font=small_font)[2] + 20
    tail = "BELOW UI LINE = OCCLUDED"
    tail_width = d.textbbox((0, 0), tail, font=small_font)[2]
    d.text((guide.width - tail_width - 7, legend_top + 5), tail,
           fill=(215, 175, 235, 255), font=small_font)
    out.parent.mkdir(parents=True, exist_ok=True)
    guide.save(out)


def semantic_edit_guide(key: str, source: Path, geometry_guide: Path,
                        out: Path) -> None:
    """Pre-warp the projected geometry guide to a candidate's working aspect.

    The map-derived guide remains authoritative for camera, keystoning, floor
    projection, framing, and transition placement. The candidate supplies only
    visual language. Resizing here is the exact inverse of final normalization,
    so the generated working image can be anisotropically fitted back to the
    plate without changing the projected contract.
    """
    s = spec(key)
    with Image.open(source) as image:
        width, height = image.size
    with Image.open(geometry_guide) as geometry:
        expected_aspect = s["plateWidth"] / 240.0
        actual_aspect = geometry.width / float(geometry.height)
        if abs(actual_aspect - expected_aspect) / expected_aspect > 0.001:
            raise SystemExit(
                f"{geometry_guide}: aspect {actual_aspect:.6f}, expected "
                f"the {s['plateWidth']}x240 plate contract ({expected_aspect:.6f})")
        guide = geometry.convert("RGB").resize(
            (width, height), Image.Resampling.NEAREST)
    d = ImageDraw.Draw(guide, "RGBA")
    header_h = max(68, round(height * 0.105))
    d.rectangle((0, 0, width, header_h), fill=(20, 20, 24, 235))
    d.text((16, 10), "PROJECTED GEOMETRY + SEMANTIC GUIDE - DO NOT RENDER MARKS OR TEXT",
           fill=(255, 255, 255, 255))
    d.text((16, 34),
           "Image 1 owns visual language only. This guide owns camera, keystoning, framing, and transitions.",
           fill=(230, 230, 230, 255))
    horizon_y = round(height * s["horizonY"] / 240.0)
    ground_y = round(height * s["groundY"] / 240.0)
    ui_y = round(height * s["visibleHeight"] / 240.0)
    d.rectangle((0, ui_y, width, height), fill=(28, 18, 40, 70))
    d.line((0, horizon_y, width, horizon_y), fill=(255, 220, 65, 255), width=3)
    d.line((0, ground_y, width, ground_y), fill=(245, 245, 245, 255), width=3)
    d.line((0, ui_y, width, ui_y), fill=(190, 105, 255, 255), width=3)
    d.text((width - 235, max(header_h + 4, horizon_y - 25)),
           "HORIZON / SKY", fill=(255, 220, 65, 255))
    d.text((width - 255, ground_y - 25),
           "ACTOR GROUND", fill=(245, 245, 245, 255))
    d.text((width - 390, ui_y + 10),
           "PERSISTENT UI BEGINS - KEEP ESSENTIAL LANDMARKS ABOVE",
           fill=(230, 195, 255, 255))
    for index, opening in enumerate(s["openings"]):
        x = round(width * opening["pixelX"] / s["plateWidth"])
        colour = ((70, 180, 255, 255) if opening["kind"] == "street"
                  else (255, 170, 55, 255))
        label_y = header_h + 14 + (index % 2) * 30
        label = SEMANTIC_GUIDE_LABELS.get(
            opening["anchor"], opening["label"].upper())
        box_width = 205
        label_x = max(4, min(width - box_width - 4, x - box_width // 2))
        d.rectangle((label_x - 4, label_y - 3,
                     label_x + box_width, label_y + 20),
                    fill=(30, 30, 34, 210))
        d.text((label_x, label_y), label, fill=colour)
        stem_top = label_y + 21
        d.line((x, stem_top, x, ground_y - 9), fill=colour, width=2)
        d.polygon(((x - 7, ground_y - 9), (x + 7, ground_y - 9),
                   (x, ground_y + 1)), fill=colour)
    d.text((16, height - 30),
           "Lower region is expendable foreground. Closed non-interactive doors may remain.",
           fill=(255, 255, 255, 255))
    out.parent.mkdir(parents=True, exist_ok=True)
    guide.save(out)


def prepare_precedent(key: str, source: Path, geometry_guide: Path,
                      out: Path) -> None:
    """Package an attractive image as a precedent, never as accepted art.

    The packet makes the vertical anamorphic transform explicit and provides an
    affordance worksheet. It does not claim that a depicted feature satisfies a
    transition and it never changes map data.
    """
    s = spec(key)
    out.mkdir(parents=True, exist_ok=True)
    source_copy = out / "aesthetic-precedent.png"
    if source.resolve() != source_copy.resolve():
        shutil.copy2(source, source_copy)
    geometry_copy = out / "projected-geometry-guide.png"
    if geometry_guide.resolve() != geometry_copy.resolve():
        shutil.copy2(geometry_guide, geometry_copy)
    normalized = out / "normalized-proof.png"
    normalize(source_copy, normalized, s["plateWidth"])
    with Image.open(normalized) as image:
        draw_overlay(key, image).save(out / "current-anchor-overlay.png")
    semantic_edit_guide(
        key, source_copy, geometry_copy, out / "semantic-edit-guide.png")

    with Image.open(source_copy) as image:
        source_width, source_height = image.size
    x_scale = s["plateWidth"] / float(source_width)
    y_scale = 240.0 / float(source_height)
    affordances = []
    for opening in s["openings"]:
        source_x = source_width * opening["pixelX"] / s["plateWidth"]
        affordances.append({
            "anchor": opening["anchor"],
            "destination": opening["label"],
            "kind": opening["kind"],
            "requiredVisualMeaning": SEMANTIC_DESCRIPTIONS.get(
                opening["anchor"], opening["label"]),
            "authoredPlateX": opening["pixelX"],
            "workingImageX": round(source_x, 2),
            "review": {
                "status": "unreviewed",
                "readable": None,
                "accessibleFromActorGround": None,
                "spatiallyPlausible": None,
                "observedPlateX": None,
                "notes": None,
            },
        })
    source_record = (str(source_copy.resolve().relative_to(ROOT))
                     if source_copy.resolve().is_relative_to(ROOT)
                     else str(source_copy.resolve()))
    packet = {
        "screen": key,
        "mapId": s["mapId"],
        "role": "aesthetic precedent only; not accepted art or geometry authority",
        "source": source_record,
        "projectionAuthority": str(
            geometry_copy.resolve().relative_to(ROOT)
            if geometry_copy.resolve().is_relative_to(ROOT)
            else geometry_copy.resolve()),
        "target": {"size": [s["plateWidth"], 240],
                   "visibleWorldHeight": s["visibleHeight"]},
        "workingTransform": {
            "sourceSize": [source_width, source_height],
            "xScale": x_scale,
            "yScale": y_scale,
            "anisotropic": abs(x_scale - y_scale) > 0.000001,
            "policy": "one deterministic full-frame transform; never stitch",
        },
        "framingRows": {
            "target": {"horizon": s["horizonY"], "actorGround": s["groundY"],
                       "persistentUiBegins": s["visibleHeight"]},
            "workingImage": {
                "horizon": round(source_height * s["horizonY"] / 240.0, 2),
                "actorGround": round(source_height * s["groundY"] / 240.0, 2),
                "persistentUiBegins": round(
                    source_height * s["visibleHeight"] / 240.0, 2),
            },
            "rule": "essential transitions stay above the persistent UI band",
        },
        "affordances": affordances,
        "imageLedRemap": {
            "status": "proposal-only",
            "allowedOnlyWhen": "every required transition exists, is readable, accessible, and perspective-coherent",
            "mustPreserve": ["left-to-right order", "destination and arrival topology",
                             "lane bounds", "non-overlapping trigger radii"],
            "authority": "owner approval before build_town.py or map data changes",
        },
        "promptPolicy": {
            "image1": "aesthetic precedent; visual language, materials, mood, and location vocabulary only",
            "image2": "semantic-edit-guide.png; authoritative camera projection, keystoning, floor geometry, framing, and transition placement",
            "firstPassPeople": "keep or add inhabitants; removal is a later selected-candidate edit",
            "avoid": ["style prose competing with image 1", "invented camera wording",
                      "rendered guide marks or labels", "weather variants before semantic acceptance"],
        },
    }
    (out / "precedent.json").write_text(
        json.dumps(packet, indent=2) + "\n", encoding="utf-8")


def remap_proposal(key: str, review_path: Path, out: Path) -> None:
    """Validate an image-led trigger remap without mutating authored data."""
    s = spec(key)
    review = json.loads(review_path.read_text(encoding="utf-8"))
    if review.get("screen") != key:
        raise SystemExit(
            f"{review_path}: screen {review.get('screen')!r}, expected {key!r}")
    rows = review.get("affordances")
    if not isinstance(rows, list):
        raise SystemExit(f"{review_path}: missing affordances array")
    by_anchor = {row.get("anchor"): row for row in rows}
    errors = []
    proposals = []
    for opening in s["openings"]:
        anchor = opening["anchor"]
        row = by_anchor.get(anchor) or {}
        observed = (row.get("review") or {}).get("observedPlateX")
        if not isinstance(observed, (int, float)) or isinstance(observed, bool):
            errors.append(f"{anchor}: review.observedPlateX is required")
            continue
        observed = float(observed)
        if not (s["compositionMarginPx"] <= observed <=
                s["plateWidth"] - s["compositionMarginPx"]):
            errors.append(
                f"{anchor}: x={observed:.2f} is outside the composed lane bounds")
        lane_y = (s["lane"]["minY"] +
                  (observed - s["compositionMarginPx"]) /
                  s["pixelsPerLaneUnit"])
        legacy_x = LEGACY_LANE_MARGIN_PX + lane_y * LEGACY_PIXELS_PER_Y
        proposals.append({
            "anchor": anchor,
            "destination": opening["label"],
            "currentPlateX": opening["pixelX"],
            "observedPlateX": round(observed, 3),
            "deltaPlateX": round(observed - opening["pixelX"], 3),
            "currentLaneY": opening["laneY"],
            "proposedLaneY": round(lane_y, 4),
            "proposedLegacyPixelX": round(legacy_x, 3),
        })
    if len(proposals) == len(s["openings"]):
        for left, right in zip(proposals, proposals[1:]):
            if right["observedPlateX"] <= left["observedPlateX"]:
                errors.append(
                    f"order violation: {right['anchor']} is not right of {left['anchor']}")
            # Town doorway radii are 0.9 runtime units. Requiring their full
            # diameters not to overlap is stricter than merely ordering centers.
            minimum = 1.8 * s["pixelsPerLaneUnit"]
            spacing = right["observedPlateX"] - left["observedPlateX"]
            if spacing < minimum:
                errors.append(
                    f"trigger overlap: {left['anchor']} -> {right['anchor']} is "
                    f"{spacing:.2f}px; need at least {minimum:.2f}px")
    result = {
        "screen": key,
        "mapId": s["mapId"],
        "sourceReview": str(review_path.resolve()),
        "status": "valid-proposal" if not errors else "invalid-proposal",
        "mutatedAuthoredData": False,
        "ownerApprovalRequired": True,
        "mustPreserve": ["destination and arrival topology", "anchor names",
                         "lane bounds", "left-to-right order",
                         "non-overlapping trigger radii"],
        "proposals": proposals,
        "errors": errors,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    if errors:
        raise SystemExit("image-led remap proposal is invalid:\n  " +
                         "\n  ".join(errors))


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    guides = sub.add_parser("guides")
    guides.add_argument("--screen", required=True, choices=sorted(SCREENS))
    guides.add_argument("--out", type=Path,
                        default=ROOT / "out" / "towngen" / "imagegen-guides")
    review = sub.add_parser("package")
    review.add_argument("--screen", required=True, choices=sorted(SCREENS))
    review.add_argument("--candidates", required=True, type=Path)
    review.add_argument("--out", required=True, type=Path)
    review.add_argument("--guide", type=Path,
                        help="exact perspective guide supplied to ImageGen")
    stitch_args = sub.add_parser("stitch")
    stitch_args.add_argument("--screen", required=True, choices=sorted(SCREENS))
    stitch_args.add_argument("--west", required=True, type=Path)
    stitch_args.add_argument("--east", required=True, type=Path)
    stitch_args.add_argument("--out", required=True, type=Path)
    normalize_args = sub.add_parser("normalize")
    normalize_args.add_argument("--screen", required=True, choices=sorted(SCREENS))
    normalize_args.add_argument("--source", required=True, type=Path)
    normalize_args.add_argument("--out", required=True, type=Path)
    normalize_args.add_argument("--filter", choices=("lanczos", "nearest"),
                                default="lanczos")
    calibrate_args = sub.add_parser("calibrate")
    calibrate_args.add_argument("--screen", required=True, choices=sorted(SCREENS))
    calibrate_args.add_argument("--source", required=True, type=Path)
    calibrate_args.add_argument("--out", required=True, type=Path)
    calibrate_args.add_argument("--observed-ground-y", required=True, type=float)
    calibrate_args.add_argument("--observed-actor-height", type=float)
    calibrate_args.add_argument("--metadata-out", type=Path)
    existing_args = sub.add_parser("calibrate-existing")
    existing_args.add_argument("--screen", required=True, choices=sorted(SCREENS))
    existing_args.add_argument("--source", required=True, type=Path)
    existing_args.add_argument("--out", required=True, type=Path)
    existing_args.add_argument("--npc-box", required=True,
                               help="bounded x,y,width,height ROI around a painted NPC")
    existing_args.add_argument("--metadata-out", type=Path)
    existing_args.add_argument("--measurement-out", type=Path)
    existing_args.add_argument("--target-actor-height", type=float, default=48.0)
    existing_args.add_argument("--roi-measurement", action="store_true",
                               help="use a tight supplied NPC ROI as the pixel measurement")
    existing_args.add_argument("--visual-ground-offset", type=float, default=0.0,
                               help="screen-specific plate-only offset; runtime ground row is unchanged")
    existing_args.add_argument("--npc-box-space", type=str,
                               help="WIDTH,HEIGHT coordinate space for --npc-box; scales the ROI to the source")
    calibrated_review_args = sub.add_parser("review-calibrated")
    calibrated_review_args.add_argument("--screen", required=True,
                                        choices=sorted(SCREENS))
    calibrated_review_args.add_argument("--source", required=True, type=Path)
    calibrated_review_args.add_argument("--out", required=True, type=Path)
    clean_args = sub.add_parser("remove-baked-figures")
    clean_args.add_argument("--source", required=True, type=Path)
    clean_args.add_argument("--out", required=True, type=Path)
    clean_args.add_argument("--box", action="append", required=True,
                            help="figure box x,y,width,height; repeat per figure")
    clean_args.add_argument("--metadata-out", type=Path)
    multi_args = sub.add_parser("calibrate-existing-multi")
    multi_args.add_argument("--screen", required=True, choices=sorted(SCREENS))
    multi_args.add_argument("--source", required=True, type=Path)
    multi_args.add_argument("--out", required=True, type=Path)
    multi_args.add_argument("--npc-box", action="append", required=True)
    multi_args.add_argument("--npc-box-space", type=str)
    multi_args.add_argument("--metadata-out", type=Path)
    multi_args.add_argument("--measurement-dir", type=Path)
    multi_args.add_argument("--roi-measurement", action="store_true",
                            help="treat each supplied box as an explicit detector person box")
    floor_args = sub.add_parser("estimate-floor")
    floor_args.add_argument("--source", required=True, type=Path)
    floor_args.add_argument("--out", required=True, type=Path)
    floor_args.add_argument("--metadata-out", type=Path)
    floor_cal_args = sub.add_parser("calibrate-floor-aware")
    floor_cal_args.add_argument("--screen", required=True, choices=sorted(SCREENS))
    floor_cal_args.add_argument("--source", required=True, type=Path)
    floor_cal_args.add_argument("--out", required=True, type=Path)
    floor_cal_args.add_argument("--npc-box", required=True)
    floor_cal_args.add_argument("--npc-box-space", required=True)
    floor_cal_args.add_argument("--floor-metadata", required=True, type=Path)
    floor_cal_args.add_argument("--metadata-out", required=True, type=Path)
    floor_cal_args.add_argument("--measurement-out", required=True, type=Path)
    annotated_args = sub.add_parser("calibrate-annotated")
    annotated_args.add_argument("--screen", required=True, choices=sorted(SCREENS))
    annotated_args.add_argument("--source", required=True, type=Path)
    annotated_args.add_argument("--annotation", required=True, type=Path)
    annotated_args.add_argument("--out", required=True, type=Path)
    annotated_args.add_argument("--metadata-out", required=True, type=Path)
    annotated_args.add_argument("--review-out", required=True, type=Path)
    v2_args = sub.add_parser("calibrate-v2")
    v2_args.add_argument("--screen", required=True, choices=sorted(SCREENS))
    v2_args.add_argument("--source", required=True, type=Path)
    v2_args.add_argument("--annotation", required=True, type=Path)
    v2_args.add_argument("--out", required=True, type=Path)
    v2_args.add_argument("--metadata-out", required=True, type=Path)
    v2_args.add_argument("--review-out", required=True, type=Path)
    spatial_overlay_args = sub.add_parser("annotate-spatial")
    spatial_overlay_args.add_argument("--screen", required=True,
                                      choices=sorted(SCREENS))
    spatial_overlay_args.add_argument("--source", required=True, type=Path)
    spatial_overlay_args.add_argument("--out", required=True, type=Path)
    derive_args = sub.add_parser("derive-working-guide")
    derive_args.add_argument("--source", required=True, type=Path)
    derive_args.add_argument("--out", required=True, type=Path)
    derive_args.add_argument("--width", type=int, default=MODEL_GUIDE_WIDTH)
    derive_args.add_argument("--height", type=int, default=MODEL_GUIDE_HEIGHT)
    edit_guide_args = sub.add_parser("edit-guide")
    edit_guide_args.add_argument("--screen", required=True, choices=sorted(SCREENS))
    edit_guide_args.add_argument("--source", required=True, type=Path)
    edit_guide_args.add_argument("--geometry-guide", required=True, type=Path)
    edit_guide_args.add_argument("--out", required=True, type=Path)
    precedent_args = sub.add_parser("precedent")
    precedent_args.add_argument("--screen", required=True, choices=sorted(SCREENS))
    precedent_args.add_argument("--source", required=True, type=Path)
    precedent_args.add_argument("--geometry-guide", required=True, type=Path)
    precedent_args.add_argument("--out", required=True, type=Path)
    remap_args = sub.add_parser("remap-proposal")
    remap_args.add_argument("--screen", required=True, choices=sorted(SCREENS))
    remap_args.add_argument("--review", required=True, type=Path)
    remap_args.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    if args.command == "guides":
        guide_crops(args.screen, args.out / args.screen)
    elif args.command == "package":
        package(args.screen, args.candidates, args.out, args.guide)
    elif args.command == "stitch":
        stitch(args.west, args.east, args.out, spec(args.screen)["plateWidth"])
    elif args.command == "edit-guide":
        semantic_edit_guide(
            args.screen, args.source, args.geometry_guide, args.out)
    elif args.command == "precedent":
        prepare_precedent(
            args.screen, args.source, args.geometry_guide, args.out)
    elif args.command == "remap-proposal":
        remap_proposal(args.screen, args.review, args.out)
    elif args.command == "annotate-spatial":
        blender_spatial_overlay(args.screen, args.source, args.out)
    elif args.command == "derive-working-guide":
        derive_working_guide(
            args.source, args.out, width=args.width, height=args.height)
    elif args.command == "calibrate":
        calibrate_frame(
            args.screen, args.source, args.out,
            args.observed_ground_y,
            observed_actor_height=args.observed_actor_height,
            metadata_out=args.metadata_out)
    elif args.command == "calibrate-existing":
        calibrate_existing(
            args.screen, args.source, args.out, args.npc_box,
            metadata_out=args.metadata_out,
            measurement_out=args.measurement_out,
            target_actor_height=args.target_actor_height,
            roi_measurement=args.roi_measurement,
            visual_ground_offset=args.visual_ground_offset,
            npc_box_space=tuple(int(part) for part in args.npc_box_space.split(","))
            if args.npc_box_space else None)
    elif args.command == "review-calibrated":
        review_calibrated(args.screen, args.source, args.out)
    elif args.command == "remove-baked-figures":
        remove_baked_figures(args.source, args.out, args.box,
                             metadata_out=args.metadata_out)
    elif args.command == "calibrate-existing-multi":
        calibrate_existing_multi(
            args.screen, args.source, args.out, args.npc_box,
            npc_box_space=tuple(int(part) for part in args.npc_box_space.split(","))
            if args.npc_box_space else None,
            metadata_out=args.metadata_out,
            measurement_dir=args.measurement_dir,
            roi_measurement=args.roi_measurement)
    elif args.command == "estimate-floor":
        result = estimate_painted_floor(args.source, args.out)
        metadata = args.metadata_out or args.out.with_suffix(".json")
        metadata.parent.mkdir(parents=True, exist_ok=True)
        metadata.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    elif args.command == "calibrate-floor-aware":
        calibrate_floor_aware(
            args.screen, args.source, args.out, args.npc_box,
            tuple(int(part) for part in args.npc_box_space.split(",")),
            args.floor_metadata, args.metadata_out, args.measurement_out)
    elif args.command == "calibrate-annotated":
        calibrate_annotated(args.screen, args.source, args.annotation, args.out,
                            args.metadata_out, args.review_out)
    elif args.command == "calibrate-v2":
        calibrate_v2(args.screen, args.source, args.annotation, args.out,
                     args.metadata_out, args.review_out)
    else:
        filters = {
            "lanczos": Image.Resampling.LANCZOS,
            "nearest": Image.Resampling.NEAREST,
        }
        normalize(args.source, args.out, spec(args.screen)["plateWidth"],
                  resampling=filters[args.filter])


if __name__ == "__main__":
    main()
