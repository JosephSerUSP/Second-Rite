# Task — batch item models three ways, and have them judged blind

## Goal

Produce item models at scale using the new parts vocabulary, and find out
**whether the vocabulary actually helps** by having the results scored blind
against two other arms — including the existing batch-produced model as a
hidden control.

The deliverable is not a finished item database. It is **evidence about an
authoring method**, plus whatever good models fall out along the way. If the
blind scores say composition does not beat a single profile, that is a real and
useful result: report it, do not bury it.

Work in bounded passes of 10 items. Surface a contact sheet after every pass.

## Read first, in full

- `tools/delegate/GOAL-MODE-PREAMBLE.md` — the standing safety contract. Read it
  completely before touching anything. It is not optional and it is not
  summarised here.
- `AGENTS.md`
- `tools/asset-production/parts.py` — the authored form vocabulary
- `tools/asset-production/lathe.py` — the primitive underneath it
- `tools/asset-production/build_food_cohort.py` — a worked example of a cohort
- `tools/asset-production/check_item_models.py` — the corpus gate
- `engine/item_model_sheet.lua` — the contact sheet renderer

## Current truth to establish before changing anything

Verify each of these yourself. Do not take this document's word for them.

1. `python tools/asset-production/check_item_models.py --report` prints
   `ITEM MODELS OK` and lists `duplicate_geometry` groups.
2. `python tools/asset-production/build_food_cohort.py` runs clean, and
   `python -m unittest discover -s tools/asset-production/tests -p "test_lathe.py"`
   passes.
3. `lovec . item-sheet tools/asset-production/food-cohort-items.txt probe.png`
   prints `ITEM SHEET OK`. Note where it says the file was written: the LOVE
   **save directory**, not the repo. You must copy sheets out of there.
4. `tests/test_model_census.py` fails to import `mesh_recipe` in a fresh
   checkout. Pre-existing, out of scope, not a finding.

## Owner decisions (do not revisit)

- **Curry and Stew are excluded.** The owner hand-refined them. Never regenerate
  or overwrite `curry.obj` or `stew.obj`.
- The point is authoring capability, not database coverage. Stopping early with
  good evidence beats grinding through every item.
- Models are judged by eye on contact sheets. The corpus gate is a floor, not a
  measure of quality.

## Cohort selection

Derive cohorts mechanically, never by taste:

```
python tools/asset-production/check_item_models.py --report
```

Take `duplicate_geometry` groups — items that currently share one mesh — and
work through them largest first, 10 items per pass, skipping Curry and Stew.
Target 60 items total. Stop earlier if you hit the stop conditions below.

## The experiment: three arms per item

For every item in a pass, produce three renders:

| Arm | What it is |
|---|---|
| **A** | Composed from `parts.py`: at least three distinct part calls merged together |
| **B** | A single `lathe.lathe()` profile, no `merge`, no composition |
| **C** | The existing batch-produced model, untouched — a **hidden control** |

Arm C matters most. A blind reviewer scoring the current models tells us what
the scores actually mean; without it, A and B are numbers with no scale. Never
tell the reviewer which arm an image came from.

### Order of operations, so arm C survives

Arm C is the model already on disk, so **render it before you overwrite
anything**:

1. Render the pass's items as they currently are → arm C images.
2. Write your arm A models over those `.obj` paths, render → arm A images.
3. `git checkout -- assets/models/items/` to restore, write arm B, render.
4. Restore arm A as the final committed state.

This is the one place you are explicitly authorised to write over existing files
under `assets/models/items/`, and only inside your own worktree, and only for
the items in the current pass. Run `git status` before and after each step.
Never touch `assets/models/matcaps/`.

You are **not** authorised to edit anything in `data/`. Items already point at
these paths; you are replacing file contents, never rewiring the database.

## The blind review sub-agent

Write `tools/asset-production/blind_review.py`. It is a deterministic script you
then run — do not do the reviewing yourself in conversation, and do not
hand-write scores.

- Input: a directory of rendered PNGs plus a manifest mapping each image to its
  **item name** and its **arm**.
