# World presentation and spatial ownership audit

**Date:** 2026-08-20
**Repository truth:** main and origin/main at d5a7f8d2a3095f20ef83f8a31da78f76b5344f95 after fetch.
**Scope:** evidence and executable probes for #841 only; no #836/#837/#838 implementation or schema migration.

## Finding

Two existing boundaries should be extended rather than replaced:

1. WorldCamera is already the resolved Scene-default-plus-session-override world-projection contract. Projection-window panning should be one additional projection parameter on this record, routed to its current consumers.
2. The current Map is a strong grid-topology adapter, not proof that every spatial family belongs in a universal Map schema. Its resolved structure/renderable seams are reusable; its authored layout and Event x/y semantics remain first-class Project truth.

A low-cadence environment cannot retain only color plus depth. It must retain every camera/projection input that produced them. Otherwise 60 Hz actors projected with a newer camera swim against color/depth produced by an older one. The first follow-up should be a narrow attachment/cadence fixture with explicit snapshot diagnostics—not a render graph, world-renderer rewrite, or spatial migration.

## Evidence labels

| Label | Meaning |
| --- | --- |
| **Fact** | Checked-out source or generated engine state. |
| **Demonstrated** | Command/probe run for this audit. |
| **Inference** | Consequence of evidence, not a commitment. |
| **Owner choice** | Visual/product decision not yet ratified. |

## Current Map frame graph and attachment ownership

~~~mermaid
flowchart TD
 A["love.draw: bind logical color Canvas + temporary depth/stencil"] --> B["frame_renderer -> scene_host -> scene_compositor"]
 B --> C["world_renderer(map) -> vertex_shading_resolver -> renderer.drawMap"]
 C --> D["viewport_3d.draw"]
 D --> E["fog/panorama background"]
 E --> F["one shared alpha + depth less/write pass: structural meshes, placed models, Event models, Event billboards"]
 F --> G["native world-space Effekseer"]
 G --> H["disable + clear depth; door overlay"]
 H --> I["Map HUD: minimap, coordinates, prompt"]
 I --> J["scene pictures, dock, windows, transition"]
 J --> K["screen-space Effekseer, popups, late pictures, dev overlay"]
 K --> L["unbind logical Canvas; nearest-scale to host output"]
~~~

**Fact.** The Map Scene is explicit in generated state: draw world, world map. Normal play creates one logical color Canvas at the active presentation.surface profile: Classic 256×240, 4:3 320×240, or Wide 426×240. Canonical authored composition remains 256×240 with a profile-specific origin. World draws in render-surface coordinates; UI/dialogue/battle draw in composition coordinates. An environment target must be a separate, clearly named third surface meaning—not a change to either of these.

**Fact.** viewport_3d draws fog/panorama first, sets setDepthMode("less", true), then far-to-near intermixes structural surfaces, placed models, Event models, and Event billboards. It resets depth and calls love.graphics.clear(false, false, 1) before HUD/UI. Therefore the current Map path has no retained world depth for a later actor-only pass.

**Fact.** Normal Map play has no off-screen environment target or multi-canvas attachment. Its other Canvas work is deterministic 64×64 wall composite/glow baking. item_model_view.lua is a local color-plus-custom-depth Canvas precedent, but not a world compositor.

**Fact.** Current ordering relies on implicit state: current bound target supplies width/height; composition origin supplies viewport center; shader and native Effekseer need matching camera facts; depth is reset twice because backends are not trusted to restore it through push/pop; native Effekseer flushes LÖVE batches.

### Object/pass census

| Pressure case | Current source/renderer path | Result |
| --- | --- | --- |
| Floor/wall/ceiling | grid layout -> resolved structure -> viewport mesh/placed-surface queues | Structural, but shares the single depth-tested world queue. |
| Opening/door | opening cell -> model kit or mesh pieces; door_transition is overlay/camera approach | Structural; no generic animated-door render pass. |
| Fixture/light object | tile/generated placement -> placed model; optional world effect | Same queue; effect is late native world draw. |
| Rotating fan/moving prop | no generic Map semantic/cadence class | Unresolved pressure case. |
| Decorative/gameplay NPC | both are Events | No decorative-only cadence policy. |
| Sprite Event | resolved Event page/common event -> billboard | Dynamic geometry in shared depth queue. |
| 3D Event | resolved Event model -> placed model | Same path as structural kit pieces. |
| Weather | ambientEffect -> camera-following world Effekseer | Cannot blindly freeze without a policy. |
| Torch/flame | fixture effect -> world Effekseer | Effect clock already differs from static geometry. |
| Projectile | battle/screen effect, no Map-world subsystem | Screen-space late pass. |
| Transparent geometry | no dedicated transparent policy found | Must be explicitly probed. |
| World marker | HUD/minimap/prompt | Composition UI, not world-depth content. |

**Inference.** Present membership is renderer materialization category plus semantic owner, not environment versus actor. A future cadence policy should be declared presentation policy and pressure-tested; do not create isActor/background taxonomy based on object kind.

