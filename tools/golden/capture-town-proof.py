"""Capture the bounded-lane town proof through the real LÖVE renderer.

The runtime emits base64 frames because LÖVE's filesystem sandbox cannot write
to an arbitrary checkout path. This wrapper owns decoding and preserves the
runtime metadata beside the PNGs.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--game-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--lovec", default=r"C:\Program Files\LOVE\lovec.exe", type=Path
    )
    parser.add_argument(
        "--surface", default=None, choices=("classic", "four_three", "wide"),
        help="presentation surface to photograph at; default is the Project's "
             "own. 'wide' (426x240) is the widest the game actually renders, "
             "which is what an img2img input wants -- a wider frame than the "
             "game has would invite the model to invent outside it.",
    )
    args = parser.parse_args()
    args.game_root = args.game_root.resolve()
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=True)

    result = subprocess.run(
        [str(args.lovec), str(args.game_root)]
        + ([f"surface={args.surface}"] if args.surface else [])
        + ["town-proof-frames"],
        cwd=args.game_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        raise SystemExit(result.stdout[-6000:] + "\n" + result.stderr[-6000:])
    begin, end = "TOWN PROOF BEGIN", "TOWN PROOF END"
    if begin not in result.stdout or end not in result.stdout:
        raise SystemExit("town proof markers missing\n" + result.stdout[-6000:])
    payload_text = result.stdout.split(begin, 1)[1].split(end, 1)[0].strip()
    payload = json.loads(payload_text)
    for frame in payload.get("frames", []):
        name = frame["label"] + ".png"
        (args.output / name).write_bytes(base64.b64decode(frame["image"]))
        frame.pop("image", None)
    (args.output / "town-proof.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"THESTRA_TOWN_PROOF OK frames={len(payload.get('frames', []))} "
        f"output={args.output}"
    )


if __name__ == "__main__":
    main()
