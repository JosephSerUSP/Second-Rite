"""Build img2img inputs for the town from live-runtime captures.

The inputs come from the REAL renderer, not from Blender: every frame here is
what the game actually draws, at the surface it actually draws it on, with the
player and NPCs staged in it. That last part is not decoration -- a frame
without a character gives the model no scale reference, and a generated street
that dwarfs a person reads as correct until someone stands in it.

Two things this does beyond capturing.

**It crops away the dead area.** A captured frame is 42-72% black: the plate
screens carry content in the top 144 of 240 lines, and the modelled 3D
interiors do not fill a wide surface at all -- they render about 256 px wide
and the rest is void. Handing a model a mostly-black image spends its attention
on nothing and invites it to invent inside the void, which is exactly the
failure already recorded for the img2img direction pass: it is reliable on
material and palette and it deletes the near band every time.

**It records where each crop came from.** The manifest carries map id, title,
lane position, the crop box and the source size, so a generated image can be
placed back into the frame it was derived from rather than guessed at.

Determinism was measured, not assumed: two independent captures of all 45
frames differ by zero pixels, so an input regenerates identically and a
generated image can always be traced to a reproducible source.

    python tools/asset-gen/make_town_img2img_inputs.py \
        --game-root <staged game> --output out/town-img2img --surface wide
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# The three screens worth generating against. Every other town screen is either a
# plate the AI produced in the first place -- feeding a model its own output back
# teaches it nothing and compounds whatever was wrong with it -- or an empty
# blockout with no visual language to carry. These three are modelled
# environments built from the .blend sources, so they are the only frames that
# carry the grammar a new plate should inherit.
REFERENCE_MAPS = (17, 28, 29)   # the Praca, Alicia's Padaria, Laura's Smithy
CAPTURE = ROOT / "tools" / "golden" / "capture-town-proof.py"


PLAYER_SPRITE = ("projects", "hichaukitoden-game", "assets", "character",
                 "player.png")
# Where the player's feet sit inside the window, measured from its TOP. 129 of a
# 146-tall window is where the interiors already stood, so they keep their
# framing and every other screen is brought to them.
FEET_FROM_TOP = 129
# Detection is a real match, not a guess: an interior scores about 10 and the
# Praca's plate about 29 (it is a flat painted figure over a painted street).
# Anything far above that is not the player, and a silently wrong anchor would
# misframe every crop, so it fails loudly instead.
PLAYER_MATCH_LIMIT = 60.0


def find_player(image):
    """Where the player stands, by searching for the actual sprite.

    Anchoring on the content's floor was wrong: the screens' content ends at
    different heights -- an interior at 146 rows, the Praca's plate at all 240 --
    so a bottom-anchored window puts the character at a different height in each,
    which is the one thing that must NOT vary. The character is the constant, so
    the character is what the window is hung from.

    Returns (centre x, feet y).
    """
    import numpy as np
    from PIL import Image
    sprite = Image.open(str(ROOT.joinpath(*PLAYER_SPRITE))).convert("RGBA")
    sprite = sprite.crop(sprite.getbbox())
    data = np.asarray(sprite)
    mask = data[:, :, 3] > 128
    reference = data[:, :, :3].astype(int)
    height, width = data.shape[:2]
    frame = np.asarray(image.convert("RGB")).astype(int)
    rows, columns = frame.shape[:2]
    best, at = None, None
    for y in range(rows - height + 1):
        for x in range(columns - width + 1):
            error = np.abs(frame[y:y + height, x:x + width] - reference)[mask].mean()
            if best is None or error < best:
                best, at = error, (x, y)
    if best is None or best > PLAYER_MATCH_LIMIT:
        raise SystemExit("could not find the player in the frame (best match %.1f, "
                         "limit %.1f); the anchor would be wrong"
                         % (best if best is not None else -1, PLAYER_MATCH_LIMIT))
    return at[0] + width // 2, at[1] + height


def player_box(image, target):
    """A fixed window hung from the player, so the character lands identically.

    Horizontal centre and vertical feet both come from the figure, so the three
    screens read as one town photographed the same way rather than three
    different subjects.
    """
    width, height = target
    centre_x, feet_y = find_player(image)
    x0 = max(0, min(image.width - width, centre_x - width // 2))
    y0 = max(0, min(image.height - height, feet_y - FEET_FROM_TOP))
    return (x0, y0, x0 + width, y0 + height)


def content_box(image):
    """The non-black region, which is the part worth generating against."""
    box = image.convert("RGB").getbbox()
    return box or (0, 0, image.width, image.height)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--game-root", required=True, type=Path,
                        help="staged runnable game (tools/ci/stage-project-gates.js)")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--surface", default="wide",
                        choices=("classic", "four_three", "wide"))
    parser.add_argument("--scale", type=int, default=3,
                        help="integer upscale for the model's benefit; NEAREST, "
                             "so no interpolation invents detail the game lacks")
    parser.add_argument("--uniform-crop", default="273x146",
                        help="crop every frame to this WxH window over its "
                             "content, hung from the player so the character "
                             "lands in the same place; 'off' keeps each frame's "
                             "own content box")
    parser.add_argument("--maps", default=",".join(str(m) for m in REFERENCE_MAPS),
                        help="comma-separated map ids to keep, or 'all'. Defaults "
                             "to the three modelled screens; see REFERENCE_MAPS.")
    parser.add_argument("--keep-raw", action="store_true",
                        help="also keep the uncropped captures")
    args = parser.parse_args()

    from PIL import Image

    output = args.output.resolve()
    raw = output / "raw"
    output.mkdir(parents=True, exist_ok=True)

    result = subprocess.run(
        [sys.executable, str(CAPTURE), "--game-root", str(args.game_root),
         "--output", str(raw), "--surface", args.surface],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if result.returncode != 0:
        raise SystemExit(result.stdout[-4000:] + "\n" + result.stderr[-4000:])
    print(result.stdout.strip().splitlines()[-1])

    proof = json.loads((raw / "town-proof.json").read_text(encoding="utf-8"))
    by_label = {f["label"]: f for f in proof.get("frames", [])}

    titles = {}
    maps_dir = ROOT / "projects" / "hichaukitoden-game" / "data" / "maps"
    for path in maps_dir.glob("*.json"):
        try:
            titles[int(path.stem)] = json.loads(
                path.read_text(encoding="utf-8")).get("title", "")
        except Exception:
            pass

    keep = None
    if args.maps.strip().lower() != "all":
        keep = {int(m) for m in args.maps.split(",") if m.strip()}

    entries = []
    for png in sorted(raw.glob("*.png")):
        label = png.stem
        frame = by_label.get(label, {})
        if keep is not None and frame.get("mapId") not in keep:
            png.unlink()
            continue
        image = Image.open(png)
        if args.uniform_crop.lower() == "off":
            box = content_box(image)
        else:
            width, height = (int(v) for v in args.uniform_crop.lower().split("x"))
            box = player_box(image, (width, height))
        cropped = image.crop(box)
        if args.scale > 1:
            cropped = cropped.resize(
                (cropped.width * args.scale, cropped.height * args.scale),
                Image.NEAREST)
        out_path = output / f"{label}.png"
        cropped.save(out_path)
        map_id = frame.get("mapId")
        entries.append({
            "label": label,
            "file": out_path.name,
            "mapId": map_id,
            "title": titles.get(map_id, ""),
            "lanePosition": label.split("-")[-1],
            "surface": args.surface,
            "sourceSize": [image.width, image.height],
            "cropBox": list(box),
            "scale": args.scale,
            "outputSize": [cropped.width, cropped.height],
            "actor": frame.get("actor"),
            "projectionWindowOffsetX": frame.get("projectionWindowOffsetX"),
        })

    (output / "inputs.json").write_text(
        json.dumps({"surface": args.surface, "scale": args.scale,
                    "frames": entries}, indent=2) + "\n", encoding="utf-8")

    if not args.keep_raw:
        for png in raw.glob("*.png"):
            png.unlink()

    if keep is not None and {e["mapId"] for e in entries} != keep:
        raise SystemExit("asked for maps %s but captured %s"
                         % (sorted(keep), sorted({e["mapId"] for e in entries})))
    sizes = sorted({tuple(e["outputSize"]) for e in entries})
    if args.uniform_crop.lower() != "off" and len(sizes) != 1:
        raise SystemExit("uniform crop asked for one size, produced %s" % (sizes,))
    print(f"TOWN IMG2IMG INPUTS OK frames={len(entries)} "
          f"surface={args.surface} scale={args.scale}x sizes={sizes}")
    print(f"  manifest: {output / 'inputs.json'}")


if __name__ == "__main__":
    main()
