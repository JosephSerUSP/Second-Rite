# World-presentation ownership audit probe (#841)

This is an **isolated architecture probe**, not production renderer code and not a
new Map format.

Run it with the repository-pinned LÖVE 11.5 runtime:

```bash
love tools/audits/world-presentation-ownership
```

The compact executable fixture concentrates on the framebuffer/temporal/projection
questions that cannot be settled from source inspection alone. The broader
world-object ownership census is in the dated report; `freeform-pressure.json`
separately carries the non-grid spatial-family pressure case.

Controls:

- `1` — static camera/projection control;
- `2` — moving camera with the **held** environment optical snapshot (correct 15/60 case);
- `3` — deliberately wrong **current** 60 Hz camera over stale environment depth;
- `A` — toggle color-only edge smoothing before live actors;
- `D` — toggle the deliberately wrong retained-depth mutation control (live actors write into the held environment depth);
- `V` — toggle final composite / environment-only debug view;
- `M` — cycle requested MSAA `0 -> 2 -> 4 -> 8` and rebuild attachments;
- `S` — capture the current frame to the LÖVE save directory;
- `R` — reset deterministic time/state;
- `Esc` — quit.

At startup the fixture prints a capability probe containing:

- LÖVE version and renderer information;
- custom depth attachment creation/rebind success;
- requested and actual MSAA for color/depth Canvases;
- same-sample final-color + retained-depth rebind result;
- single-sample color + tested-depth rebind result (a sample-mismatch control whenever the tested depth Canvas actually has MSAA).

The environment refreshes every fourth 60 Hz frame. In mode 2 the live actor still
updates every frame, but uses the camera/projection snapshot that produced the held
environment depth. Mode 3 intentionally violates that rule so the stale-camera /
stale-projection failure is visibly detectable rather than asserted only in prose.

`D` is another negative control. Allowing a live actor to write into the retained
environment depth contaminates the snapshot with an old actor position. The held
environment attachment must therefore be treated as read-only unless an explicit
working-depth strategy owns live-vs-live depth.

`freeform-pressure.json` is not a proposed Thestra schema. It exists only to ask
which current consumer seams survive when authored spatial truth is transform/path
based rather than a cell grid.

## Evidence run

Record stdout plus captures for at least:

1. MSAA requested 0, color-AA off/on;
2. MSAA requested 4, recording actual sample counts and rebind results;
3. modes 1, 2 and 3 at matching actor times;
4. mode 2 with `D` off, then the retained-depth mutation negative control with `D` on;
5. classic-sized and wide-sized targets if the probe is later extended to profile switching on the target GPU.

Do not recapture canonical G5/G6 goldens from this tool.

## Pure numerical oracle

The stale-camera / stale-projection math can be checked without a GPU:

```bash
lua tools/audits/world-presentation-ownership/projection_oracle.lua
```

The checked-in `projection-oracle-results.txt` records the 2026-08-20 audit run.
