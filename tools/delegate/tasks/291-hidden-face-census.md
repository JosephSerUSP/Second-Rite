# Goal-mode brief — hidden-face census for #291

Work in `D:\Antigravity\Hichaukitoden`.

**Read completely before starting:** `tools/delegate/GOAL-MODE-PREAMBLE.md`,
`AGENTS.md`, `docs/reports/editor-3d-workspace-spike-2026-08-10.md`, and issue
#291 including its comments. Follow the preamble's safety rules throughout.

## Objective

**Measure**, per map, how many faces the map compiler currently emits that no
player camera can ever see. Turn the standing estimate — "somewhere between a
quarter and a half of wall faces" — into a number.

This is a **measurement task. Implement no culling.** Do not change emitted
geometry, do not alter the renderer, do not modify any golden reference. The
deliverable is evidence that tells the owner whether #291 is worth prioritising.

## What counts as never-visible

Classify each emitted face into exactly one bucket:

1. **`sealed`** — a wall-cell side face whose neighbouring cell is also a solid
   wall. Sealed inside the mass; unreachable by any camera.
2. **`exterior`** — a wall face on the map boundary pointing away from the
   playable area.
3. **`visible`** — everything else. When uncertain, classify as `visible`. A
   false `visible` understates the win; a false `sealed` would justify deleting a
   face the player can see. Bias deliberately toward the safe error.

Openings and doors change adjacency: a wall face adjacent to an opening is
**visible**, not sealed. Getting this rule right matters more than any count.

Also report, separately and without classifying them as either:

- the count of **walkable-cell ceiling quads** emitted (those gated by
  `mapData.ceilingStyle ~= "sky"`);
- the count of maps using `ceilingStyle == "sky"` versus not.

These inform the authoring-profile table in #291 but are not "hidden" in the
game's own camera.

## Where the truth lives

Geometry is compiled **in-engine**, so this measurement must run in LÖVE. Do not
attempt to recompute geometry in Python or JavaScript — that is the exact mistake
#286/#287 corrected.

- `presentation/map_renderable_bundle.lua` resolves structure, compiled geometry,
  materials and provenance. Wall faces come from its `faces` list; floor and
  ceiling quads are emitted per walkable cell. This is the authority.
- `engine/model_census_review.lua` is the precedent for a deterministic in-engine
  review harness. Follow its shape.
- CLI modes are dispatched by exact token match in `main.lua` (around the
  `census-review` / `render-census-review` / `surface-crop-check` block). Adding
  a new token there is the established pattern.
- `tests/test_map_geometry_export.lua` and `tests/test_map_build_profiler.lua`
  show how existing tests drive this area.

Re-read the preamble's warning about CLI tokens: **an unknown token is silently
ignored and boots the game normally.** Assert on expected positive output.

## Deliverables

1. A committed, deterministic harness — a new CLI mode following the
   `census-review` precedent — that walks every map and emits per-map counts as
   machine-readable output. Deterministic across runs on the same commit.
2. Tests covering the classification rules, especially the opening/door adjacency
   case and the map-boundary case. Include a **negative control**: a fixture
   where a face that looks sealed is actually visible, proving the classifier
   distinguishes them rather than passing by luck.
3. A report at `docs/reports/hidden-face-census-2026-08-11.md` containing a
   per-map table (total faces, `sealed`, `exterior`, `visible`, percentage never
   visible), repo-wide totals, and the ceiling counts above. State the commit
   measured.
4. A short "what this implies for #291" section: which maps benefit most, and
   whether the win is concentrated in thick-walled maps or spread evenly.

## Explicitly out of scope

- Implementing culling or visibility profiles. That is #291's own work, informed
  by this.
- Any change to `presentation/map_renderable_bundle.lua`'s emitted output.
- Any golden recapture. If a gate goes red, that is a finding to report, not a
  reference to regenerate.
- Editor or viewport changes.

## Progress continuity

Nominated progress file: `docs/reports/hidden-face-census-2026-08-11.md`. Update
after every meaningful batch with maps processed, counts so far, test results,
defects found, and the next bounded action.

## Completion criteria

Complete only when:

- every map in the project has been measured, with none skipped silently — an
  unmeasurable map must be listed with the reason;
- the classifier's tests pass, including the negative control;
- the report is accurate and states its commit;
- G1, unit and save gates are green, demonstrating the harness broke nothing;
- changes are committed to a branch (never `main`, never force-pushed).

Do not declare completion because a pass budget ended. If the classification rule
turns out to be ambiguous for a real map layout, stop and report the ambiguity
with a concrete example rather than guessing — an inflated number is worse than
no number, because it would justify work that does not pay.
