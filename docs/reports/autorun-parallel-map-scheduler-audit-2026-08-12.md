# Autorun and Parallel Map Scheduler Audit

**Date:** 2026-08-12
**Baseline:** `main` at `65fff43e` (`#308C`, current checkout before this audit)
**Scope:** docs plus headless characterization only
**Status:** investigation; no scheduler, Map process schema, Area schema, or production runtime behavior is implemented

## Reading guide

This report uses four labels:

- **Repository fact:** observed in current code, data, tests, or generated state.
- **Owner direction:** a constraint from this investigation request.
- **Inference:** a conclusion drawn from those facts.
- **Proposal:** a candidate for a future implementation, not a ratified contract.

The authority order remains `docs/ENGINE-STATE.md` for current state and
`docs/SPEC.md` for behavior and rationale. The earlier reports from #330 and
#340 are architecture evidence, not substitutes for the live code.

## 1. Current Event trigger model

### 1.1 Map Event records

**Repository fact:** authored Map Events live in `data/maps/*.json` under each
Map's `events` array. A current event record may carry coordinates, a trigger,
inline `commands`, a `scriptId` Common Event link, presentation fields, spatial
metadata, and `pages`.

The current content uses these trigger values:

| Trigger | Current occurrence path | Current behavior |
| --- | --- | --- |
| `interact` (or omitted) | Confirm input while facing the Event cell | Resolves the Event Page and starts an interactive Event Program. |
| `bump` | A blocked forward movement into a wall-bound Event | May start the Event, including a door/transfer program. |
| `step` | Successful movement lands on the Event cell | Resolves and starts the Event after the step Flow. |
| `touch` | Successful movement lands on the Event cell, or facing interaction accepts it | Participates in the same current touch/step or interaction paths. |

`main.lua` owns the input occurrence paths. `engine.exploration` owns the
movement commit and Page resolution. There is no current update-loop scan that
starts a Map Event merely because its condition is true.

**Repository fact:** the current map trigger vocabulary is therefore an
occurrence vocabulary. It answers *what caused this program to start*, not
*how a resident program is scheduled*.

### 1.2 Current direction

The owner direction is the useful distinction:

```text
Action / Touch / Step = occurrences that start a program
Autorun              = foreground scheduled process while eligible
Parallel             = background scheduled process while eligible
```

This report does not add those names to the schema. It records that current
`interact`, `bump`, `step`, and `touch` behavior must not be repurposed as a
hidden scheduler contract.

## 2. Current Page and Event state model

### 2.1 Page resolution

`engine.exploration.resolvePage(ev, session)` walks an Event's ordered Pages,
evaluates each condition, and makes the **last matching Page** win. The Page
overrides are merged onto a shallow copy of the base Event. Conditions use the
shared prefixed condition grammar and fall back to formulas.

The resolved table can replace commands, trigger, presentation, movement and
other Event fields. Persistent and temporary Event overrides are applied after
Page resolution.

**Repository fact:** there is no separately persisted `activePage` object. The
current Page is an effective incarnation resolved when a caller needs the
Event. The characterization suite pins the last-match behavior and the base
Event fallback.

### 2.2 Semantic boundary

An Event Page remains the correct semantic unit for one spatial Event:

```text
Map Event instance
    -> effective Page
        -> condition
        -> presentation / movement / trigger fields
        -> Event Program
```

This is not the same as a Map's lifecycle. A Map has no competing Page
incarnations in the current model, and an Area is not implemented. Giving a Map
or Area Event Pages would imply spatial-entity semantics that the lifecycle
question does not require.

### 2.3 What persists today

Event-local behavior that does persist is represented through session state,
Map runtime data, `eventOverrides`, `tempEventOverrides`, mutated Event data,
or the Map cache. The active Page selection itself is not a saved interpreter
continuation. A new lookup resolves it again from current conditions and
overrides.

## 3. Current Common Event model

Common Events are loaded from `data/commonEvents.json` and are named reusable
command lists. The current repository has 20 Common Events according to the
generated engine state.

There are three current invocation shapes:

1. A Map Event or effective Page uses `scriptId`; the host looks up that Common
   Event and runs its commands as the Event's program.
