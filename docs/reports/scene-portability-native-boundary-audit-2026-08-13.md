# Authored Scene portability, native-boundary, and backend-neutrality audit

**Date:** 2026-08-13  
**Issue:** #414  
**Audited main:** `63010d0e3864a17c0a41d5d6c6ca674ad8d0f735`  
**Scope:** evidence/architecture only; no runtime migration, no Battle edits, no formula parser, no RTP moves.

## 1. Executive result

The current Scene architecture is substantially more portable than GitHub language statistics make it look, but portability is uneven at exactly the boundaries #414 asked to test.

The durable center is already recognizable:

- Scene lifecycle hooks and logical input are authored data;
- ordinary menu/controller state is overwhelmingly Scene-instance `v` state;
- Event Programs and Flows express branching, queries, state mutation, domain commands, and Scene transitions without presentation dependencies;
- windows and pictures are authored presentation requests;
- #399 moved image-picture formula evaluation to the engine side, so presentation receives resolved transforms rather than defining gameplay expressions;
- the Battle domain kernel is meaningfully distinct from authored Battle lifecycle policy and presentation choreography.

The main portability gaps are narrower than “too much Lua”:

1. **Formula semantics are authored contract but only implicitly specified through Lua today.** Current content relies on Lua-like truthiness, value-returning `and/or`, `~=`, `%`, `#`, 1-based indexing, nil/absence behavior, helper functions, and current precedence. Another backend could reproduce these semantics without Lua, but only after Thestra owns the meaning explicitly. Follow-up: #416.
2. **A few authored Scenes hide their controller behind SCRIPT/native code.** Recruitment is the clearest case: all eight hooks trampoline into `engine/recruitment.lua`, which combines a legitimate transaction kernel with one particular Scene controller. Follow-up: #417.
3. **Dialogue is authored-looking presentation around host-owned orchestration.** `main.lua` owns the GraphWalker/input progression and mirrors current dialogue data into Scene `v` every frame. Follow-up: #418.
4. **Battle has legitimate native domain code plus historical one-off native Scene composition.** `engine/battle.lua` is primarily the authoritative resolver/kernel. `engine/scenes/battle.lua` additionally owns controller and presentation/revelation choreography that is not inherently part of the resolver. This audit does not edit or mass-lower Battle.
5. **Scene `v` is not a persistent Variable store.** The #400 lifetime conclusions hold across this corpus. Most `v` is cursor/mode/derived presentation state. The main portability hazards are live object references in Battle and `reserve.v.popupMemberRef`, plus interpreter/controller scratch such as `_guard`, Battle `action`, and `hookHandled`. #410 already owns the migration/classification follow-up; no duplicate issue was opened.
6. **Time remains under-specified independently of authorability.** Four authored Scenes use `on_frame`; `items` subtracts `0.016`, Item Creation advances a fixed roulette step per frame, and `reserve` uses a frame hook only to reset `_guard`. #386 already owns the timing contract.
7. **RTP ownership and portability are related but not identical.** A Project-owned Scene can still be backend-neutral; a default candidate can still be backend-bound today. The ownership classifications below coordinate with #390 and make no file moves.

The RPG Maker thought experiment is therefore useful when stated narrowly: a competent event author can understand most current Scenes as **state + conditions + Event commands + presentation + explicit semantic primitives**. The failures are specific places where the authored file stops describing what actually happens.

## 2. Evidence basis and method

### Repository truth read

- `AGENTS.md` and delegation/provenance rules;
- #325 owner architecture comments;
- #385, merged #393, merged #397;
- #386, #387, #388 and owner corrections;
- #394 and merged #399;
- #400 completed architecture comment and existing follow-ups #407/#409/#410/#411;
- #390;
- `docs/SPEC.md`;
- generated `docs/ENGINE-STATE.md`;
- all 21 current `data/scenes/*.json` resources;
- all four current Flow files;
- `data/commonEvents.json` at Scene-orchestration crossings;
- `engine/scene_host.lua`, `engine/interpreter.lua`, `engine/interpreter_core.lua`, `engine/formula.lua`;
- `data/engine.json` command/formula/script registries;
- `presentation/scene_compositor.lua`, `presentation/window_renderer.lua`, image/string picture renderers;
- Scene validation in `engine/validator_core.lua` / `engine/validator_rules.lua` and editor-facing command-context evidence;
- `engine/battle.lua` and `engine/scenes/battle.lua` read-only plus authored Battle Scene/Flow.

### Tests used as thought experiments

For each Scene:

1. **Authorability/RPG Maker lowering:** can the behavior be read as state + conditions + event commands + presentation + explicit semantic primitives, without requiring that RPG Maker literally implement Thestra primitives?
2. **Backend replacement:** could the authored resource keep the same semantic meaning if Lua/LÖVE were replaced by a backend implementing the same Thestra contracts?
3. **Ownership:** is the current resource a baseline/default candidate, optional template, Second Gate Project composition, mixed composition/policy, or tooling surface?

These tests do not recommend an exporter, a second backend, or a mass rewrite.

## 3. Semantic metrics

Generated truth reports **21 authored Scenes** and **one native Scene module**, `engine/scenes/battle.lua`.

### 3.1 Scene ownership classification

