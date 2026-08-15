# Progression semantics and the JosephSeraph house baseline

Status: durable architecture intent for #548. This note specializes the authoring ontology from #308/#325 and the pinned RTP ownership model from #385. It defines semantic ownership, not the final field names or Event schema for the implementation issues.

## Core position

Thestra does not need a dedicated "learn skills on level-up" system.

A game that wants that behavior should express it as an ordinary consequence of a meaningful level transition through the shared Event Program vocabulary. Second Gate itself does not intend to learn skills on level-up; that makes the example useful as a composability fixture rather than a game requirement.

The architecture should distinguish four layers:

```text
Project-authored policy/content
        ↓ override / extend
Thestra house baseline (pinned RTP)
        ↓ compose
Authored semantic vocabulary
        ↓ implemented by
Native/runtime semantic primitives
```

The engine decides that something happened safely. Authored Event Programs decide what that happening means in this game.

## Semantic runtime, opinionated baseline

"Neutral" is not the design target for Thestra's RPG defaults.

Useful RPG defaults are inevitably opinionated. RPG Maker's defaults descend from a specific Japanese console-RPG grammar; that does not make them invalid defaults. Thestra is primarily, and may remain solely, JosephSeraph's engine. When a baseline needs an opinion, it should derive from the owner's recurring body of work rather than from hypothetical universal-engine consumers.

Canonical principle:

> **Thestra runtime should strive for semantic generality. Thestra RTP should strive for JosephSeraph coherence.**

A house baseline may therefore intentionally prefer compact JRPG-like numbers, particular menu grammars, a useful EXP curve, familiar recovery behavior, default Scene compositions, UI resources, and other recurring authoring conventions.

The requirement is not cultural or genre neutrality. The requirements are:

- the behavior is reusable beyond one concrete Project;
- the provider and revision are explicit and inspectable;
- the Project can intentionally override or Make Local the behavior;
- reopening a pinned Project is reproducible;
- export materializes the resolved behavior hermetically;
- concrete Second Gate content, lore, IDs, balance sentences, or branding are not silently promoted merely because they are convenient.

A useful scope rule is:

> **Generalize from the body of work, not from the universe of possible games.**

Thestra should have a center of gravity without walls around that center.

## What "empty Project" means

A new sparse Project should be **empty locally, not semantically empty**.

The Project materializes only its own minimum identity and local authored resources. Legitimate baseline behavior may resolve from the Project's pinned Thestra RTP revision. If the author wants divergence, Make Local or an explicit Project override materializes the authored resource under Project ownership.

Therefore moving gameplay policy from Lua to data must not imply that a new Project forgets how ordinary RPG concepts work. The resolved game is conceptually:

```text
installed compatible Thestra runtime
+ pinned Thestra house baseline
+ pinned explicit Packages
+ Project-local authored resources/overrides
```

This is not a hidden "missing file -> current installation default" fallback. Resolution remains explicit, versioned, provider-aware and reproducible as defined by the RTP architecture.

## Level transition ownership

### Native invariant

Native code should own the state transition that must remain correct regardless of authored policy:

```text
GAIN_EXP
  -> apply authoritative EXP gain
  -> resolve the authored threshold for the current level
  -> if crossed, consume that threshold
  -> commit the next level atomically
  -> publish LEVEL_REACHED
  -> continue while another threshold is crossed
```

Authors should not have to reproduce the EXP-consumption loop with Event commands. A missing command must not be able to leave a Unit in an incoherent state such as enough EXP for several levels while the authoritative level was only partially updated.

For a gain that crosses from level 4 to level 9, the runtime should resolve 5, 6, 7, 8 and 9 in order.

### Authored threshold policy

The threshold/curve is game policy and should be authored data/Formula rather than a concrete equation embedded in Lua.

The exact schema is intentionally left to #549. Conceptually a house baseline may provide something as simple as:

```text
next level EXP = level * 15
```

A Project may override that with another curve. A Project may also use levels while choosing a completely different consequence model.

The arithmetic is authored; the invariant transition is native.

## LEVEL_REACHED is a meaningful domain event

After a level is committed, the runtime should publish one resolved authored event for that reached level. Initial context should stay small and evidence-driven, for example:

```text
event.unit
event.previousLevel
event.level
```

The event is post-commit: while handling level N, `unit.level == event.level == N`.

Authors should read event context directly through Formula/Event semantics. They should not need to copy the reached level into a persistent Variable merely to branch on it.

A conformance fixture may then express:

```text
WHEN Level Reached
  IF event.level == 5
    LEARN_SKILL Fire

  IF event.level == 9
    LEARN_SKILL Ice
    CHANGE_PARAM ATK +2

  IF event.level == 11
    TRANSFORM_UNIT ...

  IF event.level == 13
    GAME_OVER
```

No `skillsByLevel`, `promotionsByLevel`, `statsByLevel`, or other dedicated progression sentence is required.

## Reactions, not callback walls

Entity-authored consequences should reuse #308's reaction/Event Program direction.

