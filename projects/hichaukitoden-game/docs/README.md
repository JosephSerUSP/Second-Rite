---
type: index
scope: game
status: active
---

# Second Gate documentation

This is the home for **Second Gate-specific** design knowledge. It is intentionally stored inside the Project so the game's knowledge travels with the game and can be read equally by Obsidian, GitHub, text editors, and coding agents.

## Start here

- [Game vision](game-vision.md)
- [Creatures](creatures/README.md)
- [Game decisions](decisions/README.md)

Add a new note when a concept has become durable enough to deserve a stable home. Prefer a few strong documents over a taxonomy of empty pages.

## What belongs here

- Second Gate's game vision and player experience.
- Game-specific systems and balancing intent.
- World, characters, creatures, strata, narrative, art direction, and audio direction.
- Project-local design decisions and rationale.
- References from prose to implemented Project data where that helps keep intent and authored content connected.

## What does not belong here

- Thestra engine/editor architecture or implementation status.
- Gate procedures, CI evidence, runtime contracts, or Studio behavior.
- Commercial planning, budgets, opportunities, marketing calendars, or private business material.
- Delivery checklists that should instead be tracked as actionable work.

## Authority

These documents describe **game intent and meaning**, not implementation status. If a note says a mechanic is intended and the authored Project data does not implement it, the note does not make the mechanic implemented.

For engine/editor status and architecture, use the repository-level authorities documented in `AGENTS.md`. For concrete Second Gate authored content, inspect the Project's `data/` and `assets/`.

## Portable Markdown conventions

Obsidian is a consumer of this documentation, not a required runtime or file format.

- Use ordinary `.md` files and standard Markdown links such as `[Game vision](game-vision.md)` rather than relying on Obsidian-only syntax.
- Use small YAML frontmatter blocks for useful structured properties.
- Prefer descriptive file names in `kebab-case`.
- Link related notes instead of duplicating the same explanation.
- Keep metadata semantic and durable; do not encode transient task state that belongs in GitHub or the commercial workspace.
- Do not commit `.obsidian/` workspace state.

Obsidian recognizes standard Markdown links, so backlinks and the graph remain useful without sacrificing portability.

## Migration note

Older game-design material still exists under repository-level `docs/design/`, `docs/game design/`, and related locations. **Do not treat this new folder as evidence that those documents have already been migrated or validated.** Each legacy document should be reviewed for current relevance and then moved, rewritten, archived, or left with the engine as appropriate.

This folder is the destination for the game-specific material that survives that audit.
