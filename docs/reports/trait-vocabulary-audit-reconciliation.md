# Trait vocabulary audit reconciliation

**Status:** canonical supplement to `trait-vocabulary-audit-main.md` in PR #320.

This note reconciles the independent live-vocabulary audits produced in PRs #319 and #323. Where those audits disagree on architectural classification, the classifications in `trait-vocabulary-audit-main.md` remain authoritative for this PR. This supplement imports only evidence that adds a distinct dimension: authored usage counts, a corrected dead/unused interpretation, and several concrete architectural observations from the independent audit.

## Authored usage snapshot

The independent #323 census counted authored occurrences of the 42 registered trait codes against the same current-main investigation window. These counts are useful for prioritization, but **zero authored occurrences does not mean dead engine vocabulary** when a code still has active consumers.

| Code | Authored instances |
| --- | ---: |
| `COVER_ALIGNED_BACK` | 1 |
| `PARAM_PLUS` | 115 |
| `PARAM_RATE` | 17 |
| `HIT` | 4 |
| `EVA` | 4 |
| `CRI` | 10 |
| `CEV` | 0 |
| `HRG` | 6 |
| `POST_BATTLE_HEAL` | 3 |
| `GOLD_DIGGER` | 4 |
| `PARASITE` | 1 |
| `BATTLE_START_DAMAGE` | 1 |
| `MOVE_HEAL` | 1 |
| `RECOVERY_XP_BONUS` | 2 |
| `FLEE_CHANCE_BONUS` | 6 |
| `ON_PERMADEATH` | 6 |
| `SEE_TRAPS` | 5 |
| `SEE_WALLS` | 2 |
| `SYMBIOSIS` | 1 |
| `INITIATIVE` | 5 |
| `REAR_GUARD` | 3 |
| `ELEMENT_CHANGE` | 8 |
| `ELEMENT_ADD` | 10 |
| `XP_RATE` | 2 |
| `CRAFT_YIELD_RATE` | 1 |
| `PENETRATION` | 1 |
| `EXECUTION_THRESHOLD` | 2 |
| `EXECUTION_RESIST` | 1 |
| `FORCE_ACTION` | 2 |
| `INVERT_TARGETING` | 1 |
| `STATE_RATE` | 5 |
| `STATE_IMMUNITY` | 3 |
| `STATE_CATEGORY_IMMUNITY` | 1 |
| `STATE_CATEGORY_RATE` | 5 |
| `STATUS_SUCCESS` | 4 |
| `DAMAGE_RATE` | 5 |
| `ITEM_EFFECT_RATE` | 8 |
| `HEAL_RATE` | 2 |
| `TARGET_RATE` | 2 |
| `ELEMENT_RATE` | 20 |
| `KILL_MP_RESTORE` | 1 |
| `BARRIER_GRANT` | 0 |

## Corrected dead/unused interpretation

The main audit's statement that all 42 registered traits are used by at least one JSON data file is too strong. The #323 authored-usage census found zero authored instances for at least `CEV` and `BARRIER_GRANT` in its snapshot.

That does **not** establish that either code is dead:

- `CEV` still has an engine consumer in critical-resolution logic;
- `BARRIER_GRANT` still has barrier/interpreter consumers and battle-flow integration.

The durable conclusion is therefore narrower: **no registered trait is proven dead by these audits, but registered/consumed and presently authored are separate facts and should be reported separately.**

## Schema drift outside the registered 42

PR #319 found a separate registry-drift hazard: `SACRIFICE_EXP_RATE` is actively referenced in the codebase while absent from `data/engine.json`'s registered trait vocabulary.

This does not change the count of 42 registered traits. It demonstrates why untyped string codes are fragile: code can acquire a vocabulary word without the canonical registry knowing about it. Any #308-era typed capability system should make this class of drift mechanically difficult or validation-failing.

## Strategic observations retained from #319

1. **Combination semantics must be explicit.** Current trait aggregation relies heavily on additive helpers such as `traits.getRate`, while some mechanics are intentionally multiplicative. A generic calculation-contribution API must declare combination/ordering semantics rather than assuming one accumulation rule.
2. **Provenance is already a demonstrated requirement.** `getActiveObjects` / `findAllSources` retain source lineage because mechanics such as `ON_PERMADEATH` need the concrete originating item/state. The generic layer must preserve that identity instead of flattening contributions to anonymous values.
3. **Half-data-driven traits expose missing lifecycle facts and selectors.** `SYMBIOSIS`, `PARASITE`, and `MOVE_HEAL` are useful evidence for semantic lifecycle points such as round/step events and references such as a neighboring battler.
4. **Structural capabilities are not automatically reactions.** Flags such as `INVERT_TARGETING` alter deep targeting behavior; #308 should not force every capability into one universal event-hook abstraction.
5. **Source-local mutable state is a real missing primitive.** Toxic/Bide-style mechanics remain awkward until a concrete state/equipment/passive instance can own persistent authored values.

## Classification reconciliation

Do not import #323's category totals into the canonical audit. That report simultaneously describes a 42-code registry while its category summary totals 45, and several classifications conflict with the transition/reaction distinction used by #313 and the main #320 audit.

For the current design work:

- `trait-vocabulary-audit-main.md` owns the working architectural classification;
- this supplement owns the independent authored-usage snapshot and reconciliation notes;
- PR #313 remains the external mechanic-pressure benchmark;
- future implementation work may revise individual classifications when concrete typed seams are introduced.
