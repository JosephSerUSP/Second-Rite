# Second Gate / Lantern Cleft environment contract

The authoring authority is `second_gate_lantern_cleft.blend`, built by
`tools/blender/build_second_gate_town.py` and exported through
`tools/blender/town_environment_pipeline.py`.

Required Blender collections are present and intentionally separated:

- `TH_SOURCE`: detailed source geometry, source materials, lights, and the real displaced masonry field.
- `TH_RENDER`: coarse 3D render geometry, Smart Project UVs, and the baked-atlas receiver.
- `TH_COLLISION`: simplified ground, gate piers, and stair blocking.
- `TH_ANCHORS`: actor, camera-focus, interaction, VFX, and occlusion anchors.
- `TH_PREVIEW_ACTORS`: three upright nearest-filtered `walker.png` cutouts with feet metadata.
- `TH_PREVIEW_ONLY`: baseline/projection markers, excluded from bake/export.
- `TH_CAMERA_PREVIEW`: fixed, level 43.27mm side-view camera.

The native proof is 426x240. The camera tracks only by horizontal projection
window translation at -96/0/+96 pixels; height, roll, pitch, and lens remain
fixed. Runtime outputs live in `exports/environments/second_gate_lantern_cleft/`.

The runtime atlas is a real UV bake on coarse 3D `TH_RENDER` surfaces. It is
not a screenshot atlas and no camera-space plane is used.
