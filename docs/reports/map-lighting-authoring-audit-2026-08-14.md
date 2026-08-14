# Map lighting authoring audit — 2026-08-14

Point-in-time evidence for #467, audited against `main@9ec8e24c5b57cb761f5a14f89552d89f09f27a64`.

This report is evidence and a proposed composition model. It does not change runtime, Studio, authored map data, or visual references. `docs/SPEC.md` remains the living reviewed engine contract; implementation follow-ups should update it when the new composition semantics land.

## Executive conclusion

The repository currently has **one good semantic light-source model, one legacy absolute painted-light model, and two presentation paths that do not yet agree about how those facts compose**.

The strongest current architecture is already visible:

```text
authored fixed-map lightObjects
        +
tileset/generator emitsLight policy
        ↓
resolved semantic light sources
        ↓
deterministic occlusion-aware vertex bake
        ↓
static vertex light field
        ↓
material/source color modulation
        ↓
orientation/material modulation
        ↓
runtime-only player light + fog
        +
material emission
```

Current `engine/lighting.lua` is a compact deterministic source-to-vertex bake. Current Studio has already gained a browser-side authoring counterpart, `ThestraViewportContract.bakeAuthoringLighting()`, and the Three viewport rebakes it in the animation frame while a Light object is dragged. **Responsive light-source authoring therefore no longer requires waiting for a LÖVE subprocess.** LÖVE remains the authoritative resolver/verification path, not the interaction loop.

The remaining architectural defect is `map.light`. It is still authored as an **absolute final RGB vertex field** with a full-white neutral/default. Runtime source baking creates a separate `runtimeLight`, and the renderer chooses:

```lua
mapData.runtimeLight or mapData.light
```

so the two representations compete. A map containing both source lights and painted lighting does not currently mean "bake the sources, then art-direct the result"; the source bake wins and the painted field is ignored.

The recommended resolution is:

> **Semantic light sources + ambient produce a derived base static-light field. Fixed-map Paint/Blur becomes a secondary signed RGB correction field. Final static light is the clamped sum of the two.**

Working equation:

```text
sourceBase = bake(topology, semanticSources, ambient)
paintCorrection = authored fixed-map signed RGB correction (neutral 0,0,0)
finalStatic = clamp(sourceBase + paintCorrection, 0, 1)
```

When no semantic source/ambient lighting policy is active, the base remains neutral/full-white so currently unlit maps do not become dark merely by adopting the new ontology.

This model is preferable to either keeping a destructive final-field replacement or using a multiplicative correction:

- it lets Paint brighten, darken, or tint an already-dark bake;
- it retains semantic light objects as reusable topology-aware source truth;
- it is compatible with procedural maps, which normally author sources/policy rather than a seed-specific paint grid;
- it can migrate the current absolute `map.light` field **without changing the resolved vertex result** by computing `correction = oldFinal - sourceBase`;
- it lets source-light edits remain frame-responsive in Studio while preserving hand-authored local art direction.

The stored correction should not force an artist to think in negative RGB values. Studio can keep a normal color/brightness painting UX by treating the chosen color as a desired **visible final vertex value** and internally storing `chosenFinal - currentSourceBase`. Blur can likewise blur the visible final field, then derive the correction against the unchanged source base.

Three fidelity is a separate defect. Current world surfaces use `THREE.MeshStandardMaterial` with vertex colors **and** the scene adds Hemisphere and Directional lights. The vertex colors already contain static-light modulation, so this applies an unrelated second illumination model. Runtime also applies a `0.76` side-wall orientation darkening that the browser source bake does not itself model. World surfaces need an unlit/custom authoring material implementing the reviewed static-light equation; neutral editor lights may remain for gizmos/editor-only proxies, but must not relight the world.

## 1. Current representations and owners

