# ORCHESTRATION — the integrator's runbook

Audience: whoever is holding the **orchestrator** seat — evaluating work
produced by executor agents (Jules, Antigravity, Zoo Code, a human, or a
future Claude session) and integrating the winners. This role is
deliberately model/tool-agnostic: it needs a shell, git, the game runtime,
and (for editor work) a browser. Any capable agent can run it from this
doc — that portability is the point.

> **Status check, 09.08.2026 — the round machinery described here is dormant.**
> Verified: no `o3/*` or other candidate branches exist; `PLAYBOOK.md` and
> `FEEDBACK.md` are gone; the per-round briefs and SPEC it cites live under
> `docs/archive/plans/`, which AGENTS.md marks **never authoritative**. Current
> practice is scoped work on its own branch, integrated on `main` and gated by
> CI. Sections 2, 4, 5 and 9 are still live and worth reading — judging a diff,
> the bug classes, golden-master discipline, repo traps. Sections 0, 3, 6 and 8
> describe a workflow nobody is running; do not follow them because they are
> written in the present tense. Retiring or splitting this file is an owner
> decision that has not been taken.

---

## 0. The shape of the workflow

- One **integration branch** per round (e.g. `fable-5-overhaul-3`). It must
  stay green on every gate at every commit.
- Each task has a **brief** in `docs/archive/plans/<round>/briefs/<ID>.md` with an
  acceptance checklist. Briefs are self-contained and tool-agnostic.
- Executors work on **candidate branches** `o3/<id>-<short-name>[-<suffix>]`
  cut from the integration branch. Cloud executors (Jules) may push several
  candidates per task; local ones (Zoo Code, Antigravity) usually push one.
- The orchestrator **evaluates → picks a winner → merges → re-gates → pushes
  → deletes all candidate branches** (winners and losers).
- Executors NEVER merge into the integration branch and never touch `main`.
  Merging is the human-gated integration step. That is this role.

## 1. The gates (run all that the change could affect)

- **G1 — validate:** `& "C:\Program Files\LOVE\lovec.exe" . validate`
  (Windows) / `love . validate` (Linux). Must end `VALIDATE OK`. The line
  `[formula] error in 'os.time()'` is an EXPECTED sandbox negative-test, not
  a failure.
- **G2 — golden:** run `love . validate golden`, extract the lines between
  `GOLDEN BEGIN` / `GOLDEN END`, split them by the `battle|<key>|name|` header
  and diff each against `tools/golden/battle_<key>.log` after normalizing line
  endings (`tr -d '\r'`). Must be byte-identical. Fixtures are authored in
  `data/goldenBattles.json`, so battle coverage grows without engine edits.
  **NEVER regenerate a golden log to make a red diff green.** Regenerating it
  is a deliberate, reviewed, local-only action (see §5). `tools/golden/check.*`
  do this comparison for you.
- **G3 — golden UI:** `tools/golden/check-ui.ps1`. Per-scene UI trace
  identity for every scene; same never-regenerate-to-go-green rule as G2.
- **G4 — engine state:** `tools/golden/check-state.ps1`. Confirms
  `docs/ENGINE-STATE.md` still matches the live engine. **Unlike G2/G3, a red
  G4 is a stale doc, not a regression** — run `tools/golden/capture-state.ps1`
  and commit the result.
- **G5 — screens:** `tools/golden/check-screens.ps1`, ends `SCREENS OK`.
  Rendered frame byte-identity. The **only** gate that can see the world view,
  so a renderer change can pass everything above and still be badly wrong.
  Never-regenerate rule as G2.
- **G6 — editor screens:** `tools/golden/check-editor.ps1`, ends
  `EDITOR SCREENS OK`. Rendered frame identity for every editor tab and modal;
  read-only by construction. Never-regenerate rule as G2.
- **unit / save:** `lovec . unittest` → `ALL UNIT TESTS OK`; `lovec . savetest`
  → `SAVETEST OK`. (The save token is `savetest`, one word — an unrecognised
  CLI token is ignored and boots the game instead of erroring, which reads as a
  pass if you are grepping for failures.)
- **Editor console check (not a gate):** `node tools/editor/server.js` (port
  8080), exercise the changed UI, confirm **zero console errors** and that a
  save round-trips. G6 sees pixels, not console errors, so this still adds
  something. Remember the editor writes straight to `data/*.json` —
  `git diff data/` afterwards.

Gate numbering follows `docs/SPEC.md` §3, which is the authority. (Before
24.07.2026 this file numbered the editor check "G3" while SPEC.md used G3 for
golden UI — if you see "G3" meaning the editor in any older document or script,
it predates this fix.)

Re-run the relevant gates **after each merge**, not just per candidate — a
candidate green in isolation can break once combined.

## 2. Picking a winner

Order of judgment:

1. **Checklist compliance** — does it meet every box in the brief's
   Acceptance section? Verify, don't trust the PR text.
2. **Footprint vs brief** — diff size should roughly match the brief's
   scope. A ~1000-line diff for a "focused selector" is a red flag: usually
   it reformatted a whole data file or rewrote unrelated code. Reject that
   churn even when it "works" — it makes review impossible and buries risk.
   (Real case: five C1 candidates reformatted all of `engine.json` for the
   same behavior a disciplined 140-line one delivered.)
