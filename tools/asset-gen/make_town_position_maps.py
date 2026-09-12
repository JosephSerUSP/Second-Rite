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
from town_projection import (PlateCamera, self_check, ACTOR_HEIGHT,
                             PIXELS_PER_UNIT, plate_width_for)

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "towngen"))
from build_town import WORLD_H as VISIBLE_WORLD_ROWS  # noqa: E402

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
UI_BAND = (195, 115, 245)
FIELD_STREET = (70, 180, 255, 72)
FIELD_ENTRANCE = (255, 155, 45, 58)
FIELD_ROUTE = (255, 220, 70, 64)
MARK_SIZE = 0.30            # of person height
RULE = 2

# The rulers are PROJECTED through the town camera, not drawn by eye. Drawing
# them by eye produced horizontal floor rules and true-vertical walls three times
# running, which is an elevation and has no keystoning in it at all. The camera
# divides by pitched depth, so a line going away from the eye converges and a
# world-vertical leans -- and only running the real transform puts that in.
#
# Floor rulers are placed by ROW and their depth solved, not chosen as round
# world numbers. The near floor -- between the player and the camera, filling the
# bottom of the picture -- spans about a hundred rows in ten world units, so a
# list of tidy depths marks the far floor densely and leaves most of the near
# floor bare. Twice now that was the complaint.
FLOOR_RULERS = 10           # rulers lying flat, spread down the visible floor
DEPTH_LINES = 9             # lines running away from the eye, across the width
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
    parser.add_argument("--scale", type=int, default=SCALE)
    parser.add_argument("--annotate", action="store_true",
                        help="add a legend and named transition annotations")
    parser.add_argument(
        "--spatial-fields", action="store_true",
        help="also draw shape-neutral event depth corridors from map data")
    args = parser.parse_args()

    if args.scale < 1:
        raise SystemExit("--scale must be a positive integer")

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
        lane = traversal["lane"]
        # The guide describes the plate we WANT, not the one on disk. Ten plates
        # are sized span*34.6 + 80, which is a width somebody chose with a scale
        # back-solved to fit it, and 80px of margin cannot cover a 256-wide view
        # at either end of the lane. The Praca is span*27.428571 + 256 exactly,
        # which is the camera's own scale plus a full composition of margin.
        per_unit = PIXELS_PER_UNIT
        height = pre["imageSize"][1]
        width = plate_width_for(float(lane["maxY"]) - float(lane["minY"]))
        centre_x = width / 2.0
        anchors = package.get("anchors", {})
        centre_y = float((pre.get("lane") or {}).get("runtimeCenterY")
                         or anchors[traversal["spawnAnchor"]]["position"][1])

        # The plate's own projection, which is how the runtime turns a position
        # along the street into a column of the image. Using it means a doorway
        # drawn here lands where the player will actually walk to it.
        def column(world_y):
            return int(round(centre_x + (world_y - centre_y) * per_unit))

        cam = PlateCamera(lane.get("depthX", 0.0), centre_y, (width, height),
                          lane.get("groundZ", 0.0), centre_x,
                          ground_row=float(projection["screenY"]))
        ok, _, ground_row, residual = self_check(cam, projection)
        if not ok:
            raise SystemExit("map %d: the camera puts the ground on row %.1f "
                             "where the screen puts it on %s (off by %.1f)"
                             % (map_id, ground_row,
                                projection["screenY"] + projection["height"],
                                residual))
        horizon = int(round(cam.horizon_row()))
        feet = int(round(cam.project(centre_y, 0.0)[1]))

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
        opening_records = []
        events = {event.get("instanceId"): event
                  for event in data.get("events", [])}
        for doorway in traversal.get("doorways", []):
            name = doorway.get("anchor")
            if name not in anchors:
                continue
            lane_y = float(anchors[name]["position"][1])
            x = column(lane_y)
            # A caret pointing at the spot. It has no width, no doorway shape and
            # no architecture: it is an arrow saying "here".
            draw.polygon([(x, feet - 1), (x - mark // 2, feet - mark),
                          (x + mark // 2, feet - mark)], fill=MARK)
            placed.append(name)
            event = events.get(doorway.get("eventInstanceId")) or {}
            event_name = event.get("name") or name.replace("_", " ")
            lane_min = float(lane["minY"])
            lane_max = float(lane["maxY"])
            at_edge = (abs(lane_y - lane_min) < 0.01
                       or abs(lane_y - lane_max) < 0.01)
            named_lateral_edge = (name.startswith("west_")
                                  or name.startswith("east_"))
            route_words = ("stair", "climb", " up", "down ", "down to")
            combined = (name + " " + event_name).lower()
            semantic_type = ("street" if at_edge and named_lateral_edge else
                             "route" if any(word in combined
                                            for word in route_words)
                             else "entrance")
            opening_records.append({
                "anchor": name,
                "eventName": event_name,
                "laneY": lane_y,
                "plateX": x,
                "radius": float(doorway.get("radius", 0.9)),
                "semanticType": semantic_type,
            })

        # Floor: rulers lying flat at fixed distances back, and lines running
        # away from the eye. The second family is the one that keystones -- they
        # converge, because the camera divides by depth.
        # Rows from just under the horizon to the very bottom edge, so the floor
        # is marked everywhere the floor is actually visible.
        top = horizon + max(2, (feet - horizon) // 8)
        rows = [top + (height - top) * step / (FLOOR_RULERS - 1)
                for step in range(FLOOR_RULERS)]
        depths = [d for d in (cam.depth_for_row(r) for r in rows) if d is not None]
        for depth in depths:
            # At a fixed depth, a world-horizontal floor ruler projects to a
            # screen-horizontal line. The old lane-bounded sample stopped at
            # the authored lane edges, making the ruler look like the edge of
            # a physical platform. Extend it across the complete image.
            row = cam.project(centre_y, 0.0, depth)
            if row:
                draw.line((0, int(round(row[1])), width, int(round(row[1]))),
                          fill=FLOOR_RULE)
        for step in range(DEPTH_LINES):
            lane_y = lane_at((step + 0.5) / DEPTH_LINES)
            points = [cam.project(lane_y, 0.0, d) for d in depths]
            points = [q for q in points if q]
            if len(points) > 1:
                draw.line([(int(a), int(b)) for a, b in points], fill=FLOOR_RULE)

        draw.line((0, horizon, width, horizon), fill=HORIZON, width=RULE)

        # Wall uprights: world-vertical, which under a pitched camera is NOT
        # screen-vertical. Extend the construction lines beyond the visible
        # world so they continue through the full frame instead of stopping at
        # the top of an invented wall fragment.
        for step in range(WALL_UPRIGHTS):
            lane_y = lane_at((step + 0.5) / WALL_UPRIGHTS)
            points = [cam.project(lane_y, height, 0.0)
                      for height in (-8.0, -4.0, 0.0, 4.0, 8.0, 16.0, 32.0)]
            points = [q for q in points if q]
            if len(points) > 1:
                draw.line([(int(a), int(b)) for a, b in points], fill=WALL_RULE)

        # One stick as tall as a person stands, so scale is stated without
        # drawing a person the model might then include.
        centre = column(centre_y)
        draw.rectangle((centre - 1, feet - person, centre, feet), fill=SCALE_MARK)

        # Preserve a text-free conditioning source. Labels must be added only
        # after any working-aspect pre-warp or anisotropic scaling makes them
        # unreadable and hands the image model distorted glyphs as geometry.
        clean_frame = frame.copy()

        spatial_clean = None
        spatial_annotated = None
        if args.spatial_fields:
            # Event fields describe WHERE interaction begins and which way
            # depth proceeds, while deliberately refusing to prescribe a door,
            # stair, arch, building, or other silhouette. The red caret remains
            # the exact gameplay position. A translucent corridor is only a
            # family of projected rays behind it, not an authored endpoint.
            spatial = frame.convert("RGBA")
            field_layer = Image.new("RGBA", spatial.size, (0, 0, 0, 0))
            field_draw = ImageDraw.Draw(field_layer, "RGBA")
            for record in opening_records:
                x = record["plateX"]
                lane_y = record["laneY"]
                kind = record["semanticType"]
                if kind == "street":
                    edge_x = 0 if x < centre_x else width - 1
                    lo, hi = sorted((x, edge_x))
                    field_draw.rectangle((lo, feet - 5, hi, feet + 4),
                                         fill=FIELD_STREET)
                    direction = -1 if edge_x == 0 else 1
                    tip = edge_x + 2 * direction
                    field_draw.polygon(((tip, feet),
                                        (tip - 12 * direction, feet - 8),
                                        (tip - 12 * direction, feet + 8)),
                                       fill=(70, 180, 255, 220))
                    continue

                radius = max(0.35, min(1.1, record["radius"]))
                depths = (0.0, 1.5, 3.5, 6.5, 11.0, 18.0)
                centre_points = [cam.project(lane_y, 0.0, depth)
                                 for depth in depths]
                left_points = [cam.project(lane_y - radius, 0.0, depth)
                               for depth in depths]
                right_points = [cam.project(lane_y + radius, 0.0, depth)
                                for depth in depths]
                centre_points = [point for point in centre_points if point]
                left_points = [point for point in left_points if point]
                right_points = [point for point in right_points if point]
                colour = FIELD_ROUTE if kind == "route" else FIELD_ENTRANCE
                outline = ((255, 220, 70, 210) if kind == "route"
                           else (255, 155, 45, 205))
                polygon = left_points + list(reversed(right_points))
                field_draw.polygon([(round(px), round(py)) for px, py in polygon],
                                   fill=colour)
                field_draw.line([(round(px), round(py)) for px, py in left_points],
                                fill=outline, width=1)
                field_draw.line([(round(px), round(py)) for px, py in right_points],
                                fill=outline, width=1)
                field_draw.line([(round(px), round(py)) for px, py in centre_points],
                                fill=outline, width=2)

            spatial_clean = Image.alpha_composite(spatial, field_layer).convert("RGB")
            spatial_annotated = spatial_clean.copy()
            if args.annotate:
                field_labels = ImageDraw.Draw(spatial_annotated, "RGBA")
                field_labels.rectangle((0, 0, width, 38),
                                       fill=(20, 20, 24, 232))
                field_labels.text((8, 5),
                                  "MAP-DERIVED SPATIAL FIELD - MARKS ARE NOT ARCHITECTURE",
                                  fill=LINE)
                field_labels.text((8, 17),
                                  "RED = EXACT TRIGGER | COLOURED CORRIDOR = DEPTH DIRECTION, NOT SHAPE",
                                  fill=LINE)
                field_labels.line((0, VISIBLE_WORLD_ROWS, width,
                                   VISIBLE_WORLD_ROWS), fill=UI_BAND, width=RULE)
                field_labels.rectangle((0, VISIBLE_WORLD_ROWS, width, height),
                                       fill=(80, 35, 105, 54))
                for index, record in enumerate(opening_records):
                    kind = record["semanticType"]
                    colour = ((70, 180, 255, 255) if kind == "street" else
                              (255, 220, 70, 255) if kind == "route" else
                              (255, 155, 45, 255))
                    prefix = {"street": "STREET EXIT", "route": "DEPTH ROUTE",
                              "entrance": "DEPTH ENTRANCE"}[kind]
                    label = "%s: %s" % (prefix, record["eventName"].upper())
                    x = record["plateX"]
                    label_y = 43 + (index % 2) * 18
                    bounds = field_labels.textbbox((0, 0), label)
                    label_w = bounds[2] - bounds[0]
                    label_x = max(3, min(width - label_w - 7,
                                         x - label_w // 2))
                    field_labels.rectangle((label_x - 3, label_y - 2,
                                            label_x + label_w + 3, label_y + 11),
                                           fill=(25, 25, 30, 205))
                    field_labels.text((label_x, label_y), label, fill=colour)
                    field_labels.line((x, label_y + 12, x, feet - mark - 2),
                                      fill=colour, width=1)

        if args.annotate:
            # These labels are authoring metadata, not scene geometry. They
            # deliberately explain the line families so a multimodal model
            # does not turn a clipped ruler into a platform edge.
            draw.text((8, 6), "WORLD GEOMETRY GUIDE - NOT FINAL ART", fill=LINE)
            draw.text((8, 16), "FIXED PERSPECTIVE 3D CAMERA / WALK LEFT-RIGHT", fill=LINE)
            draw.text((8, 26), "GREEN FLOOR PLANE | YELLOW WORLD VERTICALS | WHITE GROUND | RED THRESHOLDS", fill=LINE)
            draw.text((width - 250, 6), "HORIZON / SKY", fill=HORIZON)
            draw.text((width - 250, 16), "FLOOR CONTINUES OFF BOTH SIDES", fill=FLOOR_RULE)
            draw.line((0, VISIBLE_WORLD_ROWS, width, VISIBLE_WORLD_ROWS),
                      fill=UI_BAND, width=RULE)
            draw.text((8, VISIBLE_WORLD_ROWS + 4),
                      "PERSISTENT SEMITRANSPARENT UI BELOW - DEAD FOREGROUND; NO ESSENTIAL EXITS",
                      fill=UI_BAND)
            for doorway in traversal.get("doorways", []):
                name = doorway.get("anchor")
                if name not in anchors:
                    continue
                x = column(anchors[name]["position"][1])
                draw.text((max(2, min(width - 180, x - 20)),
                           max(40, feet - mark - 14)),
                          name, fill=MARK)

        clean_frame = clean_frame.resize(
            (width * args.scale, height * args.scale), Image.NEAREST)
        clean_name = "%02d-position-clean.png" % map_id
        clean_frame.save(args.output / clean_name)
        frame = frame.resize((width * args.scale, height * args.scale), Image.NEAREST)
        name = "%02d-position.png" % map_id
        frame.save(args.output / name)
        spatial_clean_name = None
        spatial_name = None
        if spatial_clean is not None:
            spatial_clean = spatial_clean.resize(
                (width * args.scale, height * args.scale), Image.NEAREST)
            spatial_clean_name = "%02d-spatial-field-clean.png" % map_id
            spatial_clean.save(args.output / spatial_clean_name)
            spatial_annotated = spatial_annotated.resize(
                (width * args.scale, height * args.scale), Image.NEAREST)
            spatial_name = "%02d-spatial-field.png" % map_id
            spatial_annotated.save(args.output / spatial_name)
        entries.append({"mapId": map_id, "file": name,
                        "cleanFile": clean_name,
                        "spatialFieldFile": spatial_name,
                        "spatialFieldCleanFile": spatial_clean_name,
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
                        "eventFields": opening_records,
                        "plateSize": [width, height],
                        "currentPlateSize": pre["imageSize"],
                        "pixelsPerRuntimeY": PIXELS_PER_UNIT,
                        "groundRow": feet,
                        "persistentUiBeginsRow": VISIBLE_WORLD_ROWS,
                        "persistentUiFraction": round(VISIBLE_WORLD_ROWS / height, 4),
                        "laneSpan": [traversal["lane"]["minY"], traversal["lane"]["maxY"]],
                        "outputSize": [frame.width, frame.height],
                        "scale": args.scale,
                        "annotated": args.annotate})
        print("  map %-3d %-38s doorways in view: %s"
              % (map_id, data.get("title", ""), ", ".join(placed) or "none"))

    (args.output / "inputs.json").write_text(
        json.dumps({"source": "map data and environment anchors; no plate was read",
                    "frames": entries}, indent=2) + "\n", encoding="utf-8")
    print("TOWN POSITION MAPS OK screens=%d -> %s" % (len(entries), args.output))


if __name__ == "__main__":
    main()
