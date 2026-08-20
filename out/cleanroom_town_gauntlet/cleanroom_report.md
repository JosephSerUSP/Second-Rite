# Second Gate clean-room town visual gauntlet

## Basis and compliance

Repository: `JosephSerUSP/Second-Rite`.

Worktree basis: detached `HEAD` at `3d391e0508aeee259db2577db86b20a34603ec82`; no branch was created, nothing was pushed, and no PR was merged. Remote state was fetched before the run. Required evidence read: issue #838, issue #695, PR #859, PR #862, and PR #863.

Every attempt was built by `cleanroom_gauntlet.py` after `bpy.ops.wm.read_factory_settings(use_empty=True)`. No previous `.blend`, town builder, environment package, atlas, generated material, public-library download, collision mesh, or prior render was opened or used as scene input. Attempts 07-09 were also reset and independently built; they use written findings, not copied geometry.

The only pre-existing repository visual asset consumed was `projects/hichaukitoden-game/assets/character/walker.png`. Frames 0-3 were used for the protagonist and NPC stand-ins. No public material was downloaded; all twelve environment materials were authored procedurally during this task.

## Camera

- Native output: 426x240.
- Projection: perspective, level side view, pitch 0 degrees.
- Horizontal FOV: 28.0724869359 degrees (`fovHalfX=0.25`).
- Blender lens: 43.2676048279 mm.
- Fixed eye: `(-13.3175, 5.5, 0.0)`.
- Principal point/horizon: `(213, 110)`.
- Walker calibration: 1.75 world units measured at 47.9978585 pixels.
- Projection strip: -96, 0, +96 pixels; eye, lens, and pitch were unchanged.

## Material vocabulary

`M_Stone`, `M_Plaster`, `M_Timber`, `M_Roof`, `M_Paving`, `M_Metal`, `M_Painted`, `M_Glass`, `M_Cloth`, `M_Grime`, `M_Ornament`, and `M_Water` use new Blender Noise/ColorRamp/Bump node networks with shared object-space scale conventions. The native material test is `material_test.png`. Provenance is in `material-provenance.json`.

## Divergence and convergence concepts

| ID | Concept | Native observation | Source tris | Render tris |
|---|---|---|---:|---:|
| 01 | Bellwater Fold | Tall civic fold, narrow bell mass, diagonal foreground screen; readable but quiet. | 1,348 | 48 |
| 02 | Lantern Court | Compressed court and offset threshold; best compact grouping, detached roof risk. | 1,102 | 48 |
| 03 | Silt-Crown Arcade | Unequal arcade bays with aggressive displaced wall relief; rhythm risks repetition. | 2,636 | 48 |
| 04 | Needle Forum | High civic needle, deep arch, plinth, clerestory, windows, threshold steps, quiet flank. | 3,648 | 48 |
| 05 | Windglass Row | Domestic row with glass, cloth, and staggered eaves; too flat at native scale. | 1,340 | 48 |
| 06 | Rain-Cistern Crescent | Open route around a round wet civic object; memorable but doorway competes. | 3,094 | 48 |
| 07 | Mosaic Threshold | New clean-room interpretation of deep recess + quiet wall + offset door. | 2,292 | 48 |
| 08 | Brass Veil Passage | New vertical civic mass with brass veil rhythm; strongest source triangle count. | 4,064 | 48 |
| 09 | House of the Red Eave | New asymmetrical domestic landmark with round window and red canopy. | 3,136 | 48 |

At least 03, 04, and 08 use real dense displaced TH_SOURCE panels; 04 and 08 are aggressive variants. TH_RENDER remains coarse and independent.

## Blind evaluation and selection

Two separate internal native-resolution passes scored the numbered renders without concept names or material labels. External evaluators were not available locally. The winner was 04 in both passes:

| ID | Aggregate |
|---|---:|
| 01 | 6.45 |
| 02 | 7.05 |
| 03 | 6.65 |
| 04 | **8.10** |
| 05 | 6.85 |
| 06 | 7.25 |
| 07 | 7.45 |
| 08 | 7.75 |
| 09 | 7.55 |

04 won on architectural identity, vertical mass, doorway/arch readability, human staging, and source-to-runtime collapse potential. The contact sheet with scores is `town-cleanroom-gauntlet-contact-sheet.png`; full score notes are in `evaluation.json`.

## Selected winner and package

Winner: **04 / Needle Forum**. It was re-authored from another empty Blender scene for the final pass. The source-vs-runtime reduction is 3,648 -> 50 triangles, a 72.96:1 reduction. The atlas is 1024x1024 PNG, 260,971 bytes. The runtime package totals 268,077 bytes and contains:

- `selected_runtime/environment.obj`
- `selected_runtime/environment.mtl`
- `selected_runtime/environment.png`
- `selected_runtime/collision.obj`
- `selected_runtime/environment.json`

The package follows the current contract: `contractVersion=1`, one material group, atlas dimensions 1024x1024, separate collision mesh, named anchors, bounds, and camera metadata. SHA-256 values are recorded in `material-provenance.json`.

The beauty atlas is a camera-space bake: the selected TH_SOURCE beauty pass was promoted into one atlas image with a reserved dark band for coarse runtime occluder faces, then mapped onto the coarse TH_RENDER backdrop. Preview actors and preview lights/helpers were excluded from the source beauty bake. `town-cleanroom-source-vs-baked.png` shows the matched source and baked environment plus an amplified difference image. Mean absolute RGB difference is 15.397 levels, or 6.04% of the 0-255 range, on the matched native environment pass.

## Playability readiness

The selected package includes `spawn_player`, `door_threshold`, `npc_01`, `npc_02`, `foreground_occluder`, `environment_min`, `environment_max`, `walk_route_start`, and `walk_route_end`. The collision OBJ is independent of the render OBJ. The horizontal lane is authored from y=1.45 to y=9.55 at the calibrated actor depth. This is ready for the separate #862 bounded-lane seam; no runtime engine work was duplicated here.

## ASSET FIREWALL AUDIT

Pre-existing visual file actually read:

1. `projects/hichaukitoden-game/assets/character/walker.png` — the only repository visual input.

Task-created visual files read during post-processing or final verification:

1. `material_test.png`.
2. `attempts/attempt_01.png` through `attempts/attempt_09.png`.
3. `selected_source_beauty.png`.
4. `town-cleanroom-beauty-atlas.png`.
5. `selected_runtime_environment.png` and `selected_runtime_full.png`.
6. `projection_left.png`, `projection_center.png`, and `projection_right.png`.
7. `town-cleanroom-gauntlet-contact-sheet.png`, `town-cleanroom-source-vs-baked.png`, and `town-cleanroom-projection-strip.png`.

No earlier repository visual file was read as image data. GitHub inspection of the required issues/PRs used text/metadata only; previous visual filenames were not opened. No prior environment package, material provenance file, town render, atlas, or builder was used as an input.

## Lessons for the next clean-room run

The next run should spend more of divergence on connected volumetric room construction before material polish. Native 426x240 rewards one or two unmistakable structural decisions—door depth, ceiling/eave, floor relationship, and a foreground occluder—more than many small noisy details. Camera-basis conventions must be tested independently for cameras, actors, and atlas planes; they do not share a safe quaternion. The winning source is visually usable and package-ready, but the next run should pursue a more lived-in interior/exterior hybrid so the architecture reads less like a façade study.
