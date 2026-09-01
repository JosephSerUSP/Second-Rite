---
type: design
scope: game
status: active
---

# St. Maria — audit and document of record

**Status:** canon audit complete, doctrine in draft. This is the source of truth
for St. Maria's authored facts. It does not claim implementation status; use
`docs/ENGINE-STATE.md`, the live Project and the regenerate-and-diff gate for
that. Layout decisions and art briefs derive from this record; neither derives
from the other.

Design claims below are tagged:

- **[canon]** — owner-authored, or authored game text. Binding.
- **[open]** — a real question, not yet decided.
- **[proposed]** — written by Claude for discussion. Not yet canon.

---

## 1. Why this document exists

Six sources currently describe St. Maria and they disagree. Three separate
layout proposals were written against them in August 2026, and all three reached
false conclusions — each one grounded on a different subset and reported
confidently. The failure was not carelessness in any of them. It was that no
source declared its own authority, so each analysis picked one and trusted it.

| Source | What it holds | Authority |
|---|---|---|
| `data/maps/16-31.json` | The town as it actually loads | **Runtime truth for topology** |
| `tools/towngen/build_town.py` | Authored generator for maps 16–19, 21–26 and 31 | **Authority for generated town data.** `check_town.py` regenerate-diffs its output |
| [`st-maria-layout.md`](st-maria-layout.md) | Six-screen spiral, four chords and building consolidation | **Approved layout intent** |
| [`st-maria-techniques.md`](st-maria-techniques.md) | Camera, pitch, projection-window, scale, bake and grammar mechanisms; no imagery | **Always-readable mechanism record** |
| `docs/design/town-authoring-known-good.md` | Sterile visual-research boundary and generic acceptance rules | **Authority for what fresh art work may inspect** |
| `docs/research/npc-gauntlets/dossiers/*.json` | Character canon, with provenance | **Canon for character**, explicitly provisional for dialogue |
| `docs/research/npc-gauntlets/towns/*.json` | Buildings, households, weekly obligations | **Canon for who lives and works where** |
| `docs/design/st-maria-shop-briefs.md`, `st-maria-interior-authoring.md` | Interior art briefs and authoring status | Current |
| `data/commonEvents.json`, `data/maps/*` **dialogue** | Shipped in-game text | **Provisional, NOT canon.** Largely LLM-generated. Subordinate to the dossiers |

> **Shipped text is not evidence.** The dossiers state that the live in-game
> dialogue is mostly LLM-generated and provisional. That applies to
> `commonEvents.json` too. During this audit an entire reading of the seal was
> built on CommonEvent 35 ("Chapel and Vigil") before the owner identified it as
> AI-generated test content. Quote the dossiers and the town definitions; treat
> anything a character says in the shipped data as a draft.

Two structural problems produced the original drift and are now guarded:

**Generator ownership was invisible.** A Padaria door was hand-added on 27 Aug
(`dad7cd1e`) and would once have vanished on regeneration. `SCREENS`,
`AUTHORED_NOT_GENERATED` and `tools/towngen/check_town.py` now make the boundary
executable.

**The living-town canon was once branch-only.** The dossiers and town
definitions quoted throughout this document originated on
`codex/npc-gauntlet-living-town-draft` (`a5096966`). They are now in the Project;
the branch is no longer their authority.

---

## 2. The town as shipped

The approved shape has six exteriors and four cross-connections. The live map
records and generator decide whether a checkout currently matches it:

```
                    [ Labyrinth 2 ] -- sealed
                          |
                  [ Churchyard 16 ] -----------.
                          |                    | long climb
                    [ Praça 17 ] -----.        |
                          |            | stair |
                    [ Cortiço 26 ] -.  |       |
                          |          |  |       |
                  [ Market Row 18 ] |  |       |
                          |          |  |       |
                     [ Quay 19 ] ----'  |       |
                          |             |       |
                     [ Port 31 ] -------'-------'
```

