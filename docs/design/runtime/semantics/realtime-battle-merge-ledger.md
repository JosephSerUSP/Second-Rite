# Real-time battle mode — merge ledger

Status: **owner-reviewed 2026-10-06; decisions O1–O5 recorded below.** Issue #1424, epic #1422.

## The condition this document exists to satisfy

The owner accepted building Parasite Eve–style real-time battle **beside**
production Battle (option B), only on the condition that it is designed to
**merge into production Battle later** (option A). This ledger is the evidence
for that. Every behaviour the PE Day 1 slice needs is listed with the
production owner it reuses, or, where it cannot, the divergence and how that
divergence merges. A row with no merge path is a defect in the design, not a
footnote.

Keep this ledger current in the same PR as any change to the real-time mode.

## Constraints that shape the design

- `engine/battle.lua` and `engine/scenes/battle.lua` are **owner-supervised**
  (AGENTS.md). The real-time mode calls their public methods and does not edit
  them. Any change it needs there is listed under *Owner decisions* and
  proposed as a separate, owner-reviewed patch.
- **One semantic authority** (AGENTS.md). HP, damage, costs, items, states,
  rewards and outcomes must come from the same code and data production Battle
  uses. B009's scene-local event program reimplements all of them and is
  exactly what this mode retires.
- **Battle phases are zero-SCRIPT flows** (G1). The real-time mode runs the
  existing phases and adds only the phases listed below.
- **Domain transitions happen exactly once.** The 3D presenter reads resolved
  events and never reconstructs a mutation.

## The seam

Production Battle is three separable things:

| Layer | Production today | Real-time mode |
|---|---|---|
| **Scheduler**: who acts when | `resolveRound` → `buildTurnQueue` (speed-ordered round) → `processRoundEnd` | **New** `engine/realtime_battle.lua`: fixed-step clock, AT gauges, positions, telegraphs, pause on command input |
| **Action resolver**: what one action does | `Battle:executeTurn(turn, events)`, `Battle:applyItem`: cost, cover, action sequence, `APPLY_EFFECT`, `battle.after_action`, victory/defeat | **Reused unchanged.** Every real-time action becomes one `executeTurn` call on a real `Battle` instance |
| **State and data**: battlers, skills, items, states, troops, flows | `Battler`, `GameSession`, `skills.json`, `items.json`, `states.json`, `troops.json`, `flows/battle.json` | **Reused unchanged.** Aya is a party actor and the rat a troop enemy |

So the merge (option A) is: **production Battle gains a second scheduler.** The
round queue and the real-time clock become two implementations of one
"decide who acts next" interface over the same resolver. Nothing downstream of
the scheduler forks.

## Ledger

Legend: **Reuse** = production owner used as-is · **Additive** = new registry
entry, token or field that production can adopt unchanged · **Divergence** =
behaviour production lacks, with its merge path · **Owner** = needs an owner
decision before implementation.

| # | B009 behaviour (scene-local today) | Production owner | Plan | Class |
|---|---|---|---|---|
| 1 | `hp` / `maxHp` | `Battler` vitality | Aya is a party actor in `units`; HP lives on her battler | Reuse |
| 2 | `ehp` (rat HP 20) | Troop enemy `Battler` | Rat is a unit in a troop; `Battle.new(session, troopEnemies)` | Reuse |
| 3 | Shot damage, closer is stronger | `APPLY_EFFECT` damage formulas | Weapon attack skill whose formula reads a new **distance token** (`x.battle.distance`, actor→target in world units) | Additive |
| 4 | Out of range: deterministic miss | Targeting / hit formulas | Hit chance as a formula over the distance token and the weapon's range. No scheduler-side gate, so the resolver stays the one authority | Additive |
| 5 | Range shapes (blue ground, green air) | — | Weapon data fields `range.ground` / `range.air`. Presentation reads them; the formula in #4 is the authority | Additive |
| 6 | AT gauge fills over time; act at 100 | `buildTurnQueue` orders by speed | Scheduler-owned gauge per battler, rate from the **same speed stat** the queue uses. **Divergence D1: time model** | Divergence |
| 7 | Command menu / aiming pause the fight | — (rounds are inherently paused) | Scheduler state; the clock does not advance while a player command is open | Divergence (scheduler-only, no merge cost) |
| 8 | Free movement, positions `px/py/ex/ey` | `formation` slots | Battle-scoped `battler.field = {x, y, facing}` owned by the scheduler. Whether mid-battle state must round-trip through `savegame.lua` is checked in implementation; if it must, `field` is saved like any other per-instance state | Divergence D2: spatial field |
| 9 | Ammunition (`ammo`, Ammo +6) | — (no ammo concept) | Ammo is inventory stock (`items.json`), consumed as the weapon skill's cost. Needs a **cost kind "item stock"** in `skill_cost` | **Owner** (O2) |
| 10 | PE pool and Heal 1 | `skill_cost` (charges / HP / Overcast; MP purged) | PE as a battler resource paying PE skills, regenerating over time | **Owner** (O3) |
| 11 | Medicine heals 30 and consumes stock | `Battle:applyItem` | Item in `items.json` with a heal effect; used via the resolver | Reuse |
| 12 | Rat wind-up, locks Aya's position, lunges | `getAIAction` + skill `warmup` (in rounds) | AI choice from `getAIAction`; telegraph duration is a seconds field on the skill; the scheduler resolves contact geometrically and calls `executeTurn` **only on contact** | Divergence D3: dodgeable attacks |
| 13 | Fire tail: 3 projectiles, each hits once | — | Projectile spawning is scheduler-owned; each contact is one `executeTurn` with a per-projectile hit flag | Divergence D3 |
| 14 | Dodged attack (no contact) | — | Scheduler publishes a resolved `miss` event; cooldown still starts (O4) | **Owner** (O4) |
| 15 | Escape (guaranteed today) | `flee` effect, `flee_success`, `battle.flee_attempt` | Reuse the production flee effect and its chance formula; drop the "guaranteed" prototype rule | Reuse |
| 16 | Victory: EXP 2, Ammo +6 once | `battle.victory` flow, troop rewards | Rewards authored on the troop; victory flow grants them once | Reuse |
| 17 | Defeat: fallen pose, retry | `battle.defeat` flow | Reuse; retry is a Project scene choice after the flow | Reuse |
| 18 | Per-action phase | `battle.after_action` flow | Run unchanged after every resolved action (boss phase changes need it) | Reuse |
| 19 | Round phases (poison ticks, cooldowns) | `battle.round_start` / `battle.round_end`, `skill_cost.tick` per round | Real-time "round" is a fixed authored number of scheduler ticks that runs the same phases. **Divergence D4: round as a tick count** | Divergence (O1) |
| 20 | Start of battle in the same room, no scene change | `battle.battle_start`; battle scene swaps screens | Scheduler runs `battle.battle_start` in place; the 3D presenter replaces `battle_view` for this mode | Divergence D5: presenter |
| 21 | Damage numbers, flashes, gauges | Battle feel (SPEC §2.3): smooth gauges, flashes, bouncing numbers | The 3D presenter reads resolved events and follows §2.3 | Reuse (rules) |
| 22 | Deterministic tests | G2 battle-log fixtures | Fixed-step clock + seeded battle RNG ⇒ byte-identical logs; real-time fixtures join `goldenBattles.json` | Additive |

