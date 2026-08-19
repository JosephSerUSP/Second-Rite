---
type: design
scope: game
status: active
---

# Combat

## Combat grammar

Second Gate's elemental system is a **commitment vocabulary**, not a universal rock-paper-scissors puzzle. Elements should tell the player something about how a creature, skill, or encounter wants combat to develop.

Broad identities:

- **Fire** — escalation, pressure, volatility, conversion of tempo into damage.
- **Earth** — endurance, anchoring, barriers, attrition, positional stability.
- **Water** — recovery, redirection, soft control, adaptation.
- **Wind** — speed, initiative, displacement, evasive or tempo play.
- **Light** — clarity, restoration, protection, exposure of hidden/negative states.
- **Dark** — risk, corruption, exchange, predation, state pressure.
- **Neutral** — dependable tools whose value is not conditional on elemental leverage.

These are design tendencies, not hard engine classes. A particular creature may deliberately bend them.

## Weakness and resistance

Weaknesses and resistances should change the value of a plan without making one lookup answer every encounter. Elemental advantage should interact with creature roles, states, positioning, resource pressure, and sequencing.

Ailments and elemental follow-ups can create chains of commitment: one action changes the state of combat so another becomes attractive. The point is to create readable tactical trajectories rather than a flat damage multiplier table.

## Creature roles

A creature should be recognizable by what it contributes to a formation, not only by its highest stat. Roles can include damage, protection, recovery, control, resource support, setup, exploitation, or unusual conditional behavior.

The roster should support composition choices where two individually strong creatures produce different expedition plans because their costs, elements, skills, and behavioral roles differ.

## Numbers and balance

Second Gate favors compact, legible RPG numbers and strong differentiation without inflation for its own sake. Numeric tables in historical design notes are **not** authority.

Current skill costs, parameters, growth, enemy values, item effects, and encounter data live in the Project's authored `data/`. Balance experiments and unresolved tuning belong in GitHub Issues. Use historical `vertical-slice-balance.md`, `skill-costs.md`, and `creature-parameters.md` only as provenance through the [legacy archive](../archive/legacy-repo-design/README.md).

## Battle presentation

Battle presentation should make the current tactical question legible before decorating it. Persistent information belongs in stable geometry; prompts should not duplicate facts already visible elsewhere; consequences should land with enough timing and motion to be felt.

Second Gate's UI text uses abstract actions (`Confirm`, `Cancel`) rather than physical key names when possible. Color communicates semantic role rather than arbitrary emphasis. Detailed historical presentation/UI briefs are preserved in the legacy archive; current renderer implementation remains a Thestra technical concern.

## Authority note

This document owns the game's tactical intent. Runtime semantics, targeting contracts, state-resource implementation, and presentation architecture remain repository-level Thestra concerns in `docs/SPEC.md` and `docs/design/`.