2. An interactive `CALL_COMMON_EVENT` command compiles to a graph action. The
   host dynamically injects the Common Event commands into the caller's graph
   and resumes at the caller's next node.
3. A `common_event` item effect emits a request. The presentation-bound host
   receives the request and starts the same Event path; an unbound headless host
   declines it.

**Repository fact:** `CALL_COMMON_EVENT` is interactive. Immediate mode rejects
it because immediate execution has no interaction owner or continuation slot for
the resulting graph. This is a current admissibility seam, not a statement that
all future Common Events must be dialogue-scene programs.

**Inference:** Common Event is the right reusable procedure noun. It should not
become the lifecycle source merely because a future Autorun or Parallel process
may call one. The scheduler should own the process frame; the Common Event
should remain the procedure definition and executable body.

## 4. Current interpreter lifetime

The repository has one shared command language with two current execution
modes.

### 4.1 Immediate mode

`interpreter.runImmediate(commands, ctx)` executes synchronously and returns an
event list. It requires a session, creates `ctx.events` and `ctx.v` when absent,
and does not retain a program counter after returning. Flow phases and Scene
hooks use this mode. Battle and effect code also consume this mode.

Immediate command mutations happen before the caller receives the event list.
The current `WAIT` handler appends `{ type = "wait", duration = ... }`; it does
not yield the interpreter or delay the next command.

### 4.2 Interactive mode

`interpreter.runInteractive` compiles commands to a graph. `main.lua` owns the
module-local `activeWalker`, which is a `director.GraphWalker` over that graph.
The current host advances the walker from input, timer completion, battle
result, recruit result, or automatic graph handling.

Interactive `WAIT` becomes a `WAIT_EVENT` graph action. `main.lua` records its
duration in `eventWaitRemaining`; `love.update(dt)` decrements that timer and
advances the walker when it reaches zero. The graph and walker are therefore a
real current suspension/resumption mechanism for interactive Events, but they
are not a general scheduler.

### 4.3 Battle and Dialogue continuation

An interactive Event that starts Battle stores `victoryNode` and `defeatNode` in
`pendingBattleResume`. Battle reports its resolved outcome; the caller then
moves the existing walker to the selected node and continues it. Dialogue and
Battle Scene transitions do not recreate the Map Instance or restart the Event
graph.

This is the important current pressure case:

```text
Map Event graph
    -> START_BATTLE
    -> Battle Scene displacement
    -> battle result
    -> existing caller walker resumes at the selected continuation
```

The continuation is currently host-owned in `main.lua`, not a serializable
Map-owned process object.

## 5. Current update and timing sources

The following clocks are distinct and must not be collapsed into one future
"frame" concept.

| Source | Current meaning | Gameplay authority? |
| --- | --- | --- |
| Render frame / `love.draw` | Projection of current state and presentation animation. | No. |
| `love.update(dt)` | Per-update timers, presentation updates, Scene hooks, dialogue wait, Battle update, and held-key repeat. | Partly; it is the host clock, not a generic Map process contract. |
| Scene `on_frame` hook | Immediate Event Program run once from `scene_host.update` when its Scene wait is not active. | Scene-local only. |
| Successful player step | A committed coordinate change from `exploration.tryMove`; it is not every update or every keypress. | Yes, the Map occurrence boundary. |
| Event interpreter resume | Interactive graph continuation after input, a wait timer, a Scene result, or a Battle result. | Yes for that caller's program. |
| Duration/timer | A value consumed by a particular owner: Scene wait, interactive Event wait, transition animation, or presentation effect. | Only within that owner. |
| Presentation `WAIT` | Immediate event-stream pacing information. | No semantic suspension. |

The current Map movement path is:

```text
input or held-key repeat
    -> exploration movement attempts
        -> failed bump: no coordinate commit, no step Flow
        -> successful coordinate commit
            -> exploration.step Flow
            -> step/touch Event lookup and execution
            -> encounter check only when no step Event handled
```

The #343 characterization suite already pins that order. The new suite pins
the separate immediate and interactive WAIT behavior and Scene-local wait
behavior.

## 6. Current Scene displacement behavior

`engine.scene_host.goto_scene` is synchronously `pop` then `push`. Scene hooks
run on the Scene stack, and Scene state owns its local `v`, windows and wait
timer.

