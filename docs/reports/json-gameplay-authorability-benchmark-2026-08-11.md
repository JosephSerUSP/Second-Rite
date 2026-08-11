# JSON gameplay authorability benchmark (2026-08-11)

Status: evidence report for #308, produced for #309. This report proposes no
runtime change and does not claim that the proposed vocabulary is implemented.

## Executive finding

The corpus does not ask Second Rite to reproduce plugin APIs. It repeatedly asks
for a small typed language around four different questions:

1. what value is being calculated;
2. what pending transition may be cancelled, changed, or redirected;
3. what resolved fact happened and should trigger commands; and
4. what the concrete source instance remembers.

The current engine already has important pieces: 42 registry trait codes, 93
registered commands, 17 effect types, sandboxed formulas, typed target specs,
stack barriers, source-bearing `getActiveObjects`/`findAllSources`, and a
shared command editor with seven command contexts. Current JSON is therefore
strong for phase-level orchestration and simple effects, but weak at attaching
authored behavior to per-transition lifecycle points and at composing behavior
that must act before authoritative commit.

The evidence-derived minimum for #308 is three typed seams, not a universal
hook: calculation contributions, pending-transition interceptors, and resolved
event reactions, plus source-local state and a deterministic lineage/order
contract. Presets should hide that machinery for Regen, Counter, Lifesteal,
Guts, Death Ward, and similar common sentences.

## Method and corpus

The benchmark sampled distinct gameplay pressures rather than counting plugin
versions. Yanfly Tips & Tricks supplied unusual, concrete author requests;
VisuStella Battle Core and Anti-Damage Barriers supplied a mature lifecycle and
barrier ordering reference; the notetag index supplied costs, availability,
targeting, mastery, state, reward, and action surfaces. HimeWorks, Victor
Engine, Olivia, and the Yanfly-to-VisuStella community-port discussion were
used for independent corroboration and for actor/enemy and ordering failures.

Primary corpus URLs:

- Yanfly Tips & Tricks index: <https://www.yanfly.moe/wiki/Category:RPG_Maker_MV_Plugin_Tips_%26_Tricks>
- VisuStella Battle Core: <https://www.yanfly.moe/wiki/Battle_Core_VisuStella_MZ>
- VisuStella MZ notetag index: <https://www.yanfly.moe/wiki/Category:Notetags_(MZ)>
- VisuStella Anti-Damage Barriers: <https://www.yanfly.moe/wiki/Anti-Damage_Barriers_VisuStella_MZ>
- Community MV-to-MZ port discussion: <https://forums.rpgmakerweb.com/threads/how-to-implement-every-possible-yanfly-tips-tricks-effect-in-mz-with-visustella-plugins.143816/>
- HimeWorks MV plugin list: <https://himeworks.com/mv-plugins/>
- Victor Engine MV list: <https://victorenginescripts.wordpress.com/rpg-maker-mv/>
- Olivia Battle Effects Pack 1: <https://www.yanfly.moe/wiki/Battle_Effects_Pack_1_%28Olivia%29>

The Yanfly pages used as named stress specimens include Bide, Mirror Move,
Magic Guard, Toxic, Spell Shield, Lifesteal/Leech Seed, Thornmail, Phoenix
Ring, Undead, Guts-like fatal protection, dynamic costs, limited uses, state
replacement, and target-changing examples. The index also corroborates the
same families with Healing Link, Mana Burn, Death Mark, Adapting Armor,
Elemental Exposure, Power Charge, Share Life, Stockpile, Spirit Shackles,
Critical Vulnerability, and Victory Cry.

### Scoring

`A` = current JSON; `B` = proposed #308 generic layer; `C` = one small reusable
primitive beyond that layer; `D` = deeper authority/order/lifetime pressure;
`E` = intentionally out of scope. Expressibility and ergonomics are scored
1 (poor) to 5 (strong). “Current” means no new semantic primitive, not that a
long workaround would be pleasant.

## Normalized mechanic matrix

The compact notation in the matrix is: `L` lifecycle; `V` calculated values;
`R` references/selectors; `I` pending interceptor; `Q` resolved reaction;
`M` source-local memory; `P` provenance/ownership; `C` chain/recursion; `S`
symmetry; `Now` current Second Rite; `Need` smallest reusable gap; `E/X` the
two scores (expressibility/ergonomics); `Preset` likely Studio shape.