| Surface | Current fact | Recommended ownership/lifetime |
| --- | --- | --- |
| `map.lightObjects` | Authored fixed-map point/source lights | **Authored source truth** owned by the Project Map |
| tileset/feature `emitsLight` | Reusable light-emission policy attached to semantic generated fixtures | **Authored source policy** owned by tileset/Project resource data |
| `generatedLightObjects` | Resolved placements produced from generated topology/features | **Derived source instances** for one resolved map/seed/session; reproducible from generator policy + seed/topology |
| `map.light` | Legacy absolute RGB vertex field, neutral/full-white, Paint/Blur target | **Mixed/legacy authored final field**; migrate away from competing final-field semantics |
| `runtimeLight` | Occlusion-aware result of `lighting.bake(...)`; currently shadows `map.light` | **Derived cache/resolved base/final field**, never independent authored truth |
| bake ambient | Default `{0.12,0.12,0.12}` or presentation ambient override | **Semantic environment baseline** and input to source bake; not Paint and not player light |
| proposed paint correction | Does not exist yet | **Authored fixed-map art-direction override**, neutral zero, applied after source bake |
| player light | Camera/player-relative shader uniform | **Runtime presentation modifier**, not static authored environment light |
| fog/distance shading | Shader-time visibility/color modulation | **Runtime presentation modifier**, not static environment light |
| emission/glow maps | Material emissive payload | **Material emission**, separate from environmental illumination |
| wall-side `0.76` | Runtime orientation/material darkening in `viewport_3d.colorAt` | **Resolved orientation/material modulation**, separate from the light field itself |

A critical naming/ownership rule follows: `runtimeLight` may continue to exist as an implementation cache, but the architecture must never require authors to decide between writing `map.light` and letting runtime write `runtimeLight`. There should be one final static-light equation with authored inputs and derived outputs.

## 2. Current runtime pipeline

### 2.1 Source bake

`engine/lighting.lua` owns one deterministic bake:

- input grid/topology;
- zero-based light-source positions;
- RGB source color;
- radius;
- falloff exponent;
- ambient RGB (default `0.12` each channel);
- Bresenham-like line-of-sight wall blocking;
- output `(height + 1) × (width + 1)` vertex RGB field;
- additive source contributions clamped to `1` per channel.

This is a healthy semantic primitive. It knows topology and source semantics, not renderer meshes or Studio.

### 2.2 Fixed maps with `lightObjects`

During map load, exploration combines authored `mapData.lightObjects` with any resolved `session.generatedLightObjects`. When the combined source set is non-empty it writes:

```lua
session.currentMapData.runtimeLight = lighting.bake(grid, lightSources)
```

A saved/presentation ambient override rebakes the same sources with the overridden ambient.

The renderer later selects:

```lua
local light = mapData.runtimeLight or mapData.light
```

This is the core precedence bug. `runtimeLight` does not layer over `map.light`; it replaces it as the selected field.

### 2.3 Fixed maps with painted `map.light` only

If no runtime source bake materializes, the renderer can sample authored `map.light` directly. The legacy Studio Paint path lazily creates this grid at full white and Paint writes absolute RGB values into vertices. Blur averages those absolute final RGBs.

This model is internally coherent only when `map.light` is the sole static-light authority.

### 2.4 Fixed maps with both

The mixed case is semantically ambiguous today. The intended older design prose says:

```text
light objects -> bake -> Paint/Blur overwrite/art-direct the baked field
```

but current implementation does not materialize that composition. Source objects produce `runtimeLight`; `runtimeLight` wins the renderer fallback; independent authored `map.light` is ignored.

Map 1 / St. Maria is the important migration fixture identified by #467: it is a fixed authored map and current Project data contains both a painted field and semantic source-light data. The migration must preserve its resolved appearance intentionally rather than deleting one representation because the other currently wins.

### 2.5 Procedural maps

Procedural/tileset features may author `emitsLight`. `exploration.injectTilesetFeatures()` resolves feature placements and produces generated semantic light sources. Generated maps then bake those sources over the generated topology into `runtimeLight`.

This is a substantially stronger authoring seam for procedural content than a painted vertex grid tied to one generated layout. The author can state that a torch/prefab/generator rule emits light; every seed gets a topology-aware occluded result.

The normal procedural workflow should therefore be source/policy authoring + resolved-seed preview, not Paint over a transient generated grid.

## 3. Current Studio pipeline

### 3.1 Authoritative bundle load

`presentation/editor_renderable_bridge.lua` resolves a transient Map snapshot through the real LÖVE exploration path and attaches:

```lua
result.light = resolvedMap.runtimeLight or resolvedMap.light
```

The browser adapter retains every surface's original/source vertex colors as `unlitColors`, then bilinearly samples the returned light field and multiplies RGB by it. That is a good separation: source/model color is not overwritten as authored light truth.

### 3.2 Frame-local Light-object preview is already implemented

