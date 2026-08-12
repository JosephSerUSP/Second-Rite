# Battle Scene, Event Program, and Action Sequence boundary audit

Status: research report for #326, prepared from `origin/main` at
`8bbc07054542fad8196d27d8cce9bb437b01ddf4` (2026-08-11). This report changes
no runtime behavior, authored schema, golden reference, or production battle
file.

## Executive summary

The current Battle Scene is not simply “bad native code”. It is a useful
architectural specimen whose responsibilities have already started separating:

* `engine/battle.lua` is the authoritative reusable RPG battle capability. It
  constructs and orders actions, applies costs and effects, publishes resolved
  events, and decides victory/defeat/escape.
* `engine/scenes/battle.lua` is a Scene adapter and input/log coordinator, but
  it also contains presentation choreography and a small number of calls into
  the domain capability. Its most suspicious boundary is not “battle is
  RPG-specific”; it is the direct dependency on `presentation.*` and the
  content-specific input/reward choreography mixed with Scene hosting.
* `data/scenes/battle.json`, troop Events, Action Sequences, and battle Flows
  already provide a credible shared Event Program substrate. The current
  architecture therefore does not support a wholesale “move battle to data”
  conclusion. It supports a narrower one: keep a reusable RPG Battle
  capability, move project policy and repeated procedures into authored
  programs, and make presentation consume resolved facts rather than own
  mutations.

The useful semantic floor is not a collection of tiny commands such as
“subtract HP, set a flag, sort a list”. It is a small set of RPG-shaped
capabilities: action/target resolution, typed effect transactions, resource
and state transitions, selectors, resolved event facts, deterministic event
ordering, and a host-neutral interaction/wait protocol. These are the smallest
useful layers because below them authors would reconstruct battle invariants;
above them, common RPG sentences can remain data-defined.

The evidence-derived Action Sequence rule is:

> An Action Sequence describes the authored execution of one particular action:
> its targets, timing, repeated hits, effect calls, waits, and action-specific
> presentation beats. It is not a passive rule database, a replacement for
> authoritative effect resolution, or an unrestricted battle scripting escape.

The benchmark supports the working split, with two corrections:

1. Action Sequences may need a small amount of action-local control flow and
   presentation timing; “this skill is happening” is the decisive scope test.
2. A mechanic may cross layers. “Bide” has an Action Sequence that applies the
   state, but the stored-damage behavior belongs to source-local state plus a
   resolved-damage reaction. “Magic Guard” needs a native pending-damage
   interception capability; it should not be hidden inside a skill sequence.

Dialogue is a negative Scene fixture. The current implementation proves that
an Event Program can wait for a graph walker and that the caller’s identity is
important. It also shows why a dialogue Scene is an awkward ownership model:
the host Map or Battle context is displaced while the Event remains logically
the caller. The recommended future direction is a reusable Message/Choice
modal interaction layered over a host Scene, with input capture and host
simulation pause represented as independent policies. This is a recommendation
only; no Dialogue migration is part of this report.

## Evidence labels and scope

The report uses three labels:

* **Repository fact** — directly observed in the stated current-main file or
  issue. A file and line range is included where useful.
* **External evidence** — behavior or authoring practice documented by a linked
  RPG Maker or EasyRPG source.
* **Inference / recommendation** — an architectural conclusion drawn from the
  two evidence classes. It is not current implementation status.

The owner’s historical RM2k3 projects were not available in the workspace. The
optional personal-archaeology evidence therefore remains pending; the report
does not infer personal habits from its absence.

## 1. Current Battle Scene responsibility matrix

