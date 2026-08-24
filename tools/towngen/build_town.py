"""Build the St. Maria side-view town: environment packages and map data.

Nine screens are almost entirely formulaic - the same camera, the same
projection, the same manifest shape - so they are generated from one table
rather than hand-written nine times. The parts that are not formulaic are in
SCREENS: which plate, where the painted doors are, and who stands where.

Authored dialogue is never retyped. Every migrated NPC copies its `commands`
array verbatim out of `data/maps/1.json` by event name, so the existing
writing crosses over byte-for-byte.

Usage:
    python tools/towngen/build_town.py
"""

import io
import json
import os

from PIL import Image

PROJECT = os.path.join("projects", "hichaukitoden-game")
DATA = os.path.join(PROJECT, "data")
MAPS = os.path.join(DATA, "maps")
ENV_ROOT = os.path.join(PROJECT, "assets", "environments", "st_maria_town")
PLATE_REL = "assets/environments/st_maria_town/plates"

NATIVE_W, NATIVE_H = 426, 240
# Plates are no longer a fixed width: a street earns its length and a room does
# not, and the runtime scrolls a window across whatever width the plate has.
# Everything positional is therefore read from the plate rather than assumed.
LANE_MARGIN_PX = 40
# Lane units per SECOND. Walking is continuous now, not one step per key event,
# so this is a speed rather than a stride. At this rate the Praca - the widest
# screen in the town - takes about seven seconds to cross end to end.
WALK_SPEED = 3.4
# The persistent dock owns y 144..240, so the visible world is 426x144 and
# the actor must stand inside it. Feet sit just above the dock line; the
# plates are composed with their ground strip running up to it.
WORLD_H = 144
CENTER_X = 213.0
PIXELS_PER_Y = 34.6
DEPTH_X = 7.8
GROUND_Z = -1.5
FOV_DEGREES = 28.072486935852957


def plate_size(plate):
    with Image.open(os.path.join(ENV_ROOT, "plates", plate)) as image:
        return image.size


def lane_of(plate):
    """Lane bounds and projection for one plate, derived from its real width.

    Lane units stay the same size everywhere - PIXELS_PER_Y is fixed - so a
    longer street is more lane, not faster walking. The lane stops short of the
    plate edge by a margin so the actor never straddles it.
    """
    width, _height = plate_size(plate)
    centre_x = width / 2.0
    span = (width - 2 * LANE_MARGIN_PX) / PIXELS_PER_Y
    return {
        "width": width,
        "centerX": centre_x,
        "minY": 0.0,
        "maxY": round(span, 3),
        "centre": round(span / 2.0, 3),
    }


def ground_profile(plate, authored):
    """Author a floor in PLATE PIXELS; emit it in world units.

    An artist reads a step off the picture -- "the counter is 48 pixels above
    the tables" -- so that is how it is written here. What ships is world
    height, because a 3D scene substituted for the plate has a floor at a
    world height and the profile should describe it rather than the picture.

    `authored` is [(pixel_x, pixels_above_base), ...] running west to east.
    Between two points the floor is a straight ramp, so the distance between
    them IS the length of the steps or the slope.
    """
    if not authored:
        return None
    return [{"y": lane_y_for(plate, pixel_x),
             "z": round(GROUND_Z + rise / PIXELS_PER_Y, 4)}
            for pixel_x, rise in authored]


def lane_y_for(plate, pixel_x):
    """Plate pixel x -> lane y, for the plate's own width."""
    lane = lane_of(plate)
    return round((pixel_x - lane["centerX"]) / PIXELS_PER_Y + lane["centre"], 3)