| Ownership class | Count | Scenes |
|---|---:|---|
| strong RTP default candidate | 7 | `controls`, `dialogue`, `items`, `quest_log`, `save_menu`, `shop`, `status` |
| optional RTP Scene Template candidate | 1 | `cinematic` |
| Second Gate Project-owned Scene | 2 | `recruit`, `ritual` |
| mixed reusable structure + Second Gate policy/content | 8 | `1`, `battle`, `datalog`, `game_over`, `map`, `options`, `reserve`, `title` |
| tooling/developer surface | 3 | `developer_3d`, `developer_geometry_export`, `developer_menu` |
| unresolved | 0 | — |

This is a **classification for #390 coordination**, not a move plan. In particular, “strong RTP default candidate” means the semantic role belongs in a baseline; it does not claim the current file can be copied wholesale without separating Project art/text/policy.

### 3.2 SCRIPT and native composition

- 11 / 21 Scene resources contain **zero** `SCRIPT` commands.
- 10 / 21 contain live Scene `SCRIPT`.
- The corpus contains **72 Scene SCRIPT command sites** referencing or embedding **42 Lua bodies**.
- Dominant reason by SCRIPT command site:
  - 51 sites: Scene/domain/controller composition in `1`, `battle`, `recruit`, `reserve`, `ritual`;
  - 15 sites: developer/tooling operations in the three developer Scenes;
  - 3 sites: small Map query/navigation ergonomics;
  - 3 sites: Options host/settings operations.
- One native Scene module exists: Battle.
- Dialogue has zero authored SCRIPT but still has Scene-specific native orchestration in `main.lua`; SCRIPT count alone therefore understates backend binding.

The 72-site count is not a quality score. Eight recruit sites are one-line delegates while one Item Creation body is large; native volume is less important than responsibility.

### 3.3 `on_frame`

Exactly four current authored Scenes define `on_frame`:

| Scene | Current use | Portability/timing finding |
|---|---|---|
| `1` Item Creation | calls `calcYield`; while roulette state is active the script increments `v.rouletteStep` once per frame | behavior is frame-count-dependent; `timing.steps` is a frame count despite other delay-like config values |
| `game_over` | staged authored presentation sequence using Event commands / waits | authored orchestration is legible, but final timing semantics should inherit #386 rather than implicit host cadence |
| `items` | decrements `v.popupTimer` by hard-coded `0.016` | explicit 60-Hz assumption; demonstrated #386 evidence |
| `reserve` | sets `_guard` back to zero | host already resets `_guard` per hook; this is interpreter/controller plumbing, not gameplay time |

No conclusion about #387 follows from this. #388's owner correction stands: raw variable-machine authorability and deterministic time quality are different questions.

### 3.4 State metric methodology

There is no declaration table for Scene variables: values are runtime-created by Event commands, scripts, native hooks, and Scene seeds. A raw “number of `v.*` tokens” would count aliases/reads and miss script-assigned values, so it would be less semantic than the requested audit.

Instead, §5 enumerates **every meaningful state cluster per Scene** and classifies its lifetime. Cross-corpus hazards are small and concrete:

- `_guard`: interpreter/cascade plumbing appearing as authored state in many Event-style controllers;
- Battle `action` and `hookHandled`: per-hook controller scratch;
- Battle `v.battle`: live native Battle object;
- Battle `livingMembers`, target selections, collected actions, and resolved-event queues: structures containing live Battler/target/event references;
- Reserve `popupMemberRef`: live battler/domain reference in Scene `v`;
- Dialogue GraphWalker/controller: native state lives outside `v` and is mirrored into it rather than represented by a clean Scene/query contract.

Those findings reinforce #400/#410; they do not create a second state ontology issue.

## 4. Scene-by-Scene matrix

Legend for authorability:

- **Event** — obvious authored Event-style orchestration;
- **Event + primitive** — authored orchestration over explicit semantic commands/queries;
- **SCRIPT gap** — important behavior is hidden behind SCRIPT;
- **native composition** — authored resource omits behavior implemented for that Scene in native code.

Portability answers whether the **authored resource as written** could keep its semantics, not whether the whole current executable could run unchanged.

