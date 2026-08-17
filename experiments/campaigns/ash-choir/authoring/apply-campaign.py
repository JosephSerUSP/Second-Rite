#!/usr/bin/env python3
"""Apply the Ash Choir experimental campaign to a forked Second Gate Project.

The generated JSON is the playable artifact. This small provenance script keeps
the authored decisions legible and re-runnable without adding campaign logic to
the engine.
"""

from __future__ import annotations

import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"


def load(relative: str):
    return json.loads((DATA / relative).read_text(encoding="utf-8"))


def save(relative: str, value) -> None:
    path = DATA / relative
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def text(value: str, speaker: str | None = None):
    command = {"cmd": "TEXT", "text": value}
    if speaker:
        command["speaker"] = speaker
    return command


def flag(name: str, value=True):
    return {"cmd": "SET_FLAG", "flag": name, "value": value}


def branch(condition: str, commands, otherwise=None):
    command = {
        "cmd": "CONDITIONAL_BRANCH",
        "condition": condition,
        "commands": commands,
    }
    if otherwise is not None:
        command["elseCommands"] = otherwise
    return command


def option(label: str, commands, condition: str | None = None):
    value = {"label": label, "commands": commands}
    if condition:
        value["condition"] = condition
    return value


def choices(options):
    return {"cmd": "CHOICE", "options": options}


def call(common_event_id: int):
    return {"cmd": "CALL_COMMON_EVENT", "commonEventId": common_event_id}


def item(item_id: int, count: int = 1):
    return {"cmd": "CHANGE_ITEM", "item": item_id, "count": count}


def load_map(map_id: int):
    return {"cmd": "LOAD_MAP", "mapId": map_id}


def replace_event(map_data, name: str, replacement: dict) -> None:
    for index, existing in enumerate(map_data.get("events", [])):
        if existing.get("name") == name:
            replacement["id"] = existing.get("id")
            replacement["instanceId"] = existing.get("instanceId")
            map_data["events"][index] = replacement
            return
    replacement["id"] = max([event.get("id", 0) for event in map_data.get("events", [])] + [0]) + 1
    replacement["instanceId"] = "event:ash-choir-" + name.lower().replace(" ", "-")
    map_data.setdefault("events", []).append(replacement)


def fixed_properties(existing: dict, *, name: str, label: str, sprite: str, x: int, y: int):
    return {
        "name": name,
        "label": label,
        "x": x,
        "y": y,
        "trigger": "interact",
        "sprite": sprite,
        "transparent": False,
        "priority": "same",
    }


def dungeon_event(name: str, label: str, sprite: str, commands):
    return {
        "name": name,
        "label": label,
        "spawn": "Random",
        "sprite": sprite,
        "trigger": "bump",
        "wallEvent": True,
        "minimapColor": [0.82, 0.62, 0.30],
        "commands": commands,
    }


