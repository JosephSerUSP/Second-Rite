#!/usr/bin/env python3
"""Build and write all authored maps for Second Gate: Pale Crossing.
"""
import json
import os

MAP_DIR = "projects/labs/pale-crossing/data/maps"

def write_map(map_id, data):
    layout = data.get("layout", [])
    h = len(layout)
    w = len(layout[0]) if h > 0 else 0
    data["width"] = w
    data["height"] = h
    path = os.path.join(MAP_DIR, f"{map_id}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    title = data.get('title', '').encode('ascii', errors='replace').decode('ascii')
    print(f"Authored Map {map_id}: {title} ({w}x{h}, {len(data.get('events', []))} events)")

# =========================================================================
# MAP 2: Floor 1 — Entry Vault
# =========================================================================
map2_layout = [
    "###############",
    "#...#.....#...#",
    "#.#.#.###.#.#.#",
    "#.#...#.#...#.#",
    "#.#####.#####.#",
    "#.............#",
    "###.#######.###",
    "#...#.....#...#",
    "#.#.#.###.#.#.#",
    "#.#...#.#...#.#",
    "#.#####.#####.#",
    "#.............#",
    "###....#....###",
    "######...######",
    "###############"
]

map2_data = {
    "id": 2,
    "title": "Floor 1: Entry Vault",
    "intro": "Cold air climbs the stone steps. The Bellroot Labyrinth begins here.",
    "depth": 1,
    "tileset": "dungeon_default",
    "music": "dungeon1",
    "image": "DungeonFloors1.png",
    "layout": map2_layout,
    "spawn": {"x": 7, "y": 13, "dir": "N"},
    "encounters": [
        {"actor": "pixie", "weight": 5, "levelMin": 1, "levelMax": 2},
        {"actor": "skeleton", "weight": 5, "levelMin": 1, "levelMax": 3},
        {"actor": "imp", "weight": 4, "levelMin": 1, "levelMax": 2},
        {"actor": "cocoon", "weight": 3, "levelMin": 1, "levelMax": 2},
        {"actor": "bat", "weight": 6, "levelMin": 1, "levelMax": 2},
        {"actor": "ooze", "weight": 4, "levelMin": 1, "levelMax": 2}
    ],
    "encounterTroop": "floor_1_wandering",
    "events": [
        {
            "id": 1,
            "name": "Stairs Up to St. Maria",
            "label": "Stairs Up",
            "x": 7,
            "y": 13,
            "trigger": "bump",
            "priority": "same",
            "sprite": "assets/sprites/dungeon_stairs_up.png",
            "commands": [
                {"text": "Ascend the stairs back to St. Maria?", "cmd": "TEXT"},
                {
                    "cmd": "CHOICE",
                    "options": [
                        {
                            "label": "Return to Town",
                            "commands": [
                                {"cmd": "SET_FLAG", "flag": "milestone_return_1", "value": True},
                                {"cmd": "TEXT", "text": "You climb into the grey autumn daylight of St. Maria."},
                                {"cmd": "LOAD_MAP", "mapId": 1}
                            ]
                        },
                        {"label": "Stay in Dungeon", "commands": []}
                    ]
                }
            ]
        },
        {
            "id": 2,
            "name": "Ines Mark",
            "label": "Ines Chalk Sigil",
            "x": 7,
            "y": 5,
            "trigger": "interact",
            "priority": "same",
            "sprite": "assets/sprites/dungeon_blue_chalk_sigil.png",
            "commands": [
                {"cmd": "TEXT", "text": "A backward name is drawn in damp blue chalk against the stone: 'SENI'"},
                {"cmd": "TEXT", "text": "Beneath it, in hurried strokes: 'Every summon drinks your MP with every pace. If your count falls below 400, turn back before the dark decides for you.'"},
                {"cmd": "SET_FLAG", "flag": "found_ines_mark", "value": True}
            ]
        },
        {
            "id": 3,
            "name": "First Contract: Cerberus",
            "label": "Shadowed Chamber",
            "x": 2,
            "y": 1,
            "trigger": "interact",
            "priority": "same",
            "sprite": "assets/sprites/dungeon_summoner_contract.png",
            "commands": [
                {"cmd": "SET_FLAG", "flag": "found_cerberus", "value": True},
                {
                    "condition": "flag:cerberus_recruited",
                    "commands": [
                        {"cmd": "TEXT", "text": "The antechamber is quiet. A scatter of ash and embers marks where Cerberus stood."}
                    ],
                    "elseCommands": [
                        {"cmd": "TEXT", "text": "A three-headed hound of black iron and glowing coals crouches in the recess."},
                        {"cmd": "TEXT", "text": "Saban bristles beside you, letting out a sharp, cautious warning chirp."},
                        {"cmd": "TEXT", "text": "Cerberus carries immense combat strength (ATK 28, Fire Claw), but an intense traversal drain (MPD 6). Contracting him will dramatically reduce your safe expedition margin."},
                        {
                            "cmd": "CHOICE",
                            "options": [
                                {
                                    "label": "Offer Contract (Challenge Cerberus)",
                                    "commands": [
                                        {"cmd": "BATTLE", "troop": "challenge_cerberus"},
                                        {"cmd": "SET_FLAG", "flag": "cerberus_recruited", "value": True},
                                        {"cmd": "TEXT", "text": "Cerberus lowers his central head in pact. Cerberus joins your party!"}
                                    ]
                                },
                                {
                                    "label": "Leave him space (Preserve Saban efficiency)",
                                    "commands": [
                                        {"cmd": "TEXT", "text": "You back away quietly. Saban relaxes his feathers."}
                                    ]
                                }
                            ]
                        }
                    ],
                    "cmd": "CONDITIONAL_BRANCH"
                }
            ]
        },
        {
            "id": 4,
            "name": "Vault Treasure Chest",
            "label": "Treasure Chest",
            "x": 12,
            "y": 1,
            "trigger": "interact",
            "priority": "same",
            "sprite": "assets/sprites/OBJ_TreasureChest_001.png",
            "commands": [
                {
                    "condition": "flag:chest_floor1_opened",
                    "commands": [
                        {"cmd": "TEXT", "text": "The ironbound chest stands open and empty."}
                    ],
                    "elseCommands": [
                        {"cmd": "SET_FLAG", "flag": "chest_floor1_opened", "value": True},
                        {"cmd": "CHANGE_ITEM", "item": "1", "count": 2},
                        {"cmd": "CHANGE_ITEM", "item": "2", "count": 1},
                        {"cmd": "TEXT", "text": "Opened chest! Found HP Tonic x2 and Sigil Ink x1!"}
                    ],
                    "cmd": "CONDITIONAL_BRANCH"
                }
            ]
        },
        {
            "id": 5,
            "name": "Stairs Down to Floor 2",
            "label": "Stairs Down",
            "x": 7,
            "y": 1,
            "trigger": "bump",
            "priority": "same",
            "sprite": "assets/sprites/dungeon_stairs_down.png",
            "commands": [
                {"cmd": "TEXT", "text": "Descend to Floor 2: Bellroot Chasm?"},
                {
                    "cmd": "CHOICE",
                    "options": [
                        {
                            "label": "Descend",
                            "commands": [
                                {"cmd": "TEXT", "text": "You descend into the echoing chasm below..."},
                                {"cmd": "LOAD_MAP", "mapId": 3}
                            ]
                        },
                        {"label": "Stay here", "commands": []}
                    ]
                }
            ]
        }
    ]
}
write_map(2, map2_data)

# =========================================================================
# MAP 3: Floor 2 — Bellroot Chasm
# =========================================================================
map3_layout = [
    "#################",
    "#.....#...#.....#",
    "#.###.#.#.#.###.#",
    "#.#...#.#.#...#.#",
    "#.#.###.#.###.#.#",
    "#.#.....#.....#.#",
    "#.#############.#",
    "#...............#",
    "#####.#####.#####",
    "#.....#...#.....#",
    "#.###.#.#.#.###.#",
    "#...#...#...#...#",
    "###.#####.#####.#",
    "#...............#",
    "#.#############.#",
    "#...............#",
    "#################"
]

map3_data = {
    "id": 3,
    "title": "Floor 2: Bellroot Chasm",
    "intro": "The air grows damp. Distant subterranean currents vibrate through the floor.",
    "depth": 2,
    "tileset": "dungeon_default",
    "music": "dungeon1",
    "image": "DungeonFloors1.png",
    "layout": map3_layout,
    "spawn": {"x": 8, "y": 13, "dir": "N"},
    "encounters": [
        {"actor": "cockatrice", "weight": 5, "levelMin": 2, "levelMax": 4},
        {"actor": "ghoul", "weight": 5, "levelMin": 2, "levelMax": 4},
        {"actor": "mandrake", "weight": 4, "levelMin": 2, "levelMax": 4},
        {"actor": "undine", "weight": 4, "levelMin": 2, "levelMax": 3},
        {"actor": "skeleton", "weight": 4, "levelMin": 2, "levelMax": 4}
    ],
    "encounterTroop": "wandering_x2",
    "events": [
        {
            "id": 1,
            "name": "Stairs Up to Floor 1",
            "label": "Stairs Up",
            "x": 8,
            "y": 13,
            "trigger": "bump",
            "priority": "same",
            "sprite": "assets/sprites/dungeon_stairs_up.png",
            "commands": [
                {"cmd": "TEXT", "text": "Ascend to Floor 1: Entry Vault?"},
                {
                    "cmd": "CHOICE",
                    "options": [
                        {
                            "label": "Ascend",
                            "commands": [
                                {"cmd": "LOAD_MAP", "mapId": 2}
                            ]
                        },
                        {"label": "Stay on Floor 2", "commands": []}
                    ]
                }
            ]
        },
        {
            "id": 2,
            "name": "The Salt Table",
            "label": "The Salt Table",
            "x": 3,
            "y": 3,
            "trigger": "interact",
            "priority": "same",
            "sprite": "assets/sprites/dungeon_crystal_pedestal.png",
            "commands": [
                {"cmd": "SET_FLAG", "flag": "found_salt_table", "value": True},
                {
                    "condition": "flag:salt_table_taken",
                    "commands": [
                        {"cmd": "TEXT", "text": "The stone table stands silent. A circle of dried salt still clings to the plate."}
                    ],
                    "elseCommands": [
                        {"cmd": "SET_FLAG", "flag": "salt_table_taken", "value": True},
                        {"cmd": "CHANGE_ITEM", "item": "206", "count": 2},
                        {"cmd": "TEXT", "text": "A stone table is set with an earthenware plate bearing wet mineral salt and unbaked dough."},
                        {"cmd": "TEXT", "text": "Obtained Bell Salt x2! This rare salt restores 2 skill charges to every active summon."}
                    ],
                    "cmd": "CONDITIONAL_BRANCH"
                }
            ]
        },
        {
            "id": 3,
            "name": "Daphne Alcove",
            "label": "Daphne the Wood Nymph",
            "x": 13,
            "y": 3,
            "trigger": "interact",
            "priority": "same",
            "sprite": "assets/sprites/NPC03.png",
            "commands": [
                {
                    "condition": "flag:daphne_recruited",
                    "commands": [
                        {"cmd": "TEXT", "text": "The recess is filled with soft green moss and clean water."}
                    ],
                    "elseCommands": [
                        {"cmd": "TEXT", "text": "A gentle water spirit manifests from the dripping stalactites."},
                        {"cmd": "TEXT", "speaker": "DAPHNE", "text": "The stone deeper down is changing... it smells like burned metal and lightning. Will you take me with you?"},
                        {
                            "cmd": "CHOICE",
                            "options": [
                                {
                                    "label": "Contract Daphne (Water Healer, Level 3)",
                                    "commands": [
                                        {"cmd": "BATTLE", "troop": "challenge_daphne"},
                                        {"cmd": "SET_FLAG", "flag": "daphne_recruited", "value": True},
                                        {"cmd": "TEXT", "text": "Daphne weaves her water contract with your talisman. Daphne joins your party!"}
                                    ]
                                },
                                {
                                    "label": "Leave her in the spring",
                                    "commands": [
                                        {"cmd": "TEXT", "text": "Daphne dips back into the subterranean pool."}
                                    ]
                                }
                            ]
                        }
                    ],
                    "cmd": "CONDITIONAL_BRANCH"
                }
            ]
        },
        {
            "id": 4,
            "name": "Bellroot Recovery Font",
            "label": "Recovery Font",
            "x": 8,
            "y": 7,
            "trigger": "interact",
            "priority": "same",
            "sprite": "assets/sprites/dungeon_crystal_pedestal.png",
            "commands": [
                {"cmd": "TEXT", "text": "A pillar of cool, pale light wells up from the bellroot seam."},
                {"cmd": "RECOVER_PARTY"},
                {"cmd": "TEXT", "text": "The party's wounds are mended and vitality is restored!"}
            ]
        },
        {
            "id": 5,
            "name": "The Metro Rupture Hatch",
            "label": "Heavy Steel Bulkhead",
            "x": 8,
            "y": 1,
            "trigger": "bump",
            "priority": "same",
            "sprite": "assets/sprites/map_door_001.png",
            "commands": [
                {"cmd": "TEXT", "text": "Ahead stands an impossible industrial steel bulkhead with peeled yellow safety paint."},
                {"cmd": "TEXT", "text": "A blast of freezing air smells of ozone, brake dust, and damp tiled corridors."},
                {"cmd": "TEXT", "text": "Open the heavy steel hatch and step through?"},
                {
                    "cmd": "CHOICE",
                    "options": [
                        {
                            "label": "Breach the Rupture (Enter Estacao Se)",
                            "commands": [
                                {"cmd": "TEXT", "text": "The pneumatic latch hisses open. Fluorescent lights buzz in the corridor ahead..."},
                                {"cmd": "LOAD_MAP", "mapId": 4}
                            ]
                        },
                        {"label": "Step back", "commands": []}
                    ]
                }
            ]
        }
    ]
}
write_map(3, map3_data)

# =========================================================================
# MAP 4: Floor 3 — Estação Sé (Concourse)
# =========================================================================
map4_layout = [
    "#################",
    "#...............#",
    "#.#####...#####.#",
    "#.#...#...#...#.#",
    "#.#.#.#####.#.#.#",
    "#...#.......#...#",
    "###.#########.###",
    "#...............#",
    "#.#############.#",
    "#.#.....#.....#.#",
    "#.#.###.#.###.#.#",
    "#...#.......#...#",
    "#####.#####.#####",
    "#...............#",
    "#################"
]

map4_data = {
    "id": 4,
    "title": "Floor 3: Estacao Se — Concourse",
    "intro": "White ceramic tiles. Fluorescent flicker. The impossible scent of commuter rail.",
    "depth": 3,
    "tileset": "dungeon_ffxii_depth_explore",
    "music": "event4_darkJester",
    "image": "DungeonFloors1.png",
    "layout": map4_layout,
    "spawn": {"x": 8, "y": 13, "dir": "N"},
    "encounters": [
        {"actor": "wisp", "weight": 6, "levelMin": 4, "levelMax": 6},
        {"actor": "shadow_stalker", "weight": 5, "levelMin": 4, "levelMax": 6},
        {"actor": "gargoyle", "weight": 4, "levelMin": 4, "levelMax": 6},
        {"actor": "larva", "weight": 4, "levelMin": 3, "levelMax": 5}
    ],
    "encounterTroop": "metro_wandering",
    "events": [
        {
            "id": 1,
            "name": "Stairs Up to Bellroot Chasm",
            "label": "Rupture Hatch (Return)",
            "x": 8,
            "y": 13,
            "trigger": "bump",
            "priority": "same",
            "sprite": "assets/sprites/dungeon_stairs_up.png",
            "commands": [
                {"cmd": "TEXT", "text": "Return to Floor 2: Bellroot Chasm?"},
                {
                    "cmd": "CHOICE",
                    "options": [
                        {
                            "label": "Return to Bellroot",
                            "commands": [
                                {"cmd": "LOAD_MAP", "mapId": 3}
                            ]
                        },
                        {"label": "Stay in Concourse", "commands": []}
                    ]
                }
            ]
        },
        {
            "id": 2,
            "name": "Ticket Booth (Guiche)",
            "label": "Ticket Booth",
            "x": 3,
            "y": 3,
            "trigger": "interact",
            "priority": "same",
            "sprite": "assets/sprites/NPC00.png",
            "commands": [
                {
                    "condition": "hasItem:208",
                    "commands": [
                        {"cmd": "TEXT", "text": "The ticket booth window is cracked. The green terminal display is frozen on: 'SE — BLOQUEIOS LIBERADOS'"}
                    ],
                    "elseCommands": [
                        {"cmd": "CHANGE_ITEM", "item": "208", "count": 1},
                        {"cmd": "TEXT", "text": "Inside the steel transaction tray lies a rigid plastic magnetic card with a blue logo."},
                        {"cmd": "TEXT", "text": "Obtained Metro Transit Pass (Bilhete de Acesso)! The card pulses faintly with electrical resonance."}
                    ],
                    "cmd": "CONDITIONAL_BRANCH"
                }
            ]
        },
        {
            "id": 3,
            "name": "Public Address Speaker",
            "label": "PA Speaker",
            "x": 13,
            "y": 3,
            "trigger": "interact",
            "priority": "same",
            "sprite": "assets/sprites/NPC02.png",
            "commands": [
                {"cmd": "TEXT", "text": "A metallic tone dings twice through the ceiling speaker."},
                {"cmd": "TEXT", "speaker": "ESTACAO SE", "text": "'Atenção passageiros. Permaneçam atrás da faixa amarela. Próxima estação: Liberdade.'"},
                {"cmd": "TEXT", "text": "The voice fades into the rhythmic hum of ventilation shafts."}
            ]
        },
        {
            "id": 4,
            "name": "Turnstile Barrier (Catracas)",
            "label": "Turnstile Gate",
            "x": 8,
            "y": 7,
            "trigger": "bump",
            "priority": "same",
            "sprite": "assets/sprites/map_door_001.png",
            "commands": [
                {
                    "condition": "hasItem:208",
                    "commands": [
                        {"cmd": "TEXT", "text": "You scan the Metro Transit Pass against the optical sensor. The turnstile clicks unlocked!"}
                    ],
                    "elseCommands": [
                        {"cmd": "TEXT", "text": "A row of heavy stainless steel turnstiles blocks the passage. A blue optical reader displays: 'APROXIME O CARTAO'"},
                        {"cmd": "TEXT", "text": "Search the ticket booth to find an access pass."}
                    ],
                    "cmd": "CONDITIONAL_BRANCH"
                }
            ]
        },
        {
            "id": 5,
            "name": "Platform Stairs Down",
            "label": "Platform 2 Stairs",
            "x": 8,
            "y": 1,
            "trigger": "bump",
            "priority": "same",
            "sprite": "assets/sprites/dungeon_stairs_down.png",
            "commands": [
                {"cmd": "TEXT", "text": "Descend the stairs to Platform 2 & The Rail Tunnels?"},
                {
                    "cmd": "CHOICE",
                    "options": [
                        {
                            "label": "Descend to Platform",
                            "commands": [
                                {"cmd": "LOAD_MAP", "mapId": 5}
                            ]
                        },
                        {"label": "Stay on Concourse", "commands": []}
                    ]
                }
            ]
        }
    ]
}
write_map(4, map4_data)

# =========================================================================
# MAP 5: Floor 4 — Estação Sé (Platform & Ghost Tracks)
# =========================================================================
map5_layout = [
    "###################",
    "#.................#",
    "#.###############.#",
    "#.#.............#.#",
    "#.#.###########.#.#",
    "#.#.#.........#.#.#",
    "#.#.#.#######.#.#.#",
    "#...#.#.....#.#...#",
    "###.#.#.###.#.#.###",
    "#...#.#.#.#.#.#...#",
    "#.###.#.#.#.#.###.#",
    "#.....#...#.....#.#",
    "#######...#########",
    "#.................#",
    "#.###############.#",
    "#.................#",
    "###################"
]

map5_data = {
    "id": 5,
    "title": "Floor 4: Estacao Se — Platform 2",
    "intro": "Yellow warning tiles along the track edge. An abandoned silver commuter train waits in silence.",
    "depth": 4,
    "tileset": "dungeon_ffxii_depth_explore",
    "music": "dungeon1",
    "image": "DungeonFloors1.png",
    "layout": map5_layout,
    "spawn": {"x": 9, "y": 15, "dir": "N"},
    "encounters": [
        {"actor": "shadow_stalker", "weight": 6, "levelMin": 6, "levelMax": 8},
        {"actor": "wisp", "weight": 5, "levelMin": 5, "levelMax": 7},
        {"actor": "gargoyle", "weight": 5, "levelMin": 5, "levelMax": 7},
        {"actor": "golem", "weight": 4, "levelMin": 5, "levelMax": 7}
    ],
    "encounterTroop": "metro_wandering",
    "events": [
        {
            "id": 1,
            "name": "Stairs Up to Concourse",
            "label": "Stairs Up",
            "x": 9,
            "y": 15,
            "trigger": "bump",
            "priority": "same",
            "sprite": "assets/sprites/dungeon_stairs_up.png",
            "commands": [
                {"cmd": "TEXT", "text": "Ascend back to Concourse?"},
                {
                    "cmd": "CHOICE",
                    "options": [
                        {
                            "label": "Ascend",
                            "commands": [
                                {"cmd": "SET_FLAG", "flag": "milestone_return_2", "value": True},
                                {"cmd": "SET_FLAG", "flag": "vigil_active", "value": True},
                                {"cmd": "LOAD_MAP", "mapId": 4}
                            ]
                        },
                        {"label": "Stay on Platform", "commands": []}
                    ]
                }
            ]
        },
        {
            "id": 2,
            "name": "Abandoned Train Carriage",
            "label": "Train Interior",
            "x": 3,
            "y": 9,
            "trigger": "interact",
            "priority": "same",
            "sprite": "assets/sprites/OBJ_TreasureChest_001.png",
            "commands": [
                {
                    "condition": "hasItem:209",
                    "commands": [
                        {"cmd": "TEXT", "text": "The vinyl seats of the commuter train are covered in fine dust."}
                    ],
                    "elseCommands": [
                        {"cmd": "CHANGE_ITEM", "item": "209", "count": 1},
                        {"cmd": "CHANGE_ITEM", "item": "36", "count": 1},
                        {"cmd": "CHANGE_ITEM", "item": "12", "count": 1},
                        {"cmd": "TEXT", "text": "Under an advertising placard, you find a nylon shoulder bag left on the seats."},
                        {"cmd": "TEXT", "text": "Obtained Lost Commuter's Bag, Ambrosia x1, and Golden Egg x1!"}
                    ],
                    "cmd": "CONDITIONAL_BRANCH"
                }
            ]
        },
        {
            "id": 3,
            "name": "Sub-Boss: Guardian Talos",
            "label": "Talos Guardian",
            "x": 9,
            "y": 7,
            "trigger": "bump",
            "priority": "same",
            "sprite": "assets/sprites/NPC00.png",
            "commands": [
                {
                    "condition": "flag:talos_defeated",
                    "commands": [
                        {"cmd": "TEXT", "text": "Shattered slabs of concrete and twisted iron rebar lie still across the rails."}
                    ],
                    "elseCommands": [
                        {"cmd": "TEXT", "text": "A towering construct of subway concrete and bent rail iron blocks the tunnel throat!"},
                        {"cmd": "BATTLE", "troop": "boss_talos"},
                        {"cmd": "SET_FLAG", "flag": "talos_defeated", "value": True},
                        {"cmd": "GAIN_GOLD", "amount": "75"},
                        {"cmd": "TEXT", "text": "Talos collapses in a shower of sparks and stone dust! The way to the deep breach is clear."}
                    ],
                    "cmd": "CONDITIONAL_BRANCH"
                }
            ]
        },
        {
            "id": 4,
            "name": "The Astral Breach (Rift to Choir)",
            "label": "Astral Breach",
            "x": 9,
            "y": 1,
            "trigger": "bump",
            "priority": "same",
            "sprite": "assets/sprites/dungeon_stairs_down.png",
            "commands": [
                {"cmd": "TEXT", "text": "The iron tracks shear off into an endless starry abyss where cathedral spires drift in silence."},
                {"cmd": "TEXT", "text": "Step across the Astral Breach into Floor 5: The Rusted Choir?"},
                {
                    "cmd": "CHOICE",
                    "options": [
                        {
                            "label": "Cross into the Choir",
                            "commands": [
                                {"cmd": "LOAD_MAP", "mapId": 6}
                            ]
                        },
                        {"label": "Turn back", "commands": []}
                    ]
                }
            ]
        }
    ]
}
write_map(5, map5_data)

# =========================================================================
# MAP 6: Floor 5 — The Rusted Choir (Stratum Climax)
# =========================================================================
map6_layout = [
    "#################",
    "#.......#.......#",
    "#.#####.#.#####.#",
    "#.#...#.#.#...#.#",
    "#.#.#.###.#.#.#.#",
    "#...#.......#...#",
    "#####.#####.#####",
    "#...............#",
    "#.#############.#",
    "#.#.....#.....#.#",
    "#.#.###.#.###.#.#",
    "#...#.#.#.#...#.#",
    "#####.#.#.#####.#",
    "#.....#.#.....#.#",
    "#.#####.#####.#.#",
    "#...............#",
    "#################"
]

map6_data = {
    "id": 6,
    "title": "Floor 5: The Rusted Choir",
    "intro": "Ancient cathedral spires fused with suspended subway rails. The air vibrates with the chime of bells.",
    "depth": 5,
    "tileset": "stillnight_bellroot_vigil",
    "music": "emotional1_bitSad",
    "image": "DungeonFloors1.png",
    "layout": map6_layout,
    "spawn": {"x": 8, "y": 15, "dir": "N"},
    "encounters": [
        {"actor": "crimson_lord", "weight": 4, "levelMin": 7, "levelMax": 9},
        {"actor": "flauros", "weight": 5, "levelMin": 7, "levelMax": 9},
        {"actor": "demon", "weight": 5, "levelMin": 7, "levelMax": 9},
        {"actor": "shadow_stalker", "weight": 5, "levelMin": 7, "levelMax": 9}
    ],
    "encounterTroop": "wandering_x2",
    "events": [
        {
            "id": 1,
            "name": "Return to Platform 2",
            "label": "Stairs Up",
            "x": 8,
            "y": 15,
            "trigger": "bump",
            "priority": "same",
            "sprite": "assets/sprites/dungeon_stairs_up.png",
            "commands": [
                {"cmd": "TEXT", "text": "Return across the rift to Platform 2?"},
                {
                    "cmd": "CHOICE",
                    "options": [
                        {"label": "Return", "commands": [{"cmd": "LOAD_MAP", "mapId": 5}]},
                        {"label": "Stay in Choir", "commands": []}
                    ]
                }
            ]
        },
        {
            "id": 2,
            "name": "The Borrowed Room",
            "label": "The Borrowed Room",
            "x": 3,
            "y": 13,
            "trigger": "interact",
            "priority": "same",
            "sprite": "assets/sprites/NPC03.png",
            "commands": [
                {"cmd": "SET_FLAG", "flag": "found_borrowed_room", "value": True},
                {"cmd": "TEXT", "text": "This stone chamber is an exact duplicate of Room 3 from Passage House in St. Maria."},
                {"cmd": "TEXT", "text": "A stone bowl sits on the floor with a freshly molted pink feather inside."},
                {"cmd": "TEXT", "text": "Saban presses his beak gently into your palm. His presence steady and fearless fills the chamber."}
            ]
        },
        {
            "id": 3,
            "name": "Bell of Salt",
            "label": "Bell of Salt",
            "x": 3,
            "y": 3,
            "trigger": "interact",
            "priority": "same",
            "sprite": "assets/sprites/dungeon_empty_bridle.png",
            "commands": [
                {"cmd": "SET_FLAG", "flag": "bell_salt_rung", "value": True},
                {"cmd": "TEXT", "text": "You strike the Bell of Salt. A sharp, crystalline chime echoes across the cathedral vaults."}
            ]
        },
        {
            "id": 4,
            "name": "Bell of Iron",
            "label": "Bell of Iron",
            "x": 13,
            "y": 3,
            "trigger": "interact",
            "priority": "same",
            "sprite": "assets/sprites/dungeon_empty_bridle.png",
            "commands": [
                {"cmd": "SET_FLAG", "flag": "bell_iron_rung", "value": True},
                {"cmd": "TEXT", "text": "You strike the Bell of Iron. A deep metallic resonance rolls down the subway rails."}
            ]
        },
        {
            "id": 5,
            "name": "Bell of Dusk & Resonance Altar",
            "label": "Bell of Dusk",
            "x": 8,
            "y": 7,
            "trigger": "interact",
            "priority": "same",
            "sprite": "assets/sprites/dungeon_confessional.png",
            "commands": [
                {
                    "condition": "flag:choir_harmonized",
                    "commands": [
                        {"cmd": "TEXT", "text": "All three bells vibrate in perfect three-part harmony. The Ashen Gate stands wide."}
                    ],
                    "elseCommands": [
                        {
                            "condition": "flag:bell_salt_rung, flag:bell_iron_rung",
                            "commands": [
                                {"cmd": "SET_FLAG", "flag": "choir_harmonized", "value": True},
                                {"cmd": "TEXT", "text": "You strike the Bell of Dusk. Salt, iron, and twilight resonate together in an impossible third bell tone!"},
                                {"cmd": "TEXT", "text": "The massive Ashen Gate ahead rumbles open!"}
                            ],
                            "elseCommands": [
                                {"cmd": "TEXT", "text": "The Bell of Dusk sits silent. The Bell of Salt (West) and Bell of Iron (East) must be struck first."}
                            ],
                            "cmd": "CONDITIONAL_BRANCH"
                        }
                    ],
                    "cmd": "CONDITIONAL_BRANCH"
                }
            ]
        },
        {
            "id": 6,
            "name": "Boss: Ashen Guardian Red Dragon",
            "label": "Ashen Gate Climax",
            "x": 8,
            "y": 4,
            "trigger": "bump",
            "priority": "same",
            "sprite": "assets/sprites/NPC00.png",
            "commands": [
                {
                    "condition": "flag:red_dragon_defeated",
                    "commands": [
                        {"cmd": "TEXT", "text": "Embers and shattered scales line the threshold to the Pale Crossing."}
                    ],
                    "elseCommands": [
                        {
                            "condition": "flag:choir_harmonized",
                            "commands": [
                                {"cmd": "TEXT", "text": "Beyond the Ashen Gate, an ancient Red Dragon wreathed in ash and heat uncoils from the abyss!"},
                                {"cmd": "BATTLE", "troop": "boss_red_dragon"},
                                {"cmd": "SET_FLAG", "flag": "red_dragon_defeated", "value": True},
                                {"cmd": "CHANGE_ITEM", "item": "205", "count": 1},
                                {"cmd": "TEXT", "text": "The Red Dragon crashes into the chasm! You claim the First Scale. The path to the final Pale Crossing is open."}
                            ],
                            "elseCommands": [
                                {"cmd": "TEXT", "text": "The Ashen Gate is sealed tight. Ring the three bells to harmonize the choir."}
                            ],
                            "cmd": "CONDITIONAL_BRANCH"
                        }
                    ],
                    "cmd": "CONDITIONAL_BRANCH"
                }
            ]
        },
        {
            "id": 7,
            "name": "Archway to Floor 6 (Pale Crossing)",
            "label": "Pale Archway",
            "x": 8,
            "y": 1,
            "trigger": "bump",
            "priority": "same",
            "sprite": "assets/sprites/dungeon_stairs_down.png",
            "commands": [
                {
                    "condition": "flag:red_dragon_defeated",
                    "commands": [
                        {"cmd": "TEXT", "text": "Step through the archway into Floor 6: The Pale Crossing?"},
                        {
                            "cmd": "CHOICE",
                            "options": [
                                {"label": "Cross to the Threshold", "commands": [{"cmd": "LOAD_MAP", "mapId": 7}]},
                                {"label": "Stay here", "commands": []}
                            ]
                        }
                    ],
                    "elseCommands": [
                        {"cmd": "TEXT", "text": "The guardian dragon still holds the threshold."}
                    ],
                    "cmd": "CONDITIONAL_BRANCH"
                }
            ]
        }
    ]
}
write_map(6, map6_data)

# =========================================================================
# MAP 7: Floor 6 — The Pale Crossing (Culmination)
# =========================================================================
map7_layout = [
    "###############",
    "#.............#",
    "#.###########.#",
    "#.#.........#.#",
    "#.#.#######.#.#",
    "#.#.#.....#.#.#",
    "#.#.#.###.#.#.#",
    "#.#.#.#.#.#.#.#",
    "#.#.#.###.#.#.#",
    "#.#.#.....#.#.#",
    "#.#.#######.#.#",
    "#.#.........#.#",
    "#.###########.#",
    "#.............#",
    "###############"
]

map7_data = {
    "id": 7,
    "title": "Floor 6: The Pale Crossing",
    "intro": "A platform of pale marble suspended beneath the stars. Here the Labyrinth touches all worlds.",
    "depth": 6,
    "tileset": "stillnight_bellroot_vigil",
    "music": "event8_yearning",
    "image": "DungeonFloors1.png",
    "layout": map7_layout,
    "spawn": {"x": 7, "y": 13, "dir": "N"},
    "encounters": [],
    "events": [
        {
            "id": 1,
            "name": "Thestra Seam Pedestal",
            "label": "The First Contract Pedestal",
            "x": 7,
            "y": 7,
            "trigger": "interact",
            "priority": "same",
            "sprite": "assets/sprites/dungeon_crystal_pedestal.png",
            "commands": [
                {"cmd": "TEXT", "text": "In the center of the pale stone sits a single pedestal bearing an unwritten contract seal."},
                {"cmd": "TEXT", "text": "The voices of Ines, of St. Maria, and of the underground transit lines converge into a quiet, breathless clarity."},
                {"cmd": "TEXT", "text": "You have reached the edge of the known Labyrinth. Two irrevocable choices lie before you:"},
                {
                    "cmd": "CHOICE",
                    "options": [
                        {
                            "label": "Return with Saban — Seal the Pale Gate",
                            "commands": [
                                {"cmd": "SET_FLAG", "flag": "ending_return_with_saban", "value": True},
                                {"cmd": "TEXT", "text": "You drive your summoner's seal into the pedestal, locking the deep rupture shut."},
                                {"cmd": "TEXT", "text": "Saban rests his head upon your shoulder as the white stone begins to warm with morning light..."},
                                {"cmd": "LOAD_MAP", "mapId": 8}
                            ]
                        },
                        {
                            "label": "Cross the Boundary — Awaken the Second Rite",
                            "commands": [
                                {"cmd": "SET_FLAG", "flag": "ending_second_rite", "value": True},
                                {"cmd": "TEXT", "text": "You step past the pedestal, out across the starlit void where countless worlds intersect."},
                                {"cmd": "TEXT", "text": "Your name dissolves into the foundational grammar of the Gate..."},
                                {"cmd": "LOAD_MAP", "mapId": 8}
                            ]
                        }
                    ]
                }
            ]
        }
    ]
}
write_map(7, map7_data)

# =========================================================================
# MAP 8: Epilogue — The Morning After
# =========================================================================
map8_layout = [
    "#############",
    "#...........#",
    "#.#########.#",
    "#.#.......#.#",
    "#.#.#####.#.#",
    "#.#.#...#.#.#",
    "#.#.#.#.#.#.#",
    "#.#.#####.#.#",
    "#.#.......#.#",
    "#...........#",
    "#############"
]

map8_data = {
    "id": 8,
    "title": "Epilogue — The Morning After",
    "intro": "The morning bells of St. Maria ring across the quiet valley.",
    "depth": 7,
    "safe": True,
    "tileset": "town_default",
    "music": "event6_happyfinality",
    "image": "TownAlencar.png",
    "layout": map8_layout,
    "spawn": {"x": 6, "y": 9, "dir": "N"},
    "encounters": [],
    "events": [
        {
            "id": 1,
            "name": "Epilogue Chronicle",
            "label": "Chronicle of the Pale Crossing",
            "x": 6,
            "y": 5,
            "trigger": "interact",
            "priority": "same",
            "sprite": "assets/sprites/dungeon_crystal_pedestal.png",
            "commands": [
                {"cmd": "TEXT", "text": "========================================"},
                {"cmd": "TEXT", "text": "SECOND GATE: PALE CROSSING"},
                {"cmd": "TEXT", "text": "========================================"},
                {
                    "condition": "flag:ending_return_with_saban",
                    "commands": [
                        {"cmd": "TEXT", "text": "You emerged from the Labyrinth gate at sunrise."},
                        {"cmd": "TEXT", "text": "Alicia met you with warm bread; Laura nodded from the open forge; Celina stamped your ledger with a single gold seal: 'RETURNED WITH COMPANIONS.'"},
                        {"cmd": "TEXT", "text": "Yukio watched from the parapet, counting Saban's steady footsteps in silence."},
                        {"cmd": "TEXT", "text": "You and Saban shared breakfast in Room 3 as the autumn rain softly fell over St. Maria."}
                    ],
                    "elseCommands": [
                        {
                            "condition": "flag:ending_second_rite",
                            "commands": [
                                {"cmd": "TEXT", "text": "You crossed beyond the mortal boundary into the Great Weave of the Gate."},
                                {"cmd": "TEXT", "text": "In St. Maria, the third bell sounded one last time before falling silent forever."},
                                {"cmd": "TEXT", "text": "Sister Agnes lit the lantern marked THESTRA in the chapel, where it burns with steady, undying flame."}
                            ],
                            "elseCommands": [
                                {"cmd": "TEXT", "text": "The expedition concludes in silence."}
                            ],
                            "cmd": "CONDITIONAL_BRANCH"
                        }
                    ],
                    "cmd": "CONDITIONAL_BRANCH"
                },
                {"cmd": "TEXT", "text": "Thank you for playing this complete campaign interpretation!"},
                {"cmd": "TEXT", "text": "Please record your impressions in the Owner Campaign Journal."}
            ]
        }
    ]
}
write_map(8, map8_data)

print("All maps built and written successfully!")
