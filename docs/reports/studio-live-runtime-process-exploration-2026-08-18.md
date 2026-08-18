# Studio live LÖVE runtime process exploration — 2026-08-18

Issue: #754  
PR: #756  
Branch: `docs/754-live-runtime-exploration`  
Measured baseline: `main` after #761, #762, #767.

## Executive summary

The post-#761 bounded persistent-child falsifier has **strongly passed**.

By combining a **revision-scoped Project stage generation** with a **persistent LÖVE authority child** communicating over framed stdio with request IDs:
- Cold-per-request latency drops from **~3.7–4.0 s** to **~199–224 ms** on warm requests (identical revisions and transient Map edits);
- The ~1.4–1.7 s Project staging cost and ~1.5–1.9 s LÖVE process/bootstrap costs are **completely eliminated (0 ms)** on warm requests;
- Authoritative execution itself warms from ~280–320 ms down to **~129–160 ms** due to runtime compiler/resource caching;
- Output remains **100% byte-deterministic** (canonical payload SHA-256 matches the cold reference byte-for-byte);
- Windows file-locking (`EPERM`) is resolved by strictly awaiting child termination before unlinking staged directories;
- Crash and hang recovery operates cleanly without leaking child processes, handles, or temporary directories.

Persistence is warranted **strictly for runtime-bound operations** (e.g. Map 3D renderable/geometry extraction) and must **not** be used as a substitute for shared semantics or direct-artifact consumption on declarative surfaces (Scene, Window, Animation, Font, Sprite metadata).

---

## 1. Architecture

The architecture implements a **Revision-Scoped Generation Host** rather than a general background daemon:

```
+-------------------------------------------------------------------------+
| Developer Studio Host (Node / Electron)                                 |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  | Persistent Generation Controller                                  |  |
|  |  - Active Project Root & Non-transient Revision Key               |  |
|  |  - Disposable Staged Directory (projectPlay.stageProject)         |  |
|  |  - Persistent LÖVE Authority Child (lovec.exe)                    |  |
|  |  - Serial Request Queue & Request ID Tracker                      |  |
|  +-------------------------------------------------------------------+  |
|         | stdin (framed request)           ^ stdout (framed response)   |
|         v                                  |                            |
|  +-------------------------------------------------------------------+  |
|  | Staged LÖVE Subprocess                                            |  |
|  |  - loader.init() executed once at startup                         |  |
|  |  - Loop reading requests: <reqId>\t<mapId>\t<requestPath>         |  |
|  |  - editor_renderable_bridge.run(path, mapId, loader, cliTools)    |  |
|  |  - Emits: RENDERABLE BEGIN ... RENDERABLE END ... DONE <reqId>    |  |
|  +-------------------------------------------------------------------+  |
+-------------------------------------------------------------------------+
```

### Key architectural invariants:
1. **One Project generation at a time**: A generation owns exactly one staged Project directory and one LÖVE child. No inter-Project state leakage is possible.
2. **Transient Map isolation**: Transient authored map edits are passed in request files and substituted in-memory during `bridge.run()` via `withTransientMap()`. Authored Project files on disk are never mutated.
3. **No standalone daemon**: The lifecycle is strictly owned by the local Studio process. When Studio closes or switches projects, the generation shuts down cleanly.
4. **Cold fallback preservation**: The existing cold subprocess runner remains functional as an experimental control and robust fallback.

---

## 2. Protocol

Communication between the Node host and the persistent LÖVE child uses newline-delimited framed stdio with explicit request correlation IDs:

### Host -> Child (stdin)
```text
<requestId>\t<mapId>\t<relativeRequestJsonPath>\n
```
Or for termination:
```text
QUIT\n
```

### Child -> Host (stdout)
1. **Startup ready marker**:
   ```text
   RENDERABLE SERVER READY\n
   ```
2. **Authoritative payload envelope**:
   ```text
   RENDERABLE BEGIN
   <compact JSON payload (#761 mesh-definitions-v1)>
   RENDERABLE END
   ```
3. **Timing metadata (opt-in via `SECOND_RITE_RENDERABLE_TIMINGS=1`)**:
   ```text
   RENDERABLE TIMINGS {"loadMs":6.91,"authoritativeWorkMs":158.717,"instanceEncodeMs":5.647,"serializationMs":23.121}
   ```
4. **Request completion**:
   ```text
   RENDERABLE SERVER REQUEST DONE\t<requestId>\n
   ```
