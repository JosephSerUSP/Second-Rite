# Map and Area Event Program host audit

**Date:** 2026-08-12
**Scope:** Map and future Area lifecycle behavior in the live Second Rite engine
**Status:** Docs-only architecture investigation; no schema or implementation decision
**Baseline:** `main` at `4bf1198d` (2026-08-12)
**Related work:** issues #308 and #325; reports delivered by #327 and #330; current map/generation audit in #338

## 1. Executive summary

### Verdict

**Inference / recommendation:** Maps and future Areas can cleanly own scoped authored behavior, but only as explicit Event Program hosts for a small set of semantic lifecycle phenomena. They should not acquire Event Pages, a universal callback bus, `UPDATE`, `EVERY_FRAME`, or a second script language.

The minimum useful model is:

```text
Map Instance host
    on_instance_created   (once, when a runtime instance is first resolved)
    on_activate           (when that instance becomes the active playable world)
    on_deactivate         (when it stops being the active world)
    on_player_step        (after a successful player movement commit)

Area host, if Area is ratified as an authored scope
    on_enter              (membership changes: outside -> inside)
    on_exit               (membership changes: inside -> outside)
    on_player_step        (optional, only if Area-local step policy is proven)
    on_instance_created   (only for a generated/instantiated Area that has its own lifecycle)
```

These are working semantic names, not a schema proposal. The final vocabulary must be derived from fixtures and the owner decisions listed below.

The important separation is:

```text
Map Instance lifecycle     authoritative playable-world lifecycle
Map Scene lifecycle        input, windows, scene stack, and presentation composition
Event Page                 current incarnation of one Map Event entity
Flow                       named system/domain lifecycle program
Common Event               reusable procedure invoked by a caller
Area                       future identity-bearing semantic scope inside a Map
Zone                       current spatial predicate/tag mechanism
```

The current `map` Scene cannot be the sole authority for Map lifecycle. A Map Scene is popped when dialogue or battle replaces it, even though the current Map Instance remains the world being returned to. Conversely, `exploration.loadMap` can activate a different Map Instance while the current Scene is dialogue or cinematic. Treating these as the same `on_enter`/`on_exit` would create duplicate or misleading behavior.

### Recommended first-class host surface

**Proposal:** add one Map Instance host with four initial semantic signals, and defer Area hooks until Area has stable identity and membership semantics. If Area is adopted, start with only `on_enter` and `on_exit`; add Area `on_player_step` only after a real fixture demonstrates that Map-level step plus a predicate is insufficient.

The hooks should:

- run through the existing Event Program interpreter;
- receive a typed, narrow context;
- mutate only through registered domain commands and capabilities;
- be serialized as part of the owning Map Instance when they change instance-local state;
- use deterministic host/source ordering;
- permit interaction waits only when the active host can suspend and resume safely;
- fail loudly when their owner disappears or their context is stale.

The hooks should not:

- replay a Map load, transfer, movement, or Area membership transition;
- directly mutate authoritative spatial state from the Scene or presentation layer;
- become a universal event bus;
- make Flow the parent dispatcher for all Map and Area behavior;
- execute once per render frame as gameplay authority.

### Bloat conclusion

**Inference:** Map and Area hooks provide useful authoring vocabulary when they describe transitions authors already reason about: instance creation, activation, deactivation, successful player step, Area entry, and Area exit. They become architectural bloat when every structural object receives a generic script slot for arbitrary updates. The host model earns its place only where a lifecycle source is real, typed, deterministic, and independently useful across multiple authored cases.

## 2. Evidence labels and scope

This report labels statements as follows:

- **Repository fact:** directly observed in current `main` code/data or in the referenced repository reports.
- **Owner direction:** constraint supplied by the owner in the investigation request, not a claim about current implementation.
- **Inference:** conclusion drawn from the facts and owner direction.
- **Proposal:** a candidate contract for review; it is not implemented or ratified.
- **Unresolved:** a decision the report intentionally does not freeze.

`docs/ENGINE-STATE.md` remains the status authority. The reports from #327 and #330 are architecture evidence and contracts, not substitutes for live code. The open #338 PR is used as the current map/generation/Studio audit context; its report is not treated as proof that Area or Location exists in `main`.

Non-goals of this report:

- no Map lifecycle fields;
- no Area resource or schema;
- no Event Page changes;
- no Flow rename or migration;
- no Studio implementation;
- no generic hooks or every-frame callbacks;
- no content migration.

## 3. Current exploration lifecycle trace

### 3.1 Authored Map and runtime Map Instance

**Repository fact:** Map data is loaded from `data/maps/*.json` by the shared loader. Current Maps contain fixed layout or generation inputs, events, encounter/recruit pools, zones, presentation data, and other policy fields. The current repository has no persisted Location hierarchy, Area registry, or Map parent relation in `main`.

**Repository fact:** `engine.exploration.loadMap(session, mapIdx, opts)` is the central Map activation path (`engine/exploration.lua:916-1095`). It:

1. resolves the authored Map record and fails if the ID is unknown;
2. detects a safe-to-dangerous expedition transition and runs `exploration.expedition_start` once for the new expedition;
3. caches the previously active dangerous Map Instance;
4. sets the active Map index and structure token;
5. copies authored Map data into the current runtime Map data;
6. restores a cached generated instance or generates a new one;
7. resolves fixed layout, procedural structure, events, generated features, generated zones, and lights;
8. restores or creates fog-of-war and map position;
9. publishes the session-owned `currentMapData`, `mapGrid`, player position, and runtime collections.

The runtime products are Map Instance state, not new authored Map definitions:

```text
Map definition
    -> fixed or procedural resolver
    -> mapGrid
    -> runtime events and mutations
    -> generated features, zones, and lights
    -> baked runtime lighting
    -> saved/cached Map Instance
```

**Inference:** `loadMap` is the strongest current lifecycle authority for Map Instance creation and activation. A future Map host should subscribe at this semantic seam instead of observing a renderer or guessing from the current Scene.

### 3.2 Current map movement and step processing

**Repository fact:** `engine.exploration` owns passability and commits player coordinates. `tryMove` changes `session.playerX` and `session.playerY` only on a successful step (`engine/exploration.lua:1129-1169`). The public movement functions are thin directional wrappers.

**Repository fact:** `main.lua` owns input policy and presentation transition timers. After a successful movement, it runs `flow.run("exploration.step", ...)`, then checks Map Events at the new cell, then performs a dangerous-map encounter check if no step Event opened (`main.lua:1623-1769`).

The current semantic order is:

```text
input accepted
    -> exploration.move* commits player cell
    -> exploration.step Flow
    -> step/touch Event at new cell
    -> encounter check if no step Event handled
```

**Inference:** a future Map `on_player_step` signal belongs after the movement commit and before or within an explicitly chosen ordering relative to the existing `exploration.step` Flow and Map Event trigger. It must not be fired from keypress receipt, render update, camera movement, or an unsuccessful bump.

### 3.3 Map Events, Pages, and Common Events

**Repository fact:** `exploration.resolvePage` resolves the last matching Event Page over an Event's base fields, then applies persistent and temporary overrides (`engine/exploration.lua:12-71`). Current Pages contain conditions and may override commands, triggers, presentation, and other Event incarnation fields. The current data uses `interact`, `bump`, `step`, and `touch` triggers.

**Repository fact:** `main.lua` finds Map Events by cell, resolves their current Page, and invokes either inline commands or a Common Event referenced by `scriptId` (`main.lua:1454-1504`). The command list is compiled by the shared interpreter. The resulting GraphWalker remains associated with the originating Event while the dialogue/interaction Scene is shown (`main.lua:1397-1451`).

**Inference:** Event Pages are the right host for the current gameplay incarnation of one Event entity. They are not the right abstraction for Map or Area because Map/Area behavior is scoped lifecycle policy, not a competing entity incarnation with sprite, trigger, movement, and priority.

### 3.4 Existing Flow system

**Repository fact:** `engine.flow` maps a dotted phase to a command list in `data/flows/<host>.json` and executes it synchronously with the shared interpreter (`engine/flow.lua:1-60`). Required phases fail loudly when absent. Current exploration examples include `exploration.step`, `exploration.expedition_start`, and `battle.encounter_check`.

**Repository fact:** the current `exploration.step` Flow owns traversal MP cost, movement-based healing, and trait-state synchronization. `exploration.expedition_start` records creature history at the safe-to-dangerous boundary.

**Inference:** existing Flow is already a named system lifecycle host. A Map host must not duplicate Flow semantics merely to make Map-local authoring convenient. The long-term choice is either to let a Map host participate as a separate scoped host, or to add an explicit Map-scoped provider to a named lifecycle signal. It must not create a second hidden dispatch path for the same transition.

### 3.5 Scene lifecycle

**Repository fact:** `engine.scene_host` owns the Scene stack, Scene-local `v`, window state, input hook dispatch, Scene transitions, and `on_enter`/`on_exit`/`on_frame` hooks (`engine/scene_host.lua:6-21,145-232,237-371`). Scene hooks run through immediate Event Programs. `on_frame` is called from `scene_host.update(dt, ctx)` once per simulation update, not from `love.draw`.

**Repository fact:** the `map` Scene has an `on_enter` setup hook for menu/window state (`data/scenes/map.json`). The Scene is also displaced by dialogue, battle, shops, and other Scenes through `goto_scene`, which performs pop then push (`engine/scene_host.lua:294-307`). Map Scene `on_exit` therefore describes Scene-stack displacement, not necessarily leaving the active Map Instance.

**Important pressure case:** a Map Event starts dialogue or battle. `scene_host.goto_scene("dialogue"/"battle")` pops the Map Scene, but `session.currentMapData` remains the current Map and the player returns to that same world. A Map Instance `on_deactivate` fired for every such Scene pop would incorrectly treat a modal or battle detour as leaving the Map.

**Inference:** Scene hooks remain appropriate for Scene-local UI/input state. Map lifecycle hooks must use a separate Map Instance host or an explicitly defined overlay policy.

## 4. Current Event / Page / Flow / Scene host boundaries

| Host | Current scope | Current authority | Wait behavior | Correct use for Map/Area question |
|---|---|---|---|---|
| Map Event Page | One spatial Event's active incarnation | Page resolution and Event interaction/movement fields | Interactive Event Program may wait | Keep for entity behavior; do not copy to Map/Area |
| Common Event | Named reusable procedure | Caller invokes its command list | Interactive caller can wait; immediate mode rejects interactive commands | Reuse from Map/Area hooks when a procedure is genuinely shared |
| Flow | Named domain/system phase | Host calls `flow.run(phase, ctx)` at a semantic point | Current immediate phases do not suspend | Keep for system-wide/domain lifecycle; do not make it a universal dispatcher |
| Scene hook | One Scene instance | Scene stack and Scene host | `WAIT` sets Scene wait timer; `on_frame` is update-clock work | Keep for UI/input and Scene composition |
| Action Sequence | One action execution | Battle/action capability and sequence context | Current immediate `WAIT` paces presentation; it does not suspend semantic execution | Not a Map/Area host |
| Troop Event | One encounter/troop | Battle phase invites troop-local programs | Battle contract controls admissible waits | Not a Map/Area host |
| Proposed Map Instance host | One active or resident Map runtime instance | Exploration/Map Instance lifecycle source | Only declared interaction waits | Candidate for scoped Map behavior |
| Proposed Area host | One identity-bearing Area scope inside a Map Instance | Area membership/instance source | Only declared interaction waits | Candidate, pending Area semantics |

**Repository fact:** the same Event Program substrate is already used for map/common/scene/battle-phase/action contexts. `data/engine.json` declares command contexts, and the editor/validator use that registry rather than hand-written command lists.

**Inference:** a Map/Area host is a natural extension of the existing host contract if it supplies a new semantic context. It is not a reason to create Event Pages for structural scopes or to create a second interpreter.

## 5. Map lifecycle phenomena

The owner request explicitly asks not to collapse every phenomenon into `onEnter`/`onExit`. The following table separates the observed transitions.

