# Encounter-model lab: deterministic comparison

This is tooling-only evidence from the synthetic falsification fixture, seed `374`, 240 committed steps, calibration target `0.10` encounters/step (mean 10 steps). It is not a production-model recommendation.

The same tool has an engine-hosted acceptance mode for the real First-Stratum Map 2 path: `preview-map-inspection -> engine.map_inspection -> exploration.loadMap`. Hosted verification is responsible for actually executing that fixed-seed path; the experiment does not include a copied Map 2 topology or Python-side map compiler.

| model | encounters | mean spacing | consecutive | longest dry spell |
|---|---:|---:|---:|---:|
| chance | 21 | 10.91 | 1 | 43 |
| countdown | 21 | 10.91 | 0 | 16 |
| pressure | 22 | 10.43 | 0 | 13 |
| presence | 21 | 10.91 | 0 | 19 |

The structural comparison remains useful: the memoryless control admits both a consecutive encounter and a 43-step dry spell; countdown and pressure suppress those extremes by construction; the spatial model's spacing emerges from topology pursuit/contact rather than a direct encounter clock. These rows do not select a winner.

## Spatial falsification evidence

The trace now decomposes separation rather than reporting one ambiguous delta. For each committed step, authoritative evidence records topology distance before player movement, after player movement, and after presence pursuit, yielding separate `playerMovementDelta` and `presencePursuitDelta` values.

The synthetic branch falsifier fixes the presence at `(1,1)` and the player at branch cell `(3,5)`:

- player moves to `(3,4)` → topology distance increases (`+1`): an evasion/away move is mechanically observable;
- player moves to `(2,5)` → topology distance decreases (`-1`): an approach move is mechanically observable.

Presence movement remains constrained to passable cardinal edges. Exact presence state and separation are authoritative experiment evidence only. `playerFacing.directionalThreat` continues to expose only a coarse N/E/S/W sector, proximity band, and normalized strength for future #366/#375 player-equivalent observation.

## Presence calibration limits

Presence pursuit is fixed at **2.0 topology moves per committed player step**. `--rate` changes minimum spawn distance while pursuit speed remains fixed, so comparable encounter counts at seed 374 do not establish general rate normalization.

Fixed synthetic-fixture characterization over 240 committed steps:

| rate | target mean | min spawn distance | seed 37 | seed 374 | seed 811 |
|---:|---:|---:|---:|---:|---:|
| 0.05 | 20.0 | 10 | 18 | 19 | 17 |
| 0.10 | 10.0 | 5 | 25 | 21 | 16 |
| 0.20 | 5.0 | 3 | 23 | 26 | 24 |

The variation—and the lack of a simple monotonic normalization story across this small sample—is exactly why these numbers are characterization rather than a calibrated production promise. A production decision still needs real-route and player-equivalent evidence.

No production encounter behavior, Battle file, Veil economy, HUD/audio/FX, or G5/G6 reference changes are part of this lab.

Agent-Signature:
  platform: ChatGPT
  model: GPT-5.6 Sol
  role: integration
  task: "PR #380 return-pass correction"
  base: 6a300186
