# Hospital slice working entry point

The design boundary is [St. Francis, Day 4](docs/vertical-slice.md), tracked by
[#1463](https://github.com/JosephSerUSP/Second-Rite/issues/1463). Start with the
[build brief](docs/build-brief.md), then the reference contract. Delivery status
belongs in the milestone issues and verification reports.

This directory is an ordinary standalone Thestra Project. Its bounded starter
uses original, lit proxy rooms and a compiler character to exercise entry,
elevator routing and persistent basement lock-in. Those fixtures are not
reconstructions of Hospital geometry or Aya. The title and HUD label them.

`reference/canonical-start.json` owns snapshot identities. `reference/route.json`
owns route dependencies. `starter.json` binds a small subset to Maps and explicitly
prototype stats/geometry. `tools/compile_starter.py` generates the corresponding
runtime data; edit the inputs, then regenerate. The neutral copied engine/Scene
overlays are ordinary authored Project data. No runtime code reads another game
Project, and no private reference media is needed to stage or validate.

```text
python projects/pe-day4/tools/prepare_starter.py
```

That one command checks the sources/data, stages, validates, runs the actual-host
proof, retains captures/logs/timings, and restores the playable main. Individual
commands are also available:

```text
python projects/pe-day4/tools/verify_reference.py
python projects/pe-day4/tools/test_reference.py
python projects/pe-day4/tools/compile_starter.py --check
python projects/pe-day4/tools/verify_starter.py
node tools/ci/stage-project-gates.js --project projects/pe-day4 --output out/hospital-start/play
"C:\Program Files\LOVE\lovec.exe" out/hospital-start/play validate
"C:\Program Files\LOVE\love.exe" out/hospital-start/play
```

To regenerate data, omit `--check`. To run the actual-host proof, copy staged
`main.lua` to `player-main.lua`, replace staged `main.lua` with
`tools/starter-proof.lua`, and run that stage. Restore the real main before play.
The `hospital slice starter` workflow performs these checks and retains the log.

Arrow keys move; Enter interacts/confirms; Down selects the basement in the
elevator menu. F5/F6 save/load. The blue door is the route interaction in each
proxy area. The basement door explains the current boundary. This starter does
not grant completion, restore power or run combat.

Snapshot level, inventory quantities and equipment slots load through existing
new-game and Event commands. HP/PE, gun parameters, loaded rounds, progression
and attack timing are not established as original-faithful by this starter.
Read the prototype policy in `starter.json` before using it for balance.