def author_common_events() -> None:
    events = load("commonEvents.json")

    # Keep the established arrival film, but give this interpretation a
    # concrete first clue before control returns to the town map.
    events["42"]["commands"] = [
        command for command in events["42"]["commands"]
        if not (
            (command.get("cmd") == "SET_FLAG" and command.get("flag") == "ash_arrival_seen")
            or command.get("text") == "At the edge of the square, gray dust gathers in the shape of a second shadow. Saban watches it until the rain washes it away."
        )
    ]
    events["42"]["commands"].extend(
        [
            flag("ash_arrival_seen"),
            text("At the edge of the square, gray dust gathers in the shape of a second shadow. Saban watches it until the rain washes it away."),
        ]
    )

    events["50"] = {
        "name": "Ash Choir Gate",
        "commands": [
            branch(
                "flag:ash_ending_reached",
                [
                    text("The gate guard has tied a strip of white cloth to the iron. It is the only thing in St. Maria that does not move in the wind."),
                    text("\"You already went where the ash wanted you. Go eat.\"", "Gate Guard"),
                ],
                [
                    branch("flag:ash_arrival_seen", [text("You remember the gray second shadow from your first morning in town.")]),
                    branch(
                        "flag:first_return",
                        [
                            text("The guard looks at Saban's harness, then at the gray dust caught in its seams.", "Gate Guard"),
                            text("\"You came back once. The second descent is never the same place.\"", "Gate Guard"),
                            choices(
                                [
                                    option("Descend toward the Ash Choir.", [flag("ash_second_expedition"), load_map(2)]),
                                    option("Prepare a little longer.", [text("The gate remains open. The Labyrinth is not in a hurry.")]),
                                ]
                            ),
                        ],
                        [
                            branch(
                                "hasItem:198",
                                [
                                    text("Celina's writ catches the gate lantern. The ink is ordinary; the shadow it casts is not.", "Gate Guard"),
                                    choices(
                                        [
                                            option("Begin the first expedition.", [load_map(2)]),
                                            option("Ask about the gray dust.", [text("\"It is not dust from the road. Ask Agnes if you want a name for it.\"", "Gate Guard")]),
                                            option("Not yet.", []),
                                        ]
                                    ),
                                ],
                                [
                                    text("\"Get your Crossing Writ from Registrar Celina. I do not open the gate for intentions.\"", "Gate Guard"),
                                ]
                            ),
                        ]
                    ),
                ]
            )
        ],
    }

    events["51"] = {
        "name": "Alicia's Ash Supper",
        "commands": [
            branch(
                "flag:ash_town_heard",
                [
                    text("Alicia has left a second bowl beside the stove. This one is full of salt, not food.", "Alicia"),
                    text("\"Take the portal. Save the Bell Salt for when a creature's charges, not its courage, run out.\"", "Alicia"),
                ],
                [
                    branch(
                        "flag:first_return",
                        [
                            text("Alicia wipes gray grit from Saban's bridle with a cloth. The grit stains the cloth blue.", "Alicia"),
                            text("\"You can call it ash if that helps. The old people call it a receipt.\"", "Alicia"),
                            choices(
                                [
                                    option("Tell her what you heard below.", [
                                        flag("ash_town_heard"),
                                        item(197),
                                        item(206),
                                        text("Alicia packs a Town Portal and Bell Salt into your field satchel. One creates distance; the other buys another dangerous choice.", "Alicia"),
                                    ]),
                                    option("Just eat and listen.", [
                                        flag("ash_town_heard"),
                                        item(197),
                                        text("She gives you a portal anyway. The soup is too hot and exactly what you needed.", "Alicia"),
                                    ]),
                                ]
                            ),
                        ],
                        [
                            text("Alicia is busy folding paper around a warm loaf. She points you toward the shelf without looking up.", "Alicia"),
                        ]
                    ),
                ]
            )
        ],
    }

    events["52"] = {
        "name": "Ash Choir Ending",
        "commands": [
            text("The Ash Choir is not a room. It is a row of empty mouths cut into the rock, each one holding the sound of a different creature."),
            text("The last mouth still has a little heat in it. Saban lowers his head. The Pixie, if you brought one, refuses to look at you."),
            choices(
                [
                    option("Carry the ember back to St. Maria.", [
                        flag("ash_ending_carried"),
                        item(195),
                        text("You close the ember in a Bell Salt tin. It costs one last breath of MP to keep it from going out."),
                        {"cmd": "CHANGE_MP", "amount": "-35"},
                        text("The stair home is still there. The town will have to decide what the ember means."),
                    ]),
                    option("Break the ember over the contract.", [
                        flag("ash_ending_broken"),
                        text("You press the ember to the oldest contract. The gray mark splits, and every creature beside you exhales at once."),
                        {"cmd": "GAIN_GOLD", "amount": "260"},
                        text("Nothing follows you up except the ordinary sound of your own steps."),
                    ]),
                ]
            ),
            branch("flag:ash_threshold_marked", [text("The salt mark is still visible on the threshold. Fear made a useful map.")]),
            branch("flag:ash_contract_declined", [text("The Pixie you left behind is not in the choir. You keep wondering whether that was mercy or cowardice.")]),
            branch("flag:ash_chime_skipped", [text("You chose not to listen for Saban's old owner. The unanswered name comes home with you anyway.")]),
            branch("flag:ash_salt_left", [text("The Salt Mirror remains unbroken. You spent the charges you had instead of taking another promise from the wall.")]),
            branch("flag:ash_ledger_left", [text("The blank ledger page remains blank. That feels less like safety now that you have seen what fills pages.")]),
            flag("ash_ending_reached"),
            {"cmd": "ERASE_ALL_STRING_PICTURES"},
            text("ASH CHOIR — END\n\nA compressed, experimental Second Gate campaign.\nThe gate is open; St. Maria remembers what you carried home."),
            load_map(1),
        ],
    }

    events["53"] = {
        "name": "Agnes and the Ash",
        "commands": [
            branch(
                "flag:ash_ending_reached",
                [
                    text("Agnes has set a clean saucer on the chapel step. There is a black ember in it, or the idea of one.", "Sister Agnes"),
                    branch(
                        "flag:ash_ending_carried",
                        [text("\"You brought it home. That is not the same as understanding it. It is, however, how understanding starts.\"", "Sister Agnes")],
                        [
                            branch(
                                "flag:ash_ending_broken",
                                [text("\"You broke it. Good. Some things are safest as a memory.\"", "Sister Agnes")],
                                [text("\"The ember is quiet. I cannot tell whether that is mercy.\"", "Sister Agnes")]
                            )
                        ]
                    ),
                ],
                [
                    branch(
                        "flag:first_return",
                        [
                            text("Agnes studies the ash caught in Saban's feathers. She does not brush it away.", "Sister Agnes"),
                            text("\"The Labyrinth is offering you a receipt for every step. Do not mistake a receipt for a blessing.\"", "Sister Agnes"),
                        ],
                        [text("\"If you go below, bring back a fact. Stories multiply in damp places.\"", "Sister Agnes")]
                    ),
                ]
            )
        ],
    }

    # The fork replaces the old canonical gate hub. Keeping its id valid is
    # useful for any inherited event that still points at it, but its old
    # progress-flag branches do not belong to this experiment.
    events["33"] = {"name": "Ash Choir Gate Hub", "commands": [call(50)]}
    events["41"] = {"name": "Town Portal", "commands": [text("A narrow blue seam opens through the boundary."), {"cmd": "PORTAL_TO_TOWN"}]}
    save("commonEvents.json", events)


