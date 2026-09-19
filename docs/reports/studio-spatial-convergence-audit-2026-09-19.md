# Studio spatial-convergence audit, 2026-09-19

This is the follow-up audit requested by #1128 after the shared spatial
interaction core and Walk Profile constrained-polyline work merged through
#1129 and #1130. It inspects current `main` at `4018fc6f`. It neither changes
Map or environment data nor claims final gameplay or visual acceptance.

## Decision

Studio has one reusable interaction language where the authored operation is a
spatial component transform: shared selection state, semantic Z-up axes,
modal transform feedback, cancellation, and transaction-shaped history. Walk
Profile is its first complete consumer, in both free-3D and Plate Composition
views.

Do not force every coordinate-bearing record through that language. A light
paint stroke, a grid-owned anchor rectangle, and a derived collision mesh have
different owners and operations. The relevant question is whether a surface
has a live, author-owned spatial component that benefits from select/move
semantics, not whether it has numbers that look like coordinates.

## Evidence inspected

| Surface | Current owner and mutation path | Interaction finding | Decision |
| --- | --- | --- | --- |
| Walk Profile | `Map.traversal.lane.groundProfile`; `second-rite-editor-commands.js` validates create, move, extrude, subdivide, and dissolve | `spatial-interaction.js` supplies selected-set, semantic Y/Z constraints, modal feedback, and transaction records. `three-editor-viewport-base.js` and `three-composition-viewport.js` consume the same state. | Already converged. Keep it as the reference consumer. |
| Event / world placement | Map Event identity and `worldPosition`; `event_presentation.js` and workspace callbacks mutate by Event id | Event selection participates in the shared selection view, but placement is still an immediate pointer drag: 3D is generic XYZ and plates are lane-Y-only. It has no shared modal `G` operation, semantic transform readout, or transaction boundary. | Migrate only Event placement to the spatial core in a dedicated follow-up. Preserve the different 3D and bounded-lane domains; do not turn plate placement into a free XYZ edit. |
| Fixed-map lights | Map grid lighting/lamp records; Map/Light palette paint, blur, and lamp actions | A brush stroke and a cell add/remove are paint operations, not a selected spatial transform. Their numeric parity and runtime light contract are separate. | Deliberately different. Keep paint/blur/lamp authoring out of the transform grammar. |
| Anchors and transfer markers | Pre-authored anchor rectangles live in `Map.anchors`; transitions are Event-owned records/models | Anchors are edited as named grid rectangles in Map Properties. Transfer placement belongs to the Event, and its marker is presentation of that Event authority. | Deliberately different. Do not add a second anchor/transfer spatial owner. Event-placement follow-up will improve the shared Event selection only. |
| Camera frame and plate calibration | Map `traversal.camera`; environment `preRendered.playerProjection`, slice/reference data, and image dimensions | Studio can inspect/preview the resolved runtime camera and Plate Composition, but exposes no manually proven Map camera or environment calibration mutation surface. | Migrate through #1116 only, after each supported field is proven to affect runtime composition. |
| Paths / regions | Current `zones` are JSON rectangles; no generic authored path or region topology is present | There is no live spatial component authority to migrate. Inventing one for UI consistency would create a second topology model. | Blocked by a future authored topology/capability decision, not by missing interaction mechanics. |
| Collision / environment geometry | Adopted environment products and runtime-resolved renderable bundle | The Walk Mesh control is explicitly inspection-only; Walk Profile remains Map-owned. | Deliberately read-only. Do not route derived geometry into authoring transforms. |

## Camera and plate facts verified against the selected Project

The off-centre fixtures demonstrate why #1116 must retain separate controls:

| Map | Plate size | `camera.projectionFrame.canonicalCenterX` | `playerProjection.centerX` | `runtimeCenterY` |
| --- | ---: | ---: | ---: | ---: |
| 24, Alicia's Upstairs | 424 x 240 | 213 | 233.6 | 3.15 |
| 27, Alicia's Padaria | 450 x 240 | 213 | 225 | 3.883 |
| 31, Port | 1065 x 240 | 213 | 533.998 | 14.802 |

Port also retains its authored non-flat `groundProfile`, including calibration
points beyond the playable lane interval. That is traversal authority, not a
camera/crop compensation mechanism.

## Required next work

1. Create the narrow Event-placement migration follow-up identified above.
   Its scope is shared selection/modal-transform consumption and proof in both
   existing Event domains; it must not introduce a universal placement schema.
2. Implement #1116's manual camera/plate-calibration surface. It must expose
   ownership and runtime effect separately for camera framing, plate anchor,
   and slice/reference calibration, then prove one camera edit and one plate
   calibration edit in staged LÖVE frames.
3. Leave lights, anchors, zones, and derived geometry on their existing
   authorities unless a future capability supplies a distinct authored spatial
   component with a real semantic mutation path.

## Verification

The focused spatial suite passed on this audit branch:

```text
node --test studio/editor/tests/test-spatial-interaction.js \
  studio/editor/tests/test-world-event-authoring.js \
  studio/editor/tests/test-shared-viewport-navigation.js

26 passed, 0 failed
```

This verifies the existing semantic-axis mapping, selection/transaction state,
profile topology commands, Event identity/placement authority, runtime/studio
transition transform contract, and navigation gesture separation. It is not a
substitute for the staged runtime-frame proof required by #1116.
