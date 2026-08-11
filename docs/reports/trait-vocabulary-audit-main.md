# Trait Vocabulary Audit against Current Main
## Part 1 & 2: Trait Code Census and Classification
| Code | Authored Shape | Primary Category | Symmetry | Prov. Dependent | Engine Consumers | JSON/Flow Consumers | Representative Authored Uses |
|---|---|---|---|---|---|---|---|
| `COVER_ALIGNED_BACK` | value | Structural rule / capability | Yes | No | presentation/renderer.lua, engine/battle.lua | None | Passives |
| `PARAM_PLUS` | value + dataId | Modifier / calculation contribution | Yes | No | engine/craft.lua, engine/engine_state.lua, engine/formula.lua | None | Items/States/Passives |
| `PARAM_RATE` | value + dataId | Modifier / calculation contribution | Yes | No | engine/engine_state.lua, engine/formula.lua | None | Items/States/Passives |
| `HIT` | value | Modifier / calculation contribution | Yes | No | engine/engine_state.lua, engine/interpreter_core.lua | None | Items/States/Passives |
| `EVA` | value | Modifier / calculation contribution | Yes | No | engine/engine_state.lua, engine/interpreter_core.lua | None | Items/States/Passives |
| `CRI` | value | Modifier / calculation contribution | Yes | No | engine/engine_state.lua, engine/effects_core.lua | None | Items/States/Passives |
| `CEV` | value | Modifier / calculation contribution | Yes | No | engine/effects_core.lua | None | Items/States/Passives |
| `HRG` | value | Mixed / problematic | Yes | No | engine/engine_state.lua, engine/interpreter_core.lua | None | Items/States/Passives |
| `POST_BATTLE_HEAL` | value | Resolved-event reaction / temporal behavior | Party-Only | No | engine/engine_state.lua | data/flows/battle.json, data/flows/exploration.json | Items/States/Passives |
| `GOLD_DIGGER` | value | Mixed / problematic | Party-Only | No | engine/formula.lua | data/flows/battle.json | Items/States/Passives |
| `PARASITE` | value | Mixed / problematic | Party-Only | No | engine/interpreter_core.lua | data/flows/battle.json | Items/States/Passives |
| `BATTLE_START_DAMAGE` | value | Resolved-event reaction / temporal behavior | Party-Only | No | engine/engine_state.lua, engine/interpreter_core.lua | data/troops.json | Passives, Troops |
| `MOVE_HEAL` | value | Mixed / problematic | Party-Only | No | engine/formula.lua, engine/interpreter_core.lua | data/flows/exploration.json | Passives |
| `RECOVERY_XP_BONUS` | value | Mixed / problematic | Party-Only | No | engine/engine_state.lua | data/commonEvents.json | Items/States/Passives |
| `FLEE_CHANCE_BONUS` | value | Mixed / problematic | Party-Only | No | engine/formula.lua, engine/effects_core.lua | data/flows/battle.json | Items/States/Passives |
| `ON_PERMADEATH` | mode/charges/restore/value | Pending-transition interceptor / transformer | Yes | Yes | engine/engine_state.lua, engine/interpreter_core.lua | data/flows/battle.json, data/flows/exploration.json | Items/States/Passives |
| `SEE_TRAPS` | value | Structural rule / capability | Party-Only | No | presentation/renderer.lua, engine/detection.lua | None | Passives, Equipment |
| `SEE_WALLS` | value | Structural rule / capability | Party-Only | No | presentation/renderer.lua, engine/detection.lua | None | Items/States/Passives |
| `SYMBIOSIS` | value | Mixed / problematic | Party-Only | No | engine/interpreter_core.lua | data/flows/battle.json | Items/States/Passives |
| `INITIATIVE` | value | Structural rule / capability | Yes | No | engine/battle.lua | None | Items/States/Passives |
| `REAR_GUARD` | value | Structural rule / capability | Yes | No | engine/battle.lua | None | Items/States/Passives |
| `ELEMENT_CHANGE` | value + dataId | Structural rule / capability | Yes | No | engine/craft.lua | None | Items/States/Passives |
| `ELEMENT_ADD` | value + dataId | Structural rule / capability | Yes | No | engine/traits.lua | None | Items/States/Passives |
| `XP_RATE` | value | Modifier / calculation contribution | Yes | No | engine/session.lua | None | Items/States/Passives |
| `CRAFT_YIELD_RATE` | value | Modifier / calculation contribution | Yes | No | engine/craft.lua | tools/editor/templates/scenes/crafting.json | Items/States/Passives |
| `PENETRATION` | value | Structural rule / capability | Yes | No | engine/effects_core.lua | None | Items/States/Passives |
| `EXECUTION_THRESHOLD` | value | Structural rule / capability | Yes | No | engine/effects_core.lua | None | Items/States/Passives |
| `EXECUTION_RESIST` | value | Structural rule / capability | Yes | No | engine/effects_core.lua | None | Items/States/Passives |
| `FORCE_ACTION` | value + dataId | Structural rule / capability | Yes | No | engine/battle.lua | None | Items/States/Passives |
| `INVERT_TARGETING` | value | Structural rule / capability | Yes | No | engine/targeting.lua | None | Items/States/Passives |
| `STATE_RATE` | value + dataId | Modifier / calculation contribution | Yes | No | engine/effects_core.lua | None | Items/States/Passives |
| `STATE_IMMUNITY` | value + dataId | Structural rule / capability | Yes | No | engine/effects_core.lua | None | Items/States/Passives |
| `STATE_CATEGORY_IMMUNITY` | value + dataId | Structural rule / capability | Yes | No | engine/effects_core.lua | None | Items/States/Passives |
| `STATE_CATEGORY_RATE` | value + dataId | Modifier / calculation contribution | Yes | No | engine/effects_core.lua | None | Items/States/Passives |
| `STATUS_SUCCESS` | value | Modifier / calculation contribution | Yes | No | engine/effects_core.lua | None | Items/States/Passives |
| `DAMAGE_RATE` | value | Modifier / calculation contribution | Yes | No | engine/effects_core.lua | None | Items/States/Passives |
| `ITEM_EFFECT_RATE` | value | Modifier / calculation contribution | Yes | No | engine/effects_core.lua | None | Items/States/Passives |
| `HEAL_RATE` | value | Modifier / calculation contribution | Yes | No | engine/effects.lua | None | Items/States/Passives |
| `TARGET_RATE` | value | Modifier / calculation contribution | Yes | No | engine/targeting.lua | None | Items/States/Passives |
| `ELEMENT_RATE` | value + dataId | Modifier / calculation contribution | Yes | No | engine/effects_core.lua | None | Items/States/Passives |
| `KILL_MP_RESTORE` | value | Resolved-event reaction / temporal behavior | Yes | No | presentation/renderer.lua, engine/effects_core.lua | None | Items/States/Passives |
| `BARRIER_GRANT` | at/amount/duration | Source-local state / stateful behavior | Yes | Yes | engine/interpreter_core.lua | data/flows/battle.json | States, Equipment |

