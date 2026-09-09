# Cortico courtyard revision — 2026-09-08

Work is on `codex/st-maria-exterior-pilot` in worktree `6d7d`; the owner checkout is untouched. The adopted `st_maria_cortico.blend` was edited directly. No map anchors, lane bounds, portals or camera parameters were moved.

The source now has pitched roofs on the residential wings, slatted shutters with editable hinge parents, an open common gallery, differently painted household additions, a small shrine, and planted foreground beds. Laundry is reduced to 55 percent of its previous size and placed beyond the actor lane. Quiet limewash replaces the noisy white wall material. The source light rig combines cool diffuse fill with a weak warm sun.

A packed evening sky occupies a world-space layer behind the buildings. It replaces the visible dungeon sky in this courtyard without changing other maps. Its original is `projects/hichaukitoden-game/assets/materials/cortico_evening_sky_v1.png`. Generation used the built-in image_gen tool, new-image mode, with this prompt:

> Use case: stylized-concept. Create a production game sky texture ONLY, wide landscape 3:2 image. Restrained hand-painted evening sky for a coastal Portuguese-colonial courtyard in a low-resolution late-1990s RPG. Muted slate teal and dusty blue upper sky, soft desaturated warm grey and pale apricot low horizon. A few long, soft stratified cloud banks, with faint warm illumination along their lower edges, broad quiet negative space and gentle atmospheric depth. Low contrast, painterly masses that remain legible when viewed at 426x240 game resolution. Entire image is sky from top to bottom; no buildings, no ground, no sea, no vegetation, no sun disk, no moon, no stars, no dramatic storm, no text. Sky is supporting scenery, not a spectacular focal point. Opaque RGB texture, no frame. Lighting intention: cool diffuse sky fill, very weak warm evening directional light.

Reusable authoring changes live in `tools/blender/recipes/courtyard.py`: shuttered openings, galleries and a wrapper around the existing house roof grammar. These functions add editable objects without resetting or saving a scene. The scene contract accepts transform empties while continuing to require actual bakeable geometry.

The exterior exporter now keeps source lighting by default, offers explicit staged diagnostic lighting and explicit Cycles device selection, and exports the floor's packed image binding and authored tint. Missing images and invalid tint values fail loudly. The floor retains 1,548 vertices, 1,470 faces and one-metre cells; visual terrain heights still do not implement gameplay elevation.

## Evidence and limitations

The first complete runtime preview exposed oversized near planting obscuring the actors. That preview is rejected; the source planting was subsequently reduced and moved closer to the camera so it frames the lower edge. Final frame review and package promotion are recorded below after the revised bake.

Twelve focused Blender tests pass: eleven scene-contract tests and the floor/background export test, including invalid-tint and missing-image cases. G5 remains red in Classic and Wide; no golden references were changed.

The original 1024-pixel, four-sample CUDA bake took about 64 minutes. The exterior exporter now batches opaque coordinate-independent evaluated copies while preserving editable source objects. Transparent cards and object-dependent materials remain separate: an all-material batch visibly damaged the foliage and was rejected. Temporary copies normalize active UV layers; named UV-map materials remain unbatched. Other pipeline callers retain unbatched behaviour by default. Source visibility is also currently forced on by the shared bake pipeline, so hiding an object is insufficient to exclude it as a bake contributor; an explicit bake-role contract is tracked in https://github.com/JosephSerUSP/Second-Rite/issues/1085. The background cards remain less expressive than the modelled courtyard and deserve a later source-geometry pass. This revision does not extend elevation traversal.


## Reviewed delivery

The final candidate is `out/courtyard-final`, copied into the existing Project runtime package. Its export completed in 546.8 seconds (9.1 minutes), versus approximately 64 minutes for the earlier unbatched 1024-pixel/four-sample CUDA export. Geometry changed slightly between those runs, so this is an observed iteration improvement, not a controlled benchmark.

The final package contains 8,122 runtime triangles and a 1024-pixel beauty atlas. Forty-five frames were captured on each surface. Map-26 west, centre and east were individually inspected in both Classic and Wide under `out/st-maria-cortico/courtyard-reviewed-{classic,wide}`. The tree canopy is intact, laundry sits beyond the actor lane, actors remain visible, and the bespoke cloud sky covers the dungeon backdrop. Foreground foliage is still visibly made from flat cards; this is an improvement pass, not a claim that every source element is fully modelled.

Fifteen pipeline tests pass, including temporary source batching and source-file preservation, in addition to the twelve source-contract/floor tests. G5 differs in battle effects, title and Classic developer-menu frames, with no map-frame mismatch reported; the native Effekseer shim is unavailable. No references were recaptured. The town-walk probe visits Cortico and its connections; map 28 remains unreachable in the existing probe.

The owner checkout and gameplay maps remain untouched. The revision is delivered on `codex/st-maria-exterior-pilot`. The adopted Blender file is the source of the exported geometry, lighting, floor material and sky.

Final staged checks: `VALIDATE OK`, `ALL UNIT TESTS OK`, `SAVETEST OK`, and `TOWN WALK END` (exit 0). Seven native world-effect assertions were unavailable because the Effekseer shim is absent.

Reviewed runtime frames are retained in [cortico-courtyard-proof](cortico-courtyard-proof/), with west, centre and east views on both surfaces.

Agent-Signature:
  platform: Codex
  model: GPT-6
  role: implementation
  base: 932e7a4a
