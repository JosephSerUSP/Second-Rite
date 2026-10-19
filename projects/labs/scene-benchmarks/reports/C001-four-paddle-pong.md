# C001 — Four-Paddle Pong

## Experiment

Stable ID: C001
Title: Four-Paddle Pong
Source: `A001`
Pressure: whether composition survives topology change

## Result

complete; playable.

## Authored Surface

- **Scene JSON:** `projects/labs/scene-benchmarks/data/scenes/c001_four_paddle_pong.json`
- **Updates:** `title.json`, `index.json`, `terms.json` to register the new benchmark scene.

The logic uses purely JSON declarative semantics. We created 4 explicitly placed window panels bound to state variables, 2 of which operate horizontally and 2 vertically. The ball's physics simulation uses the standard step approach, but is updated to bounce on 4 paddles rather than 2. The player controls the left and bottom paddles, and the AI controls the right and top paddles. The bounds are adjusted to be square and handle all four directions correctly.

## SCRIPT / Native Escape Hatches

None. The experiment successfully constrained itself entirely to declarative JSON without executing raw `SCRIPT` logic.

## Missing Reusable Semantics

None.

## Awkward But Expressible

Managing a large sequence of collision conditions and bounce results inside the frame physics using composite `IF` statements is slightly verbose but entirely functional. It demonstrates that composition successfully survives topology changes without requiring new engine abstractions.

## Tooling / Discoverability Gaps

There is a slight discoverability gap in finding the cleanest way to author input actions across two axes (left/right vs up/down) when mapped to different visual elements, though it is fundamentally straightforward.

## Backend Leakage

None. The variables rely strictly on supported math formula helpers (`min`, `max`) and standard delta-time evaluation (`time.dt`).

## Project Leakage

None. All files created run strictly inside the benchmark scene environment and isolated namespace.

## Author Legibility

A competent event author would easily understand the result. The explicit condition evaluations map perfectly to an event-driven system or trigger boxes with variable assignment outcomes.

## Reusable Successes

- **Formula transforms for collision/state mapping:** expanding the state transitions to support 4 collision axes worked neatly without rewriting the core delta-time physics logic.

## Architecture Recommendation

no architecture change indicated; the existing declarative logic gracefully accommodates topology changes.

## Owner Playtest

**Status:** READY FOR OWNER PLAYTEST

**Instructions:**
1. Boot the scene benchmark launcher.
2. Select `C001 Four-Paddle Pong`.
3. Use `UP/DOWN` to control the left paddle.
4. Use `LEFT/RIGHT` to control the bottom paddle.
5. Attempt to rally against the AI (which controls Top and Right).

**Observations:**
(Pending)

**Result:**
(Pending)