## Category Counts
- Modifier / calculation contribution: 16
- Structural rule / capability: 14
- Pending-transition interceptor / transformer: 1
- Resolved-event reaction / temporal behavior: 3
- Source-local state / stateful behavior: 1
- Mixed / problematic: 7


## Part 3 - Half-data-driven behavior

### SYMBIOSIS
**Description:** Heals a neighboring ally each turn.
1. **What the authored source owns:** The `SYMBIOSIS` string marker and any numeric value on the equipment/state.
2. **What the global engine/flow owns:** The hardcoded check in `engine/interpreter_core.lua` inside `FOR_EACH` over slots, the adjacency logic `slotNeighbor`, and the healing execution.
3. **Required lifecycle fact to expose:** `on_round_end` with `source`, `target`, and `adjacency` references, allowing a formula to execute a dynamic heal command.

### PARASITE
**Description:** Drains HP from a nearby ally each turn.
1. **What the authored source owns:** The `PARASITE` string marker and value.
2. **What the global engine/flow owns:** The hardcoded `PARASITE` loop in `interpreter_core.lua` to drain neighbors.
3. **Required lifecycle fact to expose:** `on_round_end` context capable of chaining an HP drain command against `neighbor` relative to the source.

### MOVE_HEAL
**Description:** Restores HP when moving on the map.
1. **What the authored source owns:** The `MOVE_HEAL` string marker.
2. **What the global engine/flow owns:** `engine/formula.lua` and `exploration.json` which check for the presence of this trait during movement steps to issue healing.
3. **Required lifecycle fact to expose:** `on_map_step` event fact capable of intercepting movement to apply arbitrary commands.

