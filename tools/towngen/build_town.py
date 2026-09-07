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
TRANSITION_ARROW_MODEL = "assets/models/st_maria/transition_arrow.obj"

NATIVE_W, NATIVE_H = 426, 240
# A plate carries the complete composition around the runtime lane. The current
# contract is 128 px of composition on either side; the old plates used 40 px.
# Keep both values because positions are authored in stable runtime lane units
# and must be convertible while screens migrate one at a time.
LANE_MARGIN_PX = 128
LEGACY_LANE_MARGIN_PX = 40
# Lane units per SECOND. Walking is continuous now, not one step per key event,
# so this is a speed rather than a stride. At this rate the Praca - the widest
# screen in the town - takes about seven seconds to cross end to end.
WALK_SPEED = 3.4
# The persistent dock owns y 144..240, so the visible world is 426x144 and
# the actor must stand inside it. Feet sit just above the dock line; the
# plates are composed with their ground strip running up to it.
WORLD_H = 144
CENTER_X = 213.0
# The camera contract's 48 px / 1.75 m = 27.428571 px per runtime lane unit.
# The scale belongs to each screen so an incremental migration can coexist with
# any deliberately retained legacy plate.
PIXELS_PER_Y = 48.0 / 1.75
LEGACY_PIXELS_PER_Y = 34.6
DEPTH_X = 7.8
GROUND_Z = 0.0
FOV_DEGREES = 28.072486935852957

# These widths are calculated from the committed lane spans and the new
# composition contract. They are explicit because a candidate plate must be
# rejected before it can alter a map or manifest.
EXPECTED_PLATE_WIDTHS = {
    "churchyard_bg.png": 924,
    "market_bg.png": 696,
    "quay_bg.png": 826,
    "lauras_smith_bg.png": 450,
    "pub_bg.png": 576,
    "chapel_bg.png": 674,
    "house_laura_bg.png": 747,
    "house_alicia_bg.png": 424,
    "lodging_bg.png": 457,
    "backstreet_bg.png": 866,
    "alicias_padaria_bg.png": 450,
    "port_bg.png": 1065,
    "praca_plate.png": 906,
}


def plate_size(plate):
    with Image.open(os.path.join(ENV_ROOT, "plates", plate)) as image:
        return image.size


def screen_scale(screen):
    value = screen.get("pixels_per_y")
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
        raise ValueError("screen %r needs a positive pixels_per_y" % screen.get("id"))
    return float(value)


def screen_margin(screen):
    value = screen.get("plate_margin_px", LANE_MARGIN_PX)
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
        raise ValueError("screen %r needs a non-negative plate_margin_px" % screen.get("id"))
    return float(value)


def plate_width(screen):
    value = screen.get("plate_width")
    if value is None:
        value = EXPECTED_PLATE_WIDTHS.get(screen.get("plate"))
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError("screen %r needs an integer plate_width" % screen.get("id"))
    return value


def stable_lane_y(screen, legacy_pixel_x):
    """Return the stable runtime coordinate behind an old pixel coordinate."""
    margin = screen.get("legacy_plate_margin_px", LEGACY_LANE_MARGIN_PX)
    scale = screen.get("legacy_pixels_per_y", LEGACY_PIXELS_PER_Y)
    return round((legacy_pixel_x - margin) / scale, 4)


def plate_pixel_x(screen, legacy_pixel_x):
    """Project an authored legacy coordinate into this screen's plate."""
    return round(screen_margin(screen) + stable_lane_y(screen, legacy_pixel_x) *
                 screen_scale(screen), 3)


def screen_lane(screen):
    return lane_of(screen["plate"], screen_scale(screen), screen_margin(screen),
                   plate_width(screen), screen.get("lane_min_y", 0.0),
                   screen.get("lane_max_y"))