| # | Source / specimen | Normalized requirement; L/V/R/I/Q/M/P/C/S | Now / Need / result | E/X / preset |
|---|---|---|---|---|
| 1 | #232 Mug; Yanfly pattern | After qualifying cover-respecting physical hit, convert final HP damage to Gold. L after damage; V finalDamage; R source,target,action,cover; Q gain Gold; P trait/equipment source; C no loop; S any battler. | `A` can run a phase command but cannot observe each resolved hit or final damage; needs resolved event + per-source reaction. `B/D`. | 2/1; Mug preset with qualifier and rate. |
| 2 | Yanfly Regen Scroll / engine HRG | Tick HP regeneration and let multiple sources compose, including a 2x source. L regeneration; V regen amount/rate; R holder,sources; I calculation; Q heal; M optional streak; P each contributor; C heal reactions; S actor/enemy. | `A` HRG sums only as one fixed query and flow applies it; no generic channel or provenance. Needs `regen` calculation channel. `B`. | 3/2; HP Regen preset plus modifier row. |
| 3 | Yanfly Leech Seed / lifesteal | Damage target and heal source from the authoritative damage result, with caps and bypass rules. L after damage; V finalDamage/heal; R source,target; Q heal; P action source; C healing reactions; S symmetry. | `A` `hp_drain` handles skill-local drain, not arbitrary passive reaction. Needs event fact and reaction. `B`. | 3/3; Lifesteal preset. |
| 4 | Yanfly Thornmail / counter | On received qualifying damage, issue retaliation against attacker, often after hit. L after damage; V finalDamage; R target,lastAttacker; Q damage; P state/equipment; C counter chains; S both sides. | Current phase cannot bind last attacker per hit. Needs event refs + chain lineage. `B/D`. | 2/2; Counterattack/Thorns preset. |
| 5 | Yanfly Magic Guard | Redirect a percentage of pending HP damage into available MP; damage remaining commits to HP; remove source when MP is exhausted. L before damage; V pending amount,ratio,availableMP; R target,source; I redirect/convert; Q state removal; M none; P state instance; C MP event may trigger; S actors/enemies. | No typed pre-damage transform or per-battler MP in current effect path. `C` resource redirect primitive. | 1/2; Damage-to-MP preset. |
| 6 | Yanfly Undead | Convert healing to damage and damage to healing, with explicit action/effect bypass. L before heal/damage; V amount,kind,bypass; R source,target; I convert; Q resulting event; M none; P state/action; C conversion must not ping-pong; S both. | Needs typed transition conversion and nonrecursive bypass tag. `C/D`. | 1/2; Undead conversion preset. |
| 7 | Yanfly Guts / fatal clamp | When pending damage would kill, clamp HP to 1 under condition and mark once-per-battle use. L before death; V pending,HP; R target; I clamp; M used flag; P passive/state instance; C clamp suppresses death; S both. | Current execution/death ward is bespoke end-of-battle behavior, not a generic damage interceptor. `C`. | 2/2; Guts preset. |
| 8 | Yanfly Phoenix Ring / death ward | Intercept lethal/death transition, restore HP, consume or break exact equipment instance. L before death or end-of-battle reap; V lethal,restore; R target,source equipment; I cancel/replace; Q revive; M charges; P concrete slot/item; C revive can trigger state events; S both. | `A` `ON_PERMADEATH` finds source at reap, but not ordinary battle death; needs typed death transition + instance mutation. `C/D`. | 2/2; Death Ward preset. |
| 9 | Yanfly Spell Shield | First eligible incoming spell/effect is cancelled, then shield source is removed. L before effect; V eligibility; R action,target,source; I cancel; M charges/once; P exact state; C cancellation must not trigger effect reactions; S both. | Barrier can reduce/cancel some domains but does not cover generic first eligible action/effect. `C`. | 2/2; Spell Shield preset. |
| 10 | VisuStella barriers | Multiple barrier kinds cancel, nullify, reduce, absorb, or disperse to MP/TP, consuming deterministic charges. L before damage/status; V amount,stacks,match; R action,target; I cancel/reduce/absorb/redirect; Q barrier consumed/removed; M stacks,duration; P barrier instance; C no loop; S both. | Current stack barrier covers a useful subset; MP/TP redirect and typed ordering remain gaps. `B/C`. | 4/3; Barrier family editor. |
| 11 | Yanfly Bide | State stores damage received over time and on removal deals 2x stored value to eligible enemies. L apply/respond/remove; V each finalDamage,stored*2; R holder,opponents; Q area damage; M stored value; P state instance; C damage can kill/trigger; S both. | Commands can model apply/remove, but no per-hit reaction/context or state-local variable. `C/D`. | 2/2; Stored Damage preset. |
| 12 | Yanfly Toxic | State-local counter increments every periodic tick and drives escalating damage. L state add/regeneration/expire; V counter,currentMaxHp; R state holder; Q damage; M counter; P exact state instance; C damage reactions; S both. | `STATE_TICKS` exists but no source-local mutable state exposed to authored commands. `C`. | 2/2; Escalating DoT preset. |
| 13 | Yanfly Mirror Move | Remember last performed skill/action and copy/force it against an appropriate target. L action start/end; V skill id,targeting; R holder,last user/target; Q forced/copy action; M lastAction; P state/passive; C forced copy recursion; S actor/enemy. | `FORCE_ACTION` is static, and commands lack action-history memory/copy semantics. `C/D`. | 1/2; Mirror/last action preset. |
| 14 | Yanfly dynamic skill cost | Cost formula depends on current HP/MP, state, history, or action context; usability and payment must agree. L availability/cost commit; V cost; R user,skill,target,history; I cost clamp/cancel; Q resource spent; M optional history; P skill/source modifiers; C no double payment; S both. | Formula charges exist, but no composable source/target cost modifiers or pending cost event. `B/C`. | 3/3; Cost formula + modifier stack. |
| 15 | Yanfly Skill Cost Mastery | Skill use count/mastery changes future cost or power. L action end; V useCount,cost; R user,skill; I cost calculation; Q record use; M per-skill mastery; P skill/actor; C no duplicate record; S both. | `RECORD_HISTORY` is generic-ish but not per-skill source-local memory. `C`. | 2/2; Mastery preset. |
| 16 | Yanfly limited uses / charges | Skill has per-creature charges; modifiers increase/decrease, spend one, or restore selected/all charges. L availability/payment/recovery; V charges; R user,skill; I cancel if unavailable; Q spend/restore; M per-skill charges; P creature instance; C restoration reactions; S both. | Current per-creature charges and restore effect are strong; dynamic trait modification is missing. `B/C`. | 4/3; Charges field + modifier. |
| 17 | Yanfly state replacement | Adding state A removes/replaces B or upgrades to C; replacement is deterministic and visible. L pending state add; V duration/stacks; R target,existing states; I replace; Q add/remove events; M stacks; P exact state instances; C replacement cascades; S both. | Current add/remove commands can sequence it, but no atomic pending state transition or instance identity. `C/D`. | 2/2; State replacement preset. |
| 18 | Yanfly target rewrite / Greed | Rewrite selected target based on source state before application, or redirect ally item to self. L target selection/pre-effect; V target; R original/current target,source; I retarget; Q effect on final target; M none; P redirecting state; C redirected effect can react; S both. | Target specs have sides/shapes/cover but no generic target transformer retaining original target. `C`. | 2/2; Redirect target preset. |
| 19 | VisuStella target eligibility / aggro | Filter/weight eligible targets by state, tags, target rate, or skill; AI and player must share legal set. L selection; V weights; R party/enemy groups; I selector filter; Q selected target; M none; P target-rate sources; C forced actions; S current AI actor/enemy divergence risk. | Current target rate and heal-lowest are partly hardcoded; selector predicates are not reusable. `B/C`. | 3/2; Selector/filter block. |
| 20 | Yanfly accuracy / always hit / force miss | Compose source, target, skill, and effect hit modifiers; allow explicit bypass. L calculation; V hit chance; R user,target,action; I force/cancel; Q hit/miss; M none; P source/action; C miss suppresses downstream reactions; S both. | HIT/EVA exist, but typed action-side bypass/force result is incomplete. `B/C`. | 3/3; Accuracy channel. |
| 21 | Yanfly critical vulnerability / critical effects | Modify critical chance or add state/effect on critical, based on resolved critical fact. L calculation + after hit; V crit chance/result; R source,target,action; Q state/effect; M once flags optional; P state/equipment; C crit reaction chains; S both. | CRI/CEV exist; generic post-critical reaction does not. `B`. | 4/3; Critical reaction preset. |
| 22 | Yanfly state success/resistance | Compose inflicter success and target state/category resistance, with immunity distinct from rate. L state calculation/intercept; V chance; R source,target,state/category; I cancel on immunity; Q state added/failed; M none; P each source; C state add reactions; S both. | Current registry is already strong (`STATE_RATE`, categories, immunity); generic state event still useful. `A/B`. | 5/4; State susceptibility preset. |
| 23 | Yanfly duration stacking / turn reset | State duration or buff/debuff turns are added, capped, refreshed, or reset by a source. L state add/refresh/tick; V duration/stack cap; R target,state; I replace/merge; Q state changed; M duration/stack; P instance; C expiry reactions; S both. | State model has duration/ticks but not general composable duration calculation. `C`. | 3/3; Duration policy preset. |
| 24 | Yanfly Absorb Ailments | Convert incoming states into healing/benefit or absorb only selected categories. L before state add; V state/category; R source,target; I cancel/convert; Q resource/state result; M charges optional; P target state; C conversion can trigger reactions; S both. | Immunity covers only cancel; conversion needs typed state interceptor. `C`. | 2/2; Ailment absorption preset. |
| 25 | Yanfly Healing Link / Echo of Light | When target receives direct healing, a linked source receives follow-up or delayed healing. L after heal; V final healing; R healer,target,linked owner; Q heal/future state; M duration/once; P link applier; C heal->heal chain must be bounded; S both. | Current commands can manually sequence but cannot observe arbitrary heals. `B/D`. | 2/2; Healing link preset. |
| 26 | Yanfly Mana Burn | Damage MP, then compute HP damage from actual MP loss. L pending/resource commit/after; V MP spent,derived HP; R source,target; I resource clamp; Q HP damage; M none; P action; C damage reactions; S both. | Shared Summoner MP is not a generic battler resource transition; needs resource domain fact. `C/D`. | 2/2; Resource conversion preset. |
| 27 | Yanfly Spirit Shackles | While state active, action by holder spends MP or receives penalty; original applier may matter. L action start/cost; V MP cost; R holder,action,applier; I cost addition/cancel; Q resource spent; M duration; P state applier; C cost event can disable action; S both. | Cost formula exists but state/action interception and applier provenance do not. `C`. | 2/2; Action tax preset. |
| 28 | Yanfly Power/Mind Charge | Store a one-shot multiplier classified by next physical/magical action, then consume it. L action calculation/end; V damage multiplier; R holder,action; I calculation; Q consume; M pending charge type; P state/passive instance; C no self-trigger; S both. | `PARAM_RATE` cannot target “next action”; needs action-local state and channel. `C`. | 2/2; Charge-next-action preset. |
| 29 | Yanfly Elemental Exposure | On elemental hit, add/stack target vulnerability to that element for later actors. L after damage/state; V element,stack/rate; R attacker,target,element; Q state/modifier; M stacks; P state applier; C damage->state; S both. | Elements/rates exist, but resolved element event and stack policy are absent. `B/C`. | 3/3; Exposure preset. |
| 30 | Yanfly Adapting Armor | On received elemental hit, grant resistance to the received element. L after damage; V element,rate,duration; R target,action; Q state add/replace; M stack/duration; P equipment source; C subsequent modifier only; S both. | `ADD_STATE` can be scripted from a phase but cannot react per hit or carry event element. `B/C`. | 2/2; Adaptive resistance preset. |
| 31 | Yanfly Death Mark / Zed-like expiry | Apply a mark, remember damage/HP relationship, and detonate on expiry. L state add/damage/expire; V stored/HP delta; R applier,target; Q damage; M stored value/duration; P mark instance; C detonation chain; S both. | State ticks exist, but local memory, applier, and expiry reaction do not. `C/D`. | 2/2; Mark/detonate preset. |
| 32 | Yanfly Stockpile / Swallow / Spit Up | Repeatedly stack a typed charge, consume it for a formula, or release it to targets. L action/use; V stacks,power; R holder,target; I availability; Q damage/heal; M stacks; P state instance; C release can react; S both. | Commands can set variables only in flow context, not instance-local skill state. `C`. | 2/2; Stack/consume preset. |
| 33 | Yanfly Share Life / Cup of Life | Equalize HP percentages or distribute excess healing across selected allies. L before/after healing; V HP ratios,excess; R group,source,target; I redirect excess; Q multiple heals; M none; P healer/skill; C heal chains; S both. | `FOR_EACH` and formulas can approximate fixed groups, but no atomic group snapshot or excess fact. `C/D`. | 2/2; Group redistribution preset. |
| 34 | Yanfly Victory Cry / reward modifier | On victory, restore resource or alter reward based on contributor/source. L victory/reward; V gold,XP,resource; R party,killer,enemy; I reward modifier; Q recovery/reward; M none; P active source; C reward reactions; S party/enemy only as applicable. | Current victory flow and GOLD_DIGGER/XP_RATE are good A-class examples; per-killer reward reactions need context. `A/B`. | 5/4; Victory Heal/Reward modifier. |
| 35 | Yanfly Beast Boost / kill stat buff | On kill, identify highest eligible stat and grant temporary boost. L kill/after action; V kill result,stat; R killer,target; Q state/buff; M tie-break/stack; P killer source; C kill->buff; S both. | KILL_MP_RESTORE is bespoke; generic kill event plus max-selector needed. `B/C`. | 2/2; Kill reward preset. |
| 36 | Yanfly Blue Magic / learn-on-hit | If a source is hit by an eligible skill, teach the skill or record it. L hit/after action; V skill id; R target,action; Q learn skill; M learned set; P target ability; C learning not a battle reaction loop; S actors/enemies differ in “learn” capability. | `learn_skill` exists, but no resolved action skill fact or capability selector. `C`. | 2/2; Learn-on-hit preset. |
| 37 | Yanfly Enemy Thieves / Poach | Kill by a qualifying source changes drops or grants an item, preserving killer provenance. L kill/reward; V drop table; R killer,enemy; Q item reward; M none; P killer skill/passive; C reward chain; S enemy target only. | Reward commands exist, but kill provenance and drop rewrite are missing. `C`. | 2/2; Poach/Mug-like reward preset. |
| 38 | HimeWorks Counter After Hit / Elemental Negation | Counter occurs after the incoming hit; elemental negation removes only elemental component. L hit ordering/intercept; V final damage/element; R attacker,target; I reduce/negate; Q counter; M none; P state/trait; C counter loop; S both. | Current barriers cover reduction but not counter-order contract or per-component fact. `B/C/D`. | 3/2; Counter timing and element filter. |
| 39 | HimeWorks state replacement/progressive states | Adding one state removes another; automatic removal adds the next state. L add/remove/expire; V state ids,duration; R target,state,applier; I replace; Q state events; M progression; P state instance; C chains; S both. | Ordinary commands can encode a fixed sequence; atomic state transition and source identity remain absent. `B/C`. | 3/3; State progression preset. |
| 40 | Victor Engine retaliation / reflect / death counter | A trait or state reacts to damage or lethal hit with retaliation, reflect, or a last action. L after hit/before death; V final damage; R attacker,target,action; I reflect/cancel; Q action/damage; M charges/once; P source instance; C loops; S both. | Confirms that “counter” spans both Q and I; current fixed traits are not enough. `C/D`. | 2/2; Counter/Death Counter presets. |
| 41 | Olivia battle effects / follow-up and target scope | Follow-up action, extra skill list, changed scope, reward, and turn stacking are authored on database objects. L action end/selection; V scope/turns; R source,target,skill; I target rewrite/availability; Q follow-up; M once/turn; P skill/state; C forced-action recursion; S actor/enemy failures are common. | Action sequences and force action are useful A/B bases; action-copy lineage and scope transformer remain gaps. `B/D`. | 3/2; Follow-up and scope presets. |
| 42 | Community MV→MZ ports / actor-enemy asymmetry | Same gameplay sentence must work on actors and enemies despite different command/turn/action paths. L all; V all; R battler side and origin; I/Q/M/P as mechanic requires; C port-specific recursion; S explicit requirement. | Current targeting has an AI branch and several flows iterate allies only; architecture must test both sides. `D`; no convenience primitive fixes authority split. | 2/2; symmetry fixture dimension, not a preset. |