### POST_BATTLE_HEAL
**Description:** Restores HP to the holder after victory.
1. **What the authored source owns:** The `POST_BATTLE_HEAL` string.
2. **What the global engine/flow owns:** `data/flows/battle.json` has a specific victory flow step that iterates all battlers and applies this trait's heal.
3. **Required lifecycle fact to expose:** `on_victory` resolved event reaction capable of triggering a heal command.

### GOLD_DIGGER
**Description:** Increases gold found.
1. **What the authored source owns:** The `GOLD_DIGGER` string marker.
2. **What the global engine/flow owns:** `engine/formula.lua` (and battle/exploration victory formulas) which directly queries `party.trait.GOLD_DIGGER`.
3. **Required lifecycle fact to expose:** A generic `on_reward_calculation` or calculation channel hook for `reward_gold`.

### KILL_MP_RESTORE
**Description:** Restores this flat amount of Summoner MP when the holder personally lands a killing blow, including an Execution.
1. **What the authored source owns:** The trait code and the flat value.
2. **What the global engine/flow owns:** `engine/effects_core.lua` which explicitly checks `KILL_MP_RESTORE` when applying lethal damage.
3. **Required lifecycle fact to expose:** `on_kill` resolved fact reaction with access to the attacker and the global MP resource pool.

### BARRIER_GRANT
**Description:** Grants a generic stack barrier from an actor, passive, equipment piece, or state. `at` is battle_start or round_start; round_start defaults to refresh semantics so producers can restore a minimum without stockpiling.
1. **What the authored source owns:** The `at` (timing), `amount`, and `duration` values.
2. **What the global engine/flow owns:** The barrier lifecycle management in `engine/interpreter_core.lua` explicitly parsing the `BARRIER_GRANT` trait.
3. **Required lifecycle fact to expose:** `on_battle_start` and `on_round_start` resolved events coupled with true source-local state storage that isn't hardcoded as "barrier".

### BATTLE_START_DAMAGE
**Description:** Damages an enemy at battle start.
1. **What the authored source owns:** The trait code and value.
2. **What the global engine/flow owns:** `data/troops.json` and engine scripts that check for this trait to initialize ambush damage.
3. **Required lifecycle fact to expose:** `on_battle_start` resolved event capable of applying arbitrary effects.

### RECOVERY_XP_BONUS
**Description:** Bonus XP at recovery sites.
1. **What the authored source owns:** The trait code.
2. **What the global engine/flow owns:** `data/commonEvents.json` explicitly checking the party's trait rate when resting at campsites.
3. **Required lifecycle fact to expose:** A generic `on_recovery` or calculation channel intercept for XP gains.

### FLEE_CHANCE_BONUS
**Description:** Increases the party's flee chance.
1. **What the authored source owns:** The trait code and value.
2. **What the global engine/flow owns:** The global escape formula explicitly querying this trait.
3. **Required lifecycle fact to expose:** Calculation channel modification for `flee_chance`.



## Part 4 - PR #313 Factual Validation against Current Main

### Number and nature of trait codes
**Confirmed.** `data/engine.json` confirms exactly 42 trait codes are currently registered.

### Command count / command surfaces
**Confirmed.** `data/engine.json` lists exactly 93 commands under `commands`. There are 7 distinct contexts.

### Effect vocabulary
**Confirmed.** `data/engine.json` lists exactly 17 `effectTypes`.

### Target vocabulary
**Confirmed.** The current target specs have side/shape/cover configurations but no dynamic selector or target-redirecting primitive.

### Provenance/source handling
**Confirmed.** `engine/traits.lua` `findAllSources` and `getActiveObjects` retain source and state/equipment provenance (especially for `ON_PERMADEATH` and `BARRIER_GRANT`).

### Lifecycle limitations
**Confirmed.** The current JSON orchestrates battle phases (start, round, end) but lacks arbitrary semantic intercepts for `action_started`, `cost_pending`, `target_pending`, or arbitrary post-damage/post-heal events.