def lane_of(plate, pixels_per_y=PIXELS_PER_Y, margin_px=LANE_MARGIN_PX,
            width=None, min_y=0.0, max_y=None):
    """Lane bounds and projection for one plate, derived from its real width.

    A screen declares how many plate pixels equal one runtime unit. A longer
    plate at that screen's scale is more lane, not faster walking. The lane
    stops short of the plate edge so the actor never straddles it.
    """
    if width is None:
        width, _height = plate_size(plate)
    span = ((width - 2 * margin_px) / pixels_per_y
            if max_y is None else max_y - min_y)
    resolved_max_y = round(min_y + span, 3) if max_y is None else round(max_y, 3)
    centre_y = round((min_y + resolved_max_y) / 2.0, 4)
    centre_x = round(margin_px + (centre_y - min_y) * pixels_per_y, 3)
    return {
        "width": width,
        "centerX": centre_x,
        "minY": round(min_y, 3),
        "maxY": resolved_max_y,
        "centre": centre_y,
    }


def ground_profile(screen, authored):
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
    scale = screen_scale(screen)
    margin = screen_margin(screen)
    return [{"y": lane_y_for(pixel_x, scale, margin),
             "z": round(GROUND_Z + rise / scale, 4)}
            for pixel_x, rise in authored]


def profile_ground_at(profile, y):
    if not profile:
        return GROUND_Z
    if y <= profile[0]["y"]:
        return profile[0]["z"]
    for i in range(1, len(profile)):
        prev, curr = profile[i - 1], profile[i]
        if y <= curr["y"]:
            span = curr["y"] - prev["y"]
            if span <= 0:
                return curr["z"]
            t = (y - prev["y"]) / span
            return round(prev["z"] + (curr["z"] - prev["z"]) * t, 4)
    return profile[-1]["z"]


def lane_y_for(*args, **kwargs):
    """Plate pixel x -> lane y, for the plate's own width.

    Supports:
        lane_y_for(pixel_x)
        lane_y_for(pixel_x, scale)
        lane_y_for(pixel_x, scale, margin)
        lane_y_for(plate, pixel_x, scale, margin)
    """
    if len(args) == 1:
        px = args[0]
        scale = kwargs.get("pixels_per_y", PIXELS_PER_Y)
        margin = kwargs.get("margin_px", LANE_MARGIN_PX)
    elif len(args) == 2:
        if isinstance(args[0], str):
            plate, px = args
            scale = kwargs.get("pixels_per_y", PIXELS_PER_Y)
            margin = kwargs.get("margin_px", LANE_MARGIN_PX)
        else:
            px, scale = args
            margin = kwargs.get("margin_px", LANE_MARGIN_PX)
    elif len(args) == 3:
        if isinstance(args[0], str):
            plate, px, scale = args
            margin = kwargs.get("margin_px", LANE_MARGIN_PX)
        else:
            px, scale, margin = args
    elif len(args) >= 4:
        plate, px, scale, margin = args[:4]
    else:
        raise ValueError("lane_y_for requires at least pixel_x")
    return round((px - margin) / scale, 4)