## Capability results and current Second Rite comparison

The A-class successes are deliberately ordinary: victory heal, reward
modifiers, state rate/category immunity, parameter/element rates, simple
charges and restoration, explicit barrier grant, action sequences, and phase
events. They work because the current JSON already owns a stable phase, a
registered command/effect, and a formula context that does not need to infer a
past transition.

The recurring B-class group is larger than the current trait registry suggests:
post-battle recovery, kill rewards, critical reactions, lifesteal, follow-up
actions, and many state behaviors need no new domain law once a reaction can
read an immutable resolved event and issue ordinary commands.

C is concentrated in a few reusable additions: a typed calculation channel;
pending transition operations; action/skill/resource event facts; state-local
memory; applier/source references; group selectors; and deterministic charges.
D is not “hard mechanic” in general. It appears where ownership or ordering is
authoritative: death versus end-of-battle reap, resource conversions, forced
action copies, conversion ping-pong, group atomicity, and actor/enemy execution
paths. E was not needed for the sampled combat corpus; renderer-only or
subsystem-specific mechanics should still remain out of scope.

### Frequency signal

Across the 42 specimens, the strongest recurring families were:

- resolved damage/heal facts and attacker/target/action references: 20+;
- pending damage/effect/state/cost interception: 17+;
- source-local counters, stacks, charges, once flags, last action, or duration:
  16+;
