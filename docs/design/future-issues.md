# Tooling Design Follow-ups

> **Intent and rationale, not backlog status.** GitHub Issues own actionable
> delivery work. This document retains only the design arguments that should
> survive independent of whether a particular implementation has landed.
> `docs/ENGINE-STATE.md` and `docs/SPEC.md` remain the authorities for the live
> system.

## Animation-token provenance in asset picking

Sprite animation timing can be influenced by authored sprite-key tokens and by
asset filename tokens. Those are distinct sources of meaning, so Studio should
make the effective value and its provenance understandable rather than showing
only a raw filename and leaving the author to infer which token wins.

The editor must reuse the runtime's resolution semantics; it should not invent a
second parser or silently normalize away the distinction.

Delivery: #402.

## Shared sprite service vs battler-specific presentation

Image loading, frame slicing, caching, and generic animation timing are reusable
presentation responsibilities. Battler-only visual behavior should not be the
module identity through which unrelated UI sprites have to pass.

The desired refactor is a responsibility boundary, not a cosmetic rename: keep
one shared sprite/cache/animation implementation and layer battler-specific
behavior on top rather than duplicating loaders or clocks.

Delivery: #403.

## Spatial domains deserve spatial authoring

Data-driven interface layout is load-bearing, but a flat form is a poor sole
editor for geometry whose meaning is spatial. Fields that jointly describe one
visual feature should be grouped, and authors should be able to see the effect
of layout edits without launching a separate mental model of the 256×240
composition.

The authoritative visual feedback should come from the engine presentation
stack. Studio must not solve editor ergonomics by maintaining a second partial
window renderer. A bounded first layout domain is preferable to a general
"visual editor for everything" rewrite.

Delivery: #404.

## What does not belong here

Completed refactors, golden updates, post-merge gate results, one-time code
searches, and "FIXED" histories are delivery evidence. They belong in PRs,
dated reports, or Git history, not in a design document that future work is
expected to read as durable guidance.
