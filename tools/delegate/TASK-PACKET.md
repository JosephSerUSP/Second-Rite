# Agent task packet — repository handoff contract

This file defines the normal handoff between the owner-facing orchestration
conversation and a fresh execution agent.

The purpose is to keep expensive execution-agent context focused on the work
that needs execution. Repository doctrine belongs in repository doctrine; a task
packet should not re-paste `AGENTS.md`, the Goal-mode safety contract, or long
chat transcripts.

## Dispatch model

The preferred workflow is:

```text
owner + orchestration/review agent
    -> establish current truth and make owner decisions
    -> write a self-contained GitHub Issue / task packet
    -> mark it agent-ready

execution agent
    -> receive only "Take #N" plus requested model/reasoning/mode
    -> read the repository task packet and required doctrine
    -> work in its own branch/worktree
    -> open a signed draft PR

review agent / owner
    -> inspect the live diff and evidence
    -> merge, or leave signed targeted follow-up on the same PR
```

The Issue is durable handoff memory. Chat is not.

## Required reads

Every task packet may assume the execution agent will first read:

- `AGENTS.md`;
- `tools/delegate/AGENT-PROVENANCE.md`;
- `tools/delegate/GOAL-MODE-PREAMBLE.md` when running unattended Goal mode.

A packet should name additional issues, PRs, reports, source files, or tests that
are specifically relevant to that task.

Do not duplicate standing doctrine into every task merely to make the prompt
look comprehensive.

## Canonical packet shape

Use only the sections that materially help the work, but preserve this order so
a fresh agent can scan packets consistently.

### Goal

State the bounded outcome in one or two paragraphs.

### Current truth to establish

Name any repository facts the agent must verify before changing code. Do not
encode assumptions as facts when the point of the task is to investigate them.

### Owner decisions

Record only decisions the owner has actually made. Label them explicitly as
owner direction. Do not promote a prior agent proposal into an owner decision.

### Required semantics / acceptance criteria

Describe observable behavior and invariants. Prefer what must remain true over a
prescribed implementation that has not yet been investigated.

### Read first

Name task-specific sources beyond the standing required reads.

### Must preserve

Call out mature behavior, compatibility contracts, architecture seams, visual
references, or provenance that the task must not accidentally replace.

### Explicit non-goals

Bound the attractive adjacent work that would otherwise cause scope creep.

### Verification

Name deterministic gates/tests relevant to this change. Never require an agent
to claim a gate it cannot actually run in its environment. Goal-mode agents must
follow the local-machine safety rules in `GOAL-MODE-PREAMBLE.md`.

### Delivery

Normally require:

- a dedicated branch/worktree;
- a draft PR against then-current `main`;
- no merge by the execution agent unless the packet explicitly delegates merge
  authority;
- a concise PR body separating what is proven/implemented from what remains
  provisional or unresolved;
- a signature following `AGENT-PROVENANCE.md`.

## Agent-ready state

`agent-ready` means the Issue has enough durable scope and acceptance criteria
that a fresh execution agent can begin without recovering the original chat.

It does **not** mean:

- architecture is globally settled;
- the task must use a particular model forever;
- the implementation is predetermined;
- owner review is waived.

Use workflow labels for workflow state, not model identity. Preferred vocabulary
is:

```text
agent-ready
agent-active
agent-review
agent-blocked
needs-owner
needs-visual-review
```

Repositories may begin with only `agent-ready` and add the others when they are
useful. Do not create a model-label taxonomy (`luna`, `sol`, `gemini`, etc.);
model/platform provenance belongs in signatures and the delegation ledger.

## Claiming work

When an execution agent takes an `agent-ready` task it should make its claim
visible before substantial work, normally by a signed Issue comment naming:

- platform/model when known;
- reasoning/mode when known;
- branch/worktree name;
- starting revision.

If another active agent has already claimed the same task, stop rather than
silently duplicate work unless the task explicitly requests independent
comparison.

A later automation may manage `agent-active` labels, but the correctness rule is
simply: concurrent agents must be able to see that another worker owns the same
bounded task.

## Staleness

Before implementation, compare the packet's assumptions and referenced base
against current `main`, current Issue comments, and merged dependencies.

If the repository has moved but the semantic task is still valid, refresh the
implementation against current truth. If a merge or owner decision invalidated
the task, stop and report rather than faithfully implementing stale instructions.

The PR body must identify meaningful divergence from the packet.

## Follow-up review

Review comments should be targeted deltas, not a full restatement of the task.
An execution agent asked to revise an existing PR should update that PR in place
unless the reviewer explicitly requests a replacement.

The reviewer signs substantial review/follow-up comments as well. This gives a
future agent a durable provenance chain without requiring access to the original
orchestration conversation.

## Minimal dispatch prompt

Once an Issue satisfies this contract, the owner's handoff to a Goal-mode agent
can be as small as:

```text
Take #347 from JosephSerUSP/Second-Rite.
Use Luna, High reasoning, Goal mode.
Read the repository delegation contracts first and leave a draft PR for review.
```

If platform/model/mode are already selected in the UI, even this is sufficient:

```text
Take #347 from JosephSerUSP/Second-Rite.
```

The repository packet carries the actual task.