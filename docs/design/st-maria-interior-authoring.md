# Authoring a St. Maria interior

This is the complete brief for adding an indoor environment to St. Maria. It is
self-contained: you should not need to read other town documents, inspect
earlier experiments, or re-derive any camera number.

If you are authoring an **exterior**, the camera contract and the character
floor limit below still bind you, but the surface and furnishing vocabulary is
written for interiors.

---

## 1. What St. Maria is

A **colonial Portuguese** town. That is a specific vocabulary, not a generic
"old" one, and getting it wrong is the fastest way to make a map that has to be
thrown away:

| Use | Not |
|---|---|
| Limewashed masonry (*caiação*), warm off-white | Grey plaster, bare brick, exposed stone coursing indoors |
| An *azulejo* dado — blue-and-white tin-glazed tile as a **waist-high band** | Azulejo covering a whole wall (reads as a church or a station) |
| Dark tropical hardwood, heavy, turned | Slender pale joinery |
| Wrought iron: window grilles, chest bands, lantern frames | Bright or decorative metalwork |
| Terracotta: pantiles, floor tile, unglazed pottery | Glazed modern ceramics |
| Panelled doors and shutters | Plank doors |

Interiors are dim, thick-walled and shuttered against heat. Light is scarce and
comes from few sources, which is what makes the lighting rules below work.

---

## 2. The fixed contract

Everything here is already solved. **Do not re-derive it, and do not change the
lens.**

- The game ships three width presets, all 240 tall: **256 × 240 ("Classic",
  the canon one)**, 320 × 240, and 426 × 240.
- The lower part of the screen is a **permanent translucent menu**, so the
  **free screen area is 256 × 144**. That is the space a composition actually
  gets, and it is where the character floor limit comes from.
- The camera record is authored at Classic. A wider preset is the same camera
  with a wider window, revealing more world at the same texel scale.
- Lens `fovHalfX = 0.25` (a tangent — 28.0725° horizontal).
- Camera distance is **solved from the actor**, not chosen: a 1.75 m Walker at
  48 native px puts the eye **18.6667 m** from the action plane, at height
  **2.2604 m**, level (pitch 0).
- **Y = 144 is the character floor limit** — the lowest a character may stand
  before the engine would need Y camera scrolling. Characters normally stand at
  **Y = 128**.

**The character floor limit is not a crop.** The scene fills the whole frame and
beyond. What falls under the status menu must be superfluous — floor extension,
a plinth — never load-bearing composition.

**The only fixed dimension is the floor LEVEL (z = 0).** Width, height and depth
are free per map. A room may be far deeper than the player can walk.

### Scrolling is a promise

A map wider than the view **scrolls**, and a scene that runs off the frame edge
tells the player there is more that way. That is fine for a corridor or a
street — but only if the map really does end somewhere the camera can reach and
reveal.

So decide which kind of map you are building:

- **Self-contained and unscrollable** — most interiors. Size it to the Classic
  **256** width so the whole room is on screen at once and no edge invites the
  player onward. `interior.base_half_width_at(depth)` gives the half-width in
  metres visible at that width; sizing the side walls to it lands them exactly
  at the frame edge.
- **A lane that scrolls** — a corridor, a street. It may run well past the
  frame, but it must **terminate in real geometry**, and you must check with a
  full-map preview that walking to the edge reaches that end.

Never leave a room a little wider than the view. It reads as a screen edge the
player can walk to, and then nothing happens there.

The camera record is generated, never hand-written:

```bash
python tools/blender/make_town_camera.py
```

### Authoring frame

```
+X = camera forward (depth)      -Y = screen right      +Z = up
metres, walkable floor at Z = 0, action plane at X = 0
```

The floor's front edge sits at native **Y = 136**, a few px above the limit, so
an exit threshold has somewhere to project. `interior.floor_edge_x(native_y)`
inverts the projection if you need another scanline.

---

## 3. Rules that are not negotiable

**One screen shows one room.** The player never sees several rooms at once. A
corridor has doors; you only ever enter your own. Do not build cutaways across
multiple spaces.

**The backdrop is black.** Walls, floor and ceiling are just surfaces with a
thickness; everything outside them is black. Do not build large camera-facing
walls to fill the frame — that is what the black backdrop is for.