| Scene | Ownership | Authorability | Backend portability as authored | State summary | SCRIPT / native boundary |
|---|---|---|---|---|---|
| `1` Item Creation | mixed | SCRIPT gap | partial | Scene mode/cursors/ingredient ids; derived crafter/item/pool/result rows; roulette presentation/process counters | 11 calls to one large `calcYield` Lua body. It queries party/inventory/databases, sorts/builds rows, evaluates crafting formulas, owns roulette selection, and commits item removal/grant. Missing seams are query/projection + domain operation + authoring ergonomics, not one monolithic native “craft scene” primitive. |
| `battle` | mixed | SCRIPT gap + native composition | low as written; lifecycle/Flow portions portable | UI modes/cursors plus live Battle/Battler/target/event references and presentation queues | 18 SCRIPT sites, five bodies, plus the only native Scene module. Resolver kernel is legitimate native; controller/revelation choreography is not automatically kernel responsibility. |
| `cinematic` | optional template | Event/skeleton | high | no meaningful production state | Empty/generic hook shell. Portability is high because behavior is minimal; template usefulness is an ownership question. |
| `controls` | strong default | Event + primitive | high | cursor/capture mode; raw key handoff; derived binding rows/count | No SCRIPT. Backend must provide logical input plus explicit raw-binding capture contract. |
| `datalog` | mixed | Event + query | high | cursor plus derived lore rows/count | No SCRIPT. Generic log browser structure; Second Gate owns lore records/policy. |
| `developer_3d` | tooling | SCRIPT gap acceptable for tooling | backend-specific tooling | cursor plus queried quality/density | Four inline SCRIPT sites call geometry/developer host API. Legitimate developer surface; not evidence for gameplay primitives. |
| `developer_geometry_export` | tooling | Event + tooling primitive, one SCRIPT ergonomic patch | backend-specific tooling | export status text | `EXPORT_MAP_GEOMETRY` is explicit; one inline script rewrites result text with `string.gsub`. This is mainly tooling/string ergonomics. |
| `developer_menu` | tooling | SCRIPT-heavy tooling | backend-specific tooling | cursor and ephemeral dev toggle snapshots | Ten inline SCRIPT sites for wireframe/FPS/perf/server/phase and cheats. Tooling may intentionally expose backend/developer capabilities. |
| `dialogue` | strong default | native composition despite zero SCRIPT | low as written | presentation mirror (`dialogueText`, speaker/portrait/choice/reveal/wait state); controller/GraphWalker remains host-owned | `main.lua` drives walker/input and mirrors values into Scene `v` every frame. Follow-up #418. |
| `game_over` | mixed | Event | high subject to #386 time contract | local stage/presentation state | No SCRIPT. Reusable lifecycle shape mixed with Second Gate copy/art/policy. |
| `items` | strong default | Event + primitive | high except timing detail | tab/cursor/mode and transient popup presentation; inventory remains domain-owned | No SCRIPT. `USE_ITEM` is an explicit semantic primitive. `popupTimer -= 0.016` is backend-cadence leakage owned by #386. |
| `map` | mixed | Event with three small SCRIPT gaps | high after query ergonomics seam | menu mode/cursors/member indices/confirmation plus `_guard` | `snapPartyIdx`, `selectPartyMember`, `pushStatus` use party occupancy queries and emit window/Scene events already semantically available elsewhere. These are small authoring/query gaps, not a native Map Scene controller. |
| `options` | mixed | Event + three host SCRIPT gaps | partial | cursor; local copy of auto-redirect setting; render-surface id | three inline scripts get/cycle render surface and set autoRedirect. Render surface is a presentation-host setting; autoRedirect is session/project policy. A portable default needs explicit settings/query commands rather than Lua calls. |
| `quest_log` | strong default | Event + query | high | cursor plus derived active-quest rows/count | No SCRIPT. Domain quest truth stays in quest owner. |
| `recruit` | Project | native composition hidden behind SCRIPT | low as written | stable source key; modes/slot; serializable selection plan; candidate/profile snapshots; error/outcome state | All eight hooks are one-line delegates to `engine/recruitment.lua`. Domain transaction kernel is legitimate native; Scene controller is one-off composition. Follow-up #417. |
| `reserve` | mixed | Event + SCRIPT gaps | partial | pane/cursor/mode/swap state; derived popup rows; one live `popupMemberRef` | Three named scripts build popup options, perform swap/dismiss operations, and push ritual. `popupMemberRef` violates the value-only portability direction from #400; #410 owns migration. |
| `ritual` | Project | SCRIPT gap | low as written | mode/pool/evolution/level cursors; extensive derived actor/cost/preview rows; transaction selection state | 11 SCRIPT calls to four large bodies (`setupRitual`, `refreshRitual`, `stepLevel`, `confirmRitual`). Mostly Second Gate summon/promotion/sacrifice policy plus queries/domain operations. |
| `save_menu` | strong default | Event + primitive | high | mode/cursor/confirmation plus derived save rows/count | No SCRIPT. Save machinery is native backend service behind explicit list/save/load commands. |
| `shop` | strong default | Event + primitive | high | buy/sell mode, cursor/count/quantity/confirmation and transient pricing | No SCRIPT. Inventory/gold truth stays domain-owned; Scene orchestrates transactions. |
| `status` | strong default | Event + primitive/query | high | member/tab/submode/cursors; derived equipment/skill/passive presentation | No SCRIPT. Equipment transaction is semantic command; presentation queries remain renderer/engine views. |
| `title` | mixed | Event + primitive | high | menu/save picker/option cursor state | No SCRIPT. Reusable title/start/continue/options shape is mixed with Second Rite branding, Common Event 42, Project map/dev destinations and policy. Coordinate extraction with #390. |

### Ownership note

`dialogue` being a strong RTP candidate does **not** mean its current implementation is portable. Conversely, `ritual` being Project-owned does **not** justify embedding Lua; Project content can and should use backend-neutral semantic contracts where useful. Ownership and native-boundary classification are orthogonal.

## 5. Scene state audit

This section uses #400 vocabulary: Scene-instance state is not persistent Variable state. Domain truth such as inventory, quests, rosters, gold, recruitment nodes, and saved settings remains with its semantic owner.

### `1` Item Creation