`tools/editor/js/thestra-viewport-contract.js` now contains `bakeAuthoringLighting()`, explicitly documented as the browser-side counterpart of `engine/lighting.lua`. It reproduces:

- default ambient;
- source radius/falloff/color;
- grid wall lookup;
- line-of-sight blocking;
- vertex-grid dimensions;
- additive/clamped channel contributions.

`three-editor-viewport.js` marks live lighting dirty as Light objects move and calls the browser bake inside its animation loop before rendering. Existing tests assert that this path does **not** wait for a runtime bundle refresh.

That already satisfies the most important interaction principle:

> **Dragging/editing a Light must feel like an editor operation, not like invoking a build/bake subprocess.**

LÖVE can still asynchronously resolve/verify authoritative data after authored state commits. It should not be the per-frame feedback path.

### 3.3 Current live preview restores source color correctly

The Three geometry retains both:

- authoritative resolved colors from the last runtime bundle;
- source/unlit colors before the adapter multiplied the bundle light.

Live authoring can therefore relight the existing geometry without asking LÖVE to recreate meshes. This is exactly the right membrane for responsive lighting.

### 3.4 Three currently double-lights world surfaces

Despite the useful vertex-light path, bundle materials are instantiated as `THREE.MeshStandardMaterial({ vertexColors: true, ... })`. The Three scene also adds:

```text
HemisphereLight intensity 2.0
DirectionalLight intensity 2.2
```

This means already-static-lit vertex colors are passed through Three's physically lit material equation under an unrelated editor light rig. Runtime does not use that lighting model.

This is a semantic fidelity defect, not a tuning problem. Lowering the two intensities would merely tune one mismatch to resemble one screenshot.

World surfaces should use an unlit/custom authoring material implementing the reviewed composition directly. Editor-only models/gizmos may keep neutral scene lighting if useful, provided world surfaces are excluded from it.

### 3.5 Orientation modulation is another explicit parity item

Runtime `viewport_3d.lua` samples the static light field and multiplies side-facing wall RGB by `0.76` before building the relevant surface colors. This is an orientation/material presentation rule, not a light source.

The browser source bake only produces a light grid. A parity fixture must therefore verify not just grid RGB values but the final world-surface modulation path, including floor/front-wall/side-wall behavior. Do not bury this difference inside arbitrary Three scene lights.

## 4. Legacy Paint/Blur is not merely disconnected UI

The old canvas code has a coherent but now-obsolete meaning:

- `ensureMapLight()` refuses procedural maps and creates a fixed-layout vertex grid;
- default is `[1,1,1]` at every vertex;
- Paint replaces vertex RGB with the chosen color;
- Blur runs a local 3×3 average over the current absolute field;
- the 2D renderer multiplies the map appearance by this field.

Because the visible authoring workspace is now Three and the legacy canvas is hidden, those pointer bindings are inaccessible in normal authoring. But reconnecting them unchanged would be the wrong fix: their data model assumes Paint owns the final field.

The implementation needs a new neutral lighting-edit command surface in the Editor Scene/Three workspace whose persisted meaning is the new art-direction layer.

## 5. Composition candidates

### Candidate A — absolute final-field replacement

```text
final = paintedField if present else sourceBake
```

Advantages:

- closest to legacy `map.light`;
- normal RGB color picker directly edits persisted values;
- trivial runtime sampling.

Problems:

- semantic source edits and painted values still compete;
- explicit rebake either destroys Paint or leaves stale source changes hidden;
- source objects cease to be live semantic authoring truth after Paint begins;
- awkward for procedural/source-policy workflows;
- reproduces the current architectural ambiguity rather than resolving it.

**Reject as the long-term composition model.**

### Candidate B — multiplicative correction

```text
final = clamp(sourceBase * grade, 0, 1)
neutral grade = [1,1,1]
```

Advantages:

- intuitive as a color grade;
- naturally preserves source-light spatial shape;
- neutral value resembles the old full-white authored field.

Problems:

- values restricted to `0..1` cannot brighten a dark source bake;
- permitting values above `1` fixes that mathematically but makes the normal color picker an incomplete authoring surface and introduces non-color gain values;
- source base near zero cannot be brightened usefully by multiplication alone;
- migration from an arbitrary old final field becomes unstable/undefined where base channels are zero or very small.

**Useful for grading, insufficient as the sole expressive correction layer.**

### Candidate C — signed additive RGB correction

```text
final = clamp(sourceBase + correction, 0, 1)
neutral correction = [0,0,0]
```

