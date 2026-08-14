# Authored state scopes evidence audit — 2026-08-13

**Issue:** #400 — Define authored state scopes: persistent Variables, self state, and transient locals  
**Baseline:** `main` at `63010d0e3864a17c0a41d5d6c6ca674ad8d0f735`  
**Status:** evidence/architecture audit; documentation only  
**Refresh:** includes merged #395 and #399 and the current draft evidence in PR #412

This report reconstructs the completed #400 research recorded in the latest issue comment and refreshes only evidence that could have changed on current `main`. It does **not** reopen the architecture from first principles. The durable design derived from this evidence is recorded separately in `docs/design/authored-state-scopes.md`.

## 1. Evidence and design are intentionally separated

### Repository evidence

The current engine has one command spelling, `SET_VAR`, but that command does not define a storage lifetime. `engine/interpreter_core.lua` writes the value into whatever table the host supplied as `ctx.v`; the formula context exposes that same table as `v`. Lifetime therefore comes from the **owner/host**, not from the `SET_VAR` noun.

Current owners are visibly different:

- `engine/scene_host.lua` owns one `v = {}` table per pushed Scene instance and binds `ctx.v = state.v` before a Scene hook runs.
- `engine/flow.lua` explicitly documents `v` as **flow-locals**; Flow and Troop command lists use `SET_VAR` for scratch intermediates.
- `engine/session.lua` owns saved playthrough/domain state such as inventory, flags, MP, rosters, creature identity, map caches and recruit nodes.
- `engine/savegame.lua` serializes selected `GameSession` state and current/cached Map runtime state. Scene-stack `v` is not part of that payload.
- Map Event pages already resolve against persistent/domain predicates such as flags, quest status and inventory, while `eventOverrides`, `mapStates` and `mapPresentationOverrides` are specialized persistent Map/Event mechanisms rather than a generic Variable store.

### Design conclusions

The evidence supports naming state by lifetime/owner instead of perpetuating the current overloaded `v` spelling:

- **Variable**: persistent saved game/playthrough authored state.
- **Switch**: boolean-valued persistent authored state with dedicated ON/OFF authoring ergonomics; it need not be a second storage engine.
- **Scene state**: state owned by one Scene instance.
- **Process local**: scratch state owned by one Flow/Troop/immediate invocation.
- **Self state**: persistent state owned by one placed Map Event instance, with author-facing **Self Switch** and **Self Variable** vocabulary.
- **Map-owned state** is a valid ownership category, but a generic author-facing Map Variable feature is not justified by the present corpus and remains reserved/deferred.
- Domain facts remain with their domain owners rather than being flattened into generic Variables.

Everything below marks repository fact separately from the design inference it supports.

## 2. Current `v.*` corpus classification

A repository-wide audit of production `v.`/`ctx.v`/`SET_VAR` uses on the baseline found the following semantic families. This is a classification of the current production corpus, not a proposal that every current key should survive unchanged.

### 2.1 Scene-instance state — the dominant production use

**Evidence.** Scene hooks are executed with the current stack entry's `state.v`; each `scene_host.push` creates a fresh `v = {}`. `goto_scene` is pop + push, so that table is replaced with the Scene instance. Examples in authored Scenes include:

- Item Creation (`data/scenes/1.json`): `state`, `crafterIdx`, `cursorIdx`, `cursorSlot`, `i1_item_id`, `i2_item_id`, `confirmOptionIdx`, `poolTargetIdx`, `rouletteStep`, `rouletteDelay`, `yieldScore`, `yieldAnomalyScore`, `isAnomaly`, `poolCurrentIdx`, plus derived display/query values populated by Scene scripts.
- Battle (`data/scenes/battle.json`): `combatState`, `selectedIndex`, `action`, `skillSelect`, `itemSelect`, `targetSelect`, target/inspect cursors and transition/log presentation state. Battle Scene scripts also publish richer transient structures such as `livingMembers`, `eventsQueue`, pending selection records and level-up rows.
- Other authored menu Scenes use the same shape for tabs, cursors, selected member/item indexes, state-machine modes, list counts/rows and derived labels.
- `scene_host` injects `_guard` per hook to prevent same-hook state cascades and uses `_capturingKey`/`rawKey` for the Controls Scene's one-key capture path.

