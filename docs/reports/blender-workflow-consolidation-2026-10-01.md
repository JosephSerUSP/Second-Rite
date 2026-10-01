# Blender workflow consolidation and session handoff

Snapshot: branch `codex/passage-house-courtyard-candidate`, scene revision 18 at
`6c1c4695`. PR #1296 is a draft stacked on open renderer PR #1294. Earlier ground,
neutral-exposure and alpha fixes merged as #1289/#1291/#1292. This handoff does
not promote the candidate, rewrite a source or claim owner PLAYED acceptance.

## Retain as reusable workflow

The maintained environment pipeline uses Cycles selected-to-active surface
baking, temporary evaluated-source batching with preserved coordinates, explicit
GPU/CPU selection and neutral exposure. `render_profiles.py` is the live quality
authority: draft/lookdev/export 64 samples, review 128, atlas 1024. Atlas denoising
is fast and chart-isolated. Saved courtyard render/viewport quality matches export.
Approximately 60 seconds is a measured target, not a hard deadline.

Connected volumes and reusable window/door assemblies separate rich source
construction from structural receivers. Winding, open-sheet semantics, conservative
culling and sampled source/receiver correspondence are checked independently.
Guarded pixel-corner UV alignment and a 0–1 camera-area allocation blend improve
texture use; #877 remains open for richer view-envelope/anisotropic treatment.

The repository-local material selection preserves upstream downloads, hashes,
licenses and dependencies separately from adaptations. Acquisition is deliberate;
offline checks/builds do not fetch. No global asset-library registration or saved
Blender preference change is required. Existing scaffold/adopted authority remains
binding; guard against owner edits before replacing a scaffold.

Runtime-resolved review poses, bounded tracking, edge exits without wall approach,
and Classic logical optics in Wide correct prior review/runtime disagreement.
Map 32 remains a staged Cortico–courtyard–lodging annex. Its profile is
`(0,0), (2,0), (8,0.30), (12,0.30)`; local datums align doorway landings without
flattening Cortico. Geography extraction reports possible transfers, not condition
reachability or an inferred island-wide elevation system. The padaria contradiction
is recorded under #1016; undocumented datum relationships remain undocumented.

## Do not retain as an accepted visual template

Owner feedback after revision 18: the continuous foreground forms are disliked;
occluding elements should be separated rather than continuous, and moving the
basin back made the bottom flatter. The full frame behind the menu needs authored
depth and interest. Added geometry, paving patterns and a hollow basin did not
establish a successful composition. Keep this experiment as evidence, not a
foreground standard or finished environment. No further scene edits accompanied
this consolidation. Issue #1308 records the deferred composition work and owner
review criteria independently from #1301's bake correspondence work.

Source and runtime are inspected separately because a plausible game frame can
conceal missing roofs and displaced shading. More samples cannot restore missing
geometry or fix wrong bake rays. #1301 retains window/cistern correspondence work.
Future visual work should use distinct foreground masses with negative space,
inspect their silhouettes from the actual camera, and compare the whole frame
with and without UI before committing to source detail.

## Evidence entry points

All candidate paths below are relative to
`projects/hichaukitoden-game/assets/authoring/candidates/passage_house_courtyard/`.

| Evidence | Location | Interpretation |
|---|---|---|
| Latest package/source metrics | `review/measurements.json`, `package/` | Revision 18, not accepted art |
| Foreground before/after | `review/camera-aware/foreground.html` | Revisions 17/18, seven positions, Classic/Wide, with/without UI |
| Allocation controls | `review/camera-aware/compare.html`, `comparison.json` | Matched revision 16 bias 0/0.5/1; later scene separately labelled |
| Independent final surfaces | `review/camera-aware/revision18/surfaces/` | Source beauty/clay and runtime clay/atlas |
| Actual bake budgets | `review/cycles-bake-study/` | Same study geometry, roughly 30/60/120 seconds; not preview timing |
| Geography | `review/shipping-geography.json` | Authored transfers, anchors and local profiles |

Historical reports and controls retain their original measurements. In particular,
`central-cycles-environment-export-2026-10-01.md` records the earlier 128-sample
policy; use `tools/blender/ENVIRONMENT-RENDERING.md` and live code for current policy.
The review archive contains 692 files before this handoff; it is preserved, not
pruned or recaptured. The offline HTML viewers work from their relative files.

Latest source: `assets/authoring/environments/passage_house_courtyard.blend` inside
the game Project, registered as scaffold. SHA-256:
`91077aeb5b9b51fd6ab8dd95a973326cedaf412ba5b7d468d21d7a184a95a0a3`.
Evaluated whole-source beauty: 222,522 triangles; exported envelope: 6,137 triangles.
These are different populations, not a pure decimation ratio. Atlas occupancy is
62.67%; final whole-process export 58.50 seconds, not a cold/warm repeat claim.

## Resume without shipping promotion

From the repository root, check library hashes/dependencies with
`python tools/blender/vendor_assets.py check` and source authority with
`python tools/blender/environment_sources.py --check`.

Stage the existing candidate using
`node tools/blender/stage_courtyard_candidate.js --output out/courtyard-next-review`
(the directory must not exist). Launch
`& "C:/Program Files/LOVE/lovec.exe" out/courtyard-next-review/game` in PowerShell.
Capture through `python tools/blender/capture_courtyard.py --game-root
out/courtyard-next-review/game --output out/courtyard-next-frames`; add
`--unobstructed` with a separate output for the whole world view. Run staged units
through the prescribed PowerShell wrapper, never from the repository as a game.

Recorded final G1, staged units, source/town checks, editor profile/history/geography
checks and fresh-source parity pass. Seven native Effekseer assertions were
unexercised; absolute G5 has documented baseline mismatches. No goldens were
recaptured. Consolidation documentation checks are separate from those historical
runtime results. Source/runtime visual parity and owner PLAYED acceptance remain
open. Shipping integration must update the owning authored map/generator authority.

Before a tooling-only merge, assess its diff separately from candidate content and
preserve the stacked PR dependency. This handoff does not split branches or assert
that all reusable changes are isolated in #1294; many reside in #1296.
