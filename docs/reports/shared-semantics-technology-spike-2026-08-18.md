# Shared-semantics technology spike — 2026-08-18

## Decision

**Recommend TypeScriptToLua, narrowly, for pure deterministic shared-semantic leaf modules.**

The experiment found a workable low-complexity mechanism for the specific architecture under test:

```text
one authored TypeScript semantic implementation
        |
        +-- tsc --------------------> ordinary JavaScript for Studio/Node
        |
        +-- TypeScriptToLua (JIT) --> generated Lua for LÖVE/LuaJIT
```

This is **not** a recommendation to migrate the engine to TypeScript, to move runtime state into Studio, or to make TypeScript the repository-wide semantic authority. It is a recommendation for a deliberately small class of code: pure, deterministic algorithms whose inputs and outputs are ordinary data and which currently have to be mirrored in Lua and JavaScript or queried through a heavyweight runtime process.

The stronger canary, vertex shading, passed the existing approximately `1e-12` numerical contract under all of:

- current runtime Lua;
- current Studio JavaScript;
- JavaScript compiled from the experimental shared TypeScript source;
- Lua generated from that same TypeScript source and executed by the repository's actual LÖVE/LuaJIT runtime.

The smaller sprite canary also matched the current runtime fixtures, including key-token precedence, filename-token inheritance, global `fps` priority over `speed`, `speed -> 4 * speed`, default `4 fps`, and current file-resolution/provenance behavior when supplied with a pure file inventory.

The same-Lua/Wasmoon alternative also achieved semantic parity for these fixtures, but it is not the recommended mechanism: Studio would gain an embedded Lua 5.4 WebAssembly VM, per-engine startup/source-load cost, JS/Lua bridge cost, and a VM whose language/runtime is not the LuaJIT 2.1 / Lua 5.1 environment that production LÖVE actually uses.

A declarative/generated contract is attractive for tables, enums, schemas, token names, precedence tables and other static data. It stops being the lowest-complexity answer when the second canary is included: expressing vertex shading requires inventing and maintaining a general algorithm DSL/code generator. A native C/Rust/Zig/WASM shared core would solve a larger portability problem than Thestra currently has while adding native ABI, browser/WASM, Android and CI packaging burdens. It was therefore assessed, not built.

## Scope and non-goals

This branch is a bounded technology spike. It does **not** wire production Studio or runtime code to either candidate.

The experiment lives under:

```text
tools/experiments/shared-semantics/
```

and is exercised by:

```text
.github/workflows/shared-semantics-spike.yml
```

Production files such as `presentation/sprite_sheet.lua`, `engine/vertex_shading.lua`, `tools/editor/js/vertex-shading.js`, and `tools/editor/js/widgets.js` were not replaced or modified.

The branch started from current `main` at:

```text
726eabcd205cb405f2be780246068938698a9284
```

The spike explicitly did not test a persistent LÖVE process. The question here is whether pure semantic questions can stop deserving a process boundary at all.

## Existing architectural context

The repository's existing authority rule has successfully prevented the Studio from silently approximating runtime behavior. The sprite-timing history exposes the cost of taking that rule literally across a process boundary:

- #402 identified authored-key/filename-token provenance as runtime semantics that Studio should not reinvent.
- merged #681 added runtime-authoritative sprite metadata/resolution.
- #713 measured the resulting cold runtime consultation as vastly more expensive than a simple asset fetch.
- merged #723 added caching/coalescing/invalidation so repeated queries amortize the cost without moving the semantic rules into JavaScript.

That history is correct as far as authority is concerned, but it leaves a pure rule hosted behind the runtime process.

There is also still an important local duplication in production Studio today: `tools/editor/js/widgets.js` contains two handwritten preview-timing parsers. They parse `[key=value]` tokens with JavaScript `parseFloat` and derive animation FPS with JavaScript truthiness, while the provenance tooltip separately asks `/api/sprite-resolution` for the runtime-authoritative answer. In other words, current Studio already has both a runtime-authoritative provenance path and local preview timing semantics.

Vertex shading is the opposite kind of canary. `engine/vertex_shading.lua` and `tools/editor/js/vertex-shading.js` deliberately mirror the same numerical algorithm. The implementation was designed so relevant arithmetic remains in the range where LuaJIT and JavaScript use equivalent IEEE double behavior, and `tools/editor/tests/test-map-vertex-shading.js` pins representative values to about `1e-12`.