- deterministic target/group selectors and original/current target identity:
  11+;
- provenance/applier/equipment-instance ownership: 13+;
- reaction chains and loop prevention: 15+;
- explicit actor/enemy symmetry: 10+.

These counts are corpus-family counts, not a claim that every plugin uses the
same implementation. They are enough to reject a design that only adds more
after-phase commands.

## Candidate minimum vocabulary for #308

### Lifecycle facts

Use domain names only where a distinct semantic timing recurs. The minimum
candidate set is:

`action_started`, `cost_pending`, `target_pending`, `effect_pending`,
`damage_pending`, `healing_pending`, `state_pending`, `death_pending`,
`resource_pending`; then `action_hit`, `damage_resolved`, `healing_resolved`,
`state_added`, `state_removed`, `state_expired`, `resource_spent`,
`resource_recovered`, `killed`, `death_prevented`, `action_finished`,
`regeneration`, `round_started`, `round_ended`, `battle_started`,
`victory`, `escape`.

This is a candidate event vocabulary, not a mandate to expose 25 independent
plugin hooks. Several can share typed transitions and event filters. The
important distinction is before/after and typed domain, not callback count.

### Modifier/calculation channels

Start with channels demonstrated repeatedly: `damage.amount` (with kind,
element, direct/indirect, cover/interceptable); `healing.amount` (direct,
regen, overheal, bypass); `regeneration.amount`; `critical.chance` and
`critical.damage`; `hit.chance`; `state.success` and `state.duration`;
`execution.threshold`; `resource.cost` and `resource.recovery`; `charges`
per skill; `target.weight`/eligibility; `reward.gold`/`xp`; and `barrier`
matching/strength. Each channel needs declared subject (source, target, action,
or group), operation (add, multiply, clamp, replace), and composition order.