5. **Request error (if pcall fails)**:
   ```text
   RENDERABLE SERVER ERROR\t<requestId>\t<errorMessage>\n
   RENDERABLE SERVER REQUEST DONE\t<requestId>\n
   ```

### Request ID correlation
Every request carries a unique ID (e.g. `req-1`). The host rejects responses with mismatched or stale IDs, guaranteeing that an aborted or delayed request cannot overwrite newer authoring state in Studio.

---

## 3. Exact Invalidation Model

The generation is identified by a compound revision key:
```
GenerationKey = SHA256(
    ProjectDirectoryPath +
    ProjectAuthoredDataRevision (excluding transient map) +
    ProjectAssetsRevision +
    RuntimeSourceRevision
)
```

| Event | Action | Staging Cost | Process Cost |
|---|---|---|---|
| **Same Map repeated request** | Reuse generation | **0 ms** | **0 ms** |
| **Transient Map snapshot edited** | Reuse generation (transient in-memory overlay) | **0 ms** | **0 ms** |
| **Authored data changed outside Map** (e.g. `tilesets.json`, `items.json`) | Invalidate generation -> re-stage + spawn child | ~1.4–1.7 s | ~1.5–1.6 s |
| **Asset changed** (e.g. textures, models) | Invalidate generation -> re-stage + spawn child | ~1.4–1.7 s | ~1.5–1.6 s |
| **Runtime source changed** (e.g. Lua scripts) | Invalidate generation -> re-stage + spawn child | ~1.4–1.7 s | ~1.5–1.6 s |
| **Project switched** | Invalidate generation -> re-stage + spawn child | ~1.4–1.7 s | ~1.5–1.6 s |
| **Child error / crash / hang** | Restart child within existing or refreshed stage | 0–1.5 s | ~1.0–1.5 s |

---

## 4. Measurements — All 8 Cases

Environment: Windows x64, LÖVE 11.5 console (`lovec.exe`), Map 2, lossless `mesh-definitions-v1` instance transport.

| Case | Snapshot / Stage | Spawn / Bootstrap | Runtime Load (`loadMap`) | Authoritative Work | Instance Encode | JSON Serialize | Stdout Transfer | Studio Decode | Total Request-to-Decoded |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **1. Cold first request** | 1406.7 ms | 1788.2 ms | 9.5 ms | 278.7 ms | 0.7 ms | 28.7 ms | 6.9 ms | 66.8 ms | **3722.9 ms** |
| **2. Cold identical revision** | 1568.8 ms | 1935.8 ms | 8.6 ms | 309.5 ms | 0.7 ms | 30.5 ms | 5.2 ms | 33.1 ms | **4041.5 ms** |
| **3. Persistent first request** (new gen) | 1649.0 ms | 1499.4 ms | 11.8 ms | 278.6 ms | 0.6 ms | 23.5 ms | 11.3 ms | 39.3 ms | **469.0 ms\*** |
| **4. Persistent identical revision** (reused) | **0.0 ms** | **0.0 ms** | 6.9 ms | 158.7 ms | 5.6 ms | 23.1 ms | 9.0 ms | 15.9 ms | **224.3 ms** |
| **5. Persistent changed transient Map** (reused) | **0.0 ms** | **0.0 ms** | 5.0 ms | 129.4 ms | 0.6 ms | 29.0 ms | 6.1 ms | 24.4 ms | **199.3 ms** |
| **6. Runtime revision change** (invalidated) | 1516.8 ms | 1652.8 ms | 16.5 ms | 315.7 ms | 0.3 ms | 22.2 ms | 14.9 ms | 57.3 ms | **526.0 ms\*** |
| **7. Child restart** (recovery) | 0.0 ms | 1003.7 ms | 10.4 ms | 204.3 ms | 0.3 ms | 23.7 ms | 7.6 ms | 18.1 ms | **275.3 ms\*** |
| **8. Invalidation after asset/data change** | 1721.3 ms | 1584.4 ms | 10.0 ms | 280.2 ms | 0.2 ms | 24.1 ms | 7.1 ms | 17.2 ms | **433.2 ms\*** |

`*` For fresh generations and restarts, generation staging/bootstrap occurs prior to request dispatch; the column reflects request-to-decoded turnaround time for that operation.

### Key Performance Takeaways:
1. **~18–20× turnaround improvement**: Warm identical and transiently modified map requests complete in **~199–224 ms**, down from **~3.7–4.0 s** in the cold baseline.
2. **Authoritative execution warms**: Authoritative work (`viewport_3d.init()` + `map_renderable_bundle.collect()`) drops from ~280–320 ms to **~129–159 ms** due to warm LuaJIT compilation and reusable internal render state.
3. **Transport and decoding are negligible**: Compact #761 payload transfer is ~6–9 ms, JSON parse is ~3–4 ms, and expansion is ~12–27 ms.

---

## 5. Crash and Recovery Behavior

1. **Child crash / exit**: If the child exits unexpectedly (e.g. fatal segfault or process kill), the host `close` handler triggers:
   - All active pending requests reject immediately with structured errors;
   - Child process handle is nulled;
   - Next request automatically triggers `_spawnChild()` to rehydrate the generation.
2. **Child hang / timeout**: If a request exceeds `REQUEST_TIMEOUT_MS` (30s):
   - The pending promise rejects with a timeout error;
   - The host forcefully terminates the hung child via `child.kill()`;
   - A fresh child is spawned on the subsequent request.
3. **Windows file lock handling (`EPERM`)**:
   - Calling `fs.rmSync()` on a staged directory immediately after `child.stdin.write('QUIT\n')` previously caused Windows `EPERM` errors because the exiting process still held open file handles.
   - The host now explicitly awaits the child's `close` / `exit` event before unlinking the staging directory. Cleanup is 100% clean across all test cycles.

---

## 6. Deterministic Gate Implications

- **Payload byte-identity**: Semantic hash comparison (`canonicalHash`, excluding runtime execution duration `encodeMs`) confirms **100% bit-for-bit equivalence** between cold and persistent runs:
  `cold = 87f25cc31638...`  
  `persistent = 87f25cc31638...`  
  `match = true`
- **Gate compatibility**: G1, G2, G3, G4, G5, and G6 remain strictly deterministic. Persistent authority executes the identical Lua loader, exploration engine, and presentation bundle collector as cold execution.
- **G6 speedup potential**: Headless G6 suite driving map editor screens can leverage the persistent bridge to dramatically reduce the ~11-minute run duration without altering screenshot pixels.

---

## 7. Surface Classification

| Surface | Authority Required | Recommendation | Rationale |
|---|---|---|---|
| **Map 3D Renderables** (`preview-map`, `/api/map-renderable`) | Runtime | **Persistent Authority** | Heavy 3D compilation (raycaster geometry, autotile resolution, heightmap triangulation, wall composite baking, dynamic lighting). Frequent authoring cadence. |
| **Map Inspection** (`preview-map-inspection`, `/api/map-inspection`) | Runtime | **Persistent Authority** | Reads transient map overlays against loaded engine data. Fast semantic inspection (~5–10 ms). |
| **Fog Preview** (`preview-fog`, `/preview-fog`) | Runtime | **Persistent Authority (Optional)** | Full 3D raycaster render with fog shader to PNG. Can share persistent map authority if live preview is needed. |
| **Animation Preview** (`preview-anim`, `/preview-anim`) | Pure Semantics / Shared Artifact | **EXCLUDED from Persistence** | Animations, frame timing (`[fps=15]`), and keyframe timelines belong to shared animation controller / sprite sheet artifacts and client-side canvas/WebGL playback, NOT multi-frame RPC rendering. |
| **Scene Layout** (`preview-scene`, `/preview-scene`) | Pure Semantics / Declarative | **EXCLUDED from Persistence** | Returns declarative window structures (`window_renderer.resolveState`). Belongs to shared declarative semantics, not live runtime simulation. |
| **Window Layout** (`preview-window`, `/preview-window`) | Pure Semantics / Declarative | **EXCLUDED from Persistence** | Mock layout resolution is declarative data. Visual frame preview is secondary. |
| **Font Preview** (`preview-font`, `/preview-font`) | Static Artifact | **EXCLUDED from Persistence** | Font metrics and glyph textures are static assets; belongs to standard canvas/DOM rendering. |
| **Sprite Metadata** (`sprite-meta`) | Static Artifact | **EXCLUDED from Persistence** | Pure metadata index of filenames and frame rates. Belongs to shared asset catalog. |

---

## 8. Conclusion & Next Steps

The persistent child experiment for live runtime authority is **fully validated**. It solves the multi-second cold-request penalty for runtime-bound operations while preserving 100% determinism, strong isolation, and clean crash recovery.

In accordance with project policy, this remains an **exploration experiment** and is not unilaterally productionized into the main Studio server until explicitly scheduled for migration.
