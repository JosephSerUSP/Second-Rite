# Studio live renderable authority — post-#761 process experiment

Date: 2026-08-18  
Issue: #754  
PR: #756

## Decision

Ordinary `/api/map-renderable` requests should use **one lazy, serial, revision-scoped LÖVE authority generation** rather than staging a Project and booting LÖVE for every request.

This is deliberately **not** a general daemon or RPC service. Runtime semantics remain in the ordinary loader, CLI tools, `presentation.editor_renderable_bridge`, and the compact `mesh-definitions-v1` transport landed by #761. Studio still submits a transient authored Map snapshot and consumes runtime-authored output.

Map Inspection remains on the existing cold reference path in this change.

## Why persistence is justified

After #761, transport size ceased to be the dominant problem. Stable cold-per-request controls were approximately:

- total: **2.06–2.33 s** after the first request;
- Project stage/snapshot: **1.14–1.43 s**;
- LÖVE process/runtime bootstrap: **0.52–0.53 s**;
- `loadMap`: **8–9 ms**;
- authoritative geometry work: **257–284 ms**;
- serialization: **24–27 ms**;
- stdout transfer: **~7 ms**;
- JSON parse: **~3 ms**;
- compact response: **~0.86 MiB**.

The problem was repeatedly reconstructing the same Project/runtime generation around each transient Map request, not Map loading or JSON transport.

## Bounded falsifier

A benchmark-only staged entry point initialized the real loader once and delegated repeated requests to `presentation.editor_renderable_bridge.run()`.

Map 2, Windows, LÖVE 11.5 + Mesa:

| case | stage | bootstrap | authoritative work | request → Studio decode |
|---|---:|---:|---:|---:|
| first/new generation | 1719 ms | 716 ms | 653 ms | 815 ms* |
| identical revision/reused | 0 | 0 | 146 ms | **215 ms** |
| changed transient Map/reused | 0 | 0 | 161 ms | **223 ms** |
| fresh restart/new generation | 1268 ms | 511 ms | 262 ms | 344 ms* |

`*` Stage/bootstrap occur before that request timer; full cold generation cost includes them.

Persistence therefore saves more than OS process creation: runtime/compiler state itself becomes usefully warm.

## Hardened production measurement

The production implementation was then measured directly, including its stage-input authority fingerprint, serial lifecycle, compact response, explicit invalidation rebuild, and ordinary Studio compatibility decode.

| case | authority fingerprint | worker compile | through Studio decode | PID |
|---|---:|---:|---:|---:|
| first request | 51.4 ms | 3201 ms | 3270 ms | 3304 |
| identical revision second | 37.9 ms | **228 ms** | **257 ms** | 3304 |
| changed transient Map | 35.1 ms | **234 ms** | **264 ms** | 3304 |
| forced non-transient invalidation | 34.3 ms | 2520 ms | 2552 ms | 7788 |

Compact response: **0.802 MiB**.

The same PID survives a changed unsaved Map snapshot; non-transient invalidation creates a new PID. The safety fingerprint costs only tens of milliseconds, so repeated production requests remain roughly **8–10× faster** than the old cold-per-request path.

Compatibility expansion still allocates about 46–50 MiB here. That is intentionally not hidden inside #754: #765 owns direct Three definition consumption.

## Production architecture

`tools/editor/runtime-renderable-worker.js` owns one lazy generation:

1. Compute a lightweight revision over the inputs that form the staged runtime generation.
2. If no compatible generation exists, compile/stage the opened Project once.
3. Replace only the disposable stage's `main.lua` with `runtime-renderable-worker-main.lua`.
4. Start one `lovec` process with `SECOND_RITE_RENDERABLE_ENCODING=instances`.
5. Send one serial request as `mapId<TAB>transientRequestPath`.
6. Delegate to `presentation.editor_renderable_bridge.run()` for authoritative output.
7. Reuse the generation for subsequent transient Map snapshots while the authority revision remains valid.

There are no request IDs and no multi-request concurrency in this implementation. Serial ownership is intentional for the first production version.

### Authority revision

The revision covers actual stage inputs:

- the public runtime export manifest;
- manifest runtime files/directories and release config;
- opened Project `data/`, `assets/`, and `project.json`;
- RTP fallback tree.

The submitted transient Map snapshot is deliberately excluded because changing it is the normal warm request case.

Path/type/size/mtime metadata is hashed instead of rereading every large asset on every request. This makes correctness independent of watcher delivery while keeping the measured fingerprint to ~35–51 ms on the hosted runner.

### Failure and lifecycle contract

- Requests are serial and bounded.
- Excess output fails loudly.
- Worker crash or timeout marks the generation stale; the next request rebuilds.
- If authority changes during a request, the response is rejected rather than accepted as fresh.
- HTTP bridge shutdown terminates the LÖVE child first, confirms process death, and only then removes the disposable stage.
- Windows `taskkill /T /F` is a bounded fallback. If the child cannot be confirmed dead, the stage is retained instead of racing file deletion.

The child-before-stage rule is required by the benchmark, which exposed an `EPERM` cleanup race when stage deletion raced process exit.

## Verification

The permanent runtime-data boundary exercises both lifecycle contracts and real LÖVE 11.5 authority:

- reuse across changed transient Map snapshots;
- explicit invalidation rebuild;
- fingerprint-driven rebuild even without watcher delivery;
- serialization of concurrent callers;
- child closure before stage deletion;
- real persistent LÖVE worker returns `mesh-definitions-v1`;
- changed transient Map reuses the same real child PID;
- clean shutdown;
- the existing cold real-LÖVE bridge remains green.

Latest measured boundary: **39/39 passing**.

## Explicit non-goals

This change does **not** add:

- a general LÖVE RPC daemon;
- multiple concurrent runtime workers;
- persistent Map Inspection;
- Int16/binary packing;
- Studio-side runtime semantics;
- runtime LOD;
- runtime instancing.

The worker exists only because the post-#761 measurements demonstrated a large, bounded, semantically safe warm-authority win.