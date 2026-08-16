# Stratum Revisit Spiral — Campaign Structure

> **Intent, not status.** This document records an owner-directed Second Gate game-flow principle. It does not assert that the described strata, floor counts, remix mechanics, or transitions are already implemented. Exact counts remain tuning knobs until playtesting establishes the right campaign length.

## Core structure

Second Gate should prefer a **spiral** campaign structure over a simple sequence of disposable dungeon biomes.

A new Stratum introduces a fresh spatial, mechanical, ecological, and dramatic thesis. Before the Campaign advances fully into the next new Stratum, the player passes through **one-floor revisits of the strata already encountered**, with their earlier ideas re-authored under later knowledge and mechanics.

The working grammar is:

```text
Stratum I
  -> revisit I
Stratum II
  -> revisit I
  -> revisit II
Stratum III
  -> revisit I
  -> revisit II
  -> revisit III
Stratum IV
  -> ...
```

In practice, the first transition may omit or compress a self-revisit if it does not earn its place. The durable rule is not a rigid spreadsheet schedule. The durable rule is **accumulating recurrence**: as the Campaign advances, its past remains mechanically available for reinterpretation instead of becoming exhausted content.

A useful working baseline is for each new Stratum to contain several substantial first-encounter floors, while each revisit is a denser single-floor variation. If new Strata average three first-encounter floors, five Strata would produce fifteen first-encounter floors plus roughly ten revisit floors: substantial playtime growth without requiring twenty-five wholly unrelated environments.

This growth is closer to quadratic than exponential in strict mathematical terms, but the desired player experience is that the dungeon **widens behind them** as they descend.

## The purpose of a revisit

A revisit is not:

- an old floor with stronger enemies;
- a palette swap;
- a procedural reroll presented as authored progression;
- mandatory backtracking through an unchanged route;
- a checklist inserted only because the structure says a revisit is due; or
- a cheap substitute for new Campaign ideas.

A revisit is:

> **a one-floor variation that tests what the player now understands about an earlier Stratum.**

The first encounter with a Stratum teaches a vocabulary. Later revisits compose with that vocabulary.

The player should ideally experience three kinds of change at once:

1. **the dungeon has changed** — topology, ecology, hazards, objective, event state, presentation, or other authored conditions differ;
2. **the surrounding game has changed** — later mechanics, creatures, resources, and Campaign knowledge now interact with the old space; and
3. **the player has changed** — their roster, tactical literacy, expectations, and memory transform how familiar material is read.

The design target is **mechanical memory**, not repetition.

## Strata as theses

Each Stratum should be designed strongly enough that it can later function as a reusable design primitive.

A Stratum therefore benefits from having a legible thesis: not merely a visual theme, but some combination of spatial rule, encounter pressure, resource question, movement idea, ecology, authored event grammar, or interpretive problem that can be meaningfully transformed later.

The useful campaign-scale relationship is:

```text
new Stratum
  -> introduces a thesis
revisit sequence
  -> applies, contradicts, combines, or reinterprets earlier theses
next Stratum
  -> introduces another thesis
```

This allows first-encounter floors to stay relatively clear. Complexity does not need to accumulate by making every new Stratum contain every previous mechanic at once. Cross-pollination can happen in the revisit layer instead.

## Backward refraction

A particularly strong default is for the **newest completed Stratum to cast its logic backward** across the revisit sequence that follows it.

If a later Stratum introduces a new principle, the following revisits can ask how that principle changes the meaning of earlier spaces.

Purely hypothetical examples:

```text
Stratum I: visibility / darkness
Stratum II: heat
Stratum III: elevation
Stratum IV: pursuit / predation
```

Possible revisits might then explore:

- I × II — heat sources reveal, distort, or destroy earlier darkness logic;
- I × III — familiar visibility problems become vertical navigation problems;
- II × III — heat behaves differently across elevations;
- I × IV — darkness becomes concealment from pursuit rather than only a navigation hazard;
- II × IV — heat attracts or repels predators; and
- III × IV — pursuing entities traverse vertical space differently from the player.

