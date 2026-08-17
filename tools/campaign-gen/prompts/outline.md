# Stage: content outline and walkthrough

Turn the goal, capability plan, and Project-owned ruleset into the smallest complete
playable content outline. Do not force town/dungeon/Summoner/monster-collecting
structure unless the goal itself asks for it.

## Goal

{{GOAL}}

## Game plan

{{PLAN}}

## Project-owned ruleset

{{RULESET}}

## Neutral schema context

{{SCHEMAS}}

## Deliverable

Reply with ONE JSON object, no other text:

```json
{
  "outline": {
    "title": "...",
    "logline": "one sentence",
    "gameLoop": "what the player repeatedly does",
    "beats": ["ordered playable beat", "..."],
    "cast": [],
    "locations": [],
    "objects": [],
    "ending": "how this small game reaches a clear done state"
  },
  "walkthrough": "# <title> -- Walkthrough\n\nExact critical path from startup to a playable interaction and ending/win state. Name only content that later enabled stages actually need to author."
}
```

The shape inside `cast`, `locations`, and `objects` is free-form Project planning data;
later prompts use it as a design contract, not as runtime schema. Keep scope bounded by
PLAN.contentBudget. It is valid for a Scene/Event minigame to have no cast, units,
items, quests, or combat content at all.
