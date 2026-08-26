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

- Native target **426 × 240**; base projection frame **256 × 144**.
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

ASSET_ID = "alicias_bakery"
WINDOW = (0.9, 2.6, 1.2, 2.6)          # y0, y1, z0, z1

def build():
    room = kit.Interior(ASSET_ID, half_width=4.6, depth=6.2, ceiling_z=3.6)

    room.floor()
    room.back_wall(openings=[WINDOW])
    room.side_walls()
    room.ceiling(beams=5)
    room.window(*WINDOW)
    tab_x, tab_y = room.exit_threshold(-1.7)

    furn.azulejo_dado(room, height=1.05)
    furn.janela(room, "window", *WINDOW)
    furn.mesa(room, "counter", (room.back_x - 1.6, 0.4))
    furn.pote(room, "jar", (room.back_x - 0.5, 2.1))
    furn.lanterna(room, "lantern", y=-1.2, z=2.15)

    room.window_light((WINDOW[0] + WINDOW[1]) / 2, (WINDOW[2] + WINDOW[3]) / 2)
    room.doorway_light(tab_x, tab_y)

    room.finish()
    return room
```

Copy `tools/blender/recipes/passage_house_room3.py` as the model for the
`main()` boilerplate.

### `Interior`

| Call | What it does |
|---|---|
| `Interior(asset_id, half_width=, depth=, ceiling_z=)` | Sets up the room; dimensions are free |
| `.floor()` / `.side_walls()` / `.ceiling(beams=)` | The shell, with real thickness |
| `.back_wall(openings=[(y0,y1,z0,z1), ...])` | Segments the wall around any number of openings, and records them |
| `.window(y0, y1, z0, z1)` | Emissive daylight behind the opening, plus a sill |
| `.doorway(name, y0, y1, z1, recess=, lit=, open_back=)` | A door with an **inward** threshold |
| `.exit_threshold(y, width=)` | The way out: floor extruded **outward** |
| `.window_light(y, z)` / `.doorway_light(x, y)` / `.light(...)` | Canonical sources |
| `.part(name, size, location, material)` | Anything bespoke |
| `.finish()` | Normals, naming, contract metadata |

Materials on the room: `wood`, `whitewash`, `azulejo`, `terracotta`, `plaster`,
`stone`, `cloth`, `iron`, `straw`, `crock`, `daylight`, `lamplight`.

### `furnishings`

`arca` (banded chest) · `cama` (bed) · `armario` (cabinet) · `mesa` (table) ·
`cadeira` (chair) · `pote` (jar) · `prateleira` (shelf) · `lanterna` (wall
lantern, casts light) · `azulejo_dado` · `janela` (grille + shutters) ·
`escada` (stair, `direction=+1` runs away from camera).

**Add to this module rather than modelling furniture inside a map.** A vase or
a cabinet built in one map is invisible to every other author; the same piece
in `furnishings.py` is reusable and improves for everyone at once.

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

Review at native **426 × 240**. An attractive Blender viewport is not authority.

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