The street chain is Churchyard → Praça → Cortiço → Market → Quay → Port.
The long climb closes the ring; Praça↔Quay, Cortiço↔Port and the padaria's
Market↔Cortiço route are authored chords.

| Map | Place | Hangs off | Notes |
|---|---|---|---|
| 20 | Laura's forge | Port | Authored 3D room; not generator-owned |
| 21 | The Rusty Tankard | Quay | The one screen with an authored floor profile |
| 22 | Chapel | Praça | |
| 23 | Padaria hearth/home | Cortiço | Attached to maps 24 and 27 |
| 24 | Padaria room upstairs | map 23 | Alicia and Laura's home |
| 25 | Passage House (Room 3/registry) | Cortiço | Celina works here |
| 27 | Alicia's Padaria | Market Row | Authored, not generator-owned |
| 28, 29 | Padaria and smith, baked 3D | Market Row | Alternate representations, not distinct rooms |

The full transition table and derivation live in `st-maria-layout.md`; this
record does not maintain a second copy.

### The grammar constraint

**[canon]** The `bounded_lane` provider gives a screen exactly **two** street
exits — its west bound and its east bound. Every other connection must be an
authored door or stair inside the bounds. A radial or forked screen is legal,
but its spokes are doorways, not street continuations. Any layout proposal that
draws a screen with three or more street edges is not expressible.