## Divergences and their merge paths

- **D1 Time model.** Production schedules by round order; real-time by gauge
  fill. Merge: a `scheduler` interface (`next actor(s)`, `advance(dt)`) with
  `round` and `realtime` implementations, chosen per troop or per Project.
  Both read the same speed stat.
- **D2 Spatial field.** Production uses formation slots. Merge: `field` becomes
  an optional battler property; slot-based battles leave it nil. Targeting
  and formulas that read distance fail loudly when it is nil, never default.
- **D3 Dodgeable attacks.** Production resolves every chosen action. Merge: an
  action may carry a *delivery* (instant / telegraphed contact / projectile).
  `instant` is today's behaviour; the resolver is unchanged because delivery
  only decides **whether and when** `executeTurn` runs.
- **D4 Round as tick count.** Merge: the `realtime` scheduler emits a round
  boundary every N fixed-step ticks, so every round-scoped rule (state ticks,
  cooldowns, warmups) keeps one meaning.
- **D5 Presenter.** `battle_view` stays the round-mode presenter. The in-room
  3D presenter is a second consumer of the same resolved events.

## Owner decisions (2026-10-06)

- **O1 Rounds: decided, ticks rather than time.** A real-time round is a fixed,
  Project-authored number of scheduler ticks, not seconds. Every round-scoped
  rule (state ticks, `TICK_SKILL_TIMERS`, warmups) keeps one meaning, and
  determinism depends only on the tick count.
- **O2 Ammo: approved.** `skill_cost` gains an item-stock cost kind. Ammo is
  ordinary inventory spent as the weapon skill's cost; it is production-usable.
- **O3 PE: decided, "PE is a renamed, slightly mechanically different MP".**
  MP here is the session pool (SPEC §1.11) and §1.20 forbids per-skill MP
  costs; the only skill→MP path is Overcast with `"charges": 0`. Since Aya is
  the whole party, the session pool is her pool. **Interpretation taken
  (overrulable):** PE skills use the existing Overcast-only shape
  (`charges: 0`, `overcast.mp: N`); the Project's terms rename MP→PE and the
  Overcast wording; in-battle PE regeneration is a data step in the Project's
  `battle.round_end` flow. This needs no production change and keeps one MP
  authority. The alternative, a per-Project opt-out of the §1.20 `mpCost` ban,
  is a SPEC change and is not taken without the owner.
- **O4 Dodged attacks: yes.** A dodged attack still starts its cooldown,
  through the same `skill_cost.startCooldown` that `executeTurn` uses.
- **O5 Seam: approved.** The real-time mode drives a real `Battle` through
  `executeTurn` / `applyItem` without editing `engine/battle.lua`. Any change
  a supervised file needs comes to the owner as its own patch.

Ledger rows updated accordingly: #9 (O2) and #10 (O3) move from *Owner* to
*Additive* and *Reuse* respectively; #14 (O4) is *Divergence, decided*.

## Out of scope for M1

Weapon customisation, bonus points, levelling curves (M3); bosses and
multi-part targets such as the alligator's head and tail (M5); rooms and
encounter zones (M2). The ledger grows when those arrive.
