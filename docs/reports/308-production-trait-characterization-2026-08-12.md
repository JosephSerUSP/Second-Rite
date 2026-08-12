# #308 production-trait characterization — 2026-08-12

This report records current behavior before any #308 migration. Repository
facts come from the live Lua/data paths and the focused tests added in
`tests/test_trait_characterization.lua`; statements labelled inference or
proposal are not current architecture commitments.

## Scope and evidence

The selected set is the smallest useful cross-section of the current families:

- `KILL_MP_RESTORE`: resolved kill reaction with a shared Summoner resource.
- `BATTLE_START_DAMAGE`: battle-start reaction assembled from a party trait and
  troop event data.
- `POST_BATTLE_HEAL` plus `GOLD_DIGGER`: victory lifecycle reaction and reward
  aggregation, showing two different consumers of party traits.
- `MOVE_HEAL`, `SYMBIOSIS`, `PARASITE`, and `RECOVERY_XP_BONUS` already have
  focused coverage in `tests/test_permadeath_wards.lua`.
- `ON_PERMADEATH` has source/provenance, charge, priority, save/load, and reap
  coverage in `tests/test_permadeath_wards.lua`.
- `BARRIER_GRANT` has lifecycle, stack, duration, matching, and interception
  coverage in `tests/test_barriers.lua`.

The new tests assert gameplay results and event ordering, not named Lua helper
calls. No authored JSON, registry entry, golden, or gameplay implementation
was changed.

## Characterized mechanics

### `KILL_MP_RESTORE`

- **Current semantic family (fact):** resolved-event reaction / temporal
  behavior.
- **Current source/discovery path (fact):** `data/units/diablos.json` authors
  passive `reaper`; `data/passives.json` gives it `KILL_MP_RESTORE = 12`;
  `engine/traits.lua` discovers the active source; `engine/effects_core.lua`
  calls `awardKill` after lethal HP damage or successful Execution.
- **Observable contract (fact):** a qualifying lethal hit restores the authored
  flat amount to `session.mp`, capped by `session.maxMp`, and emits one
  `kill_mp_restore` fact with the applied delta. A non-lethal hit does not.
- **Ordering dependencies (fact):** damage commit, then death/kill
  determination, then MP restoration. The reaction must not restore before the
  target is known to be killed.
- **Provenance/state needs (fact):** the killer battler is required; the
  passive source itself has no mutable state. The Summoner MP pool is shared
  session state. Enemy/ally symmetry is present in the effect path because the
  killer is an arbitrary battler.
- **Recommended future #308 primitive (proposal):** a resolved `kill` reaction
  with a typed target/result context and a registered resource-change command.
- **Migration difficulty (inference):** medium. The kill fact and resource
  target are clear, but #308 still needs final reaction ordering, lineage, and
  source precedence.
- **Unresolved decision:** do not freeze global source ordering or reaction
  lineage from this fixture.

### `BATTLE_START_DAMAGE`

- **Current semantic family (fact):** lifecycle reaction, partly data-driven.
- **Current source/discovery path (fact):** `shadow_stalker` authors passive
  `battleStartDamage`; `data/passives.json` supplies the numeric value;
  `data/troops.json` owns the inherited `ambush` event; the
  `battle.battle_start` flow runs `SPAWN_ENEMIES`, then the troop event. The
  event reads `party.trait.BATTLE_START_DAMAGE`, iterates living enemies, and
  guards `v.hit` so only the first is damaged.
- **Observable contract (fact):** after enemies exist, one first living enemy
  receives the authored ambush damage; later enemies are untouched.
- **Ordering dependencies (fact):** spawn must precede the troop event; the
  trait aggregate must be read before the guarded iteration; this happens
  before normal battle actions.
- **Provenance/state needs (fact):** current discovery is aggregate party
  trait access, not a concrete source callback. The temporary `v.hit` local is
  per battle-start execution. The current authoring is party-oriented and is
  not demonstrated as an enemy-side symmetric reaction.
- **Recommended future #308 primitive (proposal):** a battle lifecycle hook
  with an explicit eligible-target selector and ordinary damage command.
