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
| The **Passage House** is the player's lodging on the Cortiço; its arrival court and Room 3 are domestic/personal space. | authored |
| The **Passage Office / Registry** is the civic office on the Praça. Celina registers Summoners there, not in Room 3. | authored; #1323/#1330 |

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
| 17 | **The Praça** | high | sea between buildings | Passage Office / Registry. Chapel (Agnes). The fountain. |
| 26 | **The Cortiço** | mid | glimpses, over laundry | Many households. Passage House and its arrival court. |
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

### The Praça Registry

The Passage Office is a civic frontage on the Praça. It is intentionally not the
player's lodging: leaving Room 3, crossing the Passage House court and reaching
the Registry is the opening's first useful piece of town learning. Celina gives
the Crossing Writ there and can describe the town in altitude terms the player
can immediately act on: Churchyard/gate uphill, Market Row downhill, Port below,
Cortiço and the Passage House behind them.

This distinction is functional, not environment-count expansion. **Room 3 is
where expedition history becomes personal; the Registry is where the town
recognises the Summoner institutionally.**

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
leaves through the Arrival Court to the Cortiço, reaches the Praça, and registers
at the Passage Office. Only then are preparation and descent meaningful choices:
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
| 25 Passage House | **Room 3**, personal lodging reached through the Passage House Arrival Court on the Cortiço |
| Registrar previously copied into Room 3 | removed; registration belongs only to map 33 **Passage Office / Registry** on the Praça |

This is W1, W2 and W4 resolved together, while #1323/#1330 separate domestic
Passage House space from the civic Registry so the first town traversal has a
reason to exist.

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
2. **Celina's bed** — still open from `st-maria.md` §6. Her workplace is now
   unambiguously the Praça Registry; her private address remains a separate
   worldbuilding question.
3. **Map 20's authored 3D room** is a smith interior. Re-siting the forge to the
   Port changes which exterior its door returns to, not the room.