| Phenomenon | Current authoritative source | What happens now | Candidate host/context | Recommendation |
|---|---|---|---|---|
| First creation of a fixed Map runtime state | `exploration.loadMap` | Fixed grid, events, injected fixtures/lights, and initial position are resolved | Map Instance creation context with `created=true`, `map`, `instance`, seed if applicable | Distinguish from activation; first-class `on_instance_created` is justified only if one-time setup is needed |
| First generation of a dangerous Map | `exploration.loadMap` -> `generateDungeon` | No cached `mapStates[mapIdx]` causes generation, generated events/zones/features/lights, and runtime lighting | Map Instance creation context with generation result/provenance | Strong candidate; generated creation is a real semantic event |
| Enter/activate an existing Map Instance | `exploration.loadMap` | Cached state is restored or a fixed Map is resolved; player position is chosen by arrival mode | Map activation context with previous Map, arrival mode, instance identity, and restored/created flags | Strong candidate; do not infer from Scene `on_enter` |
| Leave/deactivate a Map Instance for a transfer | `exploration.loadMap` before switching `currentMapIndex` | Current dangerous instance is cached; current Map is replaced | Map deactivation context with destination, transfer kind, departure cell, and instance identity | Strong candidate; exact timing must be before authoritative replacement and once per real Map switch |
| Transfer between Maps | `LOAD_MAP` command -> `exploration.loadMap`; Event Program may continue in dialogue/cinematic | Map load occurs synchronously; Scene may return to Map after Event Program ends | Transfer context or paired deactivate/activate facts | Treat as a compound domain transition, not as a new generic callback |
| Return to cached generated Map | `exploration.loadMap` finds `mapStates[mapIdx]` | Grid, events, generated collections, player position, and lighting are restored | Activation context with `restored=true`, `created=false` | Same `on_activate`; expose `resumed/restored` rather than inventing `on_return` unless fixtures require it |
| Save while standing on a Map | `savegame.serialize` | Current Map snapshot and Map Instance state are serialized; only Map/town are resumable Scenes | Save context; no Map entry/exit transition | Do not fire Map enter/exit. Save/load is persistence, not travel |
| Load while standing on a Map | `savegame.deserialize`/`quickLoad`/`LOAD_GAME` | New GameSession and Map snapshot are rebuilt; Scene stack is reinitialized | Load/restore context, distinct from normal activation | Unresolved whether a loaded instance should receive `on_activate`; recommendation is an explicit `activationReason="load"`, not a hidden replay of creation |
| Player movement/step | `exploration.tryMove` then `main.lua` | Coordinates commit; exploration.step Flow, step Event, encounter check run | Player-step context with before/after cells and committed result | Strong candidate; only successful committed steps |
| Player bump/blocked movement | `exploration.tryMove` returns false; main sets bump timers | Presentation nudge/cooldown; no movement commit | No Map gameplay hook by default | Do not add `on_bump` until a real authoring requirement exists; current wall Event interaction is separate |
| Event movement | No current autonomous Event movement lifecycle in live exploration path | Map Events are spatial records; current movement behavior is not a separate host contract | Future Event/entity host | Not evidence for Map/Area hooks |
| Enter/leave authored zone | `fixture_predicates` reads zone tags for placement predicates | Zones classify cells; no membership transition is published | Future membership source | Do not promote current Zone to Area or add hooks yet |
| Enter/leave future Area | Not implemented | No Area identity, membership resolver, or overlap order exists | Area membership context | Candidate only after Area semantics are ratified |
| Battle start while on a Map | `engine.scenes.battle.triggerBattle` runs `battle.battle_start`, then replaces Scene | Map Instance remains current while Battle Scene is active | Battle lifecycle context, not Map leave | Do not treat as Map deactivation; a Map may observe only through an explicit battle-domain fact if needed |
| Battle end returning to a Map | Battle outcome Flow/Scene transition calls `goto_scene("map")` | Battle Scene leaves; same Map Instance is still current | Battle end and Map Scene activation are distinct | Do not fire Map `on_activate` unless the contract explicitly includes Scene/world reactivation; prefer a distinct `on_resume_from_battle` only if proven necessary |
| Expedition reset | `exploration.loadMap` safe -> dangerous transition clears `mapStates` and structure tokens, then runs `exploration.expedition_start` | Cached dangerous Maps are discarded before new generation | Expedition domain context | Keep as Flow/domain lifecycle; not a Map `on_instance_created` substitute |
| Map mutation | `MUTATE_TILE`/`exploration.mutateTile` increments structure revision; prepared renderable cache observes it | Authoritative grid changes and presentation cache invalidates | Map mutation context | Domain capability owns mutation; a later `on_mutated` reaction is optional and must not repair/replay it |
| Scene activation/deactivation | `scene_host.push/pop/goto_scene` | Scene hooks and transitions run; current Map may remain resident | Scene context | Keep separate from Map Instance lifecycle |

### 5.1 First creation versus activation

**Inference:** authors need both concepts for the pressure cases:

- “Seed this generated Map instance once” belongs to `on_instance_created`.
- “Show a one-time arrival sequence” may belong to `on_activate` with a persisted instance/player-arrival policy, or to the transfer Event Program if it is transfer-specific.
- “Resume local state when returning to a cached floor” belongs to `on_activate` with `restored=true`, not a new Page type.

The engine must publish a resolved instance identity and creation/restoration fact so an authored Program cannot guess whether it is first creation by inspecting a table or flag.

### 5.2 Map activation versus Map Scene entry

**Inference:** `Map` as a playable world and `map` as a Scene are currently coupled in naming but not in lifecycle. A future implementation should make the distinction visible in the contract:

```text
Map Instance active
    may have Map Scene as the visible interaction surface
    may be obscured by dialogue, battle, shop, or another modal/context

Map Scene active
    owns input/window state and presentation composition
    does not prove that a new Map Instance was entered
```

## 6. Area lifecycle pressure cases

### 6.1 Owner direction

**Owner direction:** Location is a real non-playable semantic hierarchy node, with recursively cascading policy and descendant override/interruption. A Map is one continuous playable spatial world/instance lifecycle. A named district does not automatically become another Map. Area semantics are not finalized, and a future Area may be a powerful semantic scope with policy, generation, population, and lifecycle Programs. One Map may contain fixed structure plus several independently generated spatial Areas/scopes.

**Repository fact:** current `map.zones` and `generatedZones` are predicate/tag mechanisms. `engine.fixture_predicates` builds a cell index from authored and generated tags for feature placement and distance/adjacency predicates. No current code gives a Zone stable semantic lifecycle identity, nested membership, or enter/exit events.

### 6.2 Area pressure matrix

