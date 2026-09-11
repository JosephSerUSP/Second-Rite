# Metro Mover Pilot

A minimal, audit-driven seed for Stratum III (Sao Paulo metro) and for the
generic kinematic mover primitive. It answers PR #1101's audit with a fresh,
small implementation rather than a patch on the original draft.

## Scope (deliberate)

Two safe maps prove the contract end to end:

- Map 32 (Luz Station Pilot): a two-car platform shuttle on a ping-pong
  circuit, plus stairs down to Bras and a station attendant.
- Map 33 (Bras Substation Pilot): a power/key/gate/vault/seal chain
  (breaker -> locker -> Klabin gate -> vault + titan seal -> Santa Cruz
  shortcut), plus open stairs back to Luz.

Out of scope on purpose: multi-line network art, OBJ train models,
sunken track geometry, multi-car gangway visuals, the full boss battle,
and any dev showcase CLI. The mover event keeps a placeholder sprite and
renders statically; placements (positions, door state) are published and
tested for the visual follow-up to consume. This document states that
plainly so no later reader mistakes the pilot for the finished stratum.

## Engine contract

`runtime/engine/mover_runtime.lua` is project-agnostic. It knows
waypoints, speeds, modes, consist offsets, door models, and timing. It
does not know metro lines, track materials, platform sides, or model
file naming. `tests/test_metro_stratum.lua` asserts the absence of that
knowledge by scanning the module source.

Key rules:

- Authored car cells must be walkable floor. The mover only forbids; it
  never permits over the grid.
- Boarding needs docked phase plus open doors on a car cell. Leaving
  needs the same, onto a car cell or an orthogonally adjacent cell.
- While closing/moving/opening (or with doors shut), onboard movement
  is locked.
- Offsets are 2D (dx, dy), so Y-axis paths work without engine edits.
- Visuals are data: per-car openModel/halfModel/closedModel/sprite.
  There is no path construction in the runtime.

## Save contract

`session.movers` (phase, segment, timer, position, door state, onboard
flag, player offset) is part of the map snapshot in
`engine/savegame.lua`. A save taken mid-transit restores the platform
under the player. Loading reconciles a stale onboard flag against the
restored consist instead of trusting it blindly. The test suite saves
while moving and rides the restored platform to its dock.

## Test strategy

Puzzle tests run the AUTHORED command trees through a helper that
evaluates each real CONDITIONAL_BRANCH condition and executes the taken
branch, skipping only presentation TEXT. Both the denied and granted
branches are asserted, so the conditions, flag names, gold amounts, and
transfer targets under test are the authored ones. There is no
synthetic flag injection for assertions; predecessor steps run their
own authored events.

## Visual gates

This pilot touches no global renderer behavior. The only presentation
change merges the ride camera flourish (fractional dolly, sway pitch)
into the existing focus override, and it is nil-safe: maps without a
ride resolve the identical camera. No tilesets, models, or sprites were
added, so G5/G6 see no new pixels.
