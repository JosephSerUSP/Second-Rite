# St. Maria — audit and document of record

**Status:** audit complete, doctrine in draft. This file is the intended single
source of truth for St. Maria's facts. Layout decisions and art briefs both
derive from it; neither derives from the other.

Every claim below is tagged:

- **[canon]** — owner-authored, or authored game text. Binding.
- **[shipped]** — true of `data/` right now, whether or not it should be.
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
| `data/maps/16-29.json` | The town as it actually loads | **Shipped truth for topology** |
| `tools/towngen/build_town.py` | A generator for maps 16–26 | **Stale.** Last touched 24 Aug; maps hand-edited 27 Aug. Destructive if run |
| `docs/design/st-maria-town-screens.md` | Screen graph and transition table | **Internally contradictory.** Head graph current, table at line 70 is a prior generation |
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

Two structural problems produced the drift:

**`build_town.py` never declared which maps it owns.** Nothing in Market Row
signals that it is generated output, so the Padaria door was hand-added on
27 Aug (`dad7cd1e`) and survives only until someone re-runs the generator, which
would silently delete it.

**The living-town lab is on an unmerged branch.** The dossiers and town
definitions quoted throughout this document existed only on
`codex/npc-gauntlet-living-town-draft` (`a5096966`), which is not an ancestor of
`main`. The town's character canon was one branch deletion from being lost, and
was invisible to every agent working from a normal checkout. Restored to the
working tree as part of this audit.

---

## 2. The town as shipped

**[shipped]** Five exteriors, and interiors hanging off them:

```
                    [ Labyrinth 2 ] -- sealed
                          ^
                  [ Churchyard 16 ] -- Gate Guard
                          ^ stair
   UPPER   [ Praca 17 ] ====== [ Backstreet 26 ]
              | stair                 | steps
   LOWER   [ Quay 19 ] ====== [ Market Row 18 ]
```

`======` a street: keep walking, no prompt. `|` a stair: press UP.

| Map | Place | Hangs off | Notes |
|---|---|---|---|
| 20 | Weaponsmith (Laura's forge) | Market Row | |
| 21 | The Rusty Tankard | Quay | The one screen with an authored floor profile |
| 22 | Chapel | Praca | |
| 23 | Laura's House | Backstreet | **Should not exist** — see §4 |
| 24 | Alicia's Room | Praca | **Wrong building** — see §4 |
| 25 | Passage House (Room 3) | Backstreet | One room of a building; corridor and office unwired |
| 27 | Alicia's Padaria | Market Row | Absent from the generator |
| 28, 29 | Padaria and smith, baked 3D | Market Row | Alternate representations, not distinct rooms |

**[shipped]** Door and NPC load: Praca 5, Backstreet 4, Market Row 6, Quay 3,
Churchyard 2. Market Row also carries four NPCs. The Praca is the spawn screen
and the second busiest.

**[shipped]** The exterior graph is a 4-cycle plus one spur. Every exterior has
exactly two street neighbours, so there is no branch point anywhere in the town.

### The grammar constraint

**[canon]** The `bounded_lane` provider gives a screen exactly **two** street
exits — its west bound and its east bound. Every other connection must be an
authored door or stair inside the bounds. A radial or forked screen is legal,
but its spokes are doorways, not street continuations. Any layout proposal that
draws a screen with three or more street edges is not expressible.

**[canon]** Positions are authored in **plate pixels** and converted to lane
units against the plate's real width (`PIXELS_PER_Y = 34.6`, 40px margin). Every
lane bound, door y and NPC y in the shipped JSON is therefore a function of the
plate image. Replacing a plate invalidates all of them. This is the decisive
argument for keeping the generator rather than retiring it.

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

## 4. What is wrong right now

**W1. Alicia's home and her shop are on opposite levels of town.**
Alicia's Room 24 exits to the Praca; the Padaria 27 exits to Market Row. Canon
says one building. **[shipped]** contradicts **[canon]**.

**W2. Laura has a house she should not have.**
Laura's House 23 hangs off the Backstreet. Laura sleeps at the padaria. The map
exists because nothing in the outline showed it had no building to belong to.
(Filed as issue #1006.)

**W3. Laura's separation of home and work is currently invisible.**
It is the most deliberate spatial fact about her — she is the one person in
town who walks home — and the shipped town accidentally gives her a bed next
to nothing in particular instead.

**W4. The Passage House is one room of a building with no building.**
`passage_house_corridor` is authored; the **Passage Office** (the registry that
grants the Crossing Writ) is scoped and unauthored. Both have nowhere to hang.

**W5. The Quay's fiction contradicts its topology.**
Its intro is "The town ends at the water." It is a through-street to Market Row.

**W6. Levels are asserted, not felt.**
Upper/lower is a label on a stair. `ground_profile()` exists and converts
authored plate pixels into world height, and only the Pub uses it.

**W7. There is no architectural doctrine for St. Maria anywhere.**
`art-direction.md` owns the game's look and says nothing about the town's
buildings. `docs/world/` held only `strata-and-return.md`. The exterior plates
were authored without a brief, which is the most likely reason they came out
physically incoherent — they had nothing to be coherent with.

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

**[open]** Whether the cortiço replaces the Backstreet or sits beside it. The
Backstreet is already the town's non-frontage face — laundry, back doors, a lit
shrine — and is tonally most of the way there. Making it the cortiço costs zero
new screens; making them distinct registers costs a courtyard plate.

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
- **The town needs a working port.** **[canon]** Shipping, moored boats, and at
  least one ship past its best. An island that was *stranded* by a war is a
  place whose harbour matters and whose hulls show it.
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
2. **Cortiço vs Backstreet** — replace, or coexist. See §5.2.
3. ~~**Generator ownership.**~~ **Settled.** `build_town.py` owns 16-19 and
   21-26; map 20 is authored (it became the `lauras_smith` 3D room, with an
   interior camera distance of 18.6667), and 27-29 were never generated. The
   market's three hand-added doors are now in `SCREENS`.
   `tools/towngen/check_town.py` gates the boundary from `gates (Windows)`.
4. **Thestra has no visual language, and nothing in the Project supplies one.**
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
5. **How far does §5.4 go**, and does Agnes ever know?
6. **What are the signs?** The town is oblivious "but there are signs." Those
   signs are the entire mechanism by which the reader gets ahead of the town,
   and none of them are authored yet.
7. **Re-authoring the shipped dialogue.** Now that shipped text is formally
   provisional, the town's actual lines are a draft awaiting human revision -
   and that is a much larger open item than it looks.

---

## 7. What this document does not decide

The layout. Deliberately. The braid, the radial and the terrace proposals all
remain on the table, and all three of them were written before the facts above
were assembled. They should be re-derived from this document rather than
defended.
