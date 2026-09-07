"""Promote the fresh independent town-plate generations with smooth fitting.

The source images are generated independently from the style reference and each
screen's semantic guide.  This step deliberately uses a high-quality Lanczos
fit into the authored visible-world frame; it never uses nearest-neighbour
resampling for background plates.
"""

import argparse
import json
from pathlib import Path
import shutil
import sys

from PIL import Image, ImageDraw, ImageOps

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from build_town import EXPECTED_PLATE_WIDTHS

ROOT = Path(__file__).resolve().parents[2]
GEN = Path(r"C:/Users/josep/.codex/generated_images/01a06bd2-7b02-73d3-93f7-ff903d298166")
OUT = ROOT / "out" / "towngen" / "repaint-v4"
PLATES = ROOT / "projects" / "hichaukitoden-game" / "assets" / "environments" / "st_maria_town" / "plates"
WORLD_H = 144
FRAME_H = 240

# These are the twelve outputs returned by the fresh independent batch, in the
# exact order submitted to ImageGen.
GENERATIONS = [
    "exec-cdc796e5-f85d-4dda-81b6-a08af5cdacb8.png",
    "exec-24bd0632-da75-4b15-8e6c-48f2b0c27b49.png",
    "exec-2fa73b57-8d23-48f7-a4aa-a18ae97a416b.png",
    "exec-691e7d65-6bc9-48cc-8908-8210c1aab3ac.png",
    "exec-07b813da-53ac-448d-8083-4bbaf3ed3db1.png",
    "exec-5bf3e6d4-4eeb-42c9-9be0-dfee43c0b998.png",
    "exec-b97bcbd9-b8c2-42ff-99bf-b37ff6e6395b.png",
    "exec-db701a1d-a6d7-4ded-bd2f-a460adc554b8.png",
    "exec-d7f81111-5efc-4df3-811f-85562242eec2.png",
    "exec-ca543251-3a33-4692-8fcf-3d7b11929c8b.png",
    "exec-dc2607be-f0c6-45d1-9b30-0503d2dcbd7c.png",
    "exec-fc373026-2501-4ed7-b6e3-841e131be1ba.png",
]

# Plate widths are derived from build_town.EXPECTED_PLATE_WIDTHS as the single
# authority, ensuring promotion cannot overwrite shipping assets with stale widths.
SCREEN_SPECS = [
    ("port", "port_bg.png"),
    ("churchyard", "churchyard_bg.png"),
    ("cortico", "backstreet_bg.png"),
    ("market", "market_bg.png"),
    ("quay", "quay_bg.png"),
    ("weaponsmith", "lauras_smith_bg.png"),
    ("alicias_padaria", "alicias_padaria_bg.png"),
    ("pub", "pub_bg.png"),
    ("chapel", "chapel_bg.png"),
    ("house_laura", "house_laura_bg.png"),
    ("house_alicia", "house_alicia_bg.png"),
    ("lodging", "lodging_bg.png"),
]

SCREENS = [
    (key, plate, EXPECTED_PLATE_WIDTHS[plate])
    for key, plate in SCREEN_SPECS
]