**[canon]** Positions are authored in **plate pixels** and converted to lane
units against the plate's real width and that screen's declared scale. Legacy
plates use 34.6 px/unit; modelled work uses 27.4286 px/unit; margins are 40 px.
Every lane bound, door y and NPC y is therefore a function of both the plate and
its scale. Replacing either invalidates all of them. See
[`st-maria-techniques.md`](st-maria-techniques.md#lane-and-plate-scale).

---

## 3. The people

**[canon]** From the dossiers. These are owner-authored and binding; the
dossiers mark live in-game dialogue as LLM-generated and provisional, so
individual shipped lines are *not* evidence of character.

| Person | Core | Works | Sleeps |
|---|---|---|---|
| **Alicia** | Creative, obsessive, depressed, poorly functional. Undemanding and quirky; avoids anything she fears would let someone down | Padaria — bakery, town staples, summoner provisions, and candles for the Vigil | The padaria's attached home |
| **Laura** | Trauma-armored, extremely competent, buys status with competence. Verbally committed to a rationality her choices do not support | A **formerly abandoned forge she occupies**, across town near the pub | The padaria's attached home, with Alicia |
| **Celina** | Cynical, jaded, slow to warm; an exceptionally reliable friend once earned. Fears death, uncommitment, disorder | The registry — issues the Crossing Writ | **[open]** — see §6 |
| **Sister Agnes** | A mundane source of serenity who is *also attuned to a strange source of truth* | The chapel | **[proposed]** the chapel |
| **Barkeep** | Practical, dry, hospitable; careful social triage disguised as casualness | The Rusty Tankard | The Tankard's rooms |
| **The Gambler** | Theatrical, *galhofeiro*, sketchy, good-humoured, large. A collector of numbers | Nothing. He has no trade | Rents at the Tankard when in town |

**[canon]** Household facts, from `towns/st_maria_living_week.json`:

- Alicia operates the padaria and lives in its attached house **with Laura**.
- Laura contributes money to Alicia's household; Alicia spends it on comforts
  and gifts for Laura.
- The Barkeep lives at the Tankard. The Gambler rents there and the Barkeep is
  wary of extending him informal credit.
- Alicia reliably attends Agnes's Friday feast. Celina attends briefly, Laura
  rarely, the Barkeep is usually too tired, the Gambler is unpredictable.

**[canon]** Laura and Alicia are in love with each other and no good at saying
so. The shop briefs state that if the padaria and the forge read as one room
redressed, both have failed.

---

## 4. Findings and disposition

**W1. Alicia's home and shop were unrelated maps. Resolved in the approved
layout.** Maps 23, 24 and 27 are one building spanning Market Row and Cortiço.

**W2. Laura had a house she should not have. Resolved in the approved layout.**
Map 23 is the padaria hearth/home; Laura sleeps there with Alicia.

**W3. Laura's separation of home and work was invisible. Resolved spatially.**
Her occupied forge is at the Port and her home is across town in the padaria.

**W4. Passage House had no building context. Partly resolved.** It now hangs
from the Cortiço and contains Room 3/registry authority. Further rooms remain
content scope, not a topology contradiction.

**W5. The Quay's fiction contradicted its topology. Resolved.** The Port is the
working waterfront and the Quay text no longer claims to terminate the town.

**W6. Levels are asserted, not felt.**
Upper/lower is a label on a stair. `ground_profile()` exists and converts
authored plate pixels into world height, and only the Pub uses it.

**W7. The town lacked architectural doctrine. Partly resolved.** The interior,
exterior, sterile-authoring and techniques documents now define operations and
mechanisms. Thestra's visual language remains open in §6.

**W8. The town has six named people and no population.**
There is no one who works for someone else. The pub has no cook, no supplier,
no laundry. Nobody rents except the Gambler. There is no labour in a town whose
entire economy is described as "meals, beds, steel and funerals."

---

## 5. Doctrine in draft

Everything in this section is **[proposed]** unless marked otherwise, and is the
material for discussion.

### 5.1 Tenure is the town's class structure

The pattern is not "most buildings are live-work." It is sharper:

> **Trade and bed are the same address — if you hold the frontage.**

That is the propertied pattern: Alicia over the padaria, Agnes in the chapel,
the Barkeep in the Tankard's rooms. It is the normal condition of a
pre-industrial coastal town, where separating home from work is an industrial
idea that has not arrived.

The characterisation is in who breaks it, and the breaks are already authored:

- **Laura** breaks it for love. She holds no frontage — she *occupies* an
  abandoned forge — and she sleeps at someone else's address. Her walk home
  across town is the romance drawn on the map.
- **The Gambler** breaks it by having no trade at all. He is only a bed, and he
  pays inn rates for it.
- **The Passage House** breaks it institutionally. It is the one building that
  is nobody's home, built for people passing through.

A tenure axis therefore runs across the whole town, and it wants at least four
positions: **owns the frontage**, **occupies without title** (Laura),
**rents a room** (the Gambler, the player), and **lives in the subdivided
building** — the cortiço.

### 5.2 The cortiço

A cortiço is a building that used to be something else: a grand house
subdivided, one address holding many households, sharing a courtyard and its
facilities. It is where the town's labour lives — the people whose work happens
in a building they do not hold.

It earns its place three ways:

1. **It is where the population goes.** W8 needs somewhere for the pub's cook,
   its supplier, whoever does the laundry, and dock labour to actually live.
2. **It is cheap for what it holds.** One plate, many doors, many households.
   The `bounded_lane` grammar is good at exactly this shape.
3. **It is the reoccupation thesis made walkable rather than stated.** A
   subdivided building is a building with two histories in it by definition.

The manor is its counterpart: whoever holds title to the building the cortiço
lives in is a person the town has not yet met.

**[canon]** The cortiço replaces the Backstreet. The old screen was already the
town's non-frontage face—laundry, back doors and a lit shrine—so the same map
becomes the address of households that hold no frontage.

### 5.3 Strata

**[canon]** `game-vision.md` already establishes that the Labyrinth should
resist a single explanation and suggest *"recurrence, memory, and incompatible
histories."* That principle is currently scoped to the descent. There is no
reason for it to begin at the trapdoor.

**[canon]** The sequence, from the owner:

1. **Thestra.** The original settlement, built to contain the Labyrinth. Gone.
2. **St. Maria.** A town that flourished on an island in a prosperous moment,
   repurposing Thestra's ruins while **oblivious that there was a Labyrinth at
   all**.
3. **The war.** St. Maria sat comfortably outside any warzone, but the war
   strained its finances and its navigability. It became stranded and short of
   supplies.
4. **The way in.** Someone found it. Riches followed, and the town has regained
   notoriety and financial health because of them.

> **Not the same "strata."** [`strata-and-return.md`](strata-and-return.md)
> uses *stratum* for a **band of Labyrinth floors**. Here it means an
> **archaeological layer of the town above ground**. The two are unrelated;
> that document owns the descent, this one owns the surface.

**[proposed]** Four strata follow from that, named by rupture rather than by
culture, with one signature operation each:

1. **Thestra** — present now only as the thing everything else is built *on,
   against and out of*. Its architecture is **undesigned**: there is no
   authored material vocabulary for it anywhere in the Project, and inventing
   one is a prerequisite for any exterior art. See open question 4.
2. **The oblivious town** — reuse *without recognition*. This is the layer that
   carries the whole reading, and it is visually distinct from reverent reuse: a
   niche holding a flowerpot, a pillar serving as a mooring post, a doorway too
   large for the house built into it. Nobody is being sacrilegious. Nobody
   knows. **[open]** what those older forms actually look like.
3. **The stranding** — the war's mark is *thrift*, not damage. Subdivision,
   blocking-up, patching in cheaper material, a second family in a house built
   for one. This is where the manors became cortiços: not a catastrophe, a
   slow inability to keep them.
4. **The writ** — thin, new, and the only layer that is nobody's home. The
   Passage House, the registry, the summoners.

**[proposed]** The operations vocabulary is what an artist is actually briefed
with, because periods cannot be drawn and operations can:

> **reused** · **subdivided** · **blocked** · **re-consecrated** · **robbed**
> (this building is missing its facing because that one has it) · **buttressed**
> (something is being held up that wants to fall)

Name the operation on a wall, not the century. Operations recur and combine, so
they cannot collapse into the formula that "every plate shows two strata" would
have become.

**[canon]** St. Maria is an **island**, and should feel nautical and isolated:
deep skies, the horizon, and the sea visible from many screens.

**[proposed]** Two consequences worth taking seriously before any layout work:

- **The ring is the coastline.** **[canon]** Finding P1 called the 4-cycle a
  corridor bent into a circle. On an island it is simply the rim, which is the
  correct shape. **P1 is retired rather than fixed**: what the town lacks is not
  a branch point but elevation and outlook.
- **The town needs a working port, as a sixth exterior.** **[canon]** Its own
  screen, not the Quay upgraded: shipping, moored boats, and at least one ship
  past its best. An island that a war left *stranded* is a place whose harbour
  matters and whose hulls show it. This is the first exterior St. Maria has
  gained since the two-level split, and the lower tier's identity comes from it.
- **The tiers get their identity from the water.** Upper is sky, horizon and
  rooftops seen from above; lower is the water's edge, wet stone and hulls. The
  Churchyard is already "above the rooftops" and is the town's highest outlook.
  This also retires W5 properly: "the town ends at the water" stops reading as a
  contradiction once the edge is felt from everywhere, and the Quay is merely
  where you touch it.

### 5.4 The seal

**[canon]** The Labyrinth is **not** Lovecraftian pure evil, and opening it was
not a release. The harm is barely noticed. The town has become richer and more
notable because of it. St. Maria's condition is **obliviousness, not dread** —
but there are signs.

**[canon]** There is nonetheless a reason it was sealed.

**[canon]** Agnes is *"a mundane source of serenity who is also attuned to a
strange source of truth,"* and her dossier marks *"the church connection and
strange attunement"* as canon directions — while explicitly forbidding
omniscience or exposition.

#### The design problem

Thestra spent an entire settlement on containment. Whatever the Labyrinth is
was worth founding a town around. Yet opening it produces no perceptible
catastrophe, and the town's own accounts have improved.

Anything that resolves this has to be worth a civilisation's whole effort while
being invisible at the scale of one lifetime and one ledger.

#### **[proposed]** The wealth is the mechanism

The Labyrinth pays. The paying is the harm. Not a price charged against a boon,
but the same transaction seen from two ends — which is why nobody notices: the
town is looking at its side of it, and its side is money.

Thestra did not seal a creature in. It capped a **draw**. Their achievement was
not defeating anything; it was working out what taking costs, and then stopping.

This does three things the alternatives do not. It makes the town's prosperity
inseparable from its danger, so no character has to choose between wealth and
safety — the choice is not offered. It puts the cost on people who are not
present to object. And it satisfies **recurrence**: the seal has been reached
before, by people who got rich first and understood second.

The sharpest form of that: **Thestra is what St. Maria becomes if it
understands.** The ruin the town is built on is its own future. A civilisation
that grew wealthy on the Labyrinth, learned the price, and then spent everything
it had gained building the lid. St. Maria is currently at Thestra's early stage
and is living inside the evidence.

#### **[proposed]** What Thestra was like

Not a warrior culture, and not priests in the ecstatic sense. A **custodial**
one — administrative, liturgical, patient, and obsessed with counting.

The Sumerian register fits here rather than the Lovecraftian one: temple
economies, ration lists, seals and scribes. A civilisation whose civic centre
was an accounting office for something that could not be allowed to go
unmeasured. The proposal worth testing is that their sacred objects are not
gods to worship but **tallies**, and that the place a count was kept is the
place a prayer would be said in any other culture. Nothing in the Project
authors this yet - it is an invitation to design Thestra's forms around
measurement rather than around worship.

Their end need not be dramatic. A custodial culture fails by **dwindling and by
failing to explain itself to whoever comes next** — which is precisely what
happened, since St. Maria moved in without ever learning what it had moved into.

That also gives layer 2 its best single image, if the tally reading survives:
St. Maria keeping flowers in a niche that held the count of the taken.

#### Where the unease actually lives

Not in a monster and not in dread. In **obliviousness with signs** — the town
demonstrably correct about its own prosperity and wrong about what it is
standing on. The reader should be ahead of the town, and no character should
confirm it.

Agnes is the pressure point, and her constraint is the reason she works: she is
attuned and must never explain. Proximity, not knowledge. She has spent her life
inside a building that is, unknown to her, part of the lid.

**[open]** How far this goes, and whether Agnes ever knows.

### 5.5 Filler buildings

**[canon]** Maps can and should carry **non-visitable buildings**.

**[proposed]** That is the normal case rather than a shortfall: a street whose
doors all open is a menu, not a town. Density of frontage is what makes a place
look inhabited, and it is nearly free - a painted door costs a door.

A non-visitable building is still somebody's address. It is where the register
in §5.6 lives, and the two are the same design: the town's apparent size comes
from buildings nobody enters, occupied by people nobody meets.

### 5.6 The town register

**[canon]** Alicia, Laura, the Barkeep, Celina, Agnes and the Gambler are the
game's main and supporting cast; the PC is the player's stand-in. St. Maria also
needs **minor townsfolk**, and they must not be "welcome to Coneria" - no
generic instanced villager with no bearing on the world.

**[canon]** Every minor NPC is tracked individually: a house, a job, a schedule.
The **engine does not have to simulate this**. It is an authoring source of
truth.

#### **[proposed]** Derive the roster, do not invent it

The town's population should follow from the work the town actually does, so the
count is justified rather than picked. Every business implies labour it cannot
perform alone:

| Establishment | Implies |
|---|---|
| The Rusty Tankard | a cook, a cask-carrier from the quay, someone who does the laundry, a supplier |
| Alicia's padaria | a flour supplier, and **firewood** - a wood-fired oven eats fuel every day, on an island |
| Laura's forge | charcoal and iron, both imported, therefore somebody who lands them |
| The port | boat crews, net menders, whoever keeps the moorings |
| The churchyard | somebody digs. In a town whose trade sends people below, this is not a small job |

The cortiço is where the people in that column live, because none of them hold
a frontage. That is the link between §5.1's tenure axis and this register: the
roster and the housing derive from each other rather than being authored
separately.

#### **[proposed]** The record

Cheap by design. No dossier, no interiority - those belong to the cast. What a
minor NPC needs is an **address and a reason to be somewhere**:

    id, name
    trade
    workplace      - a building, which may be non-visitable
    tenure         - owns frontage | occupies | rents a room | cortico household
    home           - a building
    routine        - where they are per time block
    ties           - who they owe, work for, avoid, are related to

The machinery already exists and is unused. The living-town definitions in
`docs/research/npc-gauntlets/towns/` carry locations, `npcIds`, and an
`initialNpcState` with home, location and obligations, over a Monday-to-Sunday
x morning/afternoon/evening grammar. **Every dossier has a `routines` field and
every one of them is empty.** The register is that slot, filled, and widened to
people who will never need a dossier.

#### **[proposed]** Three rules that keep it out of Coneria

1. **No line without an address.** Anyone who speaks is on the register, with a
   home and a workplace. If they are not on it, they do not talk.
2. **What they say comes from their state, not from a lore pool.** Their day:
   the boat, the price of charcoal, who owes whom, whether the oven was lit.
   Never a rumour about somewhere the player will never go.
3. **Most are never seen, and that is the point.** The register is mostly
   invisible. It is cheap precisely because the majority need no sprite, no
   dialogue and no room. It exists so that the handful the player does meet are
   a *sample of something real* rather than the whole of it.

Rule 3 is what makes the whole thing affordable. A register of forty people
whose entries are six fields each costs almost nothing and can be authored in
an afternoon; what it buys is that the six who speak are consistent with a town
rather than decorating one.

---

## 6. Open questions

1. **Celina's bed.** She works the newest, most outsider-facing institution.
   Own home makes her a small proprietor and softens her. Living at the Passage
   House makes her absorbed by the trade. A room in the cortiço makes her
   labour — a local administering the new economy who goes home to the old town.
   The third is **[proposed]** and unsettled.
2. **Thestra has no visual language, and nothing in the Project supplies one.**
   `showcase_thestra` (`thestra_limestone`, `thestra_shrine_recess`,
   `thestra_idol`, `thestra_pillar`) is **engineering shorthand for a geometry
   showcase on map 9, not lore** - confirmed by the owner. So layer 1 is
   currently a hole. Every other layer can be drawn from something that exists;
   the oldest and strangest one has to be invented before an exterior plate can
   show reuse-without-recognition, because the reuse has to be *of* something
   recognisable.

   **This blocks aesthetic coherence, not spatial coherence.** They are separate
   problems and only the first waits on Thestra. A layout whose screens make
   sense as a place - where the port is, what sees the sea, where people live
   and work - can be authored and walked now, and dressed later. Getting the
   town walkable is the nearer priority.
3. **How far does §5.4 go**, and does Agnes ever know?
4. **What are the signs?** The town is oblivious "but there are signs." Those
   signs are the entire mechanism by which the reader gets ahead of the town,
   and none of them are authored yet.
5. **Re-authoring the shipped dialogue.** Now that shipped text is formally
   provisional, the town's actual lines are a draft awaiting human revision -
   and that is a much larger open item than it looks.

---

## 7. What this document does not decide

Visual composition and implementation status. The approved layout is derived in
[`st-maria-layout.md`](st-maria-layout.md); reusable mechanisms are isolated in
[`st-maria-techniques.md`](st-maria-techniques.md). A fresh art direction still
starts without inspecting the compositions that produced those conclusions.