| Pressure case | Area capability it actually requires | Current evidence | Decision pressure |
|---|---|---|---|
| Market enter starts crowd ambience/local policy | Stable Area identity, membership transition, scoped state, possibly presentation policy | Map-level ambient/world effects exist; no Area membership | Supports Area `on_enter` if Area is identity-bearing |
| Market exit clears temporary local state | Area-local state and exactly-once exit transition | No Area state today; Map Instance state is saved/cached | Supports `on_exit`, with persistence rules |
| Cathedral enter runs an authored sequence | Entry transition plus interaction wait and reentrancy | Map Event/Common Event already handles sequences | Supports Area host only if entry is not better represented by a Map Event |
| Procedural dungeon Area generates independently | Area creation identity, seed/policy, generated result, provenance | One Map-wide generator currently exists; #338 records multiple scopes as owner direction | Strongly requires a distinction between Area creation and Area entry |
| Area-local encounter/population policy | Scope-aware domain capability and typed population context | Map encounter tables and `battle.encounter_check` are Map/domain-level | May belong to Area policy consumed by encounter capability, not arbitrary Area scripts |
| Same cell belongs to two semantic scopes | Multiple membership records and deterministic ordering | No overlap contract | Unresolved; do not implement from intuition |
| Nested Areas | Parent/child identity and inherited policy precedence | Location inheritance direction is owner-ratified; Area nesting is not | Unresolved; do not borrow Location hierarchy automatically |
| Direct movement between two Areas | Ordered exit/enter transition set | No membership resolver | Requires explicit ordering before hooks are safe |
| Returning to cached generated Area | Resident Area instance identity and restored state | Map cache restores generated collections; Area cache does not exist | Supports `created` versus `activate` distinction |

### 6.3 Stable identity

**Inference:** a powerful Area scope cannot be identified only by its current cells. It needs a stable authored or generated instance identity so that:

- local state can persist with the Map Instance;
- generated Areas can be restored rather than recreated;
- enter/exit reentrancy can refer to one scope;
- diagnostics can identify the host;
- Studio can show authored policy versus inherited Location policy;
- overlapping Areas can be ordered without relying on JSON hash order.

For generated Areas, the identity should be derived from the owning Map Instance, Area definition/scope identity, and deterministic generation lineage/seed. This is a proposal, not a schema decision.

### 6.4 Overlap and nesting

**Unresolved:** the repository does not currently require a final overlap or nesting model. The pressure cases do require the eventual contract to answer:

- whether a cell may belong to multiple Areas;
- whether Area containment is a tree, DAG, or flat set;
- whether membership is player-only or applies to arbitrary entities;
- whether nested Area entry fires parent then child, child then parent, or a declared order;
- whether moving between overlapping Areas emits exit/enter for every changed membership or only for a selected active Area;
- how inherited Location policy composes with Area-local behavior.

**Recommendation:** do not settle this by treating `map.zones` as Areas. First build a small membership fixture with one player, two overlapping scopes, and one nested scope. Require the fixture to produce a deterministic transition trace before choosing schema vocabulary.

### 6.5 Generated and authored Areas

**Inference:** if Areas become semantic hosts, generated and authored Areas should share the same lifecycle contract after resolution. The difference should be in the creation context and provenance, not in a second hook system:

```text
authored Area definition        -> resolved Area instance
generated Area policy + seed    -> resolved Area instance
                                  |
                                  +--> same membership and lifecycle host
```

An Area Program may inspect `origin.kind = authored|generated`, policy provenance, and instance identity, but it should not need separate `on_generated_enter` and `on_authored_enter` hooks.

### 6.6 Player entry versus arbitrary entity entry

**Proposal:** first Area hooks should be player-scoped. “Entity enters Area” is a different phenomenon requiring entity movement authority, collision/occupancy semantics, and event ordering for autonomous entities. The current engine does not supply that contract. Do not promise arbitrary entity entry just because Area is a spatial concept.

## 7. Render frame versus semantic clocks

### 7.1 Clocks that exist now

| Clock | Current owner | What it is suitable for |
|---|---|---|
| Render frame | LÖVE `love.draw` and presentation renderers | Drawing, interpolation, camera-following effects, visual animation |
| Simulation update/tick | `love.update(dt)`, Scene host, battle update, presentation update | Timer progression, Scene wait timers, animation systems, bounded scheduler work |
| Player step | Exploration movement commit followed by `main.lua` step pipeline | Traversal cost, step traits, step Events, encounter checks |
| Turn/action | Battle action and round authority | Action sequences, effect commits, battle phases |
| Periodic timer | Existing timers such as transitions, bump cooldown, skill timers | Named timer/scheduler capabilities when domain-owned |
| State-change reaction | Event/trait/effect systems and scene state | Reaction to a resolved fact or a declared state change |

### 7.2 The “every frame” pressure test

**Repository fact:** `love.update(dt)` advances presentation and Scene update paths. `scene_host.update` invokes Scene `on_frame` on the update clock, while `love.draw` renders. The current map world also updates ambient effect handles from the viewport renderer. `prepared_map_cache` explicitly suspends effects for non-active cached Maps so off-map effects do not continue updating.

**Repository fact:** Scene `on_frame` is already a data hook, but it is a Scene-local update-clock hook. It is not proof that Map or Area gameplay should run every render frame.

**Inference:** “every frame” conflates at least three different requests:

1. a visual effect should be updated/rendered every frame;
2. a simulation timer should advance while a scope is active;
3. a gameplay rule should react continuously while a condition holds.

They need different vocabulary:

```text
presentation animation       -> presentation clock
active timer                  -> named simulation timer/scheduler
while-active policy           -> explicit activation + timer/condition capability
state transition              -> resolved domain fact/reaction
player crossing a boundary   -> membership transition
```

**Strong guardrail:** Map/Area Programs must never be invoked because `love.draw` ran. A renderer frame can be repeated, skipped, or paced independently of gameplay authority. If an author truly needs a presentation-frame effect, it belongs to the presentation system or a declared presentation capability, not a gameplay lifecycle host.

### 7.3 “While active” without `UPDATE`

**Proposal:** express “while active” as an explicit activation-owned timer or scheduler registration, not as a generic Map/Area callback. The host may start or stop a named timer on `on_activate`/`on_deactivate`; timer ticks are delivered by a domain scheduler with a typed context and deterministic cadence. A future timer capability must define save/load, cancellation, and reentrancy before it becomes author-facing.

