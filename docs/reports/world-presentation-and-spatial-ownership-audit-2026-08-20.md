# World presentation and spatial ownership audit

**Date:** 2026-08-20  
**Issue:** #841  
**Repository baseline inspected:** `main@d5a7f8d2a3095f20ef83f8a31da78f76b5344f95`  
**Scope:** architecture/evidence only. No production renderer rewrite, Map migration, render graph, #836 implementation, #837 implementation, or canonical G5/G6 recapture.

**Coordination note:** the owner reports parallel independent audits of #841. At publication time no competing #841 PR, branch, issue comment, or checked-in report is visible through GitHub. This report is therefore a **consolidation candidate, not a claim of sole authority**. Parallel findings should be reconciled into this PR before #841 is closed; conflicting executable evidence outranks this prose.

## Executive finding

Current `main` is materially more general than the sketches that motivated #836/#837. The evidence does **not** justify a second camera system, a new `Map` ontology, or a broad `viewport_3d` rewrite.

Three existing boundaries should survive:

1. `runtime/presentation/world_camera.lua` is the resolved semantic camera authority, independent of gameplay topology.
2. `runtime/presentation/surface.lua` separates canonical authored composition, logical render surface, and host output. A future internal environment framebuffer is a render target, not a third meaning of “surface”.
3. The current Map world renderer has one coherent depth-tested world epoch containing structural geometry, placed models, sprite Events, 3D Event models, and world Effekseer; screen-space effects/UI follow later.

The smallest missing semantic for #837 is a **resolved principal-point / projection-center offset** on the existing `WorldCamera`, shared by every world projection consumer. The important missing semantic for #836 is a **held world-presentation snapshot** whose atomic authority is broader than color+depth: it must retain the exact resolved camera/projection state that produced those attachments.

A second important #836 finding is that live actors cannot simply render normally with `depthwrite=true` into the retained environment depth attachment. That mutates the supposedly held snapshot with stale actor depth. The simplest first proof is therefore read-only environment depth; live-vs-live 3D occlusion needs an explicit working-depth strategy.

LÖVE 11.5’s API shape can express a retained custom depth/stencil Canvas and rebind it with another color target, so LÖVE 12 is **not an architectural prerequisite**. Actual backend/MSAA behavior and the intended hard actor/environment ownership edge remain executable evidence requirements; this patch includes a repository-local LÖVE 11.5 probe but does not pretend it ran in this sandbox.

---

# 1. Current frame / canvas / depth ownership

Repository trace: `runtime/main.lua` -> `presentation/frame_renderer.lua` -> `scene_host` / `scene_compositor` -> `world_renderer.lua` -> `renderer.drawMap` -> `viewport_3d.draw`.

```text
love.draw
  |
  | bind logical render Canvas
  | clear color + depth + stencil
  v
frame_renderer.draw
  |
  +-- scene_host / scene_compositor
  |     |
  |     +-- world Scene
  |           |
  |           +-- world_renderer("map")
  |                 |
  |                 +-- renderer.drawMap
  |                       |
  |                       +-- viewport_3d.draw
  |                       |     fog/background
  |                       |     optional sky
  |                       |     ONE depth-tested world epoch:
  |                       |       structural floor/wall/ceiling
  |                       |       openings / structural model pieces
  |                       |       placed/static models/fixtures
  |                       |       sprite Event billboards
  |                       |       3D Event models
  |                       |       world Effekseer
  |                       |     disable depth test
  |                       |     explicitly clear depth
  |                       |     door transition overlay
  |                       |
  |                       +-- authored-composition HUD
  |                           minimap / coordinates / event label
  |
  +-- Scene windows / transitions / touch controls
  +-- screen-space Effekseer
  +-- popups / pictures / developer overlay
  |
  v
unbind logical render Canvas
  |
  +-- integer-nearest logical-surface -> host transform
  +-- blit logical Canvas to host window
```