- **genuine Scene-instance / mode:** `state`, selected crafter index, ingredient slot ids, confirmation/pool/roulette mode;
- **cursor/selection:** inventory cursor, confirm index, pool indices;
- **derived rows/query data:** crafter label/stats, inventory count/highlight id, slot rows/names, score/tier/anomaly/result fields, `pool` rows;
- **process/presentation scratch:** `rouletteStep`, `rouletteDelay`; currently cadence-dependent;
- **persistent/domain mirrors:** none authoritative; item removal/grant occurs through domain API at completion;
- **native handles:** none intentionally stored; the script temporarily reads live item/crafter objects.

### `battle`

- **genuine Scene/controller:** `combatState`, confirm phase, submenu/inspect/target-selection modes, selected indices, reward/level-up presentation stages;
- **cursor/selection:** `selectedIndex`, active member index, target index, inspect-state index;
- **derived rows:** `commandRows`, help text and reward/level-up presentation strings;
- **process scratch:** `action` is a one-hook input token; `hookHandled` is cascade/fallback signaling; pending log/reward flags and event queue indices are controller/revelation state;
- **native/domain handles:** `v.battle` is a live `Battle` object; `livingMembers[*].actor` are live Battlers; pending/collected actions carry target objects; resolved event queues carry actor/target/item/domain references;
- **persistent/domain mirror:** Battle/session graphs remain authoritative; Scene queues are presentation/control projections, not saved Variable truth.

The live-handle problem is portability-specific: the current Lua process can safely point into its object graph, but a backend-neutral authored value cannot mean “this Lua object identity.” Stable battler/instance identity or native context handles would be needed if/when #410 migrates these boundaries.

### `cinematic`

No meaningful current state beyond the generic Scene instance.

### `controls`

- **Scene/cursor:** binding row index, capture mode, selected button/action;
- **derived query:** binding rows/count;
- **host handoff:** raw key value while rebinding. This is a bounded input-host payload, not persistent state.

### `datalog`

Cursor is Scene-local. Lore row list/count are derived query data. Lore unlock truth remains domain/session-owned.

### developer Scenes

All developer toggle/cursor/status values are transient tooling state. Geometry/runtime objects are not serialized as authored state. Backend coupling is acceptable as tooling policy where deliberate.

### `dialogue`

The Scene receives mirrored presentation values such as current text/speaker/portrait/choice/reveal/wait state. The authoritative walker and selection state live outside Scene `v` in `main.lua`. This is an ownership/seam problem, not evidence that dialogue state should become persistent Variables. #418 should expose stable dialogue query/continuation state rather than duplicating the walker.

### `game_over`

Stage/presentation values are genuine Scene lifetime state. Session reset/start behavior is invoked semantically; it is not mirrored into `v` as persistent truth.

### `items`

Tabs, cursor/mode and popup timer/text are Scene/presentation state. Inventory/item quantities remain domain-owned. The popup timer is semantically local but its decrement currently assumes 60 Hz.

### `map`

`mode`, command/popup/member/party/confirm indices are ordinary Scene UI state. `_guard` is interpreter/cascade plumbing. Member selection is represented by party index rather than a stored Battler handle, which is the portable shape.

### `options`

Cursor/aspect profile id are Scene/UI values. `autoRedirect` is a local UI copy of a session/project setting; the setting remains domain-owned. This is a normal edit buffer as long as commit/query semantics are explicit.

### `quest_log`

Cursor is Scene-local; quest rows/count are derived. Quest status truth remains in the quest owner.

### `recruit`

`sourceKey` is a stable owner identity, which #400 permits for cross-context access. Candidate identity/stats/skills/passives/equipment are copied into serializable presentation rows. `mode`, `slotIdx`, `selectedChoice`, errors and outcome are Scene/controller state. Persistent recruit-node truth lives in `session.recruitNodes`; the native controller currently mutates requirement satisfaction there.

### `reserve`

Pane/focus/cursors/popup/swap state is Scene-local. Popup labels/options are derived rows. `popupTargetIndex`/reserve flag are stable value references. **`popupMemberRef` is a live Battler reference stored in `v` and is the clearest non-Battle value-boundary leak.** Existing #410 is the correct migration parent.

### `ritual`

Mode, selected pool/evolution/level indices and confirm state are Scene/controller state. Actor/cost/evolution/preview lists are derived query data. Domain transactions (summon/promote/sacrifice and MP/EXP-bank changes) should remain semantic owner operations. The large SCRIPT bodies currently mix query/projection and transaction invocation.

### `save_menu`

Mode/cursor/confirm are Scene state; save rows/count are derived query results. Save data is not copied into `v` as persistent authored Variables.

### `shop`

Mode/cursor/quantity/confirmation values are Scene transaction UI state. Shop item lists/prices are invocation/query data. Gold/inventory truth remains session-owned.

### `status`

Member index, tab/submode, equipment/skill/passive cursors are Scene-local. Equipment/skills/passives are queried projections; actual Battler/equipment truth remains domain-owned.

### `title`

Menu/save-picker/options cursor state is Scene-local. Save rows are derived. New-game/session/save truth remains outside Scene `v`.

### `_guard`

