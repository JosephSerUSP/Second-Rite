# St. Maria — side-view town screen graph

Status: **superseded historical design note.** Do not use its screen count,
topology, camera values, scale estimates or ownership list as current facts.
Current topology intent lives in
[`st-maria-layout.md`](../../projects/hichaukitoden-game/docs/world/st-maria-layout.md),
current mechanisms live in
[`st-maria-techniques.md`](../../projects/hichaukitoden-game/docs/world/st-maria-techniques.md),
and implementation state comes from `docs/ENGINE-STATE.md` and generated data.

> This document no longer owns the side-view screen grammar. It remains only as
> the design history that led to the present bounded-lane vocabulary.
> Who lives where, what a building is, the town's history and the intended
> layout are owned by
> [`projects/hichaukitoden-game/docs/world/st-maria.md`](../../projects/hichaukitoden-game/docs/world/st-maria.md).
>
> This file carries a transition table from a superseded generation of the
> town. Three separate layout analyses were written against it and all three
> reached false conclusions. It is retained as history, not regenerated or
> maintained.
>
> For the current generator boundary, read `SCREENS`,
> `AUTHORED_NOT_GENERATED` and `tools/towngen/check_town.py` directly.

St. Maria is fourteen screens. Each is an ordinary Map with a `traversal` block
naming the `bounded_lane` provider, so it is a Map like any other — the
provider owns horizontal position and doorway proximity, and nothing else.

## The shape of the town

St. Maria sits on two levels, joined at both ends, so it is a circuit rather
than a corridor. Nothing is more than two screens from a level change, and a
player can walk the whole town without retracing.

```
                  [ Churchyard 16 ]  -- the sealed Labyrinth door
                          ^ stair
   UPPER   [ Praça 17 ] ===== [ Backstreet 26 ]
              | west stair            | east steps
              v                       v
   LOWER   [ Quay 19 ] ===== [ Market Row 18 ]
```

`=====` is an edge exit: keep walking and the street continues, silently.
Everything else is a door — stand in front and press UP.

A passage between the two levels is authored just INSIDE its bound rather
than on it. On the bound it would be classified as the street continuing and
would announce nothing at all, and a stair to another level is something a
player chooses to take.

## Screens

| # | Screen | Lane | Doors | NPCs | Kind |
|---|--------|------|-------|------|------|
| 16 | The Churchyard | 0.0–26.012 | 1 | 2 | exterior |
| 17 | The Praca | 0.0–23.699 | 5 | 2 | exterior |
| 26 | The Backstreet | 0.0–22.254 | 4 | 0 | exterior |
| 19 | The Quay | 0.0–29.48 | 3 | 2 | exterior |
| 18 | Market Row | 0.0–29.48 | 6 | 4 | exterior |
| 20 | Weaponsmith | 0.35–7.4167 | 1 | 1 | interior |
| 21 | The Pub | 0.0–29.48 | 1 | 1 | interior |
| 22 | Chapel | 0.0–28.035 | 1 | 1 | interior |
| 23 | Laura's House | 0.0–17.919 | 1 | 1 | interior |
| 24 | Alicia's Room | 0.0–17.919 | 1 | 1 | interior |
| 25 | Passage House | 0.0–15.029 | 1 | 0 | interior |
| 27 | Alicia's Padaria | 0.35–7.4167 | 1 | 1 | interior |
| 28 | Alicia's Padaria (3D) | 0.35–7.4167 | 1 | 1 | interior |
| 29 | Laura's Smithy (3D) | 0.35–7.4167 | 1 | 1 | interior |

Generated from `data/maps/` — regenerate rather than edit. Note that maps 20,
27, 28 and 29 share an interior-room lane (0.35–7.4167): those are authored 3D
rooms, not flat plates, and they use the interior camera distance of 18.6667
rather than the plate distance of 21.1175.

Plate width is an authored design statement, not a constant: a screen earns its
length. A Classic window is 256px, so the longest streets are several screens of
walking and a room is under two.

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