**Design inference.** These values are fundamentally Scene-instance state. They should become explicit **Current Scene State** semantics as #410 migrates ambiguous `v`; renaming all of them to persistent Game Variables would change lifetime and be incorrect.

### 2.2 Derived Scene records/lists — evidence for structured values, not for Scene Actors

**Evidence.** Current Scene state already carries non-scalar derived presentation/query structures. Examples include Battle's `livingMembers`, `eventsQueue` and level-up row records (`engine/progress.lua` publishes `levelUpRows` and related fields), plus Item Creation pool/slot data and analogous authored list-row projections used by menus.

Some current structures contain live runtime references. Battle Scene scripts, for example, retain the current Battle object, battler/actor references and pending target/action objects while the Scene is active.

**Design inference.** Records/lists are useful before any Scene Actor/ECS design exists. A future generic authored value substrate should therefore support deterministic serializable records and dense lists. That does **not** mean current live Scene objects should become serializable state: functions, metatables, cycles, userdata, live engine references and surprising shared aliases remain outside generic authored values.

This finding is evidence for structured values and inspectability, not evidence for Scene Actors/ECS.

### 2.3 Scene guards, input and presentation scratch

**Evidence.** `_guard`, `hookHandled`, input action strings, raw-key capture, timers and roulette counters are deliberately short-lived control state. Merged #399 adds another clear example: formula-driven image picture transforms can read Scene `v`, and the fixture drives authored `ballX`/`ballY`-style Scene coordinates through `SHOW_IMAGE_PICTURE` / `MOVE_IMAGE_PICTURE` formula resolution.

**Design inference.** Formula visibility does not imply persistence. A value can be fully authorable and formula-readable while remaining Scene-local.

### 2.4 Flow/Troop invocation locals

**Evidence.** `engine/flow.lua` documents `v` as `flow-locals`. Current authored commands include:

- `data/flows/battle.json` `flee_attempt`: `roll = random()` exists only to branch the flee attempt.
- `data/troops.json` base `ambush`: `ambush` holds the current trait-derived amount and `hit` gates the first living enemy inside that invocation.
- `data/troops.json` base `strain`: `strainMult` is calculated from the current Battle round and used immediately to price prolonged-combat MP strain.

These values are calculations inside a process. Their meaning is exhausted by the invocation in which they are produced.

**Design inference.** They belong to **Process Locals**, not Game Variables and not persistent Event self state.

### 2.5 Developer progression-shaped scratch

**Evidence.** `data/maps/8.json` still writes `return_count` in Developer Room presets beside real persistent milestone flags. A current repository search finds no consumer of `return_count` outside that writer.

**Design inference.** Do not blindly promote it because the name resembles progression. #410 should remove it if dead or move the intended fact to an explicit persistent/domain owner if a real consumer is established.

### 2.6 Domain mirrors/projections

**Evidence.** Scene `v` frequently holds a projection or UI working copy of a fact whose source of truth lives elsewhere: inventory-derived rows/counts, creature/member information, settings/presentation selections and Battle-derived projections are examples. `engine/progress.lua` is explicit that it publishes a structured report into Scene vars for presentation; it does not make that report the creature's persistent owner.

**Design inference.** A generic Variable system must not become a dumping ground for inventory, quests, gold, creatures, battle truth, settings or other established domains. A Scene projection may be transient even when the fact it describes is persistent.

### 2.7 Campaign-era `v` is no longer current corpus

**Evidence.** Merged PR #395 purged the inert Campaign protocol, including Campaign list/switch command paths and their Scene variable projections. Current `docs/ENGINE-STATE.md` reports Project data root `data` and 91 implemented commands with no Campaign command registry residue.

**Design inference.** #400 should not preserve Campaign-era `v` examples or a Campaign state owner in durable architecture.