- **Migration difficulty (inference):** medium-high. It depends on preserving
  troop suppression/inheritance and target-selection semantics, not just
  translating a trait code.
- **Unresolved decision:** whether this belongs to a source-local reaction,
  troop event, or a composed lifecycle preset remains open.

### `POST_BATTLE_HEAL` and `GOLD_DIGGER`

- **Current semantic family (fact):** `POST_BATTLE_HEAL` is a victory reaction;
  `GOLD_DIGGER` is a reward calculation contribution. Together they are a
  mixed family rather than one interchangeable reaction shape.
- **Current source/discovery path (fact):** `high_pixie` authors
  `postBattleHeal`, and `ghoul` authors `goldDigger`; both are discovered by
  `engine/traits.lua`. `data/flows/battle.json` reads the party gold trait in
  `GAIN_GOLD`, then iterates living allies and runs `HEAL` with the
  `POST_BATTLE_HEAL` trait.
- **Observable contract (fact):** victory adds the party reward once, including
  the summed `GOLD_DIGGER` value; each living carrier receives its own authored
  post-battle heal and unrelated party members do not.
- **Ordering dependencies (fact):** reward grant and per-carrier XP/heal occur
  before `REAP_FALLEN`; dead/reaped members are not living heal targets.
- **Provenance/state needs (fact):** gold is party aggregate state; healing is
  carrier-local. No mutable source-local state is currently used.
- **Recommended future #308 primitive (proposal):** keep reward modifiers as a
  calculation channel and represent victory healing as a resolved lifecycle
  reaction; do not force both into one API merely because both occur at victory.
- **Migration difficulty (inference):** low-medium for the heal, medium for the
  reward contribution. Reward calculation composition and source precedence are
  still unresolved in #308.
- **Unresolved decision:** whether reward modifiers share the same source
  ordering/provenance model as reactions must wait for #308/#309 design work.

### Existing coverage: `MOVE_HEAL`, `SYMBIOSIS`, `PARASITE`,
`RECOVERY_XP_BONUS`, `ON_PERMADEATH`, `BARRIER_GRANT`

These are intentionally not duplicated here. Current tests establish that
`MOVE_HEAL` runs on `exploration.step` and clamps at max HP; `SYMBIOSIS` and
`PARASITE` use adjacent living-party references and safely no-op without a
neighbour; `RECOVERY_XP_BONUS` runs at the recovery site; `ON_PERMADEATH`
selects concrete sources with mode priority and source-local charges that
round-trip through saves; and `BARRIER_GRANT` creates encounter-local,
triggered, stack/duration-limited interception state. Those facts make them
important future fixtures, but adding a second assertion surface would not add
material evidence in this bounded task.

## Migration readiness

### Ready for bounded migration

- `POST_BATTLE_HEAL`, provided the migration preserves living-carrier timing,
  max-HP clamping, and the existing victory/reap boundary.
- `MOVE_HEAL`, subject to preserving the exploration-step host and its ordinary
  `HEAL` semantics.

### Needs one primitive first

- `KILL_MP_RESTORE`: needs a stable resolved kill fact plus resource-reaction
  ordering.
- `BATTLE_START_DAMAGE`: needs a lifecycle hook/target-selection primitive that
  can preserve troop inheritance and suppression.
- `SYMBIOSIS`, `PARASITE`, and `RECOVERY_XP_BONUS`: need explicit lifecycle and
  reference context in the eventual authoring representation.

### Do not migrate yet

- `ON_PERMADEATH`: final pending-death/interceptor semantics, source precedence,
  and lineage/cycle policy remain unresolved.
- `BARRIER_GRANT`: its encounter-local mutable state and pending-transition
  interception shape should not be frozen before the #308 design decisions.
- `GOLD_DIGGER`: reward-modifier composition and global source precedence are
  unresolved; migrating it now could accidentally define those decisions.

## Explicit non-goals

This change does not route production traits through `hpDamageParticipants`,
create a universal reaction registry, generalize `damage_transition.lua`, move
Execution, change Battle/Scene lifecycle, add a data schema, or recapture any
golden. The #332 observation that ordinary HP damage must remain distinguishable
from downstream Execution is recorded as a constraint for future work, not
implemented here.
