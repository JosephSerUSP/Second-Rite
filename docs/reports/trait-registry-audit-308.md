# Trait Registry & Architecture Audit for #308/#313

## 1. Complete Current Trait-Code Table

| Code | Name | Value Shape | Primary Category | Symmetry | Description |
|---|---|---|---|---|---|
| `COVER_ALIGNED_BACK` | Cover Aligned Back | `None` | Structural | AI/Formation Dependent | A living, unrestricted front-row holder of this trait protects the living back-row creature in the same column from single-target coverable attacks. |
| `PARAM_PLUS` | Parameter + | `dataId (string/id)` | Modifier | Symmetrical | Adds a flat amount to a parameter. |
| `PARAM_RATE` | Parameter % | `dataId (string/id)` | Modifier | Symmetrical | Multiplies a parameter (1.2 = +20%). |
| `HIT` | Hit Rate | `value (number)` | Modifier | Symmetrical | Modifies hit chance (base 100%). |
| `EVA` | Evasion | `value (number)` | Modifier | Symmetrical | Modifies evade chance (base 0%). |
| `CRI` | Critical Rate | `value (number)` | Modifier | Symmetrical | Modifies crit chance (base 5%). The effective rate against a given target is CRI minus that target's CEV. |
| `CEV` | Critical Evasion | `value (number)` | Modifier | Symmetrical | Subtracts from an attacker's CRI against this holder. Worth twice what it looks like: a critical is also the universal status backdoor (it forces the affliction attached to the action past the chance roll), so being hard to crit means less burst damage AND fewer forced states. Deliberately trait-driven only -- gear and passives buy it, no stat derives it, or DEF would become a super-stat on top of mitigation and physical-ailment resistance. |
| `HRG` | HP Regen | `value (number)` | Mixed | Symmetrical | Regenerates a fraction of max HP per turn. |
| `POST_BATTLE_HEAL` | Post-Battle Heal | `value (number)` | Reaction | Player Party Only | Restores HP to the holder after victory. |
| `GOLD_DIGGER` | Bonus Gold | `value (number)` | Reaction | Player Party Only | Increases gold found. |
| `PARASITE` | Parasite | `None` | Mixed | Symmetrical | Drains HP from a nearby ally each turn. |
| `BATTLE_START_DAMAGE` | Ambush Damage | `value (number)` | Reaction | Symmetrical | Damages an enemy at battle start. |
| `MOVE_HEAL` | Heal on Move | `None` | Mixed | Symmetrical | Restores HP when moving on the map. |
| `RECOVERY_XP_BONUS` | Recovery XP Bonus | `value (number)` | Mixed | Player Party Only | Bonus XP at recovery sites. |
| `FLEE_CHANCE_BONUS` | Flee Chance + | `value (number)` | Mixed | Player Party Only | Increases the party's flee chance. |
| `ON_PERMADEATH` | Death Ward / On-Death Trigger | `{mode, charges, hpFraction}` | Interceptor | Symmetrical | Saves the creature from the end-of-battle permadeath sweep (REAP_FALLEN). mode: relic (never consumed) | charges (spends one per save, breaks at zero) | ward (consumed, creature survives) | revive (consumed, reaped then restored). Optional params: hpFraction, charges, levelCost. Defaults come from system.json permadeath. |
| `SEE_TRAPS` | See Traps | `value (number)` | Mixed | Player Party Only | Detects hidden traps (value = level). |
| `SEE_WALLS` | See Secrets | `value (number)` | Mixed | Player Party Only | Reveals breakable walls. |
| `SYMBIOSIS` | Symbiosis | `None` | Mixed | Symmetrical | Heals a neighboring ally each turn. |
| `INITIATIVE` | Initiative | `value (number)` | Mixed | Symmetrical | Chance to act first at battle start. |
| `REAR_GUARD` | Rear Guard | `value (number)` | Mixed | Symmetrical | Negates enemy first strikes. |
| `ELEMENT_CHANGE` | Element Change | `dataId (string/id)` | Structural | Symmetrical | Overrides the holder's elements with dataId while active. |
| `ELEMENT_ADD` | Element Add | `dataId (string/id)` | Structural | Symmetrical | Appends dataId to the holder's elements while active, deepening an existing alignment or adding a new one. Applied after ELEMENT_CHANGE. |
| `XP_RATE` | XP Rate + | `value (number)` | Modifier | Player Party Only | Multiplies experience gained (0.5 = +50%). |
| `CRAFT_YIELD_RATE` | Craft Yield + | `value (number)` | Modifier | Symmetrical | Multiplies Item Creation yield score (0.25 = +25%). |
| `PENETRATION` | Armor Penetration | `value (number)` | Modifier | Symmetrical | Ignores this share of the target's defending stat before the damage curve (0.3 = 30%). Adds to an effect's own `penetration` and clamps at 1. Applied to the defense rather than the damage on purpose: against a soft target it is worth almost nothing and against a wall it is worth a great deal, which is what separates it from simply hitting harder. |
| `EXECUTION_THRESHOLD` | Execution Threshold | `value (number)` | Interceptor | Symmetrical | After the holder's damage lands, a surviving target at or below this fraction of its Max HP is finished outright (0.2 = a fifth). A finisher rather than a gamble: it is checked after the hit, so it closes a wounded enemy and does nothing to a healthy one. |
| `EXECUTION_RESIST` | Execution Resistance | `value (number)` | Modifier | Symmetrical | Subtracts from an attacker's EXECUTION_THRESHOLD against this holder; 1.0 is outright protection (Safety Bit). Deliberately separate from state resistance -- execution is not a state, and it subtracts rather than rolling, so it costs no randomness and partial resistance means something exact. |
| `FORCE_ACTION` | Forced Action | `dataId (string/id)` | Structural | Symmetrical | The holder can only take the skill named by dataId, whatever it or the player chose. Applied where the turn queue is built, so it constrains an AI enemy and a player creature by the same rule -- Berserk forcing a basic Attack is one authored state, not a branch in the battle code. Target is picked by the forced skill's own targeting spec. |
| `INVERT_TARGETING` | Invert Targeting | `None` | Structural | Symmetrical | Inverts targeting groups for the holder while active (`enemy` side targets allies, `ally` side targets enemies). Used by Charm and confusion effects. |
| `STATE_RATE` | State Susceptibility % | `dataId (string/id)` | Modifier | Symmetrical | Multiplies the chance of the state named by dataId landing on the holder (0.5 = half as likely, 1.5 = half again). A rate is a SLOPE, not a switch: driving it to 0 makes the state vanishingly unlikely on the ordinary path, but a critical hit still forces it. For 'never, not even on a crit', use STATE_IMMUNITY -- and G1 rejects a rate of 0 outright, because anyone authoring that almost certainly means immunity. |
| `STATE_IMMUNITY` | State Immunity | `dataId (string/id)` | Structural | Symmetrical | Absolute immunity to the state named by dataId: it never lands, including from a critical hit. Immunity is its own trait rather than a rate of zero (RPG Maker MZ's shape) so that rates can stay a slope all the way down -- a very high VIT creature is functionally unpoisonable without ever becoming categorically immune by accident -- and so 'never' is something an author states outright. |
| `STATE_CATEGORY_IMMUNITY` | State Category Immunity | `dataId (string/id)` | Structural | Symmetrical | As STATE_IMMUNITY, but for every state carrying the category named by dataId. This is a Ribbon's actual spelling (`common`), replacing the old STATE_CATEGORY_RATE-of-0 idiom. |
| `STATE_CATEGORY_RATE` | State Category % | `dataId (string/id)` | Modifier | Symmetrical | As STATE_RATE, but for every state carrying the category named by dataId (see engine.stateCategories). One trait covers a whole family, which is how a Ribbon blocks ordinary negative states without listing them -- and why `unique` exists, so death and authored curses sit outside such a blanket. Multiplies with STATE_RATE rather than replacing it. |
| `STATUS_SUCCESS` | Status Success + | `value (number)` | Modifier | Symmetrical | Multiplies the holder's chance of inflicting states (0.25 = +25%). The attacker's half of the infliction chain, which is what lets a control specialist be better at landing conditions without every one of its skills authoring a higher chance. |
| `DAMAGE_RATE` | Damage Taken % | `value (number)` | Modifier | Symmetrical | Multiplies direct HP damage taken by the holder (0.5 = half). Multiplicative across sources, unlike the additive rate traits, because two independent protections should compound rather than sum past zero. Serves Defend, barriers, protective equipment and vulnerability states alike; it does not reduce authored indirect damage such as poison ticks. |
| `ITEM_EFFECT_RATE` | Item Effect + | `value (number)` | Modifier | Symmetrical | Multiplies the magnitude of items used by the holder (0.5 = +50%), RPG Maker Pharmacology-style. In battle the acting creature is the user; in the field the best living party carrier supplies the rate because field item use has no separate user selection. |
| `HEAL_RATE` | Healing Skill + | `value (number)` | Modifier | Symmetrical | Adds to HP healing performed by the holder's skills (0.25 = +25%). Does not amplify items or permanent gains. |
| `TARGET_RATE` | Target Rate + | `value (number)` | Modifier | AI/Formation Dependent | Adds to the holder's weight when enemy AI randomly selects an opposing target. Base weight is 1; positive values implement Provoke. |
| `ELEMENT_RATE` | Element Damage Taken % | `dataId (string/id)` | Modifier | Symmetrical | Multiplies damage received from the element named by dataId (0.5 = half, 1.5 = half again). Applied after identity affinity and multiplicative across sources. |
| `KILL_MP_RESTORE` | Summoner MP on Kill | `value (number)` | Reaction | Symmetrical | Restores this flat amount of Summoner MP when the holder personally lands a killing blow, including an Execution. |
| `BARRIER_GRANT` | Barrier Grant | `{at, mode, amount}` | Mixed | Symmetrical | Grants a generic stack barrier from an actor, passive, equipment piece, or state. `at` is battle_start or round_start; round_start defaults to refresh semantics so producers can restore a minimum without stockpiling. |

## 2. Consumer/Use-Site Table

| Code | Primary Engine Consumers | Global Flow/Command Consumers | Representative Uses | Dependency on Source Identity |
|---|---|---|---|---|
| `COVER_ALIGNED_BACK` | `traits.findAllSources` | - | Equips/Passives/States | No |
| `PARAM_PLUS` | `traits.getParam` | - | Equips/Passives/States | No |
| `PARAM_RATE` | `traits.getParam` | - | Equips/Passives/States | No |
| `HIT` | `traits.getRate` | - | Equips/Passives/States | No |
| `EVA` | `traits.getRate` | - | Equips/Passives/States | No |
| `CRI` | `traits.getRate` | - | Equips/Passives/States | No |
| `CEV` | `traits.getRate` | - | Equips/Passives/States | No |
| `HRG` | `traits.getRate` | interpreter_core.lua:881 (Regen tick) | Equips/Passives/States | No |
| `POST_BATTLE_HEAL` | - | Global flow/Formula/Command, engine_state.lua (Victory) | Equips/Passives/States | No |
| `GOLD_DIGGER` | - | Global flow/Formula/Command, formula.lua (Victory) | Equips/Passives/States | No |
| `PARASITE` | - | Global flow/Formula/Command | Equips/Passives/States | No |
| `BATTLE_START_DAMAGE` | - | Global flow/Formula/Command | Equips/Passives/States | No |
| `MOVE_HEAL` | - | Global flow/Formula/Command | Equips/Passives/States | No |
| `RECOVERY_XP_BONUS` | - | Global flow/Formula/Command | Equips/Passives/States | No |
| `FLEE_CHANCE_BONUS` | - | Global flow/Formula/Command | Equips/Passives/States | No |
| `ON_PERMADEATH` | `traits.findAllSources` | - | Equips/Passives/States | Yes (breaks correct ward item) |
| `SEE_TRAPS` | - | Global flow/Formula/Command | Equips/Passives/States | No |
| `SEE_WALLS` | - | Global flow/Formula/Command | Equips/Passives/States | No |
| `SYMBIOSIS` | - | Global flow/Formula/Command | Equips/Passives/States | No |
| `INITIATIVE` | - | Global flow/Formula/Command | Equips/Passives/States | No |
| `REAR_GUARD` | - | Global flow/Formula/Command | Equips/Passives/States | No |
| `ELEMENT_CHANGE` | `traits.getElements` | - | Weapons/Stances | No |
| `ELEMENT_ADD` | `traits.getElements` | - | Weapons/Stances | No |
| `XP_RATE` | `traits.getRate` | - | Equips/Passives/States | No |
| `CRAFT_YIELD_RATE` | `traits.getRate` | - | Equips/Passives/States | No |
| `PENETRATION` | `traits.getRate` | - | Equips/Passives/States | No |
| `EXECUTION_THRESHOLD` | `traits.findAllSources` | - | Equips/Passives/States | No |
| `EXECUTION_RESIST` | `traits.getRate` | - | Equips/Passives/States | No |
| `FORCE_ACTION` | `traits.findAllSources` | - | Equips/Passives/States | No |
| `INVERT_TARGETING` | - | - | Equips/Passives/States | No |
| `STATE_RATE` | `traits.getRate` | - | Equips/Passives/States | No |
| `STATE_IMMUNITY` | `traits.hasStateImmunity` | - | Ribbons/Bosses | No |
| `STATE_CATEGORY_IMMUNITY` | `traits.hasStateImmunity` | - | Ribbons/Bosses | No |
| `STATE_CATEGORY_RATE` | `traits.getRate` | - | Equips/Passives/States | No |
| `STATUS_SUCCESS` | `traits.getRate` | - | Equips/Passives/States | No |
| `DAMAGE_RATE` | `traits.getRate` | - | Equips/Passives/States | No |
| `ITEM_EFFECT_RATE` | `traits.getRate` | - | Equips/Passives/States | No |
| `HEAL_RATE` | `traits.getRate` | - | Equips/Passives/States | No |
| `TARGET_RATE` | `traits.getRate` | - | Equips/Passives/States | No |
| `ELEMENT_RATE` | `traits.getRate` | - | Equips/Passives/States | No |
| `KILL_MP_RESTORE` | `traits.getRate` | effects_core.lua:374 (On Kill) | Equips/Passives/States | No |
| `BARRIER_GRANT` | `traits.findAllSources` | - | Equips/Passives/States | Yes (stack ownership) |

## 3. Category Counts

- **Modifier / Calculation Contribution:** 18
- **Structural Rule / Capability:** 7
- **Pending-Transition Interceptor / Transformer:** 2
- **Resolved-Event Reaction / Temporal Behavior:** 4
- **Source-Local State / Stateful Behavior:** 0
- **Mixed / Problematic (Half-data-driven):** 11
- **Total Registered Codes:** 42


## 4. Half-Data-Driven Behavior List

### SYMBIOSIS / PARASITE
Authored source owns: merely the code.
Global engine owns: the logic in `interpreter_core.lua`.
Required semantic fact: `round_start` or `turn_start` hook with a 'neighbor' target selector.

### MOVE_HEAL
Authored source owns: merely the code.
Global engine owns: Map movement tick handler.
Required semantic fact: `on_step` hook.

### POST_BATTLE_HEAL
Authored source owns: merely the code.
Global engine owns: victory flow.
Required semantic fact: `on_victory` resolved event reaction.

### KILL_MP_RESTORE
Authored source owns: the flat rate value.
Global engine owns: hardcoded lookup in `effects_core.lua`.
Required semantic fact: `on_kill` resolved event reaction.

### BARRIER_GRANT
Authored source owns: the config.
Global engine owns: execution in `barriers.lua`.
Required semantic fact: `battle_start` and `round_start` lifecycle hooks.

### BATTLE_START_DAMAGE
Authored source owns: merely the code.
Global engine owns: `engine_state.lua` party trait reading.
Required semantic fact: `battle_start` hook allowing damage commands.

### GOLD_DIGGER
Authored source owns: merely the code.
Global engine owns: `formula.lua` victory flow.
Required semantic fact: `on_victory` calculating rewards modifier.

## 5. Dead/Unused/Duplicate Vocabulary

- `SACRIFICE_EXP_RATE`: Actively used in `engine/interpreter_core.lua` via `traits.getRate(b, "SACRIFICE_EXP_RATE", session)` but is **not registered in `data/engine.json`**.
- `TRAIT_HEAL`: Explicitly documented as "absorbed/former" in `interpreter_core.lua:656`, demonstrating a past successful migration from a bespoke trait code to the generic `cmd.trait` property.

## 6. PR #313 Factual Validation against Current Main

- **Number and nature of trait codes:** *Confirmed.* 42 registered trait codes exist, heavily relying on flat value modifications rather than dynamic behavior.
- **Command count / surfaces:** *Confirmed.* The 7 command contexts and a shared editor (`renderCommandList`) exist, verifying the "one editor everywhere" claim.
- **Effect vocabulary:** *Confirmed.* 17 effect types exist (e.g. `add_status`, `remove_status`).
- **Formula capabilities:** *Confirmed.* The sandboxed formula evaluation exists (e.g., `a.trait.CODE`).
- **Target vocabulary / Selectors:** *Confirmed.* Selectors like "neighbor" are hardcoded inside traits like `SYMBIOSIS` rather than being generic selectors.
- **Provenance / Source handling:** *Confirmed.* Provenance tracking exists (`getActiveObjects` / `findAllSources`), primarily used by `ON_PERMADEATH` to break the *exact* ward item.
- **Lifecycle limitations:** *Confirmed.* Lifecycle hooks are currently global engine states (checked via loops over active objects) rather than authored event triggers on traits themselves.
- **State-local memory:** *Confirmed.* States do not currently own local memory. Escalating counters (e.g., Toxic) are not natively expressible without bespoke engine extensions.

## 7. Fixture Pressure Map

Mapping the 12 likely authorability fixtures against current capabilities:

1. **Regen/DoT (HRG)**: Overlaps hardcoded `HRG`.
   - *Missing capability:* Resolved event fact (turn/round start).
2. **Counter/Thorns**: Cannot be authored dynamically.
   - *Missing capability:* Resolved event reaction (`on_hit`/`on_damage`) + target reference (`attacker`).
3. **Lifesteal (TRAIT_HEAL)**: Supported via `cmd.trait` hack.
   - *Missing capability:* Resolved event reaction (`on_deal_damage`) with calculation channel.
4. **Guts/Death Ward (ON_PERMADEATH)**: Uses hardcoded `ON_PERMADEATH`.
   - *Missing capability:* Pending transition interceptor + source-local storage/provenance (breaking ward).
5. **Magic Guard / Shield**: No current support.
   - *Missing capability:* Pending transition interceptor (resource redirection before commit).
6. **Mirror Move**: No current support.
   - *Missing capability:* Source-local storage (last skill) + resolved event fact.
7. **Toxic (Escalating)**: No current support.
   - *Missing capability:* Source-local storage (counter) + resolved event reaction.
8. **Provoke/Aggro (TARGET_RATE)**: Overlaps `TARGET_RATE`.
   - *Missing capability:* Calculation channel for AI weights.
9. **Mug (Gold on Hit)**: No current support.
   - *Missing capability:* Resolved event reaction (`on_damage`) + resource operation.
10. **Undead (Healing = Damage)**: No current support.
    - *Missing capability:* Pending transition interceptor (reversing effect values before commit).
11. **Spell Shield (Cancel 1st Effect)**: No current support.
    - *Missing capability:* Pending transition interceptor (canceling effect) + source-local storage (charges).
12. **Bide (Store Damage)**: No current support.
    - *Missing capability:* Resolved event reaction (`on_damaged`), source-local storage, calculation channel.

## 8. 8 Strategic Observations for #308

1. **Additive Engine Assumption:** The engine heavily relies on `traits.getRate` for additive accumulation across sources. A generic modifier API must explicitly support additive vs. multiplicative compounding.
2. **Provenance is Proven Necessity:** `traits.findAllSources` proves the engine *already needs* provenance (e.g. `ON_PERMADEATH` breaking the correct item). The new API must preserve `getActiveObjects` lineage.
3. **Missing Lifecycle Hooks:** Hardcoded half-data-driven traits (`SYMBIOSIS`, `PARASITE`, `MOVE_HEAL`) reveal exactly which lifecycle hooks (`round_start`, `on_step`) and selectors (`neighbor`) are desperately missing from the generic command system.
4. **Schema Drift Hazard:** `SACRIFICE_EXP_RATE` is actively used in the codebase but entirely unregistered in `data/engine.json`, indicating drift and the danger of untyped string-based trait codes.
5. **Interceptors Exist:** `EXECUTION_THRESHOLD` demonstrates a successful "interceptor" model evaluated before effect resolution, proving the architectural space for pending-transition interception already exists.
6. **Structural Traits as Spaghetti:** `INVERT_TARGETING` shows that structural rules currently act as global flags overriding behavior deep in AI/targeting logic. The new system must find a way to express structural capabilities cleanly.
7. **Migration Precedent:** The legacy `TRAIT_HEAL` was successfully migrated to a generic command field (`cmd.trait`). This is proof that migrating bespoke traits into generic command properties is a viable, established pattern here.
8. **State-Local Memory Blockage:** State-local memory is completely missing, entirely blocking fixtures like `Toxic` or `Bide` unless implemented as bespoke Engine variables. This is the biggest gap in the current data model.
