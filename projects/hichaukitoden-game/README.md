# Second Gate

This directory is the authored **Second Gate Project**. Game-specific source and knowledge belong with the Project rather than in Thestra's engine/editor documentation.

## Project contents

- `data/` — authored game data consumed by Thestra.
- `assets/` — authored game assets.
- `docs/` — Second Gate design knowledge and project-local decisions.

## Obsidian

This Project directory is also an Obsidian vault.

1. In Obsidian, choose **Open folder as vault**.
2. Select `projects/hichaukitoden-game/`.
3. Open `docs/README.md` as the documentation home.

Obsidian is only a view/editor over ordinary Project files. No Obsidian plugin is required, and local `.obsidian/` workspace state is intentionally not tracked by Git.

## Authority boundary

- Implemented Second Gate content is represented by the Project's authored `data/` and `assets/`.
- `docs/` records **game-specific design intent, concepts, rationale, and durable decisions**. It must not claim Thestra engine/editor implementation status.
- Thestra engine/editor architecture, capabilities, gates, and technical evidence remain repository-level concerns.
- Commercial/business operations remain outside the source tree in the private studio workspace.

The legacy folder name `hichaukitoden-game` is retained for now as a repository path; the game is **Second Gate**.
