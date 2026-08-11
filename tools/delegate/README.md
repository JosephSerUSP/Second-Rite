# delegate — cheap external agents for bounded work

Hands a **bounded, well-specified job** to a cheap external coding agent running
in an isolated git worktree, and brings back a diff and a transcript for review.

The split this exists to enforce: the cheap agent supplies **labour**, the
reviewer supplies **judgement**. It returns evidence, never verdicts.

## Setup

The Codex *app* (`~/.codex/`) is already installed on this machine, but it does
not provide a scriptable entry point. The CLI is a separate install:

```bash
npm install -g @openai/codex
```

Then set `OPENAI_API_KEY` in your environment, and set a hard spend cap on the
provider's billing page. That cap is the real ceiling — `--timeout` here bounds
one run's wall clock and is deliberately not described as a token budget.

## Use

```bash
python tools/delegate/delegate.py run doc-status-drift --task-file tools/delegate/tasks/doc-status-drift.md
python tools/delegate/delegate.py ledger
python tools/delegate/delegate.py clean doc-status-drift --delete-branch
```

`run` creates `.codex-work-<slug>/` on branch `codex/<slug>` from `main`, runs
the agent there, then prints the transcript, the diffstat, and a line-ending
damage warning if one applies. `--dry-run` shows what it would do without
creating anything.

## Watching a run in flight

`run` buffers the agent's output until it exits, so its transcript is empty
while the job is going. Codex writes a JSONL rollout under `~/.codex/sessions/`
as it works, and `watch.py` renders it live:

```bash
python tools/delegate/watch.py           # follow the newest session
python tools/delegate/watch.py --once    # snapshot and exit
```

It prints shell commands, patch applications, agent prose, and a running
command / patch / file / token tally. Watch this rather than waiting for the
summary: the summary is a sentence the agent generated, the exec log is what it
actually ran.

## Sandboxing is explicit, not inherited

Every run passes `-s workspace-write`. The user's `~/.codex/config.toml` sets
`sandbox_mode = "danger-full-access"`, which is fine for a human driving Codex
interactively and wrong for an unattended delegate — under full disk access the
worktree stops being isolation and becomes merely a starting directory, since
nothing stops an absolute-path write into the primary checkout. The flag
overrides the config per invocation and leaves the interactive setup alone.

## Why a worktree, always

A delegate loose in the primary checkout can trip two traps this repo has hit
before: the editor dev server live-writes `data/*.json`, and `sed -i` silently
converts CRLF to LF so a two-line edit arrives as a whole-file rewrite. The
worktree makes the first impossible and `crlf_check` catches the second — it
flags any file whose diff largely vanishes under `--ignore-cr-at-eol`.

`.codex-work-*/` is already gitignored.

## The ledger is tracked on purpose

`ledger.jsonl` is committed, not ignored. It is the only record of which task
classes survive delegation, and accumulated evidence kept under a gitignored
directory gets destroyed by routine cleanup — that has already happened twice
here with the asset-gen ratings store.

Each row lands with `"verdict": null`. **Fill it in after reviewing the diff**
(`good` / `usable` / `bad`, plus a note). Ungraded rows make the ledger a log
instead of an experiment; after a few dozen graded runs it answers the actual
question, which is *which kinds of work are worth delegating* — not whether
delegation feels fast.

### `channel` — record it, or the ledger answers nothing

Rows carry a `channel` because more than one thing delegates work here, and they
do not have the same capabilities:

- `delegate-cli` — `delegate.py run`, forced into a worktree at
  `-s workspace-write`. Rows are written automatically.
- `codex-goal-mode` — the Codex app on the owner's local machine, long-running,
  with an owner-set access level. **No row is written automatically; append one
  by hand**, since nothing else records that the run happened.

Mixing the two unlabelled would silently confound the experiment: a goal-mode
run can reach the GPU, the Effekseer shim and the golden gates, and a CLI
delegate in a bare worktree cannot. A verdict is only comparable against runs
from the same channel.

Fill `transcript_chars` with `null` when the channel does not produce one.

## Writing a task brief

See `tasks/doc-status-drift.md` for the shape. What makes a brief work here:

- **Point at the repo's own doctrine** rather than restating it.
  `docs/EXTERNAL-AGENT-BRIEF.md` already covers not reporting unverified work.
- **State what is _not_ a finding.** Cheap models over-report; the negative
  cases do more work than the positive ones.
- **Require coverage, not just hits.** "Files I checked and found clean" is the
  part that makes a report auditable. Without it a short report is
  indistinguishable from a lazy one.
- **Make the deliverable checkable in one line-read per finding** — a quote plus
  `file:line`. If grading a finding costs as much as finding it, delegation
  saved nothing.
- **Forbid the gates.** A cheap agent reporting a gate result it could not
  observe is the failure mode that matters most; the golden gates need a GPU and
  a DLL a worktree does not have.
