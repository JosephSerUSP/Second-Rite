# First-Stratum expedition horizon gauntlet

This owner-playtest compares opening Summoner MP while holding the Second Gate
Project content and current gameplay rules constant:

| Candidate | Starting MP | Purpose |
| --- | ---: | --- |
| `control-3000` | 3000 | Current authored control |
| `intermediate-1800` | 1800 | Intermediate pool |
| `low-900` | 900 | Low pool |

Only `system.summoner.startMp` changes as a gameplay variable. Each profile also
uses a unique LÖVE save identity in its disposable Project, so no run reads or
writes the canonical `SecondRite` save profile or another candidate's saves.
`run-cards.json` records source commit, canonical Project hashes, each candidate's
exact selected data digest, and its validation and launch evidence.

## Validate and play

Run from the repository root. The selector verifies the canonical Project
against its recorded source hashes, copies it into a disposable temporary
Project, applies one immutable candidate overlay, checks the selected data
digest, and launches through the ordinary `studio/editor/project-cli.js play`
path. The temporary Project is removed after LÖVE exits; canonical Project
files and overlay files are never mutated during a run.

```powershell
node projects/experiments/gauntlet-expedition-horizon/gauntlet.js verify
node projects/experiments/gauntlet-expedition-horizon/gauntlet.js validate
node projects/experiments/gauntlet-expedition-horizon/gauntlet.js play control-3000
node projects/experiments/gauntlet-expedition-horizon/gauntlet.js play intermediate-1800
node projects/experiments/gauntlet-expedition-horizon/gauntlet.js play low-900
```

Run one candidate at a time. The launcher refuses to start a candidate if its
LÖVE window or selector process is already running. Start a new game for every
run. Keep the party and equipment the same; for the cleanest opening comparison,
keep the starting Saban-only party and do not recruit the optional Cerberus
(MPD 6) on Floor 1. Register for the Crossing Writ, enter the Labyrinth, and
explore Floor 1 until you first feel an urge to return. Decide to return or
continue as you naturally would and record what caused the decision.

Controls use existing defaults: Arrow keys or WASD move and turn in the map;
Q/E strafe; Enter interacts/selects; Escape or Backspace backs out. Floor 1 is
procedurally generated, so room layouts and encounters may differ between fresh
runs. The authored route and rules remain shared; compare the felt horizon
qualitatively rather than treating the runs as deterministic replay.

## What this does and does not test

The current authored `exploration.step` flow charges the combined MPD of living
manifested creatures on each successful dangerous-map step. This gauntlet tests
opening pool size under that implementation. It does not settle the pending
#372 battle-activation or Veil hypotheses. The First Stratum currently has no
authored Max MP Up reward, so this pass does not evaluate #373 reward timing or
size. Those remain separate owner decisions.

## Owner rating

After each run, fill the matching entry in `owner-rating.json`. Record the first
return urge, MP remaining, reason, decision, desire to push/return, perceived
unfairness, and memorable surprise. Rank the candidates after playing all
three. The rating file starts pending; validation and boot evidence cannot
stand in for owner play.

These candidates remain isolated evidence. Nothing is registered in canonical
Second Gate data, and no profile is promoted automatically.
