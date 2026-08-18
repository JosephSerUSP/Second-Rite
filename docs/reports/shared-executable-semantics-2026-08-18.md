# Shared executable semantics experiment — 2026-08-18

Issue: #772 — **Experiment with shared executable semantics across Thestra runtime and Studio**

Agent-Signature: GPT-5.6 Sol

## Executive result

The bounded experiment passes.

For **small, pure, deterministic, renderer-neutral semantics** needed locally by both the LÖVE/LuaJIT runtime and Thestra Studio, the smallest mechanism that survived this repository's deployment and causality falsifiers is:

> **one restricted TypeScript semantic source per leaf, mechanically compiled to checked-in ordinary JavaScript and ordinary LuaJIT-target Lua, with regeneration/conformance gates.**

This gives the repository **one authored semantic implementation and multiple local execution hosts**. It does not introduce a Studio-to-runtime RPC, a browser Lua VM, a runtime compiler, or a generic `thestra-core`.

The first fixture, vertex shading, passed exact numerical and deployment checks. Only after that result was healthy, the same mechanism was applied to the pure sprite timing grammar. Filesystem/resource inventory remains host-owned.

The result is evidence for the architectural distinction under investigation:

> **ONE SEMANTIC AUTHORITY, NOT NECESSARILY ONE EXECUTION HOST.**

This report is implementation evidence only. It does **not** change `AGENTS.md`; #773 owns any policy migration.

## Starting point and boundaries

The experiment branched from current `main` at task start, `ae8c6bad13e806de839388934f42abb9d8e88746`, after #766 had landed the direct Three mesh-definition consumer.

The first fixture started from two handwritten implementations of the same deterministic algorithm:

- `engine/vertex_shading.lua`;
- `tools/editor/js/vertex-shading.js`.

Both encoded the same hash constants, value noise, fractal octaves, validation, compilation, sampling, and grid behavior, with tests explicitly treating the JS implementation as Lua parity.

The experiment deliberately did **not**:

- edit `AGENTS.md`;
- migrate `engine/lighting.lua` or the #467/#475 domain;
- implement #754 persistent runtime work;
- modify map geometry or #766's direct Three consumer;
- redesign authored-storage I/O;
- move renderer truth, mutable game state, validation/Test Play, save/load, or export semantics into Studio;
- build a generic universal shared core.

## Mechanisms considered

### 1. Keep paired handwritten Lua/JS + parity tests

This remains the baseline. It has excellent deployment properties: no new toolchain and native debugging in each host. Its failure mode is semantic ownership: every semantic change is authored twice, and parity tests detect drift only after duplicate implementations already exist.

It is still the right answer for domains that do not survive the shared-source falsifiers below. #772 does not establish that all cross-runtime code should be generated.

### 2. Execute the same Lua source in Studio through an embedded Lua/WASM VM

The earlier technology spike proved this can achieve semantic identity, but it failed the bounded deployment/performance test for these tiny deterministic questions.

Measured with Wasmoon in that spike:

- VM creation: ~24.07 ms;
- semantic source load: ~9.13 ms;
- 5,000 JS→Lua calls: ~135.76 ms;
- 100,000 calls inside the VM: ~1025 ms;
- WASM payload: 271,581 bytes.

It also executes Lua 5.4 rather than the production LuaJIT 2.1 runtime. Shipping and initializing a second VM to remove roughly a hundred lines of duplicate shading semantics is a worse constraint than the existing drift risk.

**Rejected.**

### 3. Declarative algorithm/constant source + custom generators

A declarative source is attractive when the semantic authority is truly data: tables, schemas, enums, constants, mappings, or a small expression vocabulary.

Vertex shading is not just constants. It contains loops, local arithmetic, branching, validation, allocation, and numerical functions. A custom declaration capable of expressing the whole algorithm would become an ad hoc programming language and two code generators.

That increases bespoke build/debugging complexity precisely where the experiment is trying to delete semantic duplication.

**Rejected for this fixture.** A data-only authority remains appropriate for genuinely declarative future leaves.

### 4. Native shared implementation / C, Rust, Zig, or hand-authored WASM

A native or WASM core could be executable from multiple hosts, but this repository would then acquire native ABI/browser WASM/export/Android/CI packaging obligations for two small pure functions.

The deployment surface is disproportionate to the semantics being shared.

**Rejected.**

