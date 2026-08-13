# MP economy experiment lab (#376)

Development/balance tooling only. Nothing in this directory is loaded by production gameplay.

Run from the Project root:

```bash
node tools/balance/test-mp-economy-lab.js
node tools/balance/mp-economy-lab.js
```

The lab writes `tools/balance/mp-economy-results/runs.json` (full machine-readable timelines) and `report.md` (comparison evidence). Pass an alternate scenario JSON and output directory as positional arguments to consume another explicit trace, including a future #374 encounter schedule.

## Trace vocabulary

A trace is an ordered `events` array. Supported events are:

- `{"type":"step"}` — ordinary traversal; intentionally free in the experimental economy.
- `{"type":"step","veil":true}` — one consecutive Veil step.
- `{"type":"battle","rounds":6}` — one encounter at this point in the route; `rounds` only matters when the Battle Strain toggle is enabled.
- `{"type":"mp_up","amount":100}` — injected experiment-only permanent Max MP increase, capped at 9999 and restoring the applied increase like production `max_mp_plus`.
- `{"type":"milestone","label":"stairs"}` — records MP/Max MP without changing them.

There is no RNG in the simulator. A future encounter lab can therefore emit or translate its authoritative encounter timing into these explicit `battle` events, and #366/#375 traces can be correlated by sequence/milestone without exposing hidden encounter state to a player policy.

## Feasibility, not a production failure rule

Every attempted MP spend records its requested cost, paid cost, available MP, affordability, and shortfall. If the current experiment state cannot afford the full requested cost, the lab pays **zero**, marks that event and run `blocked`, and stops the trace. This makes the candidate configuration explicitly infeasible without silently modeling partial payment or choosing what the shipped game should do when MP is insufficient.

Opening Max MP must already be within the current 0–9999 experiment domain. Injected MP Up still caps at 9999 and restores only the increase actually applied by that cap.

## Production facts vs experiment assumptions

The lab's MPD profiles are explicit. The authored examples are grounded in current data: Saban/Moa has MPD 1; Pixie has MPD 3, making the Floor-1 teaching pair MPD 4. `heavy-full` is deliberately synthetic. Production `party.mpd` is the sum of living active-party MPD, including the MPD floor/trait semantics; this lab does not create battlers or copy the trait engine.

Battle Strain mirrors the current authored bands exactly for arithmetic comparison: rounds 1–5 free, 6–9 ×4 party MPD, 10–14 ×8, 15+ ×16. It is a toggle, not a production change.

The default `first-stratum-like` route is representative, not canonical. Current Floor 1 is generated/authored content, so the fixture makes its encounter and Veil schedule explicit instead of pretending there is one authoritative path through the generated map. The synthetic route exposes 5/10/20-step Veil bursts and is intended to be edited freely.

No simulator output proves fun. The classifications (`always-on`, `unusably costly`, `plausibly burst-oriented`) are structural heuristics tied to the tested burst's fraction of opening Max MP and are evidence for later human/player-equivalent playtests, not design verdicts.
