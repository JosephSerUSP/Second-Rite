---
name: Agent-ready task
about: Durable bounded handoff for an automated execution agent
title: ""
labels: ""
assignees: ""
---

<!--
Read tools/delegate/TASK-PACKET.md before filling this out.
Delete sections that genuinely do not apply; do not invent content to fill them.
After owner/reviewer preparation, apply the `agent-ready` workflow label when it
exists in the repository.
-->

## Goal


## Current truth to establish


## Owner decisions

<!-- Only actual owner direction. Otherwise write "None specific to this task." -->


## Required semantics / acceptance criteria


## Read first

- `AGENTS.md`
- `tools/delegate/AGENT-PROVENANCE.md`
- `tools/delegate/GOAL-MODE-PREAMBLE.md` when using unattended Goal mode


## Must preserve


## Explicit non-goals


## Verification


## Delivery

- Work from then-current `main` in an isolated branch/worktree.
- Open a draft PR; do not merge it yourself unless this Issue explicitly says otherwise.
- Distinguish implemented/proven behavior from provisional/unresolved architecture.
- Sign the PR and substantial follow-up comments per `tools/delegate/AGENT-PROVENANCE.md`.

---

Agent-Signature:
  platform: <platform>
  model: <model or platform-selected/unknown>
  role: delegation
  task: <issue number once created>