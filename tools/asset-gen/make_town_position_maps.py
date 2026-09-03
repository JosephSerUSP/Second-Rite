"""Draw each town screen's layout from map DATA, never from its current plate.

A positional reference has to come from somewhere that is not the placeholder.
Capturing the screen looked like the obvious source and is exactly wrong: twelve
of the fifteen town screens render a provisional AI plate, so a captured frame
hands the model its own earlier output and asks it to improve on it. Whatever was
wrong with the placeholder gets laundered into the replacement, and the model is
anchored to a composition nobody authored.

Everything needed is authored data instead:

* ``lane`` gives the walkable span,
* ``playerProjection`` gives the pixels-per-runtime-unit and where the player
  stands, which is exactly how the runtime places anything on this screen,
* the package's ``anchors`` give every doorway and stair its position along the
  street.

So the diagram is derived, not photographed. It says where the ground is, how
big a person is on it, and where the openings fall -- and says nothing about what
any of it looks like, which is the style sheet's job.

    python tools/asset-gen/make_town_position_maps.py --output out/town-positions
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
from town_projection import PlateCamera, self_check, ACTOR_HEIGHT

ROOT = Path(__file__).resolve().parents[2]
GAME = ROOT / "projects" / "hichaukitoden-game"
PLAYER = GAME / "assets" / "character" / "player.png"

# A plate is the WHOLE street, not one window onto it: the runtime scrolls a
# 426-wide view across an image up to 1100 wide. A diagram cropped to the view
# would place three doorways and hide the other five, so this is drawn at the
# plate's own size, straight from the package's imageSize.
SCALE = 3

# A guide MARKS, it does not depict.
#
# The first version drew door-shaped blocks standing on a filled ground band, and
# the model did the only thing it could with a composition: it redrew it, flat
# grey rectangles and all, in the elevation the diagram was drawn in rather than
# the perspective the style sheet shows. A picture of a door tells the model what
# shape to draw. A mark tells it where a door goes and leaves the door to it.
#
# So: a field with nothing in it, one thin line for the ground, a caret under each
# opening, and one stick the height of a person. Nothing here has a silhouette
# worth copying.
FIELD = (128, 128, 128)
LINE = (250, 250, 250)
MARK = (255, 64, 64)
SCALE_MARK = (64, 128, 255)
FLOOR_RULE = (110, 210, 140)
WALL_RULE = (225, 190, 90)
HORIZON = (245, 245, 120)
MARK_SIZE = 0.30            # of person height
RULE = 2

# The rulers are PROJECTED through the town camera, not drawn by eye. Drawing
# them by eye produced horizontal floor rules and true-vertical walls three times
# running, which is an elevation and has no keystoning in it at all. The camera
# divides by pitched depth, so a line going away from the eye converges and a
# world-vertical leans -- and only running the real transform puts that in.
#
# Depths are in world units, signed: negative is NEARER than the lane, which is
# the floor between the player and the camera. Leaving those out left the bottom
# quarter of every guide -- the most visible floor in the picture -- with no floor
# marked on it at all.
FLOOR_DEPTHS = (-4.0, -2.0, -0.8, 1.5, 4.0, 9.0, 18.0, 40.0)
DEPTH_LINES = 9             # lines running away from the eye, across the width
DEPTH_RUN = (-5.0, -2.0, -0.5, 1.0, 3.0, 7.0, 14.0, 28.0, 60.0)
WALL_HEIGHT = 6.0           # world units, about two and a half people
WALL_UPRIGHTS = 7

# The plate screens declare pitchDegrees 0. A guide projected through a screen's
# own camera therefore has no keystoning in it at all -- correctly, because that
# camera is flat -- which is exactly what came out: uprights that leaned by 0.00
# pixels over their whole height.
#
# But a plate is a painting. The runtime blits it; its perspective is not
# enforced by any camera, it only has to MATCH the screens that are modelled, and
# those are drawn through a pitched one. So the guide is projected through the
# canon camera, taken from Alicia's Padaria, and the flat records are ignored.


def screens():
    for path in sorted((GAME / "data" / "maps").glob("*.json")):
        if not path.stem.isdigit():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        traversal = data.get("traversal") or {}
        if traversal.get("provider") != "bounded_lane":
            continue
        package = json.loads((GAME / traversal["environmentPackage"].replace(
            "assets/", "assets/", 1)).read_text(encoding="utf-8"))
        yield int(path.stem), data, traversal, package


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--maps", default="all")
    args = parser.parse_args()

    keep = None if args.maps == "all" else {int(m) for m in args.maps.split(",")}
    args.output.mkdir(parents=True, exist_ok=True)
    player = Image.open(PLAYER).convert("RGBA")
    player = player.crop(player.getbbox())

    entries = []
    for map_id, data, traversal, package in screens():
        if keep is not None and map_id not in keep:
            continue
        pre = package.get("preRendered")
        if not pre:
            # A modelled screen already IS the reference; it needs no plate.
            continue
        projection = pre["playerProjection"]
        per_unit = float(projection["pixelsPerRuntimeY"])
        centre_x = float(projection["centerX"])
        width, height = pre["imageSize"]
        anchors = package.get("anchors", {})
        centre_y = float((pre.get("lane") or {}).get("runtimeCenterY")
                         or anchors[traversal["spawnAnchor"]]["position"][1])

        # The plate's own projection, which is how the runtime turns a position
        # along the street into a column of the image. Using it means a doorway
        # drawn here lands where the player will actually walk to it.
        def column(world_y):
            return int(round(centre_x + (world_y - centre_y) * per_unit))

        cam = PlateCamera(traversal["lane"].get("depthX", 0.0), centre_y,
                          pre["imageSize"],
                          traversal["lane"].get("groundZ", 0.0), centre_x)
        ok, _, ground_row, residual = self_check(cam, projection)
        if not ok:
            raise SystemExit("map %d: the camera puts the ground on row %.1f "
                             "where the screen puts it on %s (off by %.1f)"
                             % (map_id, ground_row,
                                projection["screenY"] + projection["height"],
                                residual))
        horizon = int(round(cam.horizon_row()))
        # The ground the SCREEN uses. playerProjection.screenY IS the foot line
        # -- viewport_3d says so and draws upward from it -- so the sprite height
        # is not added to it.
        feet = int(projection["screenY"])

        def lane_at(fraction):
            """Lane position at a fraction across the plate, on the lane plane."""
            return centre_y + (fraction * width - centre_x) / per_unit

        frame = Image.new("RGB", (width, height), FIELD)
        draw = ImageDraw.Draw(frame)
        # The ground: a line at its height, not a filled mass below it. A mass
        # says "the bottom third of this picture is floor", which is a
        # composition; a line says only how high the ground is.
        draw.rectangle((0, feet, width, feet + RULE - 1), fill=LINE)

        person = int(round(cam.project(centre_y, 0.0)[1] - cam.project(centre_y, ACTOR_HEIGHT)[1]))
        mark = max(3, int(person * MARK_SIZE))
        placed = []
        for doorway in traversal.get("doorways", []):
            name = doorway.get("anchor")
            if name not in anchors:
                continue
            x = column(anchors[name]["position"][1])
            # A caret pointing at the spot. It has no width, no doorway shape and
            # no architecture: it is an arrow saying "here".
            draw.polygon([(x, feet - 1), (x - mark // 2, feet - mark),
                          (x + mark // 2, feet - mark)], fill=MARK)
            placed.append(name)

        # Floor: rulers lying flat at fixed distances back, and lines running
        # away from the eye. The second family is the one that keystones -- they
        # converge, because the camera divides by depth.
        for depth in FLOOR_DEPTHS:
            points = [cam.project(lane_at(i / 24.0), 0.0, depth)
                      for i in range(25)]
            points = [q for q in points if q]
            if len(points) > 1:
                draw.line([(int(a), int(b)) for a, b in points], fill=FLOOR_RULE)
        for step in range(DEPTH_LINES):
            lane_y = lane_at((step + 0.5) / DEPTH_LINES)
            points = [cam.project(lane_y, 0.0, d) for d in DEPTH_RUN]
            points = [q for q in points if q]
            if len(points) > 1:
                draw.line([(int(a), int(b)) for a, b in points], fill=FLOOR_RULE)

        draw.line((0, horizon, width, horizon), fill=HORIZON, width=RULE)

        # Wall uprights: world-vertical, which under a pitched camera is NOT
        # screen-vertical. Drawn as projected polylines so they lean the way the
        # engine makes them lean.
        for step in range(WALL_UPRIGHTS):
            lane_y = lane_at((step + 0.5) / WALL_UPRIGHTS)
            points = [cam.project(lane_y, h * WALL_HEIGHT / 6.0, 0.0)
                      for h in range(7)]
            points = [q for q in points if q]
            if len(points) > 1:
                draw.line([(int(a), int(b)) for a, b in points], fill=WALL_RULE)

        # One stick as tall as a person stands, so scale is stated without
        # drawing a person the model might then include.
        centre = column(centre_y)
        draw.rectangle((centre - 1, feet - person, centre, feet), fill=SCALE_MARK)

        frame = frame.resize((width * SCALE, height * SCALE), Image.NEAREST)
        name = "%02d-position.png" % map_id
        frame.save(args.output / name)
        entries.append({"mapId": map_id, "file": name,
                        "openings": [
                            {"anchor": n,
                             "fraction": round(column(anchors[n]["position"][1]) / width, 4)}
                            for n in placed],
                        "personHeightFraction": round(player.height / height, 4),
                        "groundFraction": round(feet / height, 4),
                        "horizonFraction": round(horizon / height, 4),
                        "title": data.get("title", ""),
                        "intro": data.get("intro", ""),
                        "doorways": placed,
                        "plateSize": [width, height],
                        "laneSpan": [traversal["lane"]["minY"], traversal["lane"]["maxY"]],
                        "pixelsPerRuntimeY": per_unit,
                        "outputSize": [frame.width, frame.height]})
        print("  map %-3d %-38s doorways in view: %s"
              % (map_id, data.get("title", ""), ", ".join(placed) or "none"))

    (args.output / "inputs.json").write_text(
        json.dumps({"source": "map data and environment anchors; no plate was read",
                    "frames": entries}, indent=2) + "\n", encoding="utf-8")
    print("TOWN POSITION MAPS OK screens=%d -> %s" % (len(entries), args.output))


if __name__ == "__main__":
    main()