These are examples of the **composition principle**, not commitments to these exact Strata or mechanics.

The backward-refraction rule gives each inter-Stratum sequence a coherent identity. The Campaign is not merely revisiting several old places independently; it is asking a new question of everything that came before.

## Revisit design requirements

A revisit must earn its place.

As a working authoring constraint, a revisit should substantially alter at least **two meaningful axes** relative to the earlier appearance. Relevant axes include:

- topology or route logic;
- objective;
- encounter composition;
- enemy ecology or behavior;
- environmental rule;
- resource economy;
- access pattern;
- event state;
- landmark meaning;
- narrative or ontological interpretation;
- reward structure;
- time pressure;
- visibility or information conditions; and
- interaction with mechanics learned later.

This is not a literal validator rule. It is a defense against low-value "same floor, higher numbers" content.

Revisits may reuse architecture, landmarks, props, textures, encounter ingredients, music motifs, or event setups when recognition itself has value. Reuse is desirable when it produces **memory plus difference**.

A strong player reaction is:

> “I know this place — but this is not the situation I remember.”

## Recognizable landmarks

The Campaign should deliberately preserve some recognizable spatial motifs between first encounter and revisit.

Whole maps do not need to be copied. A corridor, chamber silhouette, stair, vista, machine, landmark, or route relationship may be enough to trigger recognition.

Recognition creates design leverage. Once the player remembers what a space used to mean, the revisit can change that meaning with very little exposition.

This turns level design into a form of character development: a Stratum establishes itself, returns under pressure, contradicts expectations, and accumulates history.

## Pacing and floor weight

The revisit spiral creates a production advantage only if it does not become a pacing tax.

As later transitions contain more revisits, those floors should usually be **shorter and denser than a first-encounter floor**. A useful initial tuning target is roughly half to two-thirds the exploration weight of a substantial new floor, though playtesting should determine the real value.

Revisits should assume prior literacy. They do not need the same amount of onboarding, scenic introduction, or low-pressure wandering as the first encounter with a Stratum.

The intended rhythm is approximately:

```text
NEW — NEW — NEW
variation
NEW — NEW — NEW
variation — variation
NEW — NEW — NEW
variation — variation — variation
```

The increasingly long refrain should build anticipation for the unknown rather than create impatience for it. If the player begins thinking “show me the new Stratum already,” the revisit layer is too long, too repetitive, or insufficiently transformative.

The structure is therefore **elastic**. A weak revisit may be compressed, merged, made optional, or removed. Campaign rhythm takes precedence over symmetry.

## Asset and production leverage

The revisit spiral is intentionally fertile under Second Gate's production constraints.

It permits the Campaign to grow in playtime and mechanical depth without requiring every additional floor to introduce a wholly new tileset, prop library, enemy family, music set, and visual concept.

This is not permission to disguise repetition. The production advantage comes from spending authored effort on **transformation and composition** rather than continuously paying the full cost of novelty.

Useful reuse includes:

- familiar spaces with altered topology or traversal;
- old assets under new lighting, state, damage, occupation, or environmental conditions;
- enemies used in changed ecological relationships;
- later creatures or tools creating new solutions to old problems;
- musical motifs rearranged rather than replaced; and
- previously mundane landmarks becoming strategically or narratively charged.

A revisit that is cheap in asset terms can still be expensive in thought. That is desirable: the structure shifts cost toward game design rather than raw content volume.

## Campaign meaning

The spiral should support the sense that the Labyrinth is not ordinary disposable geography.

Second Gate does not need to explain recurrence with one definitive lore mechanism merely to justify the structure. Repetition may be read as spatial instability, memory, recursion, altered access, the Gate's ontology, or simply the authored form of the dungeon.

The important experiential effect is that descent does not erase the past.

Earlier places remain present enough to be re-read.

That makes the Campaign itself capable of memory.

## Relationship to player progression

