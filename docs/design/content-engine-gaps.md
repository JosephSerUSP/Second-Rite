# Content Behavior Requirements

> **Intent, not status.** This document records approved content promises that
> must not be weakened merely to fit a convenient primitive. It is not a census
> of what the engine can express today and not a delivery ledger.
> `docs/ENGINE-STATE.md` owns implementation inventory, `docs/SPEC.md` owns
> reviewed current mechanics, and GitHub Issues own actionable delivery work.

## Principle

Content is allowed to demand reusable engine vocabulary, but the engine should
not learn one-off rules named after a particular item, actor, or state.

When an approved content sentence cannot be expressed faithfully:

- preserve the intended behavior rather than authoring a misleading approximation;
- prefer a reusable registry-backed semantic capability;
- validate authored vocabulary so unsupported fields cannot appear meaningful
  while doing nothing;
- keep implementation sequencing and completion evidence in GitHub rather than
  in this document.

The broader transition from bespoke trait codes toward composable modifiers,
interceptors, reactions, and source-local state is tracked by #308. The
requirements below remain useful pressure tests regardless of that issue's
final schema.

## Balance intent

### Critical rates

Critical chance is a balance lever, not free power. Weapon/actor CRI values
should be judged against the trait budgets in `item-atlas-expansion.md` rather
than inherited from an old dataset merely because a number already exists.
Ordinary bonuses should remain meaningfully below signature bonuses unless a
specific item's identity justifies the exception.

### Skill potency and MP

Skill potency and MP cost are one kit-level balance decision. A potency band
copied from a reference table is not sufficient evidence by itself; finished
values must be simulated and playtested against the creature's actual stats,
role, action economy, and encounter roster.

## States and control

- **Defend** is intended to provide general protection rather than accidentally
  depending on only one defensive stat.
- **Ribbon-style protection** covers the ordinary/common negative-state family,
  not every state indiscriminately.
- Named cures should only promise targets that have authored state semantics;
  content names are not substitutes for state mechanics.
- Physical and magical evasion should remain separable if the roster needs a
  creature that is evasive on one channel but vulnerable on the other. Do not
  add a second channel merely for taxonomic completeness.

## Summoner MP / Battle Strain presentation

Long-fight pressure is only strategically fair when the player can understand
that escalation before committing choices that incur it. Any Battle Strain
presentation should read the same authoritative cost/query used by battle
semantics rather than maintain a UI-only prediction formula.

## Items, food, and Item Creation

Approved item behaviors should remain reusable semantic sentences rather than
content-specific engine branches:

- creature remains may serve as ingredients without therefore becoming
  generative outputs;
- a fixed-encounter item needs a specific authored encounter plus a
  result/continuation semantic after battle; a random encounter is not an
  equivalent approximation;
- equipment may attach an authored state payload to ordinary Attack through a
  reusable attack-state behavior;
- a selective skill-seal state should preserve ordinary commands that the design
  leaves legal rather than acting as a blanket cannot-act state;
- an escape item should use the same battle-exit authority as the ordinary flee
  action rather than a presentation or map shortcut.

## Presentation assets

A species is not visually complete merely because its data record exists. Each
creature intended to read as a distinct species should ultimately have the
portrait/battler presentation appropriate to that identity; placeholders are a
production expedient, not part of the creature design.

## Equipment behavior promises

The item atlas may map named equipment to these requirements; this document owns
the reusable design sentences, not a current inventory of which items are live.

- threshold-triggered combat behavior when an authored eligibility condition is met;
- meaningful defense penetration;
- healing amplification distinct from elemental affinity;
- authored magical protection without promising an unrelated mechanic;
- general protection with explicit tradeoffs where appropriate;
- ordinary/common state-family protection rather than indiscriminate immunity;
- finite ward charges stored on the concrete battler/equipment instance, never
  shared loader data;
- distinct support for immediate food effects versus Savor/Favorite-Food behavior;
- MPD reduction that cannot create an invalid zero/negative upkeep state, with
  displayed expedition cost agreeing with the authoritative query.

## Skill-tome safety

Teaching items are dangerous in generative Item Creation because a generated
output can bypass progression or inherit a learn-skill effect unintentionally.

Default policy:

- teaching items are excluded from generative Item Creation outputs;
- they are excluded from ingredient selection unless an authored recipe/system
  explicitly opts them in;
- deliberately creating a specific tome is a whitelist/content decision, not an
  accidental consequence of signature proximity;
- learned-skill eligibility and duplicate-learning behavior must remain validated;
- the systemic item atlas does not reserve arbitrary tome slots before the skill
  roster needs them.

## Live-data audit invariant

Before authoring a new vertical slice, compare its descriptions, traits,
effects, states, and item promises against the registered semantics in the
revision being authored. When there is a mismatch, either choose an existing
faithful semantic or raise a bounded GitHub Issue for the reusable missing
capability. Do not insert ignored fields or edit the prose into claiming that a
merely similar behavior is the same design.
