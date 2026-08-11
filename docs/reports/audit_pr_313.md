# Gameplay Vocabulary and Architecture Audit

This report completes the live trait-code inventory portion of #308 and validates the architectural pressure identified by PR #313 against current `main`.

## Part 1 & 2 — Trait Code Census and Classification

| Code | Category | Registry Definition | Authored Value Shape | Representative Authored Use | Authored Usage Count | Engine Consumers | Flow Consumers | Symmetry | Provenance | Dead/Unused |
|------|----------|---------------------|----------------------|-----------------------------|----------------------|------------------|----------------|----------|------------|-------------|
| `COVER_ALIGNED_BACK` | Structural rule / capability | A living, unrestricted front-row holder of this trait protects the living back-row creature in the same column from single-target coverable attacks. | usesDataId=False, type=none | `{"code": "COVER_ALIGNED_BACK"}` | 1 instances | renderer.lua, battle.lua | None | Party/Ally specific | No | No |
| `PARAM_PLUS` | Modifier / calculation contribution | Adds a flat amount to a parameter. | usesDataId=True, type=signed | `{"code": "PARAM_PLUS", "dataId": "atk", "value": 1}` | 115 instances | validator_core.lua, effects.lua, craft.lua, traits.lua, formula.lua | None | Symmetrical | No | No |
| `PARAM_RATE` | Modifier / calculation contribution | Multiplies a parameter (1.2 = +20%). | usesDataId=True, type=multiplierSigned | `{"code": "PARAM_RATE", "dataId": "maxHp", "value": 1.1}` | 17 instances | traits.lua, formula.lua, validator_core.lua | None | Symmetrical | No | No |
| `HIT` | Modifier / calculation contribution | Modifies hit chance (base 100%). | usesDataId=False, type=percentSigned | `{"code": "HIT", "value": -0.15}` | 4 instances | traits.lua, interpreter_core.lua | None | Symmetrical | No | No |
| `EVA` | Modifier / calculation contribution | Modifies evade chance (base 0%). | usesDataId=False, type=percentSigned | `{"code": "EVA", "value": 0.15}` | 4 instances | traits.lua, interpreter_core.lua | None | Symmetrical | No | No |
| `CRI` | Modifier / calculation contribution | Modifies crit chance (base 5%). The effective rate against a given target is CRI minus that target's CEV. | usesDataId=False, type=percentSigned | `{"code": "CRI", "value": 0.1}` | 10 instances | engine_state.lua, effects_core.lua, traits.lua | _test.json | Symmetrical | No | No |
| `CEV` | Mixed / problematic | Subtracts from an attacker's CRI against this holder. Worth twice what it looks like: a critical is also the universal status backdoor (it forces the affliction attached to the action past the chance roll), so being hard to crit means less burst damage AND fewer forced states. Deliberately trait-driven only -- gear and passives buy it, no stat derives it, or DEF would become a super-stat on top of mitigation and physical-ailment resistance. | usesDataId=False, type=percentSigned | `None` | 0 instances | effects_core.lua | None | Symmetrical | No | No |
| `HRG` | Mixed / problematic | Regenerates a fraction of max HP per turn. | usesDataId=False, type=percentSigned | `{"code": "HRG", "value": 0.05}` | 6 instances | traits.lua, interpreter_core.lua | None | Symmetrical | No | No |
| `POST_BATTLE_HEAL` | Resolved-event reaction / temporal behavior | Restores HP to the holder after victory. | usesDataId=False, type=signed | `{"code": "POST_BATTLE_HEAL", "value": 0.08}` | 3 instances | None | battle.json, _test.json, exploration.json | Party/Ally specific | No | No |
| `GOLD_DIGGER` | Mixed / problematic | Increases gold found. | usesDataId=False, type=signed | `{"code": "GOLD_DIGGER", "value": 15}` | 4 instances | formula.lua | battle.json | Party/Ally specific | No | No |
| `PARASITE` | Mixed / problematic | Drains HP from a nearby ally each turn. | usesDataId=False, type=signed | `{"code": "PARASITE", "value": 2}` | 1 instances | interpreter_core.lua | battle.json | Symmetrical | No | No |
| `BATTLE_START_DAMAGE` | Resolved-event reaction / temporal behavior | Damages an enemy at battle start. | usesDataId=False, type=signed | `{"code": "BATTLE_START_DAMAGE", "value": 2}` | 1 instances | engine_state.lua, interpreter_core.lua | None | Symmetrical | No | No |
| `MOVE_HEAL` | Resolved-event reaction / temporal behavior | Restores HP when moving on the map. | usesDataId=False, type=signed | `{"code": "MOVE_HEAL", "value": 1}` | 1 instances | formula.lua | exploration.json | Party/Ally specific | No | No |
| `RECOVERY_XP_BONUS` | Resolved-event reaction / temporal behavior | Bonus XP at recovery sites. | usesDataId=False, type=signed | `{"code": "RECOVERY_XP_BONUS", "value": 5}` | 2 instances | engine_state.lua | None | Symmetrical | No | No |
| `FLEE_CHANCE_BONUS` | Modifier / calculation contribution | Increases the party's flee chance. | usesDataId=False, type=percentSigned | `{"code": "FLEE_CHANCE_BONUS", "value": 0.2}` | 6 instances | effects_core.lua, formula.lua | battle.json | Party/Ally specific | No | No |
| `ON_PERMADEATH` | Resolved-event reaction / temporal behavior | Saves the creature from the end-of-battle permadeath sweep (REAP_FALLEN). mode: relic (never consumed) | charges (spends one per save, breaks at zero) | ward (consumed, creature survives) | revive (consumed, reaped then restored). Optional params: hpFraction, charges, levelCost. Defaults come from system.json permadeath. | usesDataId=False, type=none | `{"code": "ON_PERMADEATH", "value": 1, "mode": "ward", "hpFraction": 0.1}` | 6 instances | engine_state.lua, traits.lua, interpreter_core.lua | battle.json, exploration.json | Symmetrical | No | No |
| `SEE_TRAPS` | Structural rule / capability | Detects hidden traps (value = level). | usesDataId=False, type=none | `{"code": "SEE_TRAPS", "value": 1}` | 5 instances | detection.lua | None | Symmetrical | No | No |
| `SEE_WALLS` | Structural rule / capability | Reveals breakable walls. | usesDataId=False, type=none | `{"code": "SEE_WALLS", "value": 1}` | 2 instances | detection.lua | None | Symmetrical | No | No |
| `SYMBIOSIS` | Mixed / problematic | Heals a neighboring ally each turn. | usesDataId=False, type=signed | `{"code": "SYMBIOSIS", "value": 2}` | 1 instances | None | battle.json | Symmetrical | No | No |
| `INITIATIVE` | Structural rule / capability | Chance to act first at battle start. | usesDataId=False, type=percentSigned | `{"code": "INITIATIVE", "value": 0.05}` | 5 instances | battle.lua | None | Symmetrical | No | No |
| `REAR_GUARD` | Structural rule / capability | Negates enemy first strikes. | usesDataId=False, type=none | `{"code": "REAR_GUARD", "value": 1}` | 3 instances | battle.lua | None | Symmetrical | No | No |
| `ELEMENT_CHANGE` | Structural rule / capability | Overrides the holder's elements with dataId while active. | usesDataId=True, type=subject | `{"code": "ELEMENT_CHANGE", "dataId": "Red"}` | 8 instances | craft.lua, traits.lua, validator_core.lua | None | Symmetrical | No | No |
| `ELEMENT_ADD` | Structural rule / capability | Appends dataId to the holder's elements while active, deepening an existing alignment or adding a new one. Applied after ELEMENT_CHANGE. | usesDataId=True, type=subject | `{"code": "ELEMENT_ADD", "dataId": "Red"}` | 10 instances | traits.lua, validator_core.lua | None | Symmetrical | No | No |
| `XP_RATE` | Modifier / calculation contribution | Multiplies experience gained (0.5 = +50%). | usesDataId=False, type=percentSigned | `{"code": "XP_RATE", "value": 1.5}` | 2 instances | session.lua | None | Symmetrical | No | No |
| `CRAFT_YIELD_RATE` | Modifier / calculation contribution | Multiplies Item Creation yield score (0.25 = +25%). | usesDataId=False, type=percentSigned | `{"code": "CRAFT_YIELD_RATE", "value": 0.25}` | 1 instances | craft.lua | None | Symmetrical | No | No |
| `PENETRATION` | Pending-transition interceptor / transformer | Ignores this share of the target's defending stat before the damage curve (0.3 = 30%). Adds to an effect's own `penetration` and clamps at 1. Applied to the defense rather than the damage on purpose: against a soft target it is worth almost nothing and against a wall it is worth a great deal, which is what separates it from simply hitting harder. | usesDataId=False, type=percent | `{"code": "PENETRATION", "value": 0.45}` | 1 instances | effects_core.lua | None | Symmetrical | No | No |
| `EXECUTION_THRESHOLD` | Resolved-event reaction / temporal behavior | After the holder's damage lands, a surviving target at or below this fraction of its Max HP is finished outright (0.2 = a fifth). A finisher rather than a gamble: it is checked after the hit, so it closes a wounded enemy and does nothing to a healthy one. | usesDataId=False, type=percent | `{"code": "EXECUTION_THRESHOLD", "value": 0.18}` | 2 instances | effects_core.lua | None | Symmetrical | No | No |
| `EXECUTION_RESIST` | Resolved-event reaction / temporal behavior | Subtracts from an attacker's EXECUTION_THRESHOLD against this holder; 1.0 is outright protection (Safety Bit). Deliberately separate from state resistance -- execution is not a state, and it subtracts rather than rolling, so it costs no randomness and partial resistance means something exact. | usesDataId=False, type=percent | `{"code": "EXECUTION_RESIST", "value": 1}` | 1 instances | effects_core.lua | None | Symmetrical | No | No |
| `FORCE_ACTION` | Mixed / problematic | The holder can only take the skill named by dataId, whatever it or the player chose. Applied where the turn queue is built, so it constrains an AI enemy and a player creature by the same rule -- Berserk forcing a basic Attack is one authored state, not a branch in the battle code. Target is picked by the forced skill's own targeting spec. | usesDataId=True, type=subject | `{"code": "FORCE_ACTION", "dataId": "attack"}` | 2 instances | battle.lua, battle.lua, usability.lua, validator_core.lua | None | Symmetrical | Yes | No |
| `INVERT_TARGETING` | Structural rule / capability | Inverts targeting groups for the holder while active (`enemy` side targets allies, `ally` side targets enemies). Used by Charm and confusion effects. | usesDataId=False, type=none | `{"code": "INVERT_TARGETING", "value": 1}` | 1 instances | targeting.lua | None | Symmetrical | No | No |
| `STATE_RATE` | Modifier / calculation contribution | Multiplies the chance of the state named by dataId landing on the holder (0.5 = half as likely, 1.5 = half again). A rate is a SLOPE, not a switch: driving it to 0 makes the state vanishingly unlikely on the ordinary path, but a critical hit still forces it. For 'never, not even on a crit', use STATE_IMMUNITY -- and G1 rejects a rate of 0 outright, because anyone authoring that almost certainly means immunity. | usesDataId=True, type=multiplier | `{"code": "STATE_RATE", "dataId": "sleep", "value": 0.7}` | 5 instances | effects_core.lua, validator_core.lua | None | Symmetrical | No | No |
| `STATE_IMMUNITY` | Structural rule / capability | Absolute immunity to the state named by dataId: it never lands, including from a critical hit. Immunity is its own trait rather than a rate of zero (RPG Maker MZ's shape) so that rates can stay a slope all the way down -- a very high VIT creature is functionally unpoisonable without ever becoming categorically immune by accident -- and so 'never' is something an author states outright. | usesDataId=True, type=subject | `{"code": "STATE_IMMUNITY", "dataId": "sleep"}` | 3 instances | traits.lua, validator_core.lua | None | Symmetrical | No | No |
| `STATE_CATEGORY_IMMUNITY` | Structural rule / capability | As STATE_IMMUNITY, but for every state carrying the category named by dataId. This is a Ribbon's actual spelling (`common`), replacing the old STATE_CATEGORY_RATE-of-0 idiom. | usesDataId=True, type=subject | `{"code": "STATE_CATEGORY_IMMUNITY", "dataId": "common"}` | 1 instances | traits.lua, validator_core.lua | None | Symmetrical | No | No |
| `STATE_CATEGORY_RATE` | Modifier / calculation contribution | As STATE_RATE, but for every state carrying the category named by dataId (see engine.stateCategories). One trait covers a whole family, which is how a Ribbon blocks ordinary negative states without listing them -- and why `unique` exists, so death and authored curses sit outside such a blanket. Multiplies with STATE_RATE rather than replacing it. | usesDataId=True, type=multiplier | `{"code": "STATE_CATEGORY_RATE", "dataId": "physical", "value": 0.5}` | 5 instances | effects_core.lua, validator_core.lua | None | Symmetrical | No | No |
| `STATUS_SUCCESS` | Modifier / calculation contribution | Multiplies the holder's chance of inflicting states (0.25 = +25%). The attacker's half of the infliction chain, which is what lets a control specialist be better at landing conditions without every one of its skills authoring a higher chance. | usesDataId=False, type=percentSigned | `{"code": "STATUS_SUCCESS", "value": 0.2}` | 4 instances | effects_core.lua | None | Symmetrical | No | No |
| `DAMAGE_RATE` | Modifier / calculation contribution | Multiplies direct HP damage taken by the holder (0.5 = half). Multiplicative across sources, unlike the additive rate traits, because two independent protections should compound rather than sum past zero. Serves Defend, barriers, protective equipment and vulnerability states alike; it does not reduce authored indirect damage such as poison ticks. | usesDataId=False, type=multiplier | `{"code": "DAMAGE_RATE", "value": 0.82}` | 5 instances | effects_core.lua, item_presentation.lua | None | Symmetrical | No | No |
| `ITEM_EFFECT_RATE` | Modifier / calculation contribution | Multiplies the magnitude of items used by the holder (0.5 = +50%), RPG Maker Pharmacology-style. In battle the acting creature is the user; in the field the best living party carrier supplies the rate because field item use has no separate user selection. | usesDataId=False, type=percentSigned | `{"code": "ITEM_EFFECT_RATE", "value": 0.15}` | 8 instances | effects_core.lua, vitality.lua | None | Symmetrical | No | No |
| `HEAL_RATE` | Modifier / calculation contribution | Adds to HP healing performed by the holder's skills (0.25 = +25%). Does not amplify items or permanent gains. | usesDataId=False, type=percentSigned | `{"code": "HEAL_RATE", "value": 0.25}` | 2 instances | vitality.lua, effects.lua | None | Symmetrical | No | No |
| `TARGET_RATE` | Modifier / calculation contribution | Adds to the holder's weight when enemy AI randomly selects an opposing target. Base weight is 1; positive values implement Provoke. | usesDataId=False, type=signed | `{"code": "TARGET_RATE", "value": 2}` | 2 instances | targeting.lua | None | Symmetrical | No | No |
| `ELEMENT_RATE` | Modifier / calculation contribution | Multiplies damage received from the element named by dataId (0.5 = half, 1.5 = half again). Applied after identity affinity and multiplicative across sources. | usesDataId=True, type=multiplier | `{"code": "ELEMENT_RATE", "dataId": "Red", "value": 0.95}` | 20 instances | effects_core.lua, validator_core.lua | None | Symmetrical | No | No |
| `KILL_MP_RESTORE` | Resolved-event reaction / temporal behavior | Restores this flat amount of Summoner MP when the holder personally lands a killing blow, including an Execution. | usesDataId=False, type=signed | `{"code": "KILL_MP_RESTORE", "value": 12}` | 1 instances | effects_core.lua, renderer.lua | None | Party/Ally specific | Yes | No |
| `BARRIER_GRANT` | Source-local state / stateful behavior | Grants a generic stack barrier from an actor, passive, equipment piece, or state. `at` is battle_start or round_start; round_start defaults to refresh semantics so producers can restore a minimum without stockpiling. | usesDataId=False, type=none | `None` | 0 instances | barrier_schema.lua, interpreter_core.lua, barriers.lua | battle.json | Symmetrical | Yes | No |


### Category Counts
- **Modifier / calculation contribution**: 18
- **Structural rule / capability**: 13
- **Pending-transition interceptor / transformer**: 1
- **Resolved-event reaction / temporal behavior**: 8
- **Source-local state / stateful behavior**: 1
- **Mixed / problematic**: 4
- **Total**: 45

## Part 3 — "Half-data-driven" behavior

The following traits are merely detected by global handlers, while the actual behavior is owned globally:

1. **`SYMBIOSIS`** & **`PARASITE`**
   - **Authored source owns**: A number (the heal/damage amount).
   - **Global engine/flow owns**: Finding the neighbor (adjacency logic) and executing the command.
   - **Lifecycle fact needed**: `turn_end` or `action_end` resolved event.
2. **`MOVE_HEAL`**
   - **Authored source owns**: The amount to heal.
   - **Global engine/flow owns**: Triggering the heal every successful step.
   - **Lifecycle fact needed**: `exploration_step` resolved event.
3. **`POST_BATTLE_HEAL`**
   - **Authored source owns**: The amount to heal.
   - **Global engine/flow owns**: The victory rewards phase iteration.
   - **Lifecycle fact needed**: `battle_victory` resolved event.
4. **`GOLD_DIGGER`**
   - **Authored source owns**: The extra gold amount.
   - **Global engine/flow owns**: The base gold roll and calculation.
   - **Lifecycle fact needed**: `victory_reward_calculation` contribution channel.
5. **`KILL_MP_RESTORE`**
   - **Authored source owns**: The MP amount.
   - **Global engine/flow owns**: Detection of the kill fact in `awardKill`.
   - **Lifecycle fact needed**: `kill_resolved` reaction hook.
6. **`BARRIER_GRANT`**
   - **Authored source owns**: The barrier definition.
   - **Global engine/flow owns**: The grant execution at battle/round start.
   - **Lifecycle fact needed**: `battle_start` or `round_start` resolved event.

## Part 4 — Validate PR #313's model against current main

- **Number and nature of trait codes**: **Confirmed**. There are 42 trait codes, exactly as characterized.
- **Command count / command surfaces**: **Confirmed**. There are 93 commands and 7 contexts; `renderCommandList` in Studio is indeed universal.
- **Effect vocabulary**: **Confirmed**. 17 effect types.
- **Formula capabilities**: **Confirmed**. 52 restricted formula tokens.
- **Target vocabulary**: **Confirmed**.
- **Provenance/source handling**: **Understated**. `engine/traits.lua` `findAllSources` already robustly preserves origin instances (actor/equipment/passive/state).
- **Lifecycle limitations**: **Confirmed**.
- **State-local memory limitations**: **Confirmed**.
- **Studio shared command editor capabilities**: **Confirmed**.

## Part 5 — Pressure-map the 12 proposed authorability fixtures

1. **Mug**
   - **Existing primitives**: `combat.damage`, `target.gold`, formulas.
   - **Overlapped handler**: Hardcoded drops from enemies.
   - **Missing capability**: `action_resolved` / `damage_resolved` reaction.
   - **Missing category**: resolved event fact.
2. **Regen + double regen source**
   - **Existing primitives**: `RECOVERY_XP_BONUS` structure (basic stat sum).
   - **Overlapped handler**: Hardcoded regen loops in flows.
   - **Missing capability**: Generic calculation channel for `regeneration.amount`.
   - **Missing category**: calculation channel.
3. **Lifesteal from final damage**
   - **Existing primitives**: `combat.damage`, formulas.
   - **Overlapped handler**: `PARASITE` or hardcoded skill effects.
   - **Missing capability**: `damage_resolved` reaction filtering by skill.
   - **Missing category**: resolved event fact.
4. **Thorns/counter with counter-lineage guard**
   - **Existing primitives**: Action commands.
   - **Overlapped handler**: Hardcoded counter paths in legacy battle loop.
   - **Missing capability**: `damage_resolved` reaction with lineage ID guard to prevent recursion.
   - **Missing category**: deterministic ordering/lineage.
5. **Kill to Summoner MP and critical to state**
   - **Existing primitives**: Command lists, state infliction.
   - **Overlapped handler**: `KILL_MP_RESTORE` hardcode.
   - **Missing capability**: `kill_resolved` and `damage_resolved` reaction.
   - **Missing category**: resolved event fact.
6. **Magic Guard HP-to-MP redirect**
   - **Existing primitives**: Damage modification (e.g. `DAMAGE_RATE`).
   - **Overlapped handler**: Hardcoded damage resolution in `effects_core.lua`.
   - **Missing capability**: `damage_pending` interceptor redirect.
   - **Missing category**: pending transition.
7. **Undead conversion with bypass**
   - **Existing primitives**: `INVERT_TARGETING`.
   - **Overlapped handler**: Legacy typing checks.
   - **Missing capability**: `healing_pending` interceptor with conversion policy.
   - **Missing category**: pending transition.
8. **Guts clamp and consumable Death Ward**
   - **Existing primitives**: `EXECUTION_THRESHOLD` (sort of related).
   - **Overlapped handler**: `ON_PERMADEATH` flow hooks.
   - **Missing capability**: `death_pending` interceptor with source-local state consume.
   - **Missing category**: pending transition & source-local storage.
9. **Spell Shield / barrier variants**
   - **Existing primitives**: `BARRIER_GRANT`.
   - **Overlapped handler**: Hardcoded barrier systems.
   - **Missing capability**: Pending-transition interceptor with source-local memory.
   - **Missing category**: pending transition & source-local storage.
10. **Toxic counter, Bide, Mirror Move**
    - **Existing primitives**: None direct.
    - **Overlapped handler**: Bespoke logic per boss.
    - **Missing capability**: Source-local memory scope (`last_attacker`, `damage_taken`, `last_skill`).
    - **Missing category**: source-local storage & resolved event fact.
11. **Dynamic skill cost**
    - **Existing primitives**: `SP_COST_RATE`.
    - **Overlapped handler**: Hardcoded cost deductions.
    - **Missing capability**: `cost_pending` calculation channel.
    - **Missing category**: calculation channel.
12. **State replacement and target redirection**
    - **Existing primitives**: `STATE_IMMUNITY`.
    - **Overlapped handler**: Hardcoded `COVER_ALIGNED_BACK`.
    - **Missing capability**: `state_pending` and `target_pending` interceptors.
    - **Missing category**: pending transition & selector/reference.

## Concrete Observations for #308 Design

1. **Provenance exists**: The engine already collects source provenance robustly via `findAllSources`; the architectural gap is exposing it to commands, not collecting it.
2. **Traits act as data-bridges**: Most "problematic" traits are just static numbers queried by global flows (flows act as the logic layer).
3. **Lineage is crucial**: Without reaction lineage metadata, counters and reflections will trivially infinite-loop given the current engine's strict immediate-commit loop.
4. **Symmetry is fractured**: Traits like `MOVE_HEAL` and `GOLD_DIGGER` only apply to allies by design. Generic vocabulary needs filters rather than implicit ally-only rules.
5. **Shared Editor Surface is ready**: `renderCommandList` handles all scopes; attaching it to a `reaction` or `interceptor` source field in Studio requires no UI rewrites, just new JSON arrays.
6. **Data structure over scripting**: The existing `engine.json` registry supports strong validation; new interceptors must follow this rather than arbitrary Lua callbacks.
7. **Calculation Channels**: Modifiers (18 traits) are the largest category; a generic `calculation` channel with `subject` and `filter` could replace almost half the registry.
8. **Pending vs Resolved**: The distinction in #313 is strictly necessary. `EXECUTION_THRESHOLD` runs on resolved hits; `PENETRATION` must run before damage calculation.
9. **No dead code**: No trait is completely dead, but `BARRIER_GRANT` has 0 authored instances despite Lua implementation.
10. **Flows vs Reactions**: The flows (`battle.json`) already implement behavior using trait variables; moving to reactions shifts ownership from the global `battle.json` to the individual passive's `commands` array.