**Fact.** World-space Effekseer is drawn after LÖVE world meshes; screen-space Effekseer is drawn in frame_renderer after scene/UI layers. Lua order does not prove the native shim's depth-test/write behavior against a future retained attachment. That behavior needs fixture evidence before it can participate in cross-pass occlusion.

## Current WorldCamera contract and #837

**Fact.** presentation/world_camera.lua resolves perspective and orthographic records with pose/basis, FOV/ortho extents, projection scales, near/far planes, tiles-across/focus-depth framing, RPG sin(pitch) calibration, fog metric/origin, player-light anchor, and visibility profile. Durable Scene worldPresentation.camera defaults combine with temporary session, focus, and door overrides without rewriting Map topology.

Consumers are viewport_3d CPU culling/near classification, retro_mesh_shader.lua, world-space Effekseer matrices, fog/light anchoring, world_focus, and numerical tests in tests/test_chest_3d.lua.

**Fact.** The shader already adds a projection center from viewportCenterX/Y; Effekseer independently constructs the same offset from those values and target dimensions.

**Inference.** #837's smallest missing semantic is a normalized principal-point/NDC projection offset on resolved WorldCamera (converted to pixel center for the current target). It is not a second camera transform or a side-view renderer. Asymmetric frustum planes and a projection matrix are equivalent representations, but principal-point offset matches current consumers and avoids duplicated pixel constants. It must reach mesh projection, billboards, model actors, native effects, culling assumptions, and future interaction projection. Wider-render screen cropping is only a negative control: it cannot demonstrate depth alignment.

## LÖVE 11.5 color/depth/MSAA feasibility