# key: (map id, title, plate, intro, lane min/max, feet screenY, npcs, doors)
#   npcs:  (anchor_name, source_event_name_in_map_1, sprite, pixel_x)
#   doors: (anchor_name, label, target_map, arrival_anchor_on_target, pixel_x,
#           source_event_name_or_None, direction)
SCREENS = {
    # --- the spiral -------------------------------------------------------
    # St. Maria wraps a small island once, and the wrap DESCENDS: the sealed
    # gate is at the top, the water is at the bottom. Height is monotonic, so
    # no screen has to announce which level it is on - it can be seen.
    #
    # The streets are an open chain of six. Every screen spends both of its
    # street exits on its neighbours, so every further connection is a stair or
    # a passage authored inside the bounds. Those are the CHORDS, and they are
    # what stops a ring from being a folded line:
    #
    #   the climb        Port 31  <-> Churchyard 16   closes the loop
    #   the water stair  Praca 17 <-> Quay 19         public, broad, slow
    #   the workers'     Cortico 26 <-> Port 31       steep, for people who
    #     stair                                       live in one and work the
    #                                                 other
    #   the padaria      Market 18 <-> Cortico 26     THROUGH the building: the
    #                                                 shop fronts the low
    #                                                 street, the home backs
    #                                                 onto the high lane
    #
    # A street exit sits on a lane bound: pixel 128 at the west and (width - 128)
    # at the east. Anything else is a door, gate, or stair.
    "churchyard": dict(
        pixels_per_y=PIXELS_PER_Y,
        plate_view_transform="Standard",
        id=16, title="St. Maria - The Churchyard", plate="churchyard_bg.png",
        intro="Above the rooftops, where the town keeps the thing it is afraid of. Two lamps are kept burning.",
        screen_y=136, music="town1",
        npcs=[("guard", "Gate Guard", "npc_gate_guard", 570.0)],
        doors=[
            # The seaward bound is a cliff, not a street: the way down to the
            # water is the climb, and it is authored as a stair.
            ("port_climb", "Down to the Port", 31, "climb_churchyard", 128.0, None, "away", 1.8),
            ("labyrinth_door", "Labyrinth Gate", 2, None, 499.0, "Labyrinth Gate", "away", 2.0),
            ("east_praca", "The Praca", 17, "churchyard_stair", 924.0, None, "right"),
        ],
    ),
    "praca": dict(
        pixels_per_y=PIXELS_PER_Y,
        plate_view_transform="Standard",
        id=17, title="St. Maria - The Praca", plate="praca_plate.png",
        intro="The fountain never stops. Between the roofs, on every side, the sea.",
        screen_y=136, music="town1",
        npcs=[("child", None, "npc_child", 480)],
        doors=[
            ("west_churchyard", "The Churchyard", 16, "east_praca", 40, None, "left"),
            ("quay_stair", "Down to the Quay", 19, "praca_stair", 150, None, "away"),
            ("chapel_door", "Chapel", 22, "exit_door", 620, None, "away"),
            ("east_cortico", "The Cortico", 26, "west_praca", 860, None, "right"),
        ],
    ),
    "cortico": dict(
        pixels_per_y=PIXELS_PER_Y,
        plate_view_transform="Standard",
        id=26, title="St. Maria - The Cortico", plate="backstreet_bg.png",
        intro="One address, many households. Laundry across the court, and a lit shrine in a niche that was cut for something else.",
        screen_y=136, music="town1",
        npcs=[("scholar", "Scholar", "npc_scholar", 180.0),
              ("euler", "Euler", "npc_euler", 360.0)],
        doors=[
            ("west_praca", "The Praca", 17, "east_backstreet", 50.0, None, "left"),
            ("lodging_door", "Passage House", 25, "exit_door", 415.0, None, "away", 0.9),
            ("padaria_back", "The padaria's back door", 23, "exit_door", 505.0, None, "away", 1.5),
            ("port_stair", "Down to the Port", 31, "cortico_stair", 680.0, None, "away", 1.2),
            ("east_market", "Market Row", 18, "west_cortico", 866.0, None, "right"),
        ],
    ),
    "market": dict(
        pixels_per_y=PIXELS_PER_Y,
        plate_view_transform="Standard",
        id=18, title="St. Maria - Market Row", plate="market_bg.png",
        intro="Awnings sag with the morning's rain. Below the stalls, roofs, and then the water.",
        screen_y=136, music="town1",
        npcs=[("auctioneer", "Auctioneer", "npc_goustav", 174.0),
              ("yukio", "Yukio", "npc_yukio", 314.0)],
        doors=[
            ("west_cortico", "The Cortico", 26, "east_market", 128.0, None, "left"),
            ("padaria_door", "Alicia's Padaria", 27, "exit_door", 488.0, None, "away", 0.9),
            ("east_quay", "The Quay", 19, "west_market", 696.0, None, "right"),
        ],
    ),
    "quay": dict(
        pixels_per_y=PIXELS_PER_Y,
        plate_view_transform="Standard",
        id=19, title="St. Maria - The Quay", plate="quay_bg.png",
        intro="Wet stone and the smell of the tide. The fog does not end where the town does.",
        screen_y=136, music="town1",
        npcs=[("fisherman", None, "npc_fisherman", 175.0)],
        doors=[
            ("west_market", "Market Row", 18, "east_quay", 128.0, None, "left"),
            ("praca_stair", "Up to the Praca", 17, "quay_stair", 485.0, None, "away", 2.2),
            ("pub_door", "The Pub", 21, "exit_door", 730.0, None, "away", 0.9),
            ("east_port", "The Port", 31, "west_quay", 826.0, None, "right"),
        ],
    ),
    "port": dict(
        pixels_per_y=PIXELS_PER_Y,
        plate_view_transform="Standard",
        id=31, title="St. Maria - The Port", plate="port_bg.png",
        intro="Shipping, and one hull that has not moved in a long time. Nothing between here and the horizon.",
        screen_y=136, music="town1",
        ground=[(0.0, 0.0), (820.0, 0.0), (940.0, 16.0), (1065.0, 16.0)],
        npcs=[],
        doors=[
            ("west_quay", "The Quay", 19, "east_port", 128.0, None, "left"),
            ("forge_door", "The forge", 20, "exit_door", 360.0, None, "away", 1.2),
            ("smith_3d_door", "Laura's Smithy (3D)", 29, "exit_door", 589.0, None, "away", 0.9),
            ("cortico_stair", "Up to the Cortico", 26, "port_stair", 650.0, None, "away", 1.2),
            ("climb_churchyard", "The long climb", 16, "port_climb", 915.0, None, "away", 3.0),
        ],
    ),
    # --- interiors ---
    "weaponsmith": dict(
        pixels_per_y=PIXELS_PER_Y,
        plate_view_transform="AgX",
        id=20, title="St. Maria - Laura's forge", plate="lauras_smith_bg.png",
        intro="The forge is banked low. Everything in the room is either iron or waiting to be.",
        screen_y=136, music="town1",
        npcs=[("smith", "Weapon Shop", "npc_laura", 200.0)],
        doors=[("exit_door", "Out to the Port", 31, "forge_door", 245.0, None, "away")],
    ),
    "pub": dict(
        pixels_per_y=PIXELS_PER_Y,
        plate_view_transform="Standard",
        id=21, title="St. Maria - The Pub", plate="pub_bg.png",
        intro="Warm, low and smoke-dark. The only room in St. Maria that argues with the weather.",
        screen_y=136, music="town1",
        npcs=[("owner", "Pub Owner", "npc_pub_owner", 130.0)],
        doors=[("exit_door", "Out to the Quay", 19, "pub_door", 459.0, None, "away")],
    ),
    "chapel": dict(
        pixels_per_y=PIXELS_PER_Y,
        plate_view_transform="Standard",
        id=22, title="St. Maria - Chapel", plate="chapel_bg.png",
        intro="Blue tiles, cold wax, and a door that is never locked.",
        screen_y=136, music="town1",
        npcs=[("agnes", "EV012", "npc_agnes", 475.0)],
        doors=[("exit_door", "Out to the Praca", 17, "chapel_door", 559.0, None, "away")],
    ),
    "house_laura": dict(
        pixels_per_y=PIXELS_PER_Y,
        plate_view_transform="Standard",
        id=23, title="St. Maria - The padaria, the hearth", plate="house_laura_bg.png",
        intro="A hearth, a scrubbed table, and more tools than a kitchen needs. The oven's back wall is warm through the plaster.",
        screen_y=136, music="town1",
        npcs=[("laura", "Laura", "npc_laura", 460.0)],
        doors=[
            ("exit_door", "Out to the Cortico", 26, "padaria_back", 59.0, None, "away"),
            ("bedroom_door", "The room upstairs", 24, "exit_door", 539.0, None, "away"),
            ("shop_stair", "Down to the shop", 27, "home_stair", 629.0, None, "away"),
        ],
    ),
    "house_alicia": dict(
        pixels_per_y=PIXELS_PER_Y,
        plate_view_transform="Standard",
        id=24, title="St. Maria - The padaria, the room upstairs", plate="house_alicia_bg.png",
        intro="A narrow bed, a desk of papers, and the balcony door left open to the grey.",
        screen_y=136, music="town1",
        npcs=[("alicia", "Alicia", "npc_alicia", 110.0)],
        doors=[("exit_door", "Down to the hearth", 23, "bedroom_door", 180.0, None, "away")],
    ),
    "lodging": dict(
        pixels_per_y=PIXELS_PER_Y,
        plate_view_transform="Standard",
        id=25, title="St. Maria - Passage House", plate="lodging_bg.png",
        intro="Two beds, a washstand, and a window that does not close properly. It is paid for until spring.",
        screen_y=136, music="town1",
        npcs=[("registrar", "Registrar", "npc_celina", 260.0)],
        doors=[("exit_door", "Out to the Cortico", 26, "lodging_door", 404.0, None, "away")],
    ),
    "alicias_padaria": dict(
        pixels_per_y=PIXELS_PER_Y,
        plate_view_transform="AgX",
        id=27, title="St. Maria - Alicia's Padaria", plate="alicias_padaria_bg.png",
        intro="Warm flour and woodsmoke. The oven is the loudest thing in the room, and the counter is between you and it.",
        screen_y=136, music="town1",
        npcs=[("alicia", "Alicia", "npc_alicia", 215.0)],
        doors=[
            ("exit_door", "Out to Market Row", 18, "padaria_door", 50.0, None, "away"),
            ("home_stair", "Up to the hearth", 23, "shop_stair", 395.0, None, "away"),
        ],
    ),
}

