# Goal-mode preamble — read this before any long-running local run

This file is the standing safety and operating contract for **unattended,
long-running agent work on the owner's local machine** (ChatGPT Codex goal mode).
Every goal-mode brief for this repository should begin by requiring that this
file is read in full.

It exists because long-running plus local plus unattended is the highest-risk
combination in this project's setup, and this repository has already lost owner
work twice to careless automation.

## 1. Why a weak model is the right model here, and what follows

Goal mode runs long, so it runs on a cheap model. That is an economic decision,
and it has a design consequence you must respect:

> **Drive deterministic scripts. Do not reason where a script can decide.**

Prefer a committed script, a grep, a test, or a query over your own judgement,
every time. Where a task genuinely needs judgement, it does not belong in goal
mode — stop and report rather than guessing at scale.

Persist progress **outside your context**: files, databases, a progress report.
Assume you will lose everything you did not write down.

## 2. Never touch

Read-only unless a brief *explicitly and specifically* says otherwise.

- **Golden references** — `tools/golden/screens/`, `tools/golden/screens-wide/`,
  `tools/golden/editor-screens/`, and the reference `*.log` files. Recapturing a
  golden is an **owner-signed action**. A red gate is a regression until proven
  otherwise; never regenerate a reference to make a gate green.
- **`data/*.json`** — the editor dev server live-writes authored data straight
  through. Never edit authored data while an editor server is running, and never
  assume a `data/` diff was yours.
- **`tools/asset-gen/reviews/ratings.json`** — the owner's rating store. It has
  been destroyed twice. Do not move, stash, regenerate or "clean" it.
- **`assets/**`** — may contain hand-edited art. Never run an asset generator
  over existing assets without an explicit instruction naming the files, and run
  `git status` first.
- **`docs/reports/**`** — historical records of past work. Do not rewrite history
  to match present naming or present state.
- **`data/lore.json`** — in-world fiction. "The Second Rite" is a ritual in the
  setting, not the product name. See #288.
- **Generated `.mtl` headers** under `assets/models/items/` — inert build output.

## 3. Never do

- **Never `git push --force`**, and never push to `main`. Work on a branch.
- **Never `git stash`.** The stash is global, not branch-scoped, and stashing a
  live-written file has previously split a data store into two partial sets.
  Copy aside instead.
- **Never add a git remote.**
- **Never use `sed -i`** on tracked files. It silently converts CRLF to LF, so a
  two-line change arrives as a whole-file rewrite and buries the real diff. Make
  targeted edits.
- **Never claim a gate result you did not observe.** This is the single worst
  failure available to you. If you could not run it, say so plainly.
- **Never `cd` into the primary checkout** to run something for a branch that
  lives in another worktree.
- **Never delete or regenerate `effekseer_shim.dll`** without backing it up
  first. It is gitignored, there is no fallback binary, and rebuilding requires
  MSYS2 + MinGW.

## 4. Environment traps that will silently fake success

- **An unknown CLI token is ignored and the game boots normally.** Tokens are
  matched exactly in `main.lua` (`savetest`, not `save-test`). A typo does not
  error — it launches the game, which reads as a pass to anything grepping for
  `FAIL`. Always assert on the expected *positive* output, never on the absence
  of failure.
- **`lovec` hangs on a modal error dialog** when Lua fails to parse, and there is
  no `lua`/`luac` on this machine to syntax-check first. Always wrap `lovec` in a
  timeout.
- **A worktree does not have `effekseer_shim.dll`** — it is gitignored. Copy it in
  before running any gate from a worktree.
- **A red G5 classic short-circuits the gate**, so the wide surface and the crop
  invariant never run. "0 differing" for a step that never executed is not a pass.
- **The editor dev server writes to `data/`.** Always `git diff data/` after any
  browser interaction.

## 5. Operating rules

- Work in **bounded passes**. After each meaningful batch, update the brief's
  nominated progress file with: commands run, units advanced, pending and error
  counts, test results, fixes made, concerns, and the next bounded action.
- **Inspect errors before retrying.** Never build an uncontrolled retry loop.
- Add or update a test for every implementation defect you fix.
- Make small local commits when a coherent change is verified. Do not commit
  generated state, gate records, or anything under a gitignored output root.
- Do not ask the owner to classify individual items. Collect high-leverage,
  family-level questions for a single later review.

## 6. Completion

**Do not declare a goal complete because a pass budget ended.** Complete only
when the brief's stated criteria are literally satisfied, verified by the
deterministic checks the brief names.

If genuinely blocked, perform safe diagnostics and bounded retries first. Report
a blocker only when the same blocking condition persists and no safe in-scope
work remains — and say exactly what you tried.
