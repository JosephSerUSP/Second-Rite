# Event Program host contracts and deterministic precedence

Status: architecture/specification report for #328, prepared against current
main (2026-08-11). This report changes no Lua runtime behavior, authored
schema, golden reference, asset, or editor code.

## Executive summary

Thestra has one Event Program substrate and several legitimate hosts. The hosts
are not interchangeable callback lists: each is defined by a different source
of authority, lifetime, trigger, context, and waiting policy.

The smallest deterministic model is phenomenon-specific:

    domain phenomenon / lifecycle source
        +--> domain-wide authored policy (Flow, where defined)
        +--> encounter-scoped participation (Troop Event, where admitted)
        +--> typed source-local participation (#308, where applicable)
        +--> presentation projection

    scene lifecycle/input source
        +--> Scene hook(s)

    action transaction
        -> action-local Event Program (Action Sequence)
            -> typed pending calculation/interception (#308)
            -> authoritative commit (RPG Battle/effect capability)
            -> immutable resolved fact
            -> typed reactions (#308)
            -> action-local continuation
            -> presentation projection/pacing

This is a contract, not a runtime refactor.

* Flow remains the current lifecycle-signal-to-Event-Program mechanism.
* Thestra preserves a first-class authoritative RPG Battle semantic capability;
  engine/battle.lua is the current implementation seam, not a permanent module
  boundary.
* Troop Events are encounter-local participants. Current Flow command lists may
  invite them at explicit phases, but Flow is not their semantic owner.
* Action Sequences own the authored execution of one action.
* Common Events are reusable named procedures/processes, not lifecycle sources.
* Scene hooks belong to a Scene instance, not Battle-domain lifecycle.
* #308 calculation contributions, pending interceptors, resolved reactions,
  source-local memory, provenance, and lineage are typed phenomena.
* Only the authoritative domain capability commits a gameplay transition once.
  Presentation consumes resolved facts and never replays or repairs them.

The crucial multi-hit rule is per-effect completion: each effect request is
calculated, intercepted, committed, published, and reacted to before the
Action Sequence continues. The current implementation already commits each
APPLY_EFFECT immediately; this report makes the intended boundary explicit.

## Evidence labels and scope

* Repository fact means directly observed in current main code, data, or tests.
* Proposed contract means the architecture recommended here; it is not claimed
  implemented unless separately labeled as fact.
* Unresolved question means an owner decision still required before a schema or
  runtime seam is committed.

This report was checked against #325, #326 and merged #327, #308, merged #313
and its gameplay-authorability report, merged #320 and its reconciliation
report, #260, and current implementation. Code takes precedence over reports
where they differ. The optional owner-project RM2k3 archaeology was not
available and is not required for these conclusions.

## 1. Current verified Battle execution trace

### 1.1 Battle start

Repository fact: engine/scenes/battle.lua triggerBattle calls
flow.run("battle.battle_start", ...) unconditionally. The battle Flow runs
SPAWN_ENEMIES, barrier setup, and RUN_TROOP_EVENTS at battle_start.
SPAWN_ENEMIES uses the named troop when supplied, otherwise troop.rollForMap;
engine/troop.lua builds named or weighted-pool slots and returns battlers.

The current sequence is:

1. A Map/Common Event or encounter requests a battle. The interactive caller
   remains responsible for its eventual outcome branch.
2. battle.battle_start Flow executes immediately.
3. SPAWN_ENEMIES resolves encounter/troop and constructs enemies. This is
   authoritative setup, although Battle.new has not yet run.
4. Barrier synchronization runs for living allies and enemies.
5. Inherited base-troop Events run first, then named-troop Events. A current
   troop Event has battle_start, round_start, after_action, or round_end scope.
6. The Flow returns spawn_enemies and troop facts. The Scene pushes a fresh
   battle Scene state and constructs Battle.new.
7. The troop is attached to the Battle; input/log state is initialized and
   living members are rebuilt.
8. Presentation initializes the battle view/animations.
9. Player/AI input begins. AI decisions are later built by Battle, not by the
   presentation menu.

The setup Flow has session, loader, troopId, enemies after spawning, and troop,
but no Battle object. Later phases receive Battle. This is a current
construction asymmetry, not a general context contract.

### 1.2 One normal action

Repository fact: the Scene collects and confirms player actions. Battle then
constructs one player/AI queue, applies first-strike logic, and sorts by
priority, first strike, speed, and original order.

For one turn:

1. Battle reaches the action in queue order and checks actor/target legality.
2. For an item, Battle resolves targets, runs the item Action Sequence, then
   consumes the item authoritatively.
3. For a skill, Battle resolves targets and cover, pays cost at resolution
   time through skill_cost.spend, starts cooldown, and emits a resolved MP
   fact for overcast where applicable.
4. Battle constructs the Action Sequence context: actor a, target, targets,
   skill or item, battle, session, loader, events, and refs.
5. interpreter.runImmediate executes synchronously. APPLY_EFFECT calls the
   effect capability. Each effect mutates Battler/Session immediately and
   appends events. engine.effects stamps after-values as resolved facts.
6. The Action Sequence continues after the effect returns. Later commands see
   committed state even if presentation has not revealed the prior animation.
7. Only after the complete Action Sequence returns does current Battle call
   flow.run("battle.after_action"). That Flow runs current troop after_action
   Events. It is not a current per-hit reaction point.
8. Battle checks victory/defeat after after_action. A reserve wave may deploy
   before defeat is emitted.
9. The Scene later drains the event list. It may wait for animation, popup,
   death effect, or sequence WAIT. Those waits do not roll back the Battle or
   Session graph.

Repository fact: current default skill/item Action Sequences place
APPLY_EFFECT between animation and WAIT commands. Immediate mode rejects
interactive commands. WAIT emits a presentation wait event; it is not a
half-committed transaction.

Repository fact: current damage resolution calculates damage, applies barrier
absorption, writes HP, emits damage, marks death, awards kill MP, and may
execute. There is not yet a general #308 pending-transition interceptor or
resolved-reaction dispatcher. Existing barriers are domain-specific
pre-commit behavior, not permission for ordinary lifecycle hooks to mutate
pending damage.

### 1.3 Round boundaries

Repository fact: Battle.resolveRound performs:

1. immediate outcome check;
2. battle.round_start Flow;
3. queue construction;
4. ordered turn loop, including after_action and outcome checks after each turn;
5. battle.round_end Flow unless escape ended the round;
6. round increment.

round_start runs before queue construction, so a troop Event can affect who
acts. The current Flow refreshes barriers before troop Events. round_end runs
state ticks and skill timers, then troop Events, adjacency behavior, and barrier
aging. A defeat caused by a tick can deploy a reserve wave or emit defeat.

These are different semantic boundaries. after_action is after one complete
action procedure; round_end is after the action loop and owns periodic behavior.

### 1.4 Victory, defeat, and escape

Repository fact: a lethal action can append victory or defeat after the
authoritative outcome check. Successful escape returns from the round
immediately, so slower queued actions do not execute.

The Scene later handles the outcome:

* victory runs battle.victory Flow, which currently grants gold and XP, heals,
  reaps fallen creatures, records history, clears states, and prepares
  victory/level-up presentation;
* defeat runs battle.defeat Flow, whose authored result selects Game Over;
* escape runs battle.escaped Flow, which reaps fallen creatures, records
  history/cleanup, and selects Map.

Rewards and cleanup are authoritative mutations executed by Flow commands.
Narration, level-up display, reaping animation, and Scene timing are
Scene/presentation responsibilities. A caller resumes its interactive graph
through battle.onResolved after the Scene outcome; this is caller continuation,
not a second Battle lifecycle hook.

### 1.5 Current ordering that must not silently become contract

* current troop after_action waits until the complete Action Sequence returns,
  even when several effects have already committed;
* battle.after_action receives turn.target, not a typed resolved fact for every
  effect or a guaranteed final target;
* victory/defeat Flow begins from Scene transition handling after log timing;
* engine/scenes/battle.lua directly requires presentation modules (#260);
* setup Flow has no Battle object before Battle.new;
* base-troop inheritance is base first, own second, then authored array order;
* current arrays are ordered, but future source iteration must not rely on
  Lua hash traversal;
* fixed barriers, execution, and trait checks are not a generic #308 system.

## 2. Event Program host taxonomy

All hosts use the shared interpreter where commands are admissible. A host
supplies trigger, scope, caller identity, typed context, lifetime, and waiting
rules.

### 2.1 Map Event Page

Proposed contract: a Map Event Page is a stateful world-entity host.

Activation belongs to the Map/interaction scheduler: page predicates, trigger,
priority, spatial relation, and movement determine when the active page starts.
Scope is one live Map Event instance and active Page. Event-local state persists
with the instance. Minimum context is session, loader, map, event, page,
position/trigger, event-local state, and spatial caller references.

This Event means the active Map Event instance, not the player or Scene. It may
suspend for Message/Choice, modal interaction, or Scene transition. It may
request effects, map changes, battles, Common Events, and interaction, but
authoritative Map/session/Battle capabilities commit those transitions.

### 2.2 Common Event

Proposed contract: a Common Event is a named reusable Event Program or process
definition, not a lifecycle source.

An invoked Common Event has a caller frame, declared arguments, caller context,
a local procedure scope, and inherited lineage. It returns result/events/wait
to its caller. An Autorun-like process is a scheduler-owned process that starts
a Common Event according to a Map/Scene/domain policy. A Parallel-like process
is also scheduler-owned and ticks independently, but semantic requests touching
the same domain state are serialized by the domain scheduler.

The current implementation has an important restriction: CALL_COMMON_EVENT
is interactive and compiles into a dialogue graph, while immediate mode refuses
it. This is a current admissibility seam, not a rule that all Common Events
must always use dialogue.

### 2.3 Troop Event

Proposed contract: a Troop Event is an encounter-local Event Program owned by
the troop. Its lifecycle source is an encounter/domain phenomenon that admits
troop participation; it is not a global subscription or a Flow-owned callback.

Repository fact: current Battle Flow command lists contain
`RUN_TROOP_EVENTS` at explicit phases, so the current dispatch path is Flow ->
troop handler. That is current orchestration/migration reality, not the future
semantic claim that Flow is the universal parent of encounter participation.

Scope is one Battle/encounter. Base inheritance and suppression resolve into
an ordered list. once is encounter-local and records after the event actually
runs. Minimum context is battle, troop, phase, session, loader, party/enemies,
event, condition locals, and where relevant action or resolved fact.

A Troop Event may request effects, state, action, text, or encounter policy
through semantic commands. It cannot directly commit an effect or promote
itself into a global callback. Current base-first/own-second order is a
deterministic current-host fact; future package composition needs an explicit
source order.

### 2.4 Flow / lifecycle hook

Proposed contract: Flow remains one legitimate domain-wide lifecycle host,
mapping a named domain signal to an Event Program. It is not the parent
dispatcher for every other Event Program host.

Its source is a named fact such as battle start, round start, after action,
round end, victory, defeat, escape, exploration step, or recovery. Context is
narrow: session, loader, battle/troop/party/enemies/round/action only where
that signal owns them, plus typed facts when published. A required Flow is
validated and fails loudly when absent; it is not silently replaced by Lua.

The domain capability or scheduler owns publication of the phenomenon and the
declared ordering of any participants that phenomenon admits. The current data
model has one provider for a named Flow phase. If packages later contribute
multiple Flow providers, order and composition must be declared; last
registered callback wins is not a contract. Current Flow programs may contain
`RUN_TROOP_EVENTS`, but that implementation path does not make Flow the owner
of Troop scope, Scene hooks, or typed #308 reactions. Flow may emit requests,
events, Scene transitions, and results, but is not itself Battle effect
authority.

### 2.5 Action Sequence

Proposed contract: an Action Sequence is the Event Program for one action
instance. Its lifetime starts when Battle accepts an action and ends when the
sequence returns, fails, or is cancelled by a declared action rule.

Minimum context is source/actor, action, skill/item, original/current targets,
battle, troop where relevant, session, loader, action-local vars/refs,
lineage, and event/result stream.

It may issue multiple typed effects, repeat hits, branch on action-local facts,
invoke a Common Event where allowed, emit presentation pacing information, or
request a declared follow-up. In current immediate execution, `WAIT` emits a
presentation event and returns; it does not suspend semantic continuation. An
interactive/modal command may suspend the calling frame where the host admits
it. A future semantic yield for ATB, cancellation, or interruption must be an
explicit scheduler/domain capability, not a presentation `WAIT`. The Action
Sequence may not directly mutate HP/MP/state/inventory, replace Battle
legality/target/outcome authority, infer results by rerunning formulas, or
become a passive global listener.

The ordering contract is: each semantic effect request enters the typed
pipeline and commits before the next Action Sequence command. Reactions for
the resolved fact run at that effect boundary, subject to admissibility. A
presentation wait may pace visible replay but cannot suspend, defer, or undo
the semantic commit.

### 2.6 Scene hook

Proposed contract: a Scene hook is scoped to one active Scene instance. Its
source is Scene enter/exit, update, select, cancel, direction, inspect, or
another declared input/composition event. Context is scene, Scene-local v,
input/focus state, active interaction, session, and loader.

scene.enter is not battle.round_start. The former exists because a Scene
instance became active; the latter exists because the Battle domain began an
RPG round. A Battle Scene can host both, but they do not own each other.

Scene hooks may wait for input, Message/Choice, presentation, or Scene
transition. They own focus and composition, not Battle state. They use
explicit Battle queries/commands and never replay effects to repair UI.

### 2.7 #308 source-local modifier/interceptor/reaction

Proposed contract: source behavior attaches to a concrete state, equipment,
passive, actor, or other registered source and participates only in a typed
phenomenon.

1. Calculation contribution modifies a named channel such as damage, healing,
   cost, hit chance, regeneration, state success, or reward under declared
   operation and combination rules.
2. Pending-transition interceptor examines a typed damage, healing, state,
   target, cost, resource, or death record before commit. It may only use the
   transition's declared cancel/reduce/redirect/convert/replace operations.
3. Resolved-event reaction consumes an immutable fact after commit and issues
   ordinary semantic commands/effects with parent lineage.

Magic Guard is a damage interceptor, not an after-anything observer. Thorns is
a resolved damage reaction, not a second after_action Flow. A victory heal can
be a victory reaction when source-local; reward policy remains Flow/reward
calculation.

### 2.8 Semantic command implementation

Proposed contract: a registry-visible semantic command may be implemented by
another Event Program. The caller supplies declared typed parameters/context.
The implementation inherits caller scope and lineage and returns a declared
result/events/wait. It does not publish a new lifecycle signal, subscribe
globally, or widen context to ambient engine state.

Calling SHOW_BARK implemented by an Event Program remains one SHOW_BARK
operation, not also a Common Event, Scene hook, and Flow. If it requests damage,
that effect enters the Battle pipeline once.

## 3. Deterministic precedence model

### 3.1 Domain and transaction phases

Proposed contract:

    domain phenomenon
        domain authority publishes/establishes the typed source
            domain-wide authored policy (Flow, where defined)
            encounter-scoped participants (Troop Event, where admitted)
            typed source-local participants (#308, where applicable)
        source-specific participant phase ends

    action accepted
        legality and cost calculation
        Action Sequence command
            typed calculation contributions
            typed pending interceptors
            authoritative commit once
            immutable resolved event
            matching reactions in stable source order
        Action Sequence continuation
        action finished / domain after-action phase
    presentation projects facts and may pace replay

Lifecycle source and typed transition phase are distinct. A lifecycle program
does not gain permission to mutate a pending transition merely by running near
it.

### 3.2 Source order

When several providers participate:

1. domain authority establishes the named phase/transition;
2. calculation contributors are collected in declared source precedence and
   channel-specific combination rules;
3. pending interceptors run in declared typed order, each seeing the current
   pending record and immutable original;
4. authority commits exactly once;
5. authority publishes one resolved fact with source/action/target/lineage;
6. matching reactions run in active-source order, then authored order;
7. the caller resumes;
8. other participants run only at their own named, phenomenon-specific boundary.

The exact #308 source precedence is unresolved, but it must be declared,
inspectable, stable, and independent of hash order or registration timing.

### 3.3 Damage

For one skill hit:

1. Action Sequence chooses a target/effect request.
2. Damage calculation contributors modify the typed damage channel.
3. Authority creates a pending damage record with source, original/current
   target, action/effect, kind, element, attempted/current amount, and lineage.
4. Damage interceptors such as Magic Guard, barrier, or Guts transform it.
   Ordinary Flow/Troop/Scene hooks do not mutate it.
5. Battle/effect authority commits HP once, including death/outcome invariants,
   and publishes final amount/resulting state.
6. Matching reactions run. Lifesteal reads final amount; Thorns requests a
   nested action/effect; kill reactions consume the kill fact.
7. Action Sequence resumes. In the current immediate path, a presentation
   `WAIT` does not suspend or defer steps 3窶・; it cannot undo them.
8. Current battle.after_action Flow/Troop Events run after the complete sequence.
9. Presentation shows popup/animation from resolved facts.

### 3.4 Thorns

Thorns belongs to the target's concrete source. A matching resolved damage fact
starts it. If it invokes a named retaliation Action Sequence, that nested
action enters the same legality/pending/commit/resolved/reaction pipeline with
the incoming event as parent lineage.

The guard suppresses the same source/reaction handling its own retaliation
lineage unless an authored repeat policy permits it. A cycle diagnostic must
name the chain. No arbitrary numeric recursion limit is frozen here because
the repository establishes none; #308 owns the final guard decision.

### 3.5 Magic Guard

Magic Guard is a typed pending HP-damage interceptor. It redirects some or all
pending HP damage to MP before HP commit, preserving original/current target,
attempted amount, remaining amount, and conversion lineage. Insufficient MP
uses a declared policy for the remainder; it is not inferred afterward.

Ordinary lifecycle hooks, Scene hooks, and presentation cannot mutate pending
damage. They may observe the resolved result or request a separate operation
at their own boundary. This keeps pre-commit semantics typed and immediate.

### 3.6 Boss phase at 60 percent

The encounter desire is troop scope. A troop condition at a named lifecycle
point may display text, change state, or request an action. A response that
must distinguish the exact damage/HP result should consume a resolved fact,
not poll current HP from a second Flow.

Preferred division:

* the resolved damage/HP fact is published once;
* a Troop Event owns encounter-local policy and once semantics when the
  encounter phenomenon admits that participant;
* Action Sequence owns any named boss action choreography;
* the current Flow contains the explicit troop invitation, but the proposed
  semantic ownership remains with the encounter/domain source and its declared
  participant ordering.

Do not add a global condition and a resolved reaction that both mutate the boss.

### 3.7 Multi-hit

Each APPLY_EFFECT is a separate effect request. Calculation, interceptors,
commit, resolved fact, matching reactions, and lineage complete before the
Action Sequence runs its next command.

For `APPLY_EFFECT`, `WAIT`, `APPLY_EFFECT`, the first hit resolves and reacts
before the second because `APPLY_EFFECT` is an immediate semantic boundary,
not because `WAIT` suspends the domain. In the current immediate interpreter,
`WAIT` appends a presentation wait event and returns, so the second effect
commits before presentation later consumes that event. Presentation may reveal
`hit 1`, visible wait, `hit 2` even though authoritative Battle state has
already resolved both. This supports per-hit lifesteal, counters, barriers,
Bide, death between hits, and target invalidation without coupling semantic
progress to the renderer. A whole-sequence after-damage callback would be too
late.

Current code already performs immediate per-effect mutation and event append.
This report proposes dispatching typed reactions at that same boundary; it does
not implement that dispatch.

### 3.8 Victory

Repository fact: after the current Battle outcome check, Scene transition
handling later runs `battle.victory` Flow after the battle log timing. The
current Flow performs reward/recovery mutations, while the Scene projects the
result through victory, level-up, reap, and transition presentation. This is
the current ordering, not a settled future reward transaction boundary.

Proposed contract: the settled semantic boundary is only:

1. authoritative lethal transition;
2. immutable damage/death/kill facts;
3. Battle outcome authority determines victory/defeat/continuation.

Presentation timing must not decide whether victory or rewards occur. The
exact future location of victory Flow, the reward/recovery transaction
boundary, whether reward calculation belongs to Battle outcome finalization or
a subsequent lifecycle operation, and how current Scene-triggered victory
Flow migrates remain unresolved owner decisions.

Kill reaction is not victory lifecycle, and victory lifecycle is not a second
damage reaction. Wherever reward calculation eventually lives, it must read
authoritative kill, party, troop, and source facts rather than reconstructing a
killer from the final roster.

## 4. Narrow context contracts

| Host/phase | Minimum typed context | Must not assume |
| --- | --- | --- |
| Map Event Page | session, loader, map, event, page, trigger/position, local state, lineage | active Battle or Scene internals |
| Invoked Common Event | caller context, declared args, session, loader, local procedure state, lineage | lifecycle source of its own |
| Autorun/Parallel process | process identity, owner, tick/schedule, cancellation, session, loader | unscheduled concurrent mutation |
| Troop Event | battle, troop, phase, session, loader, party/enemies, event, condition locals, fact where applicable | a hit inferred from current HP |
| Flow | named lifecycle fact, narrow domain context, session, loader, local v | every source, Scene, or pending transition |
| Action Sequence | source, action, skill/item, original/current targets, battle, session, loader, locals/refs, lineage | direct mutation or passive subscription |
| Scene hook | scene, local v, focus/input, interaction, session, loader | Battle lifecycle equivalence |
| Calculation contribution | typed channel, immutable base/current value, subject/source/target/action, provenance | arbitrary table mutation |
| Pending interceptor | typed pending record, immutable original, current candidate, lineage, provenance | suspension or post-commit repair |
| Resolved reaction | immutable event, source/provenance, action, targets, lineage, local state handle | recomputed final amount |
| Semantic implementation | declared args, caller context, result/wait contract, lineage | new source or ambient context |

Current magic/global context that should eventually become explicit includes the
interpreter's overloaded a/b/target/ally/enemy/v bindings, the global active
session used by the Battle Scene, the troop lookup asymmetry before/after Battle
construction, and globally bound presentation hooks. This report does not
migrate them.

## 5. Waiting, suspension, and reentrancy

| Wait kind | May suspend? | Rule |
| --- | --- | --- |
| Ordinary immediate command | No | Runs synchronously and returns events/result. |
| Message/Choice | Yes for an interactive host | Caller frame remains owner; input/focus belongs to interaction. |
| Presentation `WAIT` in immediate Action Sequence | No for semantic continuation | Current handler emits a wait event and returns; presentation may pace replay after the authoritative commands have continued. |
| Asynchronous Scene interaction | Yes | Scene host owns focus/resumption; no half-commit. |
| Parallel process | Between ticks | Scheduler serializes semantic requests. |
| Pending calculation/interceptor | No | Immediate, bounded, typed, non-dialogue. |
| Resolved reaction | Normally immediate | Any wait occurs after its triggering commit. |
| Future semantic scheduler yield/interrupt | Not established by `WAIT` | Requires a named scheduler/domain capability with deterministic yield, cancellation, and resume semantics. |

Common Event calls are nested procedure frames. Action Sequence to Common Event
inherits caller scope and resumes after its result/interaction. A reaction to a
named Action Sequence enters the same semantic pipeline with parent lineage.
Semantic command implementations return through the caller and do not create a
second lifecycle source.

Proposed lineage contract: every root gets origin_id; every fact gets an event
sequence and parent event id; nested operations carry source/reaction identity
and depth. Suppress repeated source/reaction handling for the same lineage
unless an authored repeat policy permits it. Reject statically visible formula
cycles and fail loudly with source, reaction, parent, and chain when a cycle or
implementation-defined safety guard is reached. No arbitrary numeric limit is
set by this report; #308 owns it.

## 6. Mutation-authority matrix

| Surface | Observe | Request semantic operation | Direct authoritative mutation | Wait | Produce lifecycle signal |
| --- | :---: | :---: | :---: | :---: | :---: |
| Map Event Page | Yes | Yes | No | Yes, admissible interaction | No |
| Invoked Common Event | Yes | Yes | No | Declared caller/host only | No |
| Autorun/Parallel process | Yes | Yes, scheduler-mediated | No outside owner | Between ticks | No |
| Troop Event | Yes | Yes | No | Lifecycle/interaction only | No |
| Flow | Yes | Yes | No outside domain commands | Immediate unless declared | It is its named signal |
| Action Sequence | Yes | Yes | No | Modal wait where admitted; immediate `WAIT` only paces presentation | No |
| Scene hook | Yes | Yes | No Battle mutation | Yes | No Battle lifecycle |
| #308 calculation | Typed input | Contribution only | No | No | No |
| #308 interceptor | Typed pending record | Transform/cancel/redirect/replace | No | No | No |
| #308 reaction | Immutable fact | Yes, nested operation | No parent repair | Normally immediate | No generic lifecycle |
| Semantic implementation | Caller context | Declared implementation | No outside called capability | Declared only | No |
| RPG Battle/effect authority | Facts/state | Accepts requests | Yes, exactly once | No half-commit wait | Yes, typed facts |
| Presentation/BattleView | Resolved facts | No gameplay request | Never | Yes, visual clock | No |

The central rule is that Event Programs request semantic operations and observe
facts, while authoritative RPG capabilities commit transitions. Presentation
may retain an earlier frame and later advance it from a resolved fact; it never
restores, replays, or infers gameplay state.

## 7. Scheduler pressure test

The contract separates Battle transaction semantics from scheduler semantics.

Current round-based Second Gate supplies round_start, queue construction,
ordered turns, after_action, and round_end. The model maps directly. Current
`WAIT` is not a scheduler yield: it cannot be used as evidence that an ATB or
interruptible scheduler has semantic suspension.

An ATB scheduler could replace round collection with time accumulation and an
action-ready queue. It would reuse legality, cost, Action Sequence, per-effect
pending/commit/resolved/reaction, action completion, and presentation projection.
Round phases would be absent or explicitly scheduler signals, not universal
assumptions.

A CTB/timeline scheduler could choose and reinsert actors. Initiative
contributions and forced actions would target scheduler-owned channels. Reaction
actions would enter through a declared enqueue/interrupt operation and retain
lineage.

An interrupting battle could suspend/resume action frames. The scheduler owns
insertion/cancellation; the Battle capability still owns effect commits. An
interrupt must not become a duplicate damage or presentation authority. If
such a scheduler needs a yield between authoritative commits, that yield must
be explicit and scheduler-owned; it must not be inferred from renderer WAIT
completion.

The pressure test passes if future schedulers provide scheduling policy and
consume the same typed transition pipeline. It fails if scheduler code
reimplements effects, reactions, or presentation replay.

## 8. Explicit invariants

1. One semantic transition has one authoritative owner and one commit.
2. The committing authority publishes immutable resolved facts.
3. Presentation never repairs, replays, or infers committed gameplay state.
4. Action Sequence continuation observes each effect commit before the next
   effect command.
5. Immediate Action Sequence `WAIT` is presentation pacing, not semantic
   suspension; a future semantic yield must be an explicit scheduler/domain
   capability.
6. Reactions consume resolved facts, not reconstructed formulas.
7. Pending interceptors are typed, immediate, and non-suspending.
8. Ordinary lifecycle hooks cannot mutate pending typed transitions.
9. Flow is a named lifecycle mapping, not a universal callback API.
10. Troop Events are encounter-local participants; the current Flow invitation
    is an implementation path, not their semantic owner.
11. Scene hooks are Scene-instance programs, not Battle lifecycle.
12. Common Events are reusable procedures/processes, not new sources.
13. Semantic implementations inherit caller context and lineage.
14. Source order is declared and stable; hash order never decides gameplay.
15. Original/current target, provenance, action identity, and lineage survive
    nested operations.
16. Reaction-generated operations enter the same pipeline and are diagnosable.
17. RPG Battle remains a first-class semantic capability; its internal module
    decomposition remains open.
18. Scene transitions, modal interactions, and Event execution remain distinct.
19. Missing required Flow is a loud validation/runtime failure.

## 9. Accidental behavior that should not become contract

* after_action currently follows the entire sequence, not every effect.
* victory/reward Flow currently begins from Scene transition handling after log
  timing, so it must not depend on how long the player reads.
* current Flow command lists call `RUN_TROOP_EVENTS`; this dispatch path does not
  make Flow the semantic owner of Troop scope or of other host types.
* immediate Action Sequence `WAIT` currently appends a presentation event and
  execution continues; renderer pacing is not a semantic scheduler yield.
* CALL_COMMON_EVENT currently uses a dialogue graph and is unavailable in
  immediate mode; the admissibility distinction matters more than the path.
* engine/scenes/battle.lua directly requires presentation; #260 tracks this.
* setup Flow lacks Battle before Battle.new.
* fixed barriers, execution, and KILL_MP_RESTORE are not a generic reaction API.
* base-first troop inheritance is current order, not future package composition.
* current immediate recursion does not establish lineage/cycle guarantees.
* Scene-local _guard variables are not a general reaction-lineage mechanism.

## 10. Unresolved owner decisions

1. Final #308 source precedence across innate/passive, equipment, state,
   package, and authored order.
2. Pending/resolved record schema for damage, healing, state, resource, cost,
   target, and death, including original/current amount semantics.
3. Concrete lineage representation and final loud diagnostic/safety guard.
4. Which current after_action threshold patterns become resolved reactions,
   without dual observation during migration.
5. Whether future packages may contribute multiple Flow providers and how they
   compose.
6. Common Event wait/result contract for each host.
7. Minimal scheduler bridge for ATB/CTB/interrupt systems.
8. Exact victory/reward/recovery transaction boundary: whether reward
   calculation belongs to Battle outcome finalization or a subsequent
   lifecycle operation, and how current Scene-initiated victory Flow migrates;
   presentation timing must remain irrelevant.
9. #260's Battle Scene/presentation seam, without timing or golden changes.
10. Separate Dialogue modal migration design.

## 11. Smallest recommended follow-up implementation issues

1. #308 typed transition fixture: one damage pending record, resolved fact, and
   source reaction without migrating traits.
2. #308 deterministic lineage fixture: terminating Thorns chain and diagnosed
   counter-cycle with explicit source order.
3. #308 multi-hit fixture: prove per-effect commit/reaction before continuation.
4. #308 Magic Guard fixture: define insufficient-MP redirect and forbid
   lifecycle mutation of pending damage.
5. Troop threshold ownership design: migrate one boss-phase case to one
   resolved-fact observer, without a broad troop schema rewrite.
6. Semantic command result/wait fixture: one data-defined implementation with
   immediate and interactive admissibility tests.
7. Battle outcome authority audit: isolate reward/recovery from log timing.
8. #260 dependency seam: owner-supervised Battle Scene presentation boundary.

The first three are the safest next work because they test the contract without
changing authored production behavior. Do not begin a broad host migration,
Flow rename, Dialogue migration, or scheduler implementation until contexts and
lineage fixtures converge.

## Conclusion

When an RPG phenomenon occurs in Thestra, identify its lifecycle or transition
source first. The domain authority publishes/establishes that phenomenon;
domain-wide authored policy may be a Flow, an encounter may admit Troop Event
participation, and typed #308 reactions participate only at their typed
transition boundary. Scene lifecycle/input remains distinct. An action runs
its Action Sequence; a typed transition is calculated and intercepted by the
semantic capability that owns it; that capability commits once and publishes a
resolved fact; source-local reactions consume that fact and enter the same
pipeline; presentation projects the result on its own clock. Current Flow may
still contain `RUN_TROOP_EVENTS`, but that is current orchestration rather than
the universal ownership model.

This preserves composable authoring without duplicate hook systems, keeps RPG
Battle semantics authoritative and first-class, and leaves scheduling, AI,
encounter policy, Scene composition, and presentation free to evolve behind
explicit contracts.