This makes the two canaries complementary:

1. sprite timing asks whether a tiny rule can become genuinely shared without a runtime RPC;
2. vertex shading asks whether the same mechanism remains trustworthy when exact deterministic floating-point behavior matters.

## Implementations tested

### Candidate A — TypeScriptToLua

One authored file:

```text
tools/experiments/shared-semantics/src/shared-semantics.ts
```

Two compiler targets:

- ordinary JavaScript through `tsc`;
- Lua through TypeScriptToLua with `luaTarget: "JIT"`.

The source contains only the experimental pure sprite and vertex-shading semantics. File-system access is not part of the shared algorithm. The sprite resolver accepts an ordinary list of available asset paths so a future production adapter could supply that inventory from LÖVE, Studio, a package index, tests, or another host without teaching the shared core host APIs.

The experiment pins:

```text
typescript          6.0.2
typescript-to-lua   1.37.1
```

The exact TypeScript version is notable: TypeScriptToLua 1.37.1 declared an exact TypeScript 6.0.2 peer requirement. An initial attempt with 6.0.3 was rejected by npm. The spike fixed the version rather than forcing peer resolution.

Official TypeScriptToLua documentation used for the spike:

- https://typescripttolua.github.io/docs/getting-started/
- https://typescripttolua.github.io/docs/configuration/
- https://typescripttolua.github.io/docs/caveats/

The caveats matter. TypeScriptToLua explicitly does not promise identical JavaScript and Lua behavior for all source programs. Its documentation calls out boolean coercion/truthiness, `null`/`undefined`, array/table length, key iteration order, stable sorting and async execution among the possible differences. The recommendation in this report therefore depends on a **restricted shared-semantic subset plus cross-target parity tests**, not on treating transpilation as proof of equivalence by itself.

### Candidate B — the same Lua source inside Studio

One authored file:

```text
tools/experiments/shared-semantics/lua/shared-semantics.lua
```

The exact same file is:

- required by LÖVE/LuaJIT in the experiment;
- executed by Wasmoon from Node.

The experiment pins:

```text
wasmoon 1.16.0
```

Wasmoon is explicitly a Lua 5.4 VM compiled to WebAssembly with JavaScript bindings. Its official project documentation describes Node/browser embedding and warns that frequent JS/Lua interop can materially affect performance:

- https://github.com/ceifa/wasmoon

This candidate is useful because it is the literal version of “keep the Lua file authoritative and execute it in Studio.” It proves that the idea can work, but also makes the operational tradeoff visible: Studio acquires another VM and still does not execute the exact production LuaJIT VM.

### Candidate C — declarative/generated contract

No general code generator was built.

For sprite timing alone, a neutral contract could plausibly describe:

- recognized token names;
- token precedence;
- the `speed` multiplier;
- the default;
- resolution directory/candidate precedence.

Small target emitters could then generate Lua and JavaScript.

The second canary changes the economics. Vertex shading contains validation, hashing, interpolation, smoothstep, octave transforms, iteration and multiplication. Extending a neutral grammar until it can express this algorithm means designing a small programming language, its two code generators, debugging conventions, versioning, tests and semantic restrictions. That is a larger custom toolchain than TypeScriptToLua and has no external ecosystem maintaining the compiler.

**Conclusion:** use declarative generation where the semantics genuinely are declarative. Do not make a home-grown cross-language algorithm DSL the shared core.

### Candidate D — native/WASM shared core

No native proof was built because neither canary needed one to answer the architectural question.

A C/Rust/Zig-style core could expose the same implementation to Lua through a native binding/FFI path and to Studio through native Node bindings and/or WebAssembly. It would also offer a plausible future path to non-JS hosts.

That advantage comes with costs that do not exist for the recommended candidate:

- native binaries and ABI matrices;
- separate native and WASM build outputs;
- Node/Electron ABI/version concerns or a stable FFI boundary;
- browser/WASM loading/glue;
- Android NDK/cross-compilation concerns;
- platform-specific CI and packaging;
- more difficult debugging across language/ABI boundaries.

LuaJIT's official documentation confirms both Lua 5.1 compatibility and an FFI capable of calling external C functions, so this route is technically credible. It is simply disproportionate for sprite timing and vertex shading today:

- https://luajit.org/extensions.html
- https://luajit.org/ext_ffi.html

## Exact experiment commands

From `tools/experiments/shared-semantics/`:

```sh
npm install --ignore-scripts --no-audit --no-fund
node harness/build-bench.js
node harness/node-parity.js
node harness/wasmoon-parity.js
```

The actual LÖVE/LuaJIT parity lane is assembled by `.github/workflows/shared-semantics-spike.yml` using the repository's existing pinned LÖVE 11.5 installer. CI copies only the current production modules and experimental outputs required by the canaries into a temporary headless LÖVE game and runs `harness/love-main.lua` through a fail-closed bootstrap.

The production-focused hygiene commands run in the same successful workflow are:

```sh
node --test tools/editor/tests/test-map-vertex-shading.js
node tools/editor/test-sprite-timing-provenance.js
git diff --check
```

## Canary 1 — sprite timing and resolution

### Rules exercised

The candidate preserves the current runtime rules exercised by `tests/test_sprite_sheet.lua`:

- tokens in the authored sprite key are parsed;
- tokens in the resolved filename are parsed;
- a key token replaces the filename value for the same token;
- after merging, `fps` globally outranks `speed`;
- `speed` means `4 * speed` FPS;
- no timing token means `4 fps`;
- timing provenance identifies key, filename or default;
- current direct-path resolution candidates outrank indexed token-bearing filenames;
- current asset-directory search precedence is retained.

The important cross-token fixture is:

```text
pixie[speed=2]
```

against:

```text
assets/smallBattlers/Pixie[fps=15].png
```

The effective result remains `15 fps` from the filename because `fps` globally outranks `speed`, even though the `speed` token was explicitly authored in the key.

### Pure boundary

The candidate does **not** contain `love.filesystem`, Node `fs`, Electron APIs or a process RPC. Resolution receives a list of available paths.

That boundary is important for a future production migration. The semantic question is:

```text
(sprite key, available asset paths) -> resolution/provenance/timing
```

not:

```text
spawn LÖVE -> inspect project -> return timing
```

Host-specific file discovery remains host-specific infrastructure. Resolution semantics do not need to be.

### Existing Studio drift exposed by the audit

The spike did not modify production, but inspection found why moving this canary first is useful.

Current `widgets.js` preview code uses JavaScript `parseFloat` and truthiness. Runtime `presentation/sprite_sheet.lua` uses Lua `tonumber` and Lua truthiness. Those are not a semantic contract.

For example, an authored `fps=0` is truthy in Lua but falsey in JavaScript. The runtime would retain `fps = 0`; the current preview expression can fall through to `speed` or the `4 fps` default. Similarly, `parseFloat` accepts some partially numeric strings that `tonumber` rejects. These may be invalid or undesirable authored values, but they demonstrate that the present duplicate parser already has host-language behavior embedded in it.

A production migration should therefore add adversarial fixtures around zero, malformed numeric strings, whitespace and token grammar, then preserve or intentionally tighten the current runtime contract in one place. It should not merely move the current happy-path regex into TypeScript.

The experiment also probed `fps=0b10`; the current LÖVE/LuaJIT runtime, the same-Lua candidate and the TypeScriptToLua-generated Lua all produced `2`. That probe did **not** reveal a candidate mismatch.

### Verdict

**Sprite timing should be the first production migration.**

It is small enough to review exhaustively, it already has runtime fixtures and provenance tests, and production Studio still contains actual preview-side duplicate timing logic. It gives the repository a low-risk place to establish the build, generated-output and parity-test conventions before touching vertex shading.

## Canary 2 — vertex shading

### Exact pinned parity

The experiment exercises the existing pinned values across current and candidate implementations.

Representative pins include:

```text
hash01(0, 0, 0)
  0.9616300366300367

hash01(1, 2, 1729)
  0.18543956043956045

hash01(-1, 0, 23)
  0.6313644688644688

valueNoise(0.5, 0.5, 1729)
  0.42679334554334547

fractalNoise(0.5, 0.5, 1729)
  0.4540415838459217

fractalNoise(1.25, 2.75, 1729)
  0.45447714242048237

fractalNoise(-0.25, 0.5, 23)
  0.3765472024340493
```

