# Experimental spatial boundary (#1088)

These are compiler/contract experiments, not shipping Maps. No runtime or Studio
consumer imports this directory. Read the dated report in
`docs/reports/resolved-spatial-spike-2026-09-09.md` for the verdict and limits.

From the repository root:

```powershell
node --test tests/fixtures/spatial/spatial.test.js
node tests/fixtures/spatial/build.js --check
node tests/fixtures/spatial/build.js --probe --check
```

The first two commands need only Node and checked-in inputs. The third stages an
ordinary Project through `stage-project-gates.js`, installs a test-only `main.lua`
in `out/spatial-1088-stage`, and invokes LÖVE (override its path with `LOVEC`). It
executes the real generator twice with seed 97531, checks a different seed changes
the topology, parses the exported collision through the runtime OBJ importer,
and resolves the real `rpg_ortho` camera. It compares evidence without overwriting
the checked-in evidence. The disposable stage is retained for inspection; its
`main.lua` is a probe, so it is not a reusable gate stage.

`node tests/fixtures/spatial/build.js` regenerates derived JSON from the recorded
runtime evidence. `--probe` refreshes that evidence using installed LÖVE, and
`--capture` explicitly re-extracts the fixed commit named in `build.js`. Capture
does not adopt current dirty files or open/mutate a `.blend`. None of these are
golden capture commands.

`resolved_spatial.json` has a closed common vocabulary: Z-up XYZ; identified
bodies with boxes or exported mesh references; identified point, box-volume and
segment features. All positions are world coordinates; box sizes are full
extents centered on position, and segment ends are absolute. Box bodies provide
both primitive display geometry and collision volume. Mesh bodies reference
separate render/collision exports consumed through the existing OBJ importer.
Features describe locations/volumes/connections, not interaction behavior.
There are no parents, transforms with implicit inheritance, freeform tags, genre
flags, Event fields, camera policies, or runtime authoring-application calls.

`resolved_structure.json` is intentionally a separate, typed source-family
product where needed. `resolved_view.json` demonstrates joining project-owned
Event placement to physical features. Tactical legal moves are a further
consumer product. Source and resolved artifacts are not dual authorities:
edit source, regenerate output, and let `--check` reject drift.

`provenance.json` binds the committed authoring evidence to Git revision and
SHA-256. `runtime-provenance.json` identifies the five principal runtime modules
exercised by the probe, not a complete exported-game dependency manifest.
The canonical stage still loads the local Project and its normal dependencies;
the probe substitutes the captured dungeon policy and compact fixture input.
This is deterministic evidence on the installed LÖVE/Lua implementation, not a
claim that Lua RNG sequences are portable between implementations.