# Stable lane data is carried by the live maps/manifests, not by the current
# plate pixels. These bounds let a screen migrate from the legacy 40/34.6
# contract without moving its doors, NPCs, or walking distance in runtime.
SCREEN_CONTRACTS = {
    "churchyard": (0.0, 29.021, 924),
    "praca": (0.0, 23.699, 906),
    "cortico": (-2.844, 26.906, 866),
    "market": (0.0, 20.708, 696),
    "quay": (0.0, 25.448, 826),
    "port": (0.0, 29.604, 1065),
    "weaponsmith": (0.35, 7.4167, 450),
    "alicias_padaria": (0.35, 7.4167, 450),
    "pub": (0.0, 12.500, 576),
    "chapel": (0.0, 16.000, 674),
    "house_laura": (-2.516, 18.300, 747),
    "house_alicia": (-0.700, 7.000, 424),
    "lodging": (0.0, 10.400, 457),
}

# The original character sheets were authored in the shared character folder;
# newer town-only sheets live under character/town. Keep the path decision in
# the generator so every regenerated map resolves the same source asset.
ROOT_CHARACTER_SPRITES = {"npc_goustav", "npc_laura", "npc_alicia", "npc_celina"}
for _key, (_min_y, _max_y, _width) in SCREEN_CONTRACTS.items():
    SCREENS[_key].update({
        "plate_margin_px": LANE_MARGIN_PX,
        "legacy_plate_margin_px": LEGACY_LANE_MARGIN_PX,
        "legacy_pixels_per_y": LEGACY_PIXELS_PER_Y,
        "plate_width": _width,
        "lane_min_y": _min_y,
        "lane_max_y": _max_y,
    })

