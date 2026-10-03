# THE THIRD BELL — validation state

What was actually verified, by what, and what was not. Nothing here is
inferred from "it should work".

## Verified

| Check | Command | Result |
|---|---|---|
| Engine validation (G1) against the staged campaign | `lovec . validate` on the Test Play stage | **VALIDATE OK**, zero warnings |
| Save/load round-trip | `lovec . savetest` on the stage | **SAVETEST OK** |
| Content reachability report | `lovec . reachability` | only pre-existing base-game finding (Town Portal common event is item-driven, which the report cannot see) |
| Campaign spine reachable New Game → ending | `node authoring/check-spine.js` | **CAMPAIGN SPINE OK — 19 stages, 3 endings, no softlock found** |
| Boot smoke | staged campaign under `THESTRA_CI_FAIL_ON_ERROR=1`, 35 s | ran to the timeout without a runtime error; no crash screen |
| Asset mirror + launcher path | `robocopy` mirror used by `PLAY_CAMPAIGN.cmd` | exit 0, 19 asset trees present |

### The spine audit has teeth

`check-spine.js` is only worth its runtime if it can fail. Negative control:
deleting Floor 6's stairs event and re-pointing the Third Bell's gate at the
wrong item made it report exactly those two faults and exit 1. Both edits were
reverted and it went green again.

It asserts each of the 19 authored stages is produced by something in the data,
that Floor 6 has a way back up, that the ending returns the player to a map
rather than stranding a cinematic, and that the ending is gated behind the
Warden's Clapper.

## Fixed during authoring

- **`GRANT_XP target: "all_allies"`** — this engine has no party-wide battler
  ref; the string appears nowhere in the codebase. G1's targeting check does
  not cover this parameter, so it would have failed at runtime, mid-room.
  Replaced with the proven `FOR_EACH living_allies` pattern used by the
  Recovery Light common event.
- **Fifteen authored flags that nothing read.** G1 warned. Rather than
  suppressing the warnings, every one was made load-bearing: the endings now
  read back which optional rooms this particular run visited, and the gate
  guard tracks act progress. The ending differs run to run as a result.
- **Town Portal and Bell Salt were not sold anywhere in the base game.** The
  campaign is priced around retreat, so both went onto Alicia's shelf (the
  Portal only after your first return).
- **Floor 6 had no way back up** in the base game. It does now.

## NOT verified — untested seams

These are the honest gaps. No autonomous play harness exists in this repo, so
nothing below has been walked by a player or a robot.

1. **Combat balance, everywhere.** The Eternal Warden (Hyperion 13 + two Wisps
   9, with a one-time relight) has never been fought. Neither has the Red
   Dragon at the level this compressed ramp will deliver the player at. The
   compression from three incursions to two means the player reaches Act II
   roughly one incursion under-levelled versus canon pacing — deliberate, but
   unmeasured.
2. **Whether 60–90 minutes is right.** Estimated from beat count and floor
   sizes, not timed.
3. **Procedural spawn placement of the authored rooms.** The Rusted Choir, the
   Weighing Room and the Half-Contract use `spawn: Random` wall events, the
   same mechanism as the base game's authored rooms. They are guaranteed a
   legal position, not a *findable* one, and a player could plausibly cross a
   floor without meeting one.
4. **The MP economy across the whole run.** The Choir charges 25 MP and the
   Weighing Room can refill the pool; whether that nets out to real expedition
   tension or trivialises it is unknown.
5. **Text rendering.** No line in the ending sequence has been seen on screen.
   Long `TEXT` bodies and the credit string pictures may wrap badly.
6. **The epilogue town.** Alicia, Laura and the gate guard have an ending-aware
   register; the other town hubs do not, and will speak their mid-campaign
   lines after the ending.
7. **Battle effects** are disabled in any worktree lacking the gitignored
   Effekseer shim. Play from the primary checkout.

## Thestra gaps this campaign hit

Recorded here rather than worked around in engine code, per the discipline that
a campaign may not add engine commands to make its story work:

- **A campaign cannot end.** `QUIT_GAME` and `SCENE_EVENT` are scene-context
  only, so no map or common event can return the player to the title screen or
  close the game. Every authored ending in this engine must currently dead-end
  into a map. This is a generic gap — any Project with an ending has it — and
  is the one thing here worth an Issue.
