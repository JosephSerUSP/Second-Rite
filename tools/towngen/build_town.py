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
CENTER_X = 213.0
PIXELS_PER_Y = 34.6
DEPTH_X = 7.8
GROUND_Z = -1.5
FOV_DEGREES = 28.072486935852957


def lane_y(pixel_x):
    """Native pixel x -> lane y. The inverse of what the compositor draws."""
    return round((pixel_x - CENTER_X) / PIXELS_PER_Y + 5.0, 3)


# key: (map id, title, plate, intro, lane min/max, feet screenY, npcs, doors)
#   npcs:  (anchor_name, source_event_name_in_map_1, sprite, pixel_x)
#   doors: (anchor_name, label, target_map, arrival_anchor_on_target, pixel_x,
#           source_event_name_or_None)
SCREENS = {
    "gate": dict(
        id=16, title="St. Maria - Gate of Thestra", plate="gate_bg.png",
        intro="The church holds the sealed mouth of the Labyrinth. Two lamps are kept burning against the fog.",
        lane=(0.0, 10.0), screen_y=224, music="town1",
        npcs=[("guard", "Gate Guard", "npc_gate_guard", 262)],
        doors=[
            ("labyrinth_door", "Labyrinth Gate", 2, None, 193, "Labyrinth Gate"),
            ("east_praca", "The Praca", 17, "west_gate", 404, None),
        ],
    ),
    "praca": dict(
        id=17, title="St. Maria - The Praca", plate="praca_bg.png",
        intro="The fountain never stops. Laundry hangs out over the square whether or not it will dry.",
        lane=(0.0, 10.0), screen_y=212, music="town1",
        npcs=[("registrar", "Registrar", "npc_registrar", 340),
              ("child", None, "npc_child", 158)],
        doors=[
            ("west_gate", "Gate of Thestra", 16, "east_praca", 22, None),
            ("laura_door", "Laura's door", 23, "exit_door", 118, None),
            ("alicia_door", "Alicia's door", 24, "exit_door", 310, None),
            ("east_market", "Market Row", 18, "west_praca", 404, None),
        ],
    ),
    "market": dict(
        id=18, title="St. Maria - Market Row", plate="market_bg.png",
        intro="Awnings sag with the morning's rain. Most of the stalls are already empty.",
        lane=(0.0, 10.0), screen_y=224, music="town1",
        npcs=[("auctioneer", "Auctioneer", "npc_auctioneer", 100),
              ("yukio", "Yukio", "npc_yukio", 150),
              ("euler", "Euler", "npc_euler", 300),
              ("scholar", "Scholar", "npc_scholar", 352)],
        doors=[
            ("west_praca", "The Praca", 17, "east_market", 22, None),
            ("smith_door", "Weaponsmith", 20, "exit_door", 205, None),
            ("east_quay", "The Quay", 19, "west_market", 404, None),
        ],
    ),
    "quay": dict(
        id=19, title="St. Maria - The Quay", plate="quay_bg.png",
        intro="The town ends at the water. The fog does not.",
        lane=(0.0, 10.0), screen_y=224, music="town1",
        npcs=[("fisherman", None, "npc_fisherman", 92),
              ("sign", "Sign", None, 300)],
        doors=[
            ("west_market", "Market Row", 18, "east_quay", 22, None),
            ("pub_door", "The Pub", 21, "exit_door", 128, None),
            ("chapel_door", "Chapel", 22, "exit_door", 212, None),
        ],
    ),
    # --- interiors ---
    "weaponsmith": dict(
        id=20, title="St. Maria - Weaponsmith", plate="weaponsmith_bg.png",
        intro="The forge is banked low. Everything in the room is either iron or waiting to be.",
        lane=(1.5, 8.5), screen_y=222, music="town1",
        npcs=[("smith", "Weapon Shop", "npc_weaponsmith", 250)],
        doors=[("exit_door", "Out to Market Row", 18, "smith_door", 100, None)],
    ),
    "pub": dict(
        id=21, title="St. Maria - The Pub", plate="pub_bg.png",
        intro="Warm, low and smoke-dark. The only room in St. Maria that argues with the weather.",
        lane=(1.5, 8.5), screen_y=222, music="town1",
        npcs=[("owner", "Pub Owner", "npc_pub_owner", 230)],
        doors=[("exit_door", "Out to the Quay", 19, "pub_door", 100, None)],
    ),
    "chapel": dict(
        id=22, title="St. Maria - Chapel", plate="chapel_bg.png",
        intro="Blue tiles, cold wax, and a door that is never locked.",
        lane=(1.5, 8.5), screen_y=224, music="town1",
        npcs=[("agnes", "EV012", "npc_agnes", 150)],
        doors=[("exit_door", "Out to the Quay", 19, "chapel_door", 100, None)],
    ),
    "house_laura": dict(
        id=23, title="St. Maria - Laura's House", plate="house_laura_bg.png",
        intro="A hearth, a scrubbed table, and more tools than a kitchen needs.",
        lane=(1.5, 8.5), screen_y=222, music="town1",
        npcs=[("laura", "Laura", "npc_laura", 250)],
        doors=[("exit_door", "Out to the Praca", 17, "laura_door", 110, None)],
    ),
    "house_alicia": dict(
        id=24, title="St. Maria - Alicia's Room", plate="house_alicia_bg.png",
        intro="A narrow bed, a desk of papers, and the balcony door left open to the grey.",
        lane=(1.5, 8.5), screen_y=220, music="town1",
        npcs=[("alicia", "Alicia", "npc_alicia", 180)],
        doors=[("exit_door", "Out to the Praca", 17, "alicia_door", 100, None)],
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
    min_y, max_y = screen["lane"]
    centre = round((min_y + max_y) / 2.0, 3)
    anchors = {"spawn_player": {"position": [DEPTH_X, centre, GROUND_Z]}}
    for anchor, _label, _target, _arrival, pixel_x, _source in screen["doors"]:
        anchors[anchor] = {"position": [DEPTH_X, lane_y(pixel_x), GROUND_Z]}
    for anchor, _source, _sprite, pixel_x in screen["npcs"]:
        anchors["npc_" + anchor] = {"position": [DEPTH_X, lane_y(pixel_x), GROUND_Z]}
    manifest = {
        "contractVersion": 1,
        "renderMesh": "../stub/quad.obj",
        "materialLibrary": "../stub/quad.mtl",
        "textureAtlas": "../stub/atlas.png",
        "collisionMesh": "../stub/quad.obj",
        "bounds": [DEPTH_X - 1.0, min_y, GROUND_Z - 1.0, DEPTH_X + 1.0, max_y, GROUND_Z + 4.0],
        "anchors": anchors,
        "preRendered": {
            "mode": "layered_2d",
            "cameraMode": "static",
            "imageSize": [NATIVE_W, NATIVE_H],
            "slicePositions": [centre],
            "backgrounds": ["../../../../" + PLATE_REL + "/" + screen["plate"]],
            "scenes": ["../../../../" + PLATE_REL + "/" + screen["plate"]],
            "foregrounds": ["../stub/empty.png"],
            "lane": {"runtimeCenterY": centre},
            "playerProjection": {
                "centerX": CENTER_X,
                "screenY": screen["screen_y"],
                "width": 24,
                "height": 48,
                "pixelsPerRuntimeY": PIXELS_PER_Y,
            },
        },
    }
    write_json(os.path.join(ENV_ROOT, key, "environment.json"), manifest)


def build_map(key, screen, map1):
    min_y, max_y = screen["lane"]
    centre = round((min_y + max_y) / 2.0, 3)
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
            "worldPosition": [DEPTH_X, lane_y(pixel_x), GROUND_Z],
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
            "worldPosition": [DEPTH_X, lane_y(pixel_x), GROUND_Z],
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
            "lane": {"minY": min_y, "maxY": max_y, "depthX": DEPTH_X,
                     "groundZ": GROUND_Z, "speed": 0.75},
            "blockedRanges": [],
            "camera": {
                "profile": "town_sideview",
                "target": {"x": DEPTH_X, "y": centre, "z": 0.0},
                "distance": 21.1175,
                "yawDegrees": 0.0,
                "pitchDegrees": 0.0,
                "fovDegrees": FOV_DEGREES,
                "nearPlane": 0.05,
                "farPlane": 128.0,
                "projectionScale": {"x": 1.0, "y": 1.0},
                "projectionFrame": {"canonicalCenterX": 213, "canonicalHorizonY": 110},
                "tracking": {
                    "axis": "y", "center": centre,
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

    system_path = os.path.join(DATA, "system.json")
    with io.open(system_path, encoding="utf-8") as handle:
        system = json.load(handle)
    system["spawn"] = {"mapId": SCREENS["gate"]["id"], "x": 0, "y": 0, "dir": "E"}
    write_json(system_path, system)
    print("new game now starts on map %d" % SCREENS["gate"]["id"])
    print("TOWN BUILD OK")


if __name__ == "__main__":
    main()