### 5. Restricted TypeScript -> JavaScript + LuaJIT-target Lua

The prior spike demonstrated that TypeScriptToLua can compile this fixture to ordinary Lua accepted by the repository's real LÖVE 11.5 / LuaJIT 2.1 host while ordinary `tsc` produces browser/Node JavaScript.

The production experiment tightened that mechanism:

- exact tool versions are isolated under `tools/shared-semantics/`;
- authoritative leaves live in `shared/semantics/`;
- generated outputs are checked in;
- normal Studio and LÖVE execution never invoke TypeScript or TypeScriptToLua;
- CI regenerates and rejects stale outputs;
- source-state tests reject reintroduction of handwritten host algorithms;
- the shared source is restricted to deterministic host-neutral constructs.

**Accepted for these fixtures.**

## Production shape

### Authored authorities

- `shared/semantics/vertex-shading.ts`
- `shared/semantics/sprite-timing.ts`

These are deliberately separate leaves. There is no generic shared-core module.

### Generated consumers

Studio / Node:

- `tools/editor/js/generated/vertex-shading.js`
- `tools/editor/js/generated/sprite-timing.js`
- sibling JS source maps

Runtime:

- `engine/generated/vertex-shading.lua`
- `engine/generated/sprite-timing.lua`

TypeScriptToLua's source-map traceback metadata is embedded in the generated Lua rather than emitted as a sibling `.lua.map` file.

The generated tree is currently **6 files / 57,499 normalized bytes**, with deterministic normalized SHA-256:

`1b4a8eef1c034e15cfa4057ba6b627f651efa2bf19a35580423c3e288c8910f0`

### Host adapters

`engine/vertex_shading.lua` now owns only Lua-facing integration:

- requires the generated semantic leaf;
- preserves the historical three-return-value Lua sampling API;
- preserves runtime authored-map validation entry points and numerical contract pins.

`tools/editor/js/vertex-shading.js` now owns only Studio-facing integration:

- exposes the existing public `ThestraVertexShading` surface;
- consumes the generated semantic namespace;
- retains its unrelated environment-lighting DOM bootstrap.

The shading algorithm itself is not handwritten in either adapter.

## Vertex-shading conformance evidence

The production conformance lane runs the same generated authority in Node/Studio and in the repository's real LÖVE/LuaJIT host.

It preserves the existing `1e-12` numerical contract pins:

| Fixture | Expected |
|---|---:|
| `hash01(0,0,0)` | `0.9616300366300367` |
| `hash01(1,2,1729)` | `0.18543956043956045` |
| `hash01(-1,0,23)` | `0.6313644688644688` |
| `valueNoise(.5,.5,1729)` | `0.42679334554334547` |
| `fractalNoise(.5,.5,1729)` | `0.4540415838459217` |
| `fractalNoise(1.25,2.75,1729)` | `0.45447714242048237` |
| `fractalNoise(-.25,.5,23)` | `0.3765472024340493` |

It additionally runs a deterministic 2,048-point coordinate/seed sweep in both hosts and pins:

- checksum: `1048868.5265851377` (comparison tolerance `1e-7` for the accumulated sum);
- minimum: `0.11815460869851695`;
- maximum: `0.8671328344589253`.

Validation boundaries and a compiled/sample color fixture are also pinned. The pre-existing Studio map vertex-shading test remains in the lane rather than being replaced by the new test.

The prior technology spike also compared the generated implementation against the old handwritten implementations directly. Representative 100,000-call measurements were:

| Host | Handwritten baseline | Generated shared source |
|---|---:|---:|
| Node `fractalNoise` 100k | ~71.79 ms | ~44.12 ms |
| LÖVE/LuaJIT `fractalNoise` 100k | ~84.34 ms | ~25.49 ms |

These are **not optimization claims**; runner and JIT effects make them unsuitable as product performance targets. They show that the shared-source mechanism did not purchase semantic identity with a concerning per-call regression.

## Production build/runtime measurements

A successful production conformance run on the Windows Server 2025 hosted runner used Node 24.19.0 and the repository's LÖVE 11.5 installer.

Measured costs:

| Measurement | Result |
|---|---:|
| isolated `npm ci` for shared build toolchain | ~4555.249 ms |
| regeneration + stale-output check | ~2376.658 ms |
| generated module load in Node (vertex + sprite timing) | ~1.997 ms |
| Node vertex `fractalNoise`, 100k | ~42.696 ms |
| LÖVE/LuaJIT vertex `fractalNoise`, 100k | ~26.643 ms |
| Node sprite parse + effective rate, 100k | ~53.992 ms |
| LÖVE/LuaJIT sprite parse + effective rate, 100k | ~35.531 ms |

Approximate per-call costs from those loops are sub-microsecond:

- Node vertex: ~0.427 µs;
- LÖVE vertex: ~0.266 µs;
- Node sprite parse+rate: ~0.540 µs;
- LÖVE sprite parse+rate: ~0.355 µs.

The important deployment fact is that the multi-second compiler/install costs occur **only in developer/CI generation**. They are absent from ordinary Studio launch, LÖVE launch, Test Play, and exported games.

## Ordinary LÖVE deployment impact

There is no runtime compiler, Node dependency, subprocess, dynamic code generation, WASM VM, or additional native library.

The runtime consumes checked-in ordinary Lua under `engine/generated/`. `tools/export/runtime-manifest.json` already exports the entire `engine/` and `presentation/` trees, so the generated Lua travels through the existing runtime packaging path without an exporter special case.

This was an important falsifier. A mechanism requiring TypeScriptToLua to be installed on a player's machine or invoked while staging a game would have failed #772.

## Studio / browser / Node deployment impact

Studio consumes checked-in ordinary JavaScript.

- vertex shading loads its generated leaf before the existing Studio adapter;
- sprite timing loads its generated leaf synchronously before `widgets.js`;
- no Studio authoring action invokes LÖVE merely to execute these pure algorithms;
- Node tests require the same generated JavaScript directly.

A future third JavaScript host already gets the same semantic authority without rewriting the algorithm. A non-JavaScript third host would need either another mechanical target from the same restricted authority or a new mechanism audit; it would **not** require hand-authoring the semantic algorithm again merely because the execution host changed.

## CI/toolchain consequences

The build-only toolchain is intentionally isolated instead of becoming a root runtime dependency:

- TypeScript `6.0.2`;
- TypeScriptToLua `1.37.1`;
- exact lockfile checked in;
- 15 packages in the observed clean install.

The earlier spike found TypeScript `6.0.3` incompatible with the selected TypeScriptToLua peer range, which is why exact versions are pinned rather than left floating.

The permanent `Shared semantics conformance` workflow:

1. installs the isolated build toolchain;
2. regenerates JS/Lua;
3. fails if checked-in outputs are stale;
4. runs Node semantic conformance;
5. asserts host source state so handwritten algorithms cannot silently return;
6. runs the existing Studio vertex-shading parity test;
7. runs the existing sprite timing provenance contract;
8. runs the shared semantics in real headless LÖVE/LuaJIT;
9. performs diff hygiene.

## Stale generated-artifact detection

`npm run check` snapshots the checked-in outputs, regenerates, compares them, restores the checkout, and fails with the stale file list if semantic content differs.

The first production CI attempt exposed two useful build-contract details:

1. TypeScriptToLua's source traceback mapping is embedded in Lua, so expecting sibling `.lua.map` files was incorrect and was removed from the output contract.
2. Windows checkout line-ending conversion can make byte-for-byte generated files appear different even when generation is semantically identical. The stale check now compares normalized text content, not CRLF policy. The generation digest is normalized the same way.

That is precisely why the stale check was exercised in the real repository runner rather than specified only on paper.

## Generated-output reviewability and debugging

The generated targets are ordinary text JS/Lua and are checked in, so a PR can inspect exactly what each host will execute. They are mechanically verbose compared with the authored leaves, especially the Lua helper/source-map scaffolding; reviewers should therefore review the TypeScript authority first and use generated diffs as compiler-output evidence rather than treat generated Lua as the primary authored surface.

Debugging remains materially better than an opaque bytecode/VM bridge:

- Studio gets normal JavaScript plus source maps;
- Lua remains ordinary readable Lua;
- TypeScriptToLua source-map traceback metadata is embedded in the generated Lua;
- the earlier spike explicitly demonstrated a generated Lua error tracing back to the authored TypeScript source.

The restricted source style is part of the mechanism. Shared leaves avoid host APIs, async behavior, prototype mutation, sparse-array assumptions, host-specific truthiness, and iteration-order-dependent semantics.

## Second fixture: sprite timing

Vertex shading passed before this fixture was migrated.