**Thresholds extrude along the axis of travel.** This is the game's movement
grammar and it is directional:

- a room's way **out** extrudes the floor **outward, toward the camera**;
- a corridor's doors lead away, so their thresholds extrude **inward** into
  each recess.

A *raised* square says "there is a thing here". A *protruding* one says "this
direction is passable". Never raise a threshold.

**Lighting: no sun, no key.** A hard raking light is exactly what makes an
interior read as a diorama. Baseline visibility is the world light the stager
supplies; **every hard shadow must come from a source the room contains** — a
window, a lamp, a fire — authored into the `.blend` beside the geometry that
motivates it.

**An opening onto black is a hole.** On a black backdrop a window or an arch
renders as a black rectangle where the brightest thing in the room should be.
Give it an emissive plane behind it (`Interior.window` does this; for an arch
you can see through, pass `open_back=True` to `doorway` and add one yourself).

**Anything mounted on a wall breaks around its openings.** The dado does this
from `room.openings` automatically. If you add a picture rail or skirting, do
the same — a band running over a doorway makes the door look painted on.

---

## 4. Writing a map

A map file declares only what makes that place itself. The shell, thresholds
and light rig come from `tools/blender/recipes/interior.py`; furniture comes
from `tools/blender/recipes/furnishings.py`.

```python
import furnishings as furn
import interior as kit

ASSET_ID = "example_room"
WINDOW = (0.9, 2.6, 1.2, 2.6)          # y0, y1, z0, z1
ALCOVE = (-3.1, -1.3, 1.4)             # y0, y1, how far the wall steps back

def build():
    room = kit.Interior(ASSET_ID, half_width=4.6, depth=6.2, ceiling_z=3.6)

    room.floor()
    room.back_wall(openings=[WINDOW], alcoves=[ALCOVE])
    room.side_walls(openings={1: [(room.back_x - 3.4, room.back_x - 1.4,
                                   1.5, 2.9)]})
    room.ceiling(beams=5)
    room.window(*WINDOW)
    room.side_window(1, room.back_x - 3.4, room.back_x - 1.4, 1.5, 2.9)
    tab_x, tab_y = room.exit_threshold(-1.7)

    room.platform("dais", room.back_x - 2.2, room.back_x, 1.1, 4.0, 0.34)
    room.foreground("doorpost", 3.4, span=(-0.99, -0.86), z0=-0.4, z1=3.4)

    furn.azulejo_dado(room, height=1.05)
    furn.window_dressing(room, "window", *WINDOW)
    furn.jar(room, "jar", (room.back_x - 0.5, 2.1))
    furn.lantern(room, "lantern", y=-1.2, z=2.15)

    room.window_light((WINDOW[0] + WINDOW[1]) / 2, (WINDOW[2] + WINDOW[3]) / 2)
    room.side_window_light(1, room.back_x - 2.4, 2.2)
    room.doorway_light(tab_x, tab_y)

    room.finish()
    return room
```

**This example is deliberately not any real place, and it deliberately spends
every axis.** An earlier version of it was a bakery, and two independent
authoring passes both produced a bakery shaped like it. Take the structure and
throw the contents away.

Copy `tools/blender/recipes/passage_house_room3.py` as the model for the
`main()` boilerplate.

### `Interior`

| Call | What it does |
|---|---|
| `Interior(asset_id, half_width=, depth=, ceiling_z=)` | Sets up the room; dimensions are free |
| `.floor()` / `.ceiling(beams=)` | The shell, with real thickness |
| `.back_wall(openings=[(y0,y1,z0,z1), ...], alcoves=[(y0,y1,depth), ...])` | Segments the wall around openings; an alcove steps it **back** and gets its own floor, ceiling and returns |
| `.side_walls(openings={1: [(x0,x1,z0,z1)], -1: [...]})` | The two side walls, pierced per side |
| `.window(y0, y1, z0, z1)` | Emissive daylight behind the opening, plus a sill |
| `.side_window(side, x0, x1, z0, z1)` / `.side_window_light(side, x, z)` | The same, through a side wall — light **across** the room |
| `.platform(name, x0, x1, y0, y1, rise)` | A raised dais or a sunken pit; a pit past the floor limit is refused |
| `.partition(name, y, x0, x1, height=)` | A stub wall dividing the plan, stopping short of the ceiling |
| `.foreground(name, ahead, span=, z0=, z1=)` | A near-field occluder in front of the room; a proscenium is refused |
| `.doorway(name, y0, y1, z1, recess=, lit=, open_back=)` | A door with an **inward** threshold |
| `.exit_threshold(y, width=)` | The way out: floor extruded **outward** |
| `.window_light(y, z)` / `.doorway_light(x, y)` / `.light(...)` | Canonical sources |
| `.part(name, size, location, material)` | Anything bespoke |
| `.finish()` | Normals, naming, contract metadata |