The authored sample layer at `(2.5, 3.5)` remains:

```text
r = 0.9897950411471678
g = 0.9896537191396242
b = 0.9895731404301878
```

All comparisons use the existing approximately `1e-12` contract.

The successful LÖVE run identified the actual runtime as:

```text
LÖVE   11.5.0
Lua    5.1
LuaJIT 2.1.1700008891
```

and reported `LOVE PARITY OK` after comparing current Lua, same-authored-Lua and TypeScriptToLua-generated Lua.

The generated JavaScript lane independently reported `NODE PARITY OK` against the current handwritten Studio JavaScript.

### Validation and compile behavior

The experiment also runs malformed layer input through validation and compile. All relevant implementations reject the same classes of invalid fields:

- malformed `colorA`;
- strength outside `0..1`;
- non-positive scale;
- non-integral/out-of-range seed.

TypeScriptToLua's `sourceMapTraceback` was enabled. A deliberately invalid compile produced a Lua traceback that included:

```text
generated/shared_semantics.ts:351: in function 'compile'
```

alongside generated-Lua/lualib and harness frames. This is meaningfully better than debugging generated Lua without source mapping, although still noisier than a native TypeScript/JavaScript stack.

### Representative grids

The benchmark samples compiled shading across:

- Map 2 dimensions: `17 x 17`;
- Map 3 dimensions: `23 x 23`;
- a `128 x 128` stress grid representative of the repository's maximum map scale.

No numerical mismatch was observed.

### Verdict

**Vertex shading is safe to follow sprite timing, provided migration replaces the two handwritten production implementations rather than adding a third one and retains exact cross-target parity gates.**

The stronger canary did not expose meaningful numeric drift from one-source TypeScript compilation to ordinary JS and LuaJIT-target Lua.

## Measurements

All timings below are hosted-CI measurements and should be interpreted for order of magnitude, not as precise local workstation benchmarks. JIT warm-up, runner scheduling and package-network conditions create visible noise between runs.

The final successful spike run reported the following.

### Build and toolchain

| Measurement | Result |
|---|---:|
| TypeScript -> JS cold build | 834.33 ms |
| TypeScript -> Lua cold build | 1451.47 ms |
| sequential dual cold build | 2285.80 ms |
| repeat JS build | 692.46 ms |
| repeat Lua build | 1586.65 ms |
| JS watch rebuild | 412.22 ms |
| Lua watch rebuild | 516.64 ms |
| authored TS source | 16,270 bytes |
| generated tree | 62,927 bytes / 3 files |
| generated JS | 14,963 bytes |
| isolated `node_modules` | 26,951,347 bytes / 924 files |
| package directories observed | 30 |

Other successful hosted runs put the JS watch rebuild around `0.37-0.41 s` and the Lua watch rebuild around `0.44-0.54 s`.

Two consecutive generation passes produced the same tree hash:

```text
c2f48792a64b7a5f1e5a2d981a8c968caa72a38a7b27918eca6d8f7f6a00ac1e
```

and the same hash was reproduced in later hosted runs. For these canaries, generated output is stable enough for a regenerate-and-diff/hash CI policy.

A clean isolated dependency install added 17 npm packages. Successful hosted installs varied from roughly `5-7 s`, with one runner/network outlier around `25 s`. The important packaging result is not the transient download time; it is that the build dependency is non-trivial but remains a build dependency rather than a new runtime for the game or Studio.

### Native Studio/Node target

Final successful run:

| Work | Current handwritten JS | Generated JS |
|---|---:|---:|
| `fractalNoise`, 100,000 calls | 71.79 ms | 44.12 ms |
| Map 2 grid, 17 x 17 | 0.468 ms | 0.403 ms |
| Map 3 grid, 23 x 23 | 0.754 ms | 0.353 ms |
| 128 x 128 grid | 18.93 ms | 13.46 ms |

These are JIT-sensitive microbenchmarks and are **not** evidence that transpilation is an optimization. Earlier runs contained warm-up outliers. They do show that the generated ordinary-JS implementation did not introduce a concerning performance cost. Studio executes ordinary JavaScript; there is no shared-semantics VM or process startup.

### LÖVE/LuaJIT target

Final successful run:

| Work | Current Lua | Same-Lua control | TSTL generated Lua |
|---|---:|---:|---:|
| `fractalNoise`, 100,000 calls | 84.34 ms | 79.39 ms | 25.49 ms |
| Map 2 grid, 17 x 17 | 0.400 ms | 0.388 ms | 0.229 ms |
| Map 3 grid, 23 x 23 | 0.616 ms | 0.558 ms | 0.326 ms |
| 128 x 128 grid | 17.42 ms | 15.76 ms | 8.94 ms |

Again, this is a parity spike, not a performance optimization claim. The important result is that generated Lua executes normally under the repository's actual LuaJIT runtime, passes exact values, and is easily fast enough for this class of computation.

### Wasmoon / embedded same-Lua target

Final successful run:

| Measurement | Result |
|---|---:|
| VM creation | 24.07 ms |
| shared Lua source load | 9.13 ms |
| 5,000 JS -> Lua `fractalNoise` calls | 135.76 ms |
| 100,000 calls inside Lua VM | 1025 ms |
| Wasmoon WASM payload observed | 271,581 bytes |
| shared Lua source | 11,006 bytes |
| embedded VM language | Lua 5.4 |

Across successful runs, VM creation ranged roughly `22-61 ms` and source load remained around `8.5-9.1 ms`.

For a coarse task, 20-60 ms of one-time VM startup may be perfectly reasonable. For tiny semantic calls that can instead be native JavaScript, it is unnecessary overhead. The more important architectural weakness is that this validates the same source under Lua 5.4 and separately under LuaJIT; it does not make Studio execute the same VM semantics as production LÖVE.

## Failure modes observed during the spike

The failed experiment iterations are useful evidence about operational complexity.

1. **TypeScriptToLua peer coupling.** TSTL 1.37.1 rejected TypeScript 6.0.3 and required its exact 6.0.2 peer. The experiment now pins the required compiler rather than overriding npm.
2. **TypeScript 6 configuration churn.** The first JS config used options that TypeScript 6 now deprecates or constrains differently. The experimental config was adjusted. A production integration should start from current TS6 module/build conventions rather than preserve the spike's transitional compatibility settings.
3. **Windows watch-process harness.** Invoking `.cmd` compiler wrappers made process termination unreliable. The benchmark now launches compiler JS entrypoints directly and observes generated-file modification time.
4. **Benchmark API mismatch.** The first grid benchmark assumed the current JS mirror exposed a `grid()` helper. It does not. The corrected harness benchmarks the actual common `compile` + `sampleCompiled` surface.
5. **Hosted Windows OpenGL.** LÖVE initially stopped before `main.lua` because the hosted runner exposed only GDI OpenGL 1.1. The parity game now disables graphics/audio/window modules because these canaries are pure semantics.
6. **LÖVE virtual filesystem boundary.** A bootstrap initially used OS `dofile("body.lua")`; switching to LÖVE's `require("body")` loaded from the game source correctly.

None of those failures was a canary semantic mismatch. The final workflow passes every experiment and focused production-contract step.

## Decision matrix

