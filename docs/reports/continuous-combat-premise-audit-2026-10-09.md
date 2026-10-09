# Continuous combat premise audit — 2026-10-09

The continuous arena and the Day 1 recreation are both unsuitable as accepted
combat baselines. They establish useful capabilities, but both deliver the
player's attack immediately on confirmation. The reference source has an action
lifecycle between choosing an action and returning to normal control. Reusing a
damage evaluator alone does not reproduce that lifecycle.

This is a source audit, plus native visual review of the new lighting. It does
not establish original-game timing parity or owner acceptance of combat feel.
No combat behavior was changed in this audit.

## Evidence and boundaries

Reference: [khasinski/parasite-eve-decomp](https://github.com/khasinski/parasite-eve-decomp),
inspected at `f30aacf2d421a7f5034dbf013e245fea3086ed61` in
`out/pe-combat-audit/decomp`. It is a work-in-progress matching decompilation.
I inspected source; I did not reproduce its retail checksum build. Its symbol
names are interpretations, sometimes misleading: `Battle_StepEnemyMovement.c`
explicitly says it actually computes damage and starts hit reactions.

Our arena: `runtime/engine/arena_host.lua`, branch checkpoint `c970283a`.
Our Day 1 host: `runtime/engine/realtime_battle.lua` and
`projects/pe-day1/tools/chapter/build_chapter.py`, read from the separate
`b009-spatial-encounter` worktree at
`950d664085e809989f05c5d6b45c4e400764c070`. That worktree was not modified;
the Day 1 code is not present on this branch. Its generator is the authority
for the scene command lists and visual bindings discussed here.

The existing original-game reference pack was located under the primary
checkout's `out/parasite-eve-day1-reference-pack`. Its stills are composition
evidence, not measurements of attack commitment, pause rules or frame timing.
No new original-game playthrough or frame-by-frame footage measurement was
performed. Those measurements remain necessary before claiming fidelity.

## Findings

| Question | Reference source evidence | Continuous arena | Day 1 host |
|---|---|---|---|
| What does confirmation do? | Action entry and timed-hit paths are separate. | Calls `execution.execute`, resets AT, resumes simulation immediately. | `RT:commandInner` resets AT and calls `RT:resolve` immediately. |
| Is the player committed to an action? | `Battle_BeginPlayerAction` sets a move-lock bit and actor action mode; `Battle_ReturnToIdle` clears the lock and motion. | No player execution/recovery state. | Enemy pending actions exist; no corresponding player pending-action lifecycle in this command path. |
| When does damage happen? | `Battle_ResolveHitOnTimer` increments a timer and resolves when it equals `action->field08`. | At the target-confirm call. | At the command call for player skills; enemy windups/projectiles can deliver later. |
| What is range? | Target distance is planar Euclidean distance; target overlay compares it with the selected action's range (with an explicit special case). | Correct circular predicate, but one encounter-level range and one skill. | Per-skill delivery/range, distance-sensitive authored handgun damage. Outside range spends the action and misses. |
| What does an enemy threaten? | Actors, action records, animation modes and scheduled scripts participate. Full enemy patterns were not reconstructed in this pass. | Every period captures the player's position as a circular zone; no visible enemy strike or recovery. | AI selects skills; pending lunges and spreading projectiles produce distinct spatial threats. |
| What survives a hit/death? | Hit resolution and reaction state, death-animation phases, and victory/post-battle phases are explicit. | Resolved damage facts are retained internally, but no attack/hit beat presents them; victory removes the enemy root immediately. | Recoil/muzzle/hit-age bindings, windup/lunge model swaps, projectiles and outcome handling provide more feedback, without fixing immediate player resolution. |

Reference paths at the pinned revision:

- [Action lifecycle](https://github.com/khasinski/parasite-eve-decomp/blob/f30aacf2d421a7f5034dbf013e245fea3086ed61/src/main/battle/Battle_ActionLifecycle.c)
- [Timed hit](https://github.com/khasinski/parasite-eve-decomp/blob/f30aacf2d421a7f5034dbf013e245fea3086ed61/src/main/battle/Battle_ResolveHitOnTimer.c)
- [Distance/angle](https://github.com/khasinski/parasite-eve-decomp/blob/f30aacf2d421a7f5034dbf013e245fea3086ed61/src/main/battle/Battle_AngleAndDistanceFlow.c)
- [Target/range feedback](https://github.com/khasinski/parasite-eve-decomp/blob/f30aacf2d421a7f5034dbf013e245fea3086ed61/src/main/battle/Battle_TargetAndEnemyTurnFlow.c)
- [Death animation](https://github.com/khasinski/parasite-eve-decomp/blob/f30aacf2d421a7f5034dbf013e245fea3086ed61/src/main/battle/Battle_StepEntityAnimState.c)
- [Battle update](https://github.com/khasinski/parasite-eve-decomp/blob/f30aacf2d421a7f5034dbf013e245fea3086ed61/src/main/battle/Battle_Update.c)

`Battle_Update` separates its normal battle branch from menu, victory and
post-battle branches. Target selection also renders animation. This supports
explicit clock/mode ownership, but does not justify assuming every animation,
script task and effect freezes together. The exact pause matrix and enemy
execution arbitration need call-path tracing plus original-game observation.
Likewise, the timer field is evidence of sequencing, not a verified duration
in seconds. No guessed PS1 timing constants should be promoted from this audit.

## Architectural conclusion

Continuous traversal is a useful spatial substrate. The flawed premise is that
free movement + an AT gauge + target range + the shared damage evaluator are
enough to establish this combat experience. The missing layer is authored action
execution: anticipation, commitment, contact, recovery, reaction, and terminal
aftermath. Presentation is evidence of these states, not a substitute for them.

Day 1's delivery variety and visual feedback are useful references within our
own code. Its bounded-position host and immediate player command path should
not become the continuous host's authority merely because that demo feels less
bad. Do not copy either host wholesale or create a third independent resolver.

## Next playable experiment

Measure one original handgun action and one rat attack in footage: command
entry, target confirmation, movement lock, first shot, HP change, last shot,
return of control, AT restart, enemy advancement, and death/victory aftermath.
Record timestamps and distinguish observations from source interpretation.

Then implement the smallest reusable runtime-owned action lifecycle with
authored timing/delivery and presentation bindings. Existing event commands and
action-sequence capabilities must be inventoried first; add primitives only
where they lack the required semantics. Author the encounter in ordinary data.
Commit costs exactly once, resolve contact exactly once through shared action
semantics, publish resolved facts, and let presentation reveal those facts.
Presentation must not replay damage or determine simulation completion.

The experiment needs a visible player attack, a directional enemy attack with
anticipation and recovery, usable cancel/range feedback, and a visible terminal
beat. Observe and probe action ordering, movement ownership, pause/resume at
each boundary, repeated input, miss, lethal contact, and post-terminal input.
Judge it by a native playthrough alongside the original sequence; passing
probes alone will not establish feel. Production Battle internals remain under
the repository's owner-supervised boundary.

The implementation follow-up is [#1485](https://github.com/JosephSerUSP/Second-Rite/issues/1485),
with the measured-reference and event-authoring constraints above.

## Lit test environment

Both neutral rooms now have adopted `.blend` sources, low ambient light, a warm
area key and a cool area fill. The existing shared environment pipeline bakes
their geometry/materials into 512px atlases with Cycles (32 samples, CPU).
Explicit collision, walkable, obstacle and anchor collections remain separate.
The conversion preserves polygon order and coordinates to Blender's float
precision (maximum walk-coordinate difference below 1e-6); anchor positions
are unchanged. Lighting is static; this does not add dynamic lighting or
character light probes. Characters retain their existing runtime shading.

Native review: `out/continuous-lighting/room-{1,2}-ss2-idle.png`, with 32 native
room captures covering movement, repeat captures, obstacles and two render
sampling settings. Bakes are deliberately plain, with visible floor light
variation and obstacle shadows. They are a minimum useful test setting, not
final environmental art. Gameplay tokens, hostile effects and silhouettes
still need to remain legible against it in the next combat pass.

Verification passed: environment source-record check, source/product SHA-256
freshness check, sprite-fixture check, staged G1, actual-main dialogue-to-combat
proof, arena proof and staged save/load. A second export produced byte-identical
OBJ/MTL/PNG/collision products and preserved source hashes. No shared renderer or
combat code changed, and no canonical golden was regenerated. The playthrough
still emits the pre-existing `sceneState.dialogueCursorIdx` formula diagnostic;
its successful exit is not a claim that the dialogue dock is diagnostic-free.
