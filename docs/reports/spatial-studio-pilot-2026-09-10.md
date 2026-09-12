# Spatial Studio pilot: Praca, 2026-09-10

The plate-render refresh boundary recorded here was superseded by the direct
asset and generated-semantics design in
`spatial-studio-audit-2026-09-11.md`. This document remains the pilot history
and its earlier verification record.

This follows the reviewed direction of #1088 and the separate
`resolved-spatial-spike-2026-09-09.md` experiment. The experiment uses pinned
sources; this pilot uses the current Project, including its pre-existing dirty
town content. Neither constitutes acceptance of all current town artwork.

## Implemented boundary

The runtime renderable collector consumes the environment package's exported
render mesh through its existing OBJ path. The Studio bridge explicitly requests
collision inspection meshes and publishes the actual resolved WorldCamera.
Export callers do not implicitly receive collision as render geometry.

Studio displays these products without rebuilding geometry semantics. Collision
is a green wireframe overlay with a visibility control; hiding it also removes
it from pointer selection. Event world positions use the shared coordinate
adapter, including the inverse conversion on a three-axis gizmo drag. Position,
identity, dialogue and commands remain Map JSON facts. No blend, exported
anchor, or geometry product acquires Event ownership.

The Inspector lists Events for selection through occluding geometry. The
existing Event modal opens by selected identity instead of accidentally editing
the first Event at the same legacy grid coordinate. Applying or deleting affects
the selected object only; ambiguous coordinate-only opening fails loudly.

## Observed save/reopen/runtime proof

A disposable Project under `out/spatial-studio-proof` was opened in Studio.
Registrar (1702, map 17) was moved using the viewport gizmo from Y=16.763 to
Y=16.97803461873456. Its existing command list was edited through the ordinary
Event editor to display `Studio spatial round-trip proof.` The normal Save
Changes action wrote the disposable Project; reopening preserved both changes.
Shipping Project JSON was checked and did not receive this proof edit.

The canonical exporter staged that saved Project into
`out/spatial-studio-runtime`. A disposable harness drove actual bounded-lane
movement and the ordinary Space interaction. At actor Y=16.95 the real dialogue
scene displayed the saved text. The rendered screenshot was inspected: actor,
ground and dialogue were visible. Local evidence:

- `out/spatial-studio/runtime-round-trip.json`
- `out/spatial-studio/runtime-round-trip.png`
- `out/spatial-studio/runtime-round-trip.log`

The harness is evidence for this interaction, not a replacement for G5 or a
complete traversal of every town transfer. These ignored local artifacts must
be retained separately if the result is reviewed outside this checkout.

## Verification and limitations

The four experimental fixtures regenerate identically through the actual LOVE
probe; eight focused spatial tests pass. Twelve focused editor tests pass.
The live bridge test verifies environment placement preservation across an
Event-only edit, resolved camera preservation, and loud failure for a missing
package. G1 passed on the staged pilot.

The correct staged unit runner reported 257 passes and 11 failures in bounded
lane tests against current town data. G6 reported 27 of 46 matching frames and
19 mismatches, including map-tree/content differences and animated frames.
These are unresolved failures, not a green baseline claim. Existing issues
#858 (unit invocation) and #959 (historical visual failures) provide context,
but do not prove every current failure predates this candidate. No golden was
recaptured. G5 has not been run for this pilot.

The initial geometry-only camera preview was insufficient for plate maps.
The composition follow-up below replaces that preview. No transfer
activation-volume overlay or Blender Event proxy is provided. The tactical and
metroidvania fixtures remain compiler experiments, not playable production
Map families or fully editable Studio surfaces.

## Preview availability follow-up

The proof bridge left on port 8082 accepted the proof editor origin (8098),
rejecting the normal Studio origin (8080) with HTTP 403. This was agent-created
process interference, not evidence of a geometry compiler failure. The proof
services were removed after the recovery check. Future proof hosts must isolate
both HTTP and bridge ports and clean up their owned processes.