# key: (map id, title, plate, intro, lane min/max, feet screenY, npcs, doors)
#   npcs:  (anchor_name, source_event_name_in_map_1, sprite, pixel_x)
#   doors: (anchor_name, label, target_map, arrival_anchor_on_target, pixel_x,
#           source_event_name_or_None)
SCREENS = {
    # Map 16 was the Gate screen at the west end of a linear town, which made
    # the most important thing in St. Maria read as the least. It is now the
    # churchyard: a terrace above the rooftops, reached by climbing the stair
    # in the middle of the square, holding the sealed door.
    "churchyard": dict(
        id=16, title="St. Maria - The Churchyard", plate="churchyard_bg.png",
        intro="Above the rooftops, where the town keeps the thing it is afraid of. Two lamps are kept burning.",
        screen_y=136, music="town1",
        npcs=[("guard", "Gate Guard", "npc_gate_guard", 520)],
        doors=[
            ("labyrinth_door", "Labyrinth Gate", 2, None, 330, "Labyrinth Gate"),
            ("down_praca", "Down to the Praca", 17, "churchyard_stair", 75, None),
        ],
    ),
    "praca": dict(
        id=17, title="St. Maria - The Praca", plate="praca_stair_bg.png",
        intro="The fountain never stops. Above the square, the churchyard stair goes up to the sealed door.",
        screen_y=136, music="town1",
        npcs=[("registrar", "Registrar", "npc_registrar", 660),
              ("child", None, "npc_child", 300)],
        doors=[
            ("laura_door", "Laura's door", 23, "exit_door", 55, None),
            ("chapel_door", "Chapel", 22, "exit_door", 215, None),
            ("churchyard_stair", "The Churchyard", 16, "down_praca", 435, None),
            ("alicia_door", "Alicia's door", 24, "exit_door", 800, None),
            ("alley", "The Backstreet", 26, "alley_mouth", 880, None),
            ("east_market", "Market Row", 18, "west_praca", 960, None),
        ],
    ),
    "market": dict(
        id=18, title="St. Maria - Market Row", plate="market_bg.png",
        intro="Awnings sag with the morning's rain. Most of the stalls are already empty.",
        screen_y=136, music="town1",
        npcs=[("auctioneer", "Auctioneer", "npc_auctioneer", 200),
              ("yukio", "Yukio", "npc_yukio", 300),
              ("euler", "Euler", "npc_euler", 350),
              ("scholar", "Scholar", "npc_scholar", 640)],
        doors=[
            ("west_praca", "The Praca", 17, "east_market", 40, None),
            ("back_steps", "The Backstreet", 26, "market_steps", 420, None),
            ("smith_door", "Weaponsmith", 20, "exit_door", 555, None),
            ("east_quay", "The Quay", 19, "market_road", 720, None),
        ],
    ),
    "quay": dict(
        id=19, title="St. Maria - The Quay", plate="quay_bg.png",
        intro="The town ends at the water. The fog does not.",
        screen_y=136, music="town1",
        npcs=[("fisherman", None, "npc_fisherman", 150),
              ("sign", "Sign", None, 330)],
        doors=[
            ("pub_door", "The Pub", 21, "exit_door", 442, None),
            ("market_road", "Market Row", 18, "east_quay", 560, None),
        ],
    ),
    "backstreet": dict(
        id=26, title="St. Maria - The Backstreet", plate="backstreet_bg.png",
        intro="Laundry, back doors and a lit shrine. The side of the town that does not face the square.",
        screen_y=136, music="town1",
        npcs=[],
        doors=[
            ("alley_mouth", "The Praca", 17, "alley", 60, None),
            # The rented room from the opening now opens off this lane, which
            # is the only reason a player can ever return to it.
            ("lodging_door", "Passage House", 25, "exit_door", 300, None),
            ("market_steps", "Market Row", 18, "back_steps", 760, None),
        ],
    ),
    # --- interiors ---
    # Every room puts its way out in the left wall, so its west bound and its
    # painted door are the same place: walking left leaves, and so does UP.
    "weaponsmith": dict(
        id=20, title="St. Maria - Weaponsmith", plate="weaponsmith_bg.png",
        intro="The forge is banked low. Everything in the room is either iron or waiting to be.",
        screen_y=136, music="town1",
        npcs=[("smith", "Weapon Shop", "npc_weaponsmith", 300)],
        doors=[("exit_door", "Out to Market Row", 18, "smith_door", 140, None)],
    ),
    "pub": dict(
        id=21, title="St. Maria - The Pub", plate="pub_bg.png",
        intro="Warm, low and smoke-dark. The only room in St. Maria that argues with the weather.",
        screen_y=136, music="town1",
        # The one screen with a real step across the walking line: the tables
        # are on the low floor by the door, and the bar stands on a platform
        # up a short flight. Measured off the plate.
        ground=[(0, 0), (290, 0), (335, 22), (426, 22)],
        npcs=[("owner", "Pub Owner", "npc_pub_owner", 370)],
        doors=[("exit_door", "Out to the Quay", 19, "pub_door", 100, None)],
    ),
    "chapel": dict(
        id=22, title="St. Maria - Chapel", plate="chapel_bg.png",
        intro="Blue tiles, cold wax, and a door that is never locked.",
        screen_y=136, music="town1",
        npcs=[("agnes", "EV012", "npc_agnes", 330)],
        doors=[("exit_door", "Out to the Praca", 17, "chapel_door", 90, None)],
    ),
    "house_laura": dict(
        id=23, title="St. Maria - Laura's House", plate="house_laura_bg.png",
        intro="A hearth, a scrubbed table, and more tools than a kitchen needs.",
        screen_y=136, music="town1",
        npcs=[("laura", "Laura", "npc_laura", 300)],
        doors=[("exit_door", "Out to the Praca", 17, "laura_door", 95, None)],
    ),
    "house_alicia": dict(
        id=24, title="St. Maria - Alicia's Room", plate="house_alicia_bg.png",
        intro="A narrow bed, a desk of papers, and the balcony door left open to the grey.",
        screen_y=136, music="town1",
        npcs=[("alicia", "Alicia", "npc_alicia", 205)],
        doors=[("exit_door", "Out to the Praca", 17, "alicia_door", 58, None)],
    ),
    # The opening cinematic ends in a rented room ("PASSAGE HOUSE - ROOM 3",
    # "this'll be home for both of you"). It exists as a screen so that
    # authored text does not have to be rewritten to fit the new town.
    "lodging": dict(
        id=25, title="St. Maria - Passage House", plate="lodging_bg.png",
        intro="Two beds, a washstand, and a window that does not close properly. It is paid for until spring.",
        screen_y=136, music="town1",
        npcs=[],
        doors=[("exit_door", "Out to the Backstreet", 26, "lodging_door", 78, None)],
    ),
}

