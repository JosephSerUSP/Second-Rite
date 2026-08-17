# Stage: Project-owned ruleset

The generated Project has this goal and capability plan:

Goal:
{{GOAL}}

Plan:
{{PLAN}}

Author the game's own core RPG rule resources ONLY where `rulesetNeeds` says they are
needed. Unneeded resources must stay genuinely empty. Do not use familiar Second Gate
ids, roles, elements, skills, states, lore, character names, or balance conventions.
Names and ids must arise from this Project's goal.

## Neutral schema context

{{SCHEMAS}}

## Engine semantics

Formula/event semantics come from Thestra/RTP. They are reusable engine language and do
not imply any game-specific vocabulary.

## Deliverable

Reply with ONE JSON object. Use only these keys:

```json
{
  "elements.json": {},
  "roles.json": {},
  "skills.json": {},
  "states.json": {},
  "passives.json": {}
}
```

Rules:
- Every non-empty skill id must be owned by the Project and repeated in its record `id`.
- Every element/role/state/passive reference must resolve within the same output.
- Empty `{}` is correct and preferred for any irrelevant database.
- Keep the ruleset minimal: enough to make this small game coherent, not a generic RPG kit.
- Do not author units, items, maps, scenes, or startup here; later stages own those.
