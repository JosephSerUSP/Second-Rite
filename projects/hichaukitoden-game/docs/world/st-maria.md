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

**[proposed]** St. Maria is a tell: a settlement standing on its own earlier
selves. Four strata, and every exterior plate should show at least two and name
which:

1. **Pre-Lusitanian.** Whatever was built for or around the Labyrinth, oldest
   and strangest, still load-bearing — because nobody demolishes good stone.
   Surviving as foundations, as the wall a bakery was built against, as a
   courtyard that is the wrong shape for anything anyone does in it now.
2. **The reoccupation.** People moving into a place they did not build and do
   not understand, adapting rather than replacing.
3. **The colonial civic layer.** Chapel, praça, azulejo, the *name*. St. Maria
   is a Christian name laid over something older, which makes the name itself a
   ward — and puts the chapel and its graveyard directly on top of the sealed
   gate not by coincidence but as an act of containment by the town's ancestors.
4. **The Labyrinth trade.** Newest, thinnest, and the only layer that is nobody's
   home: the Passage House, the registry, the writs.

The register is Lusophone-colonial in the Santos sense — a port culture layered
over something much older, rather than a Portuguese village reproduced.

### 5.4 The seal

**[canon]** Agnes is *"a mundane source of serenity who is also attuned to a
strange source of truth,"* and her dossier marks *"the church connection and
strange attunement"* as canon directions.

**[proposed]** This is where a weird-fiction reading enters, and it enters
through the chapel rather than through the dungeon. If the Labyrinth predates
the name, then the chapel is not a chapel that happens to sit above a gate: it
is the institution that succeeded whatever kept the gate shut before it, using a
vocabulary that no longer matches what it is doing. The town seals something it
has forgotten the reason for, with a liturgy inherited from a religion that is
not the one it thinks it is practising.

That gives the seal a reason to exist and a reason not to make sense, without
requiring anyone in the town to be able to explain it — which is the failure
mode to avoid. **[open]** how far this goes, and whether Agnes knows.

### 5.5 Filler and population

**[proposed]**

- Most buildings on a plate are **not visitable**, and that is the normal case
  rather than a shortfall. A street of doors that all open is a menu.
- A non-visitable building can still be somebody's authored address. The
  population backlog holds minor residents — name, trade, tenure, where they
  live and where they work — without any of them needing a room or a portrait.
- **No generic instanced townsfolk.** The alternative to a named population is
  not a crowd of interchangeable greeters; it is a smaller number of people who
  are actually somewhere.
- The schedule machinery for this already exists and is unfilled. The
  living-week definition runs Monday–Sunday × morning/afternoon/evening with
  per-NPC obligations, energy, cash and seeded ambient pressures. Every dossier
  has a `routines` field and **every one of them is empty**.

---

## 6. Open questions

1. **Celina's bed.** She works the newest, most outsider-facing institution.
   Own home makes her a small proprietor and softens her. Living at the Passage
   House makes her absorbed by the trade. A room in the cortiço makes her
   labour — a local administering the new economy who goes home to the old town.
   The third is **[proposed]** and unsettled.
2. **Cortiço vs Backstreet** — replace, or coexist. See §5.2.
3. **Generator ownership.** Does `build_town.py` own 27 as well as 16–26, and do
   the 3D bakes 28/29 sit outside it? A regenerate-and-diff gate should follow
   whichever boundary is drawn, so a hand-edit fails loudly instead of silently.
4. **Does the strata reading hold as written?** Four layers were derived from two
   sentences of owner intent. Better corrected before anything derives from it.
5. **How far does §5.4 go**, and does Agnes know what she is doing?
6. **Merging the living-town lab.** The dossiers are restored to the working
   tree; the lab's tooling is still only on the draft branch.

---

## 7. What this document does not decide

The layout. Deliberately. The braid, the radial and the terrace proposals all
remain on the table, and all three of them were written before the facts above
were assembled. They should be re-derived from this document rather than
defended.