# Written for NPCs that have no map-1 ancestor. Short, in register, and never
# contradicting the authored dialogue that crosses over.
INVENTED = {
    "child": [{"cmd": "TEXT", "text": "\"My father says the fog is the Labyrinth breathing out.\" She keeps her toy boat behind her back."}],
    "fisherman": [{"cmd": "TEXT", "text": "\"Nothing worth catching today.\" He does not stop coiling the rope. \"Nothing worth catching most days.\""}],
}


def load_map1_commands():
    with io.open(os.path.join(MAPS, "1.json"), encoding="utf-8") as handle:
        data = json.load(handle)
    return {event.get("name"): event.get("commands", []) for event in data["events"]}


def write_json(path, value):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def build_stub():
    """The manifest requires mesh/material/atlas paths even for a flat screen."""
    stub = os.path.join(ENV_ROOT, "stub")
    os.makedirs(stub, exist_ok=True)
    with io.open(os.path.join(stub, "quad.obj"), "w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Placeholder geometry for a pre-rendered screen.\n"
                     "# Nothing draws this; the manifest contract requires a mesh path.\n"
                     "mtllib quad.mtl\no th_render_stub\n"
                     "v -1 0 -1\nv 1 0 -1\nv 1 0 1\nv -1 0 1\n"
                     "vt 0 0\nvt 1 0\nvt 1 1\nvt 0 1\n"
                     "usemtl stub\nf 1/1 2/2 3/3 4/4\n")
    with io.open(os.path.join(stub, "quad.mtl"), "w", encoding="utf-8", newline="\n") as handle:
        handle.write("newmtl stub\nKd 1.000 1.000 1.000\nd 1.0\nillum 1\n")
    Image.new("RGBA", (NATIVE_W, NATIVE_H), (0, 0, 0, 0)).save(os.path.join(stub, "empty.png"))
    Image.new("RGBA", (4, 4), (255, 255, 255, 255)).save(os.path.join(stub, "atlas.png"))


