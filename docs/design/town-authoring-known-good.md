# Second Gate town authoring — known-good findings

This document is the intentionally **sterile historical input** for future Second Gate town visual experiments.

Future art agents should use the facts and generic tooling below, but should **not inspect earlier town visual PRs, renders, contact sheets, `.blend` files, town-builder scripts, exported town packages, or previous material assets**. Those experiments were useful research, but exposing their authored content creates visual ancestry and repeatedly biases new work toward old layouts and mistakes.

The only pre-existing authored visual asset a fresh town gauntlet may consume from the repository is:

`projects/hichaukitoden-game/assets/character/walker.png`

Freshly created procedural assets, freshly generated material sources, and freshly downloaded suitably licensed public materials are allowed during the new task.

## Presentation facts

- Review at the real **426 × 240** native target. Attractive Blender viewport framing is not authority.
- The base projection frame used by the current camera work is **256 × 144**.
- `walker.png` is **144 × 48**, dimensionally six **24 × 48** cells.
- A useful physical reference is a **1.75-world-unit** Walker projecting to approximately **48 native pixels** tall at the authored action plane.
- The preferred baseline is a **level side view**: Thestra pitch **0°**.
- The preferred lens family is approximately **43.27 mm Blender-equivalent**, corresponding to approximately **28.07° horizontal FOV** / `fovHalfX = 0.25` under the current 426×240 / 256×144 contract.
- Preserve the preferred lens and solve **camera distance** for actor scale. Do not widen the lens merely to make a sprite hit 48 px.
- A principal-point / horizon placement around native **Y ≈ 110** has been compositionally useful: more architecture/sky and less floor than a centered presentation render.
- The camera eye is fixed during ordinary side-view tracking. Horizontal tracking should use the **projection window**, not camera translation.
- Representative projection-window checks around **-96 / 0 / +96 px** have been useful. Eye transform, pitch and lens must remain invariant.
- Small approximately **±3° pitch** variants have been useful as optional composition studies. They are not the baseline and must not silently change actor scale or screen anchoring.

## Camera and actor tooling rules

Do **not** reimplement camera calibration or Walker billboard presentation inside an art gauntlet.

Use the generic WorldCamera → Blender calibration tooling from the non-visual camera lane and the shared `thestra_camera.create_actor_preview(...)` helper when available.

A correct Walker preview has these invariants:

- caller supplies 24×48 frame dimensions;
- frame slicing is validated against the real sheet;
- object origin is the actor's feet/world anchor;
- nearest-neighbour sampling;
- hard transparency/chroma-key boundary;
- unlit/emissive presentation;
- camera-facing world-space plane;
- upright orientation;
- no actor pixels enter the environment bake.

An agent must never invent its own billboard quaternion/UV convention merely because it is starting a fresh art scene. Fresh art does not mean fresh infrastructure.

## Spatial composition lessons

The town must read as **real spatial architecture**, not a row of decorated frontal slabs.

Useful scenes normally contain meaningful separation between several layers, for example:

1. near architectural foreground;
2. walkable actor/action plane;
3. inhabited primary architecture;
4. secondary/back architecture;
5. distant spatial continuation or landmark where appropriate.

The exact architecture must be newly invented each run. The layer model is a spatial principle, not a template.

Additional lessons:

- foreground occlusion should belong naturally to the place rather than exist only to prove occlusion;
- openings should reveal actual deeper space when possible;
- doors should have believable human scale and wall thickness;
- architecture should imply continuation beyond the visible frame;
- a walkable route should arise from the architecture rather than look like an empty strip placed in front of a backdrop;
- native 426×240 presentation rewards a few strong structural decisions more than dozens of tiny details;
- if an untextured/clay render still reads only as boxes plus superficial trim, reject the architectural direction before material polish.

## Blender source/runtime contract

Continue using the established authoring separation:

- `TH_SOURCE` — rich Blender-only source appearance;
- `TH_RENDER` — coarse **real 3D** runtime/depth/silhouette geometry;
- `TH_COLLISION` — simple traversal/collision representation;
- `TH_ANCHORS` — spatial anchors only;
- `TH_PREVIEW_ACTORS` — Walker/NPC previews, never baked;
- `TH_PREVIEW_ONLY` — authoring helpers;
- `TH_CAMERA_PREVIEW` — downstream calibrated camera.

The intended collapse is:

**rich TH_SOURCE → coarse real 3D TH_RENDER + one baked beauty atlas**