Primary LÖVE source at the pinned [11.5 release](https://github.com/love2d/love/releases/tag/11.5) validates depth/stencil Canvases in setCanvas({ color, depthstencil = depth }), retains the attachment in the render-target set, and rejects mismatched MSAA values. See [Graphics.cpp](https://github.com/love2d/love/blob/11.5/src/modules/graphics/Graphics.cpp) and [Canvas.cpp](https://github.com/love2d/love/blob/11.5/src/modules/graphics/Canvas.cpp).

**Demonstrated.** tests/test_world_presentation_audit.lua creates a color Canvas plus depth24stencil8; it draws red at default depth, unbinds, rebinds the exact same depth attachment, and attempts equal-depth blue under strict less. Color readback remains red. It also binds matching 2× MSAA color/depth attachments.

~~~text
Installed LÖVE 11.5 probe:
ISSUE841_DEPTH_PROBE OK retained-depth msaa=32
~~~

| Question | Evidence-supported answer |
| --- | --- |
| Retain/rebind color + depth/stencil? | Yes, demonstrated for ordinary strict depth testing. |
| Matching MSAA required? | Yes; source validates it and matching 2× bound here. |
| Need sampled depth for basic actor occlusion? | No; retained attachment + ordinary depth testing is sufficient. |
| Is depth sampling/reprojection established? | No. Depth/stencil is non-readable by default; no reprojector is proposed. |
| Can color treatment preserve pristine depth? | In principle: leave original depth untouched and transform a separate color output. Exact target topology still needs a probe. |
| Transparent cross-pass policy? | Unresolved. |

**AA conclusion.** Environment MSAA can smooth its own color edges while a later actor depth test is binary per fragment, but final perceived ownership still depends on actor rasterization/postprocess. A future fixture must compare no-AA, MSAA, supersampled/downsampled color with pristine depth, and any post-AA proposal. It must show a hard actor/environment edge without halos. This audit selects no AA implementation.

## Temporal asymmetry and held camera state

**Fact.** Current camera/projection inputs can change every frame through player interpolation/turn/bump, door approach, focus dolly/pitch/FOV, session overrides, target dimensions, profile, and viewport center. Fog, panorama rotation, player light, and camera-following weather are camera-relative.

**Inference.** Holding color+depth alone is incorrect whenever actors use newer camera/projection inputs. The minimum held record is:

~~~text
color + depth/stencil
+ resolved pose/basis
+ projection kind/extents/scales/near/far
+ target dimensions + viewport/principal-point
+ fog origin/metric + panorama policy
+ player-light/effect camera-relative inputs
+ surface/scene revision + environment tick
~~~

| Environment mode | Actor camera/projection | Result |
| --- | --- | --- |
| 15 Hz environment; static camera | held snapshot | Compatible. |
| 15 Hz environment; actor motion only | held snapshot | Compatible; prove occlusion. |
| Camera/projection changes only on tick/cut | refresh environment snapshot | Compatible at intentional cadence. |
| Continuous camera | actor uses held camera, or force refresh | Correct but owner must choose visual policy. |
| Continuous camera + reprojection | new sampled/reconstructable-depth proof | Unestablished. |
| 60 Hz projection-window panning + 15 Hz environment | same stale-projection failure | Incompatible without refresh/held offset/reprojection/larger representation. |

**Owner choice.** First decide whether #836 snaps all world projection to environment cadence, forces an environment refresh on camera/projection change, or limits asymmetry to camera-static periods. Do not promise 60 Hz moving camera/projection with a 15 Hz environment before a reprojection proof.

## #836 × #837 compatibility matrix

| Environment cadence | Projection-window offset | Status |
| --- | --- | --- |
| Full-rate | static/moving | Compatible after one resolved-camera offset reaches all consumers. |
| Held | static | Compatible when the offset belongs to held snapshot. |
| Held | advances at environment cadence | Compatible, deliberately stepped. |
| Held | 60 Hz | Not established: color/depth encode old offset. |
| Held + reprojection | 60 Hz | Hypothesis only; needs quality/cost proof. |

Recommended order: prove #837 at full cadence first; prove #836 with static camera second; investigate dynamic combination only afterward.

## Spatial representation reconciliation

**Fact.** Project maps author compact layout rows and resolve to session.mapGrid; Events use integer x/y, and wall Events have cell/topology constraints. This presently carries passability, topology, opening semantics, selection address, generation, lighting/overrides, and renderer structure.

The prior [map representation survey](map-representation-architecture-survey-2026-08-11.md) already established:

~~~text
authored semantic representation
  -> deterministic resolver/compiler
resolved structural representation
  -> renderer/GPU adaptation
~~~

It identifies visibility profiles, geometry compilation, semantic selection/provenance, and Map Renderable Bundle as useful lower seams.

**Inference.** A non-grid authored-3D pressure case should first be a sibling authored resource/adapter hosted by an existing Scene, exposing only genuinely shared capabilities: identity/provenance, resolved renderables, bounds/transforms where meaningful, anchors/regions, and traversal/collision provider(s). Grid neighbor movement remains its own capability. The smallest possible cross-family Event fact is a named semantic anchor plus family-owned placement reference—not a premature universal XYZ transform. Current grid schemas remain stable.

## Measurements and transport

These staged Project commands ran against installed LÖVE 11.5. Native Effekseer was absent, so they measure current geometry/preparation but not live native effect cost.

~~~text
lovec <stage> profile-3d 1 120 current
lovec <stage> profile-3d 8 120 current
lovec <stage> profile-3d 8 120 no-draw
lovec <stage> profile-3d 8 120 no-height
lovec <stage> profile-map-build 1,8,12 1,1,1 1 fresh
~~~

| Case | Mean ms | p95 ms | Draw calls/frame | Observation |
| --- | ---: | ---: | ---: | --- |
| Map 1 current | 4.79 | 7.46 | 118.2 | 84 model draws; 36,162 resident structural vertices. |
| Map 8 current | 6.09 | 9.98 | 192 | 184 model draws; 197 height placements; 13,400 height vertices inspected/frame. |
| Map 8 no-draw | 5.68 | 13.09 | 8 | Preparation remains; final draw is not dominant. |
| Map 8 no-height | 4.21 | 7.93 | 11 | 3 model draws; confirms height representation is material. |

Cold map-build-to-first-usable samples: map 1 378 ms, map 8 513 ms, map 12 578 ms; settled samples: 13.96, 7.43, 3.33 ms. Map 8 reported 302,586 placed vertices and a 15.7 MB retained GPU estimate during cold materialization. This reinforces #148/#758: measure additional render targets/passes against actual preparation and materialization cost. These data do not justify temporal asymmetry as optimization.

Future memory accounting must use chosen dimensions/formats/sample count, including Wide, rather than an invented format budget.

## Invariants

1. Scene owns durable world-presentation defaults; Map topology does not acquire camera policy.
2. One resolved WorldCamera feeds every world-space consumer.
3. Logical render surface/composition and internal environment targets remain distinct.
4. Grid Map/Event behavior remains unchanged and first-class.
5. Held environment color, depth, and camera/projection interpretation advance atomically.
6. Pass/cadence membership is a proven presentation policy, not source-kind taxonomy.
7. World/screen Effekseer ownership stays explicit; native depth behavior is tested before cross-pass reliance.
8. No G5/G6 recapture is evidence for this audit.

## Recommended bounded follow-ups

1. **#837 prerequisite:** a full-rate projection-center WorldCamera spike in one wide neutral room. Route one offset through shader, Event billboard/model, and Effekseer; compare it with ordinary camera follow.
2. **#836 prerequisite:** a neutral attachment/cadence fixture with static occluder, Event billboard, Event model, controlled world effect, and UI. Prove static-camera 15/60 behavior plus a deliberately incorrect stale-camera control. No production split yet.
3. **Dynamic-combination decision:** only after 1–2, compare forced refresh, held-projection actors, and reprojection candidates. Reject 60 Hz panning over a 15 Hz environment mode if evidence is poor.
4. **#695 pressure prototype:** a sibling tiny authored-3D environment adapter with constrained traversal, Event/anchor, transition, and documented reuse/insufficiency boundaries—not a Map migration.

This audit recommends no render graph, environment/actor taxonomy, Map rewrite, or moving-camera fake-pre-render implementation yet.
