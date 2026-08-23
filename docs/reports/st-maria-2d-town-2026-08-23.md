# St. Maria as a side-view town — experimental branch

Branch: `exp/838-town-2d-flat`. Issue #838.

**This is an experiment and is not proposed for `main` as it stands.** It uses
flat pre-rendered plates where the authoring contract in
[`town-authoring-known-good.md`](../design/town-authoring-known-good.md) requires
coarse real-3D geometry plus a source-derived beauty atlas. That conflict is
deliberate and is discussed at the end.

Built owner-absent, overnight, on the explicit instruction to skip the Meshy
geometry step and use flat images "to get as advanced as we can".

## What it is

Ten screens of St. Maria, traversable and populated:

| Screen | Map | Reached from |
|---|---|---|
| Gate of Thestra | 16 | new-game spawn; Praca (west) |
| The Praca | 17 | Gate, Market, and four doors |
| Market Row | 18 | Praca, Quay, Weaponsmith |
| The Quay | 19 | Market, Pub, Chapel |
| Weaponsmith | 20 | Market Row |
| The Pub | 21 | The Quay |
| Chapel | 22 | The Quay |
| Laura's House | 23 | The Praca |
| Alicia's Room | 24 | The Praca |
| Passage House | 25 | the opening cinematic |

The Gate holds the sealed church door into the Labyrinth, which transfers to
map 2 exactly as before.

## What was verified, and how

| Check | Result |
|---|---|
| `lovec <stage> validate` | `VALIDATE OK` |
| `tools/ci/run-staged-unit.ps1` | `ALL UNIT TESTS OK` |
| `tests/test_bounded_lane.lua` | 103 passed, 0 failed |
| `tools/golden/capture-town-proof.py` | `THESTRA_TOWN_PROOF OK frames=30` |
| `lovec <stage> town-walk` | 9 screens reached, every interior two-way |

The golden gates G2/G3/G5/G6 were **not** run. G5 in particular photographs the
old grid town, so it is expected to be red on this branch; that has not been
measured and must not be assumed either way.

## Presentation: static stages, not a panning panorama

The transplanted compositor from #890 assumes a panning panorama - it pins the
actor and slides the plate underneath. A generated plate is 1536x1024, and
covering a wide panning street from one would need either heavy cropping or a
stitch seam. So each screen is instead a composed static stage at native
426x240: the plate holds still and the actor walks across it.

That is one variable in the compositor, not a second code path. `panX` and the
actor's screen x now share an anchor which is either the actor (panning) or the
lane centre (static), so both compositions are the same arithmetic.

The consequence worth knowing: a screen is one frame wide, about seven seconds
of walking. The town is made of more screens rather than longer ones. Adding
panning later needs wider plates, not a different renderer.

## The numeric convention

Every screen shares one calibration, which is what keeps them consistent:

- lane `y` maps to native `x` through `centerX 213`, `pixelsPerRuntimeY 34.6`
- exteriors run `y` 0..10, interiors 1.5..8.5 - a room feels smaller because its
  bounds are tighter, not because its scale differs
- actor feet at native `y` 206-224 per screen, set against each plate's ground
- door positions were read off the plates with a pixel ruler and converted with
  `y = (pixel_x - 213) / 34.6 + 5`, so every door sits where a door is painted

## Three runtime changes this needed

**Arrival anchors.** A screen spawned every entrant at its single `spawnAnchor`,
so the Praca could not return the player to whichever of its four doors they
used. An `arrival` naming an anchor in the destination package now selects it.
This reuses the string `LOAD_MAP` already carries; no new trigger and no new
authored object type. The door anchor *is* the spawn point.

**Path normalisation.** LOVE's filesystem does not collapse `..`, so a manifest
referencing a sibling directory resolved to a path that does not exist. Package
asset paths are now normalised on load.

**Input grammar.** Doorways only answered the confirm button and `up` did
nothing. Up is now the door verb - it reaches doorways only, so it can never
open a conversation the player did not aim at - and pushing further into a bound
the lane will not cross takes the doorway anchored there, which is how a
side-view town is actually left.

## Content

All fifteen authored events from map 1 were carried across **by copying their
`commands` arrays verbatim**, keyed by event name, rather than being retyped or
paraphrased. Shops, the auction and common-event calls come with them.

Two NPCs have no map-1 ancestor and carry newly written lines: a child on the
Praca and a fisherman on the Quay.

The plates and the thirteen townsperson sprites were generated. Sprites are
painted large, keyed off flat magenta, cropped to their own silhouette and
reduced to one 24x48 cell; asking for 24x48 directly does not work. The existing
`assets/sprites/NPC*.png` are 48x64 nude placeholder figures and were not used.

## Demoting the 3D grid town

`system.spawn.mapId` now points at map 16. That single value also repoints the
Town Portal, which resolves through `system.spawn` rather than a literal.

Map 1 is untouched and still loadable. The Developer Room (map 8) already
carried five `LOAD_MAP` exits to it, so no edit was needed to keep it reachable
for testing.

The opening cinematic ended on "PASSAGE HOUSE — ROOM 3" and "this'll be home for
both of you", then loaded map 1. Rather than rewrite authored text to fit a
street, the lodging room it describes exists as screen 25 - two narrow beds, a
washstand, a window that does not close - and the opening transfers there.

## Known gaps

- **No foreground occlusion layer.** `foregrounds` points at a transparent PNG,
  so actors never pass behind anything. The compositor supports a real cutout;
  it needs a depth pass the flat pipeline does not produce.
- **No panning within a screen.** See above.
- **No day/night or weather.** A flat plate cannot be relit. This is the
  clearest thing the 3D route buys and the flat route cannot.
- **Screen 25 is reachable only from the opening**, by design, and so is not
  covered by the `town-walk` route.
- **G5 is presumed red** and unmeasured.
- Sprites read slightly more muted than the owner's own
  `npc_female_redhead_dress.png`. A style call, not a defect.

## The standing conflict

The sterile contract forbids exactly this presentation: *"Do not replace the
environment with a camera-space beauty plane or one flat prerendered
background."* #890 broke the same rule and it worked; this branch does it
deliberately and at larger scale.

What this experiment establishes is that the **content and interaction layer is
sound and complete** - the screen graph, the arrival anchors, the door grammar,
the dialogue migration, the demotion of the grid town. All of that is
presentation-independent. If the plates are later replaced by low-poly geometry
carrying a baked atlas, everything in `data/` and every runtime change here
survives unchanged; only the `preRendered` block in each package is swapped for
mesh references.

That is the argument for treating this branch as a content spike rather than a
rendering proposal.