Electron now supplies its actual editor port to its bridge. Failed map previews
show the underlying error visibly with a Retry Preview action. A browser check
observed the unreachable error, restored the service, and used Retry Preview to
return to runtime geometry without reloading or saving the Map. A separate
ephemeral-port audit compiled all 29 current Project maps successfully through
the persistent runtime bridge; details are in
`out/spatial-studio/preview-audit.json`. This tests compilation, not every map's
rendered correctness or all possible causes of runtime unavailability.

## Editable plate composition correction

The fixed Classic/Wide snapshot mode was rejected because it blocked Event
manipulation and replaced interactive 3D scenes. It has been removed from the
authoring path. Fully 3D Maps now remain in the live 3D viewport, starting from
the authored environment camera pose. Initial framing is immediate for every
Map family, including dungeons; later requested navigation can still ease.

Plate Maps expose the full native-width composition from the actual renderer.
Studio owns pan/zoom and Event boxes. The renderer publishes each Event's screen
position and homogeneous horizontal projection. Studio inverts that resolved
projection to update the existing JSON world-Y field. It does not duplicate
plate calibration, camera or floor semantics. A gizmo drag previews its position;
on release the runtime recomposes the image. Double-click opens the existing
Event editor. The 3D geometry view remains accessible.

The real bridge test checks native full-plate dimensions, all authored Event
identities, projection/inverse round trips before and after a position edit,
and changed rendered pixels for an unsaved world-Y edit. It also asserts that
a fully 3D interior produces no composition-image product. In the disposable
Project, the earlier pin implementation moved Child from Y 12.717 to
14.827575245539713 and preserved it through save/reopen. The replacement shared
transform gizmo moved it to 17.072868059943662, preserving X 7.8 and Z 0.
Only the disposable Project was saved. The shipping Map remained at 12.717.

Plate and 3D viewports now consume the same Event box, selection outline,
TransformControls factory and navigation policy in `three-authoring-tools.js`.
Empty-space left drag, MMB and RMB pan in the screen plane; wheel zooms.
Alt+MMB orbits 3D. Authored hit targets and dungeon painting retain their left
gestures. The plate adapter projects the supported lane axis using runtime
coefficients and its corresponding Studio axis color. Runtime sprite bounds
also come from the actual renderer. It has no separate DOM pin vocabulary.

Browser verification exercised the shared plate gizmo and 3D interior pan/zoom;
navigation left Save Changes disabled. Switching from plate to interior also
restores the Free Authoring/Runtime Camera toolbar labels. Local evidence:
`out/spatial-studio/shared-plate-controls.png` and
`out/spatial-studio/shared-interior-controls.png`. The real bridge integration
test and 13 focused navigation, Event authoring, Inspector and viewport checks
pass. These checks do not certify every map's visual composition.

Plate sprite height remains grounded by the existing lane renderer. The plate
gizmo therefore exposes its supported horizontal placement, retaining X/Z. The
remaining generic 3D control mismatch is tracked in #1099. This is an editing
surface, not interactive gameplay or a replacement for Test Play.

The prior snapshot candidate's G6 result was 27/46 matching with 19 failing
frame names. It does not certify this corrected interaction or initial camera
behavior, and no references have been regenerated.
The corrected interaction's G6 rerun also matches 27/46 frames, with 19
mismatches. The browser interaction proofs above supplement that red gate;
they do not turn it green.
The shared-controls rerun likewise matches 27/46 with the same 19 failing frame
names (`out/spatial-studio/g6-shared-controls.log`). References remain untouched.
The corrected renderer's G5 run matched 141/144 Classic frames and all 34 Wide
frames; the crop invariant passed. The three Classic mismatches are the
developer-menu frames, whose existing dirty source changes its Bounds label.
This is still a red absolute G5 result, not permission to replace references.

## Next architectural test

Exercise source edits for the dungeon, elevated lattice and planar fixtures
through a shared inspection consumer before promoting an engine-wide spatial
format. Keep topology and tactical policy as typed companions; preserve one
resolver per fact and let the display adapter consume its output. Acceptance
requires seeing source edits survive save/reopen and verifying the resulting
structural products, rather than merely drawing three different scenes. Do not
encode these families as fake bounded-lane Maps to reuse the Praca pilot.