| From | y | Kind | To | Arrival anchor |
|------|---|------|----|----------------|
| The Churchyard 16 | 1.012 | door | The Praca 17 | `churchyard_stair` |
| The Praca 17 | 0.434 | door | The Quay 19 | `praca_stair` |
| ↳ | 4.625 | door | Alicia's Room 24 | `exit_door` |
| ↳ | 9.827 | door | The Churchyard 16 | `down_praca` |
| ↳ | 20.81 | door | Chapel 22 | `exit_door` |
| ↳ | 23.7 | door | The Backstreet 26 | `west_praca` |
| The Backstreet 26 | -0.0 | edge exit | The Praca 17 | `east_backstreet` |
| ↳ | 2.601 | door | Laura's House 23 | `exit_door` |
| ↳ | 12.717 | door | Passage House 25 | `exit_door` |
| ↳ | 20.809 | door | Market Row 18 | `back_steps` |
| The Quay 19 | 15.896 | door | The Praca 17 | `quay_stair` |
| ↳ | 21.098 | door | The Pub 21 | `exit_door` |
| ↳ | 29.48 | edge exit | Market Row 18 | `west_quay` |
| Market Row 18 | 0.0 | edge exit | The Quay 19 | `east_market` |
| ↳ | 19.075 | door | Weaponsmith 20 | `exit_door` |
| ↳ | 28.035 | door | The Backstreet 26 | `market_steps` |
| ↳ | 22.0 | door | Alicia's Padaria 27 | `exit_door` |
| ↳ | 16.0 | door | Alicia's Padaria (3D) 28 | `exit_door` |
| ↳ | 26.5 | door | Laura's Smithy (3D) 29 | `exit_door` |
| Weaponsmith 20 | 4.2833 | door | Market Row 18 | `smith_door` |
| The Pub 21 | 2.601 | door | The Quay 19 | `pub_door` |
| Chapel 22 | 2.312 | door | The Praca 17 | `chapel_door` |
| Laura's House 23 | 2.024 | door | The Backstreet 26 | `laura_door` |
| Alicia's Room 24 | 2.024 | door | The Praca 17 | `alicia_door` |
| Passage House 25 | 2.312 | door | The Backstreet 26 | `lodging_door` |
| Alicia's Padaria 27 | 7.0333 | door | Market Row 18 | `padaria_door` |
| Alicia's Padaria (3D) 28 | 7.0333 | door | Market Row 18 | `padaria_3d_door` |
| Laura's Smithy (3D) 29 | 4.2833 | door | Market Row 18 | `smith_3d_door` |

Generated from `data/maps/` — regenerate rather than edit. The Churchyard's
Labyrinth Gate is absent above because its commands are copied verbatim from
map 1 and are not a bare `LOAD_MAP`.

**Arrival anchors** are the whole reason a screen with four doors works. A
transfer carries an anchor name; if the destination publishes that anchor, the
player lands on it. So the door you came out of is the door you go back
through, and no new authored object type exists — the door event *is* the
spawn point.

## Cast

| Screen | NPC | What it is |
|--------|-----|------------|
| Churchyard 16 | Guard | Choice + quest + common event; gates the Labyrinth |
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
| Padaria 27 | Alicia | Shop |
| Padaria (3D) 28 | Alicia | Shop |
| Smithy (3D) 29 | Smith | Shop |

The Backstreet 26 carries no NPCs. Alicia appears on three screens and
Laura on two, which is a symptom rather than a design: see W1 and W2 in the
town's document of record.

Every one of these was copied verbatim by event name from the original map 1,
so the town's *content* is the existing town's content; only its shape is new.

## Art direction

Rebuilt from reference frames on 2026-08-23. The previous prompt asked for
*flat side elevation, camera exactly perpendicular, no vanishing-point
perspective*, which is why the plates read as elevations rather than as
pre-rendered scenes. It now asks for a fixed lens turned a few degrees off
square, depth staged in three planes with a dark foreground occluder, ground
that changes level, and blown highlights against near-black shadow. Interiors
are looked *into* rather than cut away.

**The step before the filter matters more than the filter.** A 3072-wide
render reduced to a 144-tall plate throws away four fifths of its pixels, and
no dither or quantiser downstream can put back what the resampler averaged
away — a pre-rendered background of the era was rendered AT its final
resolution, every pixel placed. So: bands are generated FOUR to an image
rather than two or three, which keeps the reduction near 1.5x instead of 3.4x,
and an unsharp pass restores acutance immediately after the resize.

With detail actually present, the console stage can be gentle. The pipeline is
four stages, in the order they apply:

1. **Grade** (`ps1_filter.grade`) — an offline render arrives sitting in its
   midtones. Pulling the white point down makes highlights clip rather than
   roll off, which is what makes a window read as daylight.
2. **Unsharp** — restores what the downscale averaged away.
3. **MDEC** at quality 80 — a DCT codec with half-resolution chroma. Enough
   ringing around lintels to read as compressed, not enough to smear plaster.
4. **RGB555 with a full-strength ordered dither** — 32 levels per channel,
   dithered before truncation so smooth things crosshatch instead of banding.

Applied to the world strip only; the dock band below it is a hard black the
DCT would smear into the ground line.

## Known gaps

1. **The Churchyard's way down is a door, not a staircase.** Its art puts the
   steps into depth rather than across the lane, so the exit is a doorway near
   the west end with nothing painted under it.
2. **Door load is lopsided.** Market Row now carries six doorways and four
   NPCs; the Praça carries five doorways and is also the spawn screen. See
   finding P2 in the town's document of record.
3. **Only the Pub has a floor profile.** Every other plate changes level into
   depth rather than across the walking line. The Pub's ramp approximates step
   nosings that run in perspective.
4. **No foreground occlusion.** The art now composes a dark object close to the
   lens, but `foregrounds` is still a transparent PNG, so an actor walks in
   front of the handcart instead of behind it.
5. **A flat plate cannot be relit**, so there is no day/night or weather.