### State-local memory limitations
**Confirmed.** Aside from the newly structured `BARRIER_GRANT` which adds stack barriers and duration limits to traits, generic state instances do not have mutable authorable properties exposed.

### Formula capabilities
**Confirmed.** There are 52 formula help tokens, sandboxed formulas are supported, but there are no dynamic cost interceptors in the formula contexts.

### Studio shared command editor capabilities
**Confirmed.** Tools like `entity-forms.js` and `widgets.js` show strong global editing support for these fixed schemas.




## Part 5 - Pressure Map of the 12 Proposed Authorability Fixtures

| Fixture | Existing Primitives | Overlapped Hardcode/Trait | Smallest Missing Capability | Missing Capability Type |
|---|---|---|---|---|
| 1. Mug (damage to gold) | finalDamage formula, actions | None | Resolved damage event intercept | resolved event fact |
| 2. Regen with multiplier | HRG, tick commands | HRG | Calculation channel for regen rates | calculation channel |
| 3. Lifesteal | hp_drain skill property | None | Post-damage resolve hook | resolved event fact |
| 4. Thorns/Counter | None | None | Target/Attacker reference at damage time | selector/reference |
| 5. Kill to MP & Crit to State | KILL_MP_RESTORE, STATUS_SUCCESS | KILL_MP_RESTORE | Resolved kill/critical reaction | resolved event fact |
| 6. Magic Guard (MP Redirect) | None | None | Pending HP damage interception | pending transition |
| 7. Undead Conversion | Target types | None | Pending healing interception/conversion | pending transition |
| 8. Guts & Death Ward | ON_PERMADEATH | ON_PERMADEATH | Generic lethal transition intercept | pending transition |
| 9. Spell Shield | BARRIER_GRANT | BARRIER_GRANT | Generic first-action cancellation | pending transition |
| 10. Toxic/Bide/Mirror | STATE_TICKS | STATE_TICKS | Source-local state mutation/tracking | source-local storage |
| 11. Dynamic Cost | Formulas | None | Cost interceptor / calculation modification | pending transition |
| 12. State Replace/Redirect | add/remove state commands | None | Pending state interception/atomicity | pending transition |





## Dead/Unused/Duplicate Vocabulary

- `CEV` (Critical Evasion) is purely trait-driven and actively used to calculate effective critical rate.
- `BATTLE_START_DAMAGE` is relatively niche, currently seen in some troop/passive definitions.
- There are no definitively dead or unused trait codes. All 42 traits present in `data/engine.json` are hooked up to global/system handlers and are used by at least one json data file.


## Observations for #308 Design

1. The engine heavily relies on fixed trait codes being queried manually by systems (like `HRG` in `interpreter_core.lua` or `MOVE_HEAL` in map logic), tying generic behaviors to explicit C-like engine checks.
2. Provenance tracking is actually very strong. `engine/traits.lua` `findAllSources` and `getActiveObjects` carefully package traits with their origin (actor, passive, equipment, state, savor), meaning the foundation for provenance-aware reactions is already in place.
3. Asymmetric rules are pervasive. Several mixed/problematic traits are hard-coded to party only (e.g., `MOVE_HEAL`, `GOLD_DIGGER`, `SEE_TRAPS`, `POST_BATTLE_HEAL`), showing that #308 must deal with side-specific triggers explicitly.
4. `ON_PERMADEATH` and `BARRIER_GRANT` show that the engine has begun moving towards structured intercepts, taking complex shapes (`mode/charges/restore/value` and `at/amount/duration`), confirming the pressure towards dynamic source-local states.
5. The `KILL_MP_RESTORE` and `BATTLE_START_DAMAGE` traits act as pseudo-reactions but only for specific fixed results, indicating a need for a generic `resolved-event` handler system.
6. The majority of traits (30 out of 42) fall clearly into standard Modifiers or Structural roles; only a minority act as problematic half-data-driven temporal behaviors.
7. `BARRIER_GRANT` handles duration and stacking by managing encounter-local states internally, meaning the engine has some mechanism for state-local memory, but it's hardcoded to barriers rather than generic authored states.
8. `HRG` (HP Regen) being a generic sum doesn't allow for provenance-based modifications or streak limits.
9. Any attempt to migrate the 7 'Mixed/Problematic' traits will directly require the proposed "Resolved-event reaction" and "Pending-transition interceptor" APIs.
