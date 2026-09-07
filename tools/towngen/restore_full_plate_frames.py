"""Restore complete accepted 240px town frames behind the runtime dock."""

from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "out" / "towngen"
PLATES = ROOT / "projects" / "hichaukitoden-game" / "assets" / "environments" / "st_maria_town" / "plates"
SCREENS = [
    ("port", "port_bg.png", 1065),
    ("churchyard", "churchyard_bg.png", 924),
    ("cortico", "backstreet_bg.png", 866),
    ("market", "market_bg.png", 772),
    ("quay", "quay_bg.png", 826),
    ("weaponsmith", "lauras_smith_bg.png", 450),
    ("alicias_padaria", "alicias_padaria_bg.png", 450),
    ("pub", "pub_bg.png", 576),
    ("chapel", "chapel_bg.png", 674),
    ("house_laura", "house_laura_bg.png", 747),
    ("house_alicia", "house_alicia_bg.png", 424),
    ("lodging", "lodging_bg.png", 457),
]


def center_crop(image: Image.Image, width: int) -> Image.Image:
    if image.width < width:
        raise SystemExit(f"accepted source is narrower than target: {image.size} -> {width}")
    left = (image.width - width) // 2
    return image.crop((left, 0, left + width, image.height))


def main() -> None:
    for screen, plate, width in SCREENS:
        source = OUT / screen / "replacement" / "accepted.png"
        if not source.exists():
            raise SystemExit(f"missing accepted full frame: {source}")
        with Image.open(source) as image:
            image = image.convert("RGB")
            if image.height != 240:
                raise SystemExit(f"accepted source must be 240px high: {source} {image.size}")
            restored = center_crop(image, width)
            restored.save(PLATES / plate, optimize=True)
            print(f"restored {screen}: {image.size} -> {restored.size}, full scene retained behind dock")


if __name__ == "__main__":
    main()
