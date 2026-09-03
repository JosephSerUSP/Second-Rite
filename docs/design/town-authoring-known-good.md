# Second Gate town authoring — known-good findings

This document is the intentionally **sterile historical input** for future Second Gate town visual experiments. The imagery-free mechanism record in
[`projects/hichaukitoden-game/docs/world/st-maria-techniques.md`](../../projects/hichaukitoden-game/docs/world/st-maria-techniques.md)
is also always-readable.

Future art agents may inspect camera transforms, compensation formulae, lane
constants, projection-window offsets, pixel scales, validation code and generic
tested tooling. Those are mechanisms, not visual ancestry. They should **not
inspect earlier town visual PRs, renders, contact sheets, `.blend` compositions,
town-specific composition builders, exported town packages, or previous
material assets**. Those experiments were useful research, but exposing their
authored content creates visual ancestry and repeatedly biases new work toward
old layouts and mistakes. Production topology/data generators such as
`tools/towngen/build_town.py` are readable for their numeric contract; their
referenced plates and compositions are not.

The only pre-existing authored visual asset a fresh town gauntlet may consume from the repository is:

`projects/hichaukitoden-game/assets/character/walker.png`

Freshly created procedural assets, freshly generated material sources, and freshly downloaded suitably licensed public materials are allowed during the new task.

## Presentation facts

- The game ships three width presets, all 240 tall: **256 × 240 ("Classic", the canon one)**, 320 × 240, and 426 × 240. Review at **Classic**; 426 is a wide variant, not the target.
- The lower part of the screen is a permanent translucent menu, so the **free screen area is 256 × 144** — the space a composition actually gets, and the origin of the character floor limit below.
- A map wider than the view **scrolls**, and a scene running off the frame edge promises the player more that way. Keep a self-contained interior inside the Classic 256 width; a lane that scrolls must terminate in real geometry, checked with a full-map preview.
- Attractive Blender viewport framing is not authority.
- The base projection frame used by the current camera work is **256 × 144**.
- `walker.png` is **144 × 48**, dimensionally six **24 × 48** cells.
- A useful physical reference is a **1.75-world-unit** Walker projecting to approximately **48 native pixels** tall at the authored action plane.
- The preferred baseline **was** a level side view at Thestra pitch **0°**. The authored plate camera is **pitched 17.5° down**, and it is the authority for anything painted — see "The plate coordinate contract" below. The level baseline still describes the *runtime* camera records of the plate screens, which all declare `pitchDegrees: 0`; those records do not set a plate's perspective, because a plate is blitted and never reprojected.
- The preferred lens family is approximately **43.27 mm Blender-equivalent**, corresponding to approximately **28.07° horizontal FOV** / `fovHalfX = 0.25` under the current 426×240 / 256×144 contract.
- Preserve the preferred lens and solve **camera distance** for actor scale. Do not widen the lens merely to make a sprite hit 48 px.
- A principal-point / horizon placement around native **Y ≈ 66** is the current baseline: more architecture and less floor than a centered presentation render. (An earlier **Y ≈ 110** predates the character floor limit below.)
- The camera eye is fixed during ordinary side-view tracking. Horizontal tracking should use the **projection window**, not camera translation.
- Representative projection-window checks around **-96 / 0 / +96 px** have been useful. Eye transform, pitch and lens must remain invariant.
- Small approximately **±3° pitch** variants have been useful as optional composition studies. They are not the baseline and must not silently change actor scale or screen anchoring.

### View transform

- Bake under **AgX**, not Standard. Standard clips everything above 1.0 to white
  permanently; AgX rolls it off. Below 1.0 the two differ by a curve a grade can
  recover, so "we will colour-correct later" argues *for* AgX. The reasoning and
  the one caveat — a live-rendered element composited against a plate must use
  the same transform, or highlights mismatch at the seam — are in
  [`st-maria-interior-authoring.md`](st-maria-interior-authoring.md), under
  "View transform".