Advantages:

- can brighten, darken, and tint;
- bounded correction range `[-1,+1]` is sufficient to reproduce any current `0..1` final value from any `0..1` base value;
- migration is exact: `correction = legacyFinal - sourceBase`;
- remains meaningful when sources move/rebake;
- preserves source lighting as the primary topology-aware layer;
- no division/zero instability.

Tradeoff:

- raw signed RGB is not a friendly artist-facing color control.

That tradeoff is an editor problem, not a reason to reject the storage model. Studio can author a desired final color and derive the correction automatically.

**Recommend Candidate C.**

## 6. Numeric examples for the recommended model

### Ordinary tint / local brighten

```text
sourceBase      = [0.25, 0.20, 0.15]
paintCorrection = [+0.15, -0.05, +0.10]
finalStatic     = [0.40, 0.15, 0.25]
```

The artist brightens red/blue while slightly suppressing green.

### Deliberate darkening

```text
sourceBase      = [0.70, 0.60, 0.50]
paintCorrection = [-0.20, -0.20, -0.20]
finalStatic     = [0.50, 0.40, 0.30]
```

### Clamp behavior

```text
sourceBase      = [0.95, 0.60, 0.20]
paintCorrection = [+0.10, 0.00, +0.20]
preClamp        = [1.05, 0.60, 0.40]
finalStatic     = [1.00, 0.60, 0.40]
```

Clamping occurs **after** source + correction composition. The stored correction is not silently rewritten by saturation.

### Exact migration from an old absolute painted field

```text
current source bake at vertex = [0.25, 0.20, 0.15]
legacy map.light final value   = [0.40, 0.30, 0.20]
new correction                 = [+0.15, +0.10, +0.05]
new final                      = [0.40, 0.30, 0.20]
```

This permits a mechanical migration test: every migrated vertex must reproduce the legacy final RGB within the chosen numeric tolerance before any intentional lighting redesign occurs.

## 7. Author-facing Paint/Blur semantics

Persisting a correction does **not** require exposing signed values as the primary UX.

Recommended Paint interaction:

1. compute current `sourceBase` locally in Studio;
2. sample the current final static field;
3. artist chooses/paints a normal target RGB result;
4. at each touched vertex store:

   ```text
   correction = targetFinal - sourceBase
   ```

5. show the composed result immediately in Perspective and Top Ortho.

Recommended Blur interaction:

1. snapshot the current **final composed** static field;
2. blur the visible final RGB values over the brush neighborhood;
3. convert the blurred result back to corrections with:

   ```text
   correction = blurredFinal - sourceBase
   ```

This preserves the intuitive meaning of Blur: smooth what the artist currently sees, rather than smoothing hidden signed deltas that may interact oddly with a strongly varying source bake.

Useful controls under this model:

- Paint final light color/brightness;
- Blur final static light;
- Clear Paint / reset correction to zero;
- optional display of source-only vs source+paint for diagnosis;
- explicit "resolved runtime preview" refresh when the author wants LÖVE verification, not on every stroke.

Do **not** keep a destructive "Bake sources into Paint" as the normal required workflow. If a materialize/rebase operation is later useful, name it as an explicit ownership conversion and test what happens to corrections.

## 8. Fixed-map and procedural-map UX

### Fixed authored map

First-class authoring should include:

- semantic Light objects;
- ambient/environment baseline where authored;
- immediate local source-bake preview;
- optional Paint/Blur correction over the stable fixed vertex grid;
- source-only/final diagnostic views;
- numerical/runtime verification without blocking ordinary interaction.

### Procedural map

Primary authoring should include:

- tileset/prefab `emitsLight` policy;
- generator source-placement rules;
- ambient/environment policy;
- resolved seed inspection showing generated light sources and baked result;
- reseeding to inspect robustness.

Ordinary Paint should remain unavailable because one generated seed's vertices are not stable Project-authored topology.

If the product later needs "freeze this generated result into an authored map," that operation should explicitly create a stable authored Map snapshot first. Paint can then operate on that fixed ownership just like any other fixed Map.

## 9. Ambient ownership

Ambient is part of the **static environment source bake**, not a runtime camera light and not Paint.

Current exploration can rebake source lights when a saved presentation ambient override exists. The final contract should retain the ability for an authored/runtime Map presentation state to choose ambient, but its meaning must be explicit:

```text
ambient + semantic sources -> sourceBase
```

Changing ambient invalidates/recomputes the derived source base. It does not erase the paint correction.

An unlit map with no active source/ambient lighting policy should continue to resolve to neutral/full-white static illumination, preserving current maps that never opted into dark source lighting.

## 10. Runtime-only presentation modifiers

The following must stay outside the static authoring field:

### Player light

Current runtime passes player-light color/radius/falloff to the world shader from camera/player context. This is a gameplay/session-dependent modifier.

Studio may offer a **preview toggle** using the same semantic settings, but turning it on must not change persisted static light.

### Fog / distance bands

Fog is camera/distance presentation. It may be previewed but must not be baked into source light or Paint.

### Emission

Emission/glow is a material property. It contributes visually without becoming an environmental point light unless a semantic fixture also declares `emitsLight`.

A glowing texture and a torch that illuminates the room are related authoring concepts but not interchangeable runtime facts.

### Orientation/material modulation

Runtime side-wall `0.76` shading is a surface/orientation modulation after static-light sampling. It belongs in the renderer-neutral resolved-surface contract or a shared authoring equation, not inside the source bake and not in author Paint data.

## 11. Three authoring fidelity contract

Pixel identity between LÖVE and Three is not required. **Semantic static-light identity is required.**

For world surfaces, target the conceptual equation:

```text
surfaceRGB = source/material RGB
           × resolved orientation/material modulation
           × finalStaticLight
           + material emission
```

then apply optional runtime-preview modifiers (player light, fog) separately and visibly as preview state.

Consequences:

1. Do not illuminate already-static-lit world surfaces with arbitrary Three scene lights.
2. Prefer an unlit/custom world material that directly consumes texture/material color, vertex/static light, orientation modulation, and emission.
3. Neutral scene lights may remain for editor-only gizmos/proxies if they do not affect world surfaces.
4. Preserve nearest-neighbor/color-space decisions deliberately rather than accepting Three defaults as parity.
5. Explicitly test side-wall orientation shading rather than visually tuning global lights until it "looks close."

## 12. Deterministic parity fixture

Current Node tests are valuable but prove the browser implementation against hand-authored expectations, not directly against the Lua bake for the same fixture. The duplicated source-bake algorithm is acceptable for frame-local authoring **only if drift is mechanically visible**.

Create one shared JSON fixture corpus consumed by both Lua and Node. Include at least:

- empty/no-source baseline;
- custom ambient;
- one colored source;
- falloff 1 vs 4;
- overlapping sources/clamp;
- source near map boundary;
- wall occlusion;
- a small representative floor/front-wall/side-wall surface sample;
- where practical, emission/player-light/fog boundary assertions as separate presentation tests rather than bake outputs.

The authoritative assertion should compare numerical RGB values/tolerances, not screenshots.

A browser algorithm change or Lua algorithm change that breaks parity should fail before an artist discovers it by eye.

## 13. Map 1 migration outcome

Map 1 is the required mixed-representation fixture.

The migration should proceed mechanically, not artistically:

1. resolve the current fixed topology and semantic source bake using the same ambient currently active for ordinary load;
2. preserve the current legacy `map.light` as the target final vertex field;
3. compute per vertex:

   ```text
   correction = legacyFinal - sourceBase
   ```

4. store that correction under the new authored correction representation;
5. stop treating the old absolute `map.light` as a competing fallback;
6. prove that the new composed final vertex field equals the pre-migration legacy final field at every vertex (subject only to explicit current-runtime precedence decisions documented by the migration);
7. only after the structural migration may an artist deliberately rebalance St. Maria lighting.

If current `runtimeLight` means the painted field was not actually visible whenever Map 1's Light objects were active, record both facts in the migration test:

- **current runtime-visible source result**, and
- **legacy authored painted target**.

Do not silently choose one and delete the other. The owner-facing migration should make clear which appearance is being preserved as the canonical pre-redesign result.

## 14. Proposed bounded implementation slices

### Slice A — static-light composition + migration

Engine/data/schema/tests only as far as practical:

- choose/finalize the authored correction field name;
- implement source-base + signed correction composition;
- define no-source/full-white and ambient semantics;
- remove `runtimeLight or map.light` as an ambiguous competing-authority choice;
- migrate Map 1 mechanically;
- add exact/numerical composition tests;
- amend `docs/SPEC.md` with the final contract.