Do **not** replace the environment with a camera-space beauty plane or one flat prerendered background. The runtime geometry must retain the depth/silhouette/occlusion structure needed by the scene.

Large geometry affecting actor occlusion or silhouette stays in `TH_RENDER`. Shallow surface relief may disappear into the bake.

## Bake and geometry lessons

- Correct outward face winding matters for selected-to-active baking. A source render looking acceptable does not prove bake-ray orientation is correct.
- Never render `TH_SOURCE` and coincident `TH_RENDER` together when judging source beauty.
- Displacement is useful on appropriate subdivided source surfaces, especially façade panels.
- Blindly displacing closed boxes can tear/crack shared edges; do not use that as the default relief strategy.
- Rich source geometry may be extremely expensive if the final silhouette/depth can collapse safely.
- Source-vs-baked comparison should be made at matched 426×240 framing.
- Preview actors must be excluded from all environment bake evidence.

## Material lessons

Three authoring sources remain valid and complementary:

- procedural Blender materials;
- freshly sourced public-library materials with clear commercial/redistribution-compatible licensing;
- freshly generated material-source imagery.

Known lessons:

- procedural materials are particularly useful for controlled variation, grime, moss, patina and masks;
- good scans can be strong hero-surface sources;
- generated material imagery is useful, but prior 2×2 pseudo-PBR sheets did **not** maintain reliable pixel registration between quadrants;
- prefer a flat, evenly lit generated albedo/source and derive height/roughness/masks deterministically where practical;
- do not trust image-generated tangent-space normal maps as authority;
- preserve physically coherent world/object-space texture scale across differently sized objects;
- be explicit about sRGB-looking authored values versus Blender linear values;
- at a 426×240 final target, very large source textures often waste memory and bake time without visible benefit. Downsample based on evidence.

Every fresh external material should carry provenance: source, license, retrieval date and file hashes where practical. Never store API keys.

## Playability findings to retain

A prototype has already shown that the side-view environment can support the intended interaction loop without becoming a platformer.

The useful behavioral seam is a **bounded continuous lane/provider**, not a new universal Map ontology:

- continuous left/right world position;
- authored horizontal bounds;
- no jump/gravity/platformer grammar;
- projection-window tracking while the camera eye remains fixed;
- ordinary Project/Event authority continues to own dialogue, flags and map/scene transfers;
- a doorway can transfer to an interior and a later return can reflect changed ordinary game state;
- collision/anchors should answer only the concrete traversal needs of the authored environment.

The prototype's specific map data, names, coordinates and architecture are **not** production authority. Future art work should only prepare a clean package with spawn, walk bounds/collision, doorway and NPC anchors so it can be plugged into the traversal seam later.

## Fresh-scene firewall

For a new visual gauntlet:

- begin each genuinely independent architectural direction from `bpy.ops.wm.read_factory_settings(use_empty=True)` or an equivalent empty file;
- do not open or inspect old town `.blend`s or renders;
- do not execute old town-specific composition builders;
- do not read old contact sheets or attempt descriptions;
- do not reuse old town meshes, layouts, coordinates, atlases or material assets;
- do reuse validated **generic tooling** and the facts in this document;
- `walker.png` is the only pre-existing repository visual asset allowed.

Iteration **within one declared architectural direction** may modify that direction's own fresh scene. The clean-room reset is required between independent directions, not between every revision. This avoids the opposite failure mode where a breadth quota encourages nine shallow arrangements of primitives instead of serious architectural development.

Future visual research should prefer a small number of independent directions with several critique/refinement passes each over a large batch of superficially different complete scenes.

## Evaluation rules

A visual gauntlet must fail loudly on basic presentation defects before scoring aesthetics.

Pre-score acceptance checks should include:

- Walker upright;
- feet anchored;
- expected native pixel scale;
- camera/lens/pitch contract valid;
- environment not flattened to a camera-space background plane;
- source/render collection isolation correct;
- no actor leakage into bake;
- actual 426×240 render produced.

Only then should blind aesthetic scoring occur.

Do not treat multiple numeric tables produced by the same agent as independent evaluators. Preserve raw evaluator/model provenance when external evaluation is used.

## What future agents must not learn from history

Do not provide old attempt names, winners, screenshots, architectural descriptions, layout coordinates, or previous scene-builder source to a fresh art agent.

All historical information judged worth carrying forward should be distilled into this document or into generic tested tooling. If a new lesson is important, update the distilled contract rather than telling the next art agent to browse the old experiments.
