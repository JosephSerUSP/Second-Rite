# Stage: units

This stage runs only because the game plan requires runtime Units. Author the complete
Project-owned units collection needed by the outline—no inherited protagonist, monster
roster, class assumptions, or placeholder content from another game.

Goal:
{{GOAL}}

Plan:
{{PLAN}}

Outline:
{{OUTLINE}}

Project-owned ruleset:
{{RULESET}}

Neutral schema context:
{{SCHEMAS}}

Current Project manifest:
{{MANIFEST}}

## Deliverable

ONE JSON object: `{ "units.json": [ ...complete units array... ] }`

Rules:
- Use stable Project-defined ids; every role/skill/passive/element reference resolves in RULESET.
- Author only units the playable walkthrough actually needs.
- `initialParty` is true only when ordinary startup needs that Unit in the player's party.
- No spriteKey/smallBattler/portrait/bigBattler field unless the exact asset exists in MANIFEST.availableAssets.
- Keep baseParams/balance internally coherent with this Project's own rules; no Second Gate ceilings, tiers, summoning assumptions, or named archetypes.
- If a field is irrelevant and the validator does not require it, omit it rather than fabricating game grammar.
