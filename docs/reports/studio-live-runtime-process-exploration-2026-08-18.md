# Studio live runtime authority — post-#766 process experiment

Date: 2026-08-18  
Issue: #754  
Draft PR: #756  
Baseline: `main` `ae8c6bad` (merged #766)

## Decision

**PERSIST + SNAPSHOT/STAGE REUSE**, narrowly for Studio's production compact Map renderable request.

Do **not** embed a LÖVE window. Do **not** turn this into a general runtime daemon. Do **not** route pure deterministic semantics through this host; #772 owns that class.

The proven seam is one lazy, serial, Project/revision-scoped LÖVE authority generation for `/api/map-renderable` only when Studio requests `mesh-definitions-v1`. The unsaved Map remains a per-request overlay. Expanded-control renderables and Map Inspection remain cold reference paths.

This is a post-#766 conclusion, not a replay of the original #754 premise. #761 reduced representative Map transport to about 1 MiB. #766 removed compatibility-expanded spatial reconstruction from the production Three path. The remaining process-boundary cost is repeated Project materialization plus LÖVE/runtime bootstrap and cold compiler state.

## Phase 1 — current Studio → LÖVE census

Classification:

- **A** pure deterministic semantics — #772, not #754;
- **B** deterministic derived artifact/compiler work;
- **C** actual LÖVE-dependent preview/rendering service;
- **D** actual game/runtime truth.

| Studio seam | Class | Authored state | Current execution shape | Invalidation / frequency | #754 disposition |
|---|---|---|---|---|---|
| `/api/map-renderable` → `preview-map` | **B** | transient unsaved Map + seed | cold Project materialization + LÖVE boot on `main` | transient Map changes frequently; Project/runtime/RTP/package changes invalidate generation | **persist compact generation** |
| `/api/map-inspection` → `preview-map-inspection` | **D** | transient unsaved Map | cold stage/snapshot + LÖVE | Map + runtime resolution rules | **KEEP COLD in this PR** |
| `/preview-anim` | **C** | transient animation + sprite path | cold `execOpenedProject()` | potentially frequent | measure independently before migration |
| `/preview-font` | **C** | transient font name/size | cold `execOpenedProject()` | interactive | keep cold pending evidence |
| `/preview-fog` | **C** | transient fog + Map id | cold `execOpenedProject()` | interactive | keep cold pending evidence |
| `/preview-window` | **C** | saved window registry + transient mock | cold `execOpenedProject()` | authoring-time | keep cold pending evidence |
| `/preview-scene` | **C/D** | last-saved scene data | cold `execOpenedProject()` | authoring-time | keep cold pending evidence |
| `/api/sprite-resolution` → `sprite-meta` | **A** | sprite key/path | cold on cache miss; Project cache since #723 | resolver/asset changes | **#772 / #723**, not persistent LÖVE |
| `/validate` | **D** | last-saved Project | cold validator | explicit correctness gate | **KEEP COLD** |
| `/screenshots` | **C/D** | last-saved Project | cold capture suite | episodic verification | **KEEP COLD** |
| `/play` / Test Play | **D** | staged/snapshotted Project | actual game process | explicit user action | already live; outside #754 |

The census separates two costs that should not be collapsed into one “runtime latency” number:

1. **Project materialization / LÖVE authority execution** — #754;
2. **Studio-native browser consumption** — #766/#751 after the payload arrives.

## Cold causality established after #761

Stable Map 2 controls before the persistent prototype established the residual cold shape:

| case | request → decoded | stage/snapshot | process + runtime bootstrap | `loadMap` | authoritative work | serialize | stdout | JSON parse |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| identical revision | 2063.1 ms | 1136.7 | 517.4 | 9.3 | 270.0 | 26.8 | 7.3 | 3.4 |
| changed revision | 2331.4 ms | 1433.1 | 527.9 | 9.5 | 257.1 | 23.8 | 6.7 | 3.1 |
| fresh restart | 2301.0 ms | 1365.5 | 532.7 | 7.9 | 283.8 | 25.7 | 6.7 | 3.4 |

The first request was 3204.1 ms: 1630.4 ms materialization, 745.5 ms bootstrap, and 664.2 ms authoritative work.

`loadMap()` is single-digit milliseconds. OS process creation itself measured only a few milliseconds; the ~0.52 s bucket is LÖVE/runtime initialization. The dominant reusable work is therefore **the staged Project generation plus initialized runtime/compiler state**, not Map lookup or JSON transport.

## What #766 changed

Production Studio now consumes runtime-authored definitions directly. Hosted #766 evidence:

| Map | compact payload | direct colour preparation | consumer-ready JS heap delta | Three scene creation | total measured JS heap delta |
|---|---:|---:|---:|---:|---:|
| 2 | 0.863 MiB | 387.276 ms | 0.376 MiB | 28.885 ms | 0.844 MiB |
| 3 | 1.028 MiB | 430.413 ms | 0.541 MiB | 44.442 ms | 1.222 MiB |

The ~387–430 ms preparation is placement-dependent authoring colour modulation, **not** compatibility geometry expansion. #754 neither moves nor duplicates that work. The deleted tens-of-MiB compatibility reconstruction is not counted as a persistence benefit.

## Phase 2 — persistent-process falsifier

The pre-#766 prototype already showed that an initialized generation was materially reusable:

| case | stage | bootstrap | authoritative work | request → decoded |
|---|---:|---:|---:|---:|
| first/new generation | 1719 ms | 716 ms | 653 ms | 815 ms* |
| identical revision/reused | 0 | 0 | 146 ms | **215 ms** |
| changed transient Map/reused | 0 | 0 | 161 ms | **223 ms** |
| fresh restart/new generation | 1268 ms | 511 ms | 262 ms | 344 ms* |

`*` stage/bootstrap happened before the request timer.

That evidence remained useful for process causality, but its browser-consumption numbers were stale after #766. The current branch therefore remeasured the exact compact/direct path.

## Exact post-#766 candidate measurement

Hosted Windows Server 2025, Node 24, LÖVE 11.5 + Mesa, Map 2. Runtime candidate code head: `6193f1ac`.

All cases returned the same **0.802 MiB** compact representation with **16 definitions, 445 placements, and 194 literal surfaces**. No compatibility expansion was performed.

| control | runtime authority request | direct compact prep | request → direct-ready | worker PID |
|---|---:|---:|---:|---:|
| cold one-shot | **4279.833 ms** | 353.809 ms | **4639.619 ms** | — |
| persistent first generation | 1806.654 ms | 129.356 ms | 1944.031 ms | 916 |
| persistent identical reuse | **172.398 ms** | 125.203 ms | **304.488 ms** | 916 |
| persistent changed transient Map | **145.895 ms** | 132.001 ms | **291.888 ms** | 916 |
| forced non-transient rebuild | **2924.007 ms** | 130.009 ms | **3060.931 ms** | 4376 |

The same PID survived both an identical request and a changed unsaved Map snapshot. Explicit non-transient invalidation rebuilt the stage/runtime generation and produced a new PID.

The warm same-generation path is about **15–16× faster end-to-direct-ready** than the cold one-shot on the same runner. Runtime authority execution alone falls from 4.28 s to 146–172 ms. The forced rebuild returning to 3.06 s is the important negative control: **keeping the architecture but losing useful generation reuse loses almost all of the win**.

The current worker also performs a revision fingerprint before reuse and **again after LÖVE finishes**; both checks are included in the 146–172 ms warm runtime numbers.

The 125–132 ms direct-prep numbers above are not a replacement for #766's canonical 387–430 ms browser benchmark: this run has different warm/cache conditions and was designed to compare process-boundary controls. #766 remains the browser-side budgeting authority. The same-run cold/reuse comparison is what supports #754's process decision.

## Production seam

`tools/editor/runtime-renderable-worker.js` owns one lazy serial generation:

1. fingerprint the inputs materialized into a staged player generation;
2. stage the opened Project once through the ordinary Test Play/export boundary;
3. replace only the disposable stage's `main.lua` with a tiny stdin framing host;
4. initialize the ordinary loader once in LÖVE;
5. send one serial request as `mapId<TAB>transientRequestPath`;
6. delegate semantics to `presentation.editor_renderable_bridge.run()`;
7. return the ordinary `mesh-definitions-v1` payload;
8. re-fingerprint authority after runtime completion before accepting the response;
9. reuse the generation only while the authority revision is identical.

The HTTP bridge routes only `renderableEncoding: "instances"` through the persistent worker. Expanded-control renderables retain `compileRenderable()`'s one-shot cold reference path. Map Inspection stays cold.

## Revision / lifecycle contract

### Project identity

The generation belongs to the Project selected before `project-root.js` is loaded. Project switching already relaunches Studio, so one generation cannot cross Project identity.

### Authority identity

The revision covers the stage inputs:

- runtime export manifest;
- manifest root files/runtime directories/release config;
- opened Project `data/`;
- opened Project `assets/`;
- opened Project `project.json`;
- resolved RTP fallback tree.

The submitted transient Map snapshot is deliberately excluded because it is the expected warm request overlay.

The fingerprint hashes sorted path/type/size/mtime metadata, avoiding rereading large art/audio payloads twice per request. Normal Studio and filesystem writes change this identity; runtime/source/RTP/package edits are included. The existing watcher may later provide eager invalidation, but correctness is not dependent on watcher delivery.

### Stale-response suppression

Freshness is proved before generation selection and again after runtime completion. If non-transient authority changes while a request is executing, the response is rejected rather than accepted as current truth, the generation is marked stale, and the next request rebuilds.

A focused lifecycle test changes the authority revision inside an in-flight fake-runtime request and verifies that the stale response is suppressed and a subsequent request creates a fresh generation.

### Concurrency / latest-request behavior

The first production seam is deliberately **serial**. Concurrent callers queue onto one generation; there is no request-ID multiplexing, parallel mutation, or out-of-order runtime response ownership. Existing workspace debounce/serial logic remains responsible for superseded UI work.

### Crash / timeout / error isolation

- child crash rejects active work and invalidates the generation;
- timeout marks the generation stale;
- oversized stdout fails loudly;
- the next request rebuilds;
- runtime semantic errors remain explicit request failures rather than Studio-side approximations.

### Shutdown

The worker sends `QUIT`, waits for confirmed child exit, and only then removes the disposable stage. A bounded kill is the fallback (`taskkill /T /F` on Windows). If death cannot be confirmed, the stage is retained rather than racing cleanup.

This ordering is evidence-driven: the experiment reproduced Windows `EPERM` when stage deletion raced a still-live LÖVE process.

Electron already closes the runtime bridge from `will-quit`; no new app lifecycle protocol is needed.

## Falsifiers

| falsifier | result |
|---|---|
| savings are small after #761/#766 | **NOT FIRED** — 4.64 s cold direct-ready vs 0.29–0.30 s warm on the exact post-#766 path |
| simpler stage cache captures almost all benefit | **NOT FIRED** — initialized runtime/compiler work also becomes materially warm; forced rebuild is 3.06 s |
| candidate endpoints mostly belong to pure shared semantics | **PARTLY TRUE, bounded away** — sprite timing is excluded to #772; Map compiled presentation remains this seam |
| persistence complicates Project switching/Test Play | **NOT FIRED** — Project switch already relaunches Studio; Test Play is independent |
| stale semantic truth is fragile | **NOT FIRED** — pre/post revision proof plus in-flight stale-response test |
| crash recovery is unreliable | **NOT FIRED** — crash/timeout stale the generation; child-before-stage cleanup is tested |
| embedding is required to realize the benefit | **NOT FIRED** — ordinary IPC captures the measured benefit |

## Explicit recommendation matrix

- **KEEP COLD:** validation, screenshots, Map Inspection in this PR, expanded renderable control, and other preview endpoints until individually measured.
- **CACHE STAGING:** insufficient as the final Map answer; it leaves bootstrap/cold runtime state on every request.
- **PERSIST PROCESS:** insufficient without revision-scoped materialization reuse.
- **PERSIST + SNAPSHOT/STAGE:** **recommended and implemented narrowly for compact Map renderables**.
- **EMBEDDING WORTH SEPARATE STUDY:** **not currently justified**. Revisit only for a distinct UI/product capability that IPC cannot provide.

## Verification

Exact measurement run on code head `6193f1ac`:

- syntax: PASS;
- runtime-data boundary: **39/39 PASS**;
- real cold LÖVE bridge: PASS;
- real persistent LÖVE worker emits `mesh-definitions-v1` and reuses its PID: PASS;
- exact post-#766 benchmark: PASS;
- source checkout cleanliness: PASS.

The final branch additionally adds the explicit in-flight authority-change regression test. The permanent gate covers transient reuse, explicit invalidation, fingerprint-driven rebuild without watcher delivery, stale-response suppression during execution, serial callers, child-before-stage shutdown, real LÖVE compact output/PID reuse, and the existing cold bridge.

The one-off hosted timing step was removed after the measurement was captured; lifecycle coverage remains permanent.

## Non-goals

No embedding, general daemon, parallel RPC, binary/Int16 transport, LOD, runtime instancing, G5/G6 recapture, compatibility-expanded triangle bundle, pure shared-semantics migration, or native Studio latency attribution is part of this work.

Agent-Signature: GPT-5.6 Sol