The Map Scene is displaced by Dialogue, Battle, shops and menu-like Scenes. The
Map Instance remains in `session.currentMapData`, `session.mapGrid`, and
`session.currentMapIndex`. Returning to Map pushes a new Map Scene state around
the same playable Map runtime.

This yields four independent facts:

| Question | Current answer |
| --- | --- |
| Who captures input? | The current Scene and its input hooks, then Map fallback logic where the hook declines. |
| Is world simulation paused? | There is no single global answer; current Map movement is unavailable outside Map input, while presentation and selected Scene updates continue. |
| Is the Event Program suspended? | An interactive caller may remain in `activeWalker` while Dialogue/Battle or another Scene owns the foreground. |
| Is the Map Instance resident? | Yes, across Dialogue and Battle displacement. |

**Critical conclusion:** `currentScene == "map"` cannot be the scheduler's
eligibility predicate. Scene displacement is not Map Instance departure, and
Map Instance residency is not proof that its automatic processes should run.

Actual Map replacement is owned by `exploration.loadMap`. It caches the old
dangerous runtime state before installing the new current Map. Save restore is
different again: `savegame.deserialize` creates a new `GameSession` and
restores Map state directly without calling ordinary `exploration.loadMap`.

## 7. Exact missing machinery for Autorun

The current code has no Autorun process. To support the requested pressure case,
the smallest missing pieces are:

1. **Eligibility source:** a declared condition evaluated against a specific Map
   Instance and effective Page/process definition, with a clear re-evaluation
   boundary.
2. **Foreground ownership:** a process can claim the foreground world
   execution slot while eligible. The contract must state what happens to
   player input and another foreground Event.
3. **Stable process identity:** the running process needs an owner, definition
   identity, activation generation, and effective-page/condition provenance so
   returning from Battle cannot look like a new Map activation.
4. **Continuation state:** at minimum a program counter, local variables,
   caller/lineage context, current wait descriptor, and pending interaction or
   result continuation.
5. **Interaction bridge:** TEXT/CHOICE, Battle, Dialogue and other modal
   interactions must suspend the process frame and return the result to that
   same frame.
6. **Eligibility transition policy:** the implementation must define whether a
   completed eligible Autorun immediately starts again, starts only after a
   false-to-true transition, or is one-shot for a Map Instance.
7. **Scene-independent ownership:** the process must remain associated with the
   resident Map Instance while Map Scene, Dialogue and Battle are displaced.
8. **Cancellation and replacement:** a Page change, Map replacement, expedition
   reset, or process invalidation must cancel or retire the continuation exactly
   once.
9. **Save contract:** mid-program state must either serialize completely and
   resume, or the mode must explicitly restart from an eligibility boundary.

None of this machinery exists in `GameSession`, `scene_host`, `savegame`, or the
current interpreter. Adding a foreground flag to the Map Scene would not supply
these missing lifetime boundaries.

## 8. Exact missing machinery for Parallel

The current code also has no Parallel process. It needs the Autorun machinery
except for exclusive foreground ownership, plus:

1. A resident process collection owned by a Map Instance or another explicit
   semantic scope.
2. Independent continuation state and local variables for each process.
3. A deterministic process clock or next-resume condition. A Parallel process
   must not mean arbitrary Lua called once per render frame.
4. A policy for `WAIT`: it must suspend that process only, not the entire Map
   Event/interpreter domain and not just its renderer.
5. Eligibility loss handling: condition false, Page replacement, Map
   deactivation, cache eviction and expedition reset must be explicit.
6. A serialization/restart policy for every wait and continuation state.
7. A deterministic scheduler transaction boundary so two parallels cannot
   observe a half-applied domain mutation or race through OS threads.
8. A stable ordering rule for multiple eligible processes and a defined rule for
   newly spawned, completed, cancelled and re-eligible processes.
9. Author-visible diagnostics: process identity, current node, wait reason,
   eligibility and last domain mutation should be inspectable in headless and
   Studio tooling.

The future Parallel scheduler is therefore a deterministic cooperative process
runner, not Lua threading.

## 9. Foreground versus background process contract

**Proposal:** use two explicit scheduler contracts over the shared Event Program
language.

### Foreground process

- At most one foreground world process owns the Map Instance at a time.
- It may capture world input and may suspend for interaction, Dialogue, Battle
  or another declared result.
