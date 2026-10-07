# Parasite Eve Day 4 — St. Francis Hospital vertical slice

> Design intent for #1463. This document does not claim implementation status;
> issues, generated engine state and gates own status.

## What this slice is for

St. Francis Hospital replaces Day 1 as the primary Parasite Eve vertical slice.
The objective is not to recreate the most famous opening. It is to force
Thestra to express the game's established middle-game loop in one bounded
building.

The slice should answer a harder question than “can we make a screen that looks
like Parasite Eve?”:

**Can one reusable event/battle/runtime vocabulary support PE-like exploration,
persistent environmental state, resource pressure, equipment semantics,
distinct spatial enemies, a phase-changing boss and a timed set-piece without
turning the engine into a Parasite Eve special case?**

Day 1 remains useful as a reference/onboarding lab for fixed cameras, menu/HUD
archaeology and early combat presentation.

## Boundary

Start from `reference/canonical-start.json` at the hospital exterior, after the
Day-4 NYPD briefing and Maeda arrival conversation. Do not replay Days 1–3.

End when the rooftop escape reaches the emergency elevator/gondola terminal
state after Spiderwoman.

The mandatory state graph is `reference/route.json`.

## Systems the slice must pressure

### Stateful exploration

Power is cut after the elevator crash. Three fuses, wire repair, the Autopsy
Key, Blue Cardkey, Green Cardkey, liquid-nitrogen valve and Elevator Key form a
return-traversal graph. Returning through an area must expose the changed world,
not replay the room's first-visit script.

This is the heart of the pivot: the environment is not a sequence of story
cards. The building itself is a state machine.

### Encounter ecology

Hospital should not reuse one rat behavior under different meshes. Bacterium,
Flyman, Ratman, Spider and Mixedman must produce meaningfully different spatial
problems while sharing reusable battle semantics.

A graph test may neutralize combat to prove topology. The **mechanical**
acceptance path may not edit enemy HP/AT, inject ammunition, disable attacks or
skip costs.

### Established PE progression

The slice begins after PE's onboarding period. Level-bound Parasite Energy,
status pressure, BP semantics and the Day-4 equipment economy are therefore
part of the design question rather than optional polish.

The project must not invent a smooth generic EXP/HP growth curve and then
protect it as source truth. Numeric claims link back to `reference/facts.json`.

### Magazine/reload and equipment

Gunfire must eventually consume loaded rounds and reload from carried
ammunition. Bullet capacity/range and equipment mutation need to exist at the
level required by Hospital. Tune-Up should be implemented only as deeply as the
slice needs to prove the representational model.

`reference/generalization.json` is the guardrail: PE-specific policy stays in
project data unless there is a legitimate generic engine abstraction.

### Spiderwoman

The rooftop boss must remain one encounter/domain identity across its arena
transition. The presentation may move the fight; it must not fake the phase
change by ending one unrelated battle and starting another merely to reproduce
the appearance.

The post-boss escape must have a real deadline/failure condition and a
deterministic input proof.

## Acceptance layers

Keep these reports separate:

1. **Reference contract** — evidence status and provenance are valid.
2. **Graph** — all mandatory state transitions are reachable with driven input.
   Combat cheats are allowed only here and must be obvious.
3. **Mechanical** — the canonical snapshot completes the slice under real
   resources/combat with no state injection after start.
4. **Persistence** — representative basement, restored-power/13F and pre-roof
   saves round-trip all required state.
5. **Presentation** — fixed-camera composition, UI/HUD, enemy telegraphs and
   phase transitions are human-reviewed against references.
6. **Owner play** — separate human acceptance; never inferred from automated
   probes.

A green graph test is not balance acceptance. A green relative screenshot test
is not source-fidelity acceptance. A booted window is not owner play.

## Explicit non-goals

- Replaying Days 1–3 to manufacture the starting save.
- Reconstructing every optional chest/RNG table before the mandatory loop works.
- Full cinematic recreation before stateful room events are mechanically real.
- EX Game/Chrysler systems.
- Autonomous rewrite of production Battle owners.
- Generic engine features whose only justification is “Hospital needs it.”

## Delivery order

M0 establishes reference facts, the canonical starting snapshot and the route/state contract. M1 implements traversal and persistent world-state changes. M2 replaces combat stubs with distinct enemy ecology and an honest mechanical route. M3 adds magazine/Reload and the minimum equipment economy needed by the slice. M4 finishes Spiderwoman, the rooftop escape and end-to-end acceptance.

Each milestone must preserve the separation between source facts, project-local PE policy and genuinely generic Thestra primitives. If a proposed engine feature lacks a Second Gate analogue and a second PE use-case, keep it project-local until that justification exists.