| Axis | TypeScript -> JS + TSTL Lua | Same Lua + Wasmoon | Declarative/generated contract | Native/WASM core |
|---|---|---|---|---|
| One authored source | **Yes** | **Yes** | Yes, if the grammar can express the semantics | **Yes** |
| Exact LuaJIT behavior | **Canary-proven, not language-global**; generated Lua ran under actual LuaJIT and matched pins | Runtime side exact when same file runs in LuaJIT; Studio VM is Lua 5.4, so **not exact VM parity** | Only as good as both emitters and the contract semantics | Independent implementation can be exact at API boundary, but no longer Lua semantics |
| Native Studio performance | **Yes: ordinary JS** | No; embedded WASM Lua VM | Yes after JS generation | WASM/native can be fast but needs glue |
| Browser/Electron compatibility | **Strong**; ordinary JS | Supported, with WASM/bundler concerns | Strong if JS emitter is simple | WASM viable; native Electron path adds another target |
| Node compatibility | **Strong** | Supported | Strong if JS generated | Strong via native addon/FFI/WASM, but more packaging |
| Incremental/watch | **Yes**; measured ~0.4 s JS / ~0.5 s Lua target rebuilds | No compile needed for Lua source, but VM/source lifecycle remains | Must build/maintain generator/watch | Heavier native/WASM build loops |
| Debugging | **Good enough**; native JS + verified TS source-mapped Lua traceback | Lua stacks plus JS/WASM interop boundary | Generated-code debugging depends on custom source mapping | Hardest boundary: source language, FFI/ABI/WASM glue |
| Packaging burden | Build-time npm dependencies; runtime outputs are JS/Lua | Adds embedded VM/WASM to Studio | Adds an in-house generator/tool | Highest: binaries/WASM/glue per platform |
| CI burden | Generate both targets + parity tests | Test LuaJIT **and** embedded Lua 5.4 + JS bridge | Test generator and both outputs | Platform/ABI/WASM matrix |
| Android implications | **Good**; generated ordinary Lua travels with LÖVE, no new runtime binary | Does not help game runtime; Studio-side VM only | Generated Lua could be good | NDK/cross-compile/ABI burden |
| Future non-JS runtime | Weak-to-moderate; another backend/mechanism would be needed | Any host can embed Lua, but each gains a VM | Potentially strong for genuinely declarative semantics | **Strongest** multi-host story |
| Dependency health/maturity | External maintained compiler, but exact TS peer coupling was observed | External project; real Lua 5.4/WASM, but different VM from production | Repository owns the compiler burden | Mature native/WASM ecosystems, but many dependencies/toolchains |
| Generated-output policy | Deterministic outputs measured; regenerate in staging/CI, never hand-edit | No generated semantic output | Generated files must be treated as derived | Built artifacts are derived binaries |
| Incremental pure-Lua migration | **Good for isolated pure leaf modules** | Superficially easy source reuse, but Studio pays VM cost | Good only for small declarative leaves | Poor; each migrated function crosses native boundary/toolchain |

## Recommended production mechanism

Adopt a small **shared-semantics source class**, not a shared-engine architecture.

A module qualifies only when it can be described as a deterministic data transformation:

```text
plain data in -> deterministic plain data out
```

with no dependency on host runtime identity or lifecycle.

For qualifying modules:

1. author the semantic implementation once in a tightly restricted TypeScript subset;
2. compile ordinary JS for Studio/Node;
3. compile Lua with TypeScriptToLua's `JIT` target for LÖVE;
4. execute cross-target parity fixtures in CI, including adversarial host-language edge cases;
5. treat generated JS/Lua as derived artifacts, never as editable authority;
6. keep host adapters for filesystem, DOM, Electron, LÖVE APIs and runtime state outside the shared semantic file.

This reframes the repository principle as:

> one semantic authority does not require one execution host.

The compiler pipeline is allowed to have multiple execution artifacts because there remains only one authored algorithm.

### Restricted-source rules should be explicit

A production implementation should establish a small lint/review contract before migrating the second module. At minimum, shared-semantic TypeScript should avoid or explicitly gate constructs whose JS/Lua behavior differs:

- truthiness of numeric/string values; use explicit comparisons;
- `null`/`undefined` distinctions;
- sparse arrays or array holes;
- object-key iteration where order matters;
- reliance on stable `Array.sort`;
- JS prototype/dynamic-object tricks;
- async/promise ordering;
- host-specific number parsing unless grammar is explicitly specified;
- implicit coercion;
- host APIs.

Every numerical module should retain exact pinned cross-target samples rather than assuming compiler correctness is equivalent to application parity.

## Production migration order

### 1. Sprite timing/resolution

Migrate first.

A production issue/PR should:

- extract the pure key/filename/timing/resolution decision into the authored shared semantic module;
- have LÖVE provide its available-asset inventory through a tiny adapter;
- have Studio use the same generated JS directly for preview timing and pure resolution;
- remove both handwritten preview parsers from `widgets.js`;
- preserve the current runtime resolver as the reference during migration and compare every fixture against it;
- add edge fixtures for `fps=0`, malformed numeric values, whitespace, mixed `fps`/`speed`, duplicate token names/casing as currently supported, unresolved paths and directory precedence;
- decide explicitly whether malformed authored timing remains permissive runtime behavior or becomes validated authoring input. Do not change this accidentally as a side effect of moving languages.

Once parity is proven, pure timing/resolution should no longer need a cold LÖVE RPC. Runtime consultation remains appropriate for questions that genuinely depend on runtime state rather than this pure contract.

### 2. Vertex shading

