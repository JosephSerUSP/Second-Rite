# Shared executable semantics experiment — merge-readiness result

**Issue:** #772  
**Original experiment date:** 2026-08-18  
**Status:** bounded mechanism passes after adversarial merge-readiness correction.

The original experiment report, including its first successful measurements and rejected alternatives, is preserved byte-for-byte as the [pre-review baseline](shared-executable-semantics-2026-08-18-baseline.md). This file records the durable mechanism after merge-readiness review so historical implementation details are not mistaken for the final runtime contract.

## Decision

For **small, pure, deterministic, renderer-neutral semantics** needed locally by both Thestra's LÖVE/LuaJIT runtime and Thestra Studio, the accepted mechanism is:

> **one restricted TypeScript semantic source per leaf, mechanically compiled to checked-in ordinary JavaScript and ordinary LuaJIT-target Lua, with stale-output and cross-host conformance gates.**

This is **one authored semantic authority, multiple local execution hosts**. It is not a Studio-to-runtime RPC, browser Lua VM, runtime compiler, native core, generic `thestra-core`, or justification for moving mutable/runtime/renderer truth into shared TypeScript.

The two bounded fixtures remain:

- `shared/semantics/vertex-shading.ts` — deterministic vertex-shading algorithm;
- `shared/semantics/sprite-timing.ts` — pure `[fps=N]` / `[speed=N]` token grammar and rate precedence.

Runtime filesystem/resource lookup, image/cache/quads/drawing, mutable game state, rendering, validation/Test Play, save/load and export/runtime truth remain host/runtime responsibilities.

## Merge-readiness corrections

Adversarial review found two real mechanism-boundary issues in the successful experiment and corrected them before landing.

### 1. Generated Lua module load is process-local

The initial experiment enabled TypeScriptToLua `sourceMapTraceback`. That helper registers global source-map state and replaces process-wide `debug.traceback` merely when a generated module is required. That side effect is disproportionate to these pure semantic leaves and violates the intended host-neutral boundary.

The durable Lua build therefore sets:

```json
"sourceMapTraceback": false
```

JavaScript source maps remain ordinary sibling build outputs. Generated Lua contains no `__TS__SourceMapTraceBack` install, does not create `_G.__TS__sourcemap` / `_G.__TS__originalTraceback`, and does not replace `debug.traceback`.

The real LÖVE/LuaJIT conformance harness snapshots those process globals before requiring either generated module and fails if module load changes them.

### 2. Sprite numeric-token language is explicitly portable

The original sprite fixture intentionally fixed JavaScript truthiness drift around numeric zero, but merge review also challenged the assumption that JavaScript `Number(...)` and generated LuaJIT numeric conversion accept the same string language.

The shared source now defines the portable subset explicitly:

- decimal integers/fractions, signs, leading-dot decimals and exponents are accepted when finite;
- surrounding ASCII whitespace is accepted;
- historical **unsigned `0x` hexadecimal** remains accepted;
- binary `0b` / octal `0o` spellings are rejected;
- signed hexadecimal is rejected because host behavior differs;
- non-finite and malformed suffix values are rejected as timing numbers.

The exact same boundary matrix now runs in Node and in real LÖVE/LuaJIT, including zero, unsigned hex, signed decimals, exponent, whitespace, binary/octal, signed hex, infinity and malformed suffixes.

## Permanent conformance contract

`Shared semantics conformance` owns the mechanism:

1. install the isolated pinned TypeScript / TypeScriptToLua toolchain;
2. regenerate and reject stale checked-in JS/Lua targets;
3. run Node semantic and boundary conformance;
4. assert host adapters have not regrown handwritten duplicate algorithms;
5. run the existing Studio vertex-shading parity and sprite-timing provenance contracts;
6. require the generated targets in real LÖVE/LuaJIT, including the 2,048-point shading sweep, sprite numeric-token matrix and process-global side-effect negative control;
7. run diff hygiene.

Ordinary Studio use and exported/runnable LÖVE games consume only checked-in generated JavaScript/Lua. The TypeScript toolchain is build/CI-only.

## Scope / architectural consequence

The experiment supports the distinction:

> **ONE SEMANTIC AUTHORITY, NOT NECESSARILY ONE EXECUTION HOST.**

It does **not** establish that every cross-runtime concern belongs in TypeScript. A leaf must remain small, pure, deterministic and host-neutral. Domains that require LÖVE facilities, Project materialization, renderer truth, mutable session state or product execution belong in other destination classes demonstrated by #756/#766 and by ordinary runtime truth.

No `AGENTS.md` policy changes are included here. #773 owns policy migration after this mechanism lands.

For the original measurements, alternative mechanisms, deployment discussion and pre-review generated-tree statistics, see the [preserved baseline report](shared-executable-semantics-2026-08-18-baseline.md).

Agent-Signature: GPT-5.6 Sol
