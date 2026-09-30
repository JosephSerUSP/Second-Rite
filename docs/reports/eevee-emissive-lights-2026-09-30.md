# Lighting from emissive surfaces in EEVEE, and the lantern that would not glow (2026-09-30)

Follows `eevee-environments-2026-09-30.md`, which listed "emissive glow missing" as the open effect. The
owner's question: does EEVEE not accept emission, and can we work around it? Blender 5.2.2. The rooms are
test subjects, not final: the point is the tooling, so nothing here tunes a room and no shipped file changes.

## What EEVEE does with emission

It draws it, and it does not cast it. On a sealed white room with one glowing panel and a black world:

| setup | the panel | light on the floor beside it |
|---|---|---|
| Cycles | 13.2 | 0.130 |
| EEVEE, AO raytracing | 13.2 | 0.0 |
| EEVEE + light probe volume, `capture_emission` on | 13.2 | 0.030 (23% of Cycles) |
| EEVEE + probe volume + an area light on the panel | 13.2 | 0.101 (78%) |

A larger panel gives 0.212 against 0.812 (26%) for the probe alone, and 0.690 (85%) with the light.

**Correction to my first measurement.** I first reported the probe volume returned a thousandth of Cycles'
light. That test had the probe volume sitting exactly on zero-thickness walls, so it had nothing to bounce
off. With the volume enclosing the walls, as it does in every real room (they have thickness), emission is
captured, at about a quarter. The conclusion stands (a real light is the better route), the number I gave
did not.

## Companion lights: `tools/blender/emissive_lights.py`

At render time, each emissive patch that faces into the room gets a rectangular area light on it:
`watts = pi x emission strength x emitting area`, colour from the material, a 1 cm offset along the normal.
The pi is the Lambertian flux, and it was measured, not assumed: against Cycles with bounces off, the
light matches direct lighting to 3-12% on 0.6 m and 1.6 m emitters. Two things the measurement caught:

- **Every companion needs an explicit cut-off distance.** EEVEE's `light_threshold` gives a dim, small
  light a short reach; a 23 W companion lit the far floor at a third of its real level until it had one.
- **The probe must stop capturing emission when companions exist**, or the glow is counted twice
  (`add_probe_volume(capture_emission=False)`).

It reads the material's current strength, so `--window-emission-scale` flows into the light. It is
`--emissive-lights` on `stage_room_model.py`, `study_eevee_atlas.py` and `study_eevee_pilot.py`, with
`--emissive-exclude MATERIAL`. It never writes the source `.blend`.

**How much does it matter in these rooms? Little.** The emissive materials are at strength 1.2, so the
windows, embers and glowing reveal come to 1-23 W each against authored lights of 25-100 W. Lit-region
difference from Cycles (plate, mean of 255), probe plate without and with the companions:

| room | no shims | companions only |
|---|---|---|
| Smith | 9.60 | 10.79 |
| Room 3 | 10.19 | 9.99 |
| Corridor | 12.19 | 11.92 |
| Padaria | 10.86 | 9.97 |

The companions add a real but small local glow (the forge's orange on its wall, a window's spill), and in
the smith the numbers get slightly worse, which I did not chase. This also matches the project's own rule
(`st-maria-interior-authoring.md`: "`embers` is emissive and casts nothing. A hearth still needs a
`room.light` beside it"). Cycles lighting a room from emission is an accident that EEVEE does not repeat, and
the authored lights are the intended light. So the companions are available, and I would not call them
necessary. Sheets: `smith_companions_sheet.png`, `padaria_companions_sheet.png`.

## The lantern was never about emission: `tools/blender/light_fixtures.py`

The corridor's wall lanterns have a 12 W point light, 0.14 m in radius, inside an opaque 0.09 m flame box
inside a 0.16 m cage. Cycles lights the wall around them; EEVEE left them as dark silhouettes. The lantern
flame is 0.063 m² at strength 1.2, under a watt, so emission could never have been the glow. Hiding parts of
the lantern, on the wall beside it (mean of 255):

| Cycles | EEVEE as it was | cage hidden | flame hidden | both hidden | light's shadow off |
|---|---|---|---|---|---|
| 28.4 | 17.1 | 19.4 | 17.1 | 34.1 | 34.1 |

(`corridor_lantern_variants.png`.) EEVEE treats the light as a point and the housing as a closed box
around it, so the whole lantern is shadowed. Cycles samples the light's 0.14 m sphere, which is larger than
the housing, so most of it is outside and the glow escapes.

The fix releases shadow casting (Ray Visibility > Shadow) on any small mesh whose housing is **smaller than its
light**: half its longest side under the light's radius. That is the rule Cycles itself follows: the shops'
lanterns are 0.27 x 0.16 x 0.32 m around the same light, Cycles shades those too (its plates show a dim
lantern, no halo), and my first version released them and made EEVEE blaze where Cycles does not. So the
rule leaves them alone. Released, on the real rooms: the corridor's two lanterns (cage and flame each); none
in the smith, room 3 or the Padaria.

Corridor, after: exposure solves to +0.00 EV where it needed +0.52 (the lanterns were most of what the
room was missing), plate difference from Cycles 12.19 -> 10.05, and Cycles against EEVEE in the 3D room
view 11.33 -> 10.79. The lantern halos are visibly there and somewhat hotter than Cycles' soft ones
(`corridor_plates_sheet.png`, `corridor_rooms_sheet.png`). `--fixture-lights` on the same three tools.

**The atlas.** The exporter welds the lantern housing into the one room mesh, so its shadow cannot be
released for that part alone. The study keeps the source meshes in the scene as the shadow casters, unseen
by the camera, with the housings released, and the joined mesh casts none. Measured: no shadow acne from
the coincident surfaces, the halo bakes into the atlas, and atlas against its own EEVEE target is 1.44
(was 1.47), so the projection bake takes it. The other rooms: smith 2.13, room 3 2.52, Padaria 3.10, each
within 0.1 of before. The Cycles reference is rendered in the unmodified scene (without that it is twice as
bright, an artefact I had to fix in the study).

## What this changes about the earlier report

`eevee-environments-2026-09-30.md` blamed the corridor's missing lantern glow on EEVEE not casting
emission. It was the housing's shadow, and the door reveal's emission (8.9 W) and the windows' are the
real emitters. That report now points here.

## Tests

- `test_emissive_lights.py` (12 checks): one light per room-facing patch and none for a face looking into
  the wall; watts = pi x strength x area and follows a strength change; colour, direction, offset,
  rectangle size, a rotation and not a mirror, a reach on every light; a tiny emitter reported as skipped;
  an excluded material and an ignored object get none. Negative control: with the room-facing filter
  disabled, four of them fail.
- `test_light_fixtures.py` (4 checks), one of them a real EEVEE render: the wall beside a lantern is
  0.067 before and 0.216 after; a housing bigger than its light keeps its shadow; the wall, the table and
  the far box are untouched.
- Both run in `blender-item-source.yml`, headless.

## Not done, on purpose

- No room was tuned: hot lantern halos, the forge's reach in the smith and the room 3 blotch are left.
- Neither shim is on by default. Making them the default for `--engine eevee`, and putting the EEVEE
  projection bake behind `--bake-backend eevee` in the exporter, are the next steps if the owner wants them.
- The companion power law was calibrated on rectangular emitters. A curved or very elongated emitter gets a
  bounding rectangle of the same flux, which spreads it wider than the real shape.

Agent-Signature:
  platform: Claude Code (desktop)
  model: Sonnet 5.5
  role: research
  task: "work around EEVEE not casting emission; find why the corridor lantern had no glow"