Follow only after the first migration establishes the production build/parity conventions.

The production change should replace:

```text
engine/vertex_shading.lua
+
tools/editor/js/vertex-shading.js
```

as two authored algorithms with one shared source and generated host artifacts/adapters.

Do not leave the old Lua and JS implementations live beside the generated implementation. The entire point is to reduce authorities from two to one.

Retain all current pinned values and extend the lane to compare current/old implementation during the migration PR. After landing, the permanent test should compare generated JS and generated Lua against common golden fixtures or a golden-vector data file.

## Generated-output policy

The spike intentionally does not commit `generated/` output.

For production, the preferred policy is:

- author only the TypeScript semantic source;
- generate JavaScript/Lua as part of the existing staging/build flow;
- regenerate both in CI;
- run parity tests from regenerated artifacts;
- never allow manual edits to generated files.

If a direct repository-root `love .` developer path cannot consume staged/generated output without introducing more operational complexity than a checked-in artifact, committing generated Lua is acceptable as a pragmatic exception **only** if it has an unambiguous generated-file banner and CI regenerates then diffs it. Checked-in generated code must never become review-authoritative source.

The experiment's repeated identical generated-tree hash shows that a deterministic regen check is viable for these modules.

## Semantics that should not use this mechanism

The result is intentionally narrow. Do **not** migrate a module merely because it is written in Lua and Studio wants access to it.

Poor candidates include:

- LÖVE graphics, audio, input, window, filesystem or userdata behavior;
- DOM/Electron behavior;
- code whose semantics include process lifetime, runtime initialization or loaded game state;
- mutable global registries;
- gameplay systems whose authority is inseparable from runtime state without first factoring a genuinely pure function;
- global/stateful RNG streams where call order is semantic;
- coroutines, threads or async task ordering without a dedicated parity proof;
- Lua metatable behavior;
- code relying on `pairs` iteration order, sparse tables, `#` edge behavior or `nil` identity;
- JavaScript prototype/dynamic-key behavior;
- LuaJIT FFI/native data structures or integer/bit-level behavior unless specifically proven on every target;
- large engine subsystems with host-specific side effects.

Data that is naturally declarative—schemas, enums, static precedence tables, capabilities, command definitions—should remain declarative data and may use existing schema/code-generation patterns instead of being promoted into TypeScript algorithms.

## Android and future-runtime implications

The recommended mechanism adds no new game runtime on Android. The game receives generated ordinary Lua and continues to execute it through the LÖVE/LuaJIT environment it already ships with.

That is materially simpler than a native shared core, which would create Android NDK/ABI packaging work, or an embedded-Lua Studio approach, which solves the Studio host by adding a second Lua VM but does not simplify the game runtime.

TypeScriptToLua is not a universal future-runtime solution. It solves the **current two-host problem** well: JavaScript and Lua. If Thestra later gains a serious third execution runtime in another language, that is the point to reevaluate whether the pure semantic core needs a multi-target IR/DSL or native/WASM implementation. Prepaying that platform cost now would be speculative architecture.

## Repository hygiene and production-behavior proof

Final successful shared-semantics workflow:

```text
run 32183169248
job 95860732934
```

Result:

```text
Shared semantics spike: success
NODE PARITY OK
WASMOON PARITY OK
LOVE PARITY OK
```

Focused production contracts in the same run:

```text
node --test tools/editor/tests/test-map-vertex-shading.js
  5 passed, 0 failed

node tools/editor/test-sprite-timing-provenance.js
  sprite timing provenance contract: OK

git diff --check
  success
```

The experiment changes no production semantic module and no Studio/runtime call site.

## Bottom line

The spike does **not** justify a broad engine migration. It does justify replacing a small category of handwritten Lua/JavaScript mirrors and runtime RPCs with a single authored pure-semantic source.

**Use TypeScriptToLua for that category, with a restricted subset and mandatory dual-target parity tests.**

Start with sprite timing/resolution because it is small and because current Studio preview code still contains duplicate timing semantics. If the production integration remains clean, vertex shading is a strong second migration: it has already passed the exact numerical canary under the real LÖVE/LuaJIT runtime.

Do not use the mechanism for host APIs, stateful runtime authority, side-effect-heavy engine systems or code whose correctness depends on language quirks not explicitly parity-tested.
