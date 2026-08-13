# Encounter model lab (#374)

Development experiment only. This tool does **not** replace or call the production encounter system. The control policy mirrors current `ROLL_ENCOUNTER` semantics: one independent random draw per committed step.

For a real Map run, the lab asks the existing `preview-map-inspection` host to resolve the Map with `engine.map_inspection -> exploration.loadMap`, then consumes only its generated grid/entrance/exit. The lab therefore does not compile or generate Maps itself. It finds a deterministic entrance-to-exit route on that resolved topology and repeats it to the requested step count.

Run from the repository root (Windows example):

```text
python tools/encounter-lab/encounter_lab.py --lovec "C:\Program Files\LOVE\lovec.exe" --map 2 --map-seed 37402 --seed 374 --steps 240 --out tmp/encounter-trace.json --report tmp/encounter-report.md
python tools/encounter-lab/encounter_lab.py --synthetic --seed 374 --steps 240 --out tmp/synthetic-encounter-trace.json --report tmp/synthetic-encounter-report.md
python tools/encounter-lab/encounter_lab.py --synthetic --self-test
python tools/encounter-lab/encounter_lab.py --engine-self-test --lovec "C:\Program Files\LOVE\lovec.exe"
```

`--engine-self-test` is the acceptance seam for the real First-Stratum topology. It invokes Map 2 at fixed map seed `37402` through the existing LÖVE `preview-map-inspection` path, checks a cardinal/passable entrance-to-exit route, resolves the same fixed seed twice for determinism, and runs the four experiment policies on the returned topology. Hosted verification executes this command; there is no copied Python Map 2 topology or second map compiler.

The four policies are `chance`, `countdown`, `pressure`, and `presence`. `--rate` is a calibration target, not a proposed production field. Countdown bounds the next distance around the target mean; pressure randomizes a threshold around the same mean.

## Spatial evidence boundary

The spatial trace deliberately separates `authoritative` from `playerFacing`. Exact presence coordinates, topology path, movement, and separation decomposition stay under `authoritative`. Each step records three distances:

- before the player's committed move;
- after the player's committed move;
- after the presence pursuit move.

This yields distinct `playerMovementDelta` and `presencePursuitDelta` fields. The synthetic self-test contains deterministic branch examples where moving away increases topology distance and approaching decreases it. Presence pursuit itself remains passable-cardinal topology movement.

The candidate player-facing compass seam receives only N/E/S/W sector, coarse proximity (`far`/`mid`/`near`/`contact`), and normalized strength under `playerFacing.directionalThreat`. Nothing here implements a HUD or exposes hidden coordinates to player policy.

## Presence calibration limit

Presence pursuit is fixed at **2 topology moves per committed player step**. The rate parameter changes the minimum spawn distance but does not independently normalize pursuit speed. Therefore comparable encounter counts at one seed/rate are fixture evidence, **not** a general encounter-rate-normalization guarantee.

The generated report includes a small characterization over fixed seeds `37`, `374`, `811` and rates `0.05`, `0.10`, `0.20`. This is descriptive evidence only; the lab does not choose a winning encounter model or production calibration.

`modifier(step, channel) -> multiplier` remains the generic experimental seam for later #372 Veil work. The default is 1.0. This lab intentionally contains no MP cost, Veil economy, battle activation pricing, final detection formula, production encounter rewrite, or Battle file edit.
