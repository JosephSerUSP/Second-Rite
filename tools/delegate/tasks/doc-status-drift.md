# Task: find implementation-status claims in design docs

## Read first

- `docs/EXTERNAL-AGENT-BRIEF.md` — in full. Rule 1 governs this whole task.
- `AGENTS.md` — the document-authority table at the top, especially the line:
  "Design docs describe intent. They must not assert implementation status."

## The rule being enforced

This repo separates four kinds of document, and the separation is load-bearing:

| Question | Authority |
|---|---|
| What exists right now? | `docs/ENGINE-STATE.md` (generated, gated) |
| How does it work, and why? | `docs/SPEC.md` (reviewed) |
| What are we trying to build? | `docs/design/`, `docs/game design/` — **intent only** |
| Anything under `docs/archive/` | frozen, never authoritative |

Design docs drift by acquiring status claims: a doc written as "the ritual scene
should offer three rites" gets edited over time into "the ritual scene offers
three rites", and now a file whose job is to describe intent is quietly asserting
what shipped. When that claim goes stale, nothing catches it, because no gate
covers design-doc prose.

## What to find

Every place in `docs/design/**` and `docs/game design/**` that asserts
implementation status rather than intent.

Positives look like: "is implemented", "now works", "this landed in", "currently
the engine does", "as of <date> this is done", "✅", checkbox lists tracking
completion, past-tense descriptions of work ("we added", "this was changed to").

**Judgement is required — this is not a grep.** These are NOT findings:

- Present-tense descriptions of *designed behaviour* ("the player selects a rite,
  and the scene resolves it") — that is intent written in the normal way.
- Statements about the *engine's existing constraints* that the design must work
  within ("one map cell is 2.5 metres") — that is context, not a status claim.
- Historical narrative clearly framed as rationale ("this replaced an earlier
  approach that couldn't express X") — explaining why a design is shaped a
  certain way is legitimate.

The distinction: does the sentence tell the reader **what the code does today**
(finding) or **what the design wants** (fine)? If you are unsure, include it and
mark it `uncertain` — do not silently drop it and do not silently keep it.

## Deliverable

Two things, both required.

**1. A report at `docs/reports/doc-status-drift.md`** with one row per finding:

| file:line | quoted text | why it reads as status | confidence |

Quote the text exactly. Give a real line number. Confidence is `high` /
`uncertain`. Sort by file. Include a count at the top, and a short section
listing files you checked and found clean — a clean file is a result, and I need
to know coverage, not just hits.

**2. Commits rewording the `high`-confidence findings** from status to intent,
one commit per file, message `docs: state intent not status in <filename>`.

Reword; do not delete. "The scene offers three rites" becomes "The scene offers
three rites" only if that was always the design — if the sentence is genuinely
reporting a shipped state, the fix is usually to move the fact out or recast it
as the requirement it came from. Where a sentence is load-bearing status that
belongs somewhere, say so in the report and leave it alone rather than
inventing a rewrite.

Leave every `uncertain` finding **unedited**. Report it, do not touch it.

## Constraints

- Do not edit `docs/SPEC.md`, `docs/ENGINE-STATE.md`, `AGENTS.md`, or anything
  under `docs/archive/`. They are out of scope; SPEC and ENGINE-STATE are
  *supposed* to carry status.
- Do not touch anything outside `docs/`. No code, no `data/*.json`, no tools.
- Do not use `sed -i` or any in-place stream edit on these files. This repo is
  CRLF; `sed -i` silently rewrites every line ending and turns a one-line change
  into a whole-file diff. Edit files directly.
- Do not run the golden gates. They need a GPU and a DLL this worktree does not
  have, and a gate you cannot actually observe is worse than one you skip.

## Reporting

Per rule 1 of the external-agent brief: report what you verified, not what you
intended. If you ran out of budget partway through `docs/design/`, say which
files you actually read and which you did not. A partial pass with honest
coverage is useful. A complete-sounding pass with unknown coverage is not.