def author_town() -> None:
    town = load("maps/1.json")

    replace_event(
        town,
        "Gate Guard",
        {
            **fixed_properties(
                {}, name="Gate Guard", label="Gate Guard", sprite="assets/sprites/NPC00.png", x=8, y=2
            ),
            "commands": [call(50)],
        },
    )
    replace_event(
        town,
        "Alicia",
        {
            **fixed_properties(
                {}, name="Alicia", label="Alicia", sprite="assets/sprites/NPC04.png", x=15, y=9
            ),
            "trigger": "bump",
            "wallEvent": True,
            "commands": [call(51)],
        },
    )
    replace_event(
        town,
        "EV012",
        {
            **fixed_properties(
                {}, name="EV012", label="Sister Agnes", sprite="assets/sprites/NPC11.png", x=9, y=6
            ),
            "commands": [call(53)],
        },
    )
    replace_event(
        town,
        "Scholar",
        {
            **fixed_properties(
                {}, name="Scholar", label="Scholar Alchemist", sprite="assets/sprites/NPC05.png", x=12, y=14
            ),
            "commands": [
                text("The Scholar holds a charcoal pencil over an empty ledger. He does not write.", "Scholar"),
                branch(
                    "flag:ash_ledger_read",
                    [text("\"You found a page that waits for a person. Keep it away from the chapel books.\"", "Scholar")],
                    [text("\"If you find a mark that looks like ash but feels like ink, bring me the shape, not the story.\"", "Scholar")]
                ),
            ],
        },
    )
    replace_event(
        town,
        "Euler",
        {
            **fixed_properties(
                {}, name="Euler", label="Euler", sprite="assets/sprites/NPC08.png", x=10, y=14
            ),
            "commands": [
                text("Euler sniffs the ash on Saban's feathers and decides not to bark.", "Euler"),
                branch(
                    "flag:ash_town_heard",
                    [text("The dog follows you to the gate, then sits down before you can ask it to.")],
                    [text("The dog leans against your knee. It is warm, ordinary, and therefore worth noticing.")]
                ),
            ],
        },
    )
    save("maps/1.json", town)