def build_environment(key, screen):
    lane = lane_of(screen["plate"])
    anchors = {"spawn_player": {"position": [DEPTH_X, lane["centre"], GROUND_Z]}}
    for anchor, _label, _target, _arrival, pixel_x, _source in screen["doors"]:
        anchors[anchor] = {
            "position": [DEPTH_X, lane_y_for(screen["plate"], pixel_x), GROUND_Z]}
    for anchor, _source, _sprite, pixel_x in screen["npcs"]:
        anchors["npc_" + anchor] = {
            "position": [DEPTH_X, lane_y_for(screen["plate"], pixel_x), GROUND_Z]}
    manifest = {
        "contractVersion": 1,
        "renderMesh": "../stub/quad.obj",
        "materialLibrary": "../stub/quad.mtl",
        "textureAtlas": "../stub/atlas.png",
        "collisionMesh": "../stub/quad.obj",
        "bounds": [DEPTH_X - 1.0, lane["minY"], GROUND_Z - 1.0,
                   DEPTH_X + 1.0, lane["maxY"], GROUND_Z + 4.0],
        "anchors": anchors,
        "preRendered": {
            "mode": "layered_2d",
            "imageSize": [lane["width"], NATIVE_H],
            "slicePositions": [lane["centre"]],
            "backgrounds": ["../../../../" + PLATE_REL + "/" + screen["plate"]],
            "scenes": ["../../../../" + PLATE_REL + "/" + screen["plate"]],
            "foregrounds": ["../stub/empty_%d.png" % lane["width"]],
            "lane": {"runtimeCenterY": lane["centre"]},
            "playerProjection": {
                "centerX": lane["centerX"],
                "screenY": screen["screen_y"],
                "width": 24,
                "height": 48,
                "pixelsPerRuntimeY": PIXELS_PER_Y,
            },
        },
    }
    write_json(os.path.join(ENV_ROOT, key, "environment.json"), manifest)
    # The transparent foreground must match its plate's dimensions.
    empty = os.path.join(ENV_ROOT, "stub", "empty_%d.png" % lane["width"])
    if not os.path.exists(empty):
        Image.new("RGBA", (lane["width"], NATIVE_H), (0, 0, 0, 0)).save(empty)


def lane_block(screen, lane):
    block = {"minY": lane["minY"], "maxY": lane["maxY"], "depthX": DEPTH_X,
             "groundZ": GROUND_Z, "speed": WALK_SPEED}
    profile = ground_profile(screen["plate"], screen.get("ground"))
    if profile:
        block["groundProfile"] = profile
    return block