- A player occurrence that arrives while it owns the foreground must have an
  explicit policy: queue, reject, or become a nested caller. It must not
  accidentally start a second foreground program.
- Its continuation remains the same process across Scene displacement.
- Completing the body does not itself imply a Map Scene transition.

### Background process

- It never captures player input by default.
- It advances only at scheduler-owned process boundaries.
- It may wait without blocking the foreground process, subject to declared
  interaction restrictions.
- It requests domain mutations through the authoritative domain capability; it
  does not mutate shared state concurrently.
- Multiple background processes are serialized deterministically.

This contract leaves source-local precedence unresolved. Flow, Map Event,
Autorun, Parallel, Battle and #308 reaction sources should not be forced into a
single global callback order merely because they share an interpreter.

## 10. Simulation eligibility

The scheduler needs an explicit policy with more state than the current Scene
stack. The relevant axes are:

| Axis | Meaning |
| --- | --- |
| Map Instance resident | Its runtime Map state exists and may be in `mapStates` or current session fields. |
| Map Instance current/active | It is the authoritative playable world selected by `currentMapIndex`. |
| Simulation eligible | Its declared automatic processes are allowed to advance at this scheduler boundary. |
| Input eligible | It may receive player input. |
| Foreground owner | A process or interaction currently owns world execution. |
| Presentation active | Its Scene/presentation objects may continue updating. |

**Proposal:** the default policy should be:

- current active Map Instance: eligible, unless an explicit world-pause policy
  says otherwise;
- Map Instance resident only in a cache: not eligible;
- Map Scene displaced by Dialogue or Battle while the same Map Instance remains
  current: process eligibility is decided independently of the Scene stack;
- current Map with a modal interaction: foreground Event suspension and
  background simulation are separate policy decisions;
- menus/pause-like Scenes: default to no Map process advancement unless an
  explicit host policy admits it;
- actual Map replacement or expedition reset: retire/deactivate old Map
  processes exactly once and evaluate the new Map under its own activation
  policy;
- save restore: use an explicit `load`/`restore` reason, not an inferred Scene
  enter or a false Map activation.

This is a policy proposal, not current behavior. Current code only proves
residency and replacement seams; it does not publish simulation eligibility.

## 11. Deterministic ordering requirements

Current Map movement already provides one concrete ordering requirement:

```text
coordinate commit
    -> exploration.step Flow
    -> matching step/touch Event
    -> encounter check if no step Event handled
```

For the future scheduler, the falsifiable minimum is:

1. At the start of a simulation tick, take a deterministic snapshot of eligible
   processes. A process becoming eligible during the tick joins the next
   snapshot unless the host explicitly defines a same-tick continuation.
2. Run one process until it completes, waits, suspends, or yields at an explicit
   semantic boundary. No OS threads and no interleaving inside a domain command.
3. Serialize all authoritative domain mutations through the owner capability.
4. Use a stable order within one scheduler scope: authored declaration order or
   another persisted process key. The choice must be visible and tested.
5. Define whether a process that completes and remains eligible is requeued in
   the same tick or next tick. The safer initial prototype is next tick.
6. Define cancellation before the next process starts when Page/Map eligibility
   becomes false.
7. Record an execution trace with tick, scope, process key, program counter,
   wait/yield reason and emitted domain facts.

No global precedence between Flow and every other Event Program host is selected
here. The #330 report's phenomenon-specific host model remains the better
boundary: source authority and participant scope are declared by the domain
phenomenon.

## 12. Waiting, suspension and resumption

The word `WAIT` currently names several different things:

| Wait | Current owner | Current effect |
| --- | --- | --- |
| Immediate interpreter `WAIT` | Event stream / presentation consumer | Emits pacing data; semantic commands continue synchronously. |
| Interactive Event `WAIT` | `activeWalker` plus `main.lua` timer | Suspends the caller graph until the timer expires. |
| Scene hook `WAIT` | Scene state | Blocks that Scene's `on_frame` hook while its local timer remains. |
| Dialogue TEXT/CHOICE | Interactive caller plus Dialogue Scene | Input/modal suspension; caller walker remains owner. |
| Battle transition | Caller walker plus Battle result callback | Suspends at the action node and resumes at an outcome branch. |
| Future scheduler yield | Not implemented | Must be a named scheduler/domain primitive, not inferred from presentation WAIT. |

