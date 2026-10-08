"""Build original neutral raster fixtures for the standalone traversal Project.

These test figures use no sibling Project assets. Frame size is the runtime's
24x48 billboard contract; walker.png contains six frames in one horizontal row.
"""
from pathlib import Path
import struct
import zlib
import sys

ROOT = Path(__file__).resolve().parents[3]
TARGET = ROOT / "projects/experiments/continuous-surface-gauntlet/assets/character"


def figure(stride):
    pixels = [[(0, 0, 0, 0) for _ in range(24)] for _ in range(48)]

    def box(x0, y0, x1, y1, color):
        for y in range(y0, y1):
            for x in range(x0, x1):
                pixels[y][x] = (*color, 255)

    # A plain faceless survey mannequin in a slate coat, grounded at row 47.
    box(9, 4, 15, 13, (190, 185, 165))
    box(8, 13, 16, 29, (65, 100, 125))
    box(7, 14, 9, 27, (40, 65, 85))
    box(16, 14, 18, 27, (40, 65, 85))
    box(8, 29, 12, 44 + stride, (40, 48, 60))
    box(13, 29, 17, 44 - stride, (40, 48, 60))
    box(7, 44 + stride, 12, 48, (24, 28, 36))
    box(13, 44 - stride, 18, 48, (24, 28, 36))
    return pixels


def png(pixels):
    width, height = len(pixels[0]), len(pixels)
    rows = b"".join(b"\x00" + bytes(channel
        for pixel in row for channel in pixel) for row in pixels)

    def chunk(kind, data):
        return (struct.pack(">I", len(data)) + kind + data
            + struct.pack(">I", zlib.crc32(kind + data)))

    return (b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(rows))
        + chunk(b"IEND", b""))


if __name__ == "__main__":
    if "--check" not in sys.argv:
        TARGET.mkdir(parents=True, exist_ok=True)
    outputs = {TARGET / "player.png": png(figure(0))}
    frames = [figure(s) for s in (0, 1, 2, 0, -1, -2)]
    outputs[TARGET / "walker.png"] = png([sum((frame[y] for frame in frames), [])
        for y in range(48)])
    atlas = [[(112, 124, 132, 255) if x % 16 == 0 or y % 16 == 0
        else (165, 174, 180, 255) for x in range(64)] for y in range(64)]
    outputs[TARGET.parent / "environments/archive_antechamber/environment.png"] = png(atlas)
    for path, data in outputs.items():
        if "--check" in sys.argv:
            assert path.read_bytes() == data, f"fixture disagrees with source: {path}"
        else:
            path.write_bytes(data)
    print("CONTINUOUS_RASTER_FIXTURES_OK")