This keeps the semantic surface small and makes the clock visible to Studio authors:

```text
On Activate -> START_TIMER("market_crowd", period=...)
On Deactivate -> CANCEL_TIMER("market_crowd")
Timer tick -> named Event Program / capability
```

That is a proposal for a future reusable capability, not a request to add timer fields now.

## 8. Map Event Program host proposal

### 8.1 Candidate host contract

**Proposal:** a Map Instance host owns lifecycle programs attached to the resolved Map Instance, with authored definitions supplied by the Map and inherited Location policy later. The host is not an Event Page and not a second Map Scene.

Candidate initial slots:

| Slot | Semantic meaning | Minimum context | Wait? |
|---|---|---|---|
| `on_instance_created` | The Map Instance was resolved for the first time in its current lineage | `session`, `loader`, `map`, `mapInstance`, `creation.kind`, `seed`, `generationResult`, `lineage` | Only if creation occurs under an interaction-capable caller; default immediate |
| `on_activate` | An existing or newly created Map Instance became the active playable world | `session`, `loader`, `map`, `mapInstance`, `fromMap`, `arrival`, `restored`, `activationReason`, `player` | Yes only through a declared transition/interaction owner |
| `on_deactivate` | The active Map Instance is about to be replaced by another active Map Instance | `mapInstance`, `toMap`, `transfer`, `departure`, `reason`, `lineage` | No half-commit; a declared pre-transfer interaction may wait before replacement |
| `on_player_step` | A player movement commit completed | `map`, `mapInstance`, `player`, `fromCell`, `toCell`, `direction`, `safe`, `stepIndex`, `lineage` | Prefer immediate; interaction waits need explicit movement suspension |

`on_activate` must expose whether it is a first creation, cached return, save/load restore, battle return, or ordinary transfer. If those reasons need materially different behavior, use explicit typed reason data or a separate domain signal; do not make authors infer it from flags.

### 8.2 Pressure-case classification

| Desired behavior | Best first owner | Reason |
|---|---|---|
| One-time arrival sequence | Transfer Event Program or Map `on_activate` with explicit persistent policy | Transfer-specific narration belongs to the transfer caller; Map-wide arrival policy belongs to Map activation |
| Update Map-local state on entering | Map `on_activate` | State is scoped to the Map Instance and must survive cache/save rules |
| Logic immediately before leaving | Map `on_deactivate` | The Map Instance is still authoritative before replacement; caller supplies destination/reason |
| React to a player step | Map `on_player_step` or existing `exploration.step` Flow | Use Map host for Map-local policy; keep system-wide traversal policy in Flow |
| React to first generated instance creation | Map `on_instance_created` | Creation is distinct from entry and can carry generation provenance |
| Resume behavior when returning to cached generated Map | Map `on_activate` with `restored=true` | Same host, explicit restoration reason; no duplicate creation event |
| React to battle start while standing on Map | Battle lifecycle or explicit Map observation capability | Map is not deactivated; do not smuggle Battle into Map context |
| React after battle returns | Battle end plus Map Scene transition, or explicit activation reason if needed | Same Map Instance may remain active; avoid false re-entry |

### 8.3 What Map hooks may mutate

**Proposal:** Map hooks may:

- mutate Map Instance-local variables through a declared namespace;
- call registered commands that mutate session flags, inventory, party, or other domain-owned state when the command context permits it;
- request Map-owned capabilities such as presentation policy, spawn/population policy, or a transfer, subject to the capability's authority;
- launch a Common Event as a nested procedure when the host contract declares the call admissible;
- emit text or interaction requests through the shared interaction protocol.

They may not:

- write `session.currentMapIndex`, `mapGrid`, generated collections, or player coordinates directly;
- mutate a pending domain transition owned by another capability;
- ask presentation to commit gameplay state;
- re-run `loadMap` to “repair” a missing instance;
- assume a Map remains active after yielding without a host-owned continuation token.

### 8.4 Map hook alternatives considered

1. **Use Map Scene `on_enter`/`on_exit`.** Rejected as the sole model. It confuses Scene replacement with Map Instance replacement and fires on dialogue/battle detours.
2. **Put all Map behavior in Flow.** Rejected as the parent dispatcher. It hides Map-local ownership, makes scope precedence unclear, and turns Flow into the universal bus #330 explicitly warns against.
3. **Attach behavior to a Map Event Page at the spawn cell.** Rejected. It invents a sentinel entity, fails for generated instances without that Event, and couples Map lifecycle to spatial presentation.
4. **Add generic `ON_ANYTHING`/`UPDATE` hooks.** Rejected by the bloat and clock tests.
5. **Use Common Events only.** Retain Common Events as procedures invoked by a host, but do not make the caller reconstruct lifecycle identity or ordering.

## 9. Area Event Program host proposal

### 9.1 Preconditions

**Proposal:** do not add Area hooks until the following are true in a reviewed design:

- Area has stable identity within a Map and resolved Area Instance identity for generated scopes;
- current membership can be computed from authoritative spatial state;
- membership transitions are emitted once, not inferred by each host;
- overlap/nesting ordering is deterministic;
- Area-local state persistence is defined;
- authored and generated Areas resolve through one contract;
- the Studio can distinguish inherited Location policy from Area-local behavior.

These are not demands for a complete Area implementation now. They are the minimum semantic prerequisites for avoiding a misleading hook surface.

### 9.2 Candidate initial Area slots

**Proposal:** after the preconditions, the smallest Area surface is:

| Slot | Meaning | Context | Mutation boundary |
|---|---|---|---|
| `on_enter` | Player membership changed from outside to inside | `map`, `mapInstance`, `area`, `areaInstance`, `fromCell`, `toCell`, `membershipBefore/After`, `origin`, `lineage` | Area-local state and registered domain capabilities |
| `on_exit` | Player membership changed from inside to outside | Same, with `toArea`/destination membership as needed | Area-local state and registered domain capabilities |

An optional `on_player_step` is not part of the initial surface. A Map `on_player_step` plus an Area membership transition should cover the common cases. If an Area needs a repeated step policy, that is evidence for a named Area-scoped timer or a specific step participant, not automatic permission to run every Area Program on every step.

`on_instance_created` belongs only if an Area is itself generated/resolved as a separately persisted instance. If “Area” is only a static membership grouping, creation is a Map Instance concern and should not be duplicated.