The existing Battle continuation is evidence for the desired no-restart rule:
returning from Battle moves the original walker to its continuation. A future
Autorun must use the same shape, but with a scheduler-owned frame rather than a
`main.lua` singleton.

## 13. Save/load implications

### 13.1 Current evidence

`savegame.serialize` stores GameSession data, Map runtime data, Map cache state,
party state, flags, inventory and related persistent records. It does not store:

- `activeWalker` graph or program counter;
- `eventWaitRemaining`;
- `pendingBattleResume`;
- Scene-local `v` or Scene wait timers;
- a Common Event caller stack;
- Map process identity, eligibility or scheduler time.

The characterization suite asserts the absence of continuation/process fields in
the current payload. The existing save rule is consequently “save from a
resumable Map/Town state,” not “serialize every live Event execution.”

### 13.2 Future choices that must be explicit

An Autorun or Parallel process saved mid-program requires one of:

- full serialization of process definition/version, owner Map Instance,
  effective Page, program counter, locals, wait descriptor, caller lineage and
  pending interaction/result;
- a defined restart-from-eligibility policy for that mode;
- a hybrid policy that serializes some process kinds and rejects others.

Restart is not automatically safe: an Autorun that already changed a flag,
started Battle, or mutated a Map can duplicate side effects if its continuation
is lost. Conversely, restoring a process against a changed Page or changed
authored program needs a version/invalidation rule. This report does not choose
the policy without a fixture and owner decision.

## 14. Map-owned process pressure case

The conceptual pressure case is:

```text
Map Instance
    Processes
        opening sequence [foreground scheduled process]
        ambience logic   [background scheduled process]
```

This is preferable as an explicit Map-owned semantic scope when the behavior is
about the Map Instance as a whole. It avoids requiring an invisible Event at
`(0,0)` whose spatial trigger and Page semantics would be misleading.

The Map-owned process context would need, at minimum, Map Instance identity,
current Map definition identity, process definition identity, local state,
eligibility policy, caller lineage, and a declared interaction/simulation policy.
It should be able to call Common Events and shared commands, but authoritative
Map mutation remains with exploration/Map capabilities.

The pressure case also exposes the crucial distinction:

- opening sequence may remain foreground while Dialogue or Battle temporarily
  owns presentation/input and then return to the same frame;
- ambience logic may continue during a modal or be paused by policy;
- neither process should silently continue just because its Map is cached but no
  longer current.

No Map process schema is added by this report.

## 15. Area-owned process pressure case

An eventual Area scope could conceptually own:

```text
Area
    Processes
        local ambience [background]
        entry sequence [foreground or interaction-capable]
```

But current code does not provide the prerequisites:

- no Area resource or stable Area identity;
- no membership resolver;
- no overlap/nesting rule;
- no enter/exit ordering;
- no save identity for Area-local state;
- no current transition fact for membership change.

**Inference:** Area processes must not be inferred from current Zone tags. A Zone
currently classifies cells for placement/detection; it is not an identity-bearing
membership scope. Area hooks should wait until Area identity and membership
semantics are independently ratified and falsified by fixtures.

If Area is later accepted, the smallest initial lifecycle surface is likely
`on_enter` and `on_exit`, with process ownership and overlap ordering still
explicit. Area Event Pages are not implied by this.

## 16. Studio authorability implications

The editor consequences are architectural, not a request to implement them now.

1. Map Event Pages should remain the current incarnation of one spatial Event;
   the editor should not present Map/Area processes as fake Pages.
2. Map/Area process definitions need an explicit owner and scheduling mode in
   their own schema surface. A generic trigger dropdown would conflate
   occurrence and scheduling again.
3. The command list must remain the shared `renderCommandList` surface and use
   `engine.json` contexts. Autorun/Parallel should not get a second scripting
   language or a private command editor.
4. Common Events should remain linkable reusable procedures, distinct from the
   spatial/presentation definition of an Event Template/Prefab.
5. Studio needs to show eligibility, current continuation, waits and ownership
   without implying that current Scene visibility is the process lifetime.
