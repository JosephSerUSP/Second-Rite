# Thestra design and architecture notes

This repository-level directory is for **Thestra runtime, presentation, RTP, Project semantics, and Thestra Studio design/architecture intent**. It is not the authoritative home for Second Gate game design.

For Second Gate's game vision, systems, world, characters/creatures, balance intent, and art direction, use:

[`projects/hichaukitoden-game/docs/`](../../projects/hichaukitoden-game/docs/README.md)

Documents here may use Second Gate as a fixture or motivating example when investigating a reusable Thestra capability. That does not make concrete Second Gate content, lore, balance sentences, or branding reusable engine policy.

## How this directory is grouped

Three owners, matching the semantic boundary the repository already enforces
physically in `runtime/`, `studio/` and `projects/`:

- [`runtime/`](runtime/) — Thestra runtime and presentation, split by what a
  note is about:
  - [`runtime/rendering/`](runtime/rendering/) — how the world is drawn:
    shaders, lighting, geometry, camera framing, readability.
  - [`runtime/semantics/`](runtime/semantics/) — what the engine knows: Event
    and battler state, identity vocabulary, progression, RTP layering.
- [`studio/`](studio/) — Thestra Studio: editor surfaces, authoring UX, and the
  bundles Studio consumes.
- [`contracts/`](contracts/) — what runtime, Studio and a Project owe each
  other: root and storage boundaries, authored state scopes, the
  source/semantic/compiled seam, the player-equivalent membrane.

Notes that describe the design process rather than a subject stay at this root:
this README, `content-engine-gaps.md` and `future-issues.md`.

Implementation status remains governed by [`../ENGINE-STATE.md`](../ENGINE-STATE.md); reviewed architecture/behavior by [`../SPEC.md`](../SPEC.md); actionable work by GitHub Issues.

The classification that established this boundary is recorded in [`../reports/second-gate-document-authority-audit-2026-08-18.md`](../reports/second-gate-document-authority-audit-2026-08-18.md).