### Pending-transition operations

The corpus supports a small generic set: `cancel`, `clamp`, `reduce`,
`amplify`, `redirect(resource|target)`, `convert(kind)`, `replace`,
`retarget`, `consume_charge`, and `bypass(tag)`. These must operate on typed
pending records, not arbitrary Lua tables. “Convert” needs a declared source
and destination domain and a nonrecursive/bypass policy; “redirect” needs the
remaining amount and original/current references preserved.

### Resolved event context

Every event should expose immutable facts only when applicable: event type and
lineage; source/target/originalTarget/currentTarget; action/skill/item; effect
kind; attempted and final amount; absorbed/redirected/converted amounts;
element/damage kind/cover tag; hit and critical result; state id/category,
duration and applier; resource kind, attempted and actual spend; charge id and
remaining count; kill/death result; and the concrete source/provenance handle.
“Final” must be written by the authority that committed it. A reaction must not
rerun a damage formula.

### Source-local memory

The smallest recurring operations are `read`, `write`, `add`, `multiply`,
`clamp`, `consume`, `reset`, `exists/once`, and `remember-last`. Storage scopes
need explicit lifetime: source instance, state instance, battler, action,
battle, or session. State/equipment/passive instance identity must be
preserved; loader data remains immutable. Charges and counters must be saved if
their lifetime crosses save boundaries.

