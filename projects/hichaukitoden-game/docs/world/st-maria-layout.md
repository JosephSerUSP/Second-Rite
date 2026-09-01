---
type: design
scope: game
status: proposal
---

# St. Maria — layout, derived

**Status: proposal, awaiting approval.** Derived from
[`st-maria.md`](st-maria.md); nothing here is authored yet. The three earlier
layout proposals are superseded — they predate the island, the port, and the
retirement of P1.

---

## 1. What actually constrains this

| Constraint | Source |
|---|---|
| A screen has exactly **two street exits** — its west and east bound. Everything else is a door. | `bounded_lane`, canon |
| St. Maria is an **island**. The ring is the coastline; **P1 is retired**. | canon |
| The deficiency is **elevation and outlook**, not branching. | canon |
| The **port is a sixth exterior**, its own screen. | canon |
| Sea visible from many screens. Upper is sky and horizon, lower is the water's edge. | canon |
| Alicia operates the padaria and **lives in its attached house with Laura**. | canon |
| Laura **occupies an abandoned forge across town, near the pub**. | canon |
| The Passage House is one building: corridor, Room 3, and Celina's office. | authored |

The last two are the sharpest, because together they specify a **walk**. Laura's
home and her work must be far apart, her forge must be near the pub, and the
route between them is the most characterful line the map can draw.

---

## 2. The shape: a spiral, not a ladder

Six exteriors on a ring, and the ring **descends** as it goes round. One circuit
of the island takes you from the Labyrinth gate at the top to the water at the
bottom and back up.

```
                  [ Labyrinth ] -- sealed
                        |
    high      [ 16 Churchyard ] ------------------.
                        |                          |
              [ 17 Praça ]                         |
                        |                          |
              [ 26 Backstreet / Cortiço ]          | the climb
                        |                          | (closes the ring)
              [ 18 Market Row ]                    |
                        |                          |
              [ 19 Quay ]                          |
                        |                          |
    water     [ 31 The Port ] -------------------- '
```

Plus **one chord**: the existing Praça→Quay water stair, kept.

**Why a spiral rather than two tiers joined by rungs.** Two tiers make elevation
a *label on a stair* — the thing W6 says is already wrong. A spiral makes height
monotonic, so every screen sits at a different altitude, every screen has a
different relationship to the horizon, and the sea does compositional work on
all six instead of one. It also means the player never has to be told which
level they are on: they can see it.

**What the chord buys.** Two routes from the civic centre to the water: the long
way round through the cortiço and the market, or straight down the stair. That
is a real choice without a branch point, and it costs nothing — the stair is
already authored.

**The climb is the ring's closure**, from the Port back up to the Churchyard: the
outside of the island, the least built stretch, the biggest sky.

---

## 3. Screen by screen

| # | Screen | Altitude | Outlook | Holds |
|---|--------|----------|---------|-------|
| 16 | **The Churchyard** | highest | horizon over every roof in town | The sealed Labyrinth gate. The Guard. The graveyard. |
| 17 | **The Praça** | high | sea between buildings | Chapel (Agnes). The fountain. Spawn. |
| 26 | **The Cortiço** | mid | glimpses, over laundry | Many households. The Passage House. |
| 18 | **Market Row** | mid-low | roofs below, water beyond | The padaria and its attached house. Stalls. |
| 19 | **The Quay** | low | the water itself | The Rusty Tankard. |
| 31 | **The Port** | lowest | open sea, hulls, sky | Laura's forge. Shipping. The beaten ship. |

### The Cortiço replaces the Backstreet

**[proposed]** — this closes open question 2. The Backstreet is already the
town's non-frontage face: laundry, back doors, a lit shrine. That is most of the
way to a cortiço courtyard, and making it one costs **zero new screens**. It
becomes the address for everyone in §5.6's register who holds no frontage, and
for the Passage House, which belongs beside them precisely because it is the one
building that is nobody's home.

### The Port

The new screen, and the one the town has never had. Working shipping, moored
boats, and at least one ship past its best — an island a war left stranded shows
it in its hulls. Laura's abandoned forge is here: iron and charcoal are landed
at the port, so a forge by the water is where a forge would be, and it is
adjacent to the pub on the Quay exactly as canon requires.

---

## 4. The walk this produces

**Laura goes home** from the Port, through the Quay past the Tankard where the
barkeep is, through Market Row, to the padaria — three screens, uphill, at the
end of the day. She is the only person in St. Maria who commutes, and now the
map says so.

**The player's first loop** is Praça → down the stair → Quay → Market for
supplies → back up. The Labyrinth is visible from the start and reached last.

---

## 5. Building consolidation

Independent of the shape above, and true under any layout:

| Now | Becomes |
|---|---|
| 24 Alicia's Room (off Praça) | a room of **the padaria building**, off Market Row |
| 23 Laura's House (off Backstreet) | retired as a house; Laura sleeps in the padaria's attached home |
| 27 Padaria (off Market) | the shop half of the same building |
| 20 Weaponsmith | Laura's forge, re-sited to the Port |
| 25 Passage House Room 3 | one room of the Passage House, on the Cortiço |

This is W1, W2 and W4 resolved together, and it is the change that makes the two
women's living arrangement legible instead of contradicted.

---

## 6. Cost

| Item | Cost |
|---|---|
| New exterior plates | **1** — the Port |
| Re-sited screens | 0. The five existing exteriors keep their plates |
| Re-wired doors | ~12, all through `SCREENS` in `build_town.py` |
| Retired maps | 0 — 23 and 24 are reused as rooms rather than deleted |
| Blocked on Thestra | nothing. This is spatial coherence; dressing comes later |

The town is walkable with the existing plates the moment the wiring lands. They
will look wrong — they already do — but the *place* will be correct, and the art
pass has something true to dress.

---

## 7. Open

1. **Does the spiral hold**, or do you want the two-tier braid back? The spiral
   is the stronger read of an island but it is the one real choice here.
2. **Does the Cortiço replace the Backstreet**, as proposed, or coexist?
3. **Celina's bed** — still open from `st-maria.md` §6. The Cortiço is the
   proposal.
4. **Map 20's authored 3D room** is a smith interior. Re-siting the forge to the
   Port changes which exterior its door returns to, not the room.