## 3. Lifetime and save evidence

### Scene lifetime

`engine/scene_host.lua` is decisive current evidence:

1. a pushed Scene receives a new stack entry with `v = {}`;
2. optional transition vars seed that new table;
3. hooks bind `ctx.v` to that table;
4. popping removes the Scene entry;
5. `goto_scene` performs pop then push.

There is no save serialization of the Scene stack or Scene `v`. `engine/savegame.lua` explicitly treats Battle/dialogue/menu Scenes as mid-transition state that is not safe to resume into; saves are offered from Map/Town and restore a new `GameSession` plus Map data.

**Conclusion:** current Scene `v` is Scene-instance state, not persistent Variables.

### Flow/Troop lifetime

`engine/flow.lua` names `v` as Flow locals, and current Flow/Troop uses are scratch calculations. `SET_VAR` has no independent storage owner; it writes the host-provided table.

**Conclusion:** the command should eventually target explicit owner semantics rather than making `SET_VAR` itself imply a lifetime.

### Persistent playthrough/domain state

`GameSession` and `savegame` currently persist domain-owned state including:

- gold;
- inventory;
- flags and unlocked lore;
- MP/max MP and EXP bank;
- party/reserve/storage, persistent creature instance identity/growth/history and recruit-node state;
- memorial records;
- dungeon floor and current Map reconstruction data;
- `mapStates`, `eventOverrides`, `portalReturn` and `mapPresentationOverrides`;
- the current Map snapshot (grid, visited grid, runtime events/light/generated products, player position/facing).

These are evidence that the project already has durable playthrough state without a generic Game Variable substrate.

**Conclusion:** adding Game Variables should add one authored persistent owner; it should not replace existing semantic owners.

### Specialized Map/Event persistence

`exploration.resolvePage` resolves Map Event pages and then overlays persistent `eventOverrides[mapIndex][eventId]` and temporary Event overrides. The map lifecycle audit also shows `mapStates[mapIndex]` as a specialized dangerous-Map cache. Neither mechanism is a generic author-facing Map Variable or Self Variable store.

**Conclusion:** stable Map + placed Event identity already matters. Persistent Self state should attach to one placed Event instance. Generic Map Variables remain a possible future owner, not a current requirement.

## 4. #398 falsification: St. Maria permission is not Scene `v`

The owner report in #398 suggested that Labyrinth permission might be forgotten after leaving and returning to St. Maria. Current authored truth falsifies the proposed `v` explanation.

Current PR #412 reproduces the real sequence against authored St. Maria/Labyrinth data:

1. the Registrar/authority grants **Crossing Writ**, item `198`;
2. the Labyrinth gate page condition checks `hasItem:198`;
3. ordinary enter/return Map transfer preserves that inventory-owned permission;
4. JSON save/load converts numeric table keys to strings;
5. current `savegame.deserialize` restores `inventory` directly without normalizing numeric keys, so lookup by numeric item id can fail after load.

PR #412 fixes that numeric inventory-key restoration and deliberately leaves `ctx.v` untouched.

**Evidence conclusion:** #398 is not evidence that Scene `v` forgot persistent permission. The semantic fact has playthrough lifetime, but the current domain representation is the persistent Crossing Writ item. Inventory remains the correct owner if possession of the Writ is the authored meaning of permission.

This is also an important ontology guardrail: persistent does not automatically mean Variable.

## 5. External precedent

External systems are precedent for authoring vocabulary and owner distinctions, not mandates for Thestra's implementation.

### RPG Maker Switches, Variables and Self Switches

RPG Maker MZ's official help distinguishes **Control Switches** (ON/OFF), **Control Variables** (stored values) and **Control Self Switch**. Its Map Event page conditions separately expose Switch, Variable and Self Switch conditions. The official beginner documentation describes ordinary Switches as game-wide and Self Switches as local to an individual Map Event.

Sources:

- RPG Maker MZ Help — Game Progression: https://rpgmakerofficial.com/product/MZ_help-en/01_10_02.html
- RPG Maker MZ Help — Map Event Settings: https://rpgmakerofficial.com/product/MZ_help-en/01_09_03.html
- RPG Maker MZ beginner guide — Switches and Self Switches: https://rpgmakerofficial.com/product/mz/guide/event/switch.html
- RPG Maker 2003 official product page (event-system lineage/context): https://www.rpgmakerweb.com/products/rpg-maker-2003

**Precedent:** author-facing Switch and Variable concepts can be global/playthrough state while Self state is tied to a placed event.

### Maniacs Patch / RPG Maker 2003 extension precedent

The Maniacs Patch is an actively maintained extension of the Steam RPG Maker 2003 runtime/editor. Its extended Control Variables/TPC ecosystem is a useful precedent for richer variable addressing and community Self Variable techniques without requiring an object/ECS ontology.

Sources:

- Maniacs Patch project site: https://bingshan1024.github.io/steam2003_maniacs/
- EasyRPG known-patches technical reference: https://wiki.easyrpg.org/development/technical-details/known-patches
- Current RM2k3 Maniacs SelfVar technique reference: https://www.rpg-maker.fr/tutoriels-730-rm2k3-utiliser-les-selfvar-maniacs.html

**Precedent:** richer self-scoped numeric/value state is an established authoring need; the important semantic is owner identity, not a forced Scene Actor abstraction.

### VisuStella MZ Events & Movement Core

VisuStella's Events & Movement Core turns ordinary named Switches/Variables into Self Switches/Self Variables and also offers Map Switch/Map Variable scopes. Its remote Self Variable command requires Map ID + Event ID, and Map state calls require Map ID.

Source:

- Events and Movement Core VisuStella MZ: https://www.yanfly.moe/wiki/Events_and_Movement_Core_VisuStella_MZ

**Precedent:** explicit owner identity is a practical way to permit cross-context access. Its Map Variables also demonstrate that a Map scope is coherent, but precedent alone does not prove Thestra needs to ship that feature now.

## 6. Durable conclusions supported by the audit

1. **Variable means persistent saved game/playthrough authored state.**
2. Current Scene `v` is fundamentally Scene-instance state and must not be renamed wholesale into Variables.
3. Flow/Troop/immediate scratch such as flee `roll`, ambush `hit` and `strainMult` belongs to process/invocation-local state.
4. Persistent Self state belongs to one placed Map Event instance.
5. Preserve author-facing **Self Switch** and **Self Variable** vocabulary.
6. Switch may share a typed value substrate with Variables while retaining dedicated Control Switch, ON/OFF, page-condition and search ergonomics.
7. Generic Map-owned state is architecturally valid, but a production generic **Map Variable** feature is not currently proven necessary; keep it deferred/reserved.
8. Structured values are justified before Scene Actors: deterministic serializable records/lists, deep copy-by-value, no functions/metatables/cycles/userdata/live engine refs/surprising aliasing.
9. Cross-context access may exist only through explicit stable owner identity.
10. #398 is not a Scene-`v` permission-loss bug; current permission is Crossing Writ item 198, and the reproduced defect is save/load numeric inventory-key restoration.
11. Domain truth such as inventory, quests/progression, gold and creatures remains in its existing semantic owner rather than being dumped into Variables.
12. Studio direction is owner-aware: **Game Variables / Current Map State / Selected Event Self State / Current Scene State / Process Locals**, with search, Switch affordances, optional declarations/defaults, runtime-created values and no numeric preallocation requirement.

## 7. Value semantics supported now

The audit supports a conservative generic value boundary for future #407/#409 work:

- scalars: boolean, finite number, string and absence/null semantics as defined by the implementation issue;
- deterministic records with string keys;
- dense ordered lists;
- copy-by-value at state-owner boundaries so one assignment cannot create surprising cross-owner aliases;
- deterministic serialization/round-trip behavior.

Reject from the generic authored substrate:

- functions/closures;
- metatables;
- cycles;
- userdata;
- NaN/infinities or other non-deterministic/non-portable numeric values;
- live Battle/Battler/Scene/renderer/loader references;
- implicit shared mutable table aliases.