### Selectors and references

Prefer a small composable vocabulary: `self/source`, `target`,
`original_target`, `current_target`, `action_user`, `last_attacker`,
`applier`, `neighbor`, `owner`, `source_instance`, `state_instance`,
`equipment_instance`, `all_living_allies`, `all_living_enemies`,
`lowest_hp`, `highest_hp`, `eligible`, `random_eligible`, and `same_element`.
Selectors should filter first, then order, then choose; they should never hide a
fallback random choice inside a “choose” operation.

### Provenance and ownership

The existing active-object order is a good base: innate, passives, equipment
slots, states, temporary/per-instance sources. Extend each contributor with a
stable source handle and authored order. A reaction that consumes/breaks/removes
its provider must receive that handle, not rediscover the first matching code.
State application must retain applier where a later mechanic needs it.

## Ordering, recursion, and cycles

The corpus contains useful chains and dangerous cycles. Do not globally ban
reaction-generated effects. Use a deterministic transaction context:

- assign an `origin_id` to the root action and a monotonically increasing event
  sequence within it;
- attach `parent_event_id`, source handle, reaction identity, and depth;
- process pending interceptors in declared domain order, then commit once;
- publish the resolved event, then enqueue reactions in active-source order and
  authored order;
- permit reaction-generated transitions to enter the same pipeline;
- suppress the same source/reaction identity when its guard says it already
  handled that lineage, with an explicit authored opt-in for legitimate repeat;