def author_floor(map_id: int, title: str, intro: str, profile: str, special_events) -> None:
    dungeon = load(f"maps/{map_id}.json")
    dungeon["title"] = title
    dungeon["intro"] = intro
    dungeon["generationProfile"] = profile
    dungeon["category"] = "dungeon"
    dungeon["safe"] = False
    # Keep only generic runtime-owned services. Every campaign-specific beat
    # below is an ordinary authored Map Event.
    dungeon["events"] = [
        event for event in dungeon.get("events", []) if event.get("scriptId") in {1, 4, 7, 12, 13}
    ]
    dungeon["events"].extend(special_events)
    save(f"maps/{map_id}.json", dungeon)


def author_dungeons() -> None:
    author_floor(
        2,
        "Floor 1: The Gray Threshold",
        "The first stone is warm. Something has already written down that you arrived.",
        "entry",
        [
            dungeon_event(
                "Ash Ledger",
                "The Gray Ledger",
                "assets/sprites/dungeon_reliquary_drawers.png",
                [
                    branch(
                        "flag:ash_ledger_read",
                        [text("The ledger is shut. The gray line on its cover now ends at your name.")],
                        [
                            text("A narrow ledger has been mortared into the wall. Its pages are packed with tiny charcoal marks."),
                            text("The first page says ST. MARIA. The second page says SABAN. The third page is blank except for a place where a wet thumb has pressed through."),
                            choices([
                                option("Read the blank page.", [
                                    flag("ash_ledger_read"),
                                    item(195),
                                    text("The page takes the heat from your fingers and leaves behind an Ether Seed. It is not a reward; it is an advance payment."),
                                ]),
                                option("Leave the page closed.", [flag("ash_ledger_left")]),
                            ]),
                        ]
                    )
                ],
            ),
            dungeon_event(
                "Contract Knot",
                "A Contract in the Seam",
                "assets/sprites/dungeon_summoner_contract.png",
                [
                    branch(
                        "flag:ash_contract_taken",
                        [text("The seam is empty. A few green sparks still remember the shape of the creature you named.")],
                        [
                            text("A Pixie is wedged in a crack beside a contract knot. It watches Saban first, then your hand."),
                            text("The knot is eager. Your MP is not infinite, and every new creature changes the price of walking home."),
                            choices([
                                option("Offer a contract.", [
                                    {"cmd": "OPEN_RECRUIT", "actorId": "pixie", "level": 2, "sourceKey": "ash_choir:pixie"},
                                    flag("ash_contract_taken"),
                                    text("The Pixie accepts. Its first act is to touch Saban's wing, as if checking that the older contract is still there."),
                                ]),
                                option("Leave the creature space.", [flag("ash_contract_declined"), text("The Pixie stays in the seam. The choice remains yours, even after you walk away.")]),
                            ]),
                        ]
                    )
                ],
            ),
        ],
    )

    author_floor(
        3,
        "Floor 2: The Salt Gallery",
        "Every alcove is dry except one. Every dry alcove smells like the town above.",
        "standard",
        [
            dungeon_event(
                "Salt Mirror",
                "The Salt Mirror",
                "assets/sprites/dungeon_crystal_pedestal.png",
                [
                    branch(
                        "flag:ash_salt_taken",
                        [text("The mirror shows your party with one extra shadow. The Bell Salt in your pack is cold now.")],
                        [
                            text("A sheet of salt has grown across the wall like a mirror. It reflects St. Maria's square, but nobody in the reflection has a face."),
                            choices([
                                option("Break off a clean piece.", [
                                    flag("ash_salt_taken"),
                                    item(206),
                                    text("You take Bell Salt. It restores local charges, not the strategic MP that bought the walk here."),
                                ]),
                                option("Leave the mirror intact.", [flag("ash_salt_left")]),
                            ]),
                        ]
                    )
                ],
            ),
            dungeon_event(
                "Listening Stair",
                "The Listening Stair",
                "assets/sprites/dungeon_confessional.png",
                [
                    branch(
                        "flag:ash_chime_heard",
                        [text("The stair is quiet now. Your own footsteps arrive a half-second before you make them.")],
                        [
                            text("A stair descends into a wall and comes back out of the same wall. From inside it, creatures are making the small sounds they make when they think they are alone."),
                            choices([
                                option("Listen for Saban.", [
                                    flag("ash_chime_heard"),
                                    {"cmd": "CHANGE_MP", "amount": "-35"},
                                    text("You hear Saban's old owner's name, scraped away and spoken from the other side. The stair takes 35 MP for the privilege."),
                                ]),
                                option("Do not spend the MP.", [flag("ash_chime_skipped"), text("You keep walking. The sound follows until the next encounter.")]),
                            ]),
                        ]
                    )
                ],
            ),
        ],
    )

    final_gate = dungeon_event(
        "Ash Choir",
        "The Ash Choir",
        "assets/sprites/dungeon_empty_bridle.png",
        [
            branch(
                "flag:ash_boss_defeated",
                [text("The mouths in the rock are dark. One still holds a coal that refuses to cool.")],
                [
                    branch("flag:ash_second_expedition", [text("The gate remembers your first return. This time it has prepared a guardian.")]),
                    text("Seven empty mouths open in the wall. They are not carved for voices; they are carved for the silence after voices stop."),
                    text("A broad-backed shape blocks the center of the choir. It has the posture of a creature waiting for a contract to be read aloud."),
                    choices([
                        option("Enter the choir.", [
                            {"cmd": "BATTLE", "troop": "boss_ash_choir", "onVictory": [
                                flag("ash_boss_defeated"),
                                item(195),
                                {"cmd": "GAIN_GOLD", "amount": "220"},
                                text("The choir stops singing. A warm ember drops from the guardian's chest into your open hand."),
                                {"cmd": "ERASE_EVENT"},
                                call(52),
                            ]},
                        ]),
                        option("Mark the threshold and retreat.", [
                            flag("ash_threshold_marked"),
                            text("You draw a line of salt across the threshold. It will not stop the guardian, but it gives the fear a shape."),
                        ]),
                    ]),
                ]
            )
        ],
    )

    author_floor(
        4,
        "Floor 3: The Ash Choir",
        "The climax is not deeper. It is more willing to answer.",
        "standard",
        [final_gate],
    )


def author_boss() -> None:
    troops = load("troops.json")
    troops["boss_ash_choir"] = {
        "id": "boss_ash_choir",
        "name": "Boss: Ash Choir Guardian",
        "description": "A compact experimental climax: one heavy guardian and one echo that pressure MP without requiring a level-10 dragon fight.",
        "members": [
            {"actor": "golem", "level": 5},
            {"actor": "wisp", "level": 4},
        ],
        "events": [
            {
                "id": "choir_open",
                "at": "battle_start",
                "once": True,
                "commands": [
                    {"cmd": "EMIT_TEXT", "fallback": "The guardian opens its mouth. The Wisp inside it says Saban's name."},
                ],
            },
        ],
    }
    save("troops.json", troops)


def main() -> None:
    author_common_events()
    author_town()
    author_dungeons()
    author_boss()


if __name__ == "__main__":
    main()