`scene_host.runHook` resets `state.v._guard = 0` before each hook. Authored hooks then repeatedly test/set `_guard` to stop later branches in the same hook after one branch fires. That makes `_guard` an interpreter/cascade implementation device, not a game-state concept. It should not be promoted into persistent Variables or treated as meaningful Scene domain state. Its eventual removal/internalization belongs with #410 rather than a new issue.

## 6. SCRIPT audit

`SCRIPT` is not categorically wrong. It is explicitly a backend escape hatch. The audit asks whether the **reason** for each current use is stable.

| Scene | SCRIPT sites | Lua bodies | What the SCRIPT actually does | Why current Event Programs cannot fully express it | Dominant missing thing / judgment |
|---|---:|---:|---|---|---|
| `1` | 11 | 1 | query/sort inventory and discipline data, build derived rows, evaluate craft formulas, choose roulette pool/result, advance roulette, remove ingredients/grant output | no compact database query/projection/sort/list-building vocabulary; craft transaction and roulette are not decomposed into semantic commands | query + Scene projection + native domain op; backend-bound Project composition today |
| `battle` | 18 | 5 | route input modes/targeting/submenus, build command rows/help, drain log events, stage reward/level-up transitions | current commands lack reusable Battle-controller queries/commit/revelation seams; some work is presentation-specific | mixed controller/query/presentation + native domain calls; highest owner-supervised concern |
| `developer_3d` | 4 | 4 | read/cycle geometry quality and density | developer setting/query commands absent | legitimate tooling/backend escape hatch |
| `developer_geometry_export` | 1 | 1 | rewrite export status string | string replacement ergonomics absent | authoring ergonomics only; tooling |
| `developer_menu` | 10 | 10 | read/set dev overlays/server/phase and invoke cheats | intentionally developer-only APIs are not general commands | legitimate tooling/backend escape hatch |
| `map` | 3 | 3 | snap cursor to occupied party slot, open member popup if occupied, push Status with member index | party occupancy/first-member query awkward; script emits events equivalent to existing commands | query + ergonomics; small and highly lowerable |
| `options` | 3 | 3 | read/cycle render surface; set autoRedirect | no authored setting/query command for these properties | presentation-host setting + domain setting; reusable default should not require Lua |
| `recruit` | 8 | 8 | delegate each hook to `api.recruitment.on*RecruitScene(ctx)` | the entire controller exists only in native recruitment module | one-off native Scene composition; #417 |
| `reserve` | 3 | 3 | derive popup policy/options, perform swap/dismiss, push ritual | roster queries/transactions and dynamic row construction not fully commandized | native domain operations + query/projection; contains live handle leak |
| `ritual` | 11 | 4 | initialize/refresh summon/promotion/sacrifice projections, step levels/evolutions, commit transactions | extensive Second Gate queries, projection construction and ritual domain operations absent | Project domain operation + query/projection; backend-bound today |

### SCRIPT sandbox boundary

`interpreter_core` deliberately sandboxes SCRIPT: normal scripts do not receive `love`, `io`, `os`, `require`, or raw session/loader access while `scripting.allowRawAccess` is false. The API facade therefore already reduces accidental backend coupling.

But authored SCRIPT is still **Lua source** and still relies on Lua tables, `pairs`/`ipairs`, table mutation, reference identity, `#`, standard-library behavior, and Lua control syntax. A Rust/Python backend preserving the same semantic command contracts could keep zero-SCRIPT Scenes unchanged; it could not execute these Scene resources unchanged without either embedding Lua or replacing the SCRIPT portions.

That is acceptable for a deliberate escape hatch. It is architecturally expensive when a reusable/default Scene requires the escape hatch for its normal controller.

## 7. Formula-language portability

### 7.1 What exists today

`engine/formula.lua` constructs a restricted environment and evaluates `return <expr>` through Lua `load`. Authored consumers receive only number/string/boolean results; errors are reported and the core evaluator currently returns a fallback value plus error information. Context views expose battlers, party/enemy aggregates, session, combat, battle, `v`, ingredients and helper functions. Some views use Lua metatables internally for lazy trait/base lookup.

`data/engine.json` documents helpers and views, and the window renderer adds row-scoped/window-scoped expression context such as selected-row access.

### 7.2 Syntax/semantics actually consumed by current authored content

The current corpus demonstrably uses:

- integer and decimal numeric literals;
- strings and booleans;
- `+`, `-`, `*`, `/`, `%`, unary minus;
- `<`, `<=`, `>`, `>=`, `==`, `~=`;
- `and`, `or`, `not`;
- **value-returning `and/or` idioms**, not merely boolean logic, for fallbacks/ternary-like selection;
- parentheses and current Lua precedence;
- dotted record access, including nested metadata/trait views;
- bracket indexing with dynamic expressions such as per-party-slot count arrays;
- **1-based array indexing**;
- **`#` list length** (for example ritual evolution lists);
- absence/nil checks and `or` fallbacks;
- helper calls including `random`, `floor`, `ceil`, `round`, `abs`, `min`, `max`, `clamp`, and presentation formatting/window helpers where supplied;
- `random()` as a float form and `random(m,n)` as bounded integer form;
- row-local fields shadowing broader Scene formula context in window/list evaluation.

