---
name: second-rite-golden-gates
description: >-
  Run and triage Second Rite's golden gates (G2 battle logs, G3 UI traces, G4
  engine state, G5 screen pixels, G6 editor pixels). Use when a gate is red,
  when deciding whether a diff is a regression or machine drift, when a change
  needs gate coverage before landing, or when a reference log or screenshot is
  a candidate for recapture.
license: project
metadata:
  version: "1.0.0"
  category: verification
  tags: ["gates", "golden", "regression", "screenshots", "triage"]
---

# Golden gate triage

**Facts about the gates live in [`AGENTS.md`](../../../AGENTS.md) (the table and
the gate notes) and [`docs/SPEC.md`](../../../docs/SPEC.md) §3. Read them for
what each gate guards. This skill is only the procedure for what to *do* when
one goes red** — the part that has been re-derived by hand every time.

## The one rule that outranks everything here

A red G2/G3/G5/G6 is a **regression until proven otherwise**. Regenerating a
reference log or recapturing a screenshot to make a gate green is an
**owner-signed action**, never a step you take to unblock yourself. If triage
ends at "the machine changed," you present the evidence and ask — you do not
recapture.

G4 is the exception: red G4 means the generated doc is stale. Run
`tools/golden/capture-state.ps1` and commit it.

## Procedure

### 1. Run the gate, don't guess

```bash
powershell -NoProfile -ExecutionPolicy Bypass -File tools\golden\check.ps1
```

`check-validate.ps1` (G1), `check.ps1` (G2), `check-ui.ps1` (G3),
`check-state.ps1` (G4), `check-screens.ps1` (G5), `check-editor.ps1` (G6). The
`.sh` twins are Linux-only — on this machine always use `.ps1`.

Since #700 the repository root owns no `data/`, so a bare `lovec . <command>`
cannot run any gate. Each `.ps1` above stages the default Project through
`tools/ci/stage-project-gates.js` and removes the stage afterwards. To run
several gates against one stage — or to run `unittest` / `savetest`, which have
no wrapper — stage once and pass it in:

```bash
node tools/ci/stage-project-gates.js --output "$gateRoot"
powershell -NoProfile -ExecutionPolicy Bypass -File tools\golden\check.ps1 -GameRoot "$gateRoot"
```

A caller-supplied `-GameRoot` is never deleted by the gate.

Wrap any bare `lovec` invocation in a timeout. A Lua syntax error puts LOVE on
a **modal error window that never exits**, and the owner has had to close it by
hand more than once.

**But do not put a short timeout on G6.** It drives 46 editor states through a
real headless Chrome and takes roughly 10-11 minutes. A 10-minute timeout kills
it partway and looks exactly like a hang: the harness prints its per-step lines
only as it goes, so a killed run leaves you staring at the last line before the
capture loop. Give it 20+ minutes, and run it with `python -u` (or straight to a
file) if you want to watch progress -- piping G6 through `grep`/`tail` makes
Python block-buffer its stdout and hides the step counter entirely.

### 2. For G5/G6, measure before you look

```bash
python tools/golden/triage.py --heatmaps
```

`check-screens` / `check-editor` tell you *which* frames differ and write a
side-by-side gallery. `triage.py` tells you *how* they differ, which is what
decides the next step. Per differing frame it reports changed-pixel count,
fraction of frame, bounding box, and max channel delta, then a reading:

| Reading | Signature | What it means |
|---|---|---|
| `LOCALIZED` | small bbox, large channel deltas | Something specific moved or drew wrong. **Regression.** Find it. |
| `BROAD` | large bbox, large channel deltas | A whole surface changed — palette, layout, camera. **Regression.** |
| `DRIFT?` | ≥20% of pixels, max delta ≤8 | Candidate machine shift (GPU/driver/font/Chrome). Needs confirmation, then owner sign-off. |
| `LAYOUT` | frame size changed | Resolution or viewport change. Always real. |
| `NEW` | no reference | New coverage. Capture is expected. |
| `STALE` | matches its reference | Leftover output from an older run, not a finding. |

It is a **report, not a gate** — it always exits 0, deliberately, exactly like
`lovec <gateRoot> reachability`. Never wire it into CI as a pass/fail.

### 3. Confirm a `DRIFT?` before believing it

`DRIFT?` is the only reading that can end in "not our fault," so it gets the
highest bar. Confirm both:

- The same frames drift on a commit that **could not** have caused it (stash
  your change, re-run). Drift is indifferent to your diff; a regression is not.
- Nothing in the diff touches the renderer, fonts, layout, or asset pipeline.

A gate that goes red on exactly the scenes you just changed is not drift, no
matter how small the deltas.

### 4. Localize a regression

The bbox is the answer to "where." Map it onto the scene: the dock is the
bottom band, the context-help bar the top. Then read the frame's own name —
G5 paths are `<group>/<scene>/<NN>-after-<input>.png`, so the *first* failing
step in a sequence is the one to debug; later frames usually just inherit it.

Cross-check against the gate that should have caught it. A visual-only red with
G1–G3 green means the change is presentation-only. **G3 red plus G5 green is
suspicious** — it usually means the scene isn't in the screenshot harness at
all, which is a coverage hole, not a pass.

### 5. Beware the gate that passes too easily

A gate that goes green on the first try over code you just changed is a
**coverage question, not luck**. Confirm the gate actually exercises the path:
break the code deliberately and check the gate notices. G3 never enters the
battle presentation path (issue #196) — that class of blind spot is why this
step exists.

## Harness traps

These have each cost a real debugging session.

**All gates**
- Running a gate from the wrong worktree. `cd` into the checkout the branch
  actually lives in — `git worktree list` first. Gates read the working tree,
  not the branch name.
- `git status` before anything that writes. The editor dev server writes form
  edits **straight through to `data/*.json`**, and asset generators overwrite
  owner-hand-edited PNGs.

**G5**
- `-OutDir` is ignored; output always lands in `tools/golden/screens-actual/`.
- The IDE Run button fires in the primary worktree regardless of your shell's
  cwd.
- Secondary worktrees lack the Effekseer DLL, so effects render as nothing and
  every effect frame reads as a false regression. Rebuild with
  `tools/effekseer/build.ps1` or run G5 from the primary worktree.

**G6**
- Read-only by construction — **no step may save**, because the editor writes
  through to `data/`.
- Placeholder status text renders before the real value, so a frame captured
  too early is a false diff.
- Piping its stdout can deadlock; redirect to a file as `check-screens.ps1`
  does.
- Chrome must be findable — set `CHROME_PATH`. A CDP `Origin` 403 means Chrome
  refused the debug connection, not that the editor is broken.

## Adding coverage

New scene, tab or modal → add it to the harness in the same change, or it is
invisible to every gate. G5 scenes come from the screenshot harness; G6 steps
from `STEPS` in `tools/golden/editor-screens.py`. A tab that throws before it
paints breaks no other gate — that is precisely the hole G6 exists to close.

## Recapture (owner-signed only)

When the owner has signed off:

```bash
powershell -NoProfile -ExecutionPolicy Bypass -File tools\golden\capture-screens.ps1
```

Then re-run the check, confirm green, and commit the references **in their own
commit** with the sign-off and the evidence in the message. Never fold a
recapture into a feature commit — it hides the one thing a reviewer must see.