Revisits should exploit the fact that player progression changes the meaning of old mechanics even when the environment is only partially altered.

A later roster, new creature capabilities, different item economy, stronger tactical literacy, or newly understood systemic relationships may turn an earlier hazard into an opportunity, an earlier threat into a resource, or an earlier route into a different decision problem.

This means not every revisit needs maximal environmental mutation. Sometimes the richest variation is produced by deliberately keeping one old rule stable while changing the player's available answers to it.

The design question is not only “what changed in the floor?” but also:

> **what can the player now do, notice, or infer here that they could not before?**

## Encounter and reward implications

Revisit encounters should favor recombination over simple stat escalation.

Useful possibilities include:

- old enemies placed into later ecological relationships;
- mixed encounter families that were previously separated;
- changed formation or terrain pressures;
- enemies whose significance changes because the player now recognizes their behavior;
- optional high-risk branches that exploit later capabilities; and
- rewards that make returning to old conceptual territory feel materially worthwhile.

A revisit should not be balanced merely by multiplying HP and damage. Difficulty can emerge from composition, information, objectives, attrition, routing, and unfamiliar interactions among familiar pieces.

## Authoring checklist

When proposing a revisit, answer:

1. What did the player learn about this Stratum the first time?
2. What later Campaign knowledge or mechanic now exists?
3. Which assumption from the earlier visit is being preserved?
4. Which assumption is being broken or reinterpreted?
5. What two or more meaningful axes change?
6. Which landmark or motif creates recognition?
7. Why is this better as a revisit than as an unrelated new floor?
8. What production material is intentionally reused?
9. What genuinely new authored work makes the reuse worthwhile?
10. Is the floor short and dense enough for its position in the accumulating refrain?
11. What does the player now understand, do, or feel that the original floor could not produce?

If those questions do not produce interesting answers, the revisit is not owed a place in the Campaign.

## Working growth model

For `S` Strata, if each Stratum contributes `N` substantial first-encounter floors and each transition eventually revisits each completed Stratum once, the rough content count is:

```text
first-encounter floors = S * N
revisit floors         = S * (S - 1) / 2
```

With five Strata and three first-encounter floors per Stratum:

```text
15 first-encounter floors
10 revisit floors
25 total authored floors
```

This is a planning model, not a quota. Optional branches, town sequences, bosses, special spaces, compressed revisits, omitted weak revisits, and differently sized Strata can all change the actual Campaign.

The reason to preserve the model is that it makes the production implication visible: **each new Stratum adds not only its own floors, but future reinterpretation opportunities across the material already built.**

## Open tuning questions

The following remain deliberately unresolved:

- exact number of Strata;
- exact number of first-encounter floors per Stratum;
- whether a Stratum immediately receives a self-revisit before the next Stratum;
- whether every previous Stratum must appear in every transition;
- whether some revisits are optional, secret, merged, or replaced by special sequences;
- how often revisit floors culminate in bosses or other major encounters;
- how town returns interleave with the revisit refrain;
- whether the final descent breaks, accelerates, or completes the established spiral; and
- how literally the Labyrinth acknowledges recurrence in fiction.

Playtesting and campaign exploration should answer these rather than aesthetic symmetry alone.

## Durable principles

- Second Gate's dungeon progression should behave like a spiral, not a disposable biome ladder.
- New Strata introduce theses; revisits reinterpret earlier theses under later mechanics and knowledge.
- The Campaign accumulates a playable past.
- Revisit floors are authored variations, not stat-scaled repeats.
- Recognition is a resource: preserve selected landmarks and motifs so change has something to act upon.
- Revisit sequences should become richer as the Campaign grows, but not so long that they delay novelty intolerably.
- Later mechanics may refract backward across earlier Strata, creating a combinatorial dungeon grammar.
- Player progression itself is part of the remix.
- Asset reuse is a strength when it buys mechanical, spatial, dramatic, or ontological reinterpretation.
- Symmetry is subordinate to quality. A revisit that does not create meaningful difference may be omitted.