No production evidence from this audit requires formulas to support arbitrary statements, function definitions, userdata, engine objects, cycles, or general table mutation. Large record/list construction currently occurs in SCRIPT or native query code, not formula return values.

### 7.3 Semantics another backend must not guess

A backend-neutral implementation needs a Thestra-owned answer for:

1. **numbers:** numeric type/range, division/modulo, rounding and coercion policy;
2. **strings/booleans:** comparison and conversion rules;
3. **truthiness:** current Lua behavior makes only false/absence falsey; zero and empty strings are truthy;
4. **`and` / `or`:** current content depends on operands being returned, not boolean coercion;
5. **precedence:** current authored meaning inherits Lua precedence today;
6. **equality:** current `==`/`~=` do not perform string/number coercion;
7. **records/indexing:** missing field behavior, invalid indexing, dynamic bracket lookup;
8. **arrays:** 1-based indices, contiguous length semantics for `#`, out-of-range behavior;
9. **absence/nil:** equality, boolean fallback, interpolation, arithmetic and nested access behavior;
10. **helpers:** exact argument/return/error behavior and which contexts provide extra pure helpers;
11. **random:** range semantics and the deterministic promise under seeded validation. Equal ranges are not enough if cross-backend golden traces ever require an identical random stream; that would require a specified PRNG contract;
12. **errors:** parse, missing-field, type, arithmetic/index and helper failures; whether a given command fails, falls back, or surfaces an authoring error;
13. **records/tables:** which values may be read as records/lists without making Lua table identity part of the authored language.

The conclusion is **not** “Thestra formulas should mean Lua forever.” It is “today's authored subset has observable semantics that must be named before a different implementation can claim compatibility.” #416 owns that bounded specification/conformance work.

## 8. Flows and Common Events

Current generated truth lists four Flow resources: `_test`, `battle`, `exploration`, `quest`.

- `_test` is validator pressure material. Its SCRIPT cases prove the sandbox, including the expected failure of `os.time()` while raw access is disabled. It is not production Scene policy.
- `battle` is a strong example of the intended split: reusable lifecycle phase names (`battle_start`, `round_start`, `after_action`, `round_end`, outcome phases) carry authored Event commands, while many actual rules inside the current file are Second Gate policy (barriers, Strain-adjacent state cleanup, reserve/reap/history, flee economics). The Flow is semantically portable even when the native Battle kernel is reimplemented.
- `exploration` uses ordinary Event commands for Second Gate traversal economics/history. The phase concept can be reused; the MPD/history policy is Project-owned.
- `quest` is close to baseline semantic composition: completion takes requirements and grants rewards through explicit commands.

`data/commonEvents.json` likewise demonstrates that orchestration can cross into Scenes through semantic commands rather than native controllers: common events use `BATTLE`, `RECRUIT`, `LOAD_MAP`, quest commands and ordinary dialogue/choice Event Programs. The title Scene starts authored Common Event 42 rather than embedding its full opening progression in native source.

The durable boundary is therefore not “Scenes own everything.” Scene UI, Event Programs, Common Events and Flows are separate authored composition layers that call the same semantic command substrate.

## 9. Battle decomposition (read-only)

Battle must not be summarized as “Lua vs JSON.” Its current responsibilities are already heterogeneous.

### 9.1 Legitimate native deterministic Battle domain/kernel

`engine/battle.lua` owns behavior that matches #325's protected Battle semantics:

- authoritative Battle instance and participant set;
- action validity/forced-action enforcement and command eligibility inputs;
- target resolution through the shared targeting authority;
- action queue construction and deterministic priority/speed/order rules;
- AI choice where the engine must produce an enemy action;
- authoritative effect/resource/state/death transitions;
- resolved event facts/provenance;
- outcome evaluation and encounter-local bookkeeping.

Those are reimplemented native primitives in a different backend, not authored Scene scripts merely because they are gameplay-visible.

### 9.2 Authored Battle lifecycle/Flow

`data/flows/battle.json` owns phase policy around battle start, round start/end, troop events, barriers, state/timer ticks, victory/escape rewards/history/reaping and encounter checks. The **phase contract** is reusable; many **rules in the current phase bodies** are Second Gate Project policy.

### 9.3 Scene-local controller/UI state

`data/scenes/battle.json` owns input/log/victory/level-up modes, command/submenu/target/inspect cursors and window visibility. That is conceptually authored Scene responsibility.

However, current controller state is entangled with live native handles (`v.battle`, battlers, targets, event objects) and SCRIPT bodies. A backend-neutral Scene value boundary would use stable identity/value projections while native context owns engine objects.

### 9.4 Embedded Battle Scene SCRIPT

Five named bodies perform:

- `handleInput`: command/submenu/target/inspect controller and action commit routing;
- `refreshConsole`: command/item/skill query projection and contextual help rows;
- `handleLogInput`: reveal/animation/event-queue advancement;
- `handleTransition`: reward/log/victory transition staging;
- `announceLevelUp`: inserts level-up narration into the presentation event queue.

These are not all the same kind of missing seam. `handleInput` mixes ordinary authored UI state with legitimate native target/commit queries. `refreshConsole` is primarily query/projection. Log/reward functions are presentation/revelation choreography over already-resolved facts.

### 9.5 Native Battle Scene module

