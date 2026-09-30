# Handoff for Codex: the Praça ground fix and the EEVEE bake backend (2026-09-30)

Session ended early at the owner's request. Branch `claude/praca-ground-and-eevee-backend` (off `origin/main`
at 36ccf0e6, after #1283, #1285 and #1288 merged). Everything below is committed on that branch EXCEPT what is
listed under "Not done". Read `AGENTS.md` first; repo rules apply (G1, squash merges, only `gates (Windows)`
required, never `git add -A` over owner edits).

## Goal (owner's words, paraphrased)

Move the project's 3D/Blender workflows to EEVEE and retire Cycles, "it needs visual diffs"; the rooms are test
subjects, the point is improving workflow and tooling, not tuning rooms. Do not publish our own asset library;
consume published content. The owner said "Let's fix this and proceed" about #1287 (the Praça's black ground),
then asked to end the session.

## What this branch contains

1. **#1287 fix in `tools/blender/export_exterior_environment.py`.** `ARCH_square_ground` is a zero-thickness
   double-sided sheet (top and underside coplanar, plus four zero-area sides). The sealed-face cull deleted the
   top and kept a 200 x 200 m underside facing down; the Cycles bake casts along the target's normal, so the
   ground baked black (the shipped `praca` package has a black ground). Now:
   - `flatten_ground_sheet` keeps only the upward face, marks it an open surface, and is applied to the SOURCE
     object in memory as well as the copy (the exporter never saves the document). Flattening only the copy
     still bakes black: a target facing up over an unflattened source hit the underside (measured mean 0.0 vs
     0.82). Both are covered by tests, with negative controls.
   - `clip_ground_to_view` cuts the ground to what the lane cameras can see plus `--ground-clip-margin` (2 m):
     40,000 m2 became 4,681 on the real source. `--keep-full-ground` restores the old behaviour.
   - `--atlas-layout view` (default; `legacy` = old smart_project + fixed 3% ground share). Uses
     `atlas_allocation.allocate_by_view` (now takes `mirrored`/`centre`; the exterior is `mirrored=False`). The
     ground is 59.5% of the pixels of a frame. Result on the real source (EEVEE study): median texels per screen
     pixel 0.00 -> 0.85, share of pixels under one texel 79% -> 55%.
2. **EEVEE bake backend.** `tools/blender/eevee_bake.py` (`EeveeBake`, `bake_atlas`, `add_arguments`,
   `settings_from_args`); `town_environment_pipeline.run_pipeline_in_blender(..., backend="cycles"|"eevee",
   eevee=...)`; both exporters take `--bake-backend cycles|eevee` (default cycles) plus `--exposure`,
   `--probe-cells`, `--probe-samples`, `--emissive-lights`, `--fixture-lights`, `--eevee-option`,
   `--bake-supersample`. Beauty frames photograph the SOURCE meshes (joined mesh hidden), UV frames the joined
   mesh. An EEVEE package records `provenance.bake` in `environment.json`; a Cycles manifest is unchanged.
3. **Per-environment EEVEE records** in `projects/hichaukitoden-game/assets/authoring/environments/
   environment-sources.json` (`eevee` key: exposureEV, probeCells, emissiveLights, fixtureLights, eeveeOptions,
   basis), validated by `tools/blender/environment_sources.py --check`. The numbers are pilot-solved starting
   points (not sign-offs); the Praça's exposure is 0 pending the owner's choice of look.
4. **Tests:** `test_exterior_bake_source` (ground sheet, clip, view layout, Cycles ground bake + controls),
   `test_eevee_backend` (tiny room through the real room exporter with both backends),
   `test_environment_sources` (EEVEE record rules). Workflow step added in `.github/workflows/blender-item-source.yml`.
   All passed locally. Not yet run on CI for this branch.
5. Docs: `docs/asset-pipeline/BLENDER_CORE.md` (EEVEE lighting, backend, Praça ground sections); module docstring
   of `export_exterior_environment.py`.

