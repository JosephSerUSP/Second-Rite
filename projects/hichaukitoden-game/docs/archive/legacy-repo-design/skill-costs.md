# Skill costs: Charges, Overcast, Cooldowns, Warmups, Conditions

*Design intent, 01.08.2026. Not a status document — see `docs/ENGINE-STATE.md`
for what exists and `docs/SPEC.md` for reviewed engine behavior.*

## 1. The problem with MP costs

MP is **the Summoner's shared pool** (`session.mp`), not a per-creature bar. It
prices the *expedition*: walking, prolonged combat, and summoner-scale decisions
all compete for the same strategic reserve.

A per-skill `mpCost` charged against that pool would mean every heal a creature
casts is spent out of the party's remaining walking distance. It also gives
every caster the same wallet, so a creature's own magical stamina disappears:
two Pixies and one Bahamut draw from one number.

Accordingly, per-skill MP values are not part of this cost model. Per-creature
charges own ordinary ability supply, while shared MP is reserved for
**Overcast** (§3.3), the one skill-cost path allowed to reach the Summoner's
pool. Overcast must be expensive enough to feel like spending the party's road
home.

## 2. Two cost families, one selection rule

| Family | Resource | Feel |
|---|---|---|
| Magic | **Charges** — a per-skill, per-creature counter refilled at Rest | "How many more times today?" |
| Physical | **Availability** — cooldown, warmup, and conditions | "Can I do it *this turn*?" |

Both answer the same question the battle menu asks — *is this row selectable,
and if not, why?* — so both resolve through **one** `canUseSkill` authority
shared by:

- the player battle command submenu;
- enemy/AI action selection, so one rule binds both sides;
- out-of-battle skill readouts that need to explain availability.

A skill a creature knows is never hidden merely because it is unusable. It is
shown disabled with its reason, because a row that vanishes teaches nothing and
looks like missing content.

## 3. Magic: Charges and Overcast

### 3.1 Charges, and what MDF really is

The RPG-Maker-compatible stat names carry broader design meanings:

- `mat` is **INT** — how hard a spell hits;
- `mdf` is **SPR** — the spirit's depth: how much magic a creature can hold;
- `def` is **VIT** — the body's resilience, not just an armour number.

Charges are where SPR stops being only mitigation and becomes an identity. A
magic skill declares a **charge formula**, not a flat number:

```json
"charges": "4 + b.base.mdf / 4"
```

Evaluate against the caster, floor the result, and clamp to a minimum of 1
except for a literal `0` (§3.3). Max charges therefore rise with base SPR while
the authored skill row still controls the starting scale.

This produces two caster archetypes from one rule:

| Statline | Result |
|---|---|
| High INT, low SPR | devastating, few castings, vulnerable to magic — a **nuke you must ration** |
| High SPR, low INT | modest damage, deep supply, strong magic resilience — **attrition** |

The glass cannon is worse on several endurance axes at once; Overcast is its
escape hatch. A very high-SPR creature may eventually have functionally ample
castings and little reason to Overcast, while an INT-heavy caster keeps paying
for burst through the Summoner's strategic pool. **That divergence is the
design, not a leak to cap.**

**Do not derive charges from a spell's potency.** Welding potency to supply
means every damage balance nudge silently changes economy. The base charge
formula is authored per skill — for example `1 + b.base.mdf / 12` for a large
spell and `6 + b.base.mdf / 4` for a cantrip. The author sizes it; SPR scales it.

### 3.2 Charges are creature state

Charges belong to the **individual creature**, keyed by skill id:

```lua
battler.charges = { windBlade = 3, soothingMote = 5 }
```

Two creatures knowing Wind Blade have independent pools, and one creature's Wind
Blade and Soothing Mote do not share. Charge state must serialize with the
persistent creature; loader definitions remain immutable shared data.

An absent per-skill charge key resolves as full. Missing instance state must not
turn a newly constructed or migrated creature's known spell into an empty pool.

### 3.3 Overcast

A magic skill at zero charges may be **Overcast**, paid out of the Summoner's MP:

```json
"charges": "4 + b.base.mdf / 4",
"overcast": { "mp": 120 }
```

The cost is deliberately steep relative to traversal. Using a 3000-MP opening
budget as a balance target, a handful of Overcasts should visibly shorten the
expedition — *this fight, or the walk home.*

Rules:

- Overcast is offered only at **zero charges**. It is never an alternative to
  spending an available charge.
- The battle menu shows Overcast as the row's cost at zero charges and disables
  it when `session.mp` is insufficient.
