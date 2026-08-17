# Stage: startup and identity

Finish the generated Project's ordinary startup, identity and Scene surface.

Goal:
{{GOAL}}

Plan:
{{PLAN}}

Outline:
{{OUTLINE}}

Current Project manifest:
{{MANIFEST}}

Current Project-owned ruleset:
{{RULESET}}

RTP event commands:
{{COMMANDS}}

Neutral schema context:
{{SCHEMAS}}

## Deliverable

Reply with ONE JSON object containing only resources that need to change:

```json
{
  "system.json": { "...": "complete Project system document" },
  "terms.json": { "...": "complete Project terms/identity document" },
  "scenes.json": [ "complete ordered Scene records" ],
  "commonEvents.json": []
}
```

Rules:
- `system.json` MUST keep `rtp.revision` = "1.0". RTP supplies reusable engine language;
  do not copy game data into the Project to replace it.
- `terms.project.title` must be the game title from the plan.
- Startup must enter a playable state through normal Scene/Event commands and only
  reference ids present in MANIFEST or resources emitted here.
- A Scene/Event-driven game may start directly in a custom Scene and keep units, items,
  elements, roles, skills, states and passives empty.
- An exploration game may use the ordinary map Scene and a Project-owned start map.
- Do not invent asset paths. Use only MANIFEST.availableAssets, or author presentation
  that requires no external asset.
- Keep the Scene set small and purpose-built for this game's grammar.