6. Preview and validation should drive the real engine and reject ambiguous
   owner/context combinations. A form that allows an unwriteable process
   context is a G1/editor contract failure.
7. Headless trace output should be author-readable: stable process key, scope,
   tick, command/node, wait reason, emitted facts and final state.

The existing “one event editor, everywhere” rule remains the right authoring
constraint. It does not require that all hosts have identical admissibility or
waiting semantics.

## 17. Minimum falsifiable implementation prototype

This is a future prototype description, not an implementation in this branch.
It is intentionally narrower than a scheduler rollout.

### Fixture

Create one synthetic Map Instance and two process definitions in a headless
test-only fixture:

- `opening`: foreground, eligible from Map activation, commands `SET_FLAG A`,
  interactive `TEXT`, `START_BATTLE`, `SET_FLAG B`, then completion;
- `ambience_a`: background, eligible while `flag:ambience`, `SET_FLAG C`,
  semantic scheduler `WAIT`, `SET_FLAG D`;
- `ambience_b`: background, same eligibility, `SET_FLAG E`, `WAIT`,
  `SET_FLAG F`.

Drive the fixture through these phases:

```text
activate Map
tick 1
open Dialogue from opening
return from Dialogue
start Battle from opening
return victory to opening
complete opening and leave eligibility true
tick 2 with two eligible parallels
WAIT ambience_a
transfer to Map B and cache Map A
return to cached Map A
save while ambience_b is waiting
restore in a new session
```

### Required trace and falsifiers

The prototype is valid only if a deterministic trace proves:

- the Autorun resumes at its post-Battle continuation, never from node one;
- Dialogue/Battle displacement does not create a false Map activation;
- Parallel A's WAIT does not suspend Parallel B or the foreground owner;
- two parallels use a stable, documented order and serialized mutations;
- a cached, non-current Map does not tick unless an explicit policy says so;
- changing eligibility cancels or retires a process exactly once;
- completion/re-eligibility behavior is observable rather than accidental;
- save/load either resumes with complete process state or follows an explicit
  restart policy without replaying committed mutations;
- render-frame frequency does not change the semantic trace.

The smallest useful trace record is:

```text
simulationTick, scopeId, processId, programCounter,
eligibility, action, waitReason, emittedDomainFacts
```

The prototype should not use OS threads, `love.draw`, Scene identity as a
process clock, or presentation WAIT as a semantic yield. It should be rejected
if any of those are required to make the trace pass.

## 18. Explicit non-decisions

This audit intentionally does **not** decide:

- the final schema names for Autorun, Parallel, Map Processes or Area Processes;
- whether Autorun re-runs continuously while eligible or only on a false-to-true
  eligibility transition;
- whether a process is defined directly or through a Common Event reference;
- whether Map process eligibility continues during Dialogue, Battle or menus;
- whether a Battle/Dialogue interaction is a modal layer or remains a Scene in
  the final architecture;
- the exact scheduler tick, fixed timestep, budget or fairness algorithm;
- global precedence between Map processes, Flows, Event occurrences, Troop
  Events, Scene hooks and #308 reactions;
- the exact ordering of Map process execution relative to
  `exploration.step`, step Events and encounter checks;
- save/load serialization versus restart policy for each process mode;
- Area identity, membership, overlap, nesting, enter/exit ordering or process
  persistence;
- a native plugin ABI, package format or scheduler extension ABI;
- any migration of existing Common Events, Map Events or Scene hooks;
- any production runtime scheduler implementation.

## Characterization changes

Added `tests/test_autorun_parallel_characterization.lua` and registered it in
the existing headless unit suite. The tests pin current behavior only:

- last-match Page resolution and base fallback;
- synchronous immediate `WAIT` versus interactive graph `WAIT`;
- interactive Common Event invocation versus immediate rejection;
- Scene-local `on_frame` wait timing;
- the current save payload's lack of Event/process continuation state.

The existing `tests/test_map_instance_lifecycle.lua` remains the authority for
Map Instance versus Map Scene displacement, Map replacement/cache, save restore,
and committed step ordering.

## Verification

- `git diff --check`
- `lovec . unittest` -> `ALL UNIT TESTS OK`

No authored JSON, schema, production Lua subsystem, golden, asset, or editor
behavior was changed.