Materials on the room: `wood`, `whitewash`, `azulejo`, `terracotta`, `plaster`,
`stone`, `cloth`, `iron`, `bronze`, `forge_scale`, `charcoal`, `bread`,
`straw`, `crock`, `daylight`, `lamplight`, `embers`.

`embers` is emissive and casts nothing. A hearth still needs a `room.light`
beside it, or you have a fire that glows and lights nothing.

### `furnishings`

**Domestic** — `chest` (banded, *arca*) · `bed` · `cabinet` (*armario*) ·
`table` · `chair` · `jar` (*pote*) · `shelf` · `lantern` (wall lantern; casts
light, and leaves a `_light` sibling) · `barrel` · `sack` · `sack_stack`.

**The wall itself** — `azulejo_dado` · `window_dressing` (grille + shutters) ·
`stair` (`direction=+1` runs away from camera).

**Shop and bakery** — `counter` (*balcao*) · `bread_oven` (*forno a lenha*) ·
`bread_basket` · `peel` · `demijohn` (*garrafao*) · `scales` (*balanca*).

**Forge** — `forge` (*forja*) · `anvil` (*bigorna*, on its *cepo*) ·
`quench_tub` (*tina*) · `bellows` (*fole*) · `weapon_rack` · `tool_rail` ·
`ingot_stack` · `workbench`.

**Add to this module rather than modelling furniture inside a map.** A vase or
a cabinet built in one map is invisible to every other author; the same piece
in `furnishings.py` is reusable and improves for everyone at once.

### Naming: English, loanword only where English needs a phrase

Pieces are named in English. A Portuguese term is kept **only** where English
cannot say the same thing in a word: `azulejo` is not "tile", it is waist-high
blue-and-white tin-glaze, so it stays. `cadeira` is exactly "chair", so it does
not — the name buys a flag on the object, not any of its Portugueseness.

That vocabulary is load-bearing in the **proportions, materials and joinery**,
which is where it survives translation: a chair in slender pale joinery is
wrong whatever it is called, and one in heavy turned hardwood with iron banding
is right whatever it is called. Name the Portuguese term in the docstring,
where it identifies the object without costing anything. The material registry
already worked this way before the furnishings did — `whitewash`, not
*caiacao*.

### One piece is one object

Every furnishing builds inside `Interior.piece`, which joins the meshes made
in the block into a **single** object. The `.blend` is the hand-editable source
document; a piece that arrives as its component boxes has to be re-identified
and box-selected before it can be moved, and a furnished shop is otherwise
about a hundred loose boxes in a flat outliner.

```python
with room.piece(name):
    room.part(f"{name}_top", ...)
    room.part(f"{name}_leg_0", ...)
```

A light cannot be joined into a mesh, so `Interior.light` called inside a block
stays a sibling. Two things to know: `join` keeps only the **active** object's
modifiers, so `piece` refuses rather than silently drop one (nothing passes
`bevel=` today, which is why the join is currently lossless); and the joined-
away objects are **freed**, so anything you need afterwards must be captured
before the block closes.

Joining does not move a vertex — the face set, winding, normals and per-face
materials are identical before and after. It does change how EEVEE batches the
scene, which shifts antialiasing by about half a percent of pixels on thin
geometry like grille bars. Renders are otherwise deterministic, so treat a
larger difference than that as a real change.

---

## 4b. The axes: how not to build the same room again

Read this before you place a single prop.

Everything in section 2 is fixed -- the camera, the backdrop, the floor level,
the width of a self-contained interior. For a while the shell could express
exactly ONE shape on top of that: a box with one pierced back wall. The only
thing an author could vary was **which props stand against the back wall**, and
so every interior authored against it came out as the same room redressed. Two
independent authoring passes produced two rooms indistinguishable from Room 3
and from each other, and that was a property of this document, not of the
people writing against it.