The shared sprite authority owns only the pure deterministic grammar:

- `[fps=N]` parsing;
- `[speed=N]` parsing;
- repeated-token last-wins behavior;
- filename tokens as defaults;
- authored key token overrides the **same** filename token;
- after merge, `fps` globally outranks `speed`;
- `speed=N` -> `4 * N` fps;
- no timing token -> default 4 fps.

Examples pinned in both Node and LÖVE include:

- key `fps=9`, filename `fps=15` -> 9 fps from key;
- key `speed=2`, filename `fps=15` -> 15 fps from filename because global `fps` precedence wins;
- key `fps=9`, filename `speed=2` -> 9 fps;
- key `speed=2`, filename `speed=3` -> 8 fps from key;
- neither -> 4 fps.

The new shared parser also closes a concrete prior cross-host inconsistency: JavaScript's old `tokens.fps || ...` treated `0` as false while Lua treats numeric zero as truthy. `fps=0` and `speed=0` now have one mechanically shared interpretation instead of host truthiness deciding the result.

Malformed numeric tokens are also interpreted by one shared numeric rule rather than Lua `tonumber` on one side and JavaScript `parseFloat` prefix parsing on the other.

### Host adapter boundary remains intact

`presentation/sprite_sheet.lua` still owns:

- LÖVE filesystem inventory;
- directory precedence;
- concrete path resolution;
- image loading/cache;
- quads, frame draw, and presentation clock.

Studio still owns:

- its asset/browser path input;
- image probing/display;
- CSS/local thumbnail animation;
- UI readiness and tooltip presentation.

Both local animation paths in `widgets.js` now synchronously call the generated timing leaf. The existing `/api/sprite-resolution` request remains asynchronous inspection/provenance metadata. **Studio animation does not wait for the runtime process.**

That preserves the historically correct causality: the runtime can remain authoritative for its resource inventory while the pure timing grammar executes locally from one authored authority.

## Exact remaining duplicated semantics

After the experiment, there are no independent handwritten vertex-shading algorithms in the runtime and Studio, and there are no independent handwritten sprite timing parsers/rate formulas in the runtime and Studio preview paths.

What remains intentionally duplicated or host-specific:

1. **Mechanical generated targets.** JS and Lua contain the same semantics in two generated representations. This is executable duplication, not authored semantic duplication; the generator/stale gate owns their relationship.
2. **Host adapters.** Lua return-shape compatibility, runtime loader iteration, browser globals/CommonJS exposure, DOM bootstrap, asset inventory, filesystem/path resolution, image loading, and UI rendering remain host code.
3. **Conformance oracles.** Tests repeat expected constants, precedence cases, and boundary outputs. Those are intentionally independent assertions, not alternate implementations.
4. **Human-readable prose.** Comments/tooltips may restate precedence for explanation; they do not compute it.
5. **Resource provenance.** Runtime resource lookup and Studio UI metadata plumbing remain different because they answer host-specific inventory/UI questions rather than one pure algorithm.

## Limitations / falsifiers that still apply

This mechanism is proven only for leaves with properties like these fixtures:

- deterministic;
- renderer-neutral;
- no filesystem or host process ownership;
- no mutable game/session state;
- no LÖVE graphics/audio API;
- small enough that generated output/tooling remains reviewable;
- expressible in the deliberately restricted cross-target subset.

It is **not** evidence to transpile the whole engine. Mutable runtime state, renderer truth, validation/Test Play, save/load/export authority, authored-storage I/O, and lighting/geometry ownership require their own architecture and should not be moved into Studio by analogy.

Likewise, if a future semantic leaf needs host-specific integer overflow, binary layout, FFI/native APIs, sparse structures, async effects, or language-specific metaprogramming, this mechanism must be re-falsified rather than assumed.

## Conclusion

For #772's bounded class, the experiment found a production-worthy mechanism:

> author a small pure semantic leaf once in restricted TypeScript, generate checked-in ordinary JS and LuaJIT-target Lua, execute both locally, and enforce parity/freshness mechanically.

Vertex shading survived the strict numerical, deployment, startup, per-call, CI, reviewability, stale-output, and debugging falsifiers. Sprite timing then successfully used the same mechanism while keeping resource discovery as host adapters and keeping Studio animation local.

The evidence therefore supports **one semantic authority without requiring one execution host** for this narrow class of semantics. It does not justify a generic shared core or a broad runtime migration.