- This is a **mechanism**, not a composition, so it is readable under the
  sterile rule above (see issue #1016).

### The plate coordinate contract

Five facts, each of which has been got wrong at least once. They are collected
here because they only make sense together (issue #1016).

**The floor is z = 0.** It used to be z = -1.5 on ten screens and 0 on the rest,
which was an authoring accident rather than a convention: the Praca blend, where
the hand-authored assets and the placement calibration live, establishes 0 as
floor level. Every lane, anchor and ground profile now stands on it. Rebasing the
floor is a *relabelling*, so anything measured against the floor — the eye height
above all — moves with it; leaving the eye at its old absolute height lifts the
whole picture by about 41 rows.

**`playerProjection.screenY` is the ground row.** `viewport_3d` calls it "the
authored foot line" and draws the figure upward from it. It is NOT the top of the
sprite, and adding the 48-row sprite height to it puts the expected ground 48
rows too low, which makes a correct camera look badly wrong.

**The plate camera is the one in the .blend, not the one in the map.** A plate is
paint: the runtime blits it and never reprojects it, so the map's camera record
cannot govern its perspective — and every plate screen declares `pitchDegrees: 0`,
so projecting through it yields an elevation with no keystoning at all. The
authored camera in `st_maria_praca_modelled.blend` is location
`(-10.8667, 11.8495, 2.2604)`, euler `(107.5, 0, -90)` — 17.5° down — 20.344 mm
on a 36 mm sensor, `shift_y -0.247574`, rendering 906 × 240. It reproduces that
package's declared `centerX` of 453 to a hundredth of a pixel.
`tools/asset-gen/town_projection.py` carries it, with a self-check.

**Pixels per world unit along the lane is 27.428571**, and it is derived, not
chosen: the focal length in pixels (half the plate's 240 rows over the vertical
half extent 0.234375, so 512) over the 18.6667-unit distance to the lane. Ten
placeholder plates declare **34.6**, which is not a rival calibration — their
widths are exactly `span x 34.6 + 80` in every case, so a width was picked and a
scale back-solved to fit it.

**A plate is `span x 27.428571 + 256` pixels wide.** The lane, plus a full
composition of margin, so the 256-wide window is still filled when the player
stands at either end. The Praca is exactly that; the 34.6 plates carry 80 px of
margin, 40 per end, and cannot cover the view at the lane extremes. `imageSize`
and `pixelsPerRuntimeY` must be updated *with* a regenerated plate and never
before it, or the doorways slide off their anchors.

The ground row itself is an authoring parameter, not a constant: the blend leaves
it at `make_town_camera.py`'s default `--feet-y` of 128, the plates author 136,
and both are legal above the 144 character floor limit.

### Character floor limit

- **Y = 144** is the **lowest a character may stand** before the engine would need Y camera scrolling. It derives from the 256 × 144 base projection frame.
- This bounds **character placement only. It is not a crop.** The scene must still fill the whole 426 × 240 target and beyond, exactly as the overscan rule below requires. Floor continues past Y = 144, foreground sits in front of it, and outdoor scenes especially want ground well below it. Whatever falls under the status menu should be superfluous — floor extension, a plinth, or eventually a solid plate — never load-bearing composition.
- Characters usually stand a little above the limit: **Y ≈ 128** (144 − 16) is the normal action-plane placement, leaving 16 px of headroom.
- With the fixed lens, these fully determine the camera. A 1.75-unit Walker at 48 native px solves eye distance **18.6667** units; feet at Y = 128 with the horizon at Y = 66 solves eye height **2.2604** units.
- Do not hand-author these numbers. `tools/blender/make_town_camera.py` derives the calibration record from the lens, the actor's pixel height and the desired feet/horizon placement, and `tools/blender/stage_room_model.py` fails if a staged actor's feet project below the limit.

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

`right = forward × up`. With forward **+X** and up **+Z**, screen-right is **−Y**; a **+Y** right vector produces a determinant `-1` (mirrored) basis. Measured on the shipped parity fixture: `det = -1.0000`, quaternion round-trip error `2.0000`, and a staged actor renders upside down. The camera-parity gate does not catch this — it validates point projection and transform invariance, both of which a reflection preserves, and it never stages an actor. See issue #935.

Coordinate handedness is load-bearing. A camera basis with a reflection / determinant `-1` cannot be passed through a quaternion conversion and assumed to survive unchanged; a quaternion represents rotation, not reflection. Camera/billboard helpers should preserve the explicit basis or equivalent matrix and assert the resulting actor is upright rather than trusting quaternion conversion alone.

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

The strongest recent clean-room geometry came from **a small number of independent architectural lineages followed by serious refinement within each lineage**. That research structure should be retained. Independent directions should begin empty; once a direction survives clay review, continuing to model and refine that same newly authored scene is desirable.

## Full-environment framing and continuity gate

A successful frame must read as a view **inside an environment**, not a photographed diorama sitting in empty world space.

Before material polish, reject a composition if any of the following is true:

- the walkable floor/ground ends visibly at the bottom or side of the frame without an authored spatial reason;
- the camera can see accidental world-background/void underneath, beside, or behind the set;
- a projection-window move reveals the edge of the authored set;
- the scene has no meaningful foreground depth layer;
- the foreground consists only of a token pole, slab, arch fragment or prop added to satisfy an occlusion checklist;
- architecture terminates at the screenshot boundary instead of implying continued streets, walls, roofs, alleys, terrain, water, or other spatial continuation.

Author **overscan in world space**. Ground, foreground, architecture and background coverage should extend beyond the visible 426×240 frame and beyond the intended projection-window tracking envelope. At the representative -96 / 0 / +96 checks, the scene should remain spatially complete rather than exposing set edges.

The floor is part of the composition. A narrow clipped strip of paving at the bottom is not enough: the frame should contain enough authored ground/threshold space to make Walker's footing and the traversable place legible.

A genuine foreground layer should sit at a meaningfully different camera depth from the action plane and contribute real overlap/occlusion as the actor moves, while still feeling architecturally or environmentally necessary.

Deliberately visible sky, distant haze, water, abyss, courtyard opening or other negative space is valid. **Unintended empty world is not.**

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
- A selected-to-active bake target must own a valid **active, non-overlapping atlas UV layout**. Existing tiling/world-space UVs are not automatically a usable receiver atlas; overlapping receiver UVs can make an otherwise successful bake silently unusable.
- Bake proxy placement and cage/ray distance must be treated as measured geometry. Coplanar/behind-the-source proxies, excessive source-to-proxy distance, and proxies larger than the source region they represent can silently black out, drop, or occlude detail.
- Combined beauty bake values are scene-linear. The exported texture must have an explicit color-space contract. If runtime/browser/Blender consumers will sample a PNG as sRGB color, do not write raw linear RGB bytes into that PNG; encode to the expected file color space or carry and honor an unambiguous linear-texture contract end to end.

The final beauty atlas must be **causally derived from the selected TH_SOURCE appearance and mapped through real TH_RENDER UVs**. Two recent false positives clarify this rule:

- copying a 426×240 source beauty render/screenshot into a file named `atlas` is not a geometry beauty bake;
- synthesizing a separate procedural atlas for TH_RENDER, independent of the TH_SOURCE materials and lighting, is also not a source-to-runtime beauty bake.

A valid proof must demonstrate that the source scene's surface appearance is transferred to the coarse geometry. Prefer an actual UV/selected-to-active bake or another per-surface transfer that can be traced from TH_SOURCE to TH_RENDER. Report UV/atlas coverage and show a matched source-vs-runtime comparison.

Do not invent a competing environment-package schema inside a visual experiment. Use the current generic environment-package contract or keep the output explicitly experimental and non-consumable until a separate architecture task establishes a change.

## Camera-aware atlas allocation

A bounded camera makes ordinary world-area UV density unnecessarily conservative. If the authored camera/view envelope is known, the atlas can spend more texels on surfaces that occupy more native screen space and fewer on surfaces that are unlikely to contribute to the final views.

Treat this as a **continuous importance problem**, not a binary `visible -> full / invisible -> delete` rule.

A general allocator should support a tunable blend between:

- **world/surface-area density** — appropriate when every face may matter equally; and
- **view-weighted density** — appropriate when camera movement is narrow and screen contribution is predictable.

The view-weighted side should evaluate a **camera envelope**, not one frozen screenshot. That envelope may include projection-window positions and, where the authored scene allows them, bounded eye/orientation/pitch changes. For each face, useful signals include expected projected area across the envelope, peak projected area, facing angle, occlusion, and the amount of camera movement required to expose it.

Do not collapse all currently invisible faces into one class. Distinguish at least conceptually between:

- visible in the nominal/current view;
- front-facing but currently offscreen, reachable by ordinary pan;
- nearly visible / near-facing surfaces reachable by a small camera change, such as the top of an object viewed from slightly below;
- front-facing but currently occluded surfaces that a modest move could reveal;
- strongly back-facing surfaces requiring a large orbit/change of viewpoint;
- genuinely internal or unreachable surfaces.

A near-facing top should retain substantially more texture budget than the back of an object that faces fully away from every plausible camera. Accessibility should decay with required camera change rather than jump from full importance to zero at the current backface boundary.

Keep **culling separate from texel weighting**. A conservative allocator should retain a minimum world-area/texel floor even for low-importance faces; destructive face removal should be an explicit stronger optimization justified by a truly fixed camera contract. Static-camera scenes may choose a high view bias, modestly moving cameras a blended bias, and free-camera scenes a near-world-uniform bias.

The allocator should report its assumptions and evidence: camera samples/envelope, view-bias parameters, minimum density, texels assigned to visible/near-visible/low-accessibility faces, and projected texels-per-native-screen-pixel. This makes atlas optimization reviewable rather than a hidden consequence of UV packing.

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

Recent sterile runs were geometrically more promising but remained **texturally weak**. Generic `Noise → ColorRamp → Bump` materials repeated across hero surfaces do not by themselves create convincing masonry, wood, roof tile, paving or plaster. Texture richness should include **material-specific structure** where the surface calls for it: masonry courses and mortar, directional wood grain, tile/shingle rhythm, paving joints, wear patterns tied to use, plausible roughness variation, and relief that survives the native presentation.

A generated-material script or downloaded source file does not count as evidence unless the material is actually connected to and visible on the final TH_SOURCE scene. Material evaluation must inspect the final native render, not merely a material swatch or provenance manifest.

Procedural-only final materials remain valid if they are genuinely structured and convincing, but procedural noise is better treated as one layer of a material system—not as the entire surface vocabulary by default. Hero surfaces should receive deliberate texture authorship.

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
- do reuse validated **generic tooling**, numeric mechanisms, and the facts in
  this document and `st-maria-techniques.md`;
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
- actual 426×240 render produced;
- floor/ground coverage remains intentional across the frame;
- no accidental void/set edge is visible in center or representative projection-window views;
- a meaningful foreground depth layer exists;
- the claimed beauty atlas is derived from TH_SOURCE rather than copied from a framebuffer or synthesized independently;
- materials visible on hero surfaces contain enough material-specific structure to survive native-size review.

Only then should blind aesthetic scoring occur.

Do not treat multiple numeric tables produced by the same agent as independent evaluators. Preserve raw evaluator/model provenance when external evaluation is used.

## What future agents must not learn from history

Do not provide old attempt names, winners, screenshots, architectural descriptions, layout coordinates, or previous scene-builder source to a fresh art agent.

All historical information judged worth carrying forward should be distilled into this document or into generic tested tooling. If a new lesson is important, update the distilled contract rather than telling the next art agent to browse the old experiments.