`engine/scenes/battle.lua` additionally owns:

- construction/initialization of a native Battle object;
- living-member projection;
- submission/undo/target helper operations exposed to Scene SCRIPT;
- draining resolved events;
- battle-log strings;
- animation scheduling/callbacks;
- damage/heal/state/death popups;
- BattleView delayed revelation;
- reward/level-up/victory presentation stages;
- transition callbacks to the invoking Event Program.

The first set includes reusable semantic seams around the domain kernel. The middle is presentation choreography and should remain backend/presentation work even if its current module lives under `engine/scenes`. The last is lifecycle/continuation plumbing.

The architectural concern is **one-off composition**, not the existence of native Battle primitives. The module directly imports renderer/battle-view/animation presentation modules and exists only for Battle. That makes it the highest-concentration historical boundary, but it is owner-supervised and this PR changes none of it.

### 9.6 Reusable RTP Battle composition candidate

A future baseline Battle composition can reasonably include:

- Battle Scene lifecycle and standard logical-input modes;
- command/skill/item/target selection presentation;
- resolved-event log/revelation choreography;
- generic victory/defeat transition hooks;
- authored Battle lifecycle phase scaffolding.

It should **not** bake Second Gate-specific reserve-wave/permadeath/reap/Strain/reward policy into the reusable baseline merely because those rules currently run during Battle. #390 owns physical/default-layer extraction.

## 10. Presentation and backend boundaries

The presentation side is mostly already in the right conceptual layer.

- `scene_compositor` selects world/windows/backdrop composition and calls presentation modules; its LÖVE dependencies are below the authored Scene contract.
- `window_renderer` resolves declarative window/list/text/cursor/filter/priority data. It uses formula contexts and builds projections from domain data. A new backend would reimplement the renderer/query projection while preserving authored window semantics.
- image/string picture renderers own motion interpolation, text wrapping/reveal and draw ordering. LÖVE calls here are expected backend implementation.
- #399 is important: numeric image-picture transform formulas are evaluated through the engine/interpreter before presentation. Presentation receives numbers, so authored formula meaning is not accidentally defined by `tonumber` in the renderer.

There are still native references inside presentation projections (`battlerRef` in window rows for flash/render identity), but those are renderer-internal row enrichments, not authored serialized Scene state. The boundary becomes a problem only when such identities are stored in author-facing `v` or SCRIPT-visible values as if they were portable data.

## 11. Scene host, interpreter, validator, and editor support

### Scene host

`scene_host` already supplies a backend-reimplementable contract:

- stack/push/pop/goto lifecycle;
- fresh Scene `v` per instance;
- named logical input hooks;
- window/presentation events;
- Event hook interpretation;
- suspension for waits;
- native Scene kind registration as an optional capability.

Implementation details such as dynamic Lua `require("engine.scenes." .. kind)` are backend-specific below that contract.

`_guard` is the notable leak: the host knows about and resets a variable that authored resources also manipulate. This is interpreter plumbing masquerading as Scene state.

### Interpreter

The interpreter is already the strongest portability seam. Commands name semantic operations; presentation is injected; Flows/Common Events/Scenes use one command language. A different backend is expected to reimplement command handlers while preserving command/resource semantics.

Raw SCRIPT is explicitly outside that guarantee unless the backend chooses to embed the same Lua escape hatch.

### Validator

Current Scene validation is substantial and useful:

- validates draw modes/backdrops/formulas/windows/hooks;
- infers variables assigned by Event commands and named scripts to seed formula mock contexts;
- syntax-checks named Scene scripts using Lua `load`;
- validates SCRIPT refs;
- validates registered command contexts that also drive editor authorability.

The validator therefore documents an important fact: SCRIPT's authored syntax is consciously Lua today. Formula validation, in contrast, should eventually validate a Thestra-owned formula contract even if Lua remains its implementation; #416 provides that future conformance boundary.

### Editor

`data/engine.json` registers command contexts and `validator_rules` explicitly notes that the editor builds command pickers from those contexts. This supports the architecture desired by #325: explicit semantic commands are authorable vocabulary, while SCRIPT is an escape hatch. A missing semantic command is therefore not just a runtime concern; it directly affects whether a behavior can be constructed in Studio without code.

## 12. What changes require native source today?

### Usually authored-resource-only

- menu ordering, branching and cursor behavior in zero-SCRIPT menus;
- quest/exploration/battle Flow policy that is already commands;
- title/game-over/shop/status/save/item window composition;
- picture placement/transform formulas after #399;
- most window content/formulas/resource references;
- Common Event dialogue/choices/quest/map-transfer orchestration.

### Require or strongly invite native source today

- adding/changing the Battle resolver/kernel or targeting semantics;
- recruitment Scene lifecycle/controller behavior because it lives in `engine/recruitment.lua`;
- dialogue GraphWalker/Scene synchronization because it lives in `main.lua`;
- Battle input/log/revelation choreography spanning `data/scenes/battle.json` SCRIPT and `engine/scenes/battle.lua`;
- large Item Creation/Ritual/Reserve projection/transaction behavior embedded in Lua scripts;
- Options render-surface host behavior;
- developer/tooling host toggles;
- any new formula construct whose meaning is not accepted by the current Lua evaluator/context.

