# Continuous combat lifecycle experiment — 2026-10-09

Follow-up to the premise audit and #1485. This pass implements an experimental
runtime-owned action lifecycle, rather than inheriting the Day 1 host's immediate
player resolution. It does not establish original-game parity or owner acceptance
of combat feel. No owner-supervised Battle files were changed.

## Behavior

An in-range confirmation enters anticipation (0.24s). HP and skill costs are
unchanged until contact. Contact calls the shared action executor exactly once;
its resolved HP fact feeds presentation. Recovery (0.42s) retains movement/input
commitment. Repeated confirmation or cancel cannot skip either stage or replay
damage. AT and enemy advancement hold during this player action. These values
and arbitration rules are explicitly experimental tuning.

The Sentinel pursues using the shared world-actor movement/collision authority.
Once nearby and ready, it locks the player's position for a 0.7s windup, then
lunges toward that destination over 0.55s and recovers for 0.85s. Contact requires
the player and attacker to reach the telegraphed area and be within contact
distance; dodging or an obstructed lunge can miss. Misses do not call the effect
executor. The red circle is fixed through windup/strike, not retargeted after a
dodge. Readiness can fill during enemy actions, so command selection and cancel
remain useful during a telegraph.

Lethal contact keeps bindings active through player recovery and 1.1s of
aftermath. The defeated actor fades; only then do cleanup, authored outcome
commands and exploration resume. Saves/transfers stay blocked until cleanup.
The UI distinguishes victory aftermath from resumed exploration.

## Existing-block inventory and ownership

`actionSequences` already compose effects through `runImmediate`; `WAIT` emits
presentation wait events. Those lists cannot schedule authoritative contact over
simulation time. They remain the effect language, called at contact. The new
`engine/action_timeline.lua` is an ordered-phase primitive with no knowledge of
attacks, Battlers, rendering or controls. It splits a large dt at phase boundaries
and exits each phase once. The arena owns phase selection and arbitration;
`ARENA_START` exposes all durations as registry-declared formulas through the
ordinary command editor. World actors share `moveToward` rather than duplicating
movement normalization in the arena. No alternate damage/cost evaluator exists.

Presentation reads the resolved contact and authoritative phase clocks for
tracers, hit flashes, damage labels with velocity/gravity, and aftermath fade.
It never executes damage or advances the action. Enemy skin time is separate
from player execution time, so freezing enemy advancement also freezes its
locomotion animation. The source rig inventory was inspected read-only through
the pinned Blender launcher: Idle, Walk and Run only. This pass adds no skeletal
attack clip and makes no claim to have one.

Native capture exposed a pre-existing screen-Y sign error in the shared
`projectPerspective` helper on an unclipped render surface. Corrected the
TypeScript authority and regenerated Lua/JS outputs. The new optical-axis test
checks an off-center principal point against the shader's screen-Y convention,
rather than round-tripping through the same helper. Damage labels now appear
over their resolved target. Shipping screenshot evidence below found no frame
changes from this fix.

## Verification and limits

`out/combat-lifecycle/` retains native captures and logs. The arena proof covers
anticipation without mutation, movement/clock ownership, ignored repeated input,
contact/cost exactly once, recovery, fixed telegraph destination, dodged lunge,
enemy recovery, lethal contact, aftermath, win/loss cleanup and recovery,
post-terminal save, range refusal and ordinary cancel/pause behavior. The timeline
unit checks contact/recovery boundaries with both a large step and partitioned
steps, invalid durations/dt, zero dt and no replay after completion.

The actual main-host playthrough also uses physical key callbacks to traverse
NPC dialogue, enter combat, choose Attack and Target, observe contact/recovery,
and regain control. It passes; it still emits the known dialogue cursor formula
diagnostic tracked by #1486.

Shipping G1, G2, G3, G4 and full units passed, including seven native Effekseer
assertions. The shared-semantics build-current and Node conformance checks pass.
All 161 Classic and 161 Wide shipping captures match the retained pre-change
captures as decoded RGBA. This is local relative evidence, not canonical G5/G6
acceptance; no golden was recaptured. Editor rendered acceptance remains open.

The playable is still a small, one-skill experiment. Original footage has not
been measured frame by frame, so timing fidelity and exact original pause/
execution arbitration remain unproven. Skeletal attacks, audio, more varied
enemy patterns and final camera/HUD composition remain outside this checkpoint.
#1485 stays open. Native play by the owner is the next feel assessment; tests
establish ordering and invariants, not that the experience feels good.
