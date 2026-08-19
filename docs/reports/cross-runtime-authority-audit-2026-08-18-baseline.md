# Cross-Runtime Authority Audit — 2026-08-18

**Repository:** `JosephSerUSP/Second-Rite`  
**Audited main:** `726eabcd205cb405f2be780246068938698a9284`  
**Scope:** Thestra runtime + Thestra Studio cross-runtime semantic authority, execution-host boundaries, duplicate semantics, and authoring latency.  
**Status:** architecture/evidence report only. No production architecture, `AGENTS.md`, runtime semantics, or Studio behavior changed by this audit.

## Executive finding

The repository's current rule — **“One implementation, never an approximation. The editor previews through the real engine.”** — solved a real and important problem: it made semantic drift structurally suspicious and pushed final-fidelity questions through the actual runtime. That success should be preserved.

Its literal execution-host interpretation is now too coarse.

Current main contains four materially different kinds of work that the rule often treats as one:

1. **Pure deterministic semantics** that can run anywhere if there is one authoritative source of the rule.
2. **Derived resources / IR** whose authority is established when a source revision changes and which multiple consumers can then reuse.
3. **Runtime facilities** that genuinely need the Lua/LÖVE implementation, resource loader, or presentation stack, but do not need a fresh stage and cold process for each query.
4. **Actual runtime truth**: simulation, validation, final rendering, Test Play, screenshots, export smoke, and other operations where running the game/runtime is the point.

The current architecture often makes categories 1–3 pay category-4 costs.

The clearest measured examples are now complementary rather than competing:

- Sprite provenance historically made a ~13 ms image lookup accompany a ~2390 ms `sprite-resolution` runtime consultation (#713). #723 amortized that with caching, but the underlying fact is mostly filename/key-token parsing + resource resolution and does not intrinsically require game state, GPU rendering, or a cold LÖVE process.
- After #761, Map 2's authoritative renderable payload is only ~0.86 MiB, yet #754 measured an identical-revision request at ~2063 ms because staging and LÖVE bootstrap dominate. Its persistent-child falsifier cut the warm identical-revision request to roughly ~215 ms end-to-end while preserving the existing Lua authority.
- Separately, #765 measured Studio reconstructing the compact definition/placement IR into the historical per-surface representation: Map 2 adapter + modulation was ~382 ms and ~109 MiB of JS heap versus essentially zero adapter expansion and ~1 MiB for direct definition consumption. This is a **consumer representation problem**, not a runtime-host problem.
- Studio already contains deliberate browser-local semantic implementations for animation timing, vertex shading, static-light baking/sampling, wall-side modulation, icon palette rendering, and authored-storage behavior. Several are explicitly labelled “paired” or “exact browser-side counterpart.” The literal rule is therefore already descriptively false; what currently protects correctness is parity intent/tests and careful ownership, not one physical execution host.

The audit therefore supports a successor principle:

> **ONE SEMANTIC AUTHORITY, NOT NECESSARILY ONE EXECUTION HOST.**
>
> A semantic rule has one authoritative definition or mechanically generated contract. Pure deterministic semantics may execute in every host that needs them. Expensive deterministic derivation should produce revision/content-addressed artifacts that multiple hosts consume directly. Lua/LÖVE-backed services should remain process boundaries only when they genuinely need runtime facilities, and they should be persistent/incremental when used on the authoring path. Actual simulation, validation, Test Play, final renderer fidelity, and golden truth remain real runtime boundaries.

This report proposes that invariant; it does **not** modify repository policy yet.

---

## 1. Audit basis and current architecture

### Repository authority consulted

The audit used current-main code, not historical reports, as implementation truth, with `AGENTS.md`, `docs/ENGINE-STATE.md`, and `docs/SPEC.md` as policy/architecture context.

Relevant history was inspected in full before classifying current paths:

- #402 — animation-token provenance requirement;
- merged #681 — runtime-authoritative sprite metadata and `sprite-meta`;
- #713 — measured per-thumbnail LÖVE boot cost;
- merged #723 — sprite-resolution cache/invalidation/coalescing;
- #754 — live/persistent runtime exploration and current timing measurements;
- draft PR #756 — measurement/design implementation of #754, deliberately not productionizing persistence;
- #765 — direct Three definition consumption;
- draft PR #766 — direct mesh-definition experiment;
- #467 — lighting authoring architecture, including the already-explicit requirement that drag/paint feedback not wait on LÖVE.

Open issues/PRs and named branches were searched for overlapping cross-runtime/shared-core ownership. No open PR currently owns this audit. A branch named `exp/shared-semantics-spike` exists without a PR, but the most suggestive file, `engine/semantic_calculation.lua`, is byte-identical to current main and is already current production architecture from #308. It is not evidence of a competing active shared-core implementation.

### Existing policy that matters

The current policy has two separate ideas that should not be lost when its wording eventually changes:

- **one semantic implementation / no approximations;**
- **final previews and validation use real runtime authority.**

The problem is the implicit third claim that has grown around them:

- **therefore a semantic question implemented in Lua must cross a fresh LÖVE process boundary.**

That third claim is not necessary for the first two to remain true.

### Existing architecture already hints at the successor model

The repository already contains several useful precedents:

- `engine/semantic_calculation.lua` is explicitly pure, side-effect-free calculation semantics isolated from participant discovery and authority commits.
- `docs/SPEC.md` describes the Formula language as a portable authored contract even though the current evaluator is Lua.
- `docs/design/authored-data-storage.md` distinguishes semantic identity from physical storage representation and declares storage behavior shared across runtime/tools.
- #761 changed the map-renderable wire format into exact reusable definitions + placements: an authoritative IR rather than repeated expanded geometry.
- #723 caches results from runtime authority instead of treating every query as a new truth computation.

The audit recommendation is therefore an extension of patterns already present, not a foreign architectural reset.

---

# 2. Studio → LÖVE / runtime-boundary census

## Legend

**Clock**

- **A** — Authoring clock: pointer/keystroke/selection/drag/load feedback.
- **C** — Compilation clock: revision-derived deterministic work.
- **R** — Runtime/truth clock: actual game/runtime execution, final validation, or fidelity evidence.

**Destination**

1. **Shared executable semantics**
2. **Authoritative compiled artifact / IR**
3. **Persistent semantic / preview service**
4. **Actual game/runtime boundary**

“Cold LÖVE” below means the current production path starts a new `lovec`/LÖVE child for the request. The long-lived Node `runtime-bridge-server.js` does **not** currently make its LÖVE child persistent.

## Complete current Studio boundary table

| Boundary / surface | Caller and trigger | Immediate authoring path? | Stage / snapshot? | Cold LÖVE? | Large artifact? | Reuse today | Semantic fact / real dependencies | Why must this cross a process boundary? | Destination |
|---|---|---:|---:|---:|---:|---|---|---|---|
| **Sprite resolution / timing provenance** (`GET /api/sprite-resolution`, `sprite-meta`) | `widgets.js` sprite field requests metadata when inspecting/selecting sprite assets | **Yes, but async/non-blocking**; local animation paints without waiting | Yes via `execOpenedProject()` | Yes on cache miss | No | #723 result cache + in-flight coalescing + invalidation signatures | Resolve logical sprite path; parse `[fps=N]` / `[speed=N]`; key token precedence over filename; default rate. Needs filesystem inventory/stat for path resolution, but no game state/GPU. | **It does not intrinsically need to.** Current boundary exists because authority is implemented in `presentation/sprite_sheet.lua`. Pure token/timing semantics plus a host FS adapter are extraction candidates. | **1** |
| **Map renderable bundle** (`preview-map`) | Three map viewport / runtime bridge on map load and authoritative refresh | **Yes**; central authoring surface | Yes: same-root data snapshot or external full stage | Yes | After #761 transport is ~0.86–1.03 MiB on measured Maps 2/3; historically huge | No revision result cache; every request currently re-stages/reboots | Generated/resolved map; presentation geometry/material/resource resolution; renderable definitions/placements; provenance; static-light/shading source data. Uses current Lua loader and presentation stack, LÖVE filesystem and some presentation initialization. No live save/player state is required for the authoring request. | **A boundary is presently justified by implementation dependencies, but a fresh boundary per request is not.** The compact renderable is compilation output and the LÖVE host should be warm/revision-scoped while those dependencies remain Lua/LÖVE-owned. | **2 + 3** |
| **Map inspection** (`preview-map-inspection`) | map inspector / server POST with transient map | **Yes** when inspecting procedural/generated topology | Yes | Yes | Moderate structured JSON, not the dominant mesh payload | None | Deterministic generated map, rooms/corridors/openings/zones/events/features/lights/protected cells/entrance/exit/tileset. Uses `GameSession`, map loader/generation and resource resolution. No renderer/GPU or player save state. | **No fundamental reason.** Near-term it crosses because the authoritative generation/loader is Lua. Treat as a persistent semantic service now; later it may become revision-derived IR or shared pure semantics if generation is extracted. | **3**, potentially **2/1** later |
| **Scene preview** (`preview-scene`) | Studio explicit scene preview | Usually explicit preview, not every keystroke | Yes | Yes | Rendered output | None | Real Scene host, presentation composition, fonts/assets/rendering | **Yes for final-fidelity preview.** This is intentionally runtime presentation truth. It should not become the primitive for ordinary form feedback. | **4** |
| **Window preview** (`preview-window`) | window editor explicit preview with current layout/mock payload | User-invoked/preview refresh; can be authoring-adjacent | Yes | Yes | Rendered output, small | None | Real runtime UI panel/text rendering, font metrics/resources, LÖVE graphics | **Yes when the question is “what will the real runtime draw?”** Local geometry/form editing can stay local; the fidelity oracle remains LÖVE. | **4** |
| **Animation runtime preview** (`preview-anim`) | explicit runtime animation preview | Authoring-adjacent but separate from smallBattler's local CSS/frame preview | Yes | Yes | Rendered output | None | Real animation/presentation execution, image resources, timing/runtime drawing | **Yes for runtime-fidelity oracle.** It should not be required for each frame of interactive scrub/selection when the needed rule is pure. | **4** |
| **Font preview** (`preview-font`) | font selection/preview | Authoring-adjacent explicit preview | Yes | Yes | Rendered output | None | Real LÖVE font loading/metrics and runtime panel/text rendering | **Yes for exact runtime font/pixel truth.** A browser thumbnail may still be presentation adaptation, but final authority belongs here. | **4** |
| **Fog preview** (`preview-fog`) | map/fog editor preview | Authoring-adjacent explicit fidelity preview | Yes | Yes | Rendered output | None | Runtime map presentation, fog shader/pipeline, LÖVE graphics | **Yes.** GPU/renderer behavior is the semantic question. | **4** |
| **Validation** (`GET /validate`, `lovec . validate`) | server after save / explicit validation / gates | Not pointer-clock; save feedback | Yes through opened-Project execution | Yes | Diagnostic text only | None | Whole authored-data loader/validator/reference graph, runtime semantics; generally no need for final GPU, but intentionally broad authoritative validation | **Yes as a truth boundary, not because it is Lua.** Validation is allowed to pay whole-project cost and proves the actual runtime can consume the Project. Avoid duplicating it in JS. Incremental diagnostics could later supplement it, never replace G1. | **4** |
| **Test Play** (`POST /play`) | user requests Play | No; explicit runtime action | Yes | New visible game process by design | No serialized preview artifact | N/A | Real game state, input, simulation, audio, presentation, save behavior | **Absolutely yes.** Running the game is the product. | **4** |
| **Test Battle** (`play-test-battle` / `test-battle`) | Studio test-battle action | No; explicit runtime action | Yes | Yes/new game runtime | No large bridge artifact | N/A | Real battle state/simulation/presentation | **Yes.** This is simulation truth. | **4** |
| **Campaign-generator Test Play / executable proof** | generation workflow stages fixture/project and boots it | No; bounded proof after generation | Yes | Yes | No bridge artifact | None | Full generated Project boot/playability and real runtime contract | **Yes.** It is an integration/product proof, not editing feedback. | **4** |
| **Screenshots / G5-supporting runtime capture** (`screenshots`) | explicit Studio/tooling capture and golden workflows | No ordinary authoring | Yes | Yes | Potentially large encoded image output; server allows much larger stdout | Golden/reference reuse is external to request path | Exact game renderer pixels under deterministic fixtures | **Yes.** Renderer/GPU/presentation fidelity is the evidence. | **4** |
| **Export preflight / staged validation / packaged smoke** | Export Game path | No; build/ship clock | Full stage by definition | Yes (`validate`, plus packaged executable smoke where applicable) | Export artifacts intentionally large | Build artifacts, not editor query cache | Hermetic packaged runtime, resolved resources, compiled data, platform runtime, validator | **Yes.** The artifact being validated is the thing being shipped. | **4** |
| **Runtime map bridge Node service** (`runtime-bridge-server.js`) | Studio map client calls persistent Node bridge | Yes | The Node service itself persists, but each LÖVE request stages/snapshots | Each request cold-boots | See renderable/inspection rows | Node process persists only | Routing, request-file lifecycle, staging, child execution | **Node process separation is an implementation choice; semantic process separation depends on called operation.** #754 shows the child should persist for suitable operations. | Infrastructure for **3** |
| **Same-root runtime-data snapshot** (`createRuntimeDataSnapshot`) | `project-play.js` and runtime bridge before runtime queries | It sits directly in front of many A-clock requests | Copies authored JSON, resolves defaults/RTP, compiles runtime data into disposable tree | N/A itself | Can be filesystem-heavy; #754 measured snapshot/stage as dominant ~1.1–1.7 s class cost | **None across requests** | Deterministic Project/RTP/default resolution and runtime-data compilation; no game state/GPU | **It should not be repeated simply because a semantic query follows.** This is compilation-clock work. A revision-scoped snapshot/artifact identity should be reused until its inputs change. | **2** |
| **External Project full stage** (`stageRuntimeGame`) | `project-play.js` when Project and runtime roots differ | Can precede authoring previews for external Projects | Copies runtime directories + Project assets/data, resolves inherited resources, compiles data | N/A itself | Potentially large filesystem copy | None across preview requests | Packaging/staging composition, not the queried semantic fact | **It is justified for export/Test Play hermeticity, not for each authoring query.** Persistent preview service should own one revision-scoped stage, or consume explicit source roots where safe. | **2/3** for preview; **4** for export/play |

## Runtime CLI modes that exist but are not ordinary Studio query surfaces

`main.lua` also exposes `preview-texture`, `preview-texture-batch`, and `preview-geometry`. These are primarily asset/build/development tooling paths rather than evidence that the current Studio UI asks LÖVE for those facts on each authoring interaction. Their classification still follows the same rule:

- image decode/GPU/render fidelity operations may remain LÖVE/tool-owned;
- stable expensive preprocessing should become compiled/cacheable artifacts;
- the existence of a Lua CLI mode is not itself architectural evidence that a browser editor interaction must spawn it.

## The staging multiplier is the first-order process cost

`tools/editor/project-play.js` makes the cost shape explicit:

- same-root requests construct a disposable runtime-data snapshot so repo development still sees exact resolved/compiled Project data without copying runtime/assets;
- external Projects construct a full staged runtime game;
- the temporary tree is then removed when the child exits.

That model is excellent for **isolation and truth**, but expensive when repeated as a prelude to low-entropy semantic questions.

#754's measurements show this is not a theoretical concern. On the post-#761 Map 2 control:

| request | snapshot/stage | LÖVE bootstrap | map load | authority work | serialize | transfer | JS parse | compatibility work |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| first | ~1630 ms | ~746 ms | ~8 ms | ~664 ms | ~22 ms | ~8 ms | ~3 ms | ~58 ms |
| identical revision | ~1137 ms | ~517 ms | ~9 ms | ~270 ms | ~27 ms | ~7 ms | ~3 ms | ~37 ms |

OS process creation itself was only a few milliseconds in the same investigation. The expensive “process boundary” is really **reconstructing the runtime host context**: stage/snapshot + LÖVE initialization + broad module/resource initialization.

The persistent-child experiment then demonstrated roughly:

- first request still pays staging/bootstrap;
- identical-revision warm request: ~215 ms end-to-end in the instrumented harness;
- changed transient map with same project revision: ~223 ms;
- fresh restart returns to hundreds of milliseconds plus stage/bootstrap.

That is strong evidence for destination 3 where LÖVE facilities are still genuinely required.

---

# 3. Parallel / handwritten semantics census

## Classification

- **A — harmless presentation adaptation:** transforms an authoritative fact into host-specific UI/render representation without deciding game meaning.
- **B — generated/contract-derived behavior:** consumer behavior constrained by an authoritative schema/artifact/manifest rather than independently re-deciding semantics.
- **C — true parallel handwritten semantic implementation:** two or more hosts manually encode the same rule.
- **D — deliberately local authoring behavior because runtime consultation would be too slow:** usually also C today, but with an important product reason for local execution.

## Current cases

| Semantic area | Runtime / authority-side implementation | Studio/tool counterpart | Class | Risk / observation | Destination |
|---|---|---|---|---|---|
| **Sprite timing token grammar and precedence** | `presentation/sprite_sheet.lua::parseKey`, timing metadata, `fps > speed`, speed→fps conversion, default rate | `tools/editor/js/widgets.js` parses `[fps=]` / `[speed=]` and computes local preview rate | **C + D** | This is the canonical historical contradiction. The local animation needs immediate frames; the runtime query supplies provenance/tooltip metadata. Two handwritten timing implementations still exist. | **1** |
| **Sprite resource search directories / filename resolution cues** | `presentation/sprite_sheet.lua` asset-directory order and resolution | `widgets.js` `ASSET_STRIP_DIRS` explicitly mirrors runtime resolution search paths for the asset strip | **C + D** | Resource search policy can drift even if timing parsing stays aligned. Separate pure resolution policy from host filesystem adapters. | **1**, with FS adapters |
| **Vertex shading** | `engine/vertex_shading.lua` | `tools/editor/js/vertex-shading.js` | **C + D** | Runtime file explicitly calls out a **paired JS implementation**. It is pure, renderer-neutral deterministic math: ideal shared-semantics experiment material. | **1** |
| **Static lighting bake / visibility / falloff** | `engine/lighting.lua` | `thestra-viewport-contract.js::bakeAuthoringLighting` | **C + D** | JS labels itself an **exact browser-side counterpart**. This is deliberately local so moving lights/painting remains frame-responsive; #467 already codifies that constraint. | **1** |
| **Static light-grid bilinear sampling** | runtime/presentation lighting sampling | `thestra-viewport-contract.js::sampleAuthoringLighting`; additional sampling in `second-rite-editor-adapter.js` | **C + D** | Small formula, but repeated in multiple browser modules increases drift surface. | **1** |
| **Wall-side orientation modulation (`0.76`)** | runtime viewport/material shading | `second-rite-editor-adapter.js::surfaceOrientationFactor` | **C + D** | Tiny constant/formula with visible authoring consequence. Better generated/shared than copied. | **1** or contract-generated constant |
| **Icon palette shader behavior** | runtime GLSL/palette semantics | `tools/editor/js/icon-renderer.js` | **C + D, sanctioned** | `AGENTS.md` currently documents this as the deliberate exception because icon drag must be immediate. It proves the architecture already accepts local execution when latency demands it; the safer future is shared/generated shader semantics, not cold runtime calls. | **1**, low urgency |
| **Authored-storage physical contract** | `engine/data/authored_storage.lua` | `tools/data/authored-storage-physical.js`, `tools/data/authored_storage.py` | **C + B** | Highest breadth duplicate found: path safety, representation checks, fragment identity/order, manifest interpretation and version behavior exist in Lua/JS/Python. The manifest centralizes declarations, but executable rules are still handwritten in three hosts. | **1** and/or generated conformance contract |
| **Authored-storage manifest/schema declarations** | shared manifest + runtime consumers | JS/Python consumers | **B** | Healthy direction: source declarations can be shared even when host IO differs. Expand this style rather than hand-copying policy. | **1/B** |
| **Map definition/placement wire representation** | #761 runtime-authored renderable bundle | `second-rite-editor-adapter.js::decodeTransport()` compatibility expansion | **B + A** | Not a semantic reimplementation; the browser faithfully expands authoritative IR. But it destroys the compact representation and measured tens/hundreds of MiB of browser memory. #765/#766 already own removing the expansion. | **2** |
| **Runtime Z-up → Three Y-up transform and winding adaptation** | authoritative bundle uses runtime coordinates | `thestra-viewport-contract.js` converts to Three coordinate conventions | **A** | This is a consumer/backend adaptation, not game-semantic duplication, provided the transform exists in one adapter and is tested. It should not require LÖVE execution. | Local presentation adapter |
| **Three camera/editor navigation policy** | no gameplay equivalent | viewport contract / Three workspace | **A** | Editor-only authoring behavior; not a semantic mirror. | Local |
| **Three world fidelity/pixelation presentation** | runtime has its own renderer/shaders | `three-world-fidelity-core.js` | Primarily **A** | Different renderer host approximates/represents authoring view; exact final-pixel authority remains G5/runtime. Any copied semantic constants should be contract-driven, but WebGL implementation itself need not be shared with LÖVE. | Local A + runtime truth oracle |
| **Schema-driven Studio forms** | authored config/registry/schema sources | generated/editor form source and widgets | **B** | This is the healthy alternative to duplicating validation logic: Studio consumes declared shape. | Keep B |
| **Whole-Project semantic validation** | LÖVE validator / loader | Studio `/validate` calls real validator | **Not duplicated** | No evidence was found that Studio contains a second G1 semantic validator. Keep this boundary. JS save/storage checks are local shape/storage guards, not replacement runtime validation. | **4** |
| **Formula language** | current Lua formula evaluator/compiler | no equivalent full Studio evaluator found in this audit | **No current duplicate** | `SPEC` already defines Formula as a portable pure contract. If Studio needs live formula explanation/prediction, this should become shared executable semantics rather than a new handwritten JS evaluator or per-keystroke LÖVE query. | Future **1** if cross-host execution is needed |
| **Pure semantic calculation reducer** | `engine/semantic_calculation.lua` | no competing Studio implementation found | **Healthy seam** | Its explicit purity and separation from source discovery/commit authority is a model for extraction boundaries. The stale `exp/shared-semantics-spike` branch does not contain a different version. | Potential future **1** |

## Important distinction: duplication is not automatically wrong

The audit does **not** conclude that every pair of Lua and JS files must be mechanically fused.

The question is whether the duplicated code decides the same semantic fact.

- Three coordinate conversion is host adaptation: it belongs in the adapter.
- A `BufferGeometry` constructor is consumer representation: it belongs in Three.
- Browser DOM sizing, camera controls, selection outlines and gizmos are Studio behavior.
- Final LÖVE shaders and Three authoring materials may be different implementations because they are different renderers, provided semantic inputs (lighting field, material identity, side-factor contract, fog state, etc.) are not independently invented.

What should be eliminated is **parallel authority**: two handwritten pieces of code that may disagree about a fact whose disagreement would change authored/game meaning.

---

# 4. Destination classification

## 1 — Shared executable semantics

### Strong first candidates

1. **Vertex shading**
   - pure numeric inputs/outputs;
   - no filesystem, LÖVE API, game session or renderer required;
   - already duplicated intentionally and parity-tested;
   - useful in runtime, Studio and potentially future tooling/languages.

2. **Static-light bake + sample math**
   - deterministic topology/light-source inputs → RGB grid;
   - no inherent GPU requirement;
   - Studio must run it synchronously while dragging;
   - #467 already says frame-local feedback must not wait for LÖVE.

3. **Sprite timing grammar/precedence**
   - tiny, deterministic, well-understood historical fixture;
   - ideal proof that shared authority can execute locally;
   - filesystem/path search should be separated from pure token precedence.

4. **Authored-storage representation/path/identity policy**
   - cross-language drift risk is larger than its UI visibility suggests;
   - shared manifest is a good start, but executable policy remains triplicated;
   - likely needs a mix of generated test vectors/contracts and host-specific IO rather than forcing all IO through one runtime.

### “Why must this cross a process boundary?”

For these candidates: **it should not.**

A process boundary adds no semantic protection if every host is executing the same authoritative rule or generated contract. It only adds latency, staging invalidation complexity and failure modes.

### What “shared” should mean

This audit intentionally does not choose Lua-to-JS translation, WASM, embedded Lua, a new language, code generation, or another framework.

A follow-up experiment should compare at least:

- **single portable source compiled/generated to host bindings**;
- **one embeddable implementation invoked by both Lua and JS**;
- **generated tables/test vectors plus tiny host evaluators** for domains where the rule is declarative;
- **schema/IR generation** where data declaration, not an algorithm VM, is the true authority.

The experiment should be falsifiable on maintenance burden, debuggability, startup/runtime cost, source maps/error messages, CI portability, and whether it preserves ordinary LÖVE deployment.

Do **not** begin by declaring JavaScript the canonical language and translating it to Lua, or vice versa. The semantic domain should choose the representation.

---

## 2 — Authoritative compiled artifact / IR

### Strong current cases

1. **Runtime-data snapshots / compiled authored resources**
   - source Project + RTP/default/package inputs produce deterministic runtime data;
   - current editor requests rebuild disposable snapshots repeatedly;
   - source revision/content identity should own invalidation.

2. **Map renderable definitions + placements (#761)**
   - already a successful authoritative IR;
   - #765 shows Studio should consume it directly instead of expanding back to old geometry arrays;
   - per-placement color/modulation can remain placement-owned while position/normal/UV/index definitions are shared; the #765 falsifier passed exactly for measured Maps 2/3.

3. **Generated map inspection / topology** where source revision + seed/config make the result stable
   - currently easiest to obtain from Lua service;
   - repeated consumers should not need to regenerate identical topology.

4. **Expensive asset preprocessing**
   - geometry prebakes, texture compilation, generated asset metadata and similar deterministic products belong on source-change/build clocks, not every view-open clock.

### “Why must this cross a process boundary?”

The **artifact may cross** because producers and consumers are different processes/languages. The **derivation need not repeat** at every crossing.

Authority lives in:

- producer version;
- explicit inputs;
- revision/content identity;
- deterministic artifact format;
- validation/conformance tests.

This is stronger than “call the producer every time” because it makes identity and invalidation explicit.

---

## 3 — Persistent semantic / preview service

### Strong current cases

1. **Map renderable producer while it still requires the Lua/LÖVE presentation stack.**
2. **Map inspection / procedural generation while generation remains runtime-Lua-owned.**
3. Potential future renderer/resource queries that need LÖVE filesystem/image/font facilities but not a new process each time.

#754 now provides unusually strong evidence for this category. The right first implementation is **not embedding the game**. It is one revision-scoped staged/snapshotted context plus a long-lived authority child that accepts serialized requests, invalidates on relevant source changes, and can be killed/restarted safely.

Required safety properties from #754 should remain:

- child lifecycle tied to Project/runtime revision;
- one request at a time until concurrency is proven safe;
- bounded timeout and health detection;
- crash recovery;
- kill/await child before deleting its stage;
- invalidate on non-transient Project content/assets/runtime/config/RTP/package changes and project switch;
- transient authored map payloads may change within the same host revision when the operation explicitly supports them.

### “Why must this cross a process boundary?”

Because some producers currently depend on the real Lua/LÖVE loader/presentation/resource environment, and process isolation is useful for crash/resource ownership. That is a convincing reason for **a service boundary**, but not for **stage + cold boot per query**.

---

## 4 — Actual game/runtime boundary

Keep these LÖVE-owned and real:

- Test Play;
- Test Battle;
- real Scene/window/font/animation/fog fidelity previews;
- G1 whole-Project validation;
- screenshots and G5 pixel truth;
- runtime/unit/integration tests whose claim is about actual game behavior;
- export preflight, packaged executable validation and smoke;
- audio/input/save/session behavior;
- any semantic fact that depends on mutable game state rather than authored/revision state.

### “Why must this cross a process boundary?”

Because **the runtime execution is itself the evidence**. Moving these into Studio would weaken the proof or couple editor stability to game failures.

---

# 5. The three clocks

## Authoring clock

**Purpose:** maintain a feeling of direct manipulation.

Examples:

- typing numbers/text;
- dragging lights/events/models;
- painting/blur;
- changing a sprite and seeing it animate;
- moving the camera;
- selecting/picking surfaces;
- toggling layer visibility;
- changing a numeric shading/light property.

### Rule

No authoring-clock operation should synchronously depend on:

- staging an entire Project;
- compiling all runtime data;
- cold-booting LÖVE;
- serializing an unbounded whole-map artifact;
- waiting for a full validation/game simulation pass.

The authoring clock may use:

- shared pure semantics;
- current compiled artifacts;
- local presentation adaptation;
- optimistic/transient preview state;
- a persistent service if the particular interaction can tolerate its bounded latency;
- async runtime truth that catches up without blocking direct manipulation.

### Current good examples

- static-light baking is already local while dragging;
- vertex shading is already local;
- smallBattler frame animation is already local;
- sprite provenance request is async and does not block paint;
- Three picking/selection consumes authoritative provenance locally.

### Current violations / pressure points

- initial/refresh map-renderable requests reconstruct stage/snapshot and cold-boot LÖVE before useful authoritative world geometry arrives;
- map inspection similarly pays compilation/runtime-host setup for deterministic authored/generated facts;
- external Projects can pay full staging where a revision-scoped preview context would suffice;
- if future formula/stat/predicate inspection follows the old rule literally, it is likely to reproduce the sprite-meta mistake.

---

## Compilation clock

**Purpose:** turn authored inputs into deterministic reusable derived resources when relevant inputs change.

Candidates include:

- resolved/default-materialized runtime data;
- map-generation/topology products for stable revision+seed;
- renderable definitions/placements;
- geometry prebakes;
- compiled resource metadata;
- sprite-resolution inventories/path indexes;
- source-derived schemas/bindings/contracts.

### Required architecture

A compilation product should expose an identity that includes all semantically relevant inputs, for example conceptually:

```text
artifact identity = hash(
    source revision/content,
    runtime semantic version,
    RTP/default/package inputs,
    build/preview options,
    compiler/producer version
)
```

Not every artifact needs a cryptographic CAS in the first implementation. The important shift is **explicit invalidation ownership** instead of “new process means fresh truth.”

### Current clock inversion

`createRuntimeDataSnapshot()` performs compilation-clock work immediately before many runtime queries, then deletes the result when the child exits. Identical revisions therefore repeatedly reconstruct the same effective Project.

#723's sprite cache is a useful local fix but also shows the danger of ad-hoc invalidation: once more surfaces cache derived truth, the repository needs a common revision/content identity vocabulary rather than one bespoke signature recipe per endpoint.

---

## Runtime / truth clock

**Purpose:** answer questions whose truth is the actual running runtime or final validator/renderer.

Examples:

- can this Project really boot/play?;
- does G1 accept the complete authored graph?;
- what exact pixels does LÖVE draw?;
- does the packaged executable run?;
- does a battle transition mutate state correctly?;
- do save/load/input/audio/native integrations behave correctly?

This clock may be slower. Its job is proof, not direct manipulation.

### Key separation

The editor should be allowed to show immediate authoring feedback derived from shared semantics or the last valid compiled artifact **while runtime truth catches up**.

That is not an approximation if the immediate path executes the same semantic authority. It is simply a different execution host/clock.

---

# 6. Highest-risk current architectural mistakes

## 1. Treating process locality as semantic authority

The current wording makes “executed inside LÖVE” feel safer than “executed elsewhere,” even for pure math. That encourages developers either to create slow runtime RPCs or to create unacknowledged mirrors when latency becomes intolerable.

**Risk:** both performance regressions and hidden drift.

## 2. Reconstructing identical runtime host context per query

The current bridge snapshots/stages and cold-boots repeatedly even when the authoritative Project/runtime revision is unchanged.

**Risk:** authoring latency grows with repository/project size even if the requested semantic fact is tiny. #754 demonstrates this directly.

## 3. Parallel handwritten semantics without one architectural category

Vertex shading, lighting, sprite timing and authored-storage behavior are not all documented as the same class of problem. Some are sanctioned, some are merely labelled counterparts, some are protected by parity tests.

**Risk:** a future contributor follows policy literally in one domain and follows performance precedent in another, producing inconsistent architecture.

## 4. Conflating producer authority with consumer representation

#761 proved the runtime can author a compact exact mesh IR, but the browser then expanded it back into the historical arrays.

**Risk:** “authority preserved” can still conceal huge avoidable memory/CPU costs. #765 shows representation must be audited independently from semantic ownership.

## 5. Invalidation is endpoint-specific instead of a first-class contract

#723 computes its own disk/runtime signatures. Runtime-data snapshots are disposable. Persistent-service proposals need their own revision invalidation. Artifact work needs compiler/version identity.

**Risk:** caches either miss too often and fail to solve latency, or become stale and violate the very authority rule they were meant to preserve.

## 6. Cross-language storage semantics are broader than the visible preview mirrors

Authored storage is currently implemented in Lua, JS and Python. This is less visually obvious than lighting drift but potentially more dangerous because it affects path safety, identity, ordering and load/write behavior.

**Risk:** a Project can mean different physical things to runtime, Studio and tooling even while visual parity is green.

## 7. The old invariant can cause future pure semantics to be designed around RPC

Formula evaluation, semantic calculations, predicates, modifier explanations and similar future editor features are natural pressure points.

**Risk:** repeating the sprite-meta history at larger scale.

---

# 7. Easiest / highest-value extraction candidates

## Candidate A — vertex shading (best first experiment)

Why first:

- already pure and renderer-neutral;
- explicitly paired Lua/JS;
- deterministic bounded inputs/outputs;
- strong existing tests/parity expectations;
- immediately exercises the architectural question without entangling IO, game state or GPU.

Falsifier:

- if making one executable semantic source usable in Lua and browser makes debugging/build/deployment substantially worse than the current parity pair, do not force the mechanism onto broader domains.

## Candidate B — sprite timing grammar

Why second:

- tiny historical fixture with known precedence and performance story;
- can separate pure semantic parsing from host-specific filesystem/resource lookup;
- can delete the most symbolically important duplicate in `widgets.js` without forcing local preview to become async.

Falsifier:

- if the chosen shared mechanism costs more to initialize/evaluate than the entire rule or cannot run in plain Studio/LÖVE distributions without new fragile packaging, choose generated rules/test vectors or another mechanism.

## Candidate C — lighting bake + sample

Why after the mechanism is proven:

- bigger algorithm and authoring-critical;
- immediate performance requirement is real;
- existing #467 already owns lighting ontology/fidelity and requires local feedback;
- moving it too early would mix cross-runtime mechanism choice with unresolved lighting-content semantics.

## Candidate D — authored-storage conformance

Why important but separate:

- multi-language and high-impact;
- likely better served by authoritative manifest/schema + generated conformance vectors than by embedding one implementation everywhere;
- should be approached after the experiment distinguishes **shared executable algorithm** from **shared declarative contract**.

---

# 8. Systems that should remain LÖVE-owned

The successor rule must not become “move everything out of Lua.” The following remain healthy runtime ownership:

1. **Mutable game/session state and authoritative transitions.**
2. **Battle/exploration simulation and event execution.**
3. **Final LÖVE renderer, shaders, graphics-state interactions and exact pixel output.**
4. **Audio/input/native integration and platform runtime behavior.**
5. **Whole-Project runtime validation as the release/truth oracle.**
6. **Test Play / Test Battle.**
7. **Runtime save/load behavior.**
8. **Exported executable/package smoke.**
9. **Presentation/resource behavior whose meaning genuinely depends on LÖVE APIs**, unless/until it is deliberately refactored into a pure semantic layer plus host adapter.

Even for these systems, editor integration may use a persistent process rather than repeated cold boots. Ownership and lifecycle are separate questions.

---

# 9. Recommended sequencing

## Step 1 — Land/finish the already-proven representation work (#765/#766)

The direct-definition experiment passed the critical placement-color falsifier on measured Maps 2/3. Preserve runtime-authored geometry definitions, use placement-owned RGB/modulation/provenance where needed, and stop reconstructing the old full surface arrays in Studio.

This should happen before attributing remaining viewport cost to process architecture.

## Step 2 — Productize the bounded persistent-runtime result from #754

Use the measured design, not a speculative embedded game window:

- one revision-scoped preview stage/snapshot;
- one persistent LÖVE authority child;
- transient map requests within the valid revision;
- explicit invalidation and health/lifecycle rules;
- instrument the production path so warm-hit and invalidation behavior remain observable.

Do not make Test Play itself the persistent semantic service.

## Step 3 — Run a shared deterministic semantic-core experiment on a tiny pure domain

Start with vertex shading, then sprite timing. Compare mechanisms rather than committing to a framework prematurely.

Acceptance should prove:

- one semantic source/contract;
- both LÖVE and Studio execute it locally;
- no cold runtime call in the authoring loop;
- deterministic parity;
- understandable stack traces/debugging;
- no material deployment burden;
- a path for future third hosts without rewriting the rule.

## Step 4 — Establish a common revision/artifact identity contract

Before multiplying caches/services, define what invalidates:

- runtime semantic source;
- Project authored source;
- assets/resources;
- RTP/default/package inputs;
- compiler/producer version;
- per-request transient inputs.

Then let sprite cache, runtime-data snapshot reuse, map artifact cache and persistent service share that vocabulary.

## Step 5 — Migrate the architecture rule only after experiments prove the mechanism

Update `AGENTS.md`/SPEC language after the repo can point to concrete working examples in all four destination categories.

The policy should forbid **parallel authority**, not local execution.

---

# 10. External precedents — lessons for Thestra

Only official/primary project documentation is used here. The point is not that Thestra should imitate another engine's implementation language; it is that mature tooling consistently separates **semantic ownership** from **the process that currently answers a UI query**.

## Godot — shared tool/runtime code, separate actual game process

Primary sources:

- Running code in the editor: <https://docs.godotengine.org/en/stable/tutorials/plugins/running_code_in_the_editor.html>
- Game embedding: <https://docs.godotengine.org/en/latest/tutorials/editor/game_embedding.html>

Godot's `@tool` model permits selected code to execute in the editor, in the game, or both. That is direct precedent for **reuse of the same semantic implementation across execution hosts** rather than forcing every editor visualization to RPC into a game.

At the same time, Godot states that the actual game runs in a **separate process even when visually embedded** in the editor, explicitly preserving crash isolation.

**Lesson for Thestra:** do not conflate reusable semantics with Test Play. Shared deterministic functions can execute in Studio; the actual game remains a distinct runtime boundary.

## Unreal Engine — Runtime modules are reusable dependencies of Editor modules

Primary sources:

- Modules: <https://dev.epicgames.com/documentation/en-us/unreal-engine/unreal-engine-modules>
- Editor modules: <https://dev.epicgames.com/documentation/en-us/unreal-engine/setting-up-editor-modules-for-customizing-the-editor-in-unreal-engine?lang=en-US>

Unreal separates Runtime and Editor modules, but editor modules are specifically built to support types/classes in runtime modules. Modules are separately compiled dependency units rather than duplicated implementations.

**Lesson for Thestra:** the healthy dependency direction is “editor host depends on reusable runtime/semantic modules,” not “editor rewrites runtime semantics” and not “editor must launch the game to call every runtime function.” Editor-only adapters stay separate.

## Unity — Runtime and Editor assemblies with explicit dependencies

Primary sources:

- Unity 6 package assembly layout: <https://docs.unity3d.com/cn/6000.0/Manual/cus-asmdef.html>
- Current assembly-definition format: <https://docs.unity3d.com/ja/current/Manual/assembly-definition-file-format.html>

Unity's package conventions explicitly separate `Runtime/...asmdef` and `Editor/...Editor.asmdef` assemblies. Assembly definitions make dependencies explicit and allow compilation to rebuild only affected dependency units rather than recompiling one undifferentiated body of code.

**Lesson for Thestra:** reusable semantic code should live in a host-neutral dependency domain, while Studio/Electron/DOM behavior remains editor-only. Incremental rebuild boundaries matter to authoring responsiveness as much as runtime architecture does.

## Defold — cross-language generated contracts + incremental compiled asset cache

Primary sources:

- Defold engine overview / DDF: <https://defold.com/2020/12/27/engine-overview-pt1/>
- Asset caching: <https://defold.com/manuals/caching-assets/>
- Editor scripts: <https://defold.com/manuals/editor-scripts/>

Defold's engine overview describes DDF on top of Protobuf with generated bindings for **C++, Java and Python**, used by both tools and game runtime. This is strong precedent for one schema/contract producing bindings for multiple implementation hosts rather than manually mirroring shape rules.

Its asset cache is shared by editor/CLI project builds and recompiles only modified assets; external cache keys include engine version, source names/content and build options.

Defold editor scripts also demonstrate that editor/runtime can sometimes require the same Lua modules when the shared subset is compatible, despite running in different hosts.

**Lesson for Thestra:** generated cross-language contracts are appropriate for representation/schema domains; compiled artifacts should be keyed by all semantic inputs; a host boundary does not imply handwritten duplicate semantics.

## TypeScript language service — long-lived semantic context + versioned snapshots

Primary source:

- <https://github.com/microsoft/TypeScript/wiki/Using-the-Language-Service-API>

The TypeScript language service is explicitly designed as a **long-lived program/compilation context**, computes only the minimum information needed for a query, and consumes versioned `ScriptSnapshot`s that describe current text and change ranges for incremental parsing.

**Lesson for Thestra:** Studio's semantic host should think in Project revisions/snapshots, not “fresh process means fresh authority.” Ask only for the fact a UI surface needs, and retain reusable semantic context across queries.

## clangd — immediate foreground facts layered over slower derived state

Primary sources:

- Threads/request handling: <https://clangd.llvm.org/design/threads>
- Indexing: <https://clangd.llvm.org/design/indexing>
- Code walkthrough: <https://clangd.llvm.org/design/code>

clangd keeps one worker/context per open file, caches ASTs/preambles, discards obsolete work, and deliberately allows latency-sensitive completion to use the immediately available preamble instead of blocking for every background update. Its dynamic per-file index layers current edited-file facts over the slower background project index so active edits do not wait for full-project recompilation.

**Lesson for Thestra:** authoring feedback and compilation truth can have different clocks without becoming semantically dishonest. Revision identity, cancellation and “latest useful artifact” are architectural tools, not approximations.

## rust-analyzer — pure derived semantic database, IO at boundaries, incremental queries

Primary sources:

- Architecture: <https://rust-analyzer.github.io/book/contributing/architecture.html>
- Salsa/incremental guide: <https://rust-analyzer.github.io/book/contributing/guide.html>

rust-analyzer models source/project structure as input (“ground”) state and computes semantic state lazily/on demand. Its core semantic database performs no filesystem IO; clients submit deltas. The architecture explicitly isolates build-system/IO concerns from semantic inputs, and uses a separate process where genuinely unsafe/non-deterministic proc macros warrant isolation.

**Lesson for Thestra:** separate **semantic computation** from filesystem/runtime adapters. Process isolation should be justified by unsafe/stateful/environmental behavior, not simply by implementation language. Small authored deltas should invalidate only dependent derived state.

---

# 11. Proposed successor architectural invariant

The following is a proposal for later policy migration, **not a change made by this audit**:

> ## One semantic authority, not necessarily one execution host
>
> Every gameplay/authoring fact has one authoritative semantic definition or mechanically generated contract. Do not maintain parallel handwritten implementations that can disagree about the same fact.
>
> **Pure deterministic semantics** needed by multiple hosts must be shared as executable semantics or generated from one authoritative source, and may execute locally in runtime, Studio, CI, or future hosts.
>
> **Deterministic derived resources** belong to the compilation clock. Produce them when their semantic inputs/revision change, give them explicit version/content identity, and let multiple hosts consume the authoritative artifact directly instead of re-deriving or expanding it unnecessarily.
>
> **Lua/LÖVE-dependent semantic or preview facilities** may remain behind a process boundary, but authoring-path services should be persistent/incremental and revision-scoped rather than repeatedly staging and cold-booting the runtime.
>
> **Actual runtime truth** — mutable simulation, final rendering, Test Play, validation, goldens, package smoke and other product execution — remains owned by the real runtime.
>
> Presentation adapters may translate authoritative facts into host-specific coordinates, UI, GPU buffers and widgets. They must not silently invent alternate game semantics.
>
> If an immediate authoring interaction would require a heavyweight runtime call, first ask whether the requested fact belongs to shared semantics or a compiled artifact. Do not call a cold runtime merely because the current implementation happens to be Lua.

This preserves the spirit of the existing rule while making process boundaries answerable rather than axiomatic.

---

# 12. Follow-up ownership / issue grouping

The audit intentionally recommends **few** issues.

## Existing issue to reuse — #754: persistent runtime surfaces

Owns:

- productionizing the persistent/revision-scoped runtime child where warranted;
- stage/snapshot reuse;
- lifecycle/invalidation/health;
- runtime request timings.

Do not open another “live runtime” issue.

## Existing issue/PR to reuse — #765 / #766: authoritative artifact consumption

Owns:

- direct definition/placement consumption in Three;
- removal of compatibility expansion;
- placement-owned color/provenance without cloning definition geometry;
- browser heap/scene-creation/picking evidence.

Do not fold this into #754.

## Existing issue to reuse — #467: lighting ontology and frame-local authoring

Owns lighting-source/bake/paint/fidelity semantics and already requires that lighting drag/paint feedback not wait for LÖVE. A shared-executable mechanism should integrate with that contract rather than invent a second lighting architecture issue.

## New bounded issue recommended — shared deterministic semantics experiment

Scope:

- evaluate one mechanism on vertex shading first;
- add sprite timing second if the first proof is healthy;
- compare generated/shared mechanisms without creating a generic framework;
- produce falsifiable deployment/debug/performance evidence;
- leave map generation, simulation and renderer ownership out.

## New bounded issue recommended — architecture-rule migration

Scope:

- only after #754/#765 and the shared-semantics experiment establish examples;
- update `AGENTS.md`/SPEC language;
- document destination taxonomy and three clocks;
- remove obsolete “must call real engine for every preview semantic” wording without weakening runtime truth gates.

A separate “artifact architecture” issue is not currently necessary: #765 owns the most urgent consumer artifact work, while revision identity can be either a bounded #754 follow-up or created later if implementation reveals it deserves independent ownership.

---

# 13. Top five next actions

1. **Finish #765/#766 from the passing placement-color evidence and delete the compatibility expansion cost.** This isolates browser representation from host-process cost.
2. **Productize #754's persistent-child design for map renderable/inspection with revision-scoped staging and explicit invalidation.** Do not embed Test Play as the solution.
3. **Run the shared deterministic semantic experiment on `engine/vertex_shading.lua` ↔ `tools/editor/js/vertex-shading.js`, then sprite timing.** Choose mechanism from evidence, not language preference.
4. **Define one revision/artifact identity vocabulary before adding more caches.** Include Project source, runtime semantics, RTP/default/package inputs, assets and producer/compiler version.
5. **Only then migrate the repository invariant** to “one semantic authority, not necessarily one execution host,” preserving real-runtime validation/Test Play/golden boundaries.

---

# 14. Surprising findings that materially change the architecture

## Surprise 1 — the literal invariant is already not how Studio works

The smallBattler itself animates locally. Lighting bakes locally. Vertex shading runs locally. The icon picker renders locally. Authored storage has three host implementations. Several files say so explicitly.

The repository has already discovered the successor architecture piecemeal; it has not named it yet.

## Surprise 2 — #754 is not primarily about OS process creation

The measured process-spawn primitive is trivial relative to **snapshot/stage + LÖVE bootstrap + authority initialization**. The architectural unit to cache is the **runtime semantic context for a Project revision**, not merely a child PID.

## Surprise 3 — #761/#765 show that “one authority” and “one representation” are different questions

The runtime can be perfectly authoritative and Studio can still waste 100+ MiB rebuilding an obsolete consumer shape. A future architecture audit must always ask independently:

1. who decides the semantic fact?;
2. when is it derived?;
3. what representation crosses the boundary?;
4. what representation does each consumer actually need?

## Surprise 4 — authored storage may be the largest semantic-drift surface

The visually obvious mirrors are lighting/sprite math, but Lua + JS + Python authored-storage behavior has broader consequences for Project identity, path safety and ordering. Shared-core work should not stop at graphics math.

## Surprise 5 — the repository already has a good model for pure semantics

`engine/semantic_calculation.lua` is deliberately side-effect-free and separated from source discovery and commit authority. That decomposition is exactly what makes semantics portable: **extract the calculation, not the entire gameplay owner.**

---

# 15. Verification / audit limitations

This report is a documentation-only change and does not alter production code.

The audit was anchored to current remote `main@726eabcd205cb405f2be780246068938698a9284` through the connected GitHub repository API. The local shell in this session could not reach GitHub over the network, so a full local checkout/test execution was not available from that shell. Repository policy explicitly treats tool availability as session state; the connected GitHub path was used instead of reporting the repository blocked.

Appropriate repository verification for this report is therefore:

- review the branch diff and confirm it contains only this report;
- let the repository's normal PR documentation/repository-hygiene checks run on the published audit branch/PR;
- do **not** claim G1–G6 or runtime tests as newly executed evidence for a Markdown-only architecture report when the environment could not execute them locally.

No G5/G6 reference images are changed or recaptured.