This list is a better portability metric than Lua LOC: it says which gameplay/presentation decisions cross the authored/native boundary.

## 13. Evidence vs design conclusions

### Direct evidence

- 21 authored Scenes and one native Scene module exist at the audited head.
- 10 Scenes contain SCRIPT; 11 do not.
- 72 Scene SCRIPT command sites reference/embed 42 Lua bodies.
- four Scenes use `on_frame`.
- `items` authors `0.016` as its timer decrement.
- Item Creation advances roulette by one step per frame.
- `scene_host` resets `_guard` every hook.
- Battle stores a native Battle object and structures containing Battler/target references in `v`.
- Reserve stores `popupMemberRef` as a live member reference.
- recruitment's eight authored hooks delegate to native recruitment Scene-controller functions.
- dialogue production state/input is controlled in `main.lua` and mirrored into Scene `v`.
- formulas are evaluated with Lua `load` and current content relies on Lua-observable expression semantics.
- #399 moved picture transform formula evaluation to engine/interpreter semantics before presentation.

### Design conclusions strongly justified by the corpus

- authored Scene semantics are backend-neutral **only to the extent they are stated in Thestra contracts**, not merely because they are JSON;
- native semantic primitives are compatible with authored portability; bespoke one-Scene controllers are the higher concern;
- Scene state exposed as authored values should be deterministic serializable values/stable identities, not native object references;
- formulas are an authored Thestra language whose implementation may be Lua today but whose semantics must be specified independently;
- presentation requests should stay authored/backend-neutral while renderer/LÖVE implementation remains replaceable;
- SCRIPT remains legitimate as an explicit backend escape hatch, but reusable/default composition should not require large SCRIPT merely for normal lifecycle/controller behavior when a reusable semantic seam is demonstrated;
- RTP ownership must be decided by reusable semantic role, not by JSON/Lua file extension.

These are the only conclusions promoted into the short design note accompanying this report.

## 14. Existing issues that already own findings

No duplicates were opened for:

- **#386** — deterministic authored Scene timing / `on_frame` contract;
- **#387** — possible Scene Actor ergonomics; not treated as an expressive prerequisite after #388 owner correction;
- **#390** — RTP/Project/Package/Studio ownership decomposition and physical extraction;
- **#400 / #407** — persistent Game Variable/Switch substrate;
- **#409** — persistent Map Event Self state;
- **#410** — migrate ambiguous current `v`, including interpreter scratch/process-local/native-handle separation;
- **#411** — owner-aware state inspector/search.

## 15. New bounded follow-ups

Duplicate searches found no existing issue for these demonstrated seams:

- **#416 — Specify the backend-neutral Thestra formula contract.** Documentation/conformance scope; no parser/backend implementation required.
- **#417 — Lower Recruit Scene lifecycle onto authored orchestration and recruitment primitives.** Preserve the native atomic recruitment kernel; expose the minimum reusable query/transaction seam instead of eight native Scene-hook delegates.
- **#418 — Expose Dialogue Scene lifecycle through a reusable authored seam.** Preserve one GraphWalker/Event substrate; remove the one-off host Scene mirror/controller dependency.

No Battle follow-up was opened from this audit because the boundary is owner-supervised and a broad “decompose Battle” ticket would be less bounded than the evidence warrants without owner-selected responsibility scope.

## 16. Unresolved questions

1. **Battle native-context representation:** when #410 reaches Battle, should authored Battle controller state carry stable battler instance ids, opaque non-serializable native context handles kept outside `v`, or query tokens? The audit proves live Lua object identity is not portable; it does not choose the replacement.
2. **Formula PRNG contract:** does backend-neutral semantics require identical random streams across implementations, or only deterministic streams per backend under a seed plus documented range behavior? Golden compatibility may eventually force the stronger answer.
3. **Window query ownership:** some current list sources construct rich domain projections inside `window_renderer`. They are backend-reimplementable, but a future non-visual consumer may justify moving pure query projection below presentation. Current evidence does not require that migration now.
4. **Item Creation/Ritual command seams:** both are Project-heavy. The audit demonstrates backend binding, but it does not yet prove which projection operations deserve generic registry commands versus remaining Project/package SCRIPT.
5. **Battle revelation API:** resolved-fact presentation is correctly downstream of authoritative resolution, but current callback/animation choreography is strongly Lua/presentation-module-shaped. A later owner-supervised task should choose the smallest presentation contract before moving code.
6. **Cinematic:** current behavior is too skeletal to prove whether it should become a shipped optional RTP template or remain an internal sample. #390 can resolve ownership when a concrete template contract exists.

## 17. Non-conclusions / guardrails preserved

This audit does **not** conclude or implement any of the following:

- mass Scene rewrite;
- “Battle should be JSON”;
- “all SCRIPT is bad”;
- generic Map Variables;
- Scene Actors/ECS;
- RPG Maker exporter;
- Rust/Python backend;
- formula parser replacement;
- save-schema changes;
- state inspector implementation;
- Battle owner-supervised edits;
- G5/G6 recapture.

The strongest result is narrower: **authored portability already has a coherent semantic core; the remaining architecture work is to name formula semantics and replace a few one-off controller/handle leaks with explicit stable seams.**
