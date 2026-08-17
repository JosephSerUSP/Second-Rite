# Stage: game plan

Design the smallest complete Thestra Project that satisfies this goal:

{{GOAL}}

This is NOT a request to fit the goal into Second Gate or into a mandatory RPG database.
Decide the game's grammar from the goal itself. A dungeon RPG may need units, skills,
elements and battles; a puzzle/minigame/adventure may need almost none of those and can
be primarily Scene/Event driven.

## Reusable Thestra engine language

Event commands available from the Project's declared RTP engine registry:
{{COMMANDS}}

## Neutral authored schema context

{{SCHEMAS}}

## Deliverable

Reply with ONE JSON object and no other text:

```json
{
  "plan": {
    "title": "Project-owned game title",
    "grammar": "short description of the actual game loop and rules",
    "capabilities": {
      "exploration": true,
      "combat": false,
      "inventory": false,
      "quests": false,
      "customScenes": true
    },
    "stages": ["maps", "events"],
    "rulesetNeeds": {
      "elements": false,
      "roles": false,
      "skills": false,
      "states": false,
      "passives": false
    },
    "startup": "what ordinary startup must enter and why",
    "playableProof": "the shortest input path that demonstrates the game is playable",
    "contentBudget": "small bounded scope"
  }
}
```

`stages` may contain ONLY: units, items, quests, maps, events.
Include a stage only when the game genuinely needs that authored database. Do not add
RPG-shaped stages merely because they exist. `rulesetNeeds` is equally sparse.