Already merged earlier this session (context): asset library browser and in-repo SR_GroundCover library, packed/view
atlas layouts, EEVEE projection atlas, emissive companion lights (`emissive_lights.py`, pi x strength x area watts),
`light_fixtures.py` (release shadow on a housing smaller than its lamp), exterior study, reports under `docs/reports/eevee-*`.

## Not done (the next steps, in order)

1. **Install the regenerated Praça package.** A fresh package from this branch's exporter is in
   `out/praca_regen2/praca/` (gitignored, in the `pilot` worktree; regenerate with
   `blender -b --python tools/blender/export_exterior_environment.py -- --blend projects/hichaukitoden-game/assets/
   authoring/environments/st_maria_praca_modelled.blend --output <dir>`; the Cycles bake takes ~17 minutes, run it
   alone). Verified: the ground island bakes (region mean 65.9, 63% texels lit). **Do not copy the whole
   package.** The regenerated manifest's `anchors` differ from the shipped ones (`alicia_door` y 2.881 shipped vs
   4.625; `chapel_door`, `churchyard_stair`, `quay_stair` also differ), so the shipped manifest was not made from
   the current source's anchors. Install only `environment.obj`, `environment.png`, and the `bounds` and `stats`
   of `environment.json`; keep the shipped `anchors`, `collision.obj` and `environment.mtl` (the approach used for
   the shop packages in #1278). Then run the Lua suites that touch it (`tests/test_baked_environment_package.lua`,
   `tests/test_bounded_lane.lua`, via `tools/ci/run-staged-unit.ps1 -GameRoot`), G1, and photograph before/after
   with `tools/blender/photograph_room_package.py` (`--lane-y 4 12 20`). `bounds` in the manifest is only read
   by the developer navmesh overlay in `runtime/presentation/viewport_3d.lua` (`drawTownBounds`); it changes from
   +-100 to about x -13.8..46, y -27..51. Regenerating the shipped package is an owner-signed step; the owner said
   "fix this", so this is covered, but say so in the PR.
2. Open the PR (this branch is pushed; a draft PR may already exist), let CI run, merge when green. Close #1287 with it.
3. Foliage bakes near black in the Cycles atlas (undiagnosed; EEVEE atlas renders it green).
4. Make EEVEE the default for `--engine eevee` plates/atlases with the shims on; decide per environment whether to flip
   `--bake-backend` default. The owner judged EEVEE "quite satisfactory" and a good Cycles-retirement candidate.
5. The exterior is ~0.6 EV brighter under EEVEE than the Cycles atlas (facade ratio 0.64-0.68 at five held-out
   positions); ask the owner which look is intended before setting `exposureEV` in the Praça's record.
6. Open owner decisions: material specular for `sr_*` (owner said not in this pass); running
   `tools/blender/recipes/adopt_praca_ground_cover.py` on the real Praça `.blend` (#1270, not granted);
   24 orphaned `*_variant_*` dungeon model files.

## Gotchas learned

- The Write tool works where heredocs fail in this shell; files in the working tree are CRLF (autocrlf), edit with
  LF-normalising scripts and write back CRLF. Keep `.gitattributes` `-text` files as they are.
- Do not run heavy Blender jobs concurrently (earlier OOM); the Cycles Praça bake is ~4 GB and ~17 min.
- `rm -rf "$d/..."` with a shell variable is blocked; use `"${d:?}/..."`.
- A squash-merged PR deletes its branch; pushing the old branch recreates it. Branch from `origin/main` for new work.
- Per-room EEVEE tuning lives in the records above; the corridor needs `--probe-cells 4` and
  `light_threshold=0.0002` or light leaks through its ceiling shell.
- Memory files for this owner are in `C:\Users\josep\.claude\projects\D--Antigravity-Hichaukitoden\memory\`.

Agent-Signature:
  platform: Claude Code (desktop)
  model: Sonnet 5.5
  role: handoff
  task: "end of session: Praça ground fix and EEVEE bake backend"
