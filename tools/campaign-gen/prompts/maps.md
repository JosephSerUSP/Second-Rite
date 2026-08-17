# Stage: maps

This stage runs only because the game plan needs authored Maps. Generate the complete
Project-owned map collection required by the walkthrough. Map topology, categories,
encounters and traversal must come from this game's goal—not from Second Gate's town /
dungeon conventions.

Goal:
{{GOAL}}

Plan:
{{PLAN}}

Outline:
{{OUTLINE}}

Current Project manifest:
{{MANIFEST}}

Project-owned ruleset:
{{RULESET}}

RTP Event commands:
{{COMMANDS}}

Neutral schema context:
{{SCHEMAS}}

## Deliverable

ONE JSON object: `{ "maps.json": [ ...complete maps array... ] }`

Rules:
- Map ids are unique and stable. The map referenced by ordinary startup must exist.
- For hand-authored layouts, every row is equal width; `#` is wall and `.` is floor.
  Spawn/event coordinates are 0-based floor cells.
- Add only events needed to establish traversal or hand off to the events stage. A short
  TEXT placeholder is acceptable when the events stage will replace it.
- Reference only Project units/items/rules that exist in MANIFEST/RULESET.
- Do not invent sprite/model/texture paths. Use only MANIFEST.availableAssets, or omit
  presentation asset fields.
- Procedural generation is optional, not assumed. Use it only when the goal/plan calls
  for it and the neutral schema/validator supports the required fields.
- Do not fabricate shops, encounters, treasure, recruits, dungeon depth, or a town hub
  simply because those concepts exist in another game.