### 9.3 Deterministic membership transition

**Proposal:** one authoritative membership resolver compares the prior and committed player membership sets after movement. It emits one transition record containing:

```text
before = ordered Area identities
after  = ordered Area identities
entered = ordered additions
exited  = ordered removals
```

The resolver, not each Area host, decides membership. The host consumes that record. This prevents two Area Programs from independently deciding that the same move entered or exited a scope.

The final ordering is unresolved. Candidate ordering dimensions that must be chosen explicitly include parent depth, authored priority, stable identity, and declaration order. Lua table iteration must never decide it.

### 9.4 Area policy versus Map/Location policy

**Proposal:** keep three visibly distinct sources:

```text
Location inherited policy
    defaults/constraints inherited through the non-playable hierarchy

Map policy
    policy owned by the continuous playable world / Map Instance

Area-local behavior
    behavior attached to one identity-bearing subdivision inside the Map
```

A Location policy may be inherited into a Map or Area if the owner later ratifies that relation. It should be displayed as inherited provenance, not copied into the Area's local program. An Area override/interruption should be explicit and diagnosable.

## 10. Zone distinction

**Repository fact:** `map.zones` contains authored rectangles or cell lists with IDs/tags, and `generatedZones` contains runtime tags such as room/corridor/anchor/entrance/exit. `fixture_predicates` combines them for spatial predicates. They do not currently own identity-bearing state, lifecycle, generation policy, or authored Programs.

**Inference / hypothesis:** the likely clean distinction is:

```text
Area
    identity-bearing semantic scope
    may own policy, state, generation, population, and lifecycle behavior

Zone
    spatial classification / predicate tags
    answers “what is this cell like?” for queries and placement
```

This is a hypothesis, not a ratified vocabulary. A future Area may use a Zone-like membership implementation internally, but current Zones should not be silently promoted. Doing so would make every fixture predicate tag a potential lifecycle host and would conflate generated room facts with authored semantic districts.

## 11. Waiting, reentrancy, and save/load rules

The following reuses #330's host contract and applies it to Map/Area scope.

### 11.1 Waiting

| Program kind | Wait rule |
|---|---|
| `on_instance_created` during synchronous generation | Must be immediate by default; creation cannot expose a half-built instance to gameplay |
| `on_activate` | May request a Message/Choice or declared transition interaction only if the activation owner can suspend before exposing the new input state |
| `on_deactivate` | May wait only before the old Map is replaced, with a bounded continuation owned by the transfer/transition host |
| `on_player_step` | Prefer immediate; a wait must suspend movement/encounter resolution and preserve the committed step exactly once |
| Area `on_enter`/`on_exit` | Prefer immediate; an interaction wait must be owned by the movement/transition host and must not re-evaluate membership on resume |
| Presentation `WAIT` | Never use as evidence of semantic suspension; current immediate Event Programs emit a presentation wait and continue |

**Proposal:** a hook may not yield from a pending spatial commit. Movement commits first; Area membership is resolved from that commit; then a hook may request an interaction. No hook may rewind the player cell or replay a transition after a wait.

### 11.2 Reentrancy

**Proposal:** every Map/Area invocation receives a host invocation ID and lineage. Nested Common Events inherit the caller's host scope and lineage; they do not become new lifecycle sources. A hook that requests a transfer or Map mutation schedules it through the owning capability after the current hook's bounded command list, or fails loudly if the contract disallows it.

Do not allow:

- `on_activate` recursively calling `on_activate` for the same activation;
- `on_exit` re-entering the same Map before the departure transaction settles;
- Area entry handlers mutating membership and then re-running the membership resolver in the same step;
- Map creation hooks triggering a second generation because a Common Event called `LOAD_MAP`.

The final recursion/lineage representation belongs with #308's broader deterministic reaction work, but Map/Area hosts must use the same eventual mechanism rather than inventing local guards.

### 11.3 Save/load

**Repository fact:** `engine.savegame` serializes current Map position, current runtime Map data, dangerous `mapStates`, generated collections, runtime lighting, presentation overrides, event overrides, and session state. `savegame.deserialize` reconstructs a new GameSession and current Map snapshot. Save is offered from resumable Map/town contexts, not arbitrary mid-battle/dialogue contexts.

**Proposal:** Map/Area host state must follow the owner of the state:

- Map Instance-local variables and Area-local variables serialize with the Map Instance;
- transient invocation frames, waits, and presentation handles do not serialize unless a future resumable interaction contract explicitly requires them;
- loading a save creates a new runtime host around restored state, not a replay of creation hooks;
- load may publish `activationReason="load"` if the owner wants a deterministic load-resume Program, but this must be explicit and exactly once;
- a cached Map returned within an expedition restores its instance-local state and does not re-run `on_instance_created`;
- a newly generated Map after expedition reset gets a new instance identity and may run `on_instance_created` once.

The current safe/dangerous cache asymmetry is an important design input. A future Area state contract must not assume every Map has the same cache path.

### 11.4 Disappearance mid-program

**Proposal:** if the Map/Area owner is invalidated, unloaded, or replaced while a Program is waiting, the continuation is cancelled with a loud diagnostic that names the host, instance identity, invocation ID, and reason. It must not resume against the next Map/Area by accident. If the operation is declared transfer-blocking, the transfer remains pending until the Program completes or is explicitly cancelled by the transition owner.

## 12. Deterministic ordering

### 12.1 Map order

**Proposal:** a real Map transfer has one transaction order:

```text
1. caller requests transfer with destination and arrival data
2. current Map deactivation policy runs, if admitted
3. pending deactivation operations settle
4. current Map Instance is cached/persisted as required
5. authoritative Map Instance activation/create/restore resolves
6. destination Map activation policy runs
7. player arrival is committed or exposed according to the transfer contract
8. post-arrival step/Area membership is resolved once
9. the caller resumes or the transition host exposes input
```

The exact placement of player coordinate assignment relative to `on_activate` remains an owner decision. It must be one declared fact: an activation Program must either see the resolved arrival cell or receive a separate arrival context that is not inferred from mutable session state.

### 12.2 Current step order and proposed insertion

The current step order is Flow, then Map Event, then encounter check after movement. A Map host must choose one of two explicit placements:

```text
movement commit
    -> Map on_player_step
    -> existing exploration.step Flow
    -> Map Event step/touch
    -> encounter check
```

or:

```text
movement commit
    -> existing exploration.step Flow
    -> Map on_player_step
    -> Map Event step/touch
    -> encounter check
```

**Recommendation:** keep the existing `exploration.step` Flow first because it currently owns traversal cost and per-step policy, then add Map-local `on_player_step` immediately after it and before Map Event/encounter resolution. This minimizes behavior movement and gives the Map hook a committed player step plus updated session state. If an author needs a trap/Event to pre-empt encounter checks, current Map Event behavior already supplies that boundary.

### 12.3 Area order

**Proposal:** after a successful movement commit and before encounter resolution, the membership resolver emits one delta. A future default ordering could be:

```text
Map step Flow
    -> Map on_player_step
    -> resolve Area membership delta
    -> Area exits in declared deterministic order
    -> Area enters in declared deterministic order
    -> Map Event step/touch
    -> encounter check
```

This is not ratified. The key invariant is that Area hosts consume one authoritative delta, and the order is declared rather than discovered through iteration.

### 12.4 Location inheritance and Area order

**Unresolved:** Location policy inheritance order is owner-directed as recursive cascade with descendant override/interruption, but the field-level merge and behavior ordering are not specified. The future contract must distinguish:

- inherited policy evaluation;
- Map/Area local Program order;
- Area exit/enter transition order;
- Common Event nested procedure order.

Do not merge inherited Programs into local arrays by copying them. Preserve provenance and precedence so Studio and diagnostics can explain why a behavior ran.

## 13. Mutation authority

| Proposed surface | May observe | May request | Direct mutation authority | May produce lifecycle signal |
|---|---|---|---|---|
| Map `on_instance_created` | creation/generation facts and Map definition | registered setup/population/presentation capabilities | no direct grid/session replacement | no; it is a consumer of creation |
| Map `on_activate` | activation, arrival, restored state | local policy, interactions, transfer request through host | Map-local namespace via registered commands | no |
| Map `on_deactivate` | departure and destination | cleanup, save/cache request through owner | no direct cache or Map index mutation | no |
| Map `on_player_step` | committed step and Map state | effects, flags, interactions, domain operations | no direct coordinate mutation | no |
| Area `on_enter`/`on_exit` | one resolved membership delta | local policy/population/effects | Area-local namespace via registered commands | no |
| Flow | named domain fact and domain context | domain operations | only through commands owned by their domains | it is the named lifecycle mapping, not a bus |
| Map Event Page | Event/page/position/trigger | Event commands and interaction | not Map Instance replacement | no |
| Scene hook | Scene state/input/focus | Scene transitions and interaction | Scene-local state only | no Map lifecycle |
| Exploration/Map Instance authority | all relevant requests | accepts typed lifecycle requests | Map index, grid, generation, cache, player position | yes |
| Area membership authority | committed spatial state | produces membership delta | membership facts only | yes, membership transition |
| Presentation/world renderer | resolved facts and visual state | visual effect requests | no gameplay mutation | no |

This follows #330's central rule: Event Programs request semantic operations and observe resolved facts; the capability that owns a transition commits it exactly once. A Map or Area Program must not “repair” a transition by comparing expected and actual coordinates.

## 14. Studio authorability

No UI is implemented by this report. The following is the smallest plausible authoring surface if the host model is accepted.

### 14.1 Map Inspector

**Proposal:** a Map Inspector could expose a compact Behavior section:

```text
Behavior
  On Instance Created   [Event Program...]
  On Activate           [Event Program...]
  On Deactivate         [Event Program...]
  On Player Step        [Event Program...]
```

Each slot should show its host scope and wait policy. The author should not edit raw JSON. The command list must be the existing shared `renderCommandList`, with a `map_instance` or equivalent registry context validated by `data/engine.json`.

The inspector should show the difference between:

- Map Scene `on_enter`/input hooks, which configure windows and controls;
- Map Instance lifecycle Programs, which affect the playable world;
- inherited Location policy, which is read-only at the Map level and links to its source;
- Map-local behavior, which is authored on the Map and has local provenance.

### 14.2 Area Inspector

Only after Area identity/membership exists:

```text
Area Behavior
  On Enter              [Event Program...]
  On Exit               [Event Program...]

Policy provenance
  inherited from        The Gate -> First Stratum
  local override        [details]
```

Generated Areas need a policy/provenance panel, not a separate editor language. The author should see the Area definition, generation source/seed lineage, resolved membership, and local Program slots. Runtime-generated room tags should remain visibly distinct from authored Area identity.

### 14.3 Shared editor and validation requirements

The existing architecture requires:

- shared command-list editor and clipboard;
- registry-declared context and command availability;
- validator checks for host IDs, command contexts, refs, and required slots;
- real-engine preview/validation rather than a JavaScript reimplementation;
- no new custom Event Page editor for Maps/Areas;
- G6 coverage for each new tab/modal only after a UI is actually added.

An Area/Map behavior editor that merely exposes a blank command list or lacks a resolvable context is an authoring bug, not a partial feature.

## 15. Bloat analysis

### 15.1 Useful vocabulary test

Map/Area hooks earn first-class status when all of these are true:

1. The transition is produced by one authoritative subsystem.
2. Multiple independent authored cases need it.
3. The context can be typed without exposing arbitrary engine tables.
4. The behavior is scoped to the Map/Area identity rather than a global procedure.
5. The host can define wait, ordering, save, and disappearance semantics.
6. The behavior cannot be expressed cleanly as an existing Event, Common Event, Flow, or domain capability without losing scope/authority.

`on_instance_created`, Map `on_activate`/`on_deactivate`, and Area `on_enter`/`on_exit` pass this test provisionally. Generic `on_frame` and `on_anything` do not.

### 15.2 When Common Event is enough

Use a Common Event when the behavior is a reusable procedure that a caller can explicitly invoke and that does not need to be discoverable as a lifecycle source. Examples include shared arrival narration, a reusable crowd setup procedure, or a common reward procedure invoked by a Map hook.

Use a host hook when the behavior must run because a specific Map/Area lifecycle transition occurred, with host identity, ordering, persistence, and cancellation supplied by the engine. The hook may invoke the Common Event; the concepts remain distinct.

### 15.3 Minimum surface recommendation

The smallest useful host surface is:

