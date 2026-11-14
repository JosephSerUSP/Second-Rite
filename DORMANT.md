# Dormant since 2026-11-13

Jo has paused Hichaukitoden (Thestra + the Second Gate Project) indefinitely. This
file records the state it was left in and how to pick it back up. Everything else in
the repo ([`AGENTS.md`](AGENTS.md), [`docs/SPEC.md`](docs/SPEC.md),
[`docs/ENGINE-STATE.md`](docs/ENGINE-STATE.md)) still describes the code accurately; only
the *workflow* around it was shut down.

## State at shutdown

- **main** is `5798bcb4` (2026-10-11, #1503) plus this dormancy commit, tagged
  `dormant-2026-11-13`. CI gates G1–G4 were green on it.
- **G5 was red on main** (#1617, #1605, #1454: 79/161 classic and 39/44 wide frames
  differ, suspected selective-AA change). Unresolved. Do not recapture goldens without
  investigating first (see AGENTS.md and the `second-rite-golden-gates` skill).
- **Pull requests:** none open. 35 empty Jules report PRs were closed and their branches
  deleted. 115 PRs with real work were closed **unmerged** with the label
  [`parked`](https://github.com/JosephSerUSP/Second-Rite/pulls?q=label%3Aparked); every
  branch was kept. None was verified for merge (G5 red). Biggest stacks: stale item
  models (`codex/stale-item-models-*`), Parasite Eve Day 1 lab (`agent/pe-day1-*`), the
  Hospital slice (`codex/hospital-slice-start`), and Jules scene/creative benchmarks
  (A001–A004, B001–B008, C001–C003, D002–D003).
- **Issues:** about 175 open, left as the backlog. The active epics at shutdown were
  #1422 (PE Day 1 reference lab), #1463 (PE Day 4 Hospital slice) and #1473 (drain the
  PE Day 1 stack).
- **Branches:** every branch with commits not on main is on origin. Local-only branches
  were pushed under their own names (or `parking/local/<name>` if that failed);
  detached worktree heads not already on origin went to `parking/<worktree>`.

## Automation that was switched off

| What | Where | How to turn it back on |
|---|---|---|
| Daily "Cleanup + Review" Claude task (G5 verify, Jules triage, PR review) | Claude desktop app → Scheduled tasks (`review`) | Re-enable it there |
| Daily branch-hygiene census Action | `.github/workflows/branch-hygiene.yml` | `gh workflow enable branch-hygiene.yml` |
| Jules daily audits and creative-lab runs | jules.google.com | Gone: Jules went read-only and shuts down on 2026-12-31. No schedules remain |

## Work kept off GitHub

Uncommitted work from the primary checkout and every worktree was copied, not pushed
(much of it is large generated art), to **`D:\Antigravity\Hichaukitoden-parked\`**. Each
folder has a `MANIFEST.txt` (worktree, branch, HEAD, file list), a `tracked.patch`
(`git diff --binary HEAD`) and the changed or untracked files under `files/`.
`park-log.txt` and `branch-push-log.txt` log every push, copy and removal.

Largest items: `main-checkout` (St. Maria layout candidates, about 690 MB), `room3-3d`
(Passage House room 3 environment work), the two NPC sprite gauntlets, and
`Hichaukitoden-issue-1088` (walk-profile editor). Git-ignored files (build outputs,
`out/`, `node_modules/`) in removed worktrees were not kept; they are regenerable.

The cleanup is reproducible: [`tools/dormancy/park_worktrees.sh`](tools/dormancy/park_worktrees.sh)
(dry run by default, `--apply` to act).

## How to resume

1. `git pull`, then `npm ci`. Make sure `effekseer_shim.dll` is current
   (`tools/effekseer/check-provenance.ps1`).
2. Run G1–G5 per AGENTS.md. Resolve the G5 red first; everything else has been waiting on it.
3. Pick work from the open issues or reopen a `parked` PR. Rebase it on main and re-gate
   it. Expect conflicts: most were already behind main at shutdown.
4. Restore parked local work by applying `tracked.patch` or copying from `files/` in the
   matching folder under `D:\Antigravity\Hichaukitoden-parked\`.
5. Re-enable whatever automation from the table above is still wanted, then delete this
   file and its pointers in AGENTS.md and README.md.
