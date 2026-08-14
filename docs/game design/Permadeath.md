# Permadeath

> **Intent, not status.** This document owns the game-design rule and its
> invariants. `docs/ENGINE-STATE.md` owns implementation inventory;
> `docs/SPEC.md` owns reviewed current behavior; GitHub Issues own delivery work.

**A creature that is KOed when a battle ends passes away, permanently, unless a
valid death ward saves it.**

That is deliberately simpler than an earlier Max-HP-decay concept. A second
hidden/slowly recoverable life resource asks the player to track another meter
without producing proportionate tension. KO-at-battle-end is legible: recovery
inside battle matters, and leaving a creature down when the outcome resolves is
the dangerous choice.

## Resolution boundary

Permadeath resolves once the battle outcome is known. Victory/escape may require
post-battle reaping of creatures still KOed; defeat does not need a second loss
ceremony when the run itself has already failed.

For each creature that would be lost:

1. evaluate eligible death wards deterministically;
2. if no ward saves it, bank the intended sacrifice/legacy value using the same
   economy rather than treating the creature as worthless;
3. resolve the creature's removal authoritatively once;
4. presentation may stage the visible farewell, but may not decide after the
   fact whether the creature actually died.

The exact command/event names are engine contract, not game-design authority.

## Death wards

Equipment, passives, or innate traits may protect a creature from the final
reaping step. The design recognizes four useful behavioral shapes:

| mode | behavior | consumption |
|---|---|---|
| `relic` | unconditional reusable protection | not consumed |
| `charges` | protection with a finite per-instance charge pool | consumes one charge; source may break at zero |
| `ward` | one-use prevention of the death | consumed |
| `revive` | allow the death beat, then restore the creature | consumed |

A ward may specify how much HP is restored, how many charges it begins with, or
a level cost when surviving is meant to have a lasting price. Exact defaults
belong to authored/system data rather than this design document.

## Candidate ranking

When more than one protection can save the same creature, prefer the least
expensive valid save. A reusable/innate protection should not cause a scarce
consumable ward to be spent needlessly. A charge source with no remaining
charges is not a candidate and must not block another valid protection.

The ranking must be deterministic and inspectable; source iteration order must
not decide which valuable ward disappears.

## Per-instance mutable state

Finite ward charges belong to the concrete creature/source instance. They must
never be stored by mutating shared loader/item definitions, because that would
make spending one copy alter every copy that refers to the same authored object.

Ward state that persists beyond a battle must round-trip through normal save
state with the battler/source provenance needed to identify it.

## Presentation requirements

Death wards must be legible at both decision time and resolution time:

- before committing to deeper exploration, the player should be able to inspect
  that a creature has a ward and any finite charges that are legitimate player
  knowledge;
- when a ward saves a creature, the presentation should clearly communicate the
  save and any consumption/break/remaining-charge consequence;
- presentation consumes resolved ward facts and never recomputes the death
  decision.

Delivery of that player-facing work is tracked by #405. The broader composable
trait/interceptor architecture, including death-ward semantics as a pressure
test, is tracked by #308.