These four axes exist to break that. **Spend ONE of them, for a reason the
place actually has.** Not "at least one" -- one. The first draft of this section
said to spend at least one, and the room built with all four at once was the
worst of the eight variants rendered to test them: every axis competing, the
frame cropped on three sides, the actor squeezed into what was left. More axes
is not more depth.

They are also not equal, and this is measured rather than asserted -- each was
rendered on its own against the same room:

| Axis | Verdict |
|---|---|
| **Side window** | The clear winner. Largest change in how the room reads, for the least geometry and no clutter. Reach for this one first. |
| **Alcove** | Works, but only with a header across its mouth (see below). |
| **Platform** | Quietly positive. Cheap, hard to get wrong. |
| **Partition** | Only once it is low and has end posts. Tall and blank, it is a pillar competing with the actor. |
| **Foreground** | Highest skill floor by far. Costs frame, and needs both correct placement and its own light before it pays for itself. Do not reach for it first. |

### The plan does not have to be a rectangle

`back_wall(alcoves=[(y0, y1, depth)])` steps the wall back over a span and
gives the recess its own floor, ceiling and returns. This is the cheapest real
change available: it puts a corner in the silhouette and gives a hearth, a
shrine, a bed or a stair somewhere to be that is not "against the back wall".
An alcove can carry its own window; an opening may not straddle its edge.

It builds a **header** across its mouth at `arch_z`, and that header is what
makes it work. Without one the wall simply moves back, which from a level lens
18 m away is very nearly invisible -- the first version of this axis had no
header, and the recess read as a bay with a confusing bright panel in it rather
than as a niche. Light the inside of an alcove too: a dark hole in the back wall
is not a feature.

`partition(name, y, x0, x1)` runs a stub wall away from the camera, dividing
the space. It stops short of the ceiling on purpose, because **one screen shows
one room** -- a full-height divider builds two rooms in one shot, which the
vocabulary forbids. It defaults to waist-to-chest height and carries end posts:
the first version was shoulder-high and featureless, and next to the actor it
read as a blank pillar rather than as part of the room.

### Light does not have to come from behind

`side_walls(openings={...})` plus `side_window` and `side_window_light` put an
opening in a side wall. This is the single largest change to how a room reads
for the least geometry: the same furniture throws entirely different shadows
when the light rakes ACROSS the space instead of arriving from behind the
player, and a shoebox lit from the back is most of why an interior reads flat.

### The floor does not have to be one level

`platform(name, x0, x1, y0, y1, rise)` raises a dais or sinks a pit. A raised
platform is free -- it moves a character UP the screen, away from the limit.
A sunken floor is not, so it is **measured, not trusted**: a pit whose surface
would push a character's feet past the character floor limit is refused, with
the native Y it would have landed on. Use `native_y_at(x, z)` yourself if you
want to check a composition before you build it.

### Something can be in FRONT

`foreground(name, ahead, span=, z0=, z1=)` puts geometry between the camera and
the room. Nothing ever was, which is the deepest reason these interiors read as
flat pictures: depth needs a near layer, not just a far one. Because every
light in the room is behind it, an occluder reads as a dark silhouette -- that
is the effect, not a fault.

`span` is given as a FRACTION of the visible half-width at that plane, so -1.0
and +1.0 are the frame edges whatever `ahead` you choose. The guard measures the
share of the free 256x144 area every occluder in the room COVERS between them --
cumulatively, because a post at 6% and a beam at 12% are each harmless alone and
close the frame down together.

The guard is a floor, not a recipe. Two rules it cannot check, both learned by
rendering the alternatives rather than reasoning about them:

- **Overlap the room; do not line the frame.** A full-width beam at the top or
  a post hard against the side reads as *letterboxing*, because the ceiling and
  the side walls already draw those edges. An occluder earns its place by
  overlapping the room, so something is visibly in front of something else.
- **Give it something to catch.** Every light is inside the room and aimed
  away, so an unlit occluder renders as a flat near-black shape -- at this size
  that reads as damage, not depth. Hang a lantern on the post, or put it where
  a window or doorway spills onto it. Which is the ordinary rule anyway: the
  near layer gets lit by something the place contains, like everything else.

