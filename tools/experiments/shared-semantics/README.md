# Shared-semantics technology spike

**Status:** experiment only. Nothing in this directory is wired into production Studio or runtime code.

This spike asks whether one authored semantic implementation can execute in both Thestra Studio/JavaScript and LÖVE/LuaJIT without a game-runtime RPC or a handwritten mirror.

It uses two ordered canaries:

1. sprite token/timing and file-resolution provenance;
2. deterministic vertex shading at the repository's existing ~1e-12 numerical contract.

## Candidates exercised

### TypeScriptToLua

`src/shared-semantics.ts` is the sole authored implementation for this candidate.

- `tsc` produces ordinary JavaScript under `generated/js/`.
- TypeScriptToLua with `luaTarget: "JIT"` produces Lua under `generated/lua/`.

Generated output is intentionally not committed by the spike.

### Same Lua source in Studio

`lua/shared-semantics.lua` is the sole authored implementation for this control.

- LÖVE/LuaJIT requires the file directly.
- Wasmoon executes the exact same source inside its embedded Lua 5.4 WebAssembly VM from Node.

This candidate deliberately tests the operational cost and compatibility limit of embedding a Lua VM in Studio rather than translating the semantic implementation.

## Exact local commands

From this directory:

```sh
npm install --ignore-scripts --no-audit --no-fund
node harness/build-bench.js
node harness/node-parity.js
node harness/wasmoon-parity.js
```

The LÖVE parity lane is assembled by `.github/workflows/shared-semantics-spike.yml` because it needs the repository's pinned LÖVE 11.5 distribution. The workflow copies only the required current production modules and experimental outputs into a temporary game directory, then runs `harness/love-main.lua` there.

The hosted workflow also runs the focused current production vertex-shading and sprite-timing/provenance tests plus `git diff --check`.

## What this experiment is not

- not a runtime migration;
- not permission to author the engine in TypeScript;
- not a production replacement for `presentation/sprite_sheet.lua`;
- not a production replacement for `engine/vertex_shading.lua`;
- not a persistent-LÖVE-process experiment;
- not a native/WASM platform rewrite.

The durable decision, measurements, failure modes, and migration recommendation live in the repository report produced by this spike.
