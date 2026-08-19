# Summoner Rework — Design Intent

## Core identity

The player is the Summoner. The fielded party is made of summoned spirits, and the Summoner's identity is expressed through what they sustain, direct, lose, and recover rather than through a separate battler body or personal command list.

The battle model should therefore preserve a clear asymmetry:

- spirits take actions;
- the Summoner directs those actions;
- the Summoner stays off-field and has no HP-bearing battler presence;
- shared MP is expedition pressure rather than a second character's spell bar.

## Battle role

The player directs each fielded spirit's action per round. The Summoner has no separate battle verbs and no parallel spell-casting menu.

There is no ordinary mid-battle summoning, dismissal, or sacrifice. Reserve access during battle is exceptional and automatic: the emergency wave described below.

MP exhaustion remains survivable pressure on the manifested party rather than an instant-loss state.

## Wipe, loss, and emergency reserve deployment

### Emergency wave

When the fielded party wipes and reserve spirits remain, a reserve wave may deploy automatically, up to the normal field capacity.

The deployment is free of MP cost. Its price is structural rather than monetary: the fallen field is lost and the party forfeits that round while enemies continue to act.

This should read as a desperate continuation of the same expedition, not as a normal swap command.

### Permadeath

A spirit at 0 HP is downed during battle so ordinary revival remains possible while the fight is unresolved.

A spirit still down when battle ends is permanently lost and converted through the same sacrifice-rate economy used by ritual systems. Feedback should be individual and diegetic rather than a batch accounting message: each loss receives its own reap presentation and log line.

The fielded party should never remain empty while reserve spirits still exist; after battle-side reaping or ritual-side sacrifice, reserve population may be pulled forward automatically when necessary.

### Game over

Game over means that both the fielded party and reserve are exhausted. Shared MP reaching zero is not itself a game-over condition.

## Party, reserve, and row state

Reserve capacity is not a hardcoded battle-system constant.

Each fielded spirit carries persistent front/back row state that is available to formulas and presentation. The existence of row state does not require every combat formula to consume it immediately; it is a reusable positional axis rather than a one-off damage modifier.

The battle UI should show row identity without requiring row manipulation to become a command merely because the state exists.

## Economy

The EXP Bank remains a ritual-facing economy. Battle may contribute to it through permanent loss, but should not expose bank-management as an in-battle subsystem.

Shared MP is expedition pressure and should remain readable without becoming melodramatic. Its broader movement/combat economy is specified in `docs/SPEC.md`.

## Battle presentation implications

The command console is the per-spirit command surface. There is no swap verb for emergency deployment and no dedicated Summoner command panel.

The battle composition needs to present:

- enemy battlers and their combat information,
- the 2x2 fielded spirit grid,
- row identity,
- the shared MP gauge,
- per-spirit commands,
- target feedback,
- emergency-wave feedback,
- battle log timing,
- damage/heal/effect presentation.

`docs/design/battle-windows-brief.md` describes the presentation relationships and ownership boundaries in more detail.

## Shared resource preview

Cost/gain preview should be a property of shared gauge presentation, not of one Summoner screen.

Hovering an action that would spend or grant a gauged resource may preview the affected portion directly on the gauge and append a compact cost/gain readout. The same presentation primitive should serve ritual, shops, item use, and any other surface that exposes the same resource.

## Design constraints

- Do not create a separate Summoner battler solely to justify the class identity.
- Do not turn emergency reserve deployment into ordinary mid-battle party management.
- Do not make permanent-loss resolution depend on presentation timing.
- Do not hardcode reserve size into battle logic.
- Do not introduce battle-only gauge or targeting primitives when shared ones already exist.
- Keep deterministic state transitions in battle/session ownership and let presentation consume the resolved facts and emitted events.
