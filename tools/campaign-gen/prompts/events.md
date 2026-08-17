# Stage: events

Implement the goal's interactive behavior using the Project's existing authored content
and the reusable RTP Event command language. This stage is not an RPG-story template:
it may implement dialogue, puzzles, battle triggers, switches, minigame state, endings,
or other Event-driven behavior required by PLAN and WALKTHROUGH.

Goal:
{{GOAL}}

Plan:
{{PLAN}}

Outline:
{{OUTLINE}}

## Command language registry

Use ONLY command ids and parameter contracts present here:
{{COMMANDS}}

## Current Project manifest

{{MANIFEST}}

## Project-owned ruleset

{{RULESET}}

## Neutral schema context

{{SCHEMAS}}

## Deliverable

Reply with ONE JSON object containing only the Project resources this stage changes.
Normally that is one or more of:

```json
{
  "maps.json": [],
  "commonEvents.json": [],
  "troops.json": {}
}
```

Rules:
- Preserve all current map/content ids unless the walkthrough explicitly requires a
  replacement. Every emitted reference must resolve inside MANIFEST or RULESET.
- Common Events are for genuinely shared Event behavior; they are not mandatory.
- Battle/troop data is authored only when PLAN.capabilities.combat is true.
- Do not emit raw Lua or SCRIPT-like escape hatches unless the supplied command registry
  explicitly defines such a command and the plan genuinely requires it. Prefer the
  declarative Event language.
- Do not assume quests, shops, summons, recruitment, dungeon floors, town NPCs, elements,
  or any other Second Gate mechanic. Use them only when this Project authored them.
- Do not invent asset paths.
- Keep behavior bounded to the critical playable walkthrough and clear win/end state.
