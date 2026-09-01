---
type: design
scope: game
status: active
---

# St. Maria — reusable authoring techniques

This is the town's imagery-free mechanism record. It may be read before fresh
visual authoring because it contains transforms, equations, invariants and tool
boundaries—not layouts to imitate. Earlier renders, contact sheets, `.blend`
compositions, exported packages and town-specific visual builders remain
sterile inputs under `docs/design/town-authoring-known-good.md`.

This document records conclusions, not implementation status. Runtime facts
come from `docs/ENGINE-STATE.md` and the live Project; the named tools below are
the executable authorities for their own calculations.

## Projection contract

The player is the unit of measure. `walker.png` is a 144×48 sheet containing
six 24×48 cells. A 1.75-world-unit actor must project to 48 native pixels at the
action plane, and the feet anchor is native Y=128. Therefore:

```text
pixels per world unit = 48 / 1.75 = 27.4285714286
camera distance       = 18.6666666667
eye height            = 2.2604166667
horizontal FOV        = 28.0724869359 degrees
canonical horizon Y   = 66
character floor limit = 144
```

The base composition is 256×144 inside a 256×240 Classic frame. Wide output is
426×240, but widening the output must not change the base lens or actor scale.
`tools/blender/make_town_camera.py` derives the fixture rather than asking an
author to copy these values. The serialized authority is
`tools/blender/fixtures/town_sideview_camera.json`; runtime-to-Blender parity is
owned by `tools/blender/thestra_camera.py` and
`tools/blender/check_thestra_camera.py`.

Y=144 limits character placement only. It is not a crop. Ground, foreground,
architecture and background continue through the full 426×240 frame and past
the tracking envelope. Anything hidden under the dock must be visually
superfluous, not load-bearing composition.

## Pitch and the actor

Pitch is the operation that makes world verticals converge. A principal-point
shift changes framing, not perspective, and cannot create that effect by
itself. Pitch also does not license actor keystoning: the actor is a screen-
aligned sprite blitted at the projected ground point, not a world-vertical box.

For a pitched view, keep three invariants distinct:

1. the ground point lands at Y=128;
2. the screen-aligned actor remains 48 px tall;
3. the horizon remains at Y=66.

`tools/towngen/camera_modes.py::solve_billboard()` is the conceptual authority.
At 17.5°, shifting the principal point alone makes a world-vertical 1.75-unit
probe about 50.40 px tall; that residual describes the probe, not the sprite.
The retired `tools/blender/study_town_pitch.py` measured such a box and therefore
answered the wrong question. Its useful conclusion—principal-point
compensation pins an anchor—remains, while its actor-height residual does not.

The authored Praça source uses a compensated 17.5° downward view. Production
map camera pitch stays at 0° while a screen still uses an unpitched plate: a
pitched camera against an unpitched picture moves the actor relative to a world
that did not move. Pitch flips per screen only when its plate was photographed
from the matching solved camera.

## Projection-window tracking and wide plates

Horizontal tracking moves the projection window. It never translates or yaws
the camera. Representative checks are -96, 0 and +96 native pixels; eye,
orientation, pitch and lens remain invariant across them.

A wide plate is photographed as adjacent off-axis windows from one eye and one
lens. Widening the lens to fit the whole lane changes perspective away from the
centre. Rotating the camera creates seams. `tools/towngen/photograph_blend.py`
renders projection-window tiles and joins them without resampling, cropping any
rounded-up excess symmetrically.

## Lane and plate scale

Plate pixels are authoring coordinates; runtime lane units are gameplay
coordinates. Each screen owns its conversion beside its plate:

```text
lane y = (plate x - west margin) / pixelsPerRuntimeY
lane span = (plate width - west margin - east margin) / pixelsPerRuntimeY
```

The current margins are 40 px. Historical flat plates use 34.6 px per lane
unit. Modelled work uses the camera contract's 27.4285714286 px per unit. A
23.699-unit Praça photographed at the modelled scale is approximately 730 px
wide rather than 900 px. Those two widths can describe the same lane length;
they do not describe the same actor-to-building scale.

`tools/towngen/build_town.py` carries `pixels_per_y` per screen and emits the
same value as `preRendered.playerProjection.pixelsPerRuntimeY`.
`tools/towngen/make_blockout.py` and `check_plate.py` consume that screen value.
A plate replacement changes every pixel-authored door, NPC and ground-profile
point, so the generator—not a hand edit to map JSON—owns their conversion.

The spiral's Praça world anchors are stable targets independent of plate pixel
density:

| Anchor | Lane Y |
|---|---:|
| `west_churchyard` | 0.000 |
| `quay_stair` | 3.179 |
| `chapel_door` | 16.763 |
| `east_cortico` | 23.699 |

`alicia_door` and `npc_registrar` do not belong to the current Praça.

## House grammar and source authority

The reusable grammar lives under `tools/blender/recipes/house_grammar/`. It
expresses swept bodies, courses, piers, L/T outlines, roofs, side-elevation
openings, canopies, steps and balconies as testable records before Blender
emits them. A town source should compose those operations; it should not grow a
new pile of façade boxes or a raw vertex table.

An adopted `.blend` remains source authority for hand edits. Regeneration is
only valid when the owner explicitly reopens that decision. Issue #1016 does so
for the Praça massing: the replacement must use the grammar and the world-space
anchors above, while the previous composition remains unsuitable as fresh-art
input. Other adopted sources retain the normal no-overwrite rule.

## View transform and plate provenance

New plates bake under AgX. Standard clips scene-linear highlights above 1.0;
AgX preserves them through a display roll-off. A live-rendered element meeting
an AgX plate must use a compatible transform at that seam.

The shipped plate provenance is mixed:

| Plate family | Recorded source transform |
|---|---|
| `spike_massing.py` exterior/interior plates | Standard—the generator sets it explicitly |
| Authored Padaria and smith PNGs | Not recorded in the exported package; current source blends are AgX, but that does not prove the historical PNG bake |
| New authored/modelled plates | AgX required; record it in the export provenance |

“Not recorded” is deliberate. Inferring a historical PNG's transform from its
current source file would turn an unknown into a false fact.

## Tool boundary

| Need | Authority |
|---|---|
| Derive a level camera fixture | `tools/blender/make_town_camera.py` |
| Runtime ↔ Blender projection parity | `tools/blender/thestra_camera.py`, `check_thestra_camera.py` |
| Compare pitch solution families | `tools/towngen/camera_modes.py` |
| Photograph and stitch an adopted source | `tools/towngen/photograph_blend.py` |
| Convert plate pixels to lane data | `tools/towngen/build_town.py` |
| Emit interaction overlays/specs | `tools/towngen/make_blockout.py` |
| Check plate dimensions/openings | `tools/towngen/check_plate.py` |
| Regenerate-and-diff owned town data | `tools/towngen/check_town.py` |
| Compose reusable building geometry | `tools/blender/recipes/house_grammar/` |

Mechanisms above are always-readable. Their generated images, previous visual
choices and authored compositions are not.