### What is still missing

Nothing here changes the CEILING (still flat, with optional beams), and nothing
gives a room a second storey visible in one shot. If a place needs either, that
is a new axis and it belongs in `interior.py` beside these -- not modelled by
hand inside one map, where no other author will ever find it.

---

## 5. Materials

Semantic IDs live in `tools/asset-language/materials.json`; textures live under
`projects/<project>/assets/materials/<id>/`. A recipe binds the ID and never
names a texture file, so art can land or be promoted without touching any map.

`worldSizeMetres` in each `material.json` declares how many metres one tile
spans, and everything is textured in world space at that scale — the same wood
maps identically onto a door and a floor.

```bash
python tools/blender/material_library.py check          # validate the library
python tools/materials/make_placeholder_materials.py    # regenerate placeholders
```

Current textures are **placeholders**, generated in-repo from fixed seeds. They
carry `status: placeholder`; the maintainer will replace or promote them. Do not
treat their look as final, and **do not download external textures** — anything
external needs a real source, an SPDX licence and a retrieval date recorded in
`provenance`, which is a maintainer decision.

---

## 6. Build, stage, verify

Scaffold the source document once:

```bash
blender --background --factory-startup --python tools/blender/recipes/<map>.py --
```

Render it against the real camera with a Walker in shot:

```bash
blender --background --python tools/blender/stage_room_model.py -- --model projects/hichaukitoden-game/assets/authoring/environments/<map>.blend --ambient 0.13 --render out/<map>.png
```

The stager **measures rather than trusts**. It fails if the Walker does not
project to exactly 48 px, if the feet fall below the character floor limit, or
if the camera basis is mirrored. A clean run is evidence; a render that merely
looks right is not.

Review at **Classic 256 × 240** — that is the canon preset — and compose inside
the free **256 × 144** area above the menu. An attractive Blender viewport is
not authority.

Two preview modes matter:

```bash
--target-width 426     # what a wider preset reveals
--full-map             # widen until the WHOLE map fits, to see where it ends
```

`--full-map` is how you check a scrolling map's promise: it is the same camera
with a wider window, so the scale is unchanged and the map's real ends are
visible.

### The `.blend` is source authority

Once a map's `.blend` exists it is the editable document, and the maintainer
hand-edits it. The recipe **scaffolds it once and then refuses to overwrite it**;
`--force` exists but discards hand-authoring. If a map already has a `.blend`,
change the `.blend`, not the recipe. Staging never saves it.

---

## 7. Traps that have already cost time

- `first_stratum.common.box` emits **inward** face normals (issue #936).
  `interior.recalculate_normals` fixes this for you; if you build geometry
  outside the kit, recalculate it yourself.
- A camera basis with **determinant −1** cannot survive `to_quaternion()` and
  silently renders the actor upside down. `right = forward × up`; with forward
  +X and up +Z that means `rightY = -1` (issue #935).
- `object.bound_box` / `matrix_world` are **not in sync** in background mode
  right after an import or a scale assignment. Measure through the evaluated
  depsgraph.
- Blender resolves a **relative render path against the drive root**, not the
  working directory. Pass absolute paths.
- EEVEE's engine enum id moved between releases (`BLENDER_EEVEE` →
  `BLENDER_EEVEE_NEXT` → `BLENDER_EEVEE`).
- Rendering is deterministic here — two runs of the same `.blend` are
  byte-identical. So a pixel difference after a refactor is a **real** change,
  never sampling noise. Use that.

---

## 8. What still needs authoring

From the opening walkthrough, St. Maria's interiors are:

- **Passage House, Room 3** — done (`passage_house_room3`)
- **Passage House corridor** — done (`passage_house_corridor`)
- Passage Office (the Registry — grants the Crossing Writ)
- Alicia's bakery (supplies)
- Laura's forge (equipment)
- The Rusty Tankard (rumours)
- The Chapel (Sister Agnes)

Read the place's own text in `projects/hichaukitoden-game/docs/walkthrough/`
and `data/commonEvents.json` before inventing anything. Room 3's straw, feed
bowl, low coat hook and missing picture all came from three sentences of
authored text, and they carry the room.