| Responsibility | Current owner and evidence | Classification | Keep native vs author | Smallest useful layer |
|---|---|---|---|---|
| Scene stack, scene-local `v`, push/pop/goto, hook dispatch | `engine/scene_host.lua:6-18,145-237,237-373` | generic Scene machinery; system/lifecycle hook | Keep in the host. Scene identity, lifetime, input focus, and transitions are runtime concerns. | A host that owns active context and invokes shared Event Programs; no battle-specific engine needed. |
| Battle scene registration and windows | `engine/scenes/battle.lua:36-54`; `engine/scene_host.lua:84-143` | UI/input composition; generic Scene machinery | Keep the window registry and declarative window data native/host-level. Window contents should remain data/presentation. | A registered window surface and focus protocol, not a new battle language. |
| Encounter start and enemy construction | `engine/scenes/battle.lua:107-161`; `data/flows/battle.json` | reusable RPG battle capability plus authored encounter policy | The capability must construct a valid Battle; troop choice, ambush, and setup effects belong to Flow/Troop Event data. | `START_BATTLE`/battle-start capability with typed context and Event Program hooks. |
| Battle-local roster and active members | `engine/scenes/battle.lua:74-104` | RPG battle capability observed by UI; UI composition | Keep authoritative roster membership in Battle/session. The Scene may project “who needs input” but must not reimplement forced-action rules. | A query such as eligible command subjects, backed by the Battle authority. |
| Round construction | `engine/battle.lua:602-637` | genuinely native reusable RPG semantic capability | Keep the transaction boundary native. A round is a useful RPG sentence; authors should configure policy and hooks, not rebuild queue integrity. | `resolve_round` with typed contexts and hook slots. |
| Player action collection | `engine/scenes/battle.lua` hooks/scripts in `data/scenes/battle.json`; API bridge at `engine/interpreter_core.lua:2220-2260` | UI/input composition; Event Program candidate | Authorable command-window layout and selection policy; native bridge should expose typed “commit action” and “select target”. | A shared command/target interaction capability. |
| AI action selection | `engine/battle.lua:142-235,330-341` | reusable RPG capability; project policy | Keep a valid action/target contract native. AI scoring and authored conditions can become data capabilities later, but do not duplicate player and AI legality rules. | Shared action-availability and target-eligibility queries. |
| Initiative, priority, speed ordering | `engine/battle.lua:265-360` | reusable RPG capability; possible modifier channel | Keep deterministic ordering and RNG ownership native. Rates and policy can be modified through typed calculation contributions. | An initiative scheduler with declared ordering, not a new Scene kind. |
| First strike/rear guard | `engine/battle.lua:363-414` | #308 modifier/interceptor candidate; RPG capability | The structural first-strike pass is native today. Future passive contributions should enter a typed initiative channel; do not create an `INITIATIVE` handler per new sentence. | One scheduler channel plus source-aware modifiers. |
| Target selection and cover | `engine/scenes/battle.lua:407-463`; `engine/battle.lua:720-754` | RPG capability; UI/input composition; #308 target interceptor candidate | Target legality, resolution, and cover interception belong to battle/targeting authority. Cursor movement and inspection belong to the Scene. | Shared target selectors plus a pending target rewrite/intercept seam. |
| Authoritative damage/healing/state/resource mutation | `engine/battle.lua:470-549,640-717`; `engine/effects_core.lua`; `engine/resolved_event.lua` | genuinely native reusable RPG semantic capability; #308 transition seam | Keep native and single-owner. Event Programs can request typed effects; presentation must never replay or repair them. | Typed effect transactions and immutable resolved facts. |
| Action Sequence dispatch | `engine/battle.lua:519-547,682-710`; `data/actionSequences.json` | Action Sequence responsibility | Keep the dispatch native and the sequence authored. The sequence chooses action-local composition; effects still commit in the domain owner. | A shared immediate Event Program with action context, not a second script language. |
| Troop Events | `data/troops.json`; `engine/troop.lua`; `engine/battle.lua:551-561` | Event Program candidate; RPG system/lifecycle hook | Keep troop ownership: a troop can suppress or add encounter-local behavior. Do not silently promote all troop policy to global Flow. | A battle-event host with typed lifecycle facts and troop scope. |
| Battle Flows | `engine/flow.lua:1-62`; `engine/battle.lua:557-615`; `data/flows/battle.json` | system/lifecycle hook; Event Program candidate | Retain the mechanism for now. Reassess the noun later, after hook ownership and troop/event precedence are specified. | A registered lifecycle signal that runs an Event Program. |
| Combat log event queue | `engine/scenes/battle.lua:218-359,361-405` | presentation replay/choreography; UI composition | Keep a presentation queue, but it must consume resolved event records and text facts. It must not be the authoritative event producer. | A host-neutral event stream plus presentation adapter. |
| Waits and auto-advance | `engine/scenes/battle.lua:361-405,798-867` | presentation choreography; system/lifecycle hook | Keep waits in the interaction/presentation scheduler. Data should be able to request a wait; the renderer should decide how to reveal it. | A typed wait/focus protocol shared with dialogue and other hosts. |
| Damage numbers, animation callbacks, card swaps | `engine/scenes/battle.lua:220-356`; `presentation/battle_view.lua`; `presentation/animation_player.lua` | presentation replay/choreography | Move the dependency seam, not the behavior into event data. The view may retain an earlier projection until a resolved beat arrives. | Presentation subscribes to resolved facts and owns timing/FX. |
| Victory/defeat/escape transition | `engine/scenes/battle.lua:567-754`; `engine/battle.lua:567-599` | RPG lifecycle hook; Scene transition; Second Gate policy | Battle outcome facts are native. Reward narration, emergency wave policy, and return-to-map presentation are partly authored/project policy. | Outcome hooks returning typed transition facts; host consumes scene changes. |
| Victory rewards and level-up narration | `engine/scenes/battle.lua:627-705`; `data/flows/battle.json` | Second Gate-specific policy; Event Program; UI composition | Keep reward mutation in RPG capability/Flow, but the Gold/EXP beat sequencing is presentation policy and should not define authority. | Reward result + authored presentation procedure. |
| Battle start/end cleanup | `engine/scenes/battle.lua:129-161,569-754`; `engine/battle.lua:62-97` | system/lifecycle hook; RPG capability | Native lifecycle must guarantee cleanup and outcome delivery. Project-specific sounds, warnings, and recovery are data hooks. | Explicit `battle_started`, `battle_ended`, `victory`, `defeat`, `escape` facts. |

