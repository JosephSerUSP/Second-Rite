---
type: design
scope: game
status: active
---

# St. Maria — layout, derived

**Status: approved shape.** Derived from [`st-maria.md`](st-maria.md). This file
records intent rather than delivery; the live Project and
`tools/towngen/check_town.py` report whether a checkout matches it. The three
earlier layout proposals are superseded—they predate the island, the port, and
the retirement of P1.

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
| The **Passage House is one building**: the writ's registry and the Summoners' apartments under one roof. The player lodges in one of several apartments; Celina registers Summoners in the Registry on its public floor. | authored; supersedes the #1323/#1330 two-building split |
| The house is built into the slope between the **Praça** (high) and the **Cortiço** (mid). Its public front, the Registry, opens on the Praça; its apartments and arrival court face the Cortiço. | authored |

The last three are especially useful because together they specify repeated
walks rather than a collection of services. Laura's home and her work must be
far apart, her forge must be near the pub, and a new Summoner must leave the
Passage House and reach the civic centre before the Labyrinth opens to them.

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
              [ 26 Cortiço ]                       | the climb
                        |                          | (closes the ring)
              [ 18 Market Row ]                    |
                        |                          |
              [ 19 Quay ]                          |
                        |                          |
    water     [ 31 The Port ] -------------------- '