def build_map(key, screen, map1):
    lane = lane_of(screen["plate"])
    plate = screen["plate"]
    events = []
    next_id = screen["id"] * 100 + 1

    for anchor, source, sprite, pixel_x in screen["npcs"]:
        commands = map1.get(source) if source else INVENTED.get(anchor)
        if commands is None:
            raise SystemExit("no dialogue for %s/%s" % (key, anchor))
        event = {
            "id": next_id,
            "instanceId": "st-maria-%s-%s" % (key, anchor),
            "name": anchor.replace("_", " ").title(),
            "x": 0, "y": 0,
            "worldPosition": [DEPTH_X, lane_y_for(plate, pixel_x), GROUND_Z],
            "trigger": "interact",
            "commands": commands,
        }
        if sprite:
            event.update({
                "sprite": "assets/character/town/%s.png" % sprite,
                "frameWidth": 24, "frameHeight": 48, "frameIndex": 0,
                "worldHeight": 1.75,
            })
        events.append(event)
        next_id += 1

    for anchor, label, target, arrival, pixel_x, source in screen["doors"]:
        if source and map1.get(source):
            commands = map1[source]
        else:
            command = {"cmd": "LOAD_MAP", "mapId": target}
            if arrival:
                command["arrival"] = arrival
            commands = [command]
        events.append({
            "id": next_id,
            "instanceId": "st-maria-%s-%s" % (key, anchor),
            "name": label,
            "x": 0, "y": 0,
            "worldPosition": [DEPTH_X, lane_y_for(plate, pixel_x), GROUND_Z],
            "trigger": "bump",
            "commands": commands,
        })
        next_id += 1

    doorways = [{"anchor": anchor, "eventInstanceId": "st-maria-%s-%s" % (key, anchor),
                 "radius": 0.9}
                for anchor, _l, _t, _a, _p, _s in screen["doors"]]

    write_json(os.path.join(MAPS, "%d.json" % screen["id"]), {
        "id": screen["id"],
        "title": screen["title"],
        "intro": screen["intro"],
        "depth": 0,
        "safe": True,
        "category": "town",
        "generation": "Fixed",
        "tileset": "town_default",
        "ceilingStyle": "sky",
        "music": screen["music"],
        "layout": ["."],
        "spawn": {"x": 0, "y": 0, "dir": "E"},
        "traversal": {
            "provider": "bounded_lane",
            "environmentPackage": "assets/environments/st_maria_town/%s/environment.json" % key,
            "spawnAnchor": "spawn_player",
            "lane": lane_block(screen, lane),
            "blockedRanges": [],
            "camera": {
                "profile": "town_sideview",
                "target": {"x": DEPTH_X, "y": lane["centre"], "z": 0.0},
                "distance": 21.1175,
                "yawDegrees": 0.0,
                "pitchDegrees": 0.0,
                "fovDegrees": FOV_DEGREES,
                "nearPlane": 0.05,
                "farPlane": 128.0,
                "projectionScale": {"x": 1.0, "y": 1.0},
                "projectionFrame": {"canonicalCenterX": 213, "canonicalHorizonY": 110},
                "tracking": {
                    "axis": "y", "center": lane["centre"],
                    "minOffsetX": 0, "maxOffsetX": 0,
                    "interpolationSpeed": 12.0,
                    "movementInterpolationSpeed": 14.0,
                    "animationFps": 8.0,
                },
            },
            "doorways": doorways,
        },
        "events": events,
        "treasures": [],
        "encounters": [],
        "recruits": [],
    })


def main():
    map1 = load_map1_commands()
    build_stub()
    for key, screen in SCREENS.items():
        build_environment(key, screen)
        build_map(key, screen, map1)
        print("built %-13s map %d" % (key, screen["id"]))

    index_path = os.path.join(MAPS, "index.json")
    with io.open(index_path, encoding="utf-8") as handle:
        index = json.load(handle)
    files = index.get("files", [])
    for screen in SCREENS.values():
        name = "%d.json" % screen["id"]
        if name not in files:
            files.append(name)
    index["files"] = sorted(files, key=lambda n: int(n.split(".")[0]))
    write_json(index_path, index)

    # The opening cinematic loaded the 3D grid town directly. Repoint it at the
    # lodging room its own text describes, by id rather than by position, so a
    # rebuild stays correct if the command list moves.
    commons_path = os.path.join(DATA, "commonEvents.json")
    with io.open(commons_path, encoding="utf-8") as handle:
        commons = json.load(handle)
    repointed = 0
    for common in commons.values():
        if common.get("name") != "Opening - Arrival at St. Maria":
            continue
        for command in common.get("commands", []):
            if command.get("cmd") == "LOAD_MAP" and command.get("mapId") == 1:
                command["mapId"] = SCREENS["lodging"]["id"]
                repointed += 1
    if repointed:
        write_json(commons_path, commons)
    print("opening cinematic transfers repointed: %d" % repointed)

    # Classic is the intended gameplay experience. A wider profile reveals
    # more of the same plate rather than stretching it, so the Project states
    # its intent instead of leaving the default implicit.
    engine_path = os.path.join(DATA, "engine.json")
    with io.open(engine_path, encoding="utf-8") as handle:
        engine = json.load(handle)
    engine.setdefault("ui", {})["renderSurfaceProfile"] = "classic"
    write_json(engine_path, engine)
    print("render surface profile authored: classic")

    system_path = os.path.join(DATA, "system.json")
    with io.open(system_path, encoding="utf-8") as handle:
        system = json.load(handle)
    system["spawn"] = {"mapId": SCREENS["praca"]["id"], "x": 0, "y": 0, "dir": "E"}
    write_json(system_path, system)
    print("new game now starts on map %d" % SCREENS["praca"]["id"])
    print("TOWN BUILD OK")


if __name__ == "__main__":
    main()