### What is genuinely native here?

The audit does not support removing native RPG Battle. The following are
semantic invariants rather than project flavor:

* a valid battler/action/target graph;
* one authoritative round transaction and deterministic queue order;
* typed target resolution and effect application;
* resource payment at the point an action actually resolves;
* state/death/victory decisions after authoritative mutation;
* immutable resolved facts with source/target/action provenance;
* a host-neutral way to wait for presentation or interaction.

Making these ordinary event commands would force every author to reconstruct
ordering, cancellation, target identity, and “commit exactly once” rules. That
is below the smallest useful semantic layer. Conversely, ambush text, strain
warnings, boss phases, victory narration, and an encounter’s emergency-wave
policy are already represented as data or can be represented by the same Event
Program model.

### Proliferation pressure

The current `scene_host.push` extension point attempts to load
`engine.scenes.<kind>` and lets it register kind windows
(`engine/scene_host.lua:237-270`). This makes `battle.lua` convenient, but it
also makes the path of least resistance for `atb_battle.lua`, `pong.lua`, or
`fighting.lua`.

The proliferation trigger is not the existence of authored Scenes. It is the
absence of reusable capabilities for:

* scheduling and time/turn progression;
* action collection and target selection;
* collision/occupancy or spatial queries;
* typed effects and resources;
* modal input focus and waits;
* presentation projection from resolved facts;
* reusable lifecycle Event Programs.

**Recommendation:** retain the native kind seam for genuinely reusable host
adapters, but make a data-defined Scene with attached capabilities the normal
path. A new native module should be justified by a reusable semantic capability
or a genuinely different runtime context, not by a new content sentence.

## 2. Current Action Sequence boundary

### Repository fact

Skills and items select an Action Sequence or fall back to a default sequence;
the Battle supplies `a`, `target`, `targets`, `skill`/`item`, `battle`, `session`,
`loader`, `events`, and `refs` and runs the shared immediate interpreter
(`engine/battle.lua:519-547,682-710`). This is already the right shape for a
single shared Event Program language. `data/actionSequences.json` contains
action-specific animation/effect commands rather than a general passive trait
database.

### Boundary rule

An Action Sequence is the authored procedure for resolving or presenting one
action instance. It may:

* select or expand the action’s targets;
* perform one or more hits/effect applications;
* branch on action-local facts such as hit, critical, or target state;
* invoke reusable Common Events for a procedure that is not inherently tied to
  one skill;
* emit action-local text, animation, movement, sound, and waits;
* create a declared follow-up action when that is the sentence of the action.

It should not:

* directly mutate authoritative HP/MP/inventory/state outside typed effect
  commands;
* scan global state to rediscover whether a hit happened;
* implement passive behavior because a state/equipment/trait exists;
* replace the round scheduler, target resolver, or battle end authority;
* become an unrestricted Lua escape hatch;
* own renderer rollback or replay of committed mutations.

### Representative boundary matrix

| Mechanic / author intent | Best home | Why |
|---|---|---|
| A skill hits three times with a pause between hits | Action Sequence + native effect capability | The repetition and timing are properties of this action; damage remains authoritative. |
| A healing spell heals the primary target, then splashes 50% to allies | Action Sequence + group selector | The sequence expresses this action’s composition; the selector/effect is reusable. |
| Mug converts the final damage of this hit into Gold | #308 resolved reaction, possibly invoked by an action tag | It depends on the resolved transition and source provenance, not merely on the action’s animation. |
| Lifesteal heals the user from final damage | #308 resolved reaction | It must read committed damage exactly once and avoid recomputing formulas. |
| Thorns retaliates whenever its bearer takes damage | #308 resolved reaction with lineage guard | It exists because the state/equipment exists and must work for any incoming action. |
| Magic Guard redirects pending HP damage into MP | native pending-transition/interceptor capability plus authored filter | It must intervene before commit and preserve remaining/original amounts. |
| Undead turns healing into damage | native typed conversion/interceptor plus authored state rule | Generic conversion and recursion/bypass semantics are required. |
| Bide stores received damage, then releases it on this skill | Action Sequence starts/releases; source-local state and resolved reaction store it | The action owns release timing; the state owns memory across actions. |
| Toxic increases damage on each periodic tick | lifecycle hook + source-local state + effect | It is a state/tick rule, not a one-action choreography. |
| A skill applies a temporary “next fire spell is stronger” charge | Action Sequence may consume it; #308 calculation modifier owns the passive charge | The charge changes future actions, so its existence is not action-local. |
| A skill forces the target to use a named skill immediately | native forced-action capability, invoked by Action Sequence | Queue insertion, legality, recursion, and actor/enemy symmetry cannot be left to ad hoc commands. |
| A reusable “show bark, wait, set variable” procedure | Common Event/Event Program | It is a named procedure usable from Map, Battle, or another host. |
| Battle-start ambush or boss phase at 60% HP | troop Event or lifecycle hook | It is encounter policy at a domain timing, not a skill action. |
| Damage popup, camera move, hit stop, animation wait | Scene/presentation composition | Presentation can consume the resolved event and retain its own clock. |

### Counterexamples to the simple hypothesis

The working hypothesis is useful but not absolute:

1. **A passive may need an Action Sequence.** A “counter spell” can use an
   Action Sequence for its actual retaliatory animation and hits, but the
   trigger is a #308 reaction.
2. **An action may need #308.** “Every hit of this skill applies a mark that
   detonates later” uses an Action Sequence for mark application, while the
   detonation is a resolved reaction with source-local state.
3. **A Common Event may be invoked by an Action Sequence.** Reuse is orthogonal
   to timing. The distinction is that the Common Event is a procedure, while
   the sequence supplies the action context.
4. **A lifecycle hook may call an Action Sequence.** A battle-start scripted
   meteor can be authored as a troop Event that invokes a named action
   composition; the hook owns when it happens, the sequence owns what that
   action does.

The boundary is therefore about ownership and lifetime, not command count.

## 3. External RPG Maker benchmark

### RM2k3 and evented systems

**External evidence:** the official MZ help retains the same three useful
authoring roles—Map Events, Battle Events, and Common Events. It describes Map
Events as conversations/chests/progression, Battle Events as troop-scoped
behavior such as transforming under an HP threshold, and Common Events as
reusable behavior callable from Map and Battle Events ([official Events help](https://rpgmakerofficial.com/product/MZ_help-en/01_09.html)).

The directly inspectable EasyRPG archival record of RM2k3 Battle Common Events
is especially valuable because it documents the boundary failures rather than
only the happy path. Messages, choices, variables, party changes, HP/MP
changes, conditions, and Common Event calls work in battle; map-only commands
such as picture movement or map event movement are deferred to or act on the
map; waiting for a key can freeze battle ([EasyRPG RM2k3 Battle Common Events](https://wiki.easyrpg.org/development/technical-details/common-events-battle-2003)).

Normalized author intent:

* “Run this reusable procedure during battle” is a Common Event sentence.
* “At this troop timing, transform or warn” is a Battle Event sentence.
* “Change a variable, switch, resource, state, or party membership” is a
  reusable command capability, subject to host legality.
* “Show a message/choice and resume the caller” is an interaction that needs a
  host-aware wait contract; it is not proof that the whole host should become
  a new Scene.
* “Build a custom menu/battle system with pictures, variables, switches, and
  Key Input Processing” demonstrates missing reusable capabilities (input
  routing, timer/scheduling, drawing layers, collision/target queries), not a
  requirement to preserve every workaround.

The RM2k3 evidence also gives a negative lesson: when Common Events were
allowed to call commands whose ownership was map-only, the result was deferred
or surprising behavior. Thestra should expose typed host capability and fail
loudly when a command is unavailable rather than reproducing historical
ambiguity.

### Maniacs Patch

**External evidence:** the directly inspectable Maniacs Patch description
exposes a “Control Battle” command and ATB gauge values for characters and
enemies, with a battle-start Common Event used to install the control behavior
([Maniacs Patch reference](https://www.makerando.com/forum/topic/1849-maniacs-patch/)).

Normalized pattern:

```text
engine phenomenon (ATB/defensive battle process)
    -> typed callback/control context
    -> Common Event reads or changes it
```

This is strong evidence for #308’s direction. A callback is useful when it
exposes a typed phenomenon and its ownership boundary; it is not useful when it
merely exposes an arbitrary native method. Maniacs also shows why battle
domain vocabulary should remain first-class: “ATB gauge”, “current battle
process”, and “targeting” are meaningful author concepts, not generic ECS
fields.

### VX Ace / MV / MZ ecosystem

**External evidence:** Yanfly’s Battle Engine Core documents action sequences as
instructions for constructing a customized skill both visually and
mechanically, while separately documenting battle windows, action order,
Common Events, forced actions, and ATB/CTB extension plugins ([YEP Battle Engine Core](https://www.yanfly.moe/wiki/Battle_Engine_Core_%28YEP%29)).
Its Action Sequence category includes distinct packs for mechanics, movement/
camera/presentation, and battle-system extensions ([YEP Action Sequence Pack 1](https://www.yanfly.moe/wiki/Action_Sequence_Pack_1_%28YEP%29), [Pack 2](https://www.yanfly.moe/wiki/Action_Sequence_Pack_2_%28YEP%29), [YEP ATB](https://www.yanfly.moe/wiki/Battle_System_-_ATB_%28YEP%29)).

Normalized findings from this corpus and the completed #309 benchmark:

| Repeated author request | What it reveals for Thestra |
|---|---|
| Multi-hit, cast, motion, animation, camera, wait, and forced-action sequences | Action-local orchestration is a real semantic layer; it should not be flattened into damage formulas. |
| Regen, lifesteal, thorns, Bide, Toxic, barriers, Guts, Undead, death wards | Passive and state behavior repeatedly needs calculation channels, pending interception, resolved reactions, source-local state, and provenance. This is #308 territory. |
| Dynamic costs, limited uses, mastery, skill availability | Cost/charge calculation and action eligibility are reusable RPG capabilities, not per-skill scripts. |
| Target rewriting, aggro, cover, actor/enemy differences | Target selection needs original/current target identity and shared legality queries. |
| Victory, reward, transform, and battle-start events | Lifecycle hooks hosting Event Programs are more expressive than a global hardcoded callback list. |
| ATB/CTB/STB variants | Scheduling is a reusable capability; a new timing model should not automatically require a new Scene engine. |

The prior benchmark in #313 is important methodology: it normalized plugin
mechanics into author intent and found recurring pressure around calculation,
pending transitions, resolved facts, source-local memory, selectors, and
lineage. This report adopts that evidence rather than copying plugin APIs.

## 4. Flow semantics and lifecycle hooks

### Current Flow inventory

**Repository fact:** `engine/flow.lua` maps a dotted phase such as
`battle.round_start` to an authored command list in `data/flows/<host>.json`.
It runs immediately with a context containing session, loader, battle, party,
enemies, battler refs, and `v` locals (`engine/flow.lua:1-62`). Battle calls
the phases unconditionally in these positions:

| Flow slot | Cause and context | Current content / ownership judgment |
|---|---|---|
| `battle.battle_start` | `battle.triggerBattle`; session and troop id | Encounter spawn and troop construction. Reusable RPG lifecycle with authored encounter policy. |
| `battle.round_start` | before queue construction; session, battle, party | Global/Second Gate round policy. Genuine lifecycle signal; content should remain in Flow or be split into troop-local Events by explicit precedence. |
| `battle.after_action` | after each action’s effect events, before outcome check; actor/target context | Troop reactions and boss phase policy. A good battle-event hook; it overlaps with #308 only when the trigger is a resolved effect rather than merely “an action ended”. |
| `battle.round_end` | after the queue; session and battle | Regeneration, strain, poison, exhaustion and other tick policy. Genuine lifecycle; state-specific behavior may eventually belong to #308 reactions. |
| `battle.victory` | after outcome and before leaving; session, battle, party, enemies | Rewards/recovery and Second Gate economy policy. Lifecycle signal hosting an Event Program. |
| `battle.defeat` | outcome | Recovery/game-over policy. Lifecycle signal; Scene decides transition presentation. |
| `battle.escaped` | successful escape | Expedition/map policy. Lifecycle signal; likely authored source policy. |
| `exploration.step` and related exploration slots | map movement/step context | World-specific recurring procedures such as traps, recovery, adjacency, and encounter checks. Some are general RPG lifecycle, some Second Gate economy. |
| `quest.*` | quest/progress transitions | Quest-domain lifecycle; reusable RPG capability plus authored campaign policy. |

**Repository fact:** troop Events already carry `at`, `once`, conditions, and
commands in `data/troops.json`. The file’s own descriptions explain why
ambush/strain were lifted out of global flow: an individual troop may suppress
them. That is evidence that scope and precedence matter more than the name
“Flow”.

### Flow versus registered lifecycle hook

The architecture hypothesis

```text
registered engine/system lifecycle signal -> Event Program
```

describes the current mechanism better than “Flow is a special scripting
language”. Current Flow is already a database lookup followed by shared
interpreter execution. The open question is author-facing topology:

* Flow is useful as a compact, inspectable table of required system phases.
* “Lifecycle hook” is clearer when a signal needs declared context, ordering,
  scope, cancellation/result semantics, or multiple providers.
* Scene hooks overlap when the signal is about a Scene instance’s input/frame
  lifetime rather than battle/exploration system time.
* Action Sequences overlap when the signal is inside one action’s procedure.
* #308 overlaps when the signal is a typed pending/resolved effect phenomenon.

**Recommendation:** do not rename, migrate, or delete Flow now. Keep it as the
current authoring surface while specifying each phase’s contract. Over time,
decompose only where evidence warrants it:

1. retain explicit system lifecycle slots for battle/round/victory and
   exploration/quest transitions;
2. let troop/actor/state/equipment sources register scoped Event Programs for
   typed lifecycle facts;
3. keep Scene hooks for Scene-instance composition/input/frame behavior;
4. keep Action Sequences for action-local execution;
5. route typed effect reactions through #308 rather than adding more global Flow
   names.

This is smaller and safer than either “Flow is wrong” or “every callback gets a
new Flow”.

## 5. Dialogue as a negative Scene fixture

### Current repository fact

`data/scenes/dialogue.json` is a windows-drawn Scene. Its note says it is
reached by `scene_host.goto_scene("dialogue")` from map/Event chains. The graph
walker and dialogue state are maintained in `main.lua` (`main.lua:793-911,
1180-1235,1410-1450,1770-1808`). `interpreter.runInteractive` builds a dialogue
graph from the shared command list (`engine/interpreter_core.lua:369-445,
2922-2960`). `CALL_COMMON_EVENT` starts a common-event graph and the current
caller remains conceptually the Event waiting on that graph.

This is a sound waiting model but an awkward runtime ownership model:

```text
Map/Battle host -> goto Dialogue Scene -> graph walker waits -> return/pop
```

The host context is displaced even though the authored Event is still the
caller. A Battle Event that speaks during an action can therefore look like a
Scene transition even when the desired semantics are “pause this Event and
capture message input”.

### Recommended distinction

* **Scene:** active runtime context/composition, with local state, systems,
  presentation, and input mapping.
* **Modal interaction:** temporary behavior/presentation/focus layered over the
  current host.
* **Event Program:** authored execution that may suspend on the interaction and
  resume with a result.

Dialogue normally belongs to the second and third categories. The host Scene
should survive; the caller Event identity should survive; the message/choice
modal should own focus; the Event interpreter should wait for a result.

Input capture and host simulation pause must be separate fields/policies:

| Situation | Capture input | Pause host simulation | Caller |
|---|---:|---:|---|
| Map NPC conversation | yes | usually yes | Map Event |
| Battle taunt/message between turns | yes for message controls | usually yes for battle progression, but not necessarily ambient FX | troop/skill Event |
| ATB battle announcement | yes for message | authored choice: pause ATB or let it continue | battle lifecycle Event |
| Cutscene over moving simulation | yes | possibly no | map/common Event |

This fixture should guide future architecture but does not authorize migrating
Dialogue in #326.

## 6. MZ Plugin Commands and data-defined semantic commands

### External evidence

The official MZ help describes Plugin Command as an Advanced event command that
sends a command to a plugin ([official Plugin Command help](https://rpgmakerofficial.com/product/MZ_help-en/01_10_16.html)). The official plugin tutorial explains that MZ changed from MV’s free-text command/arguments to annotation-defined command metadata, then dispatches with:

```js
PluginManager.registerCommand("PluginName", "CommandName", args => {
    // command implementation
});
```

The callback receives the configured arguments as an object ([official MZ plugin tutorial](https://rpgmakerofficial.com/product/mz/plugin/make/koushiki.html)). The official community blog emphasizes that Plugin Commands are an in-event way to call plugin behavior, with labeled commands and an Arguments table ([Using Plugins in MZ](https://www.rpgmakerweb.com/blog/using-plugins-in-mz)).

### Normalized runtime model

MZ separates four things that are often conflated:

1. plugin metadata declares the editor-visible command name, help, and typed
   argument shapes;
2. the event serializes plugin identity, command identity, and argument values;
3. `PluginManager.registerCommand` registers a runtime dispatcher;
4. the command executes in the current interpreter/event context and can use
   the engine’s current caller, variables, switches, party, battle, or Scene
   APIs.

This is good evidence for Thestra’s data-defined semantic command hypothesis,
but not evidence for introducing a native plugin ABI now.

### Thestra comparison

| MZ concept | Thestra analogue | Boundary |
|---|---|---|
| Plugin metadata | Registry entry with name, context, typed params, result/wait contract | Must be editor-visible and validator-checked. |
| Serialized plugin/command identity | `cmd` registry id plus arguments | Preserve identity; do not serialize generated Lua. |
| `registerCommand` callback | Native handler or authored Event Program implementation | An authored implementation should run through the existing interpreter. |
| Current interpreter/caller | `ctx`, `ctx.v`, session/battle/Scene host, Event identity | Must be explicit and preserved across waits. |
| Plugin parameters/dependencies | Registry/package metadata later | Do not design a complete package ABI in this report. |
| Plugin Command event node | Semantic Event command | Should be a normal command in the shared editor, not a second scripting language. |

`SHOW_BARK(speaker,text,duration)` is a plausible authored semantic command if
it declares a typed interaction result and its implementation is an Event
Program composed from existing message/wait/animation capabilities. It is not
the same thing as a Common Event: a Common Event is a named reusable procedure;
the semantic command is an editor-facing sentence with a declared signature;
the implementation may call a Common Event or may be an authored program.

Native semantic capability is justified when the command must preserve an
authoritative invariant (for example, resolve a battle effect or enqueue a
valid target transaction) that would otherwise be impossible to express safely
or would make every author reconstruct engine internals.

## 7. Candidate reusable Thestra RPG capabilities

These are recommendations, not current implementation claims.

1. **RPG Battle transaction** — battle participants, action legality, target
   resolution, deterministic queue/scheduler, effect commit, and outcome.
2. **Typed effect transitions** — damage, healing, state, death, resource,
   cost, reward, and charge transitions with pending and resolved forms.
3. **Resolved event facts** — immutable source/action/target/original-target/
   final-value/provenance records for presentation and reactions.
4. **Target selector algebra** — self/source/target, original/current target,
   applier/last attacker, eligible group, lowest/highest, random eligible,
   neighbor, cover, and actor/enemy symmetry.
5. **Action scheduler** — turn, ATB, CTB, or other declared progression with
   deterministic ordering and shared action legality.
6. **Source-local state** — state-instance, equipment-instance, battler,
   action, battle, and session scopes with explicit save lifetime.
7. **Modifier/interceptor/reaction layer (#308)** — typed calculation channels,
   pending cancellation/reduction/redirect/conversion, and post-resolution
   reactions with lineage guards.
8. **Interaction/wait capability** — message, choice, key capture, focus, and
   result delivery independent from whether the host simulation pauses.
9. **Presentation projection** — animations, damage popups, camera, waits, and
   interpolated UI consume resolved facts and never replay mutations.
10. **Lifecycle Event host** — battle/round/action/victory/escape,
    exploration-step, quest transitions, and scene-instance hooks with declared
    context and precedence.

## 8. Candidate authored/data-defined surfaces

* Troop battle Events for encounter-local start, threshold, phase, and end
  policy.
* Common Events for reusable procedures independent of a particular action.
* Action Sequences for action-local effects, multi-hit order, target expansion,
  action-specific animation, and waits.
* Flow/lifecycle Event Programs for domain-wide timing until a more explicit
  hook representation is proven.
* Source behavior definitions for #308 calculations, interceptors, reactions,
  and local memory.
* Registry-defined semantic commands with typed parameters, context, result,
  and optional authored implementation.
* Scene data for windows, layout, hook composition, input mapping, and
  presentation configuration.
* Modal interaction templates for message, choices, inspect, and target
  selection, reusable over Map, Battle, and future authored Scenes.

The existing shared command editor should remain the authoring surface. A new
host is a new context and capability contract, not a new command-list editor.

## 9. Explicit do-not-generalize conclusions

* Do not rename Skills, Items, States, Units, Troops, Battles, Events, Common
  Events, or Action Sequences into generic ECS/resource nouns. These are healthy
  RPG author vocabulary and are part of Thestra’s product identity.
* Do not turn the RPG Battle transaction into a generic “entity interaction”
  API solely for universality. A strange RPG should be able to replace its
  scheduler or battle template while retaining the semantic capabilities it
  wants.
* Do not treat historical RM2k3 workarounds—variables-as-memory,
  picture-driven UI, copied pseudo-prefabs, or map-only commands in battle—as
  the desired Thestra architecture. Preserve the author intent, improve the
  missing capability.
* Do not expose one callback per plugin or one Flow name per edge case. Prefer
  typed phenomena with declared context and shared Event Programs.
* Do not make Action Sequence an arbitrary Lua/plugin replacement. Preserve
  its action-local RPG meaning.
* Do not make all effects “just commands”. Author commands should request typed
  transitions; native capabilities own commit/order/provenance.
* Do not make renderer presentation authoritative because it is convenient for
  a visual beat. The current resolved-event seam is the correct direction.
* Do not require a non-RPG project to use RPG Battle, Skills, Troops, or
  dialogue vocabulary. It may ignore or replace those layers; universal
  coverage is not the goal.
* Second Gate-specific policy includes Summoner MP strain, reserve-wave
  deployment, permadeath/reap narration, and its particular victory reward
  presentation. These should not be mistaken for the whole reusable RPG
  substrate merely because they currently appear near battle code.

## 10. Unresolved questions

1. What is the precise precedence between global Flow, troop Events, source
   reactions, and Scene hooks when they observe the same action or timing?
2. Which current Flow slots are required engine contracts versus optional
   authored policy, and how should missing optional hooks differ from missing
   required phases?
3. What is the minimal typed context for `battle.after_action` without creating
   a second #308 reaction system?
4. How should a future ATB scheduler share action legality and target selection
   with the current round scheduler while allowing host simulation to continue
   during a modal message?
5. Which presentation waits are part of an Action Sequence result and which are
   purely renderer choreography?
6. How should a semantic command declare whether it may wait, mutate, return a
   value, or be used in immediate Flow mode?
7. How are source-instance handles serialized for save-relevant charges,
   counters, and equipment/state provenance?
8. What is the deterministic ordering contract for multiple modifiers and
   reaction-generated reactions, including lineage cycle diagnostics?
9. Can Dialogue become a modal without breaking current event identity,
   golden traces, and battle host pause policy? This should be a separate
   migration investigation.
10. Which old owner projects, if later supplied, show recurring patterns that
    should influence Studio ergonomics rather than runtime semantics?

## 11. Recommended follow-up issues, safest to most architectural

1. **Document battle hook contracts** — record each current Flow, troop Event,
   Scene hook, and Action Sequence context/result/precedence without changing
   runtime behavior.
2. **Add a repository-only authorability fixture matrix** — cover the existing
   Action Sequence, Flow, troop Event, and Common Event surfaces with actor and
   enemy cases; no new engine architecture.
3. **Separate battle presentation adapter from Scene ownership (#260)** — make
   the dependency direction explicit while preserving the existing resolved
   event and visual timing behavior.
4. **Define the typed resolved-event/reaction contract (#308)** — use Mug,
   lifesteal, thorns, and critical-to-state as the smallest fixtures; include
   lineage and source-instance identity.
5. **Define pending transition channels** — damage/heal/state/resource/cost/
   death with deterministic modifier order and loud validation.
6. **Prototype one registry-defined semantic command** — a small authored
   `SHOW_BARK`-like command using the existing editor and interpreter; explicitly
   exclude a package/plugin ABI.
7. **Specify scheduler capability boundaries** — compare current round order
   with an ATB/CTB fixture before implementing any new scheduler.
8. **Investigate Dialogue modal ownership** — preserve current Dialogue during
   the investigation; test caller identity, input capture, and independent
   simulation pause.
9. **Reassess Flow as a public noun** — only after items 1–8 establish whether
   explicit lifecycle hooks improve author comprehension without duplicating
   command surfaces.
10. **Owner-project RM2k3 archaeology** — if source directories become
    available, inspect read-only with EasyRPG/liblcf/LCF2XML and compare
    recurring author patterns to the proposed Studio surfaces.

## 12. Validation and change boundary

The report was prepared from current `origin/main` and checked against the
current Battle, Scene Host, interpreter, battle data, troop data, Flow data,
Action Sequence data, Dialogue data, presentation view, and the completed #309
benchmark/PR #313. No optional owner-project archaeology was available.

The final branch must contain only this report. No gameplay gate or golden
recapture is required for a documentation-only change; `git diff --check` and a
documentation-only status/diff review are the relevant verification.
