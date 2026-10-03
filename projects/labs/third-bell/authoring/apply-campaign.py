#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
THE THIRD BELL -- experimental, machine-authored Second Gate campaign.

Provenance script. It records exactly which authored edits turn the forked
Second Gate Project into this campaign. The authored JSON under ../data is the
deliverable; this file exists so a reader can see the campaign as a diff of
intent rather than as a wall of JSON.

Run from the Project root:  python authoring/apply-campaign.py

It is written to be re-runnable: every edit is keyed and replaces its own
previous output rather than appending a second copy.
"""

import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, os.pardir, "data")

CAMPAIGN_TAG = "third_bell"


def load(rel):
    with io.open(os.path.join(DATA, rel), "r", encoding="utf-8") as fh:
        return json.load(fh)


def save(rel, value, indent=2):
    path = os.path.join(DATA, rel)
    with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(value, indent=indent, ensure_ascii=False))
        fh.write(u"\n")


def replace_event(map_data, name, event):
    """Insert or replace one authored map event by name, keeping ids dense."""
    events = map_data.setdefault("events", [])
    for i, existing in enumerate(events):
        if existing.get("name") == name:
            event["id"] = existing.get("id")
            event["instanceId"] = existing.get("instanceId", "event:%s-%s" % (CAMPAIGN_TAG, name.lower().replace(" ", "-")))
            events[i] = event
            return
    event["id"] = max([e.get("id", 0) for e in events] + [0]) + 1
    event.setdefault("instanceId", "event:%s-%s" % (CAMPAIGN_TAG, name.lower().replace(" ", "-")))
    events.append(event)


def text(t, speaker=None, expression=None):
    cmd = {"cmd": "TEXT", "text": t}
    if speaker:
        cmd["speaker"] = speaker
    if expression is not None:
        cmd["expression"] = expression
    return cmd


def branch(condition, then, otherwise=None):
    cmd = {"cmd": "CONDITIONAL_BRANCH", "condition": condition, "commands": then}
    if otherwise is not None:
        cmd["elseCommands"] = otherwise
    return cmd


def flag(name, value=True):
    return {"cmd": "SET_FLAG", "flag": name, "value": value}


def choice(options, cancel=None):
    cmd = {"cmd": "CHOICE", "options": options}
    if cancel is not None:
        cmd["cancelOption"] = cancel
    return cmd


def opt(label, commands, condition=None):
    o = {"label": label, "commands": commands}
    if condition:
        o["condition"] = condition
    return o


def plate(image):
    return {"cmd": "ENTER_LOCATION", "image": image}


def grant_xp(amount):
    """Party XP through the one proven pattern (see Recovery Light, CE 7).

    GRANT_XP takes a single battlerRef; there is no party-wide ref in this
    engine, so a party-wide grant is FOR_EACH over living allies.
    """
    return {
        "cmd": "FOR_EACH", "scope": "living_allies", "as": "ally",
        "do": [{"cmd": "GRANT_XP", "target": "ally", "amount": amount}],
    }


def hurt(amount):
    return {
        "cmd": "FOR_EACH", "scope": "living_allies", "as": "ally",
        "do": [{"cmd": "DAMAGE", "target": "ally", "amount": amount, "pierce": True, "minHp": 1}],
    }


def card(pid, body, y=170, size=10, color=0, font=None):
    c = {
        "cmd": "SHOW_STRING_PICTURE", "id": pid, "text": body,
        "x": 128, "y": y, "anchor": "center", "align": "center", "width": 224,
        "fontSize": size, "color": color, "opacity": 1, "reveal": True,
        "layer": "screen", "shadow": True,
    }
    if font:
        c["font"] = font
    return c


def backdrop(pid, path):
    return {
        "cmd": "SHOW_IMAGE_PICTURE", "id": pid, "path": "assets/cinematics/" + path,
        "x": 128, "y": 120, "anchor": "center", "opacity": 1, "scale": 1, "layer": "backdrop",
    }


FADE_OUT = [{"cmd": "SET_SUBTRACTIVE_FADE", "amount": 1, "duration": 0.9, "easing": "burn_in"},
            {"cmd": "WAIT", "duration": 1.0}]
FADE_IN = [{"cmd": "SET_SUBTRACTIVE_FADE", "amount": 0, "duration": 1.2, "easing": "smooth"}]


def slide(pic_id, image, line, hold=3.4, y=170):
    """One cinematic beat: fade to a plate, reveal a line, fade out."""
    return ([backdrop(pic_id, image)] + FADE_IN + [card(1, line, y=y),
            {"cmd": "WAIT", "duration": hold},
            {"cmd": "ERASE_STRING_PICTURE", "id": 1}] + FADE_OUT +
            [{"cmd": "ERASE_IMAGE_PICTURE", "id": pic_id}])


# ---------------------------------------------------------------------------
# 1. Items -- three campaign key items
# ---------------------------------------------------------------------------

def author_items():
    items = load("items.json")
    by_id = dict((it.get("id"), it) for it in items)
    new = [
        {
            "id": 208, "name": "Bellroot Leaf", "type": "quest", "cost": 0, "icon": 178,
            "iconPalette": "emerald",
            "description": "A paper leaf cut from St. Maria's Summoner ledger. It is still a leaf, which means the name on it is still owed.",
            "meta": {"craftable": False, "craftIngredient": False},
        },
        {
            "id": 209, "name": "Half-Contract", "type": "quest", "cost": 0, "icon": 178,
            "iconPalette": "sapphire",
            "description": "Torn down the fold. The Summoner's half is missing; the creature's half was signed four times. The last signature is wet.",
            "meta": {"craftable": False, "craftIngredient": False},
        },
        {
            "id": 210, "name": "Warden's Clapper", "type": "quest", "cost": 0, "icon": 80,
            "iconPalette": "gold",
            "description": "Cold iron, shaped like a tongue. Something has been ringing without one for a very long time.",
            "meta": {"craftable": False, "craftIngredient": False},
        },
    ]
    for item in new:
        if item["id"] in by_id:
            items[items.index(by_id[item["id"]])] = item
        else:
            items.append(item)
    save("items.json", items)


# ---------------------------------------------------------------------------
# 2. Troop -- the Eternal Warden, the campaign's final threshold
# ---------------------------------------------------------------------------

def author_troop():
    troops = load("troops.json")
    troops["boss_eternal_warden"] = {
        "id": "boss_eternal_warden",
        "name": "Boss: The Eternal Warden",
        "description": (
            "EXPERIMENTAL / campaign-specific. Final threshold of THE THIRD BELL. "
            "The Warden keeps St. Maria's ledger and rings the answering bell. It fields two bound "
            "wisps -- the first and second bells -- and re-lights them once. Designed to run long "
            "enough to reach Battle Strain so the fight is priced against the walk home, and to "
            "punish a party that arrived with no MP left."
        ),
        "members": [
            {"actor": "hyperion", "level": 13},
            {"actor": "wisp", "level": 9},
            {"actor": "wisp", "level": 9},
        ],
        "events": [
            {
                "id": "warden_opening", "at": "battle_start", "once": True,
                "commands": [
                    {"cmd": "EMIT_TEXT", "fallback": "The Warden does not turn around. Two small lights take up position beside it."},
                    {"cmd": "SCREEN_EFFECT", "effect": "shake", "power": 3, "duration": 30},
                ],
            },
            {
                "id": "warden_reads", "at": "round_start", "once": True, "when": "battle.round == 3",
                "commands": [{"cmd": "EMIT_TEXT", "fallback": "The Warden reads a name aloud. It is not yours yet."}],
            },
            {
                "id": "warden_relight", "at": "after_action", "once": True, "when": "enemies.aliveCount <= 1",
                "commands": [
                    {"cmd": "EMIT_TEXT", "fallback": "The Warden strikes the floor. A bell that had gone out is lit again."},
                    {"cmd": "SCREEN_EFFECT", "effect": "flash", "color": [180, 200, 255], "power": 3, "duration": 30},
                    {"cmd": "SPAWN_ENEMIES", "troop": "warden_second_bell"},
                ],
            },
            {
                "id": "warden_strain_warn", "at": "round_start", "once": True, "when": "battle.round == 6",
                "commands": [{"cmd": "EMIT_TEXT", "fallback": "Strain. The summoning is being charged for its own length."}],
            },
            {
                "id": "warden_last_phase", "at": "after_action", "once": True, "when": "enemy.hpRate <= 0.35",
                "commands": [
                    {"cmd": "EMIT_TEXT", "fallback": "The Warden finally faces you, and its face is a page."},
                    {"cmd": "SCREEN_EFFECT", "effect": "shake", "power": 6, "duration": 50},
                    {"cmd": "FOR_EACH", "scope": "living_allies", "as": "ally",
                     "do": [{"cmd": "DAMAGE", "target": "ally", "amount": "max(1, floor(ally.maxHp * 0.10))", "pierce": True, "minHp": 1}]},
                ],
            },
        ],
    }
    troops["warden_second_bell"] = {
        "id": "warden_second_bell",
        "name": "The Second Bell (relit)",
        "description": "EXPERIMENTAL / campaign-specific. Reinforcement troop used once by boss_eternal_warden.",
        "members": [{"actor": "wisp", "level": 9}],
    }
    save("troops.json", troops)


# ---------------------------------------------------------------------------
# 3. Common events -- pacing spine, the Vigil's third bell, the ending
# ---------------------------------------------------------------------------

def author_common_events():
    ce = load("commonEvents.json")

    # --- 40: Stairs Up. Compressed to TWO incursions before the Vigil, and it
    # now owns the campaign's single mandatory return-to-town beat.
    ce["40"] = {
        "name": "Dungeon Entrance Stairs",
        "label": "Stairs Up",
        "minimapColor": [0, 0.8, 0.8],
        "commands": [
            text("Climb toward St. Maria?"),
            choice([
                opt("Climb up", [
                    branch("session.floor == 1", [
                        flag("first_return"),
                        # Two incursions open the Vigil (canon Second Gate uses three;
                        # this campaign compresses the ramp deliberately).
                        branch("flag:incursion_one_completed", [flag("vigil_ready")],
                               [flag("incursion_one_completed")]),
                        {"cmd": "LOAD_MAP", "mapId": "1"},
                        branch("flag:vigil_held", [
                            {"cmd": "SET_MAP_PRESENTATION", "mapId": "1", "tileset": "town_default",
                             "fogPreset": "night fog", "ambientR": "0.12", "ambientG": "0.12", "ambientB": "0.12"},
                        ], [
                            branch("flag:vigil_ready", [
                                {"cmd": "SET_MAP_PRESENTATION", "mapId": "1", "tileset": "town_003",
                                 "fogPreset": "purple_dusk", "ambientR": "0.24", "ambientG": "0.09", "ambientB": "0.18"},
                            ], []),
                        ]),
                        # The one mandatory return beat: carrying Ines's Half-Contract
                        # back up changes the town before the last descent.
                        branch("hasItem:209", [
                            branch("flag:mid_return_done", [], [
                                {"cmd": "CALL_COMMON_EVENT", "commonEventId": 45},
                            ]),
                        ], []),
                    ], [
                        {"cmd": "LOAD_MAP", "mapId": "session.floor", "arrival": "exit"},
                    ]),
                ]),
                opt("Stay", []),
            ]),
        ],
    }

    # --- 35: Chapel and Vigil. The Vigil is the campaign's midpoint; this adds
    # the beat the base game stops just short of -- the third bell answering,
    # and Agnes handing the player the rest of the game.
    vigil_attend = [
        text("At dusk, St. Maria closes its shops. Bakers, guards, children and scavengers gather without being called."),
        text("The first bell names the living. When Agnes speaks your name, the village answers: RETURNED."),
        text("At midnight, lanterns are carried to the Labyrinth gate. The second bell names those who remain below."),
        text("After the final name, something beneath St. Maria rings a third time."),
        text("Every flame bends toward the gate. One extinguished lantern relights by itself."),
        flag("vigil_held"),
        flag("third_bell_heard"),
        flag("act2_open"),
        {"cmd": "SET_MAP_PRESENTATION", "mapId": "1", "tileset": "town_default",
         "fogPreset": "night fog", "ambientR": "0.12", "ambientG": "0.12", "ambientB": "0.12"},
        text("Nobody moves until the sound stops. Then everyone moves at once, and very quickly, as though the square had been cleared by weather.", "Sister Agnes", 4),
        text("\"Two bells are ours. We ring them. The third is not ours and we do not ring it.\"", "Sister Agnes", 2),
        choice([
            opt("\"Then who does?\"", [
                text("\"That is the question the village has agreed not to ask for eleven years. You have been here nine days.\"", "Sister Agnes", 3),
                text("\"You are the only person in St. Maria who can go and look, and the only person nobody will miss.\" She says the second part kindly.", "Sister Agnes", 5),
                text("\"Find what answers us. Bring me something I can hold. And Summoner -- come back up the way you went down.\"", "Sister Agnes", 2),
                {"cmd": "CHANGE_ITEM", "item": "208", "count": 1},
                text("She presses a paper leaf into your hand -- cut from the ledger, blank on both sides. \"When it stops being blank, you will know how far down you are.\""),
            ]),
            opt("Say nothing.", [
                text("\"Good. The ones who talk during the third bell tend to answer it.\"", "Sister Agnes", 3),
                {"cmd": "CHANGE_ITEM", "item": "208", "count": 1},
                text("She presses a paper leaf into your hand anyway -- cut from the ledger, blank on both sides."),
            ]),
        ]),
    ]

    ce["35"] = {
        "name": "Chapel and Vigil",
        "commands": [
            plate("st_maria_chapel.png"),
            branch("flag:vigil_held", [
                branch("flag:warden_defeated", [
                    text("Agnes has not sat down. There is a second lantern beside the first now, and she keeps looking at the bell rope rather than at you.", "Sister Agnes", 4),
                    text("\"You are carrying it. I can hear it not ringing.\"", "Sister Agnes", 2),
                ], [
                    text("The chapel smells of cold wax and wet flowers. A single unclaimed lantern rests beneath the bell rope."),
                    choice([
                        opt("Read the lantern.", [
                            text("The card bears one name: THESTRA. The ink is fresh. The handwriting is yours."),
                        ]),
                        opt("Ask Agnes about the third bell.", [
                            text("\"It is under us and it is patient. That is all eleven years taught me.\"", "Sister Agnes", 3),
                            text("\"Go down. Take the stairs, not the seam -- a portal is a loan, and something below keeps the books.\"", "Sister Agnes", 2),
                        ]),
                        opt("Leave it alone.", []),
                    ]),
                ]),
            ], [
                branch("flag:vigil_ready", [
                    text("The chapel doors stand open. Candlelight pours across the square, and names have been tied to the eaves on narrow cards."),
                    choice([
                        opt("Attend the Vigil.", vigil_attend),
                        opt("Not yet.", [
                            text("Agnes nods. \"The village can wait. It has practice.\"", "Sister Agnes", 3),
                        ]),
                    ]),
                ], [
                    text("The chapel is cool and nearly empty. Someone has left a bucket beneath a leak in the roof."),
                ]),
            ]),
        ],
    }

    # --- 45: the mandatory return beat, fired by CE 40 when the player carries
    # the Half-Contract up the last flight of stairs.
    ce["45"] = {
        "name": "Return Beat - The Half-Contract Comes Up",
        "commands": [
            flag("mid_return_done"),
            plate("st_maria_home.png"),
            text("PASSAGE HOUSE -- ROOM 3\n\nYou did not come here first. You came here anyway; your feet did it while you were thinking about the paper."),
            text("The Half-Contract has dried on the walk up. It is a creature's half. Four signatures, one owner, and the owner's side torn away and gone."),
            branch("flag:found_ines_mark", [
                text("You have seen the hand before, backward, in blue chalk on a wall that was warm."),
            ], []),
            text("Someone has been in the room. The bed is made the way you do not make it. The feed bowl has been moved to where a larger animal could reach it."),
            choice([
                opt("Check what is missing.", [
                    text("Nothing. Nothing at all is missing. Something has been added: a second bowl, smaller, dry, and never used."),
                    flag("room_second_bowl"),
                ]),
                opt("Leave it exactly as you found it.", [
                    text("You close the door and stand in the corridor for a while, listening to five empty rooms."),
                ]),
            ]),
            text("Outside, St. Maria is doing the thing towns do after a Vigil: working loudly, so that nobody has to be quiet."),
            text("Take the paper to Agnes, and the stairs down after. The way you went down, she said."),
            flag("act3_open"),
        ],
    }

    # --- 44: THE ENDING. Three variants off one threshold choice.
    ce["44"] = author_ending()

    save("commonEvents.json", ce)


def author_ending():
    """The Third Bell -- authored ending, three variants, then the epilogue town."""

    # The coda reads back what this particular run actually did below. Every
    # optional beat in the campaign lands here, so no authored flag is
    # decorative and the ending differs run to run.
    reflections = [
        branch("flag:choir_struck_three", [
            text("The clean bell in the Rusted Choir knew your name before you gave it away. You have decided not to think about the order of those two events."),
        ], [
            branch("flag:choir_struck_two", [
                text("You still have the small change from the Rusted Choir. St. Maria mint. It spends."),
            ], [
                branch("flag:choir_struck_one", [
                    text("One thin ordinary note from a rusted bell, and you walked out on the other four. You are almost sure that was the right number."),
                ], [
                    branch("flag:choir_declined", [
                        text("You crossed the Rusted Choir with your hands at your sides and it has bothered you ever since, which was presumably the arrangement."),
                    ], []),
                ]),
            ]),
        ]),
        branch("flag:weighed_name", [
            text("The Vault still has your name on its counterweight. You got a seed and a leaf for it. Nobody has mispronounced you yet."),
        ], []),
        branch("flag:weighed_gold", [
            text("Three hundred coins, and the Weighing Room was appalled. You would do it again. That is the appalling part."),
        ], []),
        branch("flag:weighed_creature", [
            text("NOT YOURS TO WEIGH. YOU ARE HOLDING IT FOR SOMEONE. You have stopped arguing with the chalk."),
        ], []),
        branch("flag:garden_read_the_leaf", [
            text("In the Garden Without Wind your leaf hung at the height of your face and told you the terms. You cannot say you were not told the terms."),
        ], []),
        branch("flag:room_second_bowl", [
            text("There is a second feed bowl in Room 3, smaller, still dry. You have not moved it and you do not intend to."),
        ], []),
        branch("flag:found_cerberus", [
            text("Cerberus cost six MP a step for the whole campaign and was worth exactly none of it, and you would not give him back."),
        ], []),
    ]

    def credits(final_line):
        return ([
            {"cmd": "SET_SUBTRACTIVE_FADE", "amount": 1},
            {"cmd": "ERASE_ALL_STRING_PICTURES"},
            {"cmd": "ERASE_ALL_IMAGE_PICTURES"},
        ] + slide(30, "arrival_bell.png", final_line, hold=4.6)
          + slide(31, "arrival_street.png",
                  "St. Maria rang two bells that winter\nand did not discuss the third.", hold=4.2)
          + slide(32, "arrival_together.png",
                  "You came for impossible things.\nYou were charged for one.", hold=4.6)
          + [
            {"cmd": "SET_SUBTRACTIVE_FADE", "amount": 1},
            card(50, u"THE THIRD BELL", y=100, size=14, color=0, font="DotGothic16-Regular"),
            card(51, u"an experimental Second Gate campaign\nmachine-authored, not canon", y=140, size=8, color=7),
            {"cmd": "WAIT", "duration": 5.0},
            {"cmd": "ERASE_STRING_PICTURE", "id": 50},
            {"cmd": "ERASE_STRING_PICTURE", "id": 51},
            {"cmd": "WAIT", "duration": 0.8},
            flag("campaign_ending_reached"),
            {"cmd": "ERASE_ALL_STRING_PICTURES"},
            {"cmd": "ERASE_ALL_IMAGE_PICTURES"},
            {"cmd": "LOAD_MAP", "mapId": 1},
            {"cmd": "SET_MAP_PRESENTATION", "mapId": "1", "tileset": "town_default",
             "fogPreset": "night fog", "ambientR": "0.30", "ambientG": "0.28", "ambientB": "0.22"},
            {"cmd": "SET_SUBTRACTIVE_FADE", "amount": 0, "duration": 2.2, "easing": "smooth"},
            plate("st_maria_home.png"),
            text("ST. MARIA -- EARLY WINTER\n\nThe walk up took two days and you do not remember either of them."),
        ])

    return {
        "name": "The Third Bell - Ending",
        "scene": "cinematic",
        "commands": [
            text("The bell has no clapper and never has. It has been ringing for eleven years with nothing inside it."),
            text("The Warden's iron tongue is warm in your hand. It fits. Of course it fits."),
            text("Above you, through nine hundred feet of rock, St. Maria is asleep and countable."),
            text("A name goes in with the clapper. That is the whole of the mechanism. Whoever is named is what the bell means."),
            choice([
                # --- Ending A: name yourself.
                opt("Ring your own name.", [
                    flag("ending_named_self"),
                    text("You say it once, quietly, the way the Registrar taught you to say it at the gate."),
                    text("The bell takes it. The sound goes up and does not come back down."),
                ] + credits(
                    "You are still in the ledger.\nYou are simply no longer at the top of it.")
                  + [
                    text("Nine days later a woman you have never met stops you in the square and says your name correctly, and cries, and cannot explain why."),
                    text("Agnes rings two bells at the next Vigil. The third answers in your voice, and the village -- which has agreed not to ask -- says RETURNED."),
                    text("You did not get rich. You got remembered, which in St. Maria is the more expensive of the two."),
                ] + reflections),
                # --- Ending B: name a creature.
                opt("Ring the name on your oldest contract.", [
                    flag("ending_named_creature"),
                    text("Saban's contract is the oldest thing you own. The previous owner's name was scraped off it before you were given him."),
                    text("He does not resist. He has done this before, for someone else, and he remembers the shape of it."),
                    text("You say SABAN into the bell. The bell says it back, and keeps saying it."),
                    {"cmd": "FOR_EACH", "scope": "living_allies", "as": "ally",
                     "do": [{"cmd": "RECORD_HISTORY", "target": "ally", "field": "witnessed_third_bell", "amount": 1}]},
                    {"cmd": "GAIN_GOLD", "amount": "4200"},
                ] + credits(
                    "The Labyrinth pays promptly\nfor a name in good condition.")
                  + [
                    text("You are rich. Laura will not take the commission. Alicia serves you and does not sit down."),
                    text("At the next Vigil, Agnes reads the second bell's list and there is a name on it that has never been below."),
                    text("In the Garden Without Wind, nine hundred feet down, one paper leaf has finally become a root."),
                ] + reflections),
                # --- Ending C: cut the rope.
                opt("Cut the rope.", [
                    flag("ending_cut_rope"),
                    text("Ines got four signatures onto a half-contract and never got the other half back. That is not a debt. That is a filing system."),
                    text("You put the clapper down on the floor, unrung, and cut the rope above the crown."),
                    text("The bell comes down slowly, the way large things do, and does not make a sound when it lands, which is the loudest thing you have ever heard."),
                ] + credits(
                    "The ledger closed with names still owed.\nNobody came to collect.")
                  + [
                    text("There is no third bell at the winter Vigil. Agnes rings two and waits, and the silence goes on long enough that people start to leave."),
                    text("Nobody thanks you. Two of them are angry. One woman -- old, not from here, INES on the card she ties to the eaves -- finds you at the gate and holds your hands until you stop shaking."),
                    text("St. Maria will need a new reason to be worth living in. That was always going to be somebody's problem."),
                ] + reflections),
            ]),
            text("\n\nTHE THIRD BELL ends here.\n\nSt. Maria is open; the townsfolk have something to say about how it went. When you are done, rate the campaign with the journal in the README."),
        ],
    }


# ---------------------------------------------------------------------------
# 4. Dungeon authorship -- three distinct floor ideas plus the final threshold
# ---------------------------------------------------------------------------

def author_floor_3():
    """Map 4 / Floor 3: THE RUSTED CHOIR -- a push-your-luck greed ladder."""
    m = load("maps/4.json")

    strike_three = [
        text("The third bell has no rust on it at all."),
        text("You strike it. It does not ring -- it answers, in a voice with a St. Maria accent, and what it says is your own name with the vowels worn off."),
        flag("choir_struck_three"),
        {"cmd": "CHANGE_ITEM", "item": "195", "count": 1},
        text("Something falls out of the bell's mouth into your palm: an Ether Seed, warm, and heavier than a seed."),
        {"cmd": "CHANGE_MP", "amount": "-25"},
        text("The Choir takes its fee out of the summoning. Twenty-five MP that you were going to walk home on."),
        {"cmd": "BATTLE", "onVictory": [
            text("The other four bells stay quiet for the rest of your visit. That is somehow worse."),
        ]},
    ]

    strike_two = [
        text("The second bell is packed with wet salt and old wax. Striking it is like hitting a mattress."),
        flag("choir_struck_two"),
        {"cmd": "GAIN_GOLD", "amount": "180"},
        text("Coins come out. Not treasure -- change. Small denominations, St. Maria mint, the kind people carry."),
        hurt("8 + session.floor * 2"),
        text("The floor of the Choir tilts a few degrees toward the pit, and every one of you feels it in the teeth."),
        choice([
            opt("Strike the third bell.", strike_three),
            opt("Two is enough.", [text("You walk out with your change. The bells sway for a while after you have gone.")]),
        ]),
    ]

    strike_one = [
        text("The first bell is thin with rust. You strike it and the note is small and completely ordinary."),
        flag("choir_struck_one"),
        grant_xp("60"),
        text("Every creature with you goes very still and then relaxes, the way an animal does when a room stops being dangerous."),
        text("Something in the pit below rolls over."),
        choice([
            opt("Strike the second bell.", strike_two),
            opt("Leave while it is still ordinary.", [text("You take the ordinary note with you and let the other four alone.")]),
        ]),
    ]

    replace_event(m, "The Rusted Choir", {
        "name": "The Rusted Choir",
        "label": "Five Rusted Bells",
        "spawn": "Random",
        "sprite": "assets/sprites/dungeon_crystal_pedestal.png",
        "trigger": "bump",
        "wallEvent": True,
        "minimapColor": [0.85, 0.7, 0.25],
        "commands": [
            plate("campaign_rusted_choir.png"),
            branch("flag:choir_struck_three", [
                text("Five bells hang over the dry pit. Four are rusted through. The fifth is clean, and it is the one that knows your name."),
            ], [
                text("Five bells hang over the dry pit on a rail, in order of size, the way they would be hung for a procession."),
                text("They are not fixed. Somebody hung them here to be struck, and then arranged that nobody would want to."),
                text("The Choir is a bargain and it does not hide it: each bell pays better and costs more. You may stop between any two."),
                choice([
                    opt("Strike the first bell.", strike_one),
                    opt("Walk under them without touching anything.", [
                        text("You cross the Choir with your hands at your sides. Nothing happens, which the floor seems to find disappointing."),
                        flag("choir_declined"),
                    ]),
                ]),
            ]),
        ],
    })
    save("maps/4.json", m)


def author_floor_4():
    """Map 5 / Floor 4: THE WEIGHING ROOM -- the Vault appraises the expedition."""
    m = load("maps/5.json")

    weigh_gold = [
        branch("session.gold >= 300", [
            text("You put three hundred coins on the pan. The pan does not move at all, which is insulting, and then drops all the way."),
            {"cmd": "GAIN_GOLD", "amount": "-300"},
            {"cmd": "CHANGE_MP", "amount": "session.maxMp"},
            {"cmd": "CHANGE_ITEM", "item": "195", "count": 1},
            text("The summoning fills to the brim. An Ether Seed rolls off the counterweight side and stops against your boot."),
            text("The Vault has valued your money correctly and is quietly appalled by it."),
            flag("weighed_gold"),
        ], [
            text("You have nothing on you the pan will accept as money. It waits, politely, for a very long time."),
        ]),
    ]

    weigh_name = [
        text("There is no pan for this. You say your name over the empty side of the scale and the scale believes you."),
        text("It weighs about as much as a coat."),
        flag("weighed_name"),
        {"cmd": "CHANGE_ITEM", "item": "195", "count": 1},
        {"cmd": "CHANGE_ITEM", "item": "208", "count": 1},
        {"cmd": "CHANGE_MP", "amount": "session.maxMp"},
        text("An Ether Seed. A second Bellroot Leaf, this one not blank -- it has your name on it in a hand that is nearly yours."),
        text("You will get this back. You are almost certain you will get this back."),
        {"cmd": "CHANGE_MP", "amount": "-10"},
    ]

    weigh_creature = [
        text("You lift the smallest of your creatures onto the pan. It sits down. It is not frightened, which is the part you will think about later."),
        text("The Vault reads the weight, considers, and puts the creature back down on the floor, gently, unpaid."),
        text("Written on the counterweight in fresh chalk: NOT YOURS TO WEIGH. YOU ARE HOLDING IT FOR SOMEONE."),
        flag("weighed_creature"),
        grant_xp("90"),
    ]

    replace_event(m, "The Weighing Room", {
        "name": "The Weighing Room",
        "label": "The Weighing Room",
        "spawn": "Random",
        "sprite": "assets/sprites/dungeon_crystal_pedestal.png",
        "trigger": "bump",
        "wallEvent": True,
        "minimapColor": [0.75, 0.75, 0.4],
        "commands": [
            branch("flag:weighing_room_used", [
                text("The scale hangs level and empty. On the counterweight, in chalk, someone has added: CLOSED FOR THE SEASON."),
            ], [
                text("A merchant's balance scale, twice your height, bolted through the floor of a room with no door but the one you came through."),
                text("It is clean. Everything else on this floor is nine hundred years of dust and the scale is clean."),
                text("The counterweight side is already loaded with something you cannot see. The empty pan is at chest height, waiting."),
                choice([
                    opt("Weigh your money.", weigh_gold + [flag("weighing_room_used")]),
                    opt("Weigh one of your creatures.", weigh_creature + [flag("weighing_room_used")]),
                    opt("Weigh your name.", weigh_name + [flag("weighing_room_used")]),
                    opt("Weigh nothing. Leave.", [
                        text("You back out. Behind you the pan rises very slightly, as though something had been taken off it."),
                    ]),
                ]),
            ]),
        ],
    })
    save("maps/5.json", m)


def author_floor_5():
    """Map 6 / Floor 5: INES -- the half-contract, and the key to the last descent."""
    m = load("maps/6.json")

    replace_event(m, "The Half-Contract", {
        "name": "The Half-Contract",
        "label": "A Torn Contract",
        "spawn": "Random",
        "sprite": "assets/sprites/dungeon_summoner_contract.png",
        "trigger": "bump",
        "wallEvent": True,
        "minimapColor": [0.35, 0.55, 0.95],
        "commands": [
            branch("hasItem:209", [
                text("The niche is empty. The blue chalk line runs into it and stops, the way a sentence stops when the speaker is interrupted."),
            ], [
                text("The blue chalk line -- the one from the entry hall, the one that turns every corner without breaking -- ends here, in a niche at knee height."),
                text("Inside: a contract torn straight down the fold. The Summoner's half is gone. The creature's half has been signed four times."),
                branch("flag:found_ines_mark", [
                    text("Four signatures. The gate guard said Ines went down three times, and on the fourth only her creatures came back."),
                    text("So the fourth signature is not hers. Somebody signed for her, in her hand, after."),
                ], [
                    text("Four signatures in the same hand, and the fourth one is still wet."),
                ]),
                choice([
                    opt("Take it.", [
                        {"cmd": "CHANGE_ITEM", "item": "209", "count": 1},
                        text("You take the creature's half. The blue line goes out behind you, all the way back to the entry hall, floor by floor, like a lamp being turned down."),
                        branch("hasItem:208", [
                            text("In your pack, the blank Bellroot Leaf Agnes gave you is no longer blank. It says: FIVE DOWN. ONE TO GO."),
                        ], []),
                        text("Carry it up the stairs. Agnes asked for something she could hold."),
                    ]),
                    opt("Leave it where she left it.", [
                        text("You put it back exactly as it was. The chalk line stays lit. Somebody, somewhere, is still owed."),
                    ]),
                ]),
            ]),
        ],
    })
    save("maps/6.json", m)


def author_floor_6():
    """Map 7 / Floor 6: the Stillnight Sanctum -- Warden, bell, threshold, ending."""
    m = load("maps/7.json")

    # Anti-softlock: the base floor 6 had no way back up at all.
    replace_event(m, "Sanctum Stairs", {
        "name": "Sanctum Stairs",
        "scriptId": 40,
        "x": 2, "y": 2,
        "spawn": "Fixed",
        "sprite": "assets/sprites/dungeon_wall_lever.png",
    })

    warden_fight = [
        text("It is holding a rope that goes up into nothing. It has been holding it for eleven years and its arm has not moved."),
        text("Two small lights hang either side of it at head height. They are bells. They are also, in some way you would rather not have noticed, people."),
        choice([
            opt("Take the rope from it.", [
                {"cmd": "BATTLE", "troop": "boss_eternal_warden", "onVictory": [
                    flag("warden_defeated"),
                    {"cmd": "CHANGE_ITEM", "item": "210", "count": 1},
                    text("The Warden goes down without letting go of the rope, so the rope comes down with it."),
                    text("Its other hand has been closed this whole time. Inside is an iron clapper, warm, worn smooth by a grip exactly the size of yours."),
                    {"cmd": "FOR_EACH", "scope": "living_allies", "as": "ally",
                     "do": [{"cmd": "RECORD_HISTORY", "target": "ally", "field": "stood_at_the_third_bell", "amount": 1}]},
                    text("The two small lights go out politely, one after the other, like people leaving a room where somebody has died."),
                ]},
            ]),
            opt("Back away.", [
                text("You back out of the sanctum. The Warden does not follow. It has never followed anybody."),
            ]),
        ]),
    ]

    replace_event(m, "The Eternal Warden", {
        "name": "The Eternal Warden",
        "label": "The Eternal Warden",
        "spawn": "Fixed",
        "x": 8, "y": 6,
        "sprite": "assets/sprites/dungeon_empty_bridle.png",
        "trigger": "interact",
        "minimapColor": [0.9, 0.9, 1.0],
        "commands": [
            branch("flag:warden_defeated", [
                text("A coil of cut rope and a shape on the floor that is not quite a body and not quite a page."),
                {"cmd": "ERASE_EVENT"},
            ], [
                text("Something is standing at the centre of the sanctum with its back to you. It is the size of a person who has been added to."),
                branch("hasItem:209", [
                    text("The Half-Contract goes cold in your pack. That is not a figure of speech; you have to move it away from your ribs."),
                ], [
                    text("You have nothing to show it and nothing to ask it. You could still go back for both."),
                ]),
            ] + warden_fight),
        ],
    })

    replace_event(m, "The Third Bell", {
        "name": "The Third Bell",
        "label": "The Third Bell",
        "spawn": "Fixed",
        "x": 8, "y": 10,
        "sprite": "assets/sprites/dungeon_crystal_pedestal.png",
        "trigger": "interact",
        "minimapColor": [1.0, 0.95, 0.6],
        "commands": [
            branch("flag:campaign_ending_reached", [
                text("The sanctum is empty in whichever way you left it empty."),
            ], [
                branch("hasItem:210", [
                    {"cmd": "CALL_COMMON_EVENT", "commonEventId": 44},
                ], [
                    text("A bell the size of the room hangs from a rope that goes up into nothing. There is no clapper. There has never been a clapper."),
                    branch("flag:warden_defeated", [
                        text("You are missing the piece. You had it. Go and find where you put it."),
                    ], [
                        text("It is ringing anyway. You can feel it in the flat of your teeth, and there is nothing inside it to ring with."),
                        text("Somebody is holding the rope. Somebody has been holding it for eleven years."),
                    ]),
                ]),
            ]),
        ],
    })

    # The Garden Without Wind gains its campaign payload: it now reads the
    # player's own paper leaf back to them.
    for e in m.get("events", []):
        if e.get("name") == "Garden Without Wind":
            e["commands"] = [
                branch("flag:found_stillnight_garden", [
                    text("The paper leaves remain still. The one bearing Saban's name has grown a second stem."),
                ], [
                    text("White trees grow from a floor of black water. Their leaves are slips cut from St. Maria's Summoner ledger."),
                    text("Most names have become roots. Saban's is still a leaf."),
                    branch("hasItem:208", [
                        text("Agnes's leaf lifts out of your pack by itself and hangs among the others, at the height of your face, in the only part of the garden with any wind."),
                        text("It says, in ink that is not dry: THE THIRD BELL RINGS FOR WHOEVER IS NAMED. NOBODY HAS BEEN NAMED FOR ELEVEN YEARS."),
                        flag("garden_read_the_leaf"),
                    ], []),
                    branch("hasItem:209", [
                        text("One root, older than the others, has a torn edge. It matches the half-contract in your pack the way a jaw matches a jaw."),
                    ], []),
                    flag("found_stillnight_garden"),
                ]),
            ]
    save("maps/7.json", m)


# ---------------------------------------------------------------------------
# 5. Town -- the epilogue voice of St. Maria
# ---------------------------------------------------------------------------

def base_commands(entry):
    """Original (pre-campaign) body of a wrapped hub, so re-runs never nest.

    author_town_epilogue wraps existing hubs instead of rewriting them. Without
    this, a second run would wrap the wrapper and strand the first run's flags.
    """
    if "_thirdBellBase" in entry:
        return entry["_thirdBellBase"]
    entry["_thirdBellBase"] = entry.get("commands", [])
    return entry["_thirdBellBase"]


def author_town_epilogue():
    """Alicia and Laura get an epilogue register; the gate closes the campaign."""
    ce = load("commonEvents.json")

    epilogue_lines = {
        "30": ("Alicia", [
            (["flag:ending_named_self"],
             "\"I said your name this morning without meaning to. I was counting bread.\" She looks at her hands. \"Twice.\""),
            (["flag:ending_named_creature"],
             "She serves you first, before the guards, and will not take the money, and does not once ask where he is."),
            (["flag:ending_cut_rope"],
             "\"There was no third bell.\" She says it like a diagnosis. \"Half of them think you did nothing. I know what nothing sounds like.\""),
        ]),
        "31": ("Laura", [
            (["flag:ending_named_self"],
             "\"You want me to engrave what.\" She puts the tongs down. \"No. Not your name. Ask me again in a year and I still will not.\""),
            (["flag:ending_named_creature"],
             "\"I will not take the commission.\" The forge is going full. She is not making anything. \"Buy something. Do not buy it from me.\""),
            (["flag:ending_cut_rope"],
             "\"Bring me the rope.\" She is the only person in St. Maria who has asked you a direct question all week. \"I want to see the cut.\""),
        ]),
    }

    for ce_id, (speaker, lines) in epilogue_lines.items():
        existing = ce[ce_id]
        guard = None
        for cond, line in reversed(lines):
            node = branch(cond[0], [text(line, speaker, 4)], [guard] if guard else [])
            guard = node
        # Epilogue register takes priority; otherwise fall through to the
        # original hub exactly as authored.
        original = base_commands(existing)
        ce[ce_id] = {
            "name": existing.get("name"),
            "_thirdBellBase": original,
            "commands": [branch("flag:campaign_ending_reached", [guard], original)],
        }

    # The gate is where the player closes the book.
    gate = ce["34"]
    # Mid-campaign the guard tracks how far the player has got. These read the
    # act flags the Vigil and the return beat set.
    progress = [
        branch("flag:act3_open", [
            text("\"Agnes has your paper. She has not put it down since.\" He unbolts the gate before you ask. \"Stairs, she said. Not the seam.\"", "Gate Guard", 2),
        ], [
            branch("flag:act2_open", [
                text("\"You heard it too, then.\" He does not say what. \"Eleven years I have stood on top of that.\"", "Gate Guard", 5),
            ], [
                branch("flag:third_bell_heard", [
                    text("\"Whatever you heard at the Vigil, do not repeat it in the Tankard.\"", "Gate Guard", 3),
                ], []),
            ]),
        ]),
    ]
    gate["commands"] = [branch("flag:campaign_ending_reached", [
        plate("st_maria_chapel.png"),
        text("The gate guard has the writ book open and is not writing in it.", "Gate Guard", 5),
        branch("flag:ending_named_self", [
            text("\"They keep asking me to confirm you came back up. I keep saying yes.\" He taps the page. \"It is written here that you did.\"", "Gate Guard", 2),
        ], []),
        branch("flag:ending_named_creature", [
            text("\"You went down with a count and came up with a count one lower, and the book says otherwise, and I am not going to argue with the book.\"", "Gate Guard", 2),
        ], []),
        branch("flag:ending_cut_rope", [
            text("\"Eleven years I have stood here listening to that thing agree with us.\" He shuts the book. \"Thank you. Nobody else is going to say it.\"", "Gate Guard", 5),
        ], []),
        choice([
            opt("Close the book.", [
                text("\n\nTHE THIRD BELL\n\nan experimental, machine-authored Second Gate campaign\n\nThank you for playing. The owner's rating journal is in the campaign README."),
                text("You may leave the game from the menu (ESC) whenever you like. St. Maria will keep going without you; that is rather the point of it."),
            ]),
            opt("Stay in St. Maria a while longer.", []),
        ]),
    ], progress + base_commands(gate))]
    ce["34"] = gate

    save("commonEvents.json", ce)


# ---------------------------------------------------------------------------
# 6. Shop -- the retreat economy the campaign is actually priced around
# ---------------------------------------------------------------------------

def author_shop():
    """Stock the escape hatches so retreat pressure is a real purchase.

    Base Second Gate defines Town Portal (197) and Bell Salt (206) but sells
    neither, so the expedition horizon had no price attached to it. This
    campaign is explicitly about how far you can afford to walk, so both go on
    Alicia's shelf -- Bell Salt from the start, the Portal only once the town
    trusts you, and both expensive enough that buying one is a decision.
    """
    shops = load("shops.json")
    stock = shops["1"]["items"]
    have = set(row.get("id") for row in stock)
    if 206 not in have:
        stock.append({"id": 206})
    if 197 not in have:
        stock.append({"id": 197, "condition": "flag:first_return"})
    save("shops.json", shops)


def main():
    author_items()
    author_shop()
    author_troop()
    author_common_events()
    author_floor_3()
    author_floor_4()
    author_floor_5()
    author_floor_6()
    author_town_epilogue()
    print("THE THIRD BELL: campaign authored into %s" % os.path.normpath(DATA))


if __name__ == "__main__":
    main()