- Absent `overcast` means the skill cannot be cast at zero charges.
- **Enemies never Overcast.** They have no Summoner and no shared expedition MP
  pool; at zero charges they are out of that spell.
- Charge spending and Overcast MP spending belong to one skill-use resolution
  seam so the two paths cannot drift.

**Overcast-only skills** use a charge pool that is permanently empty:

```json
"charges": 0,
"overcast": { "mp": 400 }
```

No second code path is required; such a skill always enters the zero-charge
branch. Dragon-family **Breath** attacks are a natural use of this shape. A
high-MPD dragon is an expensive passenger, and its signature move bills the
Summoner again in the same expedition currency at the moment of use. A dragon
is not a creature you own; it is a creature you finance.

Consequence, accepted deliberately: an enemy cannot use an Overcast-only Breath.
Enemy Breath should be a separate skill row or troop-authored event rather than
a special case that grants enemies a fake Summoner pool.

### 3.4 Rest

**Rest fully restores charges** for every persistent creature in party, reserve,
and storage. Rest is expressed through the shared recovery event primitive
rather than a new subsystem; charge refill belongs to the same operation that
owns full party recovery.

That gives one authoring rule for town recovery and dungeon rest sites: invoke
the same recovery command and gate the event however the content requires.

**Promotion is a rest.** It is rare, rebuilds the creature, and belongs to the
same ritual economy as summoning. **Level-up is not**; raising max charges does
not refill what has already been spent.

Partial restores use an item/effect channel rather than a bespoke command:

```json
{ "type": "restore_charges", "amount": 2 }
{ "type": "restore_charges", "skill": "windBlade", "amount": "all" }
```

`amount: "all"` is the full-rest case. Item usability must reject a charge
restore when it would restore nothing, just as other restorative effects reject
waste where the system promises that behavior.

Charges do **not** regenerate per turn or per battle. Persisting across fights is
the point: the resource that makes a dungeon run a run.

## 4. Physical: Cooldown, Warmup, Conditions

These are **availability gates**, not currencies. All three are declared on the
skill and resolve through the same skill-usability predicate.

They are deliberately not stat-scaled, and the physical family deliberately
does not mirror the magic family. Making DEF shorten cooldowns for symmetry
would make VIT a super-stat. Physical skills are gated by *situation*, magic by
*supply*.

### 4.1 Cooldown

```json
"cooldown": 3
```

Turns that must pass after use before the skill becomes available again.
Cooldown ticking belongs to the authored round-end battle flow rather than a
second host-side timer path.

### 4.2 Warmup

```json
"warmup": 2
```

Turns from the **start of a battle** before the skill becomes available. A
finisher that unlocks on round 3 needs a number rather than a private state
machine.

Warmup and cooldown are independent and may differ: a skill can take four rounds
to unlock and then be usable every round, or unlock late and remain slow.

### 4.3 Conditions

```json
"condition": "a.hp >= a.maxHp"
"condition": "state:blind"
```

Conditions reuse the engine's shared condition grammar: formula expressions plus
registered/prefixed condition forms. State-based gating belongs in that same
grammar rather than a skill-private parser.

A failing condition needs an **authored reason string**, because a formula cannot
produce readable UI text:

```json
"condition": "a.hp >= a.maxHp",
"conditionText": "Only at full HP"
```

Missing `conditionText` is a validation failure. An unexplained grey row is a bug
report waiting to happen.

### 4.4 Battle-scoped state

Cooldown and warmup counters are **battle-scoped**, not persistent. Discard them
at battle end; do not write them into save data. Charges answer “how much is
left of the day”; cooldowns answer “what can I do this turn?” Different
lifetimes imply different owners.

## 5. Base stats vs final stats

**Base stats say who the creature is; final stats say how hard it is to hurt
right now.** Economy and resistance read the first; damage reads the second.

Charge and resistance formulas need `b.base.<param>` access backed by the same
base-parameter calculation used before equipment/state/passive `PARAM_PLUS` and
`PARAM_RATE` modifiers. Final `b.def` / `b.mdf` remain the modified combat
values.

Three consequences justify the rule independent of flavour:

1. **Equipment cannot buy charges.** An accessory granting +30 MDF may improve
   magic defense; it does not hand out castings.
2. **A debuff cannot strip max charges mid-fight.** Otherwise a `PARAM_RATE`
   debuff could shrink a maximum beneath the spent/current bookkeeping.
3. **Unequipping in a dungeon cannot shift max charges** under the creature's
   feet.

## 6. Defensive stats do more, and hit less hard

Giving DEF and MDF jobs beyond mitigation means mitigation should be worth
proportionally less.