```text
Map Instance: on_instance_created, on_activate, on_deactivate, on_player_step
Area:         on_enter, on_exit (only after Area semantics are ratified)
```

Do not add Map `on_battle_start`, `on_battle_end`, `on_save`, `on_load`, `on_bump`, `on_event_move`, or `on_frame` as first-class slots now. Each is either another domain's lifecycle, an explicit reason/context on an existing transition, or a future capability that needs evidence.

## 16. Explicitly unresolved owner decisions

1. Is “Map activation” the moment `loadMap` begins, after runtime structure and player position resolve, or a separate post-resolution transition?
2. Should `on_instance_created` run for fixed safe Maps, or only for separately instantiated/generated runtime Maps?
3. Should Map `on_activate` run on save/load restore, return from Battle, or only on real Map Instance activation? If it runs, which explicit reason is exposed?
4. What exact ordering should Map `on_player_step`, `exploration.step`, Map Event step/touch, Area membership, and encounter resolution use?
5. May Map deactivation wait for an authored sequence before a transfer, and who owns cancellation if the player closes or the target disappears?
6. Should Map Instance-local variables live in `mapStates`, the current Map save snapshot, or a new explicit runtime namespace?
7. Does a fixed safe Map have a persistent instance identity across transfers, or is it re-resolved from authored data each time?
8. Is Area a stable authored identity, a resolved scope, or both? How does a generated Area identity survive cache and save/load?
9. Can Areas overlap? Can they nest? Are they a tree, flat set, or another structure?
10. Is Area membership player-only initially, or must arbitrary entity entry be supported from the start?
11. What is the deterministic order for Area exits/enters under overlap/nesting?
12. Does an Area `on_enter` wait block movement/encounters, or only show a modal overlay after the step commits?
13. How does recursive Location policy inheritance compose with Map/Area-local Programs, and what does explicit interruption/reset mean?
14. Is the current Zone vocabulary retained exclusively for predicates, or can a future Area use Zone records as an implementation detail without exposing that identity to authors?
15. Is a timer/scheduler capability needed for “while active,” and if so, what is its save/load and cancellation contract?
16. Should a Map/Area hook be allowed to launch Common Events in every host, or only through explicit command-context declarations?
17. What diagnostics should be emitted when an Area disappears during generation, mutation, transfer, or a waiting Program?

## 17. Small implementation fixtures that could falsify the proposal

These are evidence fixtures, not implementation commitments. They should be small, headless, deterministic, and added only after the owner chooses a follow-up scope.

### Fixture A: Map instance creation versus activation

Create a generated Map with a creation Program that increments instance-local state and an activation Program that records `created`, `restored`, and `activationReason`. Load it once, transfer away, return, save/load, and reset the expedition. The trace must show creation exactly once per instance lineage and activation on each declared activation reason.

**Falsifies the proposal if:** the current Map loader cannot expose a stable instance identity or cannot distinguish creation, cache restore, save restore, and transfer activation without reconstructing state.

### Fixture B: Map Scene displacement without Map deactivation

Start a Map Event that opens dialogue, then a battle, then return to the same Map. Record Map Instance activation/deactivation and Map Scene enter/exit separately.

**Falsifies the proposal if:** the intended owner actually wants every modal/battle detour to count as Map deactivation, or if the engine cannot keep those scopes distinct.

### Fixture C: Step ordering

Author one Map step Program, one existing `exploration.step` Flow marker, one step Event, and one encounter marker. Walk onto a cell with each combination and assert the exact trace, including blocked movement and a step Event that prevents encounter resolution.

**Falsifies the proposal if:** no single ordering can preserve current traversal cost, trap/Event behavior, and encounter semantics.

### Fixture D: Area membership delta

Use one Map with two non-overlapping Areas and a direct move from outside -> A -> B -> outside. Record membership before/after, exits, enters, and local counters.

**Falsifies the proposal if:** membership cannot be derived from the committed player cell without Area-local duplicate decisions.

### Fixture E: Overlap and nesting

Use parent Area P, child Area C, and overlapping Area Q. Move across cells that enter/exit one or several scopes at once. Require a stable transition order in repeated runs.

**Falsifies the proposal or forces an owner decision if:** the project cannot select a meaningful deterministic order or if the desired behavior is not representable by an ordered membership delta.

### Fixture F: Generated and authored scope parity

Place one authored Area and one independently generated Area in one Map. Each runs the same entry/exit Program but records origin, identity, and seed lineage.

**Falsifies the proposal if:** generated Areas need a different host/interpreter contract rather than different creation provenance.

### Fixture G: Waiting and disappearance

Have an Area entry Program request a Message/Choice, then transfer or reset the Map while the interaction is active. Assert cancellation diagnostics and verify that no continuation mutates the destination Map.

**Falsifies the proposal if:** host-owned cancellation cannot be made deterministic, or if the desired design requires arbitrary continuation across Map replacement.

### Fixture H: No render-frame authority

Run the same Map with different render/update frame pacing while holding the simulation step sequence constant. Any gameplay flag, timer, or Area counter must be identical.

**Falsifies the proposal if:** an author-facing Map/Area behavior genuinely needs render-frame sampling to be correct. In that case it belongs to a distinct presentation/simulation capability and must not be hidden in lifecycle hooks.

## Conclusion

**Inference:** “Maps and Areas can own scoped authored behavior” is a clean extension of the Event Program host architecture only when the host is attached to a resolved semantic scope and a real lifecycle source. Map Instance creation, activation, deactivation, and committed player step are sufficiently meaningful to justify a small Map host. Future Area entry and exit are meaningful if Area identity and membership become real. Current Zones, Map Scenes, Event Pages, Common Events, and Flow each already have narrower, healthier boundaries that should remain intact.

The architecture should therefore proceed in this order:

1. preserve the distinction between Map Instance and Map Scene;
2. prove Map lifecycle context and ordering with a headless fixture before adding schema;
3. defer Area hooks until identity, membership, persistence, overlap/nesting, and ordering are decided;
4. expose both through the shared Event Program editor and registry contexts if adopted;
5. use explicit timers/schedulers for “while active,” never a gameplay `EVERY_FRAME` callback;
6. keep domain capabilities authoritative and keep presentation on its own clock.

That is the minimum semantic host model that answers the owner pressure case without turning every structural object into a generic script container.
