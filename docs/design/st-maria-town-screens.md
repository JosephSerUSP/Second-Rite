# St. Maria — side-view town screen graph

Status: experimental (`exp/838-town-2d-flat`, issue #838). This describes the
town as it is actually authored, not as it is intended to end up.

St. Maria is ten screens. Each is an ordinary Map with a `traversal` block
naming the `bounded_lane` provider, so it is a Map like any other — the
provider owns horizontal position and doorway proximity, and nothing else.

## The shape of the town

Four exteriors run west to east in a single line, from the sealed mouth of the
Labyrinth down to the water. Six interiors hang off them. There is no branching
and no map you can reach two ways, which is deliberate: the town should be
learnable in one walk.

```
  Labyrinth (map 2)
        |
     [ Gate 16 ] === [ Praca 17 ] === [ Market 18 ] === [ Quay 19 ]
                       |    |   |          |               |
                    Laura Chapel Alicia  Smith            Pub
                     23     22     24      20              21

  Passage House 25 — opening cinematic only, exits to the Praca
```

`===` is an edge exit: keep walking and the street continues. Everything below
the line is a door: stand in front of it and press UP.

## Screens

| # | Screen | Plate | Lane | Purpose |
|---|--------|-------|------|---------|
| 16 | Gate of Thestra | 600px | 0–15.03 | Threshold. Holds the sealed Labyrinth door and the Guard who gates it. |
| 17 | The Praça | 880px | 0–23.12 | The heart. Widest screen, four doors, the fountain, most of the town's life. |
| 18 | Market Row | 760px | 0–19.65 | Commerce and the largest cast — four NPCs and the weaponsmith. |
| 19 | The Quay | 470px | 0–11.27 | Where the town runs out. Short on purpose; dead end to the east. |
| 20 | Weaponsmith | 426px | 0–10 | Shop. Off Market Row. |
| 21 | The Pub | 426px | 0–10 | Shop and rumours. Off the Quay. |
| 22 | Chapel | 426px | 0–10 | Agnes. Off the Praça. |
| 23 | Laura's House | 426px | 0–10 | Laura — shop, quest and a common event. Off the Praça. |
| 24 | Alicia's Room | 426px | 0–10 | Alicia — shop and a common event. Off the Praça. |
| 25 | Passage House | 426px | 0–10 | Lodging. Reached only by the opening cinematic. |

Plate width is an authored design statement, not a constant: the Praça is the
widest place in the town because it is the most important, and the Quay is
short because the town ends there. A Classic window is 256px, so the Praça is
about three and a half screens of walking and a room is under two.

Exteriors carry roughly 38px per lane unit; interiors about 43. Both are
authored by `tools/towngen/build_town.py` from the real plate width, so a
screen cannot claim a lane its picture cannot show.

## Doors and edges

Both are doorways to the provider, and they differ by exactly one thing: an
**edge exit is authored on a lane bound**, a **door is not**. That is what the
HUD reads to decide whether to announce something, because continuing along a
street is not an interaction.

The test is exact rather than tolerant, and Market Row is why: the
weaponsmith's door stands 0.86 from the east end with a 0.9 radius, so any
tolerant test would call a shop door an exit.

| From | y | To | Arrival anchor |
|------|---|----|----------------|
| Gate 16 east | 15.03 | Praça 17 | `west_gate` |
| Gate 16 | 7.37 | Labyrinth (map 2) | — |
| Praça 17 west | 0.00 | Gate 16 | `east_praca` |
| Praça 17 | 2.89 | Laura's House 23 | `exit_door` |
| Praça 17 | 13.01 | Chapel 22 | `exit_door` |
| Praça 17 | 21.68 | Alicia's Room 24 | `exit_door` |
| Praça 17 east | 23.12 | Market Row 18 | `west_praca` |
| Market 18 west | 0.00 | Praça 17 | `east_market` |
| Market 18 | 18.79 | Weaponsmith 20 | `exit_door` |
| Market 18 east | 19.65 | Quay 19 | `west_market` |
| Quay 19 west | 0.00 | Market Row 18 | `east_quay` |
| Quay 19 | 6.50 | Pub 21 | `exit_door` |
| Every interior | ~0.5–1.7 | back the way it came | the door used |

**Arrival anchors** are the whole reason a screen with four doors works. A
transfer carries an anchor name; if the destination publishes that anchor, the
player lands on it. So the door you came out of is the door you go back
through, and no new authored object type exists — the door event *is* the
spawn point.

## Cast

| Screen | NPC | What it is |
|--------|-----|------------|
| Gate 16 | Guard | Choice + quest + common event; gates the Labyrinth |
| Praça 17 | Registrar | Choice, gives an item |
| Praça 17 | Child | Flavour text |
| Market 18 | Auctioneer | Shop |
| Market 18 | Yukio | Common event |
| Market 18 | Euler | Flavour text |
| Market 18 | Scholar | Quest |
| Quay 19 | Sign | `ENTER_LOCATION` + text |
| Quay 19 | Fisherman | Flavour text |
| Weaponsmith 20 | Smith | Shop + quest |
| Pub 21 | Owner | Shop |
| Chapel 22 | Agnes | Flavour text |
| Laura's House 23 | Laura | Shop, quest, common event |
| Alicia's Room 24 | Alicia | Shop, common event |

Every one of these was copied verbatim by event name from the original map 1,
so the town's *content* is the existing town's content; only its shape is new.

## Planned re-shape: the raised churchyard

Chosen 2026-08-23. The town as built is one continuous line, and the Labyrinth
gate sits at the west end of it, which makes the most important thing in St.
Maria read as the least. The re-shape fixes both.

```
              [ Churchyard · Labyrinth ]
                       ↑ steps
  [ Quay ] === [ Praça ] === [ Market Row ]
                       ↑ alley        ↓ steps
                  [ Backstreet ] ————————┘
```

Three changes:

1. **The gate becomes a place.** The Praça keeps its role as the social hub,
   but a broad stone stair rises from its centre to a separate Churchyard
   screen holding the sealed door, above the town. You climb to reach the thing
   the town is afraid of.
2. **The town loops.** An alley off the Praça leads up into a Backstreet — the
   poorer side, laundry and back doors — which drops by steps into Market Row.
   A loop is what stops a town reading as a corridor.
3. **Map 16 is retired.** The Gate screen's job moves to the Churchyard.

Both new connections are ordinary doors: an alley is a door, and the engine
already treats UP as the door verb, so branching costs nothing beyond art.

Height variance is the point of the two step transitions. Now that a lane
carries an authored floor profile, the stair out of the Praça and the drop into
Market Row are floor shape rather than screen transitions — you walk them.

**Blocked on art direction.** The generation group is authored as `layout_b` in
`tools/towngen/generate_plates.py` but excluded from a default run, because the
current plates read as flat elevations rather than pre-rendered scenes.
Perspective, depth and composition are being revised against references before
the group is generated.

## Known gaps

These are recorded rather than fixed, because each is a design decision rather
than a defect to clear.

1. **Passage House 25 has no inbound door.** Only the opening cinematic loads
   it, and its exit lands on the Praça's `west_gate` anchor — the gate door,
   not a lodging door. Once you leave, you cannot return.
2. **Doorway anchors have drifted from the painted art.** The anchors were
   derived from pixel positions when `build_town.py` first ran; the plates were
   re-spliced afterwards with per-screen crop anchors. Turn on
   *Developer → TOWN BOUNDS* to see the reach bands against the doors.
3. **No foreground occlusion.** The `foregrounds` layer is a transparent PNG on
   every screen, so an actor never passes behind anything.
4. **A flat plate cannot be relit**, so there is no day/night or weather.
5. **Maps 20–24 all share the lane 0–10** and a 426px plate. Interiors are
   currently uniform in a way exteriors deliberately are not.
