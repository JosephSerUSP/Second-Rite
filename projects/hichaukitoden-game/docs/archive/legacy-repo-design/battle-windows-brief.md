# Battle Windows — Design Intent

**Context:** `docs/design/summoner-rework.md` and `docs/SPEC.md` §1.2.

## Intent

Battle presentation should use the same data-authored windows system as the rest of the UI without turning cross-cutting combat presentation into fake windows.

The battle view is one composition:

- enemy presentation,
- party presentation,
- command console,
- target feedback,
- transient wave feedback,
- battle log,
- damage/heal popups,
- and screen-space battle effects.

The design succeeds when these parts read as one combat surface while retaining clear ownership boundaries.

## Engine-side prerequisites

The presentation assumes the Summoner battle model described in `summoner-rework.md`:

- the player directs each fielded spirit rather than taking a separate Summoner action;
- emergency reserve deployment is an automatic battle event, not a menu verb;
- fallen spirits may be reaped at battle end;
- front/back row exists as authored battle state even where no combat formula consumes it yet.

Those mechanics belong to battle/session ownership. Windows only present the resulting state and emitted events.

## Window and overlay inventory

### Enemy row

The enemy area presents enemy battlers and any associated name/HP information. Its geometry comes from battle layout data rather than hardcoded scene coordinates.

Enemy sprites are not required to be clipped to the strict window rectangle when their authored position or scale intentionally exceeds it.

### Party grid

The party area presents the fielded 2x2 spirit grid, HP/state information, row identity, and the shared Summoner MP readout.

The grid should remain readable when enemy presentation becomes wider or more spatially ambitious. A change to the enemy area must not silently collapse party/supporter space.

### Command console

The console is the per-spirit command surface. It should reuse the shared command/list presentation system rather than grow a battle-only widget implementation.

### Target overlay

Target reticles are cross-cutting presentation over battlers, not the content of any one window. They should remain driven by the shared targeting model rather than by battle-window-local target logic.

### Wave notice

Emergency reserve deployment warrants transient, legible feedback, but not a persistent extra battle panel. The notice is presentation of a battle event whose mechanics are owned elsewhere.

### Battle log

The log is a short, distinct timing/text strip. Its geometry must not collide with the enemy/party presentation or lower command surface.

### Popups and screen-space effects

Damage/heal numbers and combat effects are not windows. They remain cross-cutting presentation layered over the combat surface.

Weather and other ambient battle effects must respect presentation grouping: battle-space effects may cover the combat area, but should not automatically wash over unrelated UI.

## Shared gauge previews

Cost/gain preview belongs to the gauge widget, not to battle or ritual as a bespoke feature.

When an authored action would spend or grant a gauged resource, the affected portion of the gauge may be tinted and accompanied by a compact cost/gain readout. The same widget should be usable anywhere the resource appears.

## Geometry and ownership

Battle geometry is authored in logical coordinates and consumed through shared layout helpers.

The intended ownership split is:

- battle/session code owns gameplay state and emits resolved events;
- battle layout/window data owns rectangles and configurable presentation numbers;
- shared battler/presentation helpers consume those rectangles;
- renderer code owns outer scaling and effect composition.

No battle scene code should duplicate viewport scaling assumptions or treat the full screen as combat world space just because it draws battlers.

## Visual acceptance

Judge the combined battle surface using:

1. exact authored window geometry,
2. screenshots at intended viewport sizes,
3. real sprite bounds and authored battler placement,
4. deterministic gate output where the requirement is mechanically observable,
5. owner playtesting for composition and feel.

A mockup is evidence of intent, not a pixel-exact baseline.

The presentation should preserve:

- readable enemy and party lanes,
- visible shared MP pressure without a dedicated Summoner panel,
- non-overlapping command/log surfaces,
- target feedback anchored to the actual battlers,
- effect/weather isolation from unrelated UI,
- and stable centralized scaling/filter behavior.