### 6.1 Ailment resistance from base DEF/MDF

The intended state-infliction grammar is multiplicative through state and
category rates. Base DEF/MDF resistance joins that grammar as another
multiplicand rather than inventing a parallel resistance subsystem:

```text
physical category rate ×= f(base DEF)
magical / mental rate  ×= f(base MDF)
```

`f` is authored as a formula so the curve is a data knob. DEF expresses bodily
resilience (Poison, Paralysis, Blind); MDF expresses spiritual resilience
(Sleep, Charm, Confusion) and also carries charge capacity.

### 6.2 The damage coefficient is a separate balance change

If defense mitigation uses the form:

```text
potency × power² / (power + defense)
```

then weakening defense is one coefficient:

```text
potency × power² / (power + defense × k)
```

`k` belongs in authored/system balance data. Treat that coefficient adjustment as
a separate balance change from the cost model: it moves every damage number at
once, so combining the changes would make behavioral verification unable to
attribute a diff to one mechanic. Any golden regeneration caused by such a
balance change remains owner-signed per repository policy.

## 7. Immunity is a trait; a critical bypasses rates

Immunity is its own binary trait rather than an overloaded state-rate value:

| Code | Meaning |
|---|---|
| `STATE_IMMUNITY` | `dataId` = state id. Binary. Nothing lands it, ever. |
| `STATE_CATEGORY_IMMUNITY` | `dataId` = category. Binary category immunity. |

```text
chance = skill chance × STATUS_SUCCESS × state rate      -- floored at 0
critical         → lands, skipping the rate chain
immunity trait   → never lands, including on a critical
```

A rate of 0 or below therefore means *vanishingly unlikely*, not absolute
immunity. A critical can force through rates; an immunity trait cannot be
bypassed. This removes the need for a special “rate zero means immune” branch
and lets the derived DEF/MDF curve use whatever shape reads best.

The user-facing `state_immune` feedback concept remains valuable: a status that
was explicitly blocked by immunity should say so rather than disappear
silently.

### 7.1 Critical defense

With criticals as the universal status backdoor, critical defense matters twice:
less burst damage and fewer forced statuses. Use `CEV` (Critical Evasion) as the
dedicated counterpart to `CRI`:

```text
effective critical rate = CRI − CEV, floored at 0
```

`CEV` is **trait-driven only, not derived from a stat**. Gear and passives buy
crit defense. Deriving it from base DEF would hand VIT another systemic job and
recreate the super-stat problem this design avoids.

## 8. Data and validation

Skill rows may declare these optional fields:

| Field | Family | Type |
|---|---|---|
| `charges` | magic | formula string or integer (`0` = Overcast-only) |
| `overcast.mp` | magic | integer |
| `cooldown` | physical | integer turns |
| `warmup` | physical | integer turns |
| `condition` | physical | formula or prefixed condition string |
| `conditionText` | physical | display string, required with `condition` |

`mpCost` is outside this design's skill schema. A repo-owned skill carrying it
should fail validation rather than silently preserving a second cost system.

Validation must enforce:

- `charges` and formula-form `condition` compile;
- `condition` requires `conditionText`;
- `overcast` requires a `charges` key, even when that pool is literal zero;
- `mpCost` is rejected;
- `cooldown` / `warmup` are non-negative integers;
- rate-zero authoring intended as immunity is rejected or redirected toward the
  explicit immunity traits, so an author cannot silently request the wrong
  semantic.

The editor exposes the same fields and should show a sample evaluated charge
formula without inventing a second formula interpreter.

## 9. Presentation

- **Battle submenu:** each row shows its availability/cost gate — `⟨3/6⟩` for
  charges, `CD 2` for cooldown, `Rd 3` for warmup, or the authored
  `conditionText`. Unusable rows are greyed with the reason in context help.
- **Status scene:** skill rows show max/current charges and relevant gate
  information so an expedition decision can be made outside battle.
- **No new HUD element:** Overcast spends the same shared MP economy represented
  by the party's MP gauge.

## 10. Content tuning targets

Every skill should belong clearly to one cost family. Initial tuning intent:

- Attack-like basics: no gate. There must always be something to do.
- Standard spells: 4–8 charges at typical SPR, Overcast 100–200 MP.
- Big spells: 1–3 charges, Overcast 300+ MP, or no Overcast.
- Dragon Breaths: `charges: 0`, Overcast 350–500 MP.
- Signature physicals: cooldown 2–4.
- Situational physicals: a condition and usually no cooldown — the condition
  *is* the cost.

Content migration and verification consequences belong in Issues, PRs, tests,
and reviewed status sources rather than in this design document.