- reject formula dependency cycles at validation time and cap lineage depth as
  a final fault guard, with a loud diagnostic naming the chain.

Concrete hazards found: Thorns/counter can counter a counter; reflect can
reflect itself; Undead conversion can heal-to-damage-to-heal forever; a death
ward can trigger a revive reaction that re-enters death; a target rewrite can
create another pending effect; Mirror Move can copy itself; state replacement
can cascade while its source is being removed; equipment can destroy the
source currently iterating; and a modifier formula can depend on the derived
value it is helping calculate. The rules above preserve useful chains while
making lineage and cycle failure inspectable.

## Studio implications and presets

The current editor already uses registry-driven trait/effect forms and one
`renderCommandList` for map, common, scene, battle phase/troop, quest, and
action-sequence contexts. The correct extension is a source behavior section
that selects a typed lifecycle/filter and opens that same command list, with
schema-generated fields for channel, selector, memory scope, and guard. It is
not a second “passive script” editor and not a content-specific widget.

Named presets should compile to generic structures and remain inspectable:

- HP Regen: `regeneration.amount` contribution;
- Lifesteal: after `damage_resolved`, heal source by final amount or ratio;
- Counterattack/Thorns: after qualifying `damage_resolved`, issue damage to
  source with lineage guard;
- Guts: `damage_pending` clamp plus once memory;
- Death Ward: `death_pending` cancel/replace plus source-instance consume;
- Barrier: typed pending interceptor with match, operation, stacks, duration;
- Element Resistance: `damage.amount` multiplier filtered by element;
- Victory Heal: `victory` reaction;
- State Replacement: `state_pending` replace/merge policy;
- Dynamic Cost: `cost_pending` calculation contribution.

## What not to generalize

