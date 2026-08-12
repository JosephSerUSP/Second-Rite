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
            -> presentation projection/wait

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

ThÛ®|¶‰žËkºwµçU½¹•™™•Ð)½µµ¥ÑÌ‰•™½É”ÁÉ•Í•¹Ñ…Ñ¥½¸±…Ñ•È½¹ÍÕµ•ÌÑ¡…Ð•Ù•¹Ð¸AÉ•Í•¹Ñ…Ñ¥½¸µ…äÉ•Ù•…°)¡¥Ð€Å€°Ù¥Í¥‰±”Ý…¥Ð°¡¥Ð€É€•Ù•¸Ñ¡½Õ …ÕÑ¡½É¥Ñ…Ñ¥Ù”	…ÑÑ±”ÍÑ…Ñ”¡…Ì)…±É•…‘äÉ•Í½±Ù•‰½Ñ ¸Q¡¥ÌÍÕÁÁ½ÉÑÌÁ•Èµ¡¥Ð±¥™•ÍÑ•…°°½Õ¹Ñ•ÉÌ°‰…ÉÉ¥•ÉÌ°)	¥‘”°‘•…Ñ ‰•ÑÝ••¸¡¥ÑÌ°…¹Ñ…É•Ð¥¹Ù…±¥‘…Ñ¥½¸Ý¥Ñ¡½ÕÐ½ÕÁ±¥¹œÍ•µ…¹Ñ¥Œ)ÁÉ½É•ÍÌÑ¼Ñ¡”É•¹‘•É•È¸Ý¡½±”µÍ•ÅÕ•¹”…™Ñ•Èµ‘…µ…”…±±‰…¬Ý½Õ±‰”Ñ½¼)±…Ñ”¸()ÕÉÉ•¹Ð½‘”…±É•…‘äÁ•É™½ÉµÌ¥µµ•‘¥…Ñ”Á•Èµ•™™•ÐµÕÑ…Ñ¥½¸…¹•Ù•¹Ð…ÁÁ•¹¸)Q¡¥ÌÉ•Á½ÉÐÁÉ½Á½Í•Ì‘¥ÍÁ…Ñ¡¥¹œÑåÁ•É•…Ñ¥½¹Ì…ÐÑ¡…ÐÍ…µ”‰½Õ¹‘…Éäì¥Ð‘½•Ì)¹½Ð¥µÁ±•µ•¹ÐÑ¡…Ð‘¥ÍÁ…Ñ ¸((ŒŒŒ€Ì¸àY¥Ñ½Éä()I•Á½Í¥Ñ½Éä™…Ðè…™Ñ•ÈÑ¡”ÕÉÉ•¹Ð	…ÑÑ±”½ÕÑ½µ”¡•¬°M•¹”ÑÉ…¹Í¥Ñ¥½¸)¡…¹‘±¥¹œ±…Ñ•ÈÉÕ¹Ì‰…ÑÑ±”¹Ù¥Ñ½Éå€±½Ü…™Ñ•ÈÑ¡”‰…ÑÑ±”±½œÑ¥µ¥¹œ¸Q¡”)ÕÉÉ•¹Ð±½ÜÁ•É™½ÉµÌÉ•Ý…É½É•½Ù•ÉäµÕÑ…Ñ¥½¹Ì°Ý¡¥±”Ñ¡”M•¹”ÁÉ½©•ÑÌÑ¡”)É•ÍÕ±ÐÑ¡É½Õ Ù¥Ñ½Éä°±•Ù•°µÕÀ°É•…À°…¹ÑÉ…¹Í¥Ñ¥½¸ÁÉ•Í•¹Ñ…Ñ¥½¸¸Q¡¥Ì¥Ì)Ñ¡”ÕÉÉ•¹Ð½É‘•É¥¹œ°¹½Ð„Í•ÑÑ±•™ÕÑÕÉ”É•Ý…ÉÑÉ…¹Í…Ñ¥½¸‰½Õ¹‘…Éä¸()AÉ½Á½Í•½¹ÑÉ…ÐèÑ¡”Í•ÑÑ±•Í•µ…¹Ñ¥Œ‰½Õ¹‘…Éä¥Ì½¹±äè((Ä¸…ÕÑ¡½É¥Ñ…Ñ¥Ù”±•Ñ¡…°ÑÉ…¹Í¥Ñ¥½¸ì(È¸¥µµÕÑ…‰±”‘…µ…”½‘•…Ñ ½­¥±°™…ÑÌì(Ì¸	…ÑÑ±”½ÕÑ½µ”…ÕÑ¡½É¥Ñä‘•Ñ•Éµ¥¹•ÌÙ¥Ñ½Éä½‘•™•…Ð½½¹Ñ¥¹Õ…Ñ¥½¸¸()AÉ•Í•¹Ñ…Ñ¥½¸Ñ¥µ¥¹œµÕÍÐ¹½Ð‘•¥‘”Ý¡•Ñ¡•ÈÙ¥Ñ½Éä½ÈÉ•Ý…É‘Ì½ÕÈ¸Q¡”)•á…Ð™ÕÑÕÉ”±½…Ñ¥½¸½˜Ù¥Ñ½Éä±½Ü°Ñ¡”É•Ý…É½É•½Ù•ÉäÑÉ…¹Í…Ñ¥½¸)‰½Õ¹‘…Éä°Ý¡•Ñ¡•ÈÉ•Ý…É…±Õ±…Ñ¥½¸‰•±½¹ÌÑ¼	…ÑÑ±”½ÕÑ½µ”™¥¹…±¥é…Ñ¥½¸½È)„ÍÕ‰Í•ÅÕ•¹Ð±¥™•å±”½Á•É…Ñ¥½¸°…¹¡½ÜÕÉÉ•¹ÐM•¹”µÑÉ¥•É•Ù¥Ñ½Éä)±½Üµ¥É…Ñ•ÌÉ•µ…¥¸Õ¹É•Í½±Ù•½Ý¹•È‘•¥Í¥½¹Ì¸()-¥±°É•…Ñ¥½¸¥Ì¹½ÐÙ¥Ñ½Éä±¥™•å±”°…¹Ù¥Ñ½Éä±¥™•å±”¥Ì¹½Ð„Í•½¹)‘…µ…”É•…Ñ¥½¸¸]¡•É•Ù•ÈÉ•Ý…É…±Õ±…Ñ¥½¸•Ù•¹ÑÕ…±±ä±¥Ù•Ì°¥ÐµÕÍÐÉ•…)…ÕÑ¡½É¥Ñ…Ñ¥Ù”­¥±°°Á…ÉÑä°ÑÉ½½À°…¹Í½ÕÉ”™…ÑÌÉ…Ñ¡•ÈÑ¡…¸É•½¹ÍÑÉÕÑ¥¹œ„)­¥±±•È™É½´Ñ¡”™¥¹…°É½ÍÑ•È¸((ŒŒ€Ð¸9…ÉÉ½Ü½¹Ñ•áÐ½¹ÑÉ…ÑÌ()ð!½ÍÐ½Á¡…Í”ð5¥¹¥µÕ´ÑåÁ•½¹Ñ•áÐð5ÕÍÐ¹½Ð…ÍÍÕµ”ð)ð€´´´ð€´´´ð€´´´ð)ð5…ÀÙ•¹ÐA…”ðÍ•ÍÍ¥½¸°±½…‘•È°µ…À°•Ù•¹Ð°Á…”°ÑÉ¥•È½Á½Í¥Ñ¥½¸°±½…°ÍÑ…Ñ”°±¥¹•…”ð…Ñ¥Ù”	…ÑÑ±”½ÈM•¹”¥¹Ñ•É¹…±Ìð)ð%¹Ù½­•½µµ½¸Ù•¹Ðð…±±•È½¹Ñ•áÐ°‘•±…É•…ÉÌ°Í•ÍÍ¥½¸°±½…‘•È°±½…°ÁÉ½•‘ÕÉ”ÍÑ…Ñ”°±¥¹•…”ð±¥™•å±”Í½ÕÉ”½˜¥ÑÌ½Ý¸ð)ðÕÑ½ÉÕ¸½A…É…±±•°ÁÉ½•ÍÌðÁÉ½•ÍÌ¥‘•¹Ñ¥Ñä°½Ý¹•È°Ñ¥¬½Í¡•‘Õ±”°…¹•±±…Ñ¥½¸°Í•ÍÍ¥½¸°±½…‘•ÈðÕ¹Í¡•‘Õ±•½¹ÕÉÉ•¹ÐµÕÑ…Ñ¥½¸ð)ðQÉ½½ÀÙ•¹Ðð‰…ÑÑ±”°ÑÉ½½À°Á¡…Í”°Í•ÍÍ¥½¸°±½…‘•È°Á…ÉÑä½•¹•µ¥•Ì°•Ù•¹Ð°½¹‘¥Ñ¥½¸±½…±Ì°™…ÐÝ¡•É”…ÁÁ±¥…‰±”ð„¡¥Ð¥¹™•ÉÉ•™É½´ÕÉÉ•¹Ð!@ð)ð±½Üð¹…µ•±¥™•å±”™…Ð°¹…ÉÉ½Ü‘½µ…¥¸½¹Ñ•áÐ°Í•ÍÍ¥½¸°±½…‘•È°±½…°Øð•Ù•ÉäÍ½ÕÉ”°M•¹”°½ÈÁ•¹‘¥¹œÑÉ…¹Í¥Ñ¥½¸ð)ðÑ¥½¸M•ÅÕ•¹”ðÍ½ÕÉ”°…Ñ¥½¸°Í­¥±°½¥Ñ•´°½É¥¥¹…°½ÕÉÉ•¹ÐÑ…É•ÑÌ°‰…ÑÑ±”°Í•ÍÍ¥½¸°±½…‘•È°±½…±Ì½É•™Ì°±¥¹•…”ð‘¥É•ÐµÕÑ…Ñ¥½¸½ÈÁ…ÍÍ¥Ù”ÍÕ‰ÍÉ¥ÁÑ¥½¸ð)ðM•¹”¡½½¬ðÍ•¹”°±½…°Ø°™½ÕÌ½¥¹ÁÕÐ°¥¹Ñ•É…Ñ¥½¸°Í•ÍÍ¥½¸°±½…‘•Èð	…ÑÑ±”±¥™•å±”•ÅÕ¥Ù…±•¹”ð)ð…±Õ±…Ñ¥½¸½¹ÑÉ¥‰ÕÑ¥½¸ðÑåÁ•¡…¹¹•°°¥µµÕÑ…‰±”‰…Í”½ÕÉÉ•¹ÐÙ…±Õ”°ÍÕ‰©•Ð½Í½ÕÉ”½Ñ…É•Ð½…Ñ¥½¸°ÁÉ½Ù•¹…¹”ð…É‰¥ÑÉ…ÉäÑ…‰±”µÕÑ…Ñ¥½¸ð)ðA•¹‘¥¹œ¥¹Ñ•É•ÁÑ½ÈðÑåÁ•Á•¹‘¥¹œÉ•½É°¥µµÕÑ…‰±”½É¥¥¹…°°ÕÉÉ•¹Ð…¹‘¥‘…Ñ”°±¥¹•…”°ÁÉ½Ù•¹…¹”ðÍÕÍÁ•¹Í¥½¸½ÈÁ½ÍÐµ½µµ¥ÐÉ•Á…¥Èð)ðI•Í½±Ù•É•…Ñ¥½¸ð¥µµÕÑ…‰±”•Ù•¹Ð°Í½ÕÉ”½ÁÉ½Ù•¹…¹”°…Ñ¥½¸°Ñ…É•ÑÌ°±¥¹•…”°±½…°ÍÑ…Ñ”¡…¹‘±”ðÉ•½µÁÕÑ•™¥¹…°…µ½Õ¹Ðð)ðM•µ…¹Ñ¥Œ¥µÁ±•µ•¹Ñ…Ñ¥½¸ð‘•±…É•…ÉÌ°…±±•È½¹Ñ•áÐ°É•ÍÕ±Ð½Ý…¥Ð½¹ÑÉ…Ð°±¥¹•…”ð¹•ÜÍ½ÕÉ”½È…µ‰¥•¹Ð½¹Ñ•áÐð()ÕÉÉ•¹Ðµ…¥Œ½±½‰…°½¹Ñ•áÐÑ¡…ÐÍ¡½Õ±•Ù•¹ÑÕ…±±ä‰•½µ”•áÁ±¥¥Ð¥¹±Õ‘•ÌÑ¡”)¥¹Ñ•ÉÁÉ•Ñ•ÈÌ½Ù•É±½…‘•„½ˆ½Ñ…É•Ð½…±±ä½•¹•µä½Ø‰¥¹‘¥¹Ì°Ñ¡”±½‰…°…Ñ¥Ù”)Í•ÍÍ¥½¸ÕÍ•‰äÑ¡”	…ÑÑ±”M•¹”°Ñ¡”ÑÉ½½À±½½­ÕÀ…Íåµµ•ÑÉä‰•™½É”½…™Ñ•È	…ÑÑ±”)½¹ÍÑÉÕÑ¥½¸°…¹±½‰…±±ä‰½Õ¹ÁÉ•Í•¹Ñ…Ñ¥½¸¡½½­Ì¸Q¡¥ÌÉ•Á½ÉÐ‘½•Ì¹½Ð)µ¥É…Ñ”Ñ¡•´¸((ŒŒ€Ô¸]…¥Ñ¥¹œ°ÍÕÍÁ•¹Í¥½¸°…¹É••¹ÑÉ…¹ä()ð]…¥Ð­¥¹ð5…äÍÕÍÁ•¹üðIÕ±”ð)ð€´´´ð€´´´ð€´´´ð)ð=É‘¥¹…Éä¥µµ•‘¥…Ñ”½µµ…¹ð9¼ðIÕ¹ÌÍå¹¡É½¹½ÕÍ±ä…¹É•ÑÕÉ¹Ì•Ù•¹ÑÌ½É•ÍÕ±Ð¸ð)ð5•ÍÍ…”½¡½¥”ðe•Ì™½È…¸¥¹Ñ•É…Ñ¥Ù”¡½ÍÐð…±±•È™É…µ”É•µ…¥¹Ì½Ý¹•Èì¥¹ÁÕÐ½™½ÕÌ‰•±½¹ÌÑ¼¥¹Ñ•É…Ñ¥½¸¸ð)ðAÉ•Í•¹Ñ…Ñ¥½¸]%Q€¥¸¥µµ•‘¥…Ñ”Ñ¥½¸M•ÅÕ•¹”ð9¼™½ÈÍ•µ…¹Ñ¥Œ½¹Ñ¥¹Õ…Ñ¥½¸ðÕÉÉ•¹Ð¡…¹‘±•È•µ¥ÑÌ„Ý…¥Ð•Ù•¹Ð…¹É•ÑÕÉ¹ÌìÁÉ•Í•¹Ñ…Ñ¥½¸µ…äÁ…”É•Á±…ä…™Ñ•ÈÑ¡”…ÕÑ¡½É¥Ñ…Ñ¥Ù”½µµ…¹‘Ì¡…Ù”½¹Ñ¥¹Õ•¸ð)ðÍå¹¡É½¹½ÕÌM•¹”¥¹Ñ•É…Ñ¥½¸ðe•ÌðM•¹”¡½ÍÐ½Ý¹Ì™½ÕÌ½É•ÍÕµÁÑ¥½¸ì¹¼¡…±˜µ½µµ¥Ð¸ð)ðA…É…±±•°ÁÉ½•ÍÌð	•ÑÝ••¸Ñ¥­ÌðM¡•‘Õ±•ÈÍ•É¥…±¥é•ÌÍ•µ…¹Ñ¥ŒÉ•ÅÕ•ÍÑÌ¸ð)ðA•¹‘¥¹œ…±Õ±…Ñ¥½¸½¥¹Ñ•É•ÁÑ½Èð9¼ð%µµ•‘¥…Ñ”°‰½Õ¹‘•°ÑåÁ•°¹½¸µ‘¥…±½Õ”¸ð)ðI•Í½±Ù•É•…Ñ¥½¸ð9½Éµ…±±ä¥µµ•‘¥…Ñ”ð¹äÝ…¥Ð½ÕÉÌ…™Ñ•È¥ÑÌÑÉ¥•É¥¹œ½µµ¥Ð¸ð)ðÕÑÕÉ”Í•µ…¹Ñ¥ŒÍ¡•‘Õ±•Èå¥•±½¥¹Ñ•ÉÉÕÁÐð9½Ð•ÍÑ…‰±¥Í¡•‰ä]%Q€ðI•ÅÕ¥É•Ì„¹…µ•Í¡•‘Õ±•È½‘½µ…¥¸…Á…‰¥±¥ÑäÝ¥Ñ ‘•Ñ•Éµ¥¹¥ÍÑ¥Œå¥•±°…¹•±±…Ñ¥½¸°…¹É•ÍÕµ”Í•µ…¹Ñ¥Ì¸ð()½µµ½¸Ù•¹Ð…±±Ì…É”¹•ÍÑ•ÁÉ½•‘ÕÉ”™É…µ•Ì¸Ñ¥½¸M•ÅÕ•¹”Ñ¼½µµ½¸Ù•¹Ð)¥¹¡•É¥ÑÌ…±±•ÈÍ½Á”…¹É•ÍÕµ•Ì…™Ñ•È¥ÑÌÉ•ÍÕ±Ð½¥¹Ñ•É…Ñ¥½¸¸É•…Ñ¥½¸Ñ¼„)¹…µ•Ñ¥½¸M•ÅÕ•¹”•¹Ñ•ÉÌÑ¡”Í…µ”Í•µ…¹Ñ¥ŒÁ¥Á•±¥¹”Ý¥Ñ Á…É•¹Ð±¥¹•…”¸)M•µ…¹Ñ¥Œ½µµ…¹¥µÁ±•µ•¹Ñ…Ñ¥½¹ÌÉ•ÑÕÉ¸Ñ¡É½Õ Ñ¡”…±±•È…¹‘¼¹½ÐÉ•…Ñ”„)Í•½¹±¥™•å±”Í½ÕÉ”¸()AÉ½Á½Í•±¥¹•…”½¹ÑÉ…Ðè•Ù•ÉäÉ½½Ð•ÑÌ½É¥¥¹}¥ì•Ù•Éä™…Ð•ÑÌ…¸•Ù•¹Ð)Í•ÅÕ•¹”…¹Á…É•¹Ð•Ù•¹Ð¥ì¹•ÍÑ•½Á•É…Ñ¥½¹Ì…ÉÉäÍ½ÕÉ”½É•…Ñ¥½¸¥‘•¹Ñ¥Ñä)…¹‘•ÁÑ ¸MÕÁÁÉ•ÍÌÉ•Á•…Ñ•Í½ÕÉ”½É•…Ñ¥½¸¡…¹‘±¥¹œ™½ÈÑ¡”Í…µ”±¥¹•…”)Õ¹±•ÍÌ…¸…ÕÑ¡½É•É•Á•…ÐÁ½±¥äÁ•Éµ¥ÑÌ¥Ð¸I•©•ÐÍÑ…Ñ¥…±±äÙ¥Í¥‰±”™½ÉµÕ±„)å±•Ì…¹™…¥°±½Õ‘±äÝ¥Ñ Í½ÕÉ”°É•…Ñ¥½¸°Á…É•¹Ð°…¹¡…¥¸Ý¡•¸„å±”½È)¥µÁ±•µ•¹Ñ…Ñ¥½¸µ‘•™¥¹•Í…™•ÑäÕ…É¥ÌÉ•…¡•¸9¼…É‰¥ÑÉ…Éä¹Õµ•É¥Œ±¥µ¥Ð¥Ì)Í•Ð‰äÑ¡¥ÌÉ•Á½ÉÐì€ŒÌÀà½Ý¹Ì¥Ð¸((ŒŒ€Ø¸5ÕÑ…Ñ¥½¸µ…ÕÑ¡½É¥Ñäµ…ÑÉ¥à()ðMÕÉ™…”ð=‰Í•ÉÙ”ðI•ÅÕ•ÍÐÍ•µ…¹Ñ¥Œ½Á•É…Ñ¥½¸ð¥É•Ð…ÕÑ¡½É¥Ñ…Ñ¥Ù”µÕÑ…Ñ¥½¸ð]…¥ÐðAÉ½‘Õ”±¥™•å±”Í¥¹…°ð)ð€´´´ð€è´´´èð€è´´´èð€è´´´èð€è´´´èð€è´´´èð)ð5…ÀÙ•¹ÐA…”ðe•Ìðe•Ìð9¼ðe•Ì°…‘µ¥ÍÍ¥‰±”¥¹Ñ•É…Ñ¥½¸ð9¼ð)ð%¹Ù½­•½µµ½¸Ù•¹Ððe•Ìðe•Ìð9¼ð•±…É•…±±•È½¡½ÍÐ½¹±äð9¼ð)ðÕÑ½ÉÕ¸½A…É…±±•°ÁÉ½•ÍÌðe•Ìðe•Ì°Í¡•‘Õ±•Èµµ•‘¥…Ñ•ð9¼½ÕÑÍ¥‘”½Ý¹•Èð	•ÑÝ••¸Ñ¥­Ìð9¼ð)ðQÉ½½ÀÙ•¹Ððe•Ìðe•Ìð9¼ð1¥™•å±”½¥¹Ñ•É…Ñ¥½¸½¹±äð9¼ð)ð±½Üðe•Ìðe•Ìð9¼½ÕÑÍ¥‘”‘½µ…¥¸½µµ…¹‘Ìð%µµ•‘¥…Ñ”Õ¹±•ÍÌ‘•±…É•ð%Ð¥Ì¥ÑÌ¹…µ•Í¥¹…°ð)ðÑ¥½¸M•ÅÕ•¹”ðe•Ìðe•Ìð9¼ð5½‘…°Ý…¥ÐÝ¡•É”…‘µ¥ÑÑ•ì¥µµ•‘¥…Ñ”]%Q€½¹±äÁ…•ÌÁÉ•Í•¹Ñ…Ñ¥½¸ð9¼ð)ðM•¹”¡½½¬ðe•Ìðe•Ìð9¼	…ÑÑ±”µÕÑ…Ñ¥½¸ðe•Ìð9¼	…ÑÑ±”±¥™•å±”ð)ð€ŒÌÀà…±Õ±…Ñ¥½¸ðQåÁ•¥¹ÁÕÐð½¹ÑÉ¥‰ÕÑ¥½¸½¹±äð9¼ð9¼ð9¼ð)ð€ŒÌÀà¥¹Ñ•É•ÁÑ½ÈðQåÁ•Á•¹‘¥¹œÉ•½ÉðQÉ…¹Í™½É´½…¹•°½É•‘¥É•Ð½É•Á±…”ð9¼ð9¼ð9¼ð)ð€ŒÌÀàÉ•…Ñ¥½¸ð%µµÕÑ…‰±”™…Ððe•Ì°¹•ÍÑ•½Á•É…Ñ¥½¸ð9¼Á…É•¹ÐÉ•Á…¥Èð9½Éµ…±±ä¥µµ•‘¥…Ñ”ð9¼•¹•É¥Œ±¥™•å±”ð)ðM•µ…¹Ñ¥Œ¥µÁ±•µ•¹Ñ…Ñ¥½¸ð…±±•È½¹Ñ•áÐð•±…É•¥µÁ±•µ•¹Ñ…Ñ¥½¸ð9¼½ÕÑÍ¥‘”…±±•…Á…‰¥±¥Ñäð•±…É•½¹±äð9¼ð)ðIA	…ÑÑ±”½•™™•Ð…ÕÑ¡½É¥Ñäð…ÑÌ½ÍÑ…Ñ”ð•ÁÑÌÉ•ÅÕ•ÍÑÌðe•Ì°•á…Ñ±ä½¹”ð9¼¡…±˜µ½µµ¥ÐÝ…¥Ððe•Ì°ÑåÁ•™…ÑÌð)ðAÉ•Í•¹Ñ…Ñ¥½¸½	…ÑÑ±•Y¥•ÜðI•Í½±Ù•™…ÑÌð9¼…µ•Á±…äÉ•ÅÕ•ÍÐð9•Ù•Èðe•Ì°Ù¥ÍÕ…°±½¬ð9¼ð()Q¡”•¹ÑÉ…°ÉÕ±”¥ÌÑ¡…ÐÙ•¹ÐAÉ½É…µÌÉ•ÅÕ•ÍÐÍ•µ…¹Ñ¥Œ½Á•É…Ñ¥½¹Ì…¹½‰Í•ÉÙ”)™…ÑÌ°Ý¡¥±”…ÕÑ¡½É¥Ñ…Ñ¥Ù”IA…Á…‰¥±¥Ñ¥•Ì½µµ¥ÐÑÉ…¹Í¥Ñ¥½¹Ì¸AÉ•Í•¹Ñ…Ñ¥½¸)µ…äÉ•Ñ…¥¸…¸•…É±¥•È™É…µ”…¹±…Ñ•È…‘Ù…¹”¥Ð™É½´„É•Í½±Ù•™…Ðì¥Ð¹•Ù•È)É•ÍÑ½É•Ì°É•Á±…åÌ°½È¥¹™•ÉÌ…µ•Á±…äÍÑ…Ñ”¸((ŒŒ€Ü¸M¡•‘Õ±•ÈÁÉ•ÍÍÕÉ”Ñ•ÍÐ()Q¡”½¹ÑÉ…ÐÍ•Á…É…Ñ•Ì	…ÑÑ±”ÑÉ…¹Í…Ñ¥½¸Í•µ…¹Ñ¥Ì™É½´Í¡•‘Õ±•ÈÍ•µ…¹Ñ¥Ì¸()ÕÉÉ•¹ÐÉ½Õ¹µ‰…Í•M•½¹…Ñ”ÍÕÁÁ±¥•ÌÉ½Õ¹‘}ÍÑ…ÉÐ°ÅÕ•Õ”½¹ÍÑÉÕÑ¥½¸°)½É‘•É•ÑÕÉ¹Ì°…™Ñ•É}…Ñ¥½¸°…¹É½Õ¹‘}•¹¸Q¡”µ½‘•°µ…ÁÌ‘¥É•Ñ±ä¸ÕÉÉ•¹Ð)]%Q€¥Ì¹½Ð„Í¡•‘Õ±•Èå¥•±è¥Ð…¹¹½Ð‰”ÕÍ•…Ì•Ù¥‘•¹”Ñ¡…Ð…¸Q½È)¥¹Ñ•ÉÉÕÁÑ¥‰±”Í¡•‘Õ±•È¡…ÌÍ•µ…¹Ñ¥ŒÍÕÍÁ•¹Í¥½¸¸()¸QÍ¡•‘Õ±•È½Õ±É•Á±…”É½Õ¹½±±•Ñ¥½¸Ý¥Ñ Ñ¥µ”…ÕµÕ±…Ñ¥½¸…¹…¸)…Ñ¥½¸µÉ•…‘äÅÕ•Õ”¸%ÐÝ½Õ±É•ÕÍ”±•…±¥Ñä°½ÍÐ°Ñ¥½¸M•ÅÕ•¹”°Á•Èµ•™™•Ð)Á•¹‘¥¹œ½½µµ¥Ð½É•Í½±Ù•½É•…Ñ¥½¸°…Ñ¥½¸½µÁ±•Ñ¥½¸°…¹ÁÉ•Í•¹Ñ…Ñ¥½¸ÁÉ½©•Ñ¥½¸¸)I½Õ¹Á¡…Í•ÌÝ½Õ±‰”…‰Í•¹Ð½È•áÁ±¥¥Ñ±äÍ¡•‘Õ±•ÈÍ¥¹…±Ì°¹½ÐÕ¹¥Ù•ÉÍ…°)…ÍÍÕµÁÑ¥½¹Ì¸()Q½Ñ¥µ•±¥¹”Í¡•‘Õ±•È½Õ±¡½½Í”…¹É•¥¹Í•ÉÐ…Ñ½ÉÌ¸%¹¥Ñ¥…Ñ¥Ù”)½¹ÑÉ¥‰ÕÑ¥½¹Ì…¹™½É•…Ñ¥½¹ÌÝ½Õ±Ñ…É•ÐÍ¡•‘Õ±•Èµ½Ý¹•¡…¹¹•±Ì¸I•…Ñ¥½¸)…Ñ¥½¹ÌÝ½Õ±•¹Ñ•ÈÑ¡É½Õ „‘•±…É••¹ÅÕ•Õ”½¥¹Ñ•ÉÉÕÁÐ½Á•É…Ñ¥½¸…¹É•Ñ…¥¸)±¥¹•…”¸()¸¥¹Ñ•ÉÉÕÁÑ¥¹œ‰…ÑÑ±”½Õ±ÍÕÍÁ•¹½É•ÍÕµ”…Ñ¥½¸™É…µ•Ì¸Q¡”Í¡•‘Õ±•È½Ý¹Ì)¥¹Í•ÉÑ¥½¸½…¹•±±…Ñ¥½¸ìÑ¡”	…ÑÑ±”…Á…‰¥±¥ÑäÍÑ¥±°½Ý¹Ì•™™•Ð½µµ¥ÑÌ¸¸)¥¹Ñ•ÉÉÕÁÐµÕÍÐ¹½Ð‰•½µ”„‘ÕÁ±¥…Ñ”‘…µ…”½ÈÁÉ•Í•¹Ñ…Ñ¥½¸…ÕÑ¡½É¥Ñä¸%˜)ÍÕ „Í¡•‘Õ±•È¹••‘Ì„å¥•±‰•ÑÝ••¸…ÕÑ¡½É¥Ñ…Ñ¥Ù”½µµ¥ÑÌ°Ñ¡…Ðå¥•±µÕÍÐ)‰”•áÁ±¥¥Ð…¹Í¡•‘Õ±•Èµ½Ý¹•ì¥ÐµÕÍÐ¹½Ð‰”¥¹™•ÉÉ•™É½´É•¹‘•É•È]%P)½µÁ±•Ñ¥½¸¸()Q¡”ÁÉ•ÍÍÕÉ”Ñ•ÍÐÁ…ÍÍ•Ì¥˜™ÕÑÕÉ”Í¡•‘Õ±•ÉÌÁÉ½Ù¥‘”Í¡•‘Õ±¥¹œÁ½±¥ä…¹)½¹ÍÕµ”Ñ¡”Í…µ”ÑåÁ•ÑÉ…¹Í¥Ñ¥½¸Á¥Á•±¥¹”¸%Ð™…¥±Ì¥˜Í¡•‘Õ±•È½‘”)É•¥µÁ±•µ•¹ÑÌ•™™•ÑÌ°É•…Ñ¥½¹Ì°½ÈÁÉ•Í•¹Ñ…Ñ¥½¸É•Á±…ä¸((ŒŒ€à¸áÁ±¥¥Ð¥¹Ù…É¥…¹ÑÌ((Ä¸=¹”Í•µ…¹Ñ¥ŒÑÉ…¹Í¥Ñ¥½¸¡…Ì½¹”…ÕÑ¡½É¥Ñ…Ñ¥Ù”½Ý¹•È…¹½¹”½µµ¥Ð¸(È¸Q¡”½µµ¥ÑÑ¥¹œ…ÕÑ¡½É¥ÑäÁÕ‰±¥Í¡•Ì¥µµÕÑ…‰±”É•Í½±Ù•™…ÑÌ¸(Ì¸AÉ•Í•¹Ñ…Ñ¥½¸¹•Ù•ÈÉ•Á…¥ÉÌ°É•Á±…åÌ°½È¥¹™•ÉÌ½µµ¥ÑÑ•…µ•Á±…äÍÑ…Ñ”¸(Ð¸Ñ¥½¸M•ÅÕ•¹”½¹Ñ¥¹Õ…Ñ¥½¸½‰Í•ÉÙ•Ì•… •™™•Ð½µµ¥Ð‰•™½É”Ñ¡”¹•áÐ(€€•™™•Ð½µµ…¹¸(Ô¸%µµ•‘¥…Ñ”Ñ¥½¸M•ÅÕ•¹”]%Q€¥ÌÁÉ•Í•¹Ñ…Ñ¥½¸Á…¥¹œ°¹½ÐÍ•µ…¹Ñ¥Œ(€€ÍÕÍÁ•¹Í¥½¸ì„™ÕÑÕÉ”Í•µ…¹Ñ¥Œå¥•±µÕÍÐ‰”…¸•áÁ±¥¥ÐÍ¡•‘Õ±•È½‘½µ…¥¸(€€…Á…‰¥±¥Ñä¸(Ø¸I•…Ñ¥½¹Ì½¹ÍÕµ”É•Í½±Ù•™…ÑÌ°¹½ÐÉ•½¹ÍÑÉÕÑ•™½ÉµÕ±…Ì¸(Ü¸A•¹‘¥¹œ¥¹Ñ•É•ÁÑ½ÉÌ…É”ÑåÁ•°¥µµ•‘¥…Ñ”°…¹¹½¸µÍÕÍÁ•¹‘¥¹œ¸(à¸=É‘¥¹…Éä±¥™•å±”¡½½­Ì…¹¹½ÐµÕÑ…Ñ”Á•¹‘¥¹œÑåÁ•ÑÉ…¹Í¥Ñ¥½¹Ì¸(ä¸±½Ü¥Ì„¹…µ•±¥™•å±”µ…ÁÁ¥¹œ°¹½Ð„Õ¹¥Ù•ÉÍ…°…±±‰…¬A$¸(ÄÀ¸QÉ½½ÀÙ•¹ÑÌ…É”•¹½Õ¹Ñ•Èµ±½…°Á…ÉÑ¥¥Á…¹ÑÌìÑ¡”ÕÉÉ•¹Ð±½Ü¥¹Ù¥Ñ…Ñ¥½¸(€€€¥Ì…¸¥µÁ±•µ•¹Ñ…Ñ¥½¸Á…Ñ °¹½ÐÑ¡•¥ÈÍ•µ…¹Ñ¥Œ½Ý¹•È¸(ÄÄ¸M•¹”¡½½­Ì…É”M•¹”µ¥¹ÍÑ…¹”ÁÉ½É…µÌ°¹½Ð	…ÑÑ±”±¥™•å±”¸(ÄÈ¸½µµ½¸Ù•¹ÑÌ…É”É•ÕÍ…‰±”ÁÉ½•‘ÕÉ•Ì½ÁÉ½•ÍÍ•Ì°¹½Ð¹•ÜÍ½ÕÉ•Ì¸(ÄÌ¸M•µ…¹Ñ¥Œ¥µÁ±•µ•¹Ñ…Ñ¥½¹Ì¥¹¡•É¥Ð…±±•È½¹Ñ•áÐ…¹±¥¹•…”¸(ÄÐ¸M½ÕÉ”½É‘•È¥Ì‘•±…É•…¹ÍÑ…‰±”ì¡…Í ½É‘•È¹•Ù•È‘•¥‘•Ì…µ•Á±…ä¸(ÄÔ¸=É¥¥¹…°½ÕÉÉ•¹ÐÑ…É•Ð°ÁÉ½Ù•¹…¹”°…Ñ¥½¸¥‘•¹Ñ¥Ñä°…¹±¥¹•…”ÍÕÉÙ¥Ù”(€€€¹•ÍÑ•½Á•É…Ñ¥½¹Ì¸(ÄØ¸I•…Ñ¥½¸µ•¹•É…Ñ•½Á•É…Ñ¥½¹Ì•¹Ñ•ÈÑ¡”Í…µ”Á¥Á•±¥¹”…¹…É”‘¥…¹½Í…‰±”¸(ÄÜ¸IA	…ÑÑ±”É•µ…¥¹Ì„™¥ÉÍÐµ±…ÍÌÍ•µ…¹Ñ¥Œ…Á…‰¥±¥Ñäì¥ÑÌ¥¹Ñ•É¹…°µ½‘Õ±”(€€€‘•½µÁ½Í¥Ñ¥½¸É•µ…¥¹Ì½Á•¸¸(Äà¸M•¹”ÑÉ…¹Í¥Ñ¥½¹Ì°µ½‘…°¥¹Ñ•É…Ñ¥½¹Ì°…¹Ù•¹Ð•á•ÕÑ¥½¸É•µ…¥¸‘¥ÍÑ¥¹Ð¸(Ää¸5¥ÍÍ¥¹œÉ•ÅÕ¥É•±½Ü¥Ì„±½ÕÙ…±¥‘…Ñ¥½¸½ÉÕ¹Ñ¥µ”™…¥±ÕÉ”¸((ŒŒ€ä¸¥‘•¹Ñ…°‰•¡…Ù¥½ÈÑ¡…ÐÍ¡½Õ±¹½Ð‰•½µ”½¹ÑÉ…Ð((¨…™Ñ•É}…Ñ¥½¸ÕÉÉ•¹Ñ±ä™½±±½ÝÌÑ¡”•¹Ñ¥É”Í•ÅÕ•¹”°¹½Ð•Ù•Éä•™™•Ð¸(¨Ù¥Ñ½Éä½É•Ý…É±½ÜÕÉÉ•¹Ñ±ä‰•¥¹Ì™É½´M•¹”ÑÉ…¹Í¥Ñ¥½¸¡…¹‘±¥¹œ…™Ñ•È±½œ(€Ñ¥µ¥¹œ°Í¼¥ÐµÕÍÐ¹½Ð‘•Á•¹½¸¡½Ü±½¹œÑ¡”Á±…å•ÈÉ•…‘Ì¸(¨ÕÉÉ•¹Ð±½Ü½µµ…¹±¥ÍÑÌ…±°IU9}QI==A}Y9QM€ìÑ¡¥Ì‘¥ÍÁ…Ñ Á…Ñ ‘½•Ì¹½Ð(€µ…­”±½ÜÑ¡”Í•µ…¹Ñ¥Œ½Ý¹•È½˜QÉ½½ÀÍ½Á”½È½˜½Ñ¡•È¡½ÍÐÑåÁ•Ì¸(¨¥µµ•‘¥…Ñ”Ñ¥½¸M•ÅÕ•¹”]%Q€ÕÉÉ•¹Ñ±ä…ÁÁ•¹‘Ì„ÁÉ•Í•¹Ñ…Ñ¥½¸•Ù•¹Ð…¹(€•á•ÕÑ¥½¸½¹Ñ¥¹Õ•ÌìÉ•¹‘•É•ÈÁ…¥¹œ¥Ì¹½Ð„Í•µ…¹Ñ¥ŒÍ¡•‘Õ±•Èå¥•±¸(¨11}=55=9}Y9PÕÉÉ•¹Ñ±äÕÍ•Ì„‘¥…±½Õ”É…Á …¹¥ÌÕ¹…Ù…¥±…‰±”¥¸(€¥µµ•‘¥…Ñ”µ½‘”ìÑ¡”…‘µ¥ÍÍ¥‰¥±¥Ñä‘¥ÍÑ¥¹Ñ¥½¸µ…ÑÑ•ÉÌµ½É”Ñ¡…¸Ñ¡”Á…Ñ ¸(¨•¹¥¹”½Í•¹•Ì½‰…ÑÑ±”¹±Õ„‘¥É•Ñ±äÉ•ÅÕ¥É•ÌÁÉ•Í•¹Ñ…Ñ¥½¸ì€ŒÈØÀÑÉ…­ÌÑ¡¥Ì¸(¨Í•ÑÕÀ±½Ü±…­Ì	…ÑÑ±”‰•™½É”	…ÑÑ±”¹¹•Ü¸(¨™¥á•‰…ÉÉ¥•ÉÌ°•á•ÕÑ¥½¸°…¹-%11}5A}IMQ=I…É”¹½Ð„•¹•É¥ŒÉ•…Ñ¥½¸A$¸(¨‰…Í”µ™¥ÉÍÐÑÉ½½À¥¹¡•É¥Ñ…¹”¥ÌÕÉÉ•¹Ð½É‘•È°¹½Ð™ÕÑÕÉ”Á…­…”½µÁ½Í¥Ñ¥½¸¸(¨ÕÉÉ•¹Ð¥µµ•‘¥…Ñ”É•ÕÉÍ¥½¸‘½•Ì¹½Ð•ÍÑ…‰±¥Í ±¥¹•…”½å±”Õ…É…¹Ñ••Ì¸(¨M•¹”µ±½…°}Õ…ÉÙ…É¥…‰±•Ì…É”¹½Ð„•¹•É…°É•…Ñ¥½¸µ±¥¹•…”µ•¡…¹¥Í´¸((ŒŒ€ÄÀ¸U¹É•Í½±Ù•½Ý¹•È‘•¥Í¥½¹Ì((Ä¸¥¹…°€ŒÌÀàÍ½ÕÉ”ÁÉ••‘•¹”…É½ÍÌ¥¹¹…Ñ”½Á…ÍÍ¥Ù”°•ÅÕ¥Áµ•¹Ð°ÍÑ…Ñ”°(€€Á…­…”°…¹…ÕÑ¡½É•½É‘•È¸(È¸A•¹‘¥¹œ½É•Í½±Ù•É•½ÉÍ¡•µ„™½È‘…µ…”°¡•…±¥¹œ°ÍÑ…Ñ”°É•Í½ÕÉ”°½ÍÐ°(€€Ñ…É•Ð°…¹‘•…Ñ °¥¹±Õ‘¥¹œ½É¥¥¹…°½ÕÉÉ•¹Ð…µ½Õ¹ÐÍ•µ…¹Ñ¥Ì¸(Ì¸½¹É•Ñ”±¥¹•…”É•ÁÉ•Í•¹Ñ…Ñ¥½¸…¹™¥¹…°±½Õ‘¥…¹½ÍÑ¥Œ½Í…™•ÑäÕ…É¸(Ð¸]¡¥ ÕÉÉ•¹Ð…™Ñ•É}…Ñ¥½¸Ñ¡É•Í¡½±Á…ÑÑ•É¹Ì‰•½µ”É•Í½±Ù•É•…Ñ¥½¹Ì°(€€Ý¥Ñ¡½ÕÐ‘Õ…°½‰Í•ÉÙ…Ñ¥½¸‘ÕÉ¥¹œµ¥É…Ñ¥½¸¸(Ô¸]¡•Ñ¡•È™ÕÑÕÉ”Á…­…•Ìµ…ä½¹ÑÉ¥‰ÕÑ”µÕ±Ñ¥Á±”±½ÜÁÉ½Ù¥‘•ÉÌ…¹¡½ÜÑ¡•ä(€€½µÁ½Í”¸(Ø¸½µµ½¸Ù•¹ÐÝ…¥Ð½É•ÍÕ±Ð½¹ÑÉ…Ð™½È•… ¡½ÍÐ¸(Ü¸5¥¹¥µ…°Í¡•‘Õ±•È‰É¥‘”™½ÈQ½Q½¥¹Ñ•ÉÉÕÁÐÍåÍÑ•µÌ¸(à¸á…ÐÙ¥Ñ½Éä½É•Ý…É½É•½Ù•ÉäÑÉ…¹Í…Ñ¥½¸‰½Õ¹‘…ÉäèÝ¡•Ñ¡•ÈÉ•Ý…É(€€…±Õ±…Ñ¥½¸‰•±½¹ÌÑ¼	…ÑÑ±”½ÕÑ½µ”™¥¹…±¥é…Ñ¥½¸½È„ÍÕ‰Í•ÅÕ•¹Ð(€€±¥™•å±”½Á•É…Ñ¥½¸°…¹¡½ÜÕÉÉ•¹ÐM•¹”µ¥¹¥Ñ¥…Ñ•Ù¥Ñ½Éä±½Üµ¥É…Ñ•Ìì(€€ÁÉ•Í•¹Ñ…Ñ¥½¸Ñ¥µ¥¹œµÕÍÐÉ•µ…¥¸¥ÉÉ•±•Ù…¹Ð¸(ä¸€ŒÈØÀÌ	…ÑÑ±”M•¹”½ÁÉ•Í•¹Ñ…Ñ¥½¸Í•…´°Ý¥Ñ¡½ÕÐÑ¥µ¥¹œ½È½±‘•¸¡…¹•Ì¸(ÄÀ¸M•Á…É…Ñ”¥…±½Õ”µ½‘…°µ¥É…Ñ¥½¸‘•Í¥¸¸((ŒŒ€ÄÄ¸Mµ…±±•ÍÐÉ•½µµ•¹‘•™½±±½ÜµÕÀ¥µÁ±•µ•¹Ñ…Ñ¥½¸¥ÍÍÕ•Ì((Ä¸€ŒÌÀàÑåÁ•ÑÉ…¹Í¥Ñ¥½¸™¥áÑÕÉ”è½¹”‘…µ…”Á•¹‘¥¹œÉ•½É°É•Í½±Ù•™…Ð°…¹(€€Í½ÕÉ”É•…Ñ¥½¸Ý¥Ñ¡½ÕÐµ¥É…Ñ¥¹œÑÉ…¥ÑÌ¸(È¸€ŒÌÀà‘•Ñ•Éµ¥¹¥ÍÑ¥Œ±¥¹•…”™¥áÑÕÉ”èÑ•Éµ¥¹…Ñ¥¹œQ¡½É¹Ì¡…¥¸…¹‘¥…¹½Í•(€€½Õ¹Ñ•Èµå±”Ý¥Ñ •áÁ±¥¥ÐÍ½ÕÉ”½É‘•È¸(Ì¸€ŒÌÀàµÕ±Ñ¤µ¡¥Ð™¥áÑÕÉ”èÁÉ½Ù”Á•Èµ•™™•Ð½µµ¥Ð½É•…Ñ¥½¸‰•™½É”½¹Ñ¥¹Õ…Ñ¥½¸¸(Ð¸€ŒÌÀà5…¥ŒÕ…É™¥áÑÕÉ”è‘•™¥¹”¥¹ÍÕ™™¥¥•¹Ðµ5@É•‘¥É•Ð…¹™½É‰¥(€€±¥™•å±”µÕÑ…Ñ¥½¸½˜Á•¹‘¥¹œ‘…µ…”¸(Ô¸QÉ½½ÀÑ¡É•Í¡½±½Ý¹•ÉÍ¡¥À‘•Í¥¸èµ¥É…Ñ”½¹”‰½ÍÌµÁ¡…Í”…Í”Ñ¼½¹”(€€É•Í½±Ù•µ™…Ð½‰Í•ÉÙ•È°Ý¥Ñ¡½ÕÐ„‰É½…ÑÉ½½ÀÍ¡•µ„É•ÝÉ¥Ñ”¸(Ø¸M•µ…¹Ñ¥Œ½µµ…¹É•ÍÕ±Ð½Ý…¥Ð™¥áÑÕÉ”è½¹”‘…Ñ„µ‘•™¥¹•¥µÁ±•µ•¹Ñ…Ñ¥½¸Ý¥Ñ (€€¥µµ•‘¥…Ñ”…¹¥¹Ñ•É…Ñ¥Ù”…‘µ¥ÍÍ¥‰¥±¥ÑäÑ•ÍÑÌ¸(Ü¸	…ÑÑ±”½ÕÑ½µ”…ÕÑ¡½É¥Ñä…Õ‘¥Ðè¥Í½±…Ñ”É•Ý…É½É•½Ù•Éä™É½´±½œÑ¥µ¥¹œ¸(à¸€ŒÈØÀ‘•Á•¹‘•¹äÍ•…´è½Ý¹•ÈµÍÕÁ•ÉÙ¥Í•	…ÑÑ±”M•¹”ÁÉ•Í•¹Ñ…Ñ¥½¸‰½Õ¹‘…Éä¸()Q¡”™¥ÉÍÐÑ¡É•”…É”Ñ¡”Í…™•ÍÐ¹•áÐÝ½É¬‰•…ÕÍ”Ñ¡•äÑ•ÍÐÑ¡”½¹ÑÉ…ÐÝ¥Ñ¡½ÕÐ)¡…¹¥¹œ…ÕÑ¡½É•ÁÉ½‘ÕÑ¥½¸‰•¡…Ù¥½È¸¼¹½Ð‰•¥¸„‰É½…¡½ÍÐµ¥É…Ñ¥½¸°)±½ÜÉ•¹…µ”°¥…±½Õ”µ¥É…Ñ¥½¸°½ÈÍ¡•‘Õ±•È¥µÁ±•µ•¹Ñ…Ñ¥½¸Õ¹Ñ¥°½¹Ñ•áÑÌ…¹)±¥¹•…”™¥áÑÕÉ•Ì½¹Ù•É”¸((ŒŒ½¹±ÕÍ¥½¸()]¡•¸…¸IAÁ¡•¹½µ•¹½¸½ÕÉÌ¥¸Q¡•ÍÑÉ„°¥‘•¹Ñ¥™ä¥ÑÌ±¥™•å±”½ÈÑÉ…¹Í¥Ñ¥½¸)Í½ÕÉ”™¥ÉÍÐ¸Q¡”‘½µ…¥¸…ÕÑ¡½É¥ÑäÁÕ‰±¥Í¡•Ì½•ÍÑ…‰±¥Í¡•ÌÑ¡…ÐÁ¡•¹½µ•¹½¸ì)‘½µ…¥¸µÝ¥‘”…ÕÑ¡½É•Á½±¥äµ…ä‰”„±½Ü°…¸•¹½Õ¹Ñ•Èµ…ä…‘µ¥ÐQÉ½½ÀÙ•¹Ð)Á…ÉÑ¥¥Á…Ñ¥½¸°…¹ÑåÁ•€ŒÌÀàÉ•…Ñ¥½¹ÌÁ…ÉÑ¥¥Á…Ñ”½¹±ä…ÐÑ¡•¥ÈÑåÁ•)ÑÉ…¹Í¥Ñ¥½¸‰½Õ¹‘…Éä¸M•¹”±¥™•å±”½¥¹ÁÕÐÉ•µ…¥¹Ì‘¥ÍÑ¥¹Ð¸¸…Ñ¥½¸ÉÕ¹Ì)¥ÑÌÑ¥½¸M•ÅÕ•¹”ì„ÑåÁ•ÑÉ…¹Í¥Ñ¥½¸¥Ì…±Õ±…Ñ•…¹¥¹Ñ•É•ÁÑ•‰äÑ¡”)Í•µ…¹Ñ¥Œ…Á…‰¥±¥ÑäÑ¡…Ð½Ý¹Ì¥ÐìÑ¡…Ð…Á…‰¥±¥Ñä½µµ¥ÑÌ½¹”…¹ÁÕ‰±¥Í¡•Ì„)É•Í½±Ù•™…ÐìÍ½ÕÉ”µ±½…°É•…Ñ¥½¹Ì½¹ÍÕµ”Ñ¡…Ð™…Ð…¹•¹Ñ•ÈÑ¡”Í…µ”)Á¥Á•±¥¹”ìÁÉ•Í•¹Ñ…Ñ¥½¸ÁÉ½©•ÑÌÑ¡”É•ÍÕ±Ð½¸¥ÑÌ½Ý¸±½¬¸ÕÉÉ•¹Ð±½Üµ…ä)ÍÑ¥±°½¹Ñ…¥¸IU9}QI==A}Y9QM€°‰ÕÐÑ¡…Ð¥ÌÕÉÉ•¹Ð½É¡•ÍÑÉ…Ñ¥½¸É…Ñ¡•ÈÑ¡…¸)Ñ¡”Õ¹¥Ù•ÉÍ…°½Ý¹•ÉÍ¡¥Àµ½‘•°¸()Q¡¥ÌÁÉ•Í•ÉÙ•Ì½µÁ½Í…‰±”…ÕÑ¡½É¥¹œÝ¥Ñ¡½ÕÐ‘ÕÁ±¥…Ñ”¡½½¬ÍåÍÑ•µÌ°­••ÁÌIA)	…ÑÑ±”Í•µ…¹Ñ¥Ì…ÕÑ¡½É¥Ñ…Ñ¥Ù”…¹™¥ÉÍÐµ±…ÍÌ°…¹±•…Ù•ÌÍ¡•‘Õ±¥¹œ°$°)•¹½Õ¹Ñ•ÈÁ½±¥ä°M•¹”½µÁ½Í¥Ñ¥½¸°…¹ÁÉ•Í•¹Ñ…Ñ¥½¸™É•”Ñ¼•Ù½±Ù”‰•¡¥¹)•áÁ±¥¥Ð½¹ÑÉ…ÑÌ¸(