The important current contract is not “environment pass then actor pass”. `viewport_3d` accumulates many world categories into one depth-sorted/depth-tested epoch. #836 would introduce a new cadence/lifetime boundary inside an otherwise coherent world-depth lifetime.

Implicit-state dependencies worth preserving or making explicit during any later spike:

- `viewport_3d` assumes the host already bound a depth-capable Canvas;
- geometry and world Effekseer share the same resolved camera and depth lifetime;
- `viewport_3d` explicitly resets depth mode/shader/wireframe and clears depth before later 2D presentation because those are backend/global state;
- screen-space Effekseer is intentionally outside world depth;
- composition-space scissor translation is owned by `surface.beginComposition()` rather than by individual UI callers.

---

# 2. Current `WorldCamera` contract and consumers

Current `world_camera.lua` already resolves:

- perspective and orthographic projection;
- first-person and overhead profiles;
- camera position/target, yaw, pitch, forward/right basis;
- FOV degrees -> shader half-extent conversion;
- `tilesAcross` target framing / focus-depth derivation;
- independent `projectionScaleX/Y` and RPG/anamorphic correction;
- near/far planes and visibility profile;
- fog metric/origin;
- player-light anchor semantics;
- camera-space depth helpers and numerical scale oracles;
- temporary focus/cinematic overrides above Scene-owned durable defaults.

Consumers include the world mesh shader, CPU near/far/visibility helpers, world Effekseer camera matrices, fog, dynamic player light, and Studio/world-presentation tooling.

## #837 reduction

The existing shader already accepts `viewportCenterX/Y`; `effekseer.worldCameraMatrices()` independently derives equivalent projection offsets from that center. That is strong evidence the missing abstraction is not projection machinery but **one resolved semantic owner** for the shift.

Recommended first representation: normalized principal-point / NDC center offset on `WorldCamera`, composed with the renderer’s base viewport center. Asymmetric frustum extents are mathematically valid but expose more low-level representation than current authoring needs. A wider-render-and-screen-crop implementation is useful only as a negative/control path because it moves image pixels without proving every world consumer agrees.

All world consumers must receive the same resolved shift: meshes, Event sprites/models, world Effekseer, culling/depth helpers where projection matters, and picking/projection helpers where applicable.

---

# 3. Presentation-surface contract

`surface.lua` owns:

```text
canonical authored composition: 256x240
        |
        +-- explicit origin inside active logical render surface
                classic     256x240 @ (0,0)
                four_three  320x240 @ (32,0)
                wide        426x240 @ (85,0)
        |
logical render surface
        |
integer-nearest host scaling / centering
        |
host window
```

World/render-surface layers use render coordinates; authored UI uses composition coordinates translated by `beginComposition()/endComposition()`. A #836 environment color/depth pair should be called an internal framebuffer/target/snapshot, not a presentation-surface profile. It must not alter #206’s separate canonical-composition question.

---

# 4. World-object / cadence ownership census

Names such as “environment” and “actor” are insufficient to choose pass membership.

| Pressure case | Current draw family | Stable future inference? |
| --- | --- | --- |
| floor/wall/ceiling | structural world mesh | strong held default |
| static prop/fixture | placed world model | strong held default |
| animated door | structural/presentation animation | cadence is policy, not object kind |
| rotating fan/moving prop | placed model | may be held or live |
| decorative NPC | Event sprite/model | may intentionally belong to held treatment |
| gameplay NPC/protagonist | Event/live actor | strong live default, but not sufficient taxonomy |
| sprite Event | world billboard | visual type does not decide cadence |
| 3D Event actor | world model | visual type does not decide cadence |
| weather | world Effekseer | may inherit held environment cadence |
| torch/flame | world effect | may be held even though animated |
| projectile/VFX | world effect/model | usually live |
| transparent geometry | unresolved inter-geometry ordering concern | cannot hide inside opaque depth split |
| UI/marker | later presentation | screen/world semantic still matters |

If #836 survives the spike, pass/cadence membership should be a small **resolved presentation policy**, with conservative defaults and explicit override where needed—not a gameplay `isActor`/`isBackground` ontology.

---

# 5. LÖVE 11.5 retained depth / MSAA feasibility

The repository pins/asserts LÖVE 11.5 in `.github/actions/install-love/action.yml`.

Primary 11.x API documentation establishes that:

- `love.graphics.setCanvas({...})` accepts a custom `depthstencil` Canvas;
- depth Canvas formats exist;
- Canvas creation accepts an `msaa` request and `Canvas:getMSAA()` reports actual samples;
- depth testing/writing is controlled separately by `setDepthMode`;
- depth need not be sampled merely to remain depth-test authority.

Primary references:

- https://love2d.org/wiki/love.graphics.setCanvas
- https://love2d.org/wiki/love.graphics.newCanvas
- https://love2d.org/wiki/love.graphics.setDepthMode
- https://love2d.org/wiki/PixelFormat
- https://love2d.org/wiki/Canvas:getMSAA

Therefore this basic form is expressible in 11.5:

```text
bind environmentColor + customDepth
  clear color + depth
  draw opaque environment
unbind

bind finalColor + SAME customDepth
  clear final color only
  draw/postprocess held environment color with depth writes disabled
  depth-test live actor against customDepth
unbind
```

But there is a critical qualifier: **the live actor must not write into the retained environment depth** unless a separate working-depth lifetime owns those writes. Otherwise actor depth from frame N remains in the 15 Hz snapshot and can falsely occlude frame N+1 actor positions.

The audit probe therefore contains:

- custom color/depth creation and rebind;
- requested/actual MSAA logging;
- same-sample rebind;
- a single-sample color + tested-depth sample-mismatch control;
- `depthwrite=false` correct control;
- `depthwrite=true` contamination negative control.

These must be run on the pinned runtime/target GPU before #836 is implementation-ready.

---

# 6. AA and the hard cross-pass edge

The aesthetic requirement is coherent only if “environment AA” and “actor/environment ownership” are different stages.

The cleanest first proof is:

```text
environment geometry -> native color + pristine depth
                     -> color-only AA / treatment
held pristine depth  -> binary actor depth test
```

This permits smooth environment color while keeping the actor/environment decision binary at native pixels. It avoids assuming multisampled depth semantics before actual LÖVE/backend evidence exists.

Required comparison matrix for a later GPU run:

- no AA control;
- color-only postprocess AA;
- supersampled environment color + native depth authority;
- MSAA color/depth with actual sample counts recorded.

A foreground occluder crossing a live actor is the important visual oracle. Transparent inter-geometry composition remains separate; the first retained-depth proof should stay opaque/cutout.

---

# 7. Temporal asymmetry and snapshot ownership

A held environment frame is not just:

```text
color + depth
```

It is at least:

```text
color
+ depth
+ exact resolved camera pose/basis
+ projection/framing/principal-point state
+ camera-relative fog/presentation facts required to interpret the frame
```

Why: if the environment was rendered from optical state `C0/P0` and an actor is rendered at 60 Hz using `C1/P1`, the actor’s projected screen position/rays no longer correspond to the depth value stored at that pixel.

The checked-in pure numerical oracle deliberately measures this failure. In its fixture:

- using a newer camera over held environment optics moves the actor **19.27 px**;
- changing principal-point offset by 0.18 NDC moves it **23.04 px** relative to the held environment;
- fixed-camera projection shifting and camera following also disagree at another depth, proving they are not interchangeable visual tricks.

Correct first policy: actors may animate at 60 Hz in world space, but while environment color/depth are held they are projected using the **held** optical snapshot. Alternative policies—forced environment refresh, reprojection, overscan/master representation—need their own evidence.

---

# 8. #836 x #837 compatibility