Do not import arbitrary JavaScript/Lua, unrestricted object-path mutation,
reflection, content-named trait codes, one lifecycle hook per plugin callback,
renderer/internal function names, or a universal `before_anything` event. Do
not make provenance optional, let hash iteration define gameplay order, or
permit reactions to silently infer authority from current state. Do not make
all values one additive rate: regen, damage, cost, duration, target weight, and
reward use different composition rules. Do not expose actor-only convenience
paths as generic semantics. Finally, do not make presets new runtime laws;
their output must be ordinary registered semantics.

## Mechanics still awkward after the minimum vocabulary

Group-wide HP equalization with atomic snapshots, full action copying with
complex target remapping, multi-resource conversion, and cross-battle mastery
remain higher-judgment features. They should consume the vocabulary but are not
good reasons to add unrestricted scripting. Renderer choreography, grid battle
geometry, and wholly new economy subsystems remain E/out of scope for this
benchmark.

## Recommended #308 authorability fixtures

Before migrating the trait registry, implement data-only fixtures for:

1. Mug: cover-respecting final damage to Gold, including multi-hit choice;
2. Regen plus a second source that doubles regeneration;
3. Lifesteal from final damage;
4. Thorns/counter with a counter-lineage guard;
5. Kill to Summoner MP and critical to state;
6. Magic Guard HP-to-MP redirect with insufficient MP;
7. Undead conversion with an explicit bypass;
8. Guts clamp and a consumable Death Ward that owns a concrete equipment slot;
9. Spell Shield first eligible cancellation and barrier cancel/reduce/absorb/
   redirect variants;
10. Toxic counter, Bide stored damage, and Mirror Move last-skill memory;
11. Dynamic skill cost plus modified/restored limited charges;
12. State replacement and target redirection, tested for actor and enemy;
13. One reaction-generated reaction chain that terminates and reports lineage.

Each fixture should prove: no new content-named Lua handler, no bespoke trait
code, no validator hardcode, no custom editor widget, deterministic ordering,
and symmetry where the sentence is not party-specific. The first ten are the
minimum review slice; the remaining three are the architecture pressure slice.

## Evidence-derived minimum architecture proposal for #308

This is a proposal, not implemented by this report.

1. Keep the current registry and provenance collector as the extension point;
   add behavior contributions to source objects rather than adding named trait
   codes for each sentence.
2. Introduce typed calculation contributions with declared channel, operation,
   subject, filter, and order. Make composition inspectable.
3. Introduce typed pending transition records for cost, target, damage,
   healing, resource, state, and death. Allow only registered operations.
4. Commit each transition exactly once and publish immutable resolved facts at
   the authority seam.
5. Attach source-filtered reactions to resolved facts and run them through the
   ordinary command/effect pipeline with lineage metadata.
6. Add source-local state with explicit scope and instance ownership; route
   persistence through the existing save system when scope requires it.
7. Validate selector domains, channel operations, formula dependencies,
   lifecycle filters, and reaction lineage statically; fail loudly.
8. Extend the existing registry-driven Studio form and shared command editor;
   compile friendly presets into the generic representation.
9. Make actor/enemy symmetry a fixture dimension and remove special-case AI or
   party-only paths from generic semantic primitives.

This is intentionally smaller than the plugin ecosystems: it captures their
recurring gameplay sentences, not their implementation surface area.

## Current-state evidence consulted

- `data/engine.json`: 42 trait codes, 93 commands, 17 effect types, 52 formula
  help tokens, and seven command contexts.
- `engine/traits.lua`: active-object order and `findAllSources` preserve source
  provenance for actor, passive, equipment, state, and Savor sources.
- `engine/effects_core.lua`: damage/healing/state calculations and several
  fixed trait queries; authoritative effect events are the right seam for
  resolved facts.
- `engine/resolved_event.lua`: immutable after-snapshots already exist, but
  the context is currently presentation-oriented and not a general reaction
  contract.
- `data/flows/battle.json` and `data/flows/exploration.json`: phase command
  lists already express victory, regeneration, adjacency, rewards, and
  movement behavior, but fixed trait codes are inspected by global flows.
- `tools/editor/js/events.js`, `entity-forms.js`, and `widgets.js`: command
  lists and trait/effect fields are registry/editor driven; no passive-specific
  command-list surface exists yet.

