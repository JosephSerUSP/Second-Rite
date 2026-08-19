# Second Gate Project agent orientation

This directory is the authored **Second Gate Project**. The repository-root `AGENTS.md` still governs Thestra engineering workflow, gates, and safety rules; this closer file specializes documentation/content authority for work under this Project.

## Project authority

| Question | Source |
| --- | --- |
| What Second Gate content is authored now? | `data/` and `assets/` |
| What does Second Gate intend/mean as a game? | `docs/README.md` and its live linked notes |
| What old game-design source might explain a decision? | `docs/archive/legacy-repo-design/` — historical only |
| What remains actionable/unresolved? | GitHub Issues |
| How does Thestra implement/validate/render it? | repository-root `docs/ENGINE-STATE.md`, `docs/SPEC.md`, `docs/design/`, code/tests/gates |
| What is the commercial/release strategy? | private Second Gate Studio workspace, not this Project |

Game-design prose is **intent, not implementation status**. Never make a current-state claim from an archived design note. Verify concrete IDs, numbers, recipes, maps, skills, actors, items, encounters, and other authored facts against current `data/`/`assets/`.

## Documentation conventions

- Add durable Second Gate design to `docs/`, not repository-level Thestra documentation.
- Prefer extending one of the strong live documents over creating a narrow new file for every idea.
- Use ordinary Markdown and standard links; Obsidian is a consumer, not a dependency.
- Never use a doc checklist to track delivery. Use GitHub Issues.
- Do not copy commercial pricing/marketing/release material into Project docs.
- Do not promote a legacy archive source back to live authority without reconciling it against current Project data and current Issues.

## Technical boundary

Do not generalize concrete Second Gate lore, balance, IDs, or presentation choices into Thestra runtime policy merely because the Project is the primary fixture. Conversely, reusable engine/editor/RTP architecture belongs at repository level rather than in this game bible.