No Three material rewrite and no Paint UX in this slice.

### Slice B — Three world-surface lighting fidelity

Studio presentation only:

- replace `MeshStandardMaterial` + world relighting with an unlit/custom world-surface material;
- preserve source/material RGB, vertex/static light, orientation modulation, emission, nearest-neighbor texture intent and color-space semantics;
- keep gizmo/editor-only lighting separate;
- add shared Lua/Node numerical source-bake fixture and world-surface sample tests;
- no authored-data migration.

This can proceed largely in parallel with Slice A if the final static-light input contract is kept explicit.

### Slice C — Paint/Blur as first-class Three/Editor Scene authoring

After Slice A's storage contract:

- move Paint/Blur interaction from hidden `map-canvas` pointer handling onto the neutral 3D/Top-Ortho authoring surface;
- persist signed corrections while presenting normal final-color authoring UX;
- blur visible final RGB and derive correction;
- support clear/reset correction;
- fixed maps only in the first slice;
- no LÖVE subprocess in the drag/stroke feedback loop;
- use the same undo/dirty/selection semantics as other neutral Editor Scene operations.

### Later, only if evidence requires it — procedural lighting policy UX

Tileset/generator authoring already has a semantic `emitsLight` seam. Improve resolved-seed visualization/configuration when concrete authoring friction appears. Do not make this a prerequisite for fixing the fixed-map composition bug.

## 15. Decisions this audit recommends

1. **Source lighting is primary.** Fixed-map Light objects and generated/tileset source policy are the semantic source truth.
2. **Source bake is derived.** `runtimeLight` is a cache/resolved field, not authored truth.
3. **Paint survives, but changes meaning.** It becomes fixed-map signed RGB art-direction correction, not a second absolute final-field authority.
4. **Signed additive correction wins the first comparison.** It is the smallest model that can brighten/darken/tint and exactly migrate arbitrary legacy final RGB.
5. **Studio interaction stays local and frame-responsive.** The existing JS bake is the correct interaction pattern; LÖVE verifies/resolves asynchronously rather than blocking drag/strokes.
6. **Procedural maps author sources/policy, not seed-specific paint.** Paint requires stable authored topology or an explicit future freeze-to-authored conversion.
7. **Three world surfaces must be unlit by arbitrary editor lights.** Static-light fidelity is an equation, not a tuned visual resemblance.
8. **Player light, fog, emission, ambient and static source light remain named separate concepts.** They may all affect the final pixel, but they have different owners and lifetimes.
9. **Numerical parity is stronger than screenshot tuning for the shared bake.** A common fixture should gate Lua vs browser source-light semantics.

## 16. Non-decisions / intentionally deferred

This audit does not decide:

- an exact public JSON field name for the signed correction;
- a complex multi-layer lighting stack;
- arbitrary free-positioned/dynamic runtime lights;
- procedural seed painting;
- a full Three reproduction of PSX dithering/vertex snapping/fog artifacts;
- whether a future explicit "freeze/rebase/materialize" command is useful;
- an artistic relight of St. Maria.

Those should be earned by implementation or authoring evidence, not added to make the ontology look complete.

## 17. Acceptance mapping back to #467

- Every current representation/modifier has an owner/lifetime classification above.
- `lightObjects`, generated sources, Paint, ambient and derived bake receive one explicit composition direction.
- The fixed mixed-map case has a concrete signed-correction model and exact migration equation.
- Map 1 has a non-destructive migration plan.
- Procedural maps have a source/generator-policy authoring story.
- Paint/Blur is retained intentionally, but must move to the neutral 3D/Top-Ortho authoring path rather than reviving the hidden canvas.
- Existing frame-local browser bake satisfies the responsiveness requirement for Light-object edits and establishes the same pattern for Paint.
- Three's double-lighting is identified as an owning-layer defect, with a bounded fidelity slice.
- Player light, fog, emission, ambient, orientation shading and static lighting remain separate.
- No G5/G6 references are changed by this audit.

The remaining work should land as the bounded implementation slices above; #467 should remain the architecture parent until those contracts are implemented and `docs/SPEC.md` owns the final static-light equation.

Agent-Signature:
  platform: ChatGPT
  model: GPT-5.6 Sol
  role: architecture/evidence audit
  task: "#467 map lighting authoring audit"
  base: 9ec8e24c5b57cb761f5a14f89552d89f09f27a64