# Maps this generator OWNS and will overwrite. The Praça is authored in its
# modelled environment and must survive a rebuild. Maps 28/29 are modelled
# reference screens and are outside this flat-plate table entirely.
#
# tools/towngen/check_town.py gates this boundary: a hand-edit to an owned map
# now fails CI instead of surviving until the next rebuild deletes it.
AUTHORED_NOT_GENERATED = {"weaponsmith", "praca", "alicias_padaria"}
AUTHORED_REFERENCE_MAPS = {17, 20, 27, 28, 29}

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
    scale = screen_scale(screen)
    lane = screen_lane(screen)
    profile = ground_profile(screen, screen.get("ground"))
    spawn_z = profile_ground_at(profile, lane["centre"])
    anchors = {"spawn_player": {"position": [DEPTH_X, lane["centre"], spawn_z]}}
    for item in screen["doors"]:
        anchor, _label, _target, _arrival, pixel_x, _source = item[:6]
        pos_y = lane_y_for(pixel_x, scale)
        anchors[anchor] = {
            "position": [DEPTH_X, pos_y, profile_ground_at(profile, pos_y)]}
    for anchor, _source, _sprite, pixel_x in screen["npcs"]:
        pos_y = lane_y_for(pixel_x, scale)
        anchors["npc_" + anchor] = {
            "position": [DEPTH_X, pos_y, profile_ground_at(profile, pos_y)]}
    manifest = {
        "contractVersion": 1,
        "renderMesh": "../stub/quad.obj",
        "materialLibrary": "../stub/quad.mtl",
        "textureAtlas": "../stub/atlas.png",
        "collisionMesh": "../stub/quad.obj",
        "bounds": [DEPTH_X - 1.0, lane["minY"], GROUND_Z - 1.0,
                   DEPTH_X + 1.0, lane["maxY"], GROUND_Z + 4.0],
        "provenance": {
            "plateSourceViewTransform": screen["plate_view_transform"],
        },
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
                "pixelsPerRuntimeY": scale,
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
    profile = ground_profile(screen, screen.get("ground"))
    if profile:
        block["groundProfile"] = profile
    return block


def build_map(key, screen, map1):
    scale = screen_scale(screen)
    lane = screen_lane(screen)
    plate = screen["plate"]
    profile = ground_profile(screen, screen.get("ground"))
    events = []
    next_id = screen["id"] * 100 + 1

    for anchor, source, sprite, pixel_x in screen["npcs"]:
        commands = map1.get(source) if source else INVENTED.get(anchor)
        if commands is None:
            raise SystemExit("no dialogue for %s/%s" % (key, anchor))
        ev_y = lane_y_for(pixel_x, scale)
        event = {
            "id": next_id,
            "instanceId": "st-maria-%s-%s" % (key, anchor),
            "name": anchor.replace("_", " ").title(),
            "x": 0, "y": 0,
            "worldPosition": [DEPTH_X, ev_y, profile_ground_at(profile, ev_y)],
            "trigger": "interact",
            "commands": commands,
        }
        if sprite:
            sprite_root = "assets/character" if sprite in ROOT_CHARACTER_SPRITES else "assets/character/town"
            event.update({
                "sprite": "%s/%s.png" % (sprite_root, sprite),
                "frameWidth": 24, "frameHeight": 48, "frameIndex": 0,
                "worldHeight": 1.75,
            })
        events.append(event)
        next_id += 1

    for item in screen["doors"]:
        anchor, label, target, arrival, pixel_x, source = item[:6]
        direction = item[6] if len(item) > 6 else None
        if source and map1.get(source):
            commands = map1[source]
        else:
            command = {"cmd": "LOAD_MAP", "mapId": target}
            if arrival:
                command["arrival"] = arrival
            commands = [command]
        door_y = lane_y_for(pixel_x, scale)
        event = {
            "id": next_id,
            "instanceId": "st-maria-%s-%s" % (key, anchor),
            "name": label,
            "x": 0, "y": 0,
            "worldPosition": [DEPTH_X, door_y, profile_ground_at(profile, door_y)],
            "trigger": "bump",
            "model": TRANSITION_ARROW_MODEL,
            "commands": commands,
        }
        if direction:
            event["direction"] = direction
        events.append(event)
        next_id += 1

    doorways = [{"anchor": item[0], "eventInstanceId": "st-maria-%s-%s" % (key, item[0]),
                 "radius": item[7] if len(item) > 7 and item[7] is not None else 0.9}
                for item in screen["doors"]]

    map_data = {
        "id": screen["id"],
        "title": screen["title"],
        "intro": screen["intro"],
        "depth": 0,
        "safe": True,
        "category": "town",
    }
    if screen.get("parentMapId") is not None:
        map_data["parentMapId"] = screen["parentMapId"]
    map_data.update({
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
                # 18.6667 is solved from the actor - a 1.75 m Walker at 48
                # native px - and is the number every authored blend uses.
                # 21.1175 was a 2D-plate number the interior notes warn against
                # inheriting for modelled work.
                "distance": 18.666666666666668,
                "yawDegrees": 0.0,
                # All St. Maria side-view maps share the owner's downward
                # pitched camera. Plates and world-space overlays must use the
                # same contract or 3D event models will float against them.
                "pitchDegrees": -17.5,
                # Relative to target.z, so this is the contract's eye height.
                # Without it the eye resolves onto the target plane, at the
                # actor's feet.
                "eyeHeight": 2.2604166666666665,
                "fovDegrees": FOV_DEGREES,
                "nearPlane": 0.05,
                "farPlane": 128.0,
                "projectionScale": {"x": 1.0, "y": 1.0},
                # 110 predates the character floor limit; 66 is the current
                # baseline in town-authoring-known-good.md.
                "projectionFrame": {"canonicalCenterX": 213, "canonicalHorizonY": 66},
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
    write_json(os.path.join(MAPS, "%d.json" % screen["id"]), map_data)


def main():
    map1 = load_map1_commands()
    build_stub()
    for key, screen in SCREENS.items():
        if key in AUTHORED_NOT_GENERATED:
            print("skipped %-12s map %d (authored, not generated)"
                  % (key, screen["id"]))
            continue
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
