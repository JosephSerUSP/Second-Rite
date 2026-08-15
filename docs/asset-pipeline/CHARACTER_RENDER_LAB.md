# Character Render Lab

This is an **authoring and representation experiment**, not yet a production character schema.

The lab asks one concrete question: can one editable Blender character source feed both a realtime 3D actor and a deliberately tiny pre-rendered sprite representation without forcing gameplay animation semantics to care which renderer is active?

## Hypothesis

```text
editable character .blend
        │
        ├── read-only realtime export ──> GLB + named actions
        │
        └── read-only sprite bake ──────> 24x24 directional sheets
```

The semantic animation vocabulary is shared. `Idle`, `Walk`, and `Talk` are authored once. Facing is **not** duplicated into `walk_north`, `walk_south`, and similar gameplay states:

- realtime 3D resolves facing as actor/root yaw;
- a sprite representation resolves the same facing value to directional rows or frames.

A future runtime state machine can therefore remain representation-neutral.

## Source-authority rule

The first three lab `.blend` documents are scaffolded once by `tools/blender/bootstrap_character_render_lab.py`. That script is a materializer, not an ordinary compiler.

Once a source is accepted, ordinary rendering/export must be read-only. `tools/blender/render_character_render_lab.py` hashes each opened `.blend` before and after export/render and fails if the source changes.

This follows the same source-authority principle already established for item `.blend` documents: automation may create an initial editable source, but recurring compilation must not overwrite subsequent human or agent Blender edits.

## Why the shared asset contract is not extended yet

Current contract vocabulary has no proven character-specific authoring space, role, or placement frame. The lab therefore stays valid under the existing contract:

```text
representation:   full_model
authoring_space:  preview
role:             preview_only
placement_frame:  preview_frame
```

Prototype intent lives in bounded `sr_...` metadata on the Armature, including:

- source authority (`blend`);
- authored forward axis;
- rig kind;
- named clip ranges;
- requested derivative representations;
- final raster size and supersample factor.

Do not add `character_actor`, `character_local`, `actor_origin`, or similar contract vocabulary merely to make this experiment sound production-ready. Promote only the concepts that survive the lab.

## Rigging thesis: disconnected rigid puppets are legal

The prototypes deliberately do **not** require watertight character meshes or conventional deforming skin.

Each visual mass can be disconnected and exaggerated for a 24px silhouette. A real Blender Armature owns the animation, while each mesh part is rigidly weighted 100% to one bone. This gives us:

- large readable hands, feet, hair locks, sleeves and accessories;
- no requirement that limbs physically intersect under every pose;
- one coherent Action set for realtime export;
- editable Blender hierarchy and materials rather than baked transform tracks.

The lab is not claiming that production characters must use rigid weighting. It proves that this cheap vocabulary remains available.

## Three visual approaches

The initial sources deliberately explore different ways to spend a 24x24 raster budget.

### A — Soft pre-rendered doll

Smooth rounded volumes, glossy hair, cloth/skin/material separation, large facial landmarks and broad boots. This is the closest to a high-quality pre-rendered miniature whose sophisticated shading is doing substantial readability work.

### B — Faceted couture

Low-sided directional planes, asymmetrical hair, diagonal sash, satchel and wedge-like extremities. This asks whether strong lighting can turn deliberately coarse topology into a highly legible directional actor rather than a visibly primitive mesh.

### C — Ornamental sprite sculpt

Broad robe silhouette, smooth head/hair masses, metallic trim, emissive jewel and secondary ponytail/tassel motion. This prioritizes the final sprite composition over exposing the whole anatomy.

These are **rendering/authoring strategies**, not future engine backends.

## 24px render profile

The lab treats the final raster as the historical constraint while allowing the renderer to be unusually sophisticated for that footprint.

```text
Blender render: 192x192 RGBA
              ↓
8x premultiplied-alpha Lanczos resolve
              ↓
exact 24x24 RGBA frame
```

Key rules:

- no vertex snapping;
- stable subpixel geometry and animation;
- smooth normals where the model needs continuous volume and flat normals where planes are intentional;
- warm dramatic key light;
- cool separation/rim light;
- soft top fill;
- material roughness/metallic/coat differences remain meaningful;
- antialiasing is produced by supersampled coverage and the final resolve, including internal polygon/material boundaries;
- the enlarged inspection images use nearest-neighbour scaling only **after** the native 24px result exists.

This is not an attempt to emulate PlayStation rasterization faults. The aesthetic question is closer to: *how much rendering sophistication can be compressed into 576 final pixels?*

## Outputs under review

A lab run emits:

```text
<review artifact>/
  sources/                 # actual editable .blend documents
  realtime/                # GLB derivatives with animation
  spritesheets/<id>/       # exact native 24px sheets
  gifs/                    # native/enlarged motion inspection
  comparison_24px.png
  direction_readability_24px.png
  walk_cycle_contact_sheet.png
  manifest.json
```

The first runs are intentionally CI artifacts rather than committed binary sources. Visual acceptance comes before promotion to repository source authority.

## Questions the lab must answer before productionization

1. Does one Blender Action set survive realtime export cleanly enough for runtime playback?
2. Is root yaw + semantic facing sufficient for realtime while directional rows remain sufficient for sprite actors?
3. Which visual approach remains readable under actual Thestra map cameras and map lighting?
4. Should sprite-baked characters carry their own baked contact shadow, or should the map renderer own all grounding?
5. How much character lighting is source/render-profile art direction versus scene lighting inherited from the map?
6. Do production characters need a new authoring space and placement frame, and if so what do those names mean precisely?
7. Does the realtime derivative belong in GLB, another interchange format, or a Thestra-specific compiled representation?
8. How should a future animation-state resource reference semantic actions without encoding representation-specific direction names?

The lab should answer these with working artifacts before the shared contract is widened.