- The reviewer prompt receives the image and the item name. It never receives
  the arm, the file path, the recipe, or any sibling images. Shuffle before
  sending.
- Model: **`gpt-5.6-luna`** via `OPENAI_API_KEY`, already set in the
  environment. It is vision-capable — this was verified by sending it an image
  and getting a correct answer, not assumed — and it is cheap enough for a few
  hundred single-image calls. Record the model id in every row anyway: a score
  is only comparable against scores from the same judge.

  Note that this makes the reviewer the same model family as you. That is fine
  for *blind* scoring, because it never sees which arm produced an image, but
  it means the scores are one model's taste and not a fact about the art. Say
  so in the final report.
- Rubric, each scored 1–5 with one sentence of justification:
  1. **Recognisable** — does this read as the named object?
  2. **Silhouette** — is the shape clear and distinct at a glance?
  3. **Craft** — does it look deliberately made rather than generic?
- Output: append-only JSONL at `tools/asset-production/blind-review/results.jsonl`
  with image id, item name, arm, scores, justification, model id, timestamp.

**Do not write anything into `tools/asset-gen/reviews/ratings.json`.** That is
the owner's own rating store and it has been destroyed twice.

After each pass, print the running mean per arm. That table is the actual
result of this task.

## Surfacing progress — required every pass

The owner is away and wants to follow this from the chat. After **every** pass:

1. Build a filter list of the pass's item names, one per line.
2. `lovec . item-sheet <that list> pass-<N>.png` (wrap `lovec` in a timeout).
3. Copy the PNG out of the LOVE save directory into
   `tools/asset-production/blind-review/sheets/` in your worktree.
4. **Display the contact sheet in the chat** and print its absolute path.
5. Print the per-arm score table so far, and the next bounded action.

A pass that produced no visible sheet did not happen. Do not batch several
passes and surface one sheet at the end.

## Verification

Runnable here:

```
python tools/asset-production/check_item_models.py --report
python -m unittest discover -s tools/asset-production/tests -p "test_lathe.py"
python -m unittest discover -s tools/asset-production/tests -p "test_item_model_corpus.py"
timeout <n> lovec . validate        # expect VALIDATE OK
timeout <n> lovec . unittest        # expect ALL UNIT TESTS OK
```

Every new model must clear the corpus gate. When a replaced item stops
reproducing a baselined violation, remove **only** those entries from
`item-model-baseline.json`, and remove the item from `legacyItems` so it is held
to the strict silhouette bar. Never run `--write-baseline`; show the diff.

### G5 will go red. Leave it red.

Replacing item models changes the item and shop preview frames. That is
expected. **Do not recapture golden screenshots** — it is an owner-signed action
and the owner will handle it. Report which frames differ and confirm the diffs
are confined to the model preview panel. Recapturing to make a gate green is the
worst thing you can do here.

## Explicit non-goals

- No Stable Diffusion, Forge, matcap generation, or GPU work.
- No changes to `presentation/`, `engine/`, `main.lua`, or any shader.
- No changes to `data/`.
- No new material ids in `tools/asset-language/materials.json`.
- No world props, maps or editor work.

## Stop conditions

Stop and report, rather than continuing, when any of these is true:

- 60 items are done;
- three consecutive passes show arm A not beating arm C on the mean of
  **Recognisable**, since at that point the method is the finding;
- the corpus gate or the unit suite goes red for a reason you cannot explain;
- you find yourself about to do anything the preamble forbids.

## Delivery

- Your own worktree and branch, per the preamble §5.1. Never the primary
  checkout. Never push to `main`.
- Keep `tools/asset-production/blind-review/PROGRESS.md` updated every pass:
  commands run, items done, per-arm means, failures, concerns, next action.
  Assume you will lose everything not written down.
- Small local commits as coherent work verifies. Do not commit rendered sheets
  or JSONL under a gitignored output root — keep them where the brief says.
- Final report must separate what you **observed by running it** from what you
  believe, and must state plainly if arm A did not win.
- Sign per `tools/delegate/AGENT-PROVENANCE.md`.
