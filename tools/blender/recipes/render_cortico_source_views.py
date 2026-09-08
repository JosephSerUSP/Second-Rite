"""Render native west/centre/east review views from the adopted Cortico source.

This is read-only with respect to the source blend: it opens the file, changes
only the in-memory camera position and render output, and writes review PNGs.
The canonical camera rotation/pitch is never replaced.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import bpy


LANE_CENTRE = 12.031
VIEWS = (("west", 0.131), ("centre", 12.031), ("east", 23.931))


def render(blend: Path, output: Path) -> None:
    bpy.ops.wm.open_mainfile(filepath=str(blend.resolve()))
    scene = bpy.context.scene
    camera = bpy.data.objects.get("TH_CAMERA_PREVIEW")
    if camera is None:
        raise RuntimeError("adopted source is missing TH_CAMERA_PREVIEW")
    scene.camera = camera

    # Keep the authored source visible, but do not let guides/preview helpers
    # obscure the broad composition review.
    for name in ("TH_PREVIEW_ONLY", "TH_COLLISION", "TH_ANCHORS",
                 "TH_RENDER"):
        collection = bpy.data.collections.get(name)
        if collection is not None:
            collection.hide_render = True
    actors = bpy.data.collections.get("TH_PREVIEW_ACTORS")
    if actors is not None:
        actors.hide_render = False
        for obj in actors.all_objects:
            obj.hide_render = False

    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 426
    scene.render.resolution_y = 240
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.filepath = str(output.resolve())
    output.parent.mkdir(parents=True, exist_ok=True)

    source_y = camera.location.y
    try:
        for label, runtime_y in VIEWS:
            camera.location.y = LANE_CENTRE - runtime_y
            scene.render.filepath = str((output / f"{label}.png").resolve())
            bpy.ops.render.render(write_still=True)
    finally:
        camera.location.y = source_y


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--blend", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:]
                             if "--" in sys.argv else [])
    if not args.blend.is_file():
        raise SystemExit(f"source blend not found: {args.blend}")
    render(args.blend, args.output)
    print("CORTICO SOURCE VIEWS OK", args.output.resolve())


if __name__ == "__main__":
    main()