PROMPT_TEMPLATE = (
    "Create one complete smooth raster game background plate for the named "
    "side-scroller RPG screen. Use Image 1 only as the aesthetic reference "
    "and Image 2 only as a precise placement guide: use its placement, not "
    "its appearance. Preserve the guide's authored walking lane, horizon, "
    "event positions, camera framing, and persistent lower UI boundary. "
    "Render a coherent continuous floor reaching the walking lane. Remove "
    "every baked person, NPC, player, arrow, label, pin, grid, proxy, UI, "
    "watermark, and guide mark. No collage, no stitched panels, no "
    "concept-art illustration, no pixel-art look, no nearest-neighbor scaling "
    "or jagged enlarged pixels. Keep architecture and thresholds human-scaled "
    "for the 24x48 runtime actor. Style: pre-rendered early-90s CGI, "
    "side-scroller RPG, like a PSX screenshot."
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--promote", action="store_true",
                        help="copy calibrated candidates over shipping plates")
    args = parser.parse_args()
    if len(GENERATIONS) != len(SCREENS):
        raise SystemExit("generation/screen mapping is incomplete")
    contact = Image.new("RGB", (4 * 320, 3 * 180), (10, 10, 10))
    for index, ((screen, plate, width), generation) in enumerate(zip(SCREENS, GENERATIONS)):
        source = GEN / generation
        if not source.exists():
            raise SystemExit(f"missing fresh generation: {source}")
        screen_dir = OUT / screen
        source_dir = screen_dir / "source"
        source_dir.mkdir(parents=True, exist_ok=True)
        fresh = source_dir / "fresh.png"
        shutil.copy2(source, fresh)
        prompt = PROMPT_TEMPLATE + " Screen: " + screen + "."
        (screen_dir / "prompt.txt").write_text(prompt + "\n", encoding="utf-8")
        guide = ROOT / "out" / "towngen" / screen / "replacement" / "semantic-guide.png"
        # Preserve aspect ratio, crop rather than stretch, and use a smooth
        # filter.  The source is a complete scene; the authored visible-world
        # frame is the exact staged target, not a nearest-neighbour preview.
        with Image.open(fresh) as image:
            image = image.convert("RGB")
            fitted = ImageOps.fit(image, (width, WORLD_H), method=Image.Resampling.LANCZOS,
                                  centering=(0.5, 0.68))
            calibrated = screen_dir / "calibrated-clean.png"
            # The game owns a 240px frame: the painted world occupies 0..143
            # and the persistent runtime UI owns 144..239.  Keep that lower
            # region in the artifact so review files have the same geometry as
            # staging.json; do not crop the frame to the world height.
            frame = Image.new("RGB", (width, FRAME_H), (0, 0, 0))
            frame.paste(fitted, (0, 0))
            frame.save(calibrated, optimize=True)
            thumb = frame.resize((320, 180), Image.Resampling.LANCZOS)
            x = (index % 4) * 320
            y = (index // 4) * 180
            contact.paste(thumb, (x, y))
            draw = ImageDraw.Draw(contact)
            draw.rectangle((x, y, x + 319, y + 179), outline=(255, 180, 80), width=2)
            draw.line((x, y + round(180 * WORLD_H / FRAME_H), x + 319,
                       y + round(180 * WORLD_H / FRAME_H)), fill=(220, 150, 255), width=2)
            draw.text((x + 6, y + 162), screen, fill=(255, 220, 160))
        metadata = {
            "screen": screen,
            "plate": plate,
            "source": str(fresh.relative_to(ROOT)).replace("\\", "/"),
            "guide": str(guide.relative_to(ROOT)).replace("\\", "/") if guide.exists() else None,
            "targetSize": [width, FRAME_H],
            "worldSize": [width, WORLD_H],
            "fit": "aspect-preserving crop to authored visible-world frame, retained in full 240px plate canvas",
            "resampling": "PIL.Image.Resampling.LANCZOS",
            "generation": "fresh independent ImageGen output; style reference + screen guide only",
            "prompt": prompt,
        }
        (screen_dir / "calibration.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
        # Replacement source is kept under repaint-v4; promotion is explicit.
        if args.promote:
            calibrated_plate = screen_dir / "calibrated-clean.png"
            with Image.open(calibrated_plate) as check_img:
                if check_img.size != (width, FRAME_H):
                    raise SystemExit(
                        f"Cannot promote {plate}: candidate dimensions {check_img.size} "
                        f"do not match expected {(width, FRAME_H)} from EXPECTED_PLATE_WIDTHS"
                    )
            shutil.copy2(calibrated_plate, PLATES / plate)
    contact.save(OUT / "contact-sheet.png", optimize=True)


if __name__ == "__main__":
    main()