```

**The spiral is the descent, not the map.** A ring you can only walk round is a
folded line, and a folded line is what the town already suffers from. The ring
carries every screen's two street exits; **everything else is a stair or a
passage authored inside the bounds**, which is how the grammar allows a screen
to be connected to more than two places.

### The three chords

Each is a route somebody actually needs, not a link added for connectivity.

| Chord | What it is | Who uses it |
|---|---|---|
| **Praça ↔ Quay** | the public water stair — broad, lit, slow. *Already authored.* | everyone; the civic route to the water |
| **Cortiço ↔ Port** | a workers' stair. Steep, utilitarian, unlit. | the people who live in the cortiço and work the port, at dawn, who are not going to walk the market and the quay first |
| **Market Row ↔ Cortiço**, *through the padaria building* | the shop fronts the market on the lower street; the attached house backs onto the cortiço lane above. One building, two streets, two levels. | Alicia and Laura, and anyone who learns the back door exists |

The third is the one that earns the most. It makes the home-and-shop unity
**spatial** rather than merely asserted — the building is the connection — and
it gives the town a route *through* a building instead of past it. It is
discovered by shopping, not by hunting for an alley, which was the standing
objection to hiding a shortcut.

It is also ordinary architecture for the register St. Maria is written in: a
commercial frontage on the low street and a domestic door on the high lane is
what a building does on a slope.

### The resulting graph

```
                       [ Labyrinth ]
                             |
        .------------ [ 16 Churchyard ]
        |                    |
        |            [ 17 Praça ] ------------.
        |                    |                 |
   the climb        [ 26 Cortiço ] --.         | water
   (ring closes)             |        |        | stair
        |            [ 18 Market ] ---'        |
        |                    |     padaria     |
        |            [ 19 Quay ] --------------'
        |                    |
        '------------ [ 31 The Port ]
                             |
                    (workers' stair to 26)
```

**The climb is a chord too**, which is what lets the Churchyard's seaward bound
be a cliff rather than a street. So the streets run as an open chain of six and
four chords close and cross it:

| Screen | Street west | Street east | Chords |
|---|---|---|---|
| 16 Churchyard | *cliff* | 17 Praça | the climb → 31 Port |
| 17 Praça | 16 Churchyard | 26 Cortiço | water stair → 19 Quay |
| 26 Cortiço | 17 Praça | 18 Market | workers' stair → 31 Port; padaria back door |
| 18 Market Row | 26 Cortiço | 19 Quay | padaria shop front |
| 19 Quay | 18 Market Row | 31 Port | water stair → 17 Praça |
| 31 The Port | 19 Quay | *sea wall* | the climb → 16; workers' stair → 26 |

Connections per screen: Cortiço 4, Praça 3, Market 3, Quay 3, Port 3,
Churchyard 2 — the Churchyard staying thinnest is correct, because it is the
ceremonial top and the thing you climb *to*.

You can still spiral linearly from the water to the gate. You will not often
want to.

---

## 3. Screen by screen

| # | Screen | Altitude | Outlook | Holds |
|---|--------|----------|---------|-------|
| 16 | **The Churchyard** | highest | horizon over every roof in town | The sealed Labyrinth gate. The Guard. The graveyard. |
| 17 | **The Praça** | high | sea between buildings | The Passage House's public front (the Registry). Chapel (Agnes). The fountain. |
| 26 | **The Cortiço** | mid | glimpses, over laundry | Many households. The Passage House's lower face: arrival court and apartments. |
| 18 | **Market Row** | mid-low | roofs below, water beyond | The padaria and its attached house. Stalls. |
| 19 | **The Quay** | low | the water itself | The Rusty Tankard. |
| 31 | **The Port** | lowest | open sea, hulls, sky | Laura's forge. Shipping. The beaten ship. |

### The Cortiço replaces the Backstreet

This closes the former open question. The Backstreet is already the
town's non-frontage face: laundry, back doors, a lit shrine. That is most of the
way to a cortiço courtyard, and making it one costs **zero new screens**. It
becomes the address for everyone in §5.6's register who holds no frontage, and
for the Passage House, which belongs beside them precisely because it is the one
building that is nobody's home.

### The Passage House: one building, two faces

The Registry and the apartments are the same building. An office that issues the
Crossing Writ and a house that lodges the people holding it are one institution,
and the slope gives that institution two faces: a public front on the Praça and
a lower, domestic face on the Cortiço. The two faces must read as one building
(masonry, joinery, colour, signage), because each is seen from a different
screen.

Inside, the public floor (the Registry) and the apartment floors are joined by a
stair and a corridor of apartment doors, of which Room 3 is one. That interior
link is **staff-only for the player's first visit**: Celina's side of the stair
is not offered. The player still leaves the apartment, crosses the court,
climbs through the Cortiço and enters from the Praça. The opening's first piece
of town learning is therefore kept, and it is now the walk *around* their own
house rather than between two unrelated buildings. Celina gives the Crossing Writ
in the Registry and can describe the town in altitude terms the player can
immediately act on: Churchyard/gate uphill, Market Row downhill, Port below.

This distinction is functional, not environment-count expansion. **Room 3 is
where expedition history becomes personal; the Registry is where the town
recognises the Summoner institutionally.** They are different floors, not
different buildings.

### The Port

The new screen, and the one the town has never had. Working shipping, moored
boats, and at least one ship past its best — an island a war left stranded shows
it in its hulls. Laura's abandoned forge is here: iron and charcoal are landed
at the port, so a forge by the water is where a forge would be, and it is
adjacent to the pub on the Quay exactly as canon requires.

---

## 4. The walks this produces

**Laura goes home** from the Port, through the Quay past the Tankard where the
barkeep is, through Market Row, to the padaria — three screens, uphill, at the
end of the day. She is the only person in St. Maria who commutes, and now the
map says so.

**The player's first civic loop** begins in Passage House Room 3. The player
leaves along the gallery, walks down the stair and out the great door, goes
out to the Cortiço, reaches the Praça, and registers at the Registry (§5.1). Only then are preparation and descent meaningful choices:
Churchyard and the Gate are uphill; Market Row/Padaria and the Port/forge are
below. The first trip therefore teaches a useful mental map instead of asking the
player to wander until the correct NPC happens to appear.

**The return loop** should be faster because the player now knows the chords.
Coming home is not dead travel: familiar spaces are where changed NPC dialogue,
rest, shopping and expedition consequences become legible.

---

## 5. Building consolidation

Independent of the shape above, and true under any layout:

| Earlier state | Current spatial role |
|---|---|
| 24 Alicia's Room (off Praça) | a room of **the padaria building**, off Market Row |
| 23 Laura's House (off Backstreet) | retired as a separate house; Laura sleeps in the padaria's attached home |
| 27 Padaria (off Market) | the shop half of the same building |
| 20 Weaponsmith | Laura's forge, re-sited to the Port |
| 25 Passage House | **Room 3**, one apartment of the Passage House, reached from the gallery of the stair hall, whose great door opens on the Cortiço |
| 33 Passage Office | the **Registry** floor of the same Passage House, entered from the Praça |
| Registrar previously copied into Room 3 | removed; registration belongs only to the Registry floor (map 33) |

This is W1, W2 and W4 resolved together. The Registry and the apartments stay
separate *rooms* (so the first town traversal still has a reason to exist) but
are one *building*.

### 5.1 The Passage House interior

The interior is a new layout, not a redress of earlier lodging and corridor
tests, and it is a **building**, not a row of doors: two storeys, two ways in,
and a section that follows the slope. The **upper floor is level with the
Praça**; the **ground floor is level with the Cortiço court**, one storey lower.

**The player walks all of it in one screen, and the path forks.** The ground floor
and the gallery are two lanes (levels) that overlap in Y. At the stair foot the
player presses **Up** to climb to the gallery, or simply keeps walking **left** along
the ground floor, under the gallery, to the street door. At the stair top **Down**
brings them back. No stair is a transfer; the camera follows the climb. The ground
floor under the gallery also has its own life: the building's service doors
(porter's lodge, wash-house), shut, and at the left end a **street door**, the house's
second way out.

```
 PRAÇA side (high)                                       CORTIÇO side (mid)

 Praça (z 14.07) ──> [33 Registry] ── back-door stair down ──┐
                       (cellar, z 11.3)                         │ the PASSAGE: level, under the
                                                                │ Praça terrace, ~10 m
 gallery level (z 11.3)    gallery: Room 2 · ROOM 3 · Room 4 ───┘ (iron gate, locked until the Crossing Writ)
 (one storey above the street)  ^ stair (walked, one storey)                   <──┐
 ground floor    service rooms (shut)   post wall · stair foot · great door ─> street [1001 Cortiço]
 (Cortiço street, z 8.1)                                                    street door ─> same street, 3 m along

                  [34 Stair hall] is the whole of this, one screen, one continuous walk
                  [25 Room 3]  is entered from its gallery door
```

| # | Screen | Floor | Role | Axis spent (interior brief §4b) |
|---|--------|-------|------|------|
| 33 | **Registry** | Praça level | Public floor. Celina, the ledger, the Crossing Writ. Front door to the Praça. | already authored; unchanged |
| 34 | **Stair hall** (new) | both | One double-height room with two walkable lanes. Ground: the great door to the court, a post wall of lodgers' letters (some never collected), a bench, a water stand, the shut service doors, and a street door at the far end. A masonry stair stands behind the lane, linking ground to gallery. Gallery: a terracotta deck on a stone arcade, three apartment doors (Room 3's the only one lit, with traces of the others' tenants: boots, a coat, a strapped trunk, straw), and at the far end a **wrought-iron gate with the Registry visible through it**. | **Floor level, taken to a storey** — the stair, the deck and the balustrade carry the second level |
| 25 | **Room 3** | upper | One apartment, off the gallery: two beds, washstand, window that does not close, straw and a feed bowl for Saban, the missing picture, the low coat hook. | **Alcove** — an *alcova*, the sleeping recess of a rented room, with a header across its mouth |

Connections:

- **The exits.** The stair hall has two ground-floor doors, both onto the Cortiço
  street: the great door (the Passage House doorstep) and the street door at the
  far end, which lets out about 3 m along the street from it. The old Arrival Court
  (map 32) is retired. The house's Praça way in is the
  Registry's front door. The two halves are one building because of the
  **Passage**: a level corridor under the Praça terrace that joins the end of the
  gallery to the Registry's cellar, whose stair comes up at the Registry's back
  door. The numbers close: the gallery floor is 3.2 m above the Cortiço street
  (z 11.3); the Praça terrace is 6 m above it (z 14.07) and the Registry's floor is
  on the terrace; one storey under the Registry floor is also z 11.3. So the
  passage never climbs or crosses the Praça lane; it runs beneath the retaining
  wall and the strip, and nothing about it needs a plate to show it.
- **Room 3 door → along the gallery → down the stair → great door →
  Cortiço → Praça → Registry front door.** This is the opening's first civic loop,
  now starting inside one building.
- **The gate** (far end of the gallery) opens onto the Passage and is locked on the
  first visit; it opens after the player holds a Crossing Writ, so the first walk
  to the Praça is still the long way, over the street. After that the return loop is faster: Praça → Registry → gate →
  gallery → Room 3.
- **The other apartment doors** are closed, with traces of tenants who are out in
  the Labyrinth. They are set dressing, not screens.
- **Light tells the route.** The court door is the brightest thing on the ground
  floor and the camera is yawed so it recedes; a tall window lights the stair;
  Room 3's lamp is the one warm door.

The only new screen is 34; the Passage itself is not a screen, it is the
transfer between the gallery gate and the Registry's back door. The Registry
keeps its adopted room; the door on its back wall is an edit to that adopted
source, never a regeneration. Why not relocate a building instead: the Praça
lane runs between the two blocks, so any single mass would have to cross it
(an arch would hide the player behind a wall; a bridge sits above what either
plate frames), and moving the Registry or the apartments gives up the opening's
first walk or the Praça's civic role. Room 3's contents come
from its authored text (missing picture, chipped feed bowl, low coat hook, straw):
they are what make it that room and not another rented room.

---

## 6. Cost

| Item | Cost |
|---|---|
| New exterior plates | **1** — the Port |
| Re-sited screens | 0. The five existing exteriors keep their plates |
| Re-wired doors | ~16, all through `SCREENS` in `build_town.py` |
| Placeholder plate | the Port reuses `quay_bg.png` until it has art |
| Retired maps | 0 — 23 and 24 are reused as rooms rather than deleted |
| Blocked on Thestra | nothing. This is spatial coherence; dressing comes later |

The town is walkable with the existing plates the moment the wiring lands. They
will look wrong — they already do — but the *place* will be correct, and the art
pass has something true to dress.

---

## 7. Open

1. ~~Does the spiral hold?~~ **Approved**, on the condition that it is a shape
   rather than a folded line — hence the four chords above.
2. **Celina's bed** — still open from `st-maria.md` §6. Her workplace is the
   Passage House Registry; with the Registry and the apartments one building,
   an apartment there is now the cheapest answer, but it is her call as a
   character (it makes her absorbed by the trade).
3. **Map 20's authored 3D room** is a smith interior. Re-siting the forge to the
   Port changes which exterior its door returns to, not the room.