For Units, the authoring surface should be one optional Reactions collection rather than one editor section per hook. A compact row can summarize a trigger, optional condition, and ordinary Event commands:

```text
Level Reached · event.level == 9
  Learn Ice · ATK +2
```

Do not pre-populate a giant taxonomy of Unit/Item/State hooks. Add meaningful domain events when real authored systems require them.

Events represent domain transitions, not arbitrary property mutation. Healthy examples include Level Reached, Unit Defeated, Item Used, State Applied, Battle Started, Turn Ended, or Map Entered. Generic hooks such as Any Property Changed, Array Modified, or Unit Updated invite reactive-programming event spaghetti and are not a goal.

## Transformation boundary

Current transformation code demonstrates the difference between **semantic primitive** and **authored policy**.

Identity-preserving transformation is a healthy native capability. Rebuilding a Unit into another form while preserving the intended instance identity/history, growth seed, permanent gains, learned skills, equipment/state, level/EXP, and provenance should not be reimplemented as a sequence of fragile Event commands.

The authored vocabulary should expose that capability as an ordinary command, conceptually:

```text
TRANSFORM_UNIT unit destination ...
```

The command answers **how to transform safely**.

A sentence such as "at level 11, transform into X" answers **when to transform** and belongs in authored reaction policy. `gainExp()` therefore should not need to know that transformation exists.

Current hatch/metamorph/revert options must be classified separately: a mode that changes transformation invariants may deserve typed native semantics; a mode that merely describes a trigger does not.

## Growth boundary

Second Gate's seeded, uneven, budget-first growth algorithm can remain native if it is a useful stable calculation primitive. Data-driven architecture does not require rewriting deterministic algorithms into JSON.

The important separation is that "a level happened" must not intrinsically mean "apply this exact growth model."

The authored vocabulary may expose the calculation/application as a command such as:

```text
APPLY_GROWTH unit event.level
```

Second Gate can invoke it from its level policy. Another Project can use fixed `CHANGE_PARAM` commands, a different growth capability, or no stat growth at all.

Whether seeded budget growth belongs in the JosephSeraph house baseline is itself an authored-default decision. Reuse evidence, not theoretical neutrality, should decide it.

## Recovery and transaction boundaries

Moving consequences out of `gainExp()` must preserve the actual current semantics rather than mechanically moving every line into `LEVEL_REACHED`.

If current behavior heals once after a whole multi-level EXP transaction, moving `RECOVER` into a per-level reaction would silently change gameplay. The migration must distinguish:

- per-reached-level policy;
- after-the-complete-EXP-transaction policy;
- Unit-local reactions.

Add lifecycle events only when a meaningful semantic boundary is demonstrated. Do not add before/during/after variants preemptively.

## Data-driven does not mean zero Lua

Use this ownership test:

**Native runtime**
: Is this an invariant or reusable semantic operation that must remain correct regardless of game policy?

**Thestra house baseline / RTP**
: Is this a reusable JosephSeraph-style default that multiple games could reasonably begin from?

**Project**
: Is this the deliberate identity, content, or policy of this particular game?

JSON is not automatically Project-owned, and Lua is not automatically an architecture failure. A robust native transformation primitive can be correct; a hardcoded "transform automatically at level N" policy can be misplaced. A deterministic growth algorithm can be correct; hardwiring it as the definition of leveling can be misplaced.

## Implementation slices

#548 is the architecture parent. The initial bounded slices are:

- #549 — authored EXP threshold policy with native level invariants;
- #550 — post-commit `LEVEL_REACHED` event context;
- #551 — identity-preserving `TRANSFORM_UNIT` Event command;
- #552 — move automatic growth/recovery/transform consequences out of `gainExp()` while preserving exact current behavior;
- #553 — expose seeded Unit growth as composable authored behavior;
- #554 — compact Unit Reactions authoring surface over the shared Event Program system;
- #555 — prove sparse Project progression through the pinned JosephSeraph house baseline and Make Local/export.

These slices deliberately avoid one universal progression/reaction mega-PR.

## Durable invariants

- No dedicated skill-learning-on-level system is required.
- Level/EXP state transitions remain safe even when authored consequences are empty or malformed.
- Progression curve/policy is authored and provider-resolved, not an unversioned gameplay guess in Lua.
- Every crossed level is resolved deterministically and in order.
- `LEVEL_REACHED` is a meaningful post-commit event, not a generic property watcher.
- Transformation preserves identity through one authoritative semantic primitive.
- Trigger conditions for transformation remain authored policy.
- A growth algorithm may be native; applying one automatically because "levels imply growth" is authored policy.
- Sparse Projects inherit explicit pinned house behavior rather than becoming semantically blank.
- House defaults may be opinionated and JosephSeraph-shaped; concrete Second Gate content remains Project-owned.
- Event/reaction authoring reuses the shared Event Program vocabulary and editor.
- Thestra is not designed around hypothetical universal-engine users.

Agent-Signature:
  platform: ChatGPT
  model: GPT-5.6 Sol
  role: documentation
  task: "#548 progression semantics + JosephSeraph house baseline"
