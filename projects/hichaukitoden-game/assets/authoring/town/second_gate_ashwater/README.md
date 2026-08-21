# Second Gate — Ashwater Bellfoundry Lane

Second Gate is a sterile side-view town approach built as a Blender authoring
scene and a small runtime handoff package. The selected direction is the
**Bell Foundry Gate**: a deep, warm foundry portal anchors the middle of frame;
a guildhall and bell frame the route on the left; an open market workshop,
counter, crates, and awning keep the right side playable; and a near arcade
roof with visible supports provides the required foreground occlusion.

## Deliverables

- Source scene: `second_gate_ashwater_bellfoundry.blend`
- Runtime handoff: `package/`
- Camera record: `camera_record.json`
- Direction comparisons: `renders/architectural_directions_clay.png` and
  `renders/architectural_directions_refined.png`
- Source/runtime comparison: `renders/source_vs_baked_native.png`
- Projection-window continuity: `renders/projection_window_strip.png`
- Native final views: `renders/final/`

The three independent architectural directions are preserved as
`direction_a_initial.blend`, `direction_a_refined.blend`,
`direction_b_initial.blend`, `direction_b_refined.blend`,
`direction_c_initial.blend`, and `direction_c_refined.blend`.

## Handoff contract

- Target frame: 426x240, with a 256x144 base frame.
- Camera: side view, pitch 0 degrees, 43.27 mm lens, 28.07 degree base
  horizontal FOV, viewport center Y 110, and projection-window offsets -96,
  0, and +96 for continuity checks.
- Required authoring collections are present: `TH_SOURCE`, `TH_RENDER`,
  `TH_COLLISION`, `TH_ANCHORS`, `TH_PREVIEW_ACTORS`, `TH_PREVIEW_ONLY`, and
  `TH_CAMERA_PREVIEW`.
- `TH_SOURCE` is the rich presentation layer. `TH_RENDER` is a deliberately
  coarse, single-atlas runtime mesh. The atlas is derived from source color
  through the selected-to-active bake; it is not a camera-space card.
- `TH_COLLISION` is separate from presentation geometry. Gameplay anchors are
  serialized into `package/environment.json`, including player spawn, walk
  start/end, bellmaker, vendor, archivist, doorway, interaction point, and the
  foreground occluder.

## Counts and provenance

The exported runtime mesh is **621 triangles / 439 vertices**, with a 512x512
PNG atlas. Authored collection counts are recorded in
`renders/triangle_counts.json`.

All environment geometry and materials were created in the scene builder; no
external environment art was imported. The only pre-existing visual asset used
is `projects/hichaukitoden-game/assets/character/walker.png`, previewed through
the shared `tools/blender/thestra_camera.py` actor helper.

The final atlas bake requested GPU execution and used Blender Cycles OptiX on
the NVIDIA GeForce GTX 1650. The exact bake record is in
`package/environment.json`. Source paving slabs are excluded from the bake
transfer because the authored source relief is intentionally richer than the
coarse runtime surface; they remain in `TH_SOURCE`.

## Review note

The source render is the quality bar for the authored scene. The runtime atlas
is intentionally constrained and reads flatter/desaturated in the current
beauty pass, while preserving the portal, roof occlusion, route, blue drain,
and playable anchors. A follow-up art pass can improve the shared UV color
transfer without changing the camera, collision, or gameplay contract.
