# Spike harness for #841

Evidence generator for
[`docs/reports/world-presentation-and-spatial-ownership-audit-2026-08-20.md`](../../../docs/reports/world-presentation-and-spatial-ownership-audit-2026-08-20.md).

**This is not a gate and not production tooling.** It is a standalone LÖVE
project that adds the repository's `runtime/` to `package.path` so it can drive
the *real* `presentation.retro_mesh_shader` world shader and the *real*
`presentation.effekseer` world-camera matrices against its own synthetic scene.
It writes PNGs and a log to an output directory and quits. It modifies nothing.

```bash
lovec tools/spikes/841 <repoRoot> <outDir> <case>
```

`<repoRoot>` is the checkout root (the directory containing `runtime/`).
`<outDir>` must already exist; use a scratch directory, not the repo.

| Case | What it establishes |
| --- | --- |
| `capability` | LÖVE 11.5 depth-attachment, retained-depth-reuse, depth-sampling and MSAA limits; where anti-aliasing can live without softening a pass-ownership boundary |
| `temporal` | held environment colour+depth vs 60 Hz actors, static and moving camera, with a deliberately non-atomic negative control |
| `projection` | that the world shader's `viewportCenterX` uniform *is* an off-axis frustum shift; that Effekseer agrees; parallax signature vs camera follow; `vertexSnapPixels` interaction; the #836 × #837 misalignment |
| `cost` | per-pass timings and render-target memory for the split-pass shape at classic and wide surfaces |

Whole-frame cost on real content comes from the production profiler instead:

```bash
node tools/ci/stage-project-gates.js --output <gateRoot>
lovec <gateRoot> profile-3d 8 120 current forward
```

`forward` matters — a stationary run reports `nearClipMs`/`meshUploadMs` as zero
because the pose cache hits every frame.

## Traps this harness hit

- LÖVE puts the game directory in `arg[1]`; the spike's own arguments are the
  **last** three entries.
- `love.graphics.draw(canvas, 0, 0, 0, 1/3, 1/3)` with a linear filter
  point-samples. It is not a downsample and anti-aliases nothing.
- GPU timings are meaningless without a readback to force a sync, and without
  taking the minimum of several rounds.
- A fixture where the actor is never actually occluded makes every temporal
  variant score identically and look healthy.
