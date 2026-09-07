"""Restore the full 240px runtime frame without changing painted world pixels."""

from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
PLATES = ROOT / "projects" / "hichaukitoden-game" / "assets" / "environments" / "st_maria_town" / "plates"
FILES = [
    "port_bg.png", "churchyard_bg.png", "backstreet_bg.png", "market_bg.png",
    "quay_bg.png", "lauras_smith_bg.png", "alicias_padaria_bg.png", "pub_bg.png",
    "chapel_bg.png", "house_laura_bg.png", "house_alicia_bg.png", "lodging_bg.png",
]


def main() -> None:
    for name in FILES:
        path = PLATES / name
        with Image.open(path) as image:
            if image.height not in (144, 240):
                raise SystemExit(f"unexpected frame height for {name}: {image.size}")
            # The dock is a separate runtime layer. Keep the logical 240px
            # frame, but leave rows 144..239 transparent so the plate cannot
            # occlude or replace the dock.
            world = image.convert("RGBA").crop((0, 0, image.width, 144))
            frame = Image.new("RGBA", (image.width, 240), (0, 0, 0, 0))
            frame.paste(world, (0, 0))
            frame.save(path, optimize=True)
            print(f"framed {name}: {image.width}x{image.height} -> {image.width}x240 transparent dock band")


if __name__ == "__main__":
    main()
