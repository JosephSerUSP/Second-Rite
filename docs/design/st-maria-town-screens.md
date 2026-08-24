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

## The re-shape, as built

The town was one continuous line with the Labyrinth gate at the west end of
it, which made the most important thing in St. Maria read as the least.

```
              [ Churchyard 16 · Labyrinth ]
                       ↑ stair
  [ Praça 17 ] === [ Market Row 18 ] === [ Quay 19 ]
        ↓ alley            ↑ steps
  [ Backstreet 26 ] ───────────┘
```

Map 16 is the Churchyard: a terrace above the rooftops holding the sealed
door, reached by climbing the stair in the middle of the square. An alley off
the Praça opens into the Backstreet (map 26), which drops by steps into Market
Row, so the town loops. The rented room the game opens in now has a door off
the Backstreet, which is the only reason a player can ever return to it.

Both new connections are ordinary doors. UP was already the door verb, so
branching cost nothing beyond art.

## Art direction

Rebuilt from reference frames on 2026-08-23. The previous prompt asked for
*flat side elevation, camera exactly perpendicular, no vanishing-point
perspective*, which is why the plates read as elevations rather than as
pre-rendered scenes. It now asks for a fixed lens turned a few degrees off
square, depth staged in three planes with a dark foreground occluder, ground
that changes level, and blown highlights against near-black shadow. Interiors
are looked *into* rather than cut away.

The picture pipeline is three stages, in the order a console applied them:

1. **Grade** (`ps1_filter.grade`) — an offline render arrives sitting in its
   midtones. Pulling the white point down makes highlights clip rather than
   roll off, which is what makes a window read as daylight.
2. **MDEC** — a DCT codec with half-resolution chroma. The ringing around
   lintels and the blockiness in flat plaster.
3. **RGB555 with an ordered dither** — 32 levels per channel, dithered before
   truncation so smooth things crosshatch instead of banding.

Applied to the world strip only; the dock band below it is a hard black the
DCT would smear into the ground line.

## Known gaps

1. **The Churchyard's way down is a door, not a staircase.** Its art puts the
   steps into depth rather than across the lane, so the exit is a doorway near
   the west end with nothing painted under it.
2. **The Praça is 1000px with six doorways on it** — about four Classic
   screens of walking. It should be the widest place in town, but there may be
   too much square between destinations.
3. **Only the Pub has a floor profile.** Every other plate changes level into
   depth rather than across the walking line. The Pub's ramp approximates step
   nosings that run in perspective.
4. **No foreground occlusion.** The art now composes a dark object close to the
   lens, but `foregrounds` is still a transparent PNG, so an actor walks in
   front of the handcart instead of behind it.
5. **A flat plate cannot be relit**, so there is no day/night or weather.