Current Scene state may still hold live runtime objects internally. The rule above is for the **generic authored persistent value substrate**, not a retroactive ban on host-local implementation state.

## 8. Studio/inspection direction

The state inspector/search direction should expose ownership and lifetime instead of one undifferentiated variable list:

- **Game Variables** — persistent authored playthrough state, including Switch affordances;
- **Current Map State** — specialized Map-owned runtime/persistent state, while generic Map Variables remain clearly deferred;
- **Selected Event Self State** — persistent Self Switch/Self Variable values for one stable placed Event identity;
- **Current Scene State** — the active Scene instance's author-visible state;
- **Process Locals** — live locals for the currently executing authored process when such a process exists.

Search should be able to locate definitions and references by owner/path/name/type. Optional declarations/defaults should improve authoring and validation, but runtime-created values remain visible and valid; no RPG-Maker-style numeric preallocation is required by this architecture.

Implementation belongs to #411, not this report.

## 9. Unresolved questions

These remain implementation/design details for the bounded follow-ups rather than reasons to reopen #400's owner model:

- Exact syntax/commands for selecting Game Variable vs Scene state vs Process Local targets.
- Stable identity encoding for placed Events, including copied/templates/spawned Event cases and migration if authored event IDs change.
- Exact default/absence semantics and whether declarations can constrain type after first assignment.
- Save-version migration strategy for #407/#409.
- Exact cross-context read/write syntax and permission/validation rules.
- Whether any future production use actually justifies generic Map Variables; no current `v` corpus finding does.
- How much host-local Scene state should be author-visible when it contains live opaque objects that cannot be represented as generic values.
- Whether `return_count` is deleted as dead developer scratch or replaced with a domain/persistent fact after a real consumer is identified.

## 10. Bounded follow-ups already opened

Do not duplicate these issues:

- #407 — persistent Game Variable / Switch substrate and deterministic value semantics.
- #409 — persistent Map Event Self state / Self Switch / Self Variable.
- #410 — migrate ambiguous current `v` into Scene state vs process locals.
- #411 — owner-aware authored-state inspector/search.

#400 remains the architecture parent and should stay open while these semantics are being published/implemented unless repository policy later changes.

## 11. Current-main refresh notes

- **#395 Campaign purge:** removes Campaign protocol/state vocabulary from the current runtime. No Campaign owner is retained here.
- **#399 picture formulas:** image transform fields now resolve through the existing formula context, including Scene `v`; this reinforces rather than weakens the Scene-instance classification.
- **#412 / #398:** current draft evidence continues to isolate the St. Maria permission defect to numeric inventory keys after JSON save/load; it does not introduce a `v`-based permission owner.
- No subsequent current-main evidence material to this audit falsified the completed #400 conclusions.

## 12. Repository sources inspected

Primary current-tree evidence includes:

- `AGENTS.md`
- `tools/delegate/README.md`
- `tools/delegate/AGENT-PROVENANCE.md`
- `docs/SPEC.md`
- `docs/ENGINE-STATE.md`
- `engine/scene_host.lua`
- `engine/interpreter.lua`
- `engine/interpreter_core.lua`
- `engine/formula.lua`
- `engine/flow.lua`
- `engine/troop.lua`
- `engine/session.lua`
- `engine/savegame.lua`
- `engine/exploration.lua`
- `engine/progress.lua`
- `data/flows/battle.json`
- `data/troops.json`
- current authored Scene `v` corpus under `data/scenes/**`
- Developer Room `data/maps/8.json`
- #325 and relevant owner comments
- #398 and current PR #412
- #400 and all comments
- #407, #409, #410 and #411
- merged PR #395 and merged PR #399

Agent-Signature:
  platform: ChatGPT
  model: GPT-5.6 Sol
  role: documentation
  task: "#400 authored state scopes publication + verification"
  base: 63010d0e3864a17c0a41d5d6c6ca674ad8d0f735
