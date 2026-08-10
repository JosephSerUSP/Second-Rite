# LÖVE 12 migration spike — 2026-08-09

**Status:** recommendation complete  
**Issue:** #246  
**Scope:** runtime/tooling migration feasibility only; no runtime cutover, golden recapture, or Android packaging implementation

## 1. Decision

**Keep Second Rite on LÖVE 11.5 for production until LÖVE 12.0 has an official stable release.**

Do **not** block external-project Test Play/Preview on that migration. Proceed with the staged LÖVE 11.5 approach tracked by #247, then simplify/replace the staging bridge with direct external mounting after the runtime eventually moves to stable LÖVE 12.

Android packaging should remain a separate workstream. LÖVE 12 is strategically attractive for the eventual Android path, but Android is not a reason to put the production runtime on an unreleased development branch.

This is a timing recommendation, not a compatibility rejection. The current LÖVE 12 development build is substantially compatible with Second Rite; the remaining risk is concentrated in moving renderer semantics, exact visual output, native/runtime packaging, and the fact that 12.0 is still unreleased.

## 2. Evidence gathered

The spike compared the production runtime against a pinned upstream development build on the same Windows GitHub Actions runner and the same Mesa software-OpenGL stack.

| Runtime | Build used |
|---|---|
| LÖVE 11.5 | official `11.5` Windows x64 release |
| LÖVE 12 development | upstream commit `853f1cad4bb65d63f02dbcd3fa31b0c622d3abbc`, Actions run `31261258544`, Windows artifact `9022947942` (built 2026-08-08) |

The temporary probe workflow existed only on the spike branch and was removed before this report was prepared for landing. Its successful run was Second Rite Actions run `31344818821`.

### 2.1 External-project mounting

The current LÖVE 12 development build exposes `love.filesystem.mountFullPath`. The spike mounted a directory outside the checked-out game source and successfully read a sentinel file through the mounted path.

Observed result:

```text
LÖVE 11.5: mountFullPath=false
LÖVE 12:   mountFullPath=true
             mount=true
             external=true
```

This validates the architectural premise behind #246: stable LÖVE 12 should eventually let the editor/runtime consume an external project directly instead of copying/staging it into an allowed LÖVE 11.5 location.

It does **not** justify waiting for LÖVE 12. The bridge in #247 is bounded, removable compatibility work and lets the editor/project-independence architecture advance while 12.0 stabilizes.

### 2.2 LuaJIT FFI / Effekseer precondition

`require("ffi")` succeeds under both tested runtimes. This removes the most basic concern around `presentation/effekseer.lua`, which depends on LuaJIT FFI.

That is not a complete Effekseer validation. The native shim and its ABI/runtime dependencies still need a smoke test or rebuild against the final stable LÖVE 12 distribution before cutover.

### 2.3 Nonvisual gates

The current LÖVE 12 development build passed the same core suite without source changes:

| Check | LÖVE 11.5 | LÖVE 12 dev |
|---|---:|---:|
| G1 validator | PASS | PASS |
| unit tests | PASS | PASS |
| save tests | PASS | PASS |
| G2 headless smoke | PASS | PASS |
| G3 UI smoke | PASS | PASS |
| G4 state smoke | PASS | PASS |

This is strong evidence that the authored-data contract, core game logic, save path, and headless tooling are not presently migration blockers.

### 2.4 Renderer/API compatibility

The current renderer boots and exercises Second Rite's existing mesh/shader paths under LÖVE 12, but the development runtime emits deprecation warnings around legacy graphics interfaces.

The migration should explicitly clean these paths instead of relying on compatibility aliases:

- legacy mesh attribute/format conventions in `presentation/mesh.lua`;
- named custom shader vertex inputs / layout handling in `presentation/retro_mesh_shader.lua`;
- stencil/render-state calls used by presentation code;
- canvas/depth-stencil semantics where the LÖVE 12 API has changed.

The important distinction is **deprecated, not presently broken** on the pinned development build.

### 2.5 Golden visual output

Paired captures were produced under 11.5 and the pinned LÖVE 12 development build on the same hosted machine and renderer stack. No canonical reference capture was modified.

| Surface | Captures | Byte-identical PNGs |
|---|---:|---:|
| G5 classic | 144 | 0 |
| G5 wide | 34 | 0 |
| G6 editor | 38 | 0 |

The surface crop invariant passed under both runtimes.

**Interpretation:** the paired test hashes complete PNG byte streams. Therefore this proves that the current captures are not byte-identical; it does **not** prove that every pixel changed or that every difference is visually significant. G5 itself also uses exact PNG-byte hashing, however, so the existing references cannot simply be assumed to carry across a runtime cutover.