| Environment cadence | camera transform | projection-center cadence | Natural? | Reason |
| --- | --- | --- | --- | --- |
| 60 Hz | static | static | yes | ordinary shared depth |
| 15 Hz held | static | static | yes | actor uses held optics |
| 15 Hz held | 15 Hz held | static | yes | moving sequence advances atomically |
| 15 Hz held | 15 Hz held | 15 Hz held | yes | all optical state advances with snapshot |
| 15 Hz held | 60 Hz moving | static | no, not without extra machinery | stale camera/depth |
| 15 Hz held | static | 60 Hz #837 shift | no, not without extra machinery | held image/depth represent old projection window |
| 15 Hz held | 60 Hz moving | 60 Hz shift | no, not without extra machinery | both mappings stale |

Thus #836 may remain camera-independent as a capability, but moving camera/projection is not “free”. A low-cadence environment can still support moving cameras by moving them at the held cadence, refreshing on optical changes, or later adding a justified reprojection/overscan scheme.

---

# 9. Map / spatial-family reconciliation

Current Second Gate Map truth remains useful and first-class: compact grid `layout`, integer Event `x/y`, wall-event topology constraints, deterministic traversal and procedural generation.

The existing `docs/reports/map-representation-architecture-survey-2026-08-11.md` already established:

```text
authored semantic representation
  -> deterministic resolver/compiler
resolved/compiled structural representation
  -> renderer/GPU adaptation
renderer/GPU geometry
```

#695 sharpens this to: **plural at the authoring boundary; shared at the consumer boundary.**

The audit-only `freeform-pressure.json` asks what a tiny non-grid authored 3D place actually needs: placements/transforms, a constrained traversal provider, stable anchors, one Event/transition attachment, and resolved renderables/bounds/inspection. It does not prove that current grid Map needs XYZ transforms, that every environment should be called Map, or that traversal should be normalized into one universal encoding.

Recommended boundary remains:

```text
specialized authored environment family
 + specialized traversal/placement adapter
              |
              v
small resolved consumer capabilities
 renderables / bounds / anchors / lighting / inspection
              |
              v
existing Scene + world presentation host where applicable
```

Keep current grid Map byte/schema-stable while another family is prototyped beside it.

---

# 10. Performance / transport evidence

Existing repository measurements are more informative than framebuffer intuition. `viewport_3d` records the prior CPU near-plane path costing roughly **10.14 -> 4.05 ms mean** and **14.40 -> 6.39 ms p95** when disabled in its measured Map 8 sample. Effekseer documentation also records CPU simulation/submission as significant. Holding environment color therefore does not automatically quarter all world costs; update/simulation ownership must be explicit.

Nominal additional payload for one RGBA8 environment color plus one 32-bit depth-like attachment, before driver overhead:

| surface | pixels | color + depth |
| --- | ---: | ---: |
| classic 256x240 | 61,440 | 480 KiB / 0.469 MiB |
| four_three 320x240 | 76,800 | 600 KiB / 0.586 MiB |
| wide 426x240 | 102,240 | ~799 KiB / 0.780 MiB |

MSAA multiplies sample storage and must use actual `getMSAA()` results, not the request value.

The idealized cadence term `A + E/4` for actor/composite cost `A` and environment render cost `E` is only an envelope. Refresh frames cost about `A + E`; a policy that refreshes for every 60 Hz optical change loses the saving. #836 should not be sold as an optimization until representative measurements say so. It may still be valid purely as an aesthetic temporal mode.

---

# 11. Audit fixtures

`tools/audits/world-presentation-ownership/` contains three deliberately separated evidence forms:

1. **Compact LÖVE framebuffer/temporal/projection probe**: custom retained depth, requested/actual MSAA, foreground environment occluder, 60 Hz actor, 15 Hz environment, held-optics correct mode, current-optics/stale-depth negative mode, color-only AA, and retained-depth mutation negative control.
2. **Pure numerical projection oracle**: stale camera/projection mismatch and fixed-camera projection shift versus camera follow. `projection-oracle-results.txt` records the checked run.
3. **Spatial-family pressure data**: `freeform-pressure.json`, explicitly not a proposed Thestra schema.

