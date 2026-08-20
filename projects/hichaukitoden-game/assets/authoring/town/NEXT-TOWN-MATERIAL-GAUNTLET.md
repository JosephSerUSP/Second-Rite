# Next Town Material Gauntlet — work record

The PR #859 camera authority check passes using a level 0 degree pitch, `fovHalfX = 0.25`, a 28.0724869 degree horizontal FOV and a 43.2676 mm Blender-equivalent lens. Its eye is fixed at `(0.9, 5.5, 0.0)` through the `-96 / 0 / +96` projection-window checks.

This workbench adds real source material paths to the Blender gauntlet: restrained procedural Noise/ColorRamp/Bump materials, CC0 Poly Haven Cobblestone 01 maps for paving, and an OpenAI-generated limestone sheet cropped into albedo/height/roughness maps. The generated height is used only for Blender bump; it is not treated as a normal map.

The current regenerated 01–09 renders, contact sheet, panning strip, source `.blend`, and provenance are experimental evidence. Native-scale inspection shows the re-authored level camera exposes a substantive composition problem: most existing #856 source massing was placed for the old pitched camera and now leaves excessively dark voids / flattened facade staging. Therefore this is not a final winner or a valid replacement for #856 evidence. The next production pass must rebuild the street set around the validated level projection before using a material ranking as art-direction evidence.

Recommended next step: create the six-surface material court under the level camera, then rebuild attempts 01–06 with facade depth positioned for the `(0.9, 5.5, 0.0)` fixed eye before judging convergence attempts 07–09. Do not change the camera to hide the composition defect.