3. **Code quality** — matches surrounding style/indentation, reuses existing
   helpers, no dead code, no needless new dependencies.

You may merge a candidate **plus your own fixes** — that is normal. Several
C-round winners needed a repair before merging (see §4). Note the fix
honestly in the merge message.

## 3. The test-merge procedure

```
git fetch --prune
git checkout -b _t_<id> origin/o3/<candidate>
git merge <integration-branch> --no-edit      # pull latest integration IN
# run gates: G1, G2/G3 (if engine/data touched), G4 (always), editor check (if editor touched)
```
If good, merge into the integration branch with `--no-ff` and a full commit
message (§7), then `git branch -D _t_<id>`. Verifying on `_t_<id>` (candidate
+ current integration) catches conflicts the candidate's own base hid.

## 4. Bug classes worth actively checking

These are the real defects caught this project — check for them by reflex:

- **Force-path revert.** A modal that restores a snapshot on close must gate
  the restore on `!force`, or the Apply/Save path (which calls `close(true)`
  while still dirty) silently undoes the commit. (C6)
- **Reformat churn / scope creep.** See §2.2.
- **Empty-object churn.** UI that does `x.thing = x.thing || {}` on render
  stamps empty objects onto the payload; every save then rewrites files with
  noise. Materialize only on real edit; strip empties at save. (C11)
- **Bare-key vs path resolution.** Some references are bare keys resolved to
  a path at load (e.g. portrait key → `assets/portraits/<key>.png`). A
  preview that does `'/' + value` 404s for those. (C8)
- **Hiding vs editing.** When you hide deprecated/filtered options from an
  ADD list, existing records using them must still be editable — the type
  must be re-injected for the edit dialog (`ensureId` pattern). (C1, C2)
- **Alias determinism.** A consolidated command aliasing old ones must keep
  event emission identical or G2 breaks. Verify golden, not just G1. (C2)

## 5. The golden-master discipline

`tools/golden/battle_*.log` are the equivalence proof for behavior-preserving
refactors. Rules:
- Behavior-preserving tasks must leave it **byte-identical** (G2).
- A task that *intentionally* changes battle behavior (bug fix, rebalance)
  regenerates it via `tools/golden/capture.*`, and its PR must include the
  before/after log diff with a line-by-line justification.
- Such tasks are **local-only with human review** — never delegated to a
  cloud executor that would regenerate the log out of sight. (C5)

## 6. Verification-debt protocol

An executor that cannot run a gate (e.g. no browser for the editor check)
declares it unchecked in the PR checklist with the reason. The orchestrator
then **runs that gate during evaluation** before merging — debt is cleared
at integration, never merged as-is. A local executor (Zoo Code) that *can*
run them all should run and report them; if it doesn't, treat the missing
ones as debt and check them yourself.

## 7. Merge commit / PR checklist

End every integration merge message with the SPEC Ground-rules checklist,
filled honestly, plus attribution:

```
Gates: [x] G1 validate [x] G2 golden [x] G3 golden-UI [x] G4 engine-state
[x] G5 screens [x] G6 editor-screens [x] unit [x] save
[x] editor-console (if editor touched).
Unchecked = verification debt; reason: <…, or "none">.
Take the gate roster from SPEC §3, not from this template — it has been
out of date before, and a template that lists fewer gates than exist
certifies a pass nobody ran.
Spec deviations: none / <list>.
Files touched outside the brief's list: none / <list>.

Co-Authored-By: <model> <noreply@anthropic.com>
```
State which candidate won and why, and any fix you applied before merging.

## 8. Cleanup

After the winner is merged and re-gated:
```
git push origin <integration-branch>
# delete ALL candidate branches for the task, winners and losers:
git branch -r | grep 'o3/<task>' | sed 's#origin/##' | xargs git push origin --delete
```
Late candidates can arrive mid-session — re-`fetch --prune` at the end.
Never blind-delete an **unevaluated** candidate for a task you haven't done;
keep it for its own pass. Delete only superseded/evaluated branches.

## 9. Traps specific to this repo

- **Editor Save reformats data files.** "Save Database" rewrites every
  `DATA_FILES` entry via `JSON.stringify(…, 2)`, which reformats compact
  hand-authored JSON (esp. `engine.json`) and can auto-add empty objects.
  Before reverting "dirty" data files, check **content vs formatting**: parse
  both sides and compare normalized JSON; only real content changes matter.
- **New data files go in BOTH manifests:** `DATA_FILES` in
  `engine/server.lua` AND `tools/editor/server.js`.
- **Registries drive the editor + validator:** new effect types / trait
  codes / commands / meta keys are data in `engine.json`, not Lua constants.

## 10. Model routing for this seat

Split by kind of work, not by model name: a fast/cheap model for the mechanical
passes (diff triage, running gates, cleanup), and the strongest model available
for the judgment calls — architecture, anything touching the golden log,
ambiguous merges, and the subtle bug classes in §4. Model names date faster than
this document is revised (it named Opus 4.8 for months after that stopped being
the frontier), so read the tiers, not the names. The gates are what make a
cheaper model safe here: a wrong call fails a gate loudly rather than sneaking
in.
