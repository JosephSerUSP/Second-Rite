# Cortico distant scenery candidate

This is a bounded authoring helper and candidate for the adopted Cortico
modelled exterior. It adds three separated, distant opaque silhouette meshes:

| Layer | Blender depth X | Centre Y | Width | Height | Material family |
| --- | ---: | ---: | ---: | ---: | --- |
| distant vegetation (west/east pair) | 24.5 | -16 / +16 | 22.0 | 18.0 | dark wood, locally dark green |
| mid roofline (west/east pair) | 31.0 | -16 / +16 | 26.0 | 17.0 | terracotta |
| far terrain (continuous) | 38.0 | 0.0 | 60.0 | 16.0 | rough limestone, locally muted green |

The far terrain covers `Y=-30..30`, beyond the pilot lane study window and its
end margins. Roofline and vegetation are intentionally separated into west and
east silhouettes, so the continuous terrain remains behind them and visible
through their gaps. Every piece has a small X thickness and an opaque closed
side wall. There are no alpha textures, full-screen backdrop rectangles,
collision meshes, anchors, or interactive events. The materials
are existing registry families with local candidate colours; no new renderer
or global sky change is involved.

## Rebuild and evidence

From the repository root, with Blender 5.1.2 installed:

```text
"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" --background --factory-startup --python tools/blender/recipes/distant_scenery.py -- --source C:\Users\josep\.codex\worktrees\6d7d\Hichaukitoden\projects\hichaukitoden-game\assets\authoring\environments\st_maria_cortico.blend --out-dir out/cortico-distant-scenery
```

The command writes a standalone library, a scratch study blend, three
Blender-only west/centre/east frames, and a provenance manifest under
`out/cortico-distant-scenery/`. The source blend is opened for inspection and
is never saved. The frames contain a neutral review actor and use a
camera-follow review framing so all three positions are readable. The study
camera is a local clone of the pilot preview camera, preserving its source eye
and lens while applying the canon town pitch `-17.5` degrees as the equivalent
Blender `+17.5` degree rotation for this +X/-Z basis. A local Blender-only
principal-point shift keeps the adopted geometry readable; the adopted camera
object is not edited. These are scale and composition studies, not runtime
proof. The manifest records the source hash, pilot commit, camera convention,
depth order, and coverage claim.

## Explicit integration request

The pilot owner should import or append the `SCENERY_CANDIDATE` collection from
the candidate library/study into the adopted `st_maria_cortico.blend`, review
the actual source camera at west/centre/east positions, and save the source by
an explicit owner action. Before export, the owner should:

1. place the pieces under a child collection of `TH_SOURCE` (for example
   `40_DISTANT_SCENERY`), retaining their authored world transforms;
2. change only the accepted pieces' `sr_export` to `True` and keep
   `sr_preview_only`/`sr_explicit_import_only` as provenance flags;
3. leave all pieces out of `TH_COLLISION`, `TH_ANCHORS`,
   `TH_PREVIEW_ACTORS`, and gameplay data;
4. run scene-contract preflight and the pilot's exterior exporter, checking
   the emitted OBJ/MTL uses the expected material groups and that no scenery
   object was skipped by lane filtering;
5. inspect the exported package in Classic and Wide at west/centre/east and
   exercise the existing traversal/door/NPC proof. The pilot owns any runtime
   integration change and all final acceptance.

The exporter currently includes every `TH_SOURCE` descendant with
`sr_export=True` in the beauty bake, so explicit import and flagging is the
semantic boundary. Opaque meshes avoid the untested cutout-alpha bake path,
but the current bake still has a known atlas-transfer/circular-image warning
history; the export log and package must be reviewed rather than inferred from
the `.blend`. The candidate does not address the separate fixed-lane camera
tracking question or the global sky panorama. If runtime evidence exposes
camera-space layering, atlas allocation, or horizon issues, this candidate is
not a license to alter those systems silently.