The sandbox used for this audit has no LÖVE executable. The LÖVE fixture is authored but **not executed here**. This is an acceptance blocker, not a detail to paper over.

---

# 12. Invariants to preserve

1. `WorldCamera` remains the resolved world-camera semantic authority; Scene owns durable defaults.
2. Projection-window movement is projection/framing state, not movement topology or another camera ontology.
3. Authored composition, logical render surface, internal render target, and host output remain distinct.
4. Current grid Map/Event semantics remain first-class and schema-stable.
5. World and screen Effekseer roles remain explicitly separate.
6. Held environment color/depth are atomic with the optical state that produced them.
7. No live drawable tests against a snapshot produced by a different optical state unless a deliberate reprojection algorithm owns it.
8. Pass/cadence membership is presentation policy, not inferred gameplay identity.
9. Environment color treatment never becomes depth/spatial authority.
10. Live actor depth writes never mutate the retained environment snapshot; use read-only environment depth or an explicit working-depth strategy.
11. Image degradation belongs after environment shading/AA and before later live actor/UI presentation unless visual evidence proves another ordering.
12. Cross-pass AA must not silently soften the requested binary actor/environment ownership edge.
13. Transparent world geometry remains an explicit later composition problem.
14. Performance claims require representative measurements.
15. No canonical G5/G6 recapture is required or authorized by this audit.

---

# 13. Recommended bounded follow-ups after GPU evidence

**A. `WorldCamera` projection-center semantic** — normalized offset on existing resolved camera; shader/Effekseer/picking consumers share it; no Map/movement changes. Smallest credible #837 slice.

**B. Held-world framebuffer spike** — reusable held `{color, custom depth, resolved optical snapshot}`; opaque environment first; read-only environment depth; one live mesh/cutout actor; correct/incorrect stale-optics controls; explicit working-depth comparison for multiple live objects.

**C. World cadence-policy spike** — tiny `held`/`live` resolved presentation policy pressure-tested on door, decorative NPC, gameplay actor, weather, torch and projectile; do not add `isActor`/`isBackground`.

**D. AA ownership matrix** — post-AA, supersampled color/native depth, MSAA and no-AA; capture foreground-occluder crossings and actual sample counts.

**E. Plural environment-family proof under #695** — authored-3D source beside, not inside, current grid Map; one traversal provider, Event anchor, transition, renderable/inspection boundary.

Keep transparent-world composition as a separate follow-up unless #836’s first opaque proof demonstrates it is unavoidable.

---

# 14. Acceptance status at this patch boundary

| acceptance area | status |
| --- | --- |
| grounded on fetched current `main` | **complete** — `d5a7f8d2...` |
| exact current frame/canvas/depth ownership | **complete** |
| `WorldCamera` inventory / #837 reduction | **complete** |
| presentation-surface contract | **complete** |
| pass-membership pressure test | **complete in report**; durable policy intentionally not invented |
| static + moving stale-camera/projection analysis | **complete numerically**; GPU visual control authored |
| #836 x #837 matrix | **complete** |
| Map/#695 reconciliation | **complete** |
| LÖVE 11.5 API feasibility | **complete at API/source level** |
| executable LÖVE 11.5 retained-depth/MSAA proof | **fixture authored; pinned-runtime execution pending** |
| AA hard-edge positive/negative captures | **fixture authored; execution pending** |
| retained-depth mutation negative control | **fixture authored; execution pending** |
| representative new GPU performance numbers | **pending target-GPU execution** |
| canonical G5/G6 recapture | **not performed, as required** |
| production schema/runtime rewrite | **not performed, as required** |

**Recommendation:** do not close #841 merely because this report exists. First reconcile the owner’s other parallel audits into this PR, then run the repository-local probe under pinned LÖVE 11.5 and attach its capability log/captures. If those controls behave as expected, the architecture has converged enough to file/implement the bounded slices above. If they do not, revise #836’s framebuffer/depth strategy before production work begins.
