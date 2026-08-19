# Studio live runtime authority — post-#766 merge-readiness review

Date: 2026-08-18  
Issue: #754  
PR: #756  
Code baseline: `main` `ae8c6bad` (merged #766)  
Current remote `main` during review: `d71320bb` (#777, documentation-only)

## Decision

**PERSIST + REVISION-SCOPED SNAPSHOT/STAGE REUSE**, narrowly for Studio's compact `mesh-definitions-v1` Map-renderable authority.

Do **not** embed a LÖVE window. Do **not** build a general runtime daemon. Do **not** route pure deterministic semantics through this host; #772/#776 owns that class.

The production seam is one lazy, serial, Project/revision-scoped LÖVE authority generation for `/api/map-renderable` only when Studio requests the compact representation already defined by #761 and consumed directly by Three after #766. Unsaved Map state is a per-request overlay. Expanded-control renderables and Map Inspection remain cold reference paths.

#766 is important to the interpretation: this work does **not** recover time from the deleted browser compatibility expansion. The remaining win is avoiding repeated Project materialization plus LÖVE/runtime/compiler initialization for operations that genuinely require the runtime host.

## Authority-input audit

A persistent initialized generation is reusable only while every source input that can change the compiled Map representation is unchanged.

The reviewed generation identity covers the exact source roots fed to the ordinary external-Project staging boundary:

- runtime export manifest content;
- every manifest-selected runtime root file;
- every manifest-selected runtime directory, including engine/presentation Lua;
- manifest release/compiler configuration;
- generated runtime provider files copied into a staged runtime (`runtime-semantic-resources.lua` and `runtime-engine-server.lua`);
- opened Project `data/`, including non-transient Map-adjacent semantic data;
- every manifest-selected Project directory (currently including assets, and automatically covering future manifest-selected geometry/compiler configuration directories);
- opened Project `project.json`;
- the complete resolved RTP fallback tree.

This directly exercises the requested falsifiers: runtime Lua, runtime manifest, `project.json`, non-transient Project data, Project assets, tileset/model/height-map assets, RTP fallback, manifest-selected configuration, and generated runtime files all change generation identity.

Package contributions are not an input to this worker's current `stageProject()` call, so there is no untracked package-contribution input today. If that stage seam later gains package contributions, their revision must be added to generation identity at the same time.

The Node staging/compiler implementation itself is process-loaded Studio host code, not disk-read mutable generation input. A changed staging/compiler JS implementation therefore takes effect through the ordinary Studio relaunch/code deployment boundary. Generated Lua files that are copied from disk per generation are explicitly fingerprinted.

### Content-true identity

The original #756 prototype used sorted path/type/size/mtime metadata. Adversarial review rejected that contract: an equal-size edit with a preserved or restored mtime could retain stale runtime authority.

The hardened worker now makes the generation revision from **SHA-256 content digests**. A process-scoped digest cache avoids rereading unchanged large files, but metadata never substitutes for the digest. A cached digest may be reused only while strong filesystem change identity is unchanged: device/file identity, inode, size, mtime, ctime, and birth time. Equal-size rewrites with restored mtime still advance ctime; atomic replacement changes file identity. Directory membership is rescanned on every revision pass.

Hosted regression coverage rewrites equal-length runtime Lua bytes, restores the exact round-trippable old mtime, and verifies that the cached authority revision still changes across rapid edits.

## Transient Map contract

Unsaved Map state remains deliberately outside generation identity because it is the request overlay the warm host is meant to accept.

The runtime bridge still delegates semantics to `presentation.editor_renderable_bridge.run()`. That path overlays the submitted Map only in the loader for the request and restores the prior loader entry afterward; it does not save Project source. The real-LÖVE regression re-reads Project Map data after a changed transient request and proves that persistent source was not mutated.

Requests are serialized onto one worker generation. Each request gets its own staged transient JSON request file, which is deleted on completion/error. No transient Map request survives generation disposal.

Studio's Map workspace already owns UI supersession with a monotonic `bundleSerial`: an older async completion is discarded before installation when a newer authored state has been scheduled. #756 does not duplicate that browser sequencing mechanism.

Freshness is also checked at the runtime boundary itself. The worker captures the invalidation epoch and authority revision before generation selection, re-proves authority after staging before starting a new child, and re-proves it after LÖVE finishes before accepting a response. If non-transient authority changed during the request, that response is rejected and the generation is marked stale.

There remains the ordinary filesystem non-transactional edge shared by staging in general: an adversarial external A→B→A mutation could theoretically occur entirely inside one materialization interval. The production contract materially closes the realistic stale paths with content identity, pre/post proof, stage-time proof, and watcher invalidation, but this is not claimed to be an OS-wide transactional filesystem snapshot.

## Protocol review

The worker protocol remains deliberately tiny and serial; it was hardened rather than generalized.

Request framing is now:

`RENDERABLE WORKER REQUEST<TAB>request-id<TAB>map-id<TAB>relative-request-path`

Completion and error frames carry the same request identity. The Node host rejects a DONE/error frame for the wrong request ID and stales that generation.

Map IDs are rejected before staging if missing, larger than 1 KiB, or containing tab/newline framing characters. Request paths are worker-generated relative paths, not caller-provided protocol tokens. Lua-side error text has control characters flattened and is bounded. Stdout is bounded to the existing renderable transport budget, stderr diagnostics are tail-bounded, partial output times out, and a complete DONE frame whose renderable envelope cannot be parsed stales the generation.

A permanent ChildProcess `error` listener remains installed after startup so a later process/stdio failure cannot become an unhandled EventEmitter error.

## Lifecycle / failure contract

The review exercised and/or pinned:

- first generation startup;
- warm identical request;
- warm changed transient Map;
- explicit non-transient invalidation;
- fingerprint-driven invalidation without watcher delivery;
- repeated invalidations collapsing into one next generation;
- authority change while staging;
- authority change while a request is in flight;
- request serialization;
- wrong response identity;
- malformed complete output;
- partial output/timeout;
- bounded oversized output;
- child crash;
- post-readiness ChildProcess error;
- Studio/runtime-bridge shutdown;
- Project switching by Studio relaunch;
- Windows child-before-stage cleanup;
- injected POSIX/Linux kill escalation.

### Shutdown and cleanup

Shutdown sends `QUIT` and waits for confirmed child exit. If the child does not exit, async shutdown escalates to `SIGTERM`, then:

- Windows: `taskkill /T /F`;
- POSIX/Linux: `SIGKILL`.

Stage removal occurs only after child death is confirmed. If termination cannot be confirmed, the stage is retained rather than racing deletion against a live process. This preserves the Windows `EPERM` ordering discovered by the original experiment while remaining cross-platform.

The runtime bridge's existing Electron `will-quit` close boundary synchronously shuts down the worker before closing the HTTP server. A dedicated regression now pins that ownership boundary, so a persistent LÖVE child is not intentionally left orphaned when Studio/server exits.

Project identity remains process-scoped. Studio already relaunches when switching the opened Project, so a worker generation cannot cross Project identity.

## Performance evidence on hardened code

Hosted Windows Server 2025, Node 24, LÖVE 11.5 + pinned Mesa, Map 2. All controls returned the same compact direct representation: **0.802 MiB, 16 definitions, 445 placements, 194 literal surfaces**. No pre-#766 compatibility reconstruction was measured.

### Revision cost

The correctness-first full-content implementation initially measured roughly 158–191 ms for every revision pass and pushed warm direct-ready latency to roughly 0.77–0.80 s. That still beat cold execution but made the freshness proof too expensive.

With the content-digest cache described above, one cold source-content scan measured **166.926 ms** and four subsequent complete revision passes measured:

- 28.218 ms;
- 29.180 ms;
- 21.345 ms;
- 20.630 ms.

The generation revision remains content-derived; these warm passes reuse already-proved file digests only while strong file-change identity remains unchanged.

### End-to-direct-ready comparison

| control | runtime authority | Studio direct-consumer prep | request → direct-ready | PID |
|---|---:|---:|---:|---:|
| cold one-shot | 4572.983 ms | 405.417 ms | **4986.061 ms** | — |
| persistent first generation | 3444.542 ms | 189.611 ms | 3643.883 ms | 3856 |
| persistent identical reuse | **220.253 ms** | 187.569 ms | **416.464 ms** | 3856 |
| persistent changed transient Map | **193.073 ms** | 195.767 ms | **397.301 ms** | 3856 |
| forced non-transient rebuild | 2333.038 ms | 178.425 ms | 2519.529 ms | 1636 |

The exact same PID handled the identical and changed-transient warm requests. Forced non-transient invalidation produced a new PID and returned to a multi-second generation cost. That negative control remains the central architectural evidence: process persistence **without revision-scoped stage/runtime reuse** loses most of the benefit.

On this hardened run, warm direct-ready was about **12× faster** than the same-run cold control. Runtime authority itself fell from 4.57 s cold to 0.19–0.22 s warm.

The 178–196 ms direct-prep values are current direct-consumer preparation in this benchmark; #754 does not optimize browser-side placement RGB. Different hosted runs have shown that browser preparation is variable, so it is separated here from fingerprint/staging/runtime authority instead of being credited to persistence.

### Cold causality remains unchanged

Earlier post-#761 decomposition established representative cold work at roughly:

- stage/snapshot: 1.1–1.4 s;
- LÖVE/runtime initialization: ~0.52 s after process launch;
- `loadMap()`: single-digit milliseconds;
- authoritative Map work: roughly 0.26–0.28 s in those controls;
- serialization/stdout/JSON parse: tens of milliseconds rather than the dominant cost.

The current evidence therefore continues to support reuse of the staged generation and initialized runtime/compiler state, not a return to transport-size optimization as #754's explanation.

## Falsifiers

| falsifier | result |
|---|---|
| savings are small after #761/#766 | **NOT FIRED** — 4.99 s cold direct-ready vs 0.40–0.42 s warm on the current compact/direct path |
| persistence without stage/revision reuse is enough | **FIRED AS A NEGATIVE CONTROL** — forced rebuild returns to 2.52 s and a new PID |
| revision identity can safely use mtime/size metadata | **FIRED** — review replaced it with content-derived identity and regression coverage |
| stale in-flight responses can be accepted | **NOT FIRED** — pre/stage/post revision proof plus epoch guard suppress stale authority |
| transient Map state mutates Project source | **NOT FIRED** — real LÖVE regression reloads source after changed transient Map |
| protocol can rely on untagged serial framing | **FIRED** — explicit request identity and token validation added |
| Windows cleanup ordering is portable as-is | **FIRED** — POSIX SIGTERM→SIGKILL escalation added; Windows taskkill retained |
| persistence complicates Project switching | **NOT FIRED** — Project switch already relaunches Studio |
| embedding is required | **NOT FIRED** — ordinary stdin/stdout IPC captures the measured benefit |

## Verification

The hardened measurement head passed the permanent runtime-data boundary with **52/52 tests** before temporary benchmark instrumentation was removed. It included:

- syntax PASS;
- real cold LÖVE bridge PASS;
- real persistent LÖVE worker emits `mesh-definitions-v1` PASS;
- same PID across identical and changed transient Map PASS;
- Project source unchanged after transient request PASS;
- equal-size/restored-mtime cached-revision invalidation PASS;
- all authority-input categories PASS;
- stage-time and in-flight authority-change rejection PASS;
- wrong-ID/malformed/partial/oversized protocol controls PASS;
- child crash/error recovery PASS;
- injected POSIX kill escalation PASS;
- source checkout cleanliness PASS.

The subsequent final workflow removes the one-off benchmark step and adds the explicit runtime-bridge/server shutdown ownership test. The ordinary PR gates are rerun on that durable-only diff.

Relative visual A/B was also inspected rather than attributed to #756: the observed G6 failure occurred while capturing **base** `ae8c6bad`, where `editor-screens.py check` timed out after about 420 s before candidate checkout/capture and with zero frames compared. G5 relative A/B passed. That is the existing #739 G6 harness-reliability lane, not evidence of a #756 candidate rendering regression.

A transient Studio-host failure on an earlier hardening commit was likewise inspected: all boundary/unit layers passed and only native Database semantic readiness missed its host smoke window before this worker compiled a Map. The next unchanged architectural run passed the native host smoke; final-head status is the merge-readiness authority.

## Production scope / non-goals

- **PERSIST + REVISION-SCOPED SNAPSHOT/STAGE:** implemented for compact Map renderables.
- **KEEP COLD:** Map Inspection, expanded renderable control, validation, screenshots, and unrelated preview endpoints.
- **PURE SHARED SEMANTICS:** #772/#776, not this host.
- **NATIVE UI LATENCY ATTRIBUTION:** #751.
- **G6 RELIABILITY:** #739/#775.
- **THREE REPRESENTATION CONSUMPTION:** #766.
- **ARCHITECTURE POLICY WORDING:** #773; AGENTS.md is unchanged here.

No embedded LÖVE window, generic daemon, binary/Int16 transport, LOD, runtime instancing, fidelity changes, compatibility-expanded triangle bundles, or browser placement-RGB optimization is included.

Agent-Signature: GPT-5.6 Sol
