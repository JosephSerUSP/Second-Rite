---
type: index
scope: game
status: active
---

# Second Gate documentation

This is the authoritative home for **Second Gate-specific game intent and meaning**. It lives inside the Project so the game's knowledge travels with the game and can be read equally by Obsidian, GitHub, text editors, and coding agents.

## Start here

- [Game vision](game-vision.md) — identity, player fantasy, place/memory, authorship boundary.
- [Summoning and expedition](gameplay/summoning-and-expedition.md) — Summoner role, contracts, shared pressure, return and loss.
- [Combat](gameplay/combat.md) — elemental/tactical grammar, creature roles, balance authority.
- [Items and crafting](gameplay/items-and-crafting.md) — preparation, food, recipes, equipment identity.
- [St. Maria](world/st-maria.md) — **the town's document of record.** Buildings, households, tenure, the surface strata, the seal, the town register. Layout and art briefs both derive from it.
- [St. Maria layout](world/st-maria-layout.md) — **proposal.** The spiral ring, the port, and the building consolidation, derived from the document of record.
- [Strata and return](world/strata-and-return.md) — St. Maria/Labyrinth relationship, revisit spiral, Metro stratum.
- [Characters and creatures](characters-and-creatures.md) — individuality, naming, roster principles, Saban/opening anchor.
- [Art direction](art-direction.md) — world rendering, portraits, UI/presentation, cultural position.
- [Creatures](creatures/README.md) — creature-note index as individual notes are authored.
- [Game decisions](decisions/README.md) — durable Project-local decisions and rationale.
- [Walkthrough](walkthrough/README.md) — authored play walkthrough and its authoring notes.
- [Legacy repo design](archive/legacy-repo-design/README.md) — frozen pre-#778 source material; never current authority.

Prefer a few strong documents over recreating the old repository folder sprawl.

## What belongs here

- Second Gate's game vision and player experience.
- Game-specific systems and balancing intent.
- World, characters, creatures, strata, narrative, art direction, and audio direction.
- Project-local design decisions and rationale.
- References from prose to implemented Project data where that helps keep intent and authored content connected.

## What does not belong here

- Thestra engine/editor architecture or implementation status.
- Gate procedures, CI evidence, runtime contracts, reusable RTP policy, or Studio behavior.
- Commercial planning, budgets, opportunities, pricing, marketing calendars, or private business material.
- Delivery checklists that should instead be tracked as actionable work.

## Authority

These documents describe **game intent and meaning**, not implementation status. If a note says a mechanic is intended and the authored Project data does not implement it, the note does not make the mechanic implemented.

For concrete Second Gate authored content, inspect the Project's `data/` and `assets/`. For unresolved work, use GitHub Issues. For engine/editor status and architecture, use repository-level `docs/ENGINE-STATE.md`, `docs/SPEC.md`, and Thestra-oriented `docs/design/`.

Historical game-design prose moved under `archive/legacy-repo-design/` remains useful only as provenance. A legacy number, checklist, or implementation sentence does not override current Project data, current live design, or an active Issue.

## Portable Markdown conventions

Obsidian is a consumer of this documentation, not a required runtime or file format.

- Use ordinary `.md` files and standard Markdown links rather than relying on Obsidian-only syntax.
- Use small YAML frontmatter blocks for useful structured properties.
- Prefer descriptive file names in `kebab-case`.
- Link related notes instead of duplicating the same explanation.
- Keep metadata semantic and durable; do not encode transient task state that belongs in GitHub or the commercial workspace.
- Do not commit `.obsidian/` workspace state.

Obsidian recognizes standard Markdown links, so backlinks and the graph remain useful without sacrificing portability.

## Commercial boundary

Commercial/release/store/franchise material previously under repository `docs/commercial/` and `docs/design/commercial-identity.md` is no longer live source-tree authority. Its durable game-identity portion was synthesized into these Project docs; commercial provenance was migrated to the private **Second Gate — Studio** workspace. Exact historical source remains in Git history.
