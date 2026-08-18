# Studio live runtime authority — post-#766 process experiment

Date: 2026-08-18  
Issue: #754  
Draft PR: #756  
Baseline: `main` `ae8c6bad` (merged #766)

## Recommendation

**PERSIST + SNAPSHOT/STAGE REUSE**, narrowly for Studio's production compact Map renderable request.

Do **not** embed a LÖVE window. Do **not** turn this into a general runtime daemon. Do **not** move pure deterministic semantics into this process; #772 owns those.

The proven seam is one lazy, serial, Project/revision-scoped LÖVE authority generation for `/api/map-renderable` **only when Studio requests `mesh-definitions-v1`**. The submitted unsaved Map remains a per-request overlay. Expanded-control renderables and Map Inspection remain cold reference paths.

This decision is materially different from the original #754 framing. #761 reduced Map transport to about 1 MiB, and #766 removed compatibility-expanded spatial reconstruction from the production browser path. The remaining process-boundary opportunity is staging/bootstrap reuse, not shipping giant geometry artifacts.

## Phase 1 — current Studio → LÖVE census

Classification:

- **A** pure deterministic semantics — #772, not #754;
- **B** deterministic derived artifact/compiler work;
- **C** actual LÖVE-dependent preview/rendering service;
- **D** actual game/runtime truth.

| Studio seam | Class | State submitted | Current host shape | Invalidation / frequency | #754 disposition |
|---|---|---|---|---|---|
| `/api/map-renderable` → `preview-map` | **B** (authoritative deterministic compiled presentation artifact, currently executed inside LÖVE) | transient unsaved Map + seed | full Project stage/snapshot + one LÖVE boot per cold request on `main` | transient Map changes are frequent; non-transient Project/runtime/RTP/package inputs invalidate the generation | **persistent compact generation candidate** |
| `/api/map-inspection` → `preview-map-inspection` | **D** | transient unsaved Map | cold stage/snapshot + LÖVE | changes with transient Map and runtime resolution rules | **keep cold in this PR**; correctness/control seam, no evidence yet for persistence |
| `/preview-anim` | **C** | transient animation data + sprite path | cold `execOpenedProject()` | potentially frequent in Animation authoring | measure independently before any migration; not widened into this PR |
| `/preview-font` | **C** | transient font name/size | cold `execOpenedProject()` | interactive but small surface | keep cold pending direct evidence |
| `/preview-fog` | **C** | transient fog spec + Map id | cold `execOpenedProject()` | interactive environment preview | keep cold pending direct evidence |
| `/preview-window` | **C** | saved window registry + transient mock | cold `execOpenedProject()` | authoring-time | keep cold pending direct evidence |
| `/preview-scene` | **C/D** | last-saved scene data | cold `execOpenedProject()` | authoring-time, saved-state semantics | keep cold pending direct evidence |
| `/api/sprite-resolution` → `sprite-meta` | **A** | sprite key/path | cold on cache miss; Project-scoped cache since #723 | asset inventory/runtime resolver changes | **#772 / existing #723 cache**, not persistent LÖVE |
| `/validate` | **D** | last-saved Project | cold validator | explicit correctness gate | **KEEP COLD** |
| `/screenshots` | **C/D** | last-saved Project | cold capture suite | episodic verification | **KEEP COLD** |
| `/play` / Test Play | **D** | staged/snapshotted Project | launches the actual game process | explicit user action | already a live runtime; outside #754 |

The census also separates two costs that should not be collapsed into “runtime latency”:

1. **Project materialization / LÖVE authority work** — this issue;
2. **Studio-native browser consumption** — #766/#751 territory after the authoritative payload arrives.

## Current post-#761 cold decomposition

The stable post-#761 Map 2 controls already established the residual cold request shape:

| case | request → decoded | stage/snapshot | process + runtime bootstrap | `loadMap` | authoritative work | serialize | stdout transfer | JSON parse |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| identical revision | 2063.1 ms | 1136.7 | 517.4 | 9.3 | 270.0 | 26.8 | 7.3 | 3.4 |
| changed revision | 2331.4 ms | 1433.1 | 527.9 | 9.5 | 257.1 | 23.8 | 6.7 | 3.1 |
| fresh restart | 2301.0 ms | 1365.5 | 532.7 | 7.9 | 283.8 | 25.7 | 6.7 | 3.4 |

The first request was 3204.1 ms (1630.4 ms materialization + 745.5 ms bootstrap + 664.2 ms authoritative work).

`loadMap()` itself is single-digit milliseconds. OS process creation was only a few milliseconds; the ~0.52 s bucket is overwhelmingly LÖVE/runtime bootstrap. The dominant reusable work is therefore **stage/snapshot + initialized runtime/compiler state**, not Map lookup and not JSON transport.

## What #766 changed

Current production Studio no longer compatibility-expands `mesh-definitions-v1` into duplicated triangle streams before Three.

Hosted #766 evidence:

| Map | compact payload | direct placement-colour preparation | consumer-ready JS heap delta | Three scene creation | total measured JS heap delta |
|---|---:|---:|---:|---:|---:|
| 2 | 0.863 MiB | 387.276 ms | 0.376 MiB | 28.885 ms | 0.844 MiB |
| 3 | 1.028 MiB | 430.413 ms | 0.541 MiB | 44.442 ms | 1.222 MiB |

The ~387–430 ms preparation is **placement-dependent authoring colour modulation**, not the deleted geometry compatibility expansion. #754 does not move or duplicate that semantic work. The old 46–120 MiB compatibility reconstruction is not part of the current production hot path and is not counted as a benefit of persistence.

## Phase 2 — bounded persistent prototype evidence

The stale pre-#766 exploration proved the important process hypothesis before production shaping:

| case | stage | bootstrap | authoritative work | persistent request → decoded |
|---|---:|---:|---:|---:|
| first/new generation | 1719 ms | 716 ms | 653 ms | 815 ms* |
| identical revision/reused | 0 | 0 | 146 ms | **215 ms** |
| changed transient Map/reused | 0 | 0 | 161 ms | **223 ms** |
| fresh restart/new generation | 1268 ms | 511 ms | 262 ms | 344 ms* |

`*` stage/bootstrap happen before the request timer; full cold generation cost includes them.

A later production-shaped worker measured warm compile + old compatibility decode at 257–264 ms and rebuilt at ~2.55 s, while preserving one PID across an unsaved transient Map change and creating a new PID after non-transient invalidation.

Those figures are stale **only for browser consumption**. They remain useful causality evidence that initialized LÖVE/compiler state and the staged Project generation are reusable. The current branch re-runs the benchmark after #766 and keeps the compact representation compact through the direct consumer.

## Current prototype / production seam

`tools/editor/runtime-renderable-worker.js` owns one lazy serial generation:

1. fingerprint the exact inputs materialized into a staged player generation;
2. stage the opened Project once with the ordinary Test Play/export boundary;
3. replace only the disposable stage's `main.lua` with a tiny stdin framing host;
4. initialize the ordinary loader once in LÖVE;
5. send one request at a time as `mapId<TAB>transientRequestPath`;
6. delegate semantics to `presentation.editor_renderable_bridge.run()`;
7. return the ordinary `mesh-definitions-v1` payload;
8. re-fingerprint authority after runtime completion before accepting the response;
9. reuse the generation only while its authority revision remains identical.

The HTTP bridge routes only requests that explicitly ask for `renderableEncoding: "instances"` to this worker. Expanded-control renderables still execute through `compileRenderable()`'s one-shot cold path. Map Inspection stays cold.

## Revision / lifecycle contract

### Project identity

The generation is process-scoped to the Project selected before `project-root.js` is loaded. Project switching relaunches Studio, so one generation cannot cross Project identity.

### Authority identity

The generation revision covers the same semantic inputs that ordinary Project staging materializes:

- runtime export manifest;
- manifest root files/runtime directories/release config;
- opened Project `data/`;
- opened Project `assets/`;
- opened Project `project.json`;
- resolved RTP fallback tree.

The submitted transient Map snapshot is intentionally excluded because it is the expected warm per-request overlay.

The current fingerprint hashes sorted path/type/size/mtime metadata rather than rereading every art/audio byte on every request. Normal Studio and external filesystem writes therefore invalidate without depending on watcher delivery. Runtime/source/RTP/package edits also enter the fingerprint. Project switching is a process restart.

### Stale-response suppression

Freshness is proved twice:

- before selecting/reusing a generation;
- again after LÖVE finishes the request.

If authority changed during execution, the generation is marked stale and that response is rejected with `runtime authority changed during renderable request; retry`.

This post-request proof is important because Studio's existing Project watcher covers Project `data/` and `assets/`, but not every runtime/RTP stage input. Watcher delivery can later become an eager invalidation optimization; correctness does not require it.

### Concurrent/latest-request behavior

The first production seam is deliberately **serial**. Multiple callers queue onto one generation. No request-ID multiplexing, parallel runtime mutation, or out-of-order response ownership exists.

Studio's existing workspace serial/debounce logic remains responsible for discarding superseded UI requests. The worker itself never returns request B before request A.

### Crash / timeout / error isolation

- child crash rejects the active request and marks the generation unusable;
- request timeout marks the generation stale;
- oversized stdout fails loudly;
- next request rebuilds a fresh generation;
- runtime semantic errors remain request failures rather than Studio-side fallbacks.

### Shutdown

The worker sends `QUIT`, waits for confirmed child exit, then deletes the disposable stage. If graceful exit fails it uses a bounded kill (`taskkill /T /F` on Windows). If process death cannot be confirmed, the stage is retained rather than racing deletion.

This ordering is required: the experiment reproduced Windows `EPERM` when stage cleanup raced a still-live LÖVE child.

Electron already closes the runtime bridge from `will-quit`, so no new application lifecycle protocol is required.

## Falsifiers

| falsifier | result |
|---|---|
| savings small after #761/#766 | **not fired in prior process proof**; current post-#766 hosted remeasurement required before merge |
| staging cache alone captures most of win | **not fired**: warm runtime/compiler authority also fell to ~146–161 ms versus ~257–284 ms cold authoritative work, while staging reuse removes another ~1.1–1.4 s |
| most endpoints belong to pure shared semantics | **true for some endpoints, not this seam**: sprite timing is explicitly excluded to #772 |
| Project switching/Test Play becomes complex | **not fired**: Project switch already relaunches Studio; Test Play remains separate |
| stale semantic truth risk | **guarded** by pre/post authority fingerprint + serial ownership; response is rejected if authority changes during execution |
| crash recovery unreliable | **not fired in lifecycle tests**: crash/timeout invalidates generation; child-before-stage shutdown is explicit |
| embedding needed for IPC benefit | **not fired**: the measurable benefit is stage/bootstrap/runtime-state reuse with ordinary IPC |

## Explicit recommendation matrix

- **KEEP COLD:** validation, screenshots, Map Inspection in this PR, expanded renderable control, low-frequency preview endpoints until individually measured.
- **CACHE STAGING only:** rejected as the final answer for Map renderables; useful but leaves ~0.5 s bootstrap and loses the measured warm runtime/compiler benefit.
- **PERSIST PROCESS only:** rejected; persistence without revision-scoped materialization reuse leaves the dominant staging tax.
- **PERSIST + SNAPSHOT/STAGE:** **recommended and implemented narrowly for compact Map renderables**.
- **EMBEDDING WORTH SEPARATE STUDY:** **no current evidence**. Study only if a future product/UI capability genuinely requires a live LÖVE surface rather than IPC.

## Verification status

The branch adds permanent runtime-data-boundary coverage for:

- transient Map changes reusing one generation/PID;
- explicit invalidation rebuilding the generation;
- fingerprint-driven rebuild without watcher delivery;
- serial callers;
- child exit before stage deletion;
- real LÖVE `mesh-definitions-v1` output and PID reuse;
- clean shutdown;
- existing cold bridge behavior.

The hosted Windows lane additionally runs `bench-runtime-production-worker.js` against current post-#766 code. It measures cold one-shot, first persistent generation, identical reuse, changed transient reuse, forced rebuild, and direct compact-consumer preparation. Final numeric results are copied into this report once the exact candidate head completes.

## Non-goals

No embedding, general daemon, parallel RPC, binary/Int16 transport, LOD, runtime instancing, G5/G6 recapture, compatibility-expanded triangle bundle, pure shared-semantics migration, or native Studio latency attribution is part of this work.

Agent-Signature: GPT-5.6 Sol
