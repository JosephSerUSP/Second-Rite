# Level 1-10 vertical-slice balance

> **Intent and test protocol, not implementation status.** Live status remains
> the authority of `docs/ENGINE-STATE.md`, with reviewed mechanics in
> `docs/SPEC.md`. This document defines the first playable balance pass over the
> six-floor campaign concept.

## Purpose

The slice must prove that the expanded database forms a progression rather than
merely a valid collection of content. A successful run begins with ordinary
level-1 creatures and ends near level 10 after visiting Floors 1-3, with later
floors reserved for follow-up testing.

The slice must exercise:

- field MP pressure and a meaningful retreat decision;
- at least three elemental matchups;
- one Favorite Food discovery and one useful Savor activation;
- one meal used for party recovery and one battle-usable drink;
- Item Creation with found, bought, and monster-derived ingredients;
- one Egg with visible provenance and an automatic level-10 hatch;
- two ordinary level promotions;
- one branch-specific item promotion whose key cannot be crafted;
- one fragile low-MPD party and one expensive high-power party.

## Structural balance assumptions

### Experience pacing

Using a `level * 15` next-level curve as the slice's progression target gives:

| Goal | Cumulative EXP |
|---|---:|
| Level 2 | 15 |
| Level 5 | 150 |
| Level 8 | 420 |
| Level 10 | 675 |

The intended pace is roughly **45 ordinary-victory equivalents** to reach level
10 across the slice. Do not encode that as a permanent flat reward per victory:
enemy count, enemy level, encounter danger, and later reward tuning should be
able to shape the actual EXP award while preserving the overall pacing target.

### Dungeon danger uses an authored level ramp

Encounter definitions need per-enemy level ranges so the same species can remain
relevant across a floor band without duplicating Unit definitions. The authored
shape is:

```json
{
  "id": 25,
  "weight": 3,
  "levelMin": 2,
  "levelMax": 3
}
```

Each spawned enemy resolves independently within its range. Entries without a
range use the Unit's authored/default level. Floors 1-3 target the provisional
bands **1-3, 3-6, and 6-10** respectively.

The schema/validator/editor behavior for those fields belongs in `docs/SPEC.md`
and tests; this document owns only the balance intent.

### Starting HP scale constraints

Preserve deliberate early-body contrasts while tuning the expanded roster:
Pixie should remain a very fragile body around 12 base Max HP, Golem an early
~70-HP wall, Bat among the frailest ordinary bodies, and an Egg around 30 HP so
carrying one to level 10 is risky without being a near-automatic death sentence.

The level-30 growth curve remains a separate balance question. This slice is
about making the opening durability hierarchy legible first.

### Encounter cadence is measured, not assumed

For the first playtest, use a global **10% moved-tile encounter chance** as the
reference cadence and measure its variance rather than replacing it from
intuition. A per-step random roll cannot promise a fixed fight count per floor,
so the playtest record must capture steps moved and encounters actually seen.

Which authored/system field supplies that cadence is an implementation concern,
not a design-status statement here.

## Provisional slice targets

| Measure | Floor 1 | Floor 2 | Floor 3 |
|---|---:|---:|---:|
| Expected party level on entry | 1 | 3-4 | 6-7 |
| Enemy level range | 1-3 | 3-6 | 6-10 |
| Expected victories | 10-14 | 12-16 | 14-18 |
| Ordinary battle length | 2-4 rounds | 3-5 rounds | 3-6 rounds |
| Boss/pressure battle length | 5-8 rounds | 6-9 rounds | 7-10 rounds |
| Retreat MP remaining | 35-65% | 25-55% | 15-45% |
| New crafting discoveries | 2-4 | 3-5 | 3-5 |

These are measurement bands, not promises. A low-MPD Pixie/Kappa-style party
should exceed the MP band and pay for that endurance through combat risk. A
Cerberus or heavy frontline should fall below it and gain safer battles.

## Availability pass

- Floor 1 introduces Cocoon, Gbl. Thief, Mandrake, Kappa, and ordinary legacy
  creatures.
- Floor 2 introduces Undine, Homunculus, Mimic, Unicorn, and Gargoyle.
- Floor 3 introduces Cerberus and Giant as expensive early power choices.
- Ordinary equipment shops stop at tier 3.
- Tier-4/5 equipment and promotion keys belong to the auction.
- The pub is the primary meal source; dungeon merchants sell expedition staples.

The Floor 1 hidden-workshop reward should guarantee a **Mystic Egg, Pão de
Queijo, and Onigiri** alongside its quest reward. The trapped chest should grant
**Black Hinge** on either successful opening path, making Mimic-to-Pandora the
slice's first branch-specific item promotion. The foods remain useful items in
their own right and can also participate in Item Creation.

## Playtest record

For every expedition record:

- party species, levels, MPD, equipment, Favorite Food discoveries;
- steps moved, encounters won/fled, rounds per battle;
- starting/retreat MP and spell/Overcast MP spent;
- damage taken, incapacitations, and cause of each permanent death;
- EXP and levels gained;
- items found, consumed, sold, and used as ingredients;
- recipes discovered and whether each result was immediately relevant;
- promotions available, chosen, or delayed.

Balance changes should answer a recorded failure. Passing validation is not
evidence that a number is good.

## Reference static encounter sample

A deterministic 10,000-pick sample recorded during the design pass, using the
then-authored level ranges and an approximate share of the level-2-10 HP budget,
produced:

| Floor | Mean enemy level | Approx. mean enemy HP | Most common species |
|---|---:|---:|---|
| 1 | 1.83 | 40.2 | Pixie 22.5%, Skeleton 22.2%, Mandrake 14.4% |
| 2 | 4.46 | 63.6 | Skeleton 28.1%, Imp 17.0%, Wisp 13.8% |
| 3 | 7.62 | 110.8 | Golem 28.8%, Demon 18.6%, Angel 14.8% |

This table is historical measurement evidence for the target bands, not a live
content census. Its useful inference is that a heavy Floor-3 Golem share can turn
“teach party composition” into repetition; manual playtesting should measure that
pressure rather than treating the sample as a promise about later authored
encounter tables.