The migration must therefore treat G5/G6 as an owner-reviewed visual change:

1. capture 11.5 and stable 12 on the same owner machine/environment;
2. classify visual differences before changing any reference;
3. fix regressions or document intentional runtime differences;
4. recapture references only after explicit owner sign-off.

Never use a golden recapture as the first response to the runtime diff.

### 2.6 CI and exported runtime packaging

The exporter currently enumerates the LÖVE 11-era Windows runtime bundle, including SDL2-era/native DLL assumptions. The tested LÖVE 12 development artifact ships a materially different native bundle, including SDL3.

Accordingly, migration work must update both:

- `.github/workflows/verify.yml` runtime acquisition/pinning; and
- `tools/export/export-game.js` runtime file discovery/copying.

The exporter should preferably stop encoding a fragile historical DLL list and copy/validate the runtime distribution as a coherent pinned bundle.

## 3. Risk assessment

| Area | Current evidence | Migration risk |
|---|---|---|
| Core logic/data/save | G1–G4 + unit/save pass | Low |
| External project mounting | real external directory mounted/read | Low after stable release |
| LuaJIT FFI availability | `ffi` loads | Low |
| Effekseer native shim | ABI not fully exercised in spike | Medium |
| Renderer API | works with development-build deprecations | Medium |
| Golden presentation | all paired PNG byte streams differ | High / owner-sensitive |
| Windows CI runtime | development artifact works | Medium until stable artifact exists |
| Exported Windows runtime | bundle shape changes, SDL3 present | Medium |
| Android packaging | intentionally not implemented/tested here | Unknown / separate scope |
| Upstream stability | 12.0 not yet an official stable release | High timing risk |

## 4. Costed migration plan

Estimate excludes Android packaging and assumes the eventual stable 12.0 API remains close to the development build tested here.

| Work | Estimate |
|---|---:|
| Pin stable 12.0 in CI + update exporter/runtime bundle | 0.5–1 day |
| Renderer/API cleanup (mesh attrs, shader inputs, stencil/canvas semantics) | 0.5–1 day |
| External-project direct mount + remove/simplify 11.5 staging bridge | ~0.5 day |
| Effekseer native shim smoke/rebuild | 0.25–0.5 day |
| G5/G6 paired capture, classification, fixes and owner review | 0.5–1.5 days |
| **Expected migration total** | **~2–4 developer days** |

Android should be estimated and implemented separately; a first packaging/toolchain pass is plausibly another **1–2+ days**, but #246 did not gather enough device/toolchain evidence to treat that as a commitment.

## 5. Migration order and gates

When an official stable LÖVE 12.0 release exists:

1. **Pin the stable runtime.** Use an official release archive plus digest. Update CI and exporter runtime handling first so every later observation is reproducible.
2. **Resolve renderer/API deprecations.** Make explicit LÖVE 12 mesh/shader/render-state changes rather than carrying compatibility warnings indefinitely.
3. **Run the nonvisual suite.** G1, unit, save, G2, G3 and G4 must all be green before visual references are considered.
4. **Validate Effekseer.** Exercise representative effects through the FFI/native shim and rebuild the shim if the stable runtime/toolchain requires it.
5. **Run paired G5 captures.** Same owner machine, same renderer, 11.5 vs stable 12. Classify differences; do not recapture yet.
6. **Run paired G6 captures.** Same host/browser/editor setup. Classify differences.
7. **Owner visual sign-off.** Fix unintended regressions. Only then update reference captures for intentional changes.
8. **Cut over production runtime.** Switch documented/default tooling to 12 and simplify #247's staging bridge into direct `mountFullPath` project access.
9. **Treat Android separately.** Add packaging/device gates without coupling them to the desktop runtime cutover.

## 6. Recommendation by requested decision

### Migrate now / after milestone / stay 11.5?

**Stay on 11.5 now; migrate after the upstream stable 12.0 release rather than at a Second Rite content milestone.**

The compatibility evidence is encouraging enough that a future migration looks practical and bounded. It is not compelling enough to make an unreleased runtime the production baseline while Second Rite's visual/editor surface is actively evolving.

### Should external-project preview wait for LÖVE 12?

**No. Implement #247 on LÖVE 11.5 now.**

The staging bridge solves a real present-day editor architecture requirement, can be tested independently, and has a clear deletion/simplification path after LÖVE 12. Waiting would couple project independence to an upstream release date Second Rite does not control.

## 7. Follow-up boundary

The eventual stable-runtime migration should be tracked as its own implementation issue and should be blocked on an **official LÖVE 12.0 stable release**, not on speculative dates or development-build behavior.

That implementation issue should inherit the gates and owner-sign-off sequence above. #247 remains the current external-project preview path in the meantime.
