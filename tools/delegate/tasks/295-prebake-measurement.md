# Goal-mode brief — measure the #295 release prebake on the GPU host

Work on the owner's local machine. **Take your own worktree first** — see the
preamble §5.1. Do not work in `D:\Antigravity\Hichaukitoden`.

**Read completely before starting:** `tools/delegate/GOAL-MODE-PREAMBLE.md`,
`AGENTS.md`, and PR #295 including its "Performance validation" section.
Follow the preamble's safety rules throughout.

## Objective

PR #295 adds a release-time geometry prebake. Its correctness is already
covered by tests; **its benefit is unmeasured on real hardware.** Hosted CI runs
software Mesa/llvmpipe, which cannot speak to GPU-host timings.

Produce that measurement. This is a **measurement task — change no engine code**
and do not modify PR #295. If you find a defect, report it; do not fix it here.

## The comparison

PR #295 specifies it exactly. Run it on branch `agent/issue-161b-release-geometry-prebake`,
in your own worktree:

```
rmdir /s /q "%APPDATA%\LOVE\SecondRite\geocache"
lovec . profile-map-build 8 1 1 fresh
rmdir /s /q "%APPDATA%\LOVE\SecondRite\geocache"
lovec . profile-map-build 12 1 1 fresh

node tools\export\export-game.js --target love --stage-only --output dist\prebake-profile

rmdir /s /q "%APPDATA%\LOVE\SecondRite\geocache"
lovec dist\prebake-profile\stage profile-map-build 8 1 1 fresh
rmdir /s /q "%APPDATA%\LOVE\SecondRite\geocache"
lovec dist\prebake-profile\stage profile-map-build 12 1 1 fresh
```

Wrap every `lovec` invocation in a timeout — it hangs on a modal error dialog.
Assert on expected positive output; an unknown CLI token is silently ignored and
boots the game normally.

## Report these spans separately

Do not aggregate them into one number. The expected trade is removal of
deterministic compile work in exchange for deserialization, so a single total
would hide the actual finding:

- `geometry.qemDecimation`
- `geometry.compile.total`
- `geometry.prebake.deserialize`
- GPU materialization / upload spans
- `transformLightingBounds`
- `loadToFirstUsableMs`

## Repetition is mandatory

**A single run per configuration is not a measurement.** Timing on a real GPU
host varies run to run. Repeat each of the four configurations at least 5 times
and report min / median / max per span, not a single sample.

Then answer explicitly: **is the difference larger than the spread of the
baseline's own repeats?** If it is not, the honest finding is "no measurable
change on this host", and that is a perfectly good result to report. Do not
manufacture a speedup from noise.

## Verify the prebake is actually being used

A prebake that silently fails to load would produce "no change" for an
uninteresting reason. Before trusting any timing, confirm from the staged run
that `geometry.prebake.deserialize` is non-zero and that compile work actually
fell. If the staged run looks identical to the baseline in *every* span, treat
that as a likely load failure and investigate before reporting.

This is the measurement's own negative control. State the result of this check
in the report either way.

## Deliverable

`docs/reports/prebake-profile-<date>.md` containing:

- the four configurations, with min/median/max per span across repeats;
- the host and commit measured;
- the prebake-was-used check and its outcome;
- a plain statement of whether the prebake demonstrably helps on this host, is
  neutral, or is inconclusive — and if inconclusive, what would settle it.

## Explicitly out of scope

- Modifying PR #295 or any engine/exporter code.
- Golden recapture of any kind.
- Drawing #161 conclusions. #295 itself states no #161 speedup is claimed; do
  not create one.

## Progress continuity

Update the report after each configuration completes: commands run, raw
timings, anomalies, next bounded action.

## Completion criteria

Do not declare the goal complete merely because a pass budget ended.

Complete only when all four configurations have at least 5 repeats each, the
prebake-was-used check has a stated outcome, the report distinguishes signal
from run-to-run spread, and the work is committed to a branch.

If the export step or the staged run cannot be made to work, report that as the
finding with the exact failure — a blocked measurement is useful information
about the release path, and far better than a fabricated number.
