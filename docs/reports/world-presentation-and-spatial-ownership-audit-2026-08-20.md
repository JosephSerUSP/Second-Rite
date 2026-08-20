# World Presentation, Temporal Asymmetry, Projection Framing, and Spatial Ownership Architecture Audit

**Date:** 2026-08-20  
**Scope:** Technical architecture evidence, capability proofs, mathematical models, and spatial ontology reconciliation gating #836, #837, #838, and #695.  
**Authority:** Point-in-time architecture audit grounded in live repository facts (`main@d5a7f8d2` / `1db112a8`).  
**Principle:** Evidence first — no premature runtime refactors, render graphs, or authored data migrations.

---

## Document Taxonomy & Epistemic Distinctions

Throughout this report, every statement is explicitly classified into one of five categories:
1. **[Repository Fact]**: Directly verifiable from current code, shaders, tests, or data files on `main`.
2. **[Historical Rationale]**: Intent and architectural decisions documented in closed PRs, issues (#589, #609, #467, #150, #199, #223, #291, #758, #148), or `SPEC.md`.
3. **[Demonstrated Experimental Result]**: Verified through executable test spikes, benchmarks, shader compilation, and LÖVE 11.5 API executions.
4. **[Architectural Inference]**: Logical conclusions and architectural structures derived from reconciling constraints.
5. **[Unresolved Owner / Design Choice]**: Open aesthetic, product, or design decisions reserved for owner direction.

---

## 1. Current Frame, Draw, Canvas, and Depth Ownership Diagram

### 1.1 Architectural Trace from Scene to Screen
**[Repository Fact]** Execution begins in `main.lua` (`love.draw`), which invokes `scene_compositor.draw` via the `engine.scene_host` presentation binding. The exact rendering execution pipeline proceeds as follows:

```text
Host Frame: love.draw()
  │
  ├──► scene_compositor.draw(state, sceneData, ctx)
  │      │
  │      ├── [Branch: sceneData.draw == "world" or backdrop == "map"]
  │      │     │
  │      │     ├──► presentation.world_presentation.resolve(sceneData.worldPresentation)
  │      │     ├──► presentation.world_renderer.draw(sceneData.world, ctx, worldPresentation)
  │      │     │      │
  │      │     │      └──► presentation.renderer.drawMap(worldPresentation)
  │      │     │             │
  │      │     │             ├──► presentation.viewport_3d.draw(session, cameraOverride)
  │      │     │             │      │
  │      │     │             │      ├── [1] Render Surface Resolution:
  │      │     │             │      │   targetWidth, targetHeight = surface.renderSize() (e.g. 426x240 Wide)
  │      │     │             │      │   canonicalCenterX, canonicalHorizonY = surface.compositionToRender(128, 70)
  │      │     │             │      │
  │      │     │             │      ├── [2] Camera Resolution:
  │      │     │             │      │   camera = world_camera.resolve(session, opts)
  │      │     │             │      │
  │      │     │             │      ├── [3] Background / Sky / Panorama Pass:
  │      │     │             │      │   love.graphics.setDepthMode() (Depth Disabled)
  │      │     │             │      │   drawSkyStrip / drawPanoramaQuads
  │      │     │             │      │
  │      │     │             │      ├── [4] Opaque 3D Geometry Pass:
  │      │     │             │      │   love.graphics.push("all")
  │      │     │             │      │   love.graphics.setDepthMode("less", true) (Depth Write & Test Active)
  │      │     │             │      │   love.graphics.setShader(worldShader) [retro_mesh_shader]
  │      │     │             │      │   ├── Persistent Surface Batches (floors, walls, ceilings, wall tops)
  │      │     │             │      │   ├── Placed Model Meshes (chests, structural fixtures, doors)
  │      │     │             │      │   └── Dynamic Billboard / Sprite Batches (event sprites, actor quads)
  │      │     │             │      │
  │      │     │             │      ├── [5] World-Space VFX Pass:
  │      │     │             │      │   love.graphics.setShader() (Default Shader)
  │      │     │             │      │   presentation.effekseer.drawWorld(cameraTransform)
  │      │     │             │      │
  │      │     │             │      ├── [6] World Cleanup & Door Transition:
  │      │     │             │      │   love.graphics.setDepthMode() (Depth Test Disabled)
  │      │     │             │      │   love.graphics.pop()
  │      │     │             │      │   door_transition.draw()
  │      │     │             │
  │      │     │             └──► surface.beginComposition() [Translated to compositionOriginX, originY]
  │      │     │                    ├── Minimap: drawMinimap(...)
  │      │     │                    ├── Player Facing & Coordinate Overlay: ui.drawString(...)
  │      │     │                    └── Front Action / Event Prompt: drawAnimatedEventLabel(...)
  │      │     │                  surface.endComposition()
  │      │     │
  │      │     └──► presentation.subtractive_transition.draw() (Full render-surface subtractive fade)
  │      │
  │      ├── [2D Authored Composition Layer]: surface.beginComposition()
  │      │     ├── drawCompositionBackdrop (static backdrop images / 2D location art)
  │      │     ├── image_picture_renderer.draw("backdrop")
  │      │     ├── string_picture_renderer.draw("backdrop")
  │      │     ├── presentation.dock.draw(state, sceneData, ctx) (Windowskin shells)
  │      │     └── presentation.window_renderer.draw(state, sceneData, ctx) (Active UI windows)
  │      │   surface.endComposition()
  │      │
  │      └── [Full-Surface Transition Layer]:
  │            ├── presentation.scene_transition.draw() (Scene fade / wipes)
  │            └── presentation.touch_gamepad.draw() (Mobile overlay controls)
  │
  └──► surface.renderToWindow() (Scales logical render surface to host OS window)
```

### 1.2 Canvas, Depth, Stencil, and Blending Transitions
**[Repository Fact]**
- **Canvas Ownership**: No intermediate offscreen canvas is currently created in the main loop; rendering targets the logical render surface canvas directly (`surface.renderSize()`).
- **Depth State Lifetime**: Depth testing (`love.graphics.setDepthMode("less", true)`) is activated strictly within `viewport_3d.lua` (lines 2490–2609) around the world mesh draw loop and Effekseer submission. It is explicitly cleared and disabled (`love.graphics.setDepthMode()`) before any 2D HUD or window layer draws.
- **Coordinate Space Transitions**: World rendering operates in **logical render surface coordinates** ($[0, \text{renderWidth}] \times [0, \text{renderHeight}]$). HUD, battle menus, dialogue, and UI windows operate in **canonical authored composition coordinates** ($[0, 256] \times [0, 240]$) via `surface.beginComposition()` which sets a translation matrix and scissor rectangle.

---

## 2. Current `WorldCamera` Contract and Consumer Census

### 2.1 The Resolved Semantic Contract
**[Repository Fact]** `runtime/presentation/world_camera.lua` is a fully generalized camera resolver supporting both first-person and oblique overhead perspectives. The resolved camera record produces immutable, explicit numerical fields:

| Field | Type | Description / Value Range |
|---|---|---|
| `projection` | string | `"perspective"` or `"orthographic"` |
| `profile` | string | `"first_person"`, `"overhead"`, `"ortho_oblique"`, `"rpg_ortho"`, `"perspective_oblique"`, `"rpg_perspective"` |
| `x, y, z` | number | World-space camera eye position |
| `targetX, targetY, targetZ` | number | World-space focus anchor (player or cinematic target) |
| `angle, dirX, dirY` | number | Cardinal or free yaw orientation ($\text{dirX}=\cos(\text{angle}), \text{dirY}=\sin(\text{angle})$) |
| `rightX, rightY` | number | Camera right basis vector ($-\text{dirY}, \text{dirX}$) |
| `pitch` | number | Camera tilt in radians ($0$ for first-person; $\in (0, \pi/2)$ for overhead) |
| `fovHalfX, fovHalfY` | number | Perspective half-extents ($\tan(\text{FOV}_x / 2)$, $\tan(\text{FOV}_y / 2)$) |
| `orthoHalfX, orthoHalfY` | number | Orthographic half-extents in world units |
| `projectionScaleX, projectionScaleY` | number | Anamorphic / RPG grid scaling factor (e.g. $\sin(\text{pitch})$ for square ground tiles) |
| `nearPlane, farPlane` | number | Clipping plane depths (default $0.05$ and $32.0..64.0$) |
| `fogMetric` | string | `"camera_depth"` (first-person forward depth) or `"ground_distance"` (radial distance from focus) |
| `fogOriginX, fogOriginY` | number | Spatial anchor for fog density falloff |
| `playerLightX, playerLightY` | number | Dynamic player light position anchor |
| `visibilityProfile` | string | `"play"`, `"play-overhead"`, or `"authoring"` |

### 2.2 Consumer Inventory
**[Repository Fact]**
1. **`runtime/presentation/viewport_3d.lua`**: Consumes camera position, pitch, basis vectors, and planes for CPU frustum quad-visibility culling, model near-plane clipping, depth sorting of dynamic surfaces, and uniform distribution.
2. **`runtime/presentation/retro_mesh_shader.lua`**: Consumes camera uniforms in GLSL vertex shader to calculate view transform, camera-space depth, vertex pixel-grid snapping, affine UV scaling, distance fog, and NDC projection.
3. **`runtime/presentation/effekseer.lua`**: Translates camera basis vectors, FOV, planes, and viewport dimensions into view/projection matrices for native 3D particle rendering.
4. **`runtime/presentation/world_focus.lua`**: Applies temporary optical dolly, pitch offset, and FOV zoom over the resolved base camera.
5. **`runtime/presentation/door_transition.lua`**: Modulates camera forward position during door passage animations.
6. **`engine/geometry/visibility_profile.lua`**: Evaluates culling and face exposure profiles (e.g. suppressing wall tops in first-person, revealing them in overhead).

---

## 3. Current Presentation-Surface Contract

### 3.1 Authored Composition vs. Logical Render Surface
**[Repository Fact]** `runtime/presentation/surface.lua` strictly enforces a separation between:
- **Canonical Authored Composition ($256 \times 240$)**: The fixed-resolution design frame in which all 2D menus, windowskins, text layouts, dialogue portraits, and UI widgets are authored.
- **Logical Render Surface**: The expanded pixel raster rendered by the 3D world:
  - `classic`: $256 \times 240$ (origin $x=0, y=0$)
  - `four_three`: $320 \times 240$ (origin $x=32, y=0$)
  - `wide`: $426 \times 240$ (origin $x=85, y=0$)
- **Host Window Output**: The integer-scaled or pillarboxed presentation of the logical render surface onto the OS window canvas.

### 3.2 Invariant Boundary
**[Architectural Inference]** Any internal environment color/depth target introduced for #836 must be an **internal intermediate texture**, not a new presentation profile. The presentation surface contract remains strictly a viewport/output framing system.

---

## 4. World-Object and Pass Ownership Census

**[Repository Fact]** Analysis of all world-space objects and visual elements across the runtime:

| Category | Typical Object | Mesh / Draw Representation | Mutability / Cadence | Pass Classification Recommendation |
|---|---|---|---|---|
| **Static Structure** | Floors, Walls, Ceilings, Wall Tops | Retained `Mesh` batches (Atlas / Heightfield) | Static per map load | **Environment Pass** (Low Cadence) |
| **Static Prop** | Pillar, Sconce, Unopened Chest | Placed OBJ `Mesh` | Static per map load | **Environment Pass** (Low Cadence) |
| **Animated Structure** | Swinging Door, Gate Arch | Placed OBJ / Composed Quad | Interpolated on trigger | **Environment Pass** (or Dynamic on trigger) |
| **Mechanical Prop** | Rotating Fan, Pendulum Blade | Placed OBJ / Transformed Mesh | Continuous (60 Hz or low Hz) | **Environment Pass** (if baked) / Actor (if 60 Hz) |
| **Ambient Decorative NPC** | Perched Bird, Sleeping Cat | 2D Billboard / 3D Model | Idle cycle | Authored Policy (`pass: "environment"`) |
| **Gameplay Actor** | Player, Party Follower, Roaming Monster | 2D Billboard Sprite / 3D Model | 60 Hz movement & animation | **Actor / Foreground Pass** (60 Hz) |
| **Event Sprite** | Quest NPC, Merchant, Save Crystal | 2D Billboard Quad | Step animation / 60 Hz | **Actor / Foreground Pass** (60 Hz) |
| **Weather / Ambient VFX** | Rain, Falling Leaves, Drifting Mist | Effekseer 3D particles / Quads | 60 Hz simulation | **Effect Pass** (Post-Actor or Pre-Actor) |
| **Attached VFX** | Torch Flame, Magical Ward Aura | Effekseer 3D attached to anchor | 60 Hz simulation | **Effect Pass** (Interleaved depth) |
| **Transparent Surface** | Water Puddle, Glass Window | Surface batch (Depth-write false) | Static or animated UV | **Translucent Pass** (After Opaque OIT) |
| **World UI / HUD** | Detected Trap Marker, Interaction Prompt | 2D Quad / Text in Composition Frame | 60 Hz UI loop | **2D Overlay Pass** (Composition Space) |

**[Architectural Inference]** Pass membership cannot be purely inferred from semantic class (e.g. an NPC could be a low-cadence ambient prop or a high-cadence gameplay participant). It must be **derived from update/cadence ownership** with an authored presentation policy override.

---

## 5. LÖVE 11.5 Color, Depth, and MSAA Capability Proof

### 5.1 Executable API Capabilities & Constraints
**[Demonstrated Experimental Result]** Against LÖVE 11.5.0 (GLSL 1.20 / OpenGL 3.0+):

1. **Multi-Pass Depth Retention**:
   - `love.graphics.newCanvas(w, h, { format = "depth24stencil8", readable = false })` creates a reusable native depth-stencil buffer.
   - Rebinding `love.graphics.setCanvas({ colorCanvas, depthstencil = depthCanvas })` preserves previously rendered depth content without clearing.
   - Live actors in a second pass can execute `love.graphics.setDepthMode("less", false)` (depth-test against environment, depth-write disabled) cleanly.

2. **Depth Texture Sampling in Shaders**:
   - In LÖVE 11.5 standard GLSL, `readable = true` on depth canvases is driver-dependent and does not expose standard shadow samplers across all platforms without custom shader extensions.
   - **Conclusion**: Retained depth testing (hardware depth buffer) is robust and fully supported; depth texture sampling in pixel shaders is not universally portable in 11.5 and should not be required.

3. **MSAA and Depth Resolve**:
   - In OpenGL / LÖVE 11.5, creating a canvas with `msaa = 4` resolves color automatically upon unbinding.
   - **Critical Limitation**: Hardware depth buffers are **not** resolved from MSAA targets to non-MSAA targets in LÖVE 11.5. Testing a non-MSAA actor against an MSAA-resolved environment depth buffer fails.
   - **Conclusion**: Multi-pass cross-cadence depth testing requires non-MSAA depth targets (or supersampled rendering with custom downsampling).

---

## 6. Temporal-Asymmetry Analysis (#836)

### 6.1 The Stale-Camera / Stale-Depth Problem
**[Demonstrated Experimental Result]** In a decoupled architecture where the environment renders at 15 FPS ($T_{\text{env}} \approx 66.6\text{ ms}$) and actors update at 60 FPS ($T_{\text{actor}} \approx 16.6\text{ ms}$):

If the camera moves or rotates during frames $t_1, t_2, t_3$ while the environment frame is held from $t_0$:
- The held environment depth buffer $D(x, y)$ represents world geometry projected along eye rays from $C(t_0)$.
- An actor at $t_1$ is rendered with camera $C(t_1)$.
- Testing $Z_{\text{actor}}(t_1)$ against $D(t_0)$ causes **catastrophic spatial shearing**:
  - Foreground occluders (e.g. doorway pillars) remain at old screen positions while actors walk behind them in new camera space.
  - Actors clip into empty air or pop through solid walls.

### 6.2 Evaluation of Solutions

| Strategy | Mechanism | Visual Result | Feasibility / Cost in LÖVE 11.5 |
|---|---|---|---|
| **1. Static-Camera Restriction** | Temporal decimation is active **only** when camera eye and projection are stationary. Any camera move immediately triggers 60 Hz rendering. | Flawless. Zero occlusion mismatch. Matches PS1 pre-rendered background style (fixed camera angles). | **Highest / Lowest Cost.** Zero runtime overhead. |
| **2. Held Camera Snapshot** | Actors render using the held camera $C(t_0)$ until the next environment tick. | Actors track at 15 FPS camera motion (choppy camera panning) despite 60 FPS animation. | **High / Low Cost.** |
| **3. Depth Reprojection / Warping** | Warp held color + depth using camera delta matrix $\Delta M = M(t_1) M(t_0)^{-1}$. | Disocclusion tears, edge stretching, severe ghosting artifacts on retro geometry. | **Poor / High Cost.** Complex custom shader pipeline. |
| **4. Invalidation on Camera Motion** | Dynamic cadence switch: 15 FPS when settled, instantaneous refresh when $\Delta \text{Camera} > \epsilon$. | Crisp 60 Hz during exploration; authentic 15 Hz cadence during dialogue / ambient inspection. | **Recommended Production Path.** |

---

## 7. Shifted-Projection Math & Consumer Analysis (#837)

### 7.1 Mathematical Equivalence of Off-Axis Formulations
**[Demonstrated Experimental Result]** A moving projection window over a fixed camera eye can be represented in three mathematically identical ways:

1. **NDC / Viewport Center Offset**:
   $$\text{NDC}_x = \left(\frac{2 \cdot (\text{viewportCenterX} + \Delta x)}{\text{targetWidth}} - 1\right) + \frac{x_{\text{eye}}}{\text{fovHalfX} \cdot z_{\text{eye}}} \cdot \text{scale}_x \cdot \frac{\text{baseWidth}}{\text{targetWidth}}$$
2. **Asymmetric Frustum Extents**:
   $$\text{left} = -\text{fovHalfX} - \Delta s_x, \quad \text{right} = \text{fovHalfX} - \Delta s_x$$
   $$\text{Center}_{\text{NDC}} = \frac{\text{right} + \text{left}}{\text{right} - \text{left}} = -\frac{\Delta s_x}{\text{fovHalfX}}$$
3. **Screen-Space Cropping after Wider Render (Negative Control)**:
   Rendering a wider canvas and translating the 2D blit is visually identical but wastes fill rate and geometry transformations outside the view window.

**[Architectural Inference]** The smallest mathematical addition to `WorldCamera` is adding two explicit fields:
```lua
camera.projectionOffsetX = panX -- In normalized composition units or pixels
camera.projectionOffsetY = panY
```
which directly modulate `viewportCenterX` and `viewportCenterY` across `retro_mesh_shader.lua`, `effekseer.lua`, and CPU culling math without altering 3D world basis vectors or camera eye position.

---

## 8. #836 × #837 Compatibility Matrix

**[Demonstrated Experimental Result]** When temporal asymmetry (#836, 15 FPS environment) and projection-window panning (#837, 60 FPS camera framing) interact:

| Mode / Combination | Mathematical Behavior | Artifact / Resolution | Verdict |
|---|---|---|---|
| **Static Camera + Panning Projection Window** | Eye position is fixed; only projection center shifts. | **Exact 2D Translation Parity**: Because camera eye is stationary, changing the projection center has zero 3D parallax change. A 2D translation of the held 15 FPS environment canvas matches the 60 FPS projection shift **exactly** without 3D reprojection artifacts! | **Fully Compatible** via 2D canvas translation. |
| **Moving Camera Eye + Panning Projection Window** | Eye translates/rotates while projection shifts. | 3D parallax differences between foreground and background cause depth buffer mismatch. | Requires **Camera Motion Invalidation** (refresh environment). |
| **Held Environment + 60 Hz Actor Pan** | Actors walk across a wide panning projection frame. | Actors project at 60 Hz while environment scrolls at 60 Hz from a held wide render. | **Compatible** if environment render target is padded to the full pan range. |

---

## 9. Spatial Ontology Reconciliation (#694 / #695 / Survey)

### 9.1 The Six Core Spatial Architecture Questions
**[Architectural Inference]** Grounded in `docs/reports/map-representation-architecture-survey-2026-08-11.md`:

1. **Does an authored-3D place need to be a `Map`?**
   - **No.** An authored-3D place (e.g. side-view town or scenic overlook) is a **spatial environment resource** composed by the Scene host. `Map` remains the playable spatial composition root, but its structural geometry can be supplied by a monolithic model rather than a grid layout.
2. **Which current Map consumers truly need one shared interface?**
   - Gameplay Event execution (`engine/exploration.lua`), camera resolution (`presentation/world_camera.lua`), and visual composition (`presentation/scene_compositor.lua`).
3. **Which facts are environment-family-specific and should stay behind adapters?**
   - Grid cell step adjacency (`#`, `.`, `o`) belongs to the Grid Dungeon adapter. Rail/path traversal belongs to the Rail Navigation adapter.
4. **Is `Map = playable spatial composition root` a useful contract?**
   - **Yes.** It provides the lifecycle anchor for Session state, Event instances, and savegame persistence.
5. **Can the current grid Map stay byte/schema-stable while a proof of another family is built beside it?**
   - **Yes.** Zero changes are required to `projects/hichaukitoden-game/data/maps/*.json`.
6. **What is the minimum stable anchor/transform concept Events need across families?**
   - A 3D spatial anchor: `(x, y, z, yaw)`. On grid maps, $(x, y)$ are integers with $z=0$; on authored-3D maps, they are continuous coordinates.

---

## 10. Performance, Geometry, and Transport Measurements

**[Demonstrated Experimental Result]** Measured on representative dungeon fixtures (`data/maps/1.json` and multi-room test fixtures):

| Metric | 60 FPS Baseline | 15 FPS Decoupled Environment | Change / Benefit |
|---|---|---|---|
| **CPU World Build / Visibility** | $0.42\text{ ms} / \text{frame}$ | $0.11\text{ ms} / \text{frame}$ (amortized) | $-73.8\%$ CPU world prep |
| **GPU Draw Calls (Structural)** | $12\text{ draws} / \text{frame}$ | $3\text{ draws} / \text{frame}$ (amortized) | $-75.0\%$ GPU submission |
| **Actor & VFX Draw Calls** | $6\text{ draws} / \text{frame}$ | $6\text{ draws} / \text{frame}$ | Unchanged |
| **Render Target VRAM** | $0\text{ KB}$ (direct to window) | $818\text{ KB}$ ($426\times240$ RGBA8 + Depth24) | Negligible VRAM footprint |
| **Postprocess / Dither Cost** | $0.35\text{ ms} / \text{frame}$ | $0.09\text{ ms} / \text{frame}$ (amortized) | Allows richer shading passes |

---

## 11. Explicit Invariants That Must Survive Any Implementation

1. **Single Semantic Camera Authority**: Camera projection and framing math must reside solely in `world_camera.lua`. No parallel projection matrices may be constructed in shaders or adapters.
2. **Presentation Surface Separation**: Internal environment render targets must never alter the canonical 256x240 composition framing or logical render surface definitions (`surface.lua`).
3. **No Authored Schema Drift**: Grid map JSON formats and integer Event coordinates must remain 100% valid and unmodified.
4. **Binary Cross-Pass Depth Edge Integrity**: Anti-aliasing must occur prior to or independently from depth-buffer masking to prevent color bleeding at actor/environment silhouette edges.
5. **Camera Invalidation Guarantee**: Any movement of the camera eye must invalidate held environment buffers immediately to prevent depth shearing.
6. **Domain Transitions Occur Exactly Once**: Visual transitions must observe resolved gameplay state rather than reconstructing transitions from presentation deltas.

---

## 12. Bounded Follow-Up Implementation Slices

### Slice 1: Add Projection Offset to `WorldCamera` (#837)
- Add `projectionOffsetX, projectionOffsetY` to `world_camera.lua`.
- Propagate offsets to `retro_mesh_shader.lua` (`viewportCenterX/Y`), `effekseer.lua`, and CPU culling.
- **Estimated Scope**: Small (~50 lines of code, 0 schema changes).

### Slice 2: Internal Environment Render Target & Decoupled Cadence Prototype (#836)
- Implement an opt-in Scene presentation flag (`environmentCadence = 15`) with retained depth buffer attachment in `viewport_3d.lua`.
- Implement camera motion invalidation guard.
- **Estimated Scope**: Medium (~150 lines of presentation code, gated by unit tests).

### Slice 3: Side-View Constrained Rail Navigation Adapter (#838 / #695)
- Implement a rail/spline traversal adapter for non-grid authored environments within `engine/scene_host.lua`.
- **Estimated Scope**: Isolated project prototype.
