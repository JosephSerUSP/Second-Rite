# Studio live LÖVE runtime process exploration — 2026-08-18

Issue: #754  
Measured baseline: `main` after #761, rebased through `63d0963682fe242fe0604d3f94bb498e57b67d97`.

This report does **not** implement a persistent runtime host. It measures the residual cold-per-request path after #761 made renderable transport small enough that process/snapshot costs can be seen clearly.

## Decision

A bounded persistent-child prototype is now justified, but the useful experiment is **revision-aware runtime + snapshot reuse**, not merely keeping a process alive.

On the three post-first-request controls, the existing cold path takes about **2.06–2.33 s** from request start through compatibility expansion. The two dominant reusable costs are:

- Project snapshot/staging: **1.14–1.43 s**;
- LÖVE process + runtime bootstrap to the renderable bridge: **0.52–0.53 s**.

By contrast, `exploration.loadMap()` itself is only **7.9–9.5 ms**. The old intuition that Map loading was the expensive part is false for this path.

Therefore:

- a persistent child that saves only process/bootstrap time has a real but bounded ~0.52 s opportunity;
- a revision-aware host that can keep the already-materialized Project runtime/snapshot valid across an identical revision has a much larger ~1.66–1.97 s warmable opportunity before authoritative work;
- changed revisions must invalidate/re-materialize exactly as today;
- no evidence here supports embedding LÖVE, a daemon/service, or duplicating runtime semantics in Studio.

## Why #761 changed the question

#761 replaced repeated world-space triangle soup at the Studio bridge with exact runtime-authored mesh definitions + placements. For Map 2 it reduced the measured response from **57.70 MiB to 0.86 MiB** losslessly; the larger Map 3 case dropped from **77.25 MiB to 1.03 MiB**.

That removed response size as the dominant ambiguity. On the hosted #754 run Map 2 is **0.863 MiB**. JSON response serialization is ~24–27 ms after the first request, stdout transfer ~6.7–7.3 ms, and JSON parse ~3.1–3.4 ms. Those are no longer remotely large enough to explain multi-second Studio requests.

The compatibility decoder remains a separate problem: it recreates approximately **48.7–49.1 MiB** of JS heap on the stable controls. That is the motivation for the direct-Three definition-consumption experiment, not for a persistent LÖVE process.

## Measurement model

The benchmark records:

`Trequest = Tsnapshot + TrequestWrite + Tspawn/bootstrap + Tload + Twork + TinstanceEncode + Tserialize + Ttransfer + Tdecode + host overhead`

Definitions:

- **snapshot/staging**: the current `projectPlay` external-Project materialization performed before the child launches;
- **spawn process**: Node `spawn()` call to the OS child `spawn` event;
- **runtime bootstrap**: OS child `spawn` event to the first opt-in `RENDERABLE BRIDGE READY` marker;
- **spawn**: process + runtime bootstrap together, i.e. the portion a persistent child can actually amortize;
- **load**: `exploration.loadMap()` only;
- **authoritative work**: `viewport_3d.init()` + `map_renderable_bundle.collect()`;
- **instance encode**: #761 exact definition/placement encoding;
- **serialization**: Lua JSON encoding of the compact payload;
- **transfer**: observed stdout time from renderable begin marker to end marker;
- **JSON parse**: compact JSON parse in Node;
- **compatibility expansion**: current #761 Studio-boundary reconstruction into ordinary surface arrays;
- **decode**: JSON parse + compatibility expansion.

The timing marker is opt-in (`SECOND_RITE_RENDERABLE_TIMINGS=1`) and does not alter ordinary renderable response JSON.

## Hosted Windows result — Map 2, LÖVE 11.5 + Mesa

| Case | Total to decoded | Snapshot/stage | Spawn + bootstrap | `loadMap` | Authoritative work | JSON serialize | Transfer | JSON parse | Compatibility expansion | Expansion heap delta |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| first request | 3204.1 ms | 1630.4 | 745.5 | 8.2 | 664.2 | 22.0 | 8.4 | 3.1 | 58.0 | 52.82 MiB |
| identical-revision second | 2063.1 ms | 1136.7 | 517.4 | 9.3 | 270.0 | 26.8 | 7.3 | 3.4 | 36.6 | 49.11 MiB |
| changed revision | 2331.4 ms | 1433.1 | 527.9 | 9.5 | 257.1 | 23.8 | 6.7 | 3.1 | 11.3 | 48.70 MiB |
| fresh-restart control | 2301.0 ms | 1365.5 | 532.7 | 7.9 | 283.8 | 25.7 | 6.7 | 3.4 | 10.9 | 48.70 MiB |

Additional facts:

- response: **0.863 MiB** in every case;
- OS process creation itself is only ~2.7–2.9 ms after the first request; most of `Tspawn` is runtime/bootstrap (~515–530 ms);
- #761 instance encoding is sub-millisecond to ~1 ms on the stable controls;
- first-request authoritative work is much colder (664 ms) than subsequent controls (257–284 ms), so first-request numbers should not be used as the warm expectation;
- identical and changed revisions currently receive no semantic reuse at all: every case is a fresh process and a fresh Project stage. Their differences are cache/noise, not a hidden revision cache.

## What a persistent prototype must test

The next prototype should remain Studio-owned and stdio/framed-control based. It needs exactly enough lifecycle to answer the measured question:

1. launch one LÖVE child lazily;
2. associate its loaded Project snapshot/stage with an explicit content revision;
3. on an identical revision, reuse both process and valid loaded snapshot/state;
4. on a changed revision, invalidate and load the new materialized snapshot before answering;
5. after killing/restarting the process, rehydrate from the requested revision and reproduce the cold control;
6. retain the existing cold subprocess as an experimental control/fallback.

Measure the same four cases again. The headline comparison is **identical-revision second request**, not first launch.

### Falsifier

Do not productize persistence if the identical-revision request does not remove a substantial fraction of the measured ~1.66 s of snapshot + spawn + load cost on the fastest stable control, or if revision/lifecycle complexity requires semantic duplication or fragile stale-state behavior.

## Important separation from the direct-Three experiment

#754 and the #761 follow-up optimize different copies of the same path:

- persistent runtime/snapshot reuse attacks roughly **1.1–1.4 s staging + 0.52 s bootstrap**;
- direct mesh-definition consumption in Three attacks roughly **49 MiB of compatibility reconstruction** plus its 11–37 ms stable-control CPU cost.

Neither should be used to excuse the other. The direct-Three experiment should proceed even if persistence is later rejected, because its principal win is memory/representation deletion rather than FPS.

## Architectural boundary

LÖVE remains geometry/semantic/rendering authority. A warm child may remember a runtime state only when the host can prove the authored snapshot revision still matches. Studio must not learn height-map compilation, tileset resolution, scene semantics, fallback rules, lighting semantics, or other runtime knowledge merely to avoid a reload.

The evidence now supports **one bounded persistent-child + revision-reuse experiment**. It still does not support an embedded runtime, a long-lived independently discoverable localhost daemon, or general RPC infrastructure.
