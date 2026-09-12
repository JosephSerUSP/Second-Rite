# Spatial Studio architecture audit, 2026-09-11

This audit follows the #1088 spatial pilot after hands-on review of plate and
fully 3D St. Maria Maps. It evaluates the authoring boundary, camera semantics,
interaction model and invalidation behavior against SPEC section 1.1.2. It
does not accept the current town artwork or replace runtime visual gates.

## Conclusion

The authoring surface needs two display adapters over the same Map and
environment facts. A plate package is an authored layered image, so Studio
loads those layers directly and projects live Event objects over them. A fully
3D package is runtime-derived geometry, so Studio consumes the static resolved
environment bundle and displays live Event objects from Map JSON. LÖVE remains
the authority for validation, Test Play, gameplay simulation and final pixels;
it is no longer used as a plate-image refresh service.

Pure camera, projection and bounded-lane display math now has one source in
`shared/semantics/world-view.ts`. The shared-semantics build generates the
browser JavaScript and runtime Lua consumers. TypeScript is useful here because
it is compiled into both hosts; moving the math into browser-only TypeScript
would merely relocate the duplicate.

## Boundary by fact

| Fact | Authored or resolved authority | Studio consumer |
|---|---|---|
| Map/Event identity, commands and `worldPosition` | Project Map JSON | Existing Event editor and live Event objects |
| Plate layer paths, slices and player projection | Environment package manifest | Direct Three.js layered-image adapter |
| Town camera frame and projection | Generated world-view semantic leaf | Three.js camera/projection adapter |
| 3D environment and collision geometry | Runtime renderable collector | Static Three.js bundle |
| Event authoring visuals | Map JSON plus shared authoring helpers | Shared boxes, selection outline and transform gizmo |
| Final gameplay pixels and movement | LÖVE runtime | Test Play and visual proof harnesses |

## Corrected findings

The 3D viewport previously implemented screen drag through OrbitControls. That
moved the camera eye and target, while the game keeps the resolved camera frame
fixed and changes the projection window. Wheel input similarly changed camera
distance instead of the optical FOV scale. Free Authoring now intercepts blank
screen drag and wheel input as projection-window pan and optical scaling. The
runtime camera pose stays fixed. Alt+middle drag remains the explicit orbit
inspection gesture.

Studio also aimed the Three.js camera at the authored optical target. The
runtime does not derive its orientation that way: `eyeHeight`, yaw and pitch are
independent authored facts. Alicia's Padaria exposed the difference because its
target vector implies a different pitch. The generated camera record now
publishes its forward and up basis, and the Three adapter consumes that basis.
The vertical principal-point conversion also accounts for screen-down versus
clip-up coordinates. A live Studio frame now matches the composition of the
actual runtime `28-centre` town-proof frame.

The plate viewport previously asked LÖVE to render a base64 composition after
an Event drag. This made ordinary placement wait on a process boundary and left
the cursor ahead of, or behind, the returned image. Studio now fetches the
manifest's scene and foreground assets, positions Event objects with the
generated projector, and updates the dragged object before the Map mutation is
scheduled. Event-only plate edits do not compile a renderable bundle.

The runtime authoring bundle previously duplicated Event models already owned
by Studio's semantic scene. The duplicate remained at the old position until a
runtime refresh, which made 3D cursor movement appear stale. The editor bridge
now requests static environment and collision content without Event models.
One live object therefore owns selection, gizmo movement and the eventual Map
write in both plate and 3D views.

The final review also exposed two presentation problems that were not semantic
authority failures: collision wireframes obscured the Event editing vocabulary
in narrow interiors, and plate Events with a sprite read as an empty hitbox.
Collision is now an opt-in inspection overlay. The direct plate adapter draws
each resolved Event sprite inside the same shared box and selection treatment
used by the 3D editor, while the foreground plate remains the occluding layer.

The camera adapter initially had to discover the base viewport's private
cameras by wrapping `OrbitControls.prototype.update` during construction. The
audit removed that global hook. The base viewport now returns an explicit
camera-rig interface containing its perspective and orthographic cameras and
controls.

The final indoor review found one remaining competing camera writer: after the
authoritative runtime record had been applied, the asynchronously delivered
environment bundle started the base viewport's generic collision-bounds frame.
That later transition made the initial orientation and centre look inverted or
offset. A resolved runtime camera now explicitly suppresses that generic
frame; bounds framing remains available only when no runtime camera is present.
Event OBJ previews also resolve their authored companion MTL, so transition
arrows render as their arrowhead and shaft rather than an unmaterialed object.

The two fully modelled interior exits (maps 28 and 29) had also been omitted
from the event-presentation data that every other St. Maria environment exit
uses: neither bump Event named `transition_arrow.obj`, so Studio had no arrow
to draw. Both now carry that authored model and a test keeps the 3D-interior
exit invariant explicit. Studio keeps the common Event box alongside visual
assets, brightens the shared transform gizmo, and consumes `worldHeight` plus
the authored frame aspect for the same billboard dimensions as the runtime.

## Remaining structural debt

`world-presentation.js` still contains a handwritten resolver for the older
`rpg_perspective` and related Scene-camera profiles. Town side-view semantics
now use the generated leaf, but the repository does not yet have one generated
resolver for every camera profile. Migrating those remaining pure profiles is
appropriate after their Lua inputs and output records are inventoried; silently
changing Scene preview framing while doing the town fix would be unsafe.

Generic three-axis `worldPosition` control versus a bounded lane's supported
movement axis remains the separate #1099 design question. The St. Maria plate
adapter exposes only the lane axis and preserves X/Z. Fully 3D Event authoring
continues to expose XYZ until that issue defines a common topology contract.

## Verification evidence

The generated semantic module passes Node and LÖVE conformance, including the
camera basis, principal point, projection inversion, projection-window pan,
optical scale and ground interpolation. Host-cutover checks prove that
`world_camera.lua` and `bounded_lane.lua` consume the generated module. Focused
Studio tests cover shared navigation policy, world Event identity/movement,
viewport conversion, scene resolution and workspace invalidation. The live
bridge integration test confirms that plate and 3D requests contain no raster
composition and no duplicate Event placement while preserving environment and
camera authority.

The live browser proof inspected direct Praça plate composition and Alicia's
Padaria 3D composition with selected shared Event boxes and gizmos. The
corresponding actual runtime frame was captured through `town-proof-frames`.
Local evidence is under `out/spatial-studio/` and
`out/audit-spatial-runtime-classic/`; those ignored artifacts are supporting
evidence, not committed golden references.

Absolute G5/G6 results remain owner-machine claims. No visual reference was
recaptured or changed by this work. The final staged run reported `VALIDATE OK`
and `SAVETEST OK`. The repository's staged-unit launcher reached the existing
bounded-lane data result of 257 passes and 11 failures; no other suite failed.
G5 matched 141/144 Classic frames and all 34 Wide frames, with only the three
already-dirty developer-menu frames differing; its crop invariant passed. G6
matched 27/46 frames with the same 19 frame names recorded by the preceding
pilot runs. Both absolute visual gates therefore remain red, and their
references remain untouched.
