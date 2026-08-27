# C002 — Splitting Ball Pong

## Experiment

Stable ID: C002
Title: Splitting Ball Pong
Source: `A001`
Pressure: multiplicity, spawning, collections

## Result

complete; playable.

## Authored Surface

- **Scene JSON:** `projects/labs/scene-benchmarks/data/scenes/c002_splitting_pong.json`
- **Updates:** `title.json`, `index.json`, `terms.json` to register the new benchmark scene.

The logic uses purely JSON declarative semantics. We created explicitly numbered sets of variables (`ball1X`, `ball2X`, `ball3X`, etc.) and distinct explicitly placed window panels bound to those state variables. State branching turns visibility bounds down to width/height 0 when inactive (`"w": "v.ball2Active > 0 and 1 or 0"`).

## SCRIPT / Native Escape Hatches

None. The experiment successfully constrained itself entirely to declarative JSON without executing raw `SCRIPT` logic.

## Missing Reusable Semantics

The engine lacks true dynamic array / collection primitives for declarative state. We handled "spawning" and multiple balls by physically duplicating physics state logic inside `on_frame` across 3 pre-defined independent elements. If the game needed to scale to an arbitrary large number of balls, declarative arrays of structs and a true `FOREACH` construct (or map/filter hooks) would be required.

## Awkward But Expressible

It's awkward to multiplex condition-checking for shared boundaries. For example, the check to see if *any* ball crossed the left or right threshold requires a long composite `IF` condition (`v.ball1X < 0 or (v.ball2Active > 0 and v.ball2X < 0) or ...`).

Similarly, AI paddle tracking requires a composed heuristic. The AI paddle targets `v.targetBallY` which was calculated via a chain of ternary fallback evaluations (`v.ball3Active > 0 and v.ball3Y or (v.ball2Active > 0 and v.ball2Y or v.ball1Y)`).

## Tooling / Discoverability Gaps

There is a tooling gap in creating and maintaining repetitive state definitions. Without loop operations or declarative prefabs, authors must manually copy/paste and re-number fields when declaring multiplexed state nodes.

## Backend Leakage

None. The variables rely strictly on supported math formula helpers (`min`, `max`) and standard delta-time evaluation (`time.dt`).

## Project Leakage

None. All files created run strictly inside the benchmark scene environment and isolated namespace.

## Author Legibility

A competent event author would understand the result. The explicit duplication (`ball1X`, `ball2X`) maps closely to how classic RPG Maker authors used to script custom multi-bullet systems through banks of explicitly addressed event IDs and parallel execution pages.

## Reusable Successes

- **Formula transforms for layout:** using declarative dimensions to effectively hide an element (`"w": "v.ball2Active > 0 and 1 or 0"`) worked flawlessly and bypassed the need for a separate "visibility" presentation primitive.
- **Delta-time hooks:** `v.time.dt` continues to enable incredibly stable state-driven physics without coupling to `love.update`.

## Architecture Recommendation

candidate reusable semantic gap; gather more evidence.
The ability to push elements onto a collection or iterate over state vectors would make multiplicity dramatically cleaner. However, since the engine currently favors small-scale interaction and distinct semantic layout, we should wait to see how strongly future constraints pressure the need for dynamic collections.

## Owner Playtest

**Status:** READY FOR OWNER PLAYTEST

**Instructions:**
1. Boot the scene benchmark launcher.
2. Select `C002 Splitting Pong`.
3. Wait for the paddle to hit the ball twice.
4. Observe the single ball splitting into three independent trajectories.

**Observations:**
(Pending)

**Result:**
(Pending)
