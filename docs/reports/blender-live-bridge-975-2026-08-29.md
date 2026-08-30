# Issue #975 — St. Maria live Blender co-authoring proof

Date: 29 August 2026

Authoritative source: `projects/hichaukitoden-game/assets/authoring/environments/st_maria_praca.blend`

Bridge session carrying the visual evidence: `950085ea7c86f23d`
Owner disposition: diagnostic edit rejected as a saved source change; the source `.blend` remained unchanged on disk.

## Question and live evidence

The supervised session tested whether a repository-aware agent could make a
useful visual decision against the owner's already-open St. Maria Praça scene,
without turning a recipe, export, or regenerated `.blend` into a second source
of truth.

The published context identified `PROP_fountain_plinth` as a unique mesh object
in `30_PROPS`, using datablock `Cube.012`, with no material slots or library
link. Its dimensions were `1.0 × 1.1 × 1.65 m`, location
`(9.35, 11.90, -0.35)`, and unit scale. The hierarchy and collection evidence
therefore ruled out an accidental linked-mesh change and made an isolated
object transform an appropriate bounded experiment.

The calibrated 426×240 game view showed the 1.65 m plinth reading as a tall,
nearly human-height mass in the compressed side-view composition. It competed
with the fountain silhouette and closed more of the midground than the intended
low civic plinth. The proposed comparison reduced only its vertical scale to
`0.7878788`, moved its centre to `z=-0.525`, and therefore preserved its bottom
while producing a 1.30 m height.

| Evidence | Before | 1.30 m comparison |
|---|---|---|
| Calibrated game camera | [PNG](975-live-blender/game-before.png) · [manifest](975-live-blender/game-before.json) · `1d224b…f32c` | [PNG](975-live-blender/game-after-plinth-130cm.png) · [manifest](975-live-blender/game-after-plinth-130cm.json) · `b95d94…8fba` |
| Isolated selection | [PNG](975-live-blender/plinth-before-selection.png) · [manifest](975-live-blender/plinth-before-selection.json) · `994e4a…eef0` | [PNG](975-live-blender/plinth-after-selection.png) · [manifest](975-live-blender/plinth-after-selection.json) · `29287d…5eb` |

The session also published the actual [viewport capture](975-live-blender/viewport.png),
[selection capture](975-live-blender/selection.png), and complete
[context snapshot](975-live-blender/context.json). All image hashes, dimensions,
timestamps, selections, session IDs, and source paths are retained in their
sibling manifests.

## Mutation, undo, and failure found during acceptance

The first physical Ctrl+Z exposed a real Blender 5.1 integration defect: object
location and scale restored, but Blender's evaluated dimensions remained at
1.30 m. The bridge was not accepted on that result. The implementation was
changed to establish the undo state in a real `VIEW_3D` override, settle the
dependency graph before and after the operator, and refresh it in Blender's
`undo_post` handler.

That rejected state is retained explicitly as
[the defective-undo capture](975-live-blender/game-after-owner-undo.png) and
[its manifest](975-live-blender/game-after-owner-undo.json); it is failure
evidence, not the accepted undo result.

The owner-supervised acceptance was then repeated from a freshly reopened
authoritative file with the repaired add-on:

1. inspection measured the source plinth at `1.649999976 m`;
2. one bridge request produced `1.300000072 m`, location `z=-0.524999976`, and
   scale `z=0.787878811`;
3. one physical Ctrl+Z in the 3D viewport restored location
   `z=-0.349999994`, scale `z=1.0`, and dimensions `1.649999976 m`;
4. Blender remained unsaved and `git diff` reported no change to the source
   `.blend` or `data/`.

The visual evidence interval ran from 18:26:13 to 18:42:39 local time
(`16m 26s`). The later repair/retest was intentionally separate: the defect was
fixed rather than concealed inside the original proof.

## Decision and value of the live loop

The 1.30 m version was useful as a comparison, but it was not approved for the
authoritative source. Its value was diagnostic: it confirmed that plinth height
was one contributor to the heavy midground while preserving the owner's right
to continue judging the fountain and surrounding façade rhythm in Blender.

This was materially better than save/export/rerun because the same live session
provided, without saving:

- the exact object, collection, mesh-sharing, material, camera, and dirty-file
  facts behind the visual question;
- native game-camera and isolated-selection comparisons tied to those facts by
  fingerprints and manifests;
- one bounded edit whose bottom alignment was calculated from the live
  transform rather than guessed from an exported plate; and
- a one-step owner-controlled reversal that also uncovered and drove repair of
  a production undo defect.

No recipe, exporter, runtime package, staged Project, `data/` file, or
authoritative Blender source was regenerated or saved during the proof.

## Automated evidence accompanying the proof

The windowed Blender integration test now covers authenticated main-thread
dispatch, viewport/selection/camera PNGs, 320×180 and 256×144 dimensions,
pixel-negative controls, state restoration, stale fingerprints, injected
mid-operation rollback, concurrent mutation rejection, terminal shutdown, and
add-on registration. The repository verification recorded for the completed
implementation is listed in the Issue/PR rather than duplicated as mutable
status here.
