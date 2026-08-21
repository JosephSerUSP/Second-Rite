# View-weighted atlas allocation

`view_weighted_atlas.py` explores a bounded-camera alternative to ordinary world-area UV density.

The motivating measurement came from a fixed-eye town specimen where most atlas texels were spent on faces that contributed little or nothing to any native view. The production direction is **not** binary visibility culling. It is a continuous blend between world-space fairness and expected presentation demand over an authored camera envelope.

## Core model

For each face:

1. measure world-space surface area;
2. sample plausible authored camera states;
3. record projected native-pixel area, facing, in-frame state and occlusion;
4. combine expected and peak screen demand;
5. estimate view accessibility from orientation and the movement cost of the camera state that exposes or nearly exposes the face;
6. derive a view-density multiplier;
7. ease between world density and view density with `view_bias`;
8. enforce a nonzero `min_density` floor.

Conceptually:

```text
density = lerp(world_density, view_density, view_bias)
```

`view_density` includes both observed screen demand and an accessibility reserve for faces that are easy to expose but not currently visible.

## Why accessibility matters

Not all invisible surfaces are equal.

A top face seen from slightly below may need only a small pitch/eye change to become important. A wall just outside the frame may need only ordinary projection-window movement. A front-facing face may be temporarily occluded. Those should retain substantially more budget than a face pointing fully away from every authored view.

The current categories are audit labels, not hard allocation buckets:

- `visible-nominal`
- `visible-in-envelope`
- `offscreen-reachable`
- `occluded`
- `near-visible`
- `strongly-back-facing`
- `unreachable` (only when explicitly declared by the caller)

Allocation remains continuous inside and across these labels.

## Camera envelope

A `ViewSample` may vary:

- projection-window X/Y offset;
- eye translation;
- yaw;
- pitch;
- probability/weight;
- normalized movement `cost` from the nominal authored view.

The caller owns how its camera contract is sampled and how different movements map to `cost`. This keeps the allocator usable for a near-fixed side-view camera, a camera with limited authored motion, or a broader free-camera envelope.

Increasing the envelope should naturally make allocation more conservative because additional views can raise expected/peak demand and accessibility.

## Policy controls

`AllocationPolicy` exposes:

- `view_bias`: 0 = world-area fairness, 1 = strongest view weighting;
- `peak_mix`: expected-screen demand vs rare worst-case demand;
- `min_density`: hard world-space floor;
- `accessibility_reserve`: how much easy-to-expose faces retain even before they contribute screen pixels;
- movement, occlusion and offscreen falloffs.

Useful conceptual presets are:

- **free camera**: low `view_bias`;
- **bounded camera**: medium/high `view_bias`, nontrivial accessibility reserve;
- **fixed camera**: high `view_bias`, still with a conservative floor.

Do not make destructive geometry culling an automatic consequence of low atlas weight. Culling is a separate policy and is intentionally absent from this module.

## Blender proof path

`measure_envelope(...)` samples the real Blender camera and mesh. It uses native render dimensions, frame clipping, face orientation and scene ray casts for occlusion.

`allocate_blender(...)` then applies the pure demand model and creates a
`TH_ATLAS` UV layer.

The generic environment exporter exposes the two allocation authorities:

```text
python tools/blender/town_environment_pipeline.py scene.blend \
  --output out/environment --atlas-allocation area

python tools/blender/town_environment_pipeline.py scene.blend \
  --output out/environment-view --atlas-allocation view-weighted \
  --camera-envelope camera-envelope.json --view-policy bounded-camera
```

The envelope JSON is either an array of `ViewSample` records or an object with
`samples`. Each sample must name its authored state and may specify
`projectionWindowOffset`, `eyeOffset`, `yawDeg`, `pitchDeg`, `weight`, and
normalized movement `cost`. View-weighted requests fail without an explicit
envelope. `free-camera`, `bounded-camera`, and `fixed-camera` are the compact
policy presets; an object using the `AllocationPolicy` field names may be
passed when a scene needs an explicit reviewed policy.

The exported `environment.json` contains the selected policy, camera envelope,
per-face demand, packed texel, native screen-demand, UV-island, margin, and
bake-time metrics. Low weight never removes a face; explicit culling remains a
separate operation.

The first packer is deliberately **per-face**. That gives exact density control and a useful research baseline but can spend too much margin and create unnecessary seams. A chart/island-aware packer should consume the same `FaceDemand.density_multiplier` values later; the camera measurement and weighting policy should not need to change.

## Checks

Run the pure policy check without Blender:

```text
python tools/blender/check_view_weighted_atlas.py
```

It proves:

- a slightly inaccessible top surface receives more budget than a fully rear-facing surface;
- `view_bias=0` restores world-area fairness;
- widening the envelope to reveal a surface increases its allocation;
- a front-facing but occluded face remains more important than a hard rear face.

The Blender-backed end-to-end proof compares ordinary area-based packing
against view-weighted packing on the same TH_RENDER mesh, then inspects matched
native renders over the entire authored camera envelope.

The disposable A/B proof is:

```text
python tools/blender/prove_view_weighted_atlas.py
```

It writes the two packages, matched 426x240 frames, source/runtime
comparisons, the facade projection seam proof, and `proof.json` under the
ignored `out/blender/view-weighted-ab/` directory.

Refs #877 #851 #837.
