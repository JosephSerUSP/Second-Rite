# Stage: quests

This stage runs only because the generated game plan requires the Quest database.
Author only the Project-owned quests needed by the walkthrough.

Goal:
{{GOAL}}

Plan:
{{PLAN}}

Outline:
{{OUTLINE}}

Current Project manifest:
{{MANIFEST}}

Neutral schema context:
{{SCHEMAS}}

## Deliverable

ONE JSON object: `{ "quests.json": { ...complete Project quest document... } }`

Every unit/item/map reference must resolve in MANIFEST. Keep the set minimal and tied to
the critical path. Do not invent quest systems, rewards, factions, terminology, or
progression assumptions merely to resemble Second Gate or a generic JRPG.
