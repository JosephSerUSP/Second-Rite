# Agent provenance — durable attribution for automated work

Second Rite is worked on by several automated agents, models, platforms, and
human reviewers. They share repository state but do not share a continuous
conversation or reliable knowledge of one another's execution context.

A durable contribution therefore needs to say **where it came from**.

This is provenance, not credit theater and not an authority hierarchy. A model
signature does not make a claim correct. It makes the claim traceable.

## Standing rule

Every automated agent that creates or materially updates a durable GitHub-facing
artifact must sign that artifact.

This includes, when authored by an agent:

- Issue bodies and substantial Issue comments;
- pull-request bodies and substantial PR review/follow-up comments;
- architecture/research reports intended to survive the current session;
- delegation packets written for another agent.

Routine machine-generated logs, individual source comments, commit messages, and
tiny mechanical GitHub actions do not need a signature merely for existing.

Human owner comments do not need to impersonate an automated signature. If an
agent is transcribing an owner decision, the artifact must still distinguish the
**owner decision** from the agent that recorded it.

## Canonical signature

Use this block at the end of the durable artifact:

```text
Agent-Signature:
  platform: <platform>
  model: <model or platform-selected/unknown>
  role: <implementation | research | review | delegation | documentation | orchestration>
```

Add fields when they are actually known and useful:

```text
  reasoning: <level>
  mode: <mode>
  task: <issue/PR or task id>
  base: <starting revision>
```

Example for a Goal-mode Codex implementation:

```text
Agent-Signature:
  platform: Codex
  model: Luna
  reasoning: high
  mode: Goal
  role: implementation
  task: "#347"
  base: 65fff43e
```

Example for an owner-facing review performed from ChatGPT web:

```text
Agent-Signature:
  platform: ChatGPT Web
  model: GPT-5.6 Sol
  role: review
  task: "#347"
```

## Do not guess metadata

Never infer a model name, reasoning level, platform mode, or starting revision
that the current environment cannot actually establish.

Use a truthful fallback instead:

```text
model: platform-selected/unknown
```

Omit optional fields that are unavailable.

A precise unknown is better provenance than a plausible fabrication.

## Authority is separate from provenance

Keep the repository's existing authority rules intact:

- code and generated `ENGINE-STATE.md` establish current implementation truth;
- owner decisions must be labelled as owner decisions;
- design reports may contain facts, inferences, proposals, and owner direction,
  and should distinguish those categories when the distinction matters;
- a signature records the producer, not the truth status of the content.

In particular, do not turn:

```text
Agent-Signature: ...
```

into an implication that one model outranks another model or the owner.

## Reviews and handoffs

When one agent reviews another agent's work, both provenance layers should remain
visible: the PR/report keeps the implementation author's signature and the review
comment carries the reviewer's signature.

This is intentional. Future agents should be able to reconstruct chains such as:

```text
signed delegation packet
    -> signed implementation PR
    -> signed review comment
    -> signed correction comment
    -> owner signoff / merge
```

without relying on chat history.

## Relationship to the delegation ledger

`tools/delegate/ledger.jsonl` remains the experiment log for delegated runs.
Its `channel` field answers a different question from this signature:

- the ledger measures whether a class of delegated work was worth delegating;
- the signature tells a future reader who produced one durable GitHub artifact.

Do not remove or replace ledger metadata with signatures. Where a Goal-mode run
is recorded manually in the ledger, use the same truthful platform/model/mode
metadata when the ledger schema supports it; do not invent fields ad hoc merely
to duplicate the signature.