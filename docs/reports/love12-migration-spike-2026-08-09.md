# LÖVE 12 migration spike — 2026-08-09

**Status:** recommendation complete  
**Issue:** #246  
**Scope:** runtime/tooling migration feasibility only; no runtime cutover, golden recapture, or Android packaging implementation

## 1. Decision

**Keep Second Rite on LÖVE 11.5 for production until LÖVE 12.0 has an official stable release, then migrate promptly rather than waiting for a game-content milestone.**

This is a timing recommendation, not a compatibility rejection. A pinned LÖVE 12 development build already boots Second Rite, passes the nonvisual gates, exposes the external-project mount primitive the editor/runtime boundary wants, and keeps LuaJIT FFI available. The migration looks bounded and worthwhile.

Do **not** block external-project Test Play/Preview on that upstream release. Proceed with the staged LÖVE 11.5 route tracked by #247. That route has value beyond compatibility because Test Play can exercise the same runtime manifest the exporter ships. After the production runtime moves to stable LÖVE 12, interactive Test Play/Preview can use direct external mounting while export/release staging remains the packaging authority.

Android packaging should remain a separate workstream. Current upstream LÖVE builds demonstrate an APK/AAB path, but Android is not a reason to make an unreleased development runtime Second Rite's production baseline.

The main migration risk is now sharply localized: **G5/game-renderer output changes materially under LÖVE 12. G6/the editor is almost entirely stable.** That makes the golden risk real, but reviewable rather than mysterious.

## 2. Evidence gathered

The spike compared the production runtime against a pinned upstream development build on the same Windows GitHub Actions runner and the same Mesa software-OpenGL stack.

| Runtime | Build used |
|---|---|
| LÖVE 11.5 | official `11.5` Windows x64 release |
| LÖVE 12 development | upstream commit `853f1cad4bb65d63f02dbcd3fa31b0c622d3abbc`, Actions run `31261258544`, Windows artifact `9022947942` (built 2026-08-08) |

The exploratory workflows existed only on the spike branch. The broad compatibility run was Second Rite Actions run `31344818821`; the corrected repeat-controlled RGBA comparison was run `31345806414`. Neither workflow is part of the proposed production change.

No golden reference was recaptured.

### 2.1 External-project mounting

The current LÖVE 12 development build exposes `love.filesystem.mountFullPath`. The spike mounted a directory outside the checked-out game source and successfully read a sentinel file through the mounted path.

Observed result:

```text
LÖVE 11.5: mountFullPath=false
LÖVE 12:   mountFullPath=true
             mount=true
             external=true
```

This validates the architectural premise behind #246: stable LÖVE 12 should let the runtime consume an external project directly instead of copying it into a location LÖVE 11.5 can see.

It does **not** justify waiting for LÖVE 12. #247's staging route is useful now and independently useful as an export-parity test path.

### 2.2 LuaJIT FFI / Effekseer precondition

`require("ffi")` succeeds under both tested runtimes. This removes the most basic concern around `presentation/effekseer.lua`, which depends on LuaJIT FFI.

That is not a complete Effekseer validation. The native shim and its ABI/runtime dependencies still need a representative Windows smoke test or rebuild against the final stable LÖVE 12 distribution before cutover.

### 2.3 Nonvisual gates

The current LÖVE 12 development build passed the same core suite without source changes:

| Check | LÖVE 11.5 | LÖVE 12 dev |
|---|---:|---:|
| G1 validator | PASS | PASS |
| unit tests | PASS | PASS |
| save tests | PASS | PASS |
| G2 battle golden traces | PASS | PASS |
| G3 UI golden traces | PASS | PASS |
| G4 engine-state consistency | PASS | PASS |

This is strong evidence that the authored-data contract, core game logic, save path, and headless tooling are not presently migration blockers.

### 2.4 Renderer/API compatibility

The current renderer boots and exercises Second Rite's existing mesh/shader paths under LÖVE 12, but the development runtime emits deprecation warnings around legacy graphics interfaces.

The migration should explicitly clean these paths instead of relying on compatibility aliases:

- legacy mesh attribute/format conventions in `presentation/mesh.lua`;
- named custom shader vertex inputs / layout handling in `presentation/retro_mesh_shader.lua`;
- stencil/render-state calls used by presentation code;
- canvas/depth-stencil semantics where the LÖVE 12 API has changed.

The important distinction is **deprecated, not presently broken** on the pinned development build.

### 2.5 Golden visual output — corrected controlled result

The first exploratory probe compared encoded PNG streams and was too coarse to answer whether differences were renderer pixels, PNG representation, or capture nondeterminism. A second run therefore added two controls:

1. capture LÖVE 11.5 twice in the same environment to establish repeatability;
2. decode every capture to canonical RGBA and compare pixel bytes, not just PNG containers.

The corrected result is:

| Capture set | Same-runtime repeat | 11.5 → 12 RGBA differences |
|---|---:|---:|
| G5 Classic, all harness frames | 0 / 144 | **88 / 144** |
| G5 Wide, all harness frames | 0 / 144 | **89 / 144** |
| G6 editor | 1 / 38 | **2 / 38** |

For G5, the result is unambiguous: the 11.5 repeat is pixel-identical, while LÖVE 12 changes real rendered pixels in 88 Classic frames and 89 Wide frames. The changed-pixel counts were 3,832,427 of 8,847,360 sampled Classic pixels and 6,939,807 of 14,722,560 sampled Wide pixels. This is a broad renderer-level shift, not a handful of PNG metadata differences.

The curated Wide golden set is 34 frames. **31 of those 34 paths are among the pixel-different 11.5→12 captures**; the two `special/location-art` frames and `menu/options/03-after-escape.png` remain pixel-identical in this controlled comparison.

G6 tells a different story. Its 11.5 repeat already changes `map-editor/map-properties.png` by 922 pixels, so that frame is existing harness nondeterminism and cannot be attributed to LÖVE 12. The cross-runtime comparison changes two frames:

- `map-editor/map-properties.png` — also changes in the 11.5 repeat; tracked separately as #253;
- `engine/fog.png` — not present in the 11.5 repeat delta, therefore the one clean editor-side LÖVE 12 signal from this run.

**Interpretation:** the golden risk is substantial for the game renderer but small for the editor. It remains an owner-sensitive migration because G5 is the only gate that sees the world view, and a runtime-wide pixel shift must be inspected before any reference changes. The evidence does **not** justify treating all G6 frames as migration churn.

No reference should be recaptured as the first response. At migration time:

1. reproduce the paired 11.5/stable-12 capture on the owner machine/environment;
2. inspect representative G5 differences and determine whether the shift is an acceptable engine change or a regression caused by deprecated API behavior;
3. fix regressions before changing references;
4. recapture only intentional output changes, with explicit owner sign-off.

### 2.6 CI and exported runtime packaging

The exporter currently enumerates the LÖVE 11-era Windows runtime bundle, including SDL2-era/native DLL assumptions. The tested LÖVE 12 development artifact ships a materially different native bundle, including SDL3 and the newer MSVC runtime family.

Accordingly, migration work must update both:

- `.github/workflows/verify.yml` runtime acquisition/pinning; and
- `tools/export/export-game.js` runtime file discovery/copying.

The exporter should preferably validate/copy the pinned runtime distribution as a coherent bundle rather than encode a historical DLL list that will age independently of LÖVE.

### 2.7 Android path

The current upstream LÖVE CI produces Android APK and AAB artifacts, and the official Android project is Gradle-based. That is enough to say LÖVE 12 is a sensible foundation for Second Rite's eventual Android packaging path.

It is **not** evidence that Second Rite's Android exporter/device matrix is already solved. APK/AAB authoring, signing, package metadata, device validation, touch/safe-inset behavior, lifecycle, storage, audio, and store requirements remain separate implementation work.

## 3. Risk assessment

| Area | Current evidence | Migration risk |
|---|---|---|
| Core logic/data/save | G1–G4 + unit/save pass | Low |
| External project mounting | real external directory mounted/read | Low after stable release |
| LuaJIT FFI availability | `ffi` loads | Low |
| Effekseer native shim | ABI not fully exercised in spike | Medium |
| Renderer API | works, but emits LÖVE 12 deprecations | Medium |
| G5/game presentation | 88/144 Classic and 89/144 Wide frames have real pixel deltas | **High / owner-sensitive** |
| G6/editor presentation | one clean runtime-attributable frame; one pre-existing flaky frame | Low–Medium |
| Windows CI runtime | development artifact works | Medium until stable artifact exists |
| Exported Windows runtime | bundle shape changes, SDL3 present | Medium |
| Android packaging | upstream path exists; Second Rite path unimplemented | Separate scope |
| Upstream stability | 12.0 not yet an official stable release | High timing risk |

## 4. Costed migration plan

The cost below is relative engineering/review weight rather than a calendar promise. Android packaging is excluded.

| Work | Relative cost | Why |
|---|---|---|
| Pin stable 12.0 in CI and tooling | Small | one runtime source/digest, existing CI install seam |
| Update Windows exporter/runtime bundle | Small–Medium | concrete DLL-set change plus packaging tests |
| Migrate deprecated mesh/shader/render-state APIs | Medium | concentrated renderer code, but visually sensitive |
| Add direct external-project runtime mounting | Medium | project-root/bootstrap seam plus fail-loud tests |
| Effekseer native shim smoke/rebuild | Small–Medium | FFI contract looks intact; native dependency still needs proof |
| G5 classification and renderer fixes | **Large / dominant** | broad real pixel shift across world/UI-backed game frames |
| G6 classification | Small | one clean runtime-dependent frame in the controlled run |
| Owner-approved golden recapture, if needed | Review-sensitive | only after true differences are classified |

The migration is therefore not primarily a logic/data rewrite. It is a **renderer verification + runtime packaging migration**, with G5 review as the dominant uncertainty.

## 5. Migration order and gates

When an official stable LÖVE 12.0 release exists:

1. **Pin the stable runtime.** Use an official release archive plus digest. Update CI/runtime acquisition so every later observation is reproducible.
2. **Update exporter runtime handling.** Teach the Windows exporter the stable 12 bundle before treating any build as shippable.
3. **Resolve renderer/API deprecations.** Make explicit LÖVE 12 mesh/shader/render-state changes rather than carrying compatibility warnings indefinitely.
4. **Run the nonvisual suite.** G1, unit, save, G2, G3 and G4 must all remain green.
5. **Validate Effekseer.** Exercise representative effects through the FFI/native shim and rebuild native glue if the stable runtime/toolchain requires it.
6. **Add direct project mounting.** Use `mountFullPath` for interactive external-project runtime access, while retaining exporter staging as the packaging/release boundary.
7. **Run paired G5 captures.** Same owner machine/renderer, 11.5 vs stable 12. Classify real pixel changes; do not recapture yet.
8. **Run paired G6 captures.** Treat #253's map-properties flake separately; classify only repeat-controlled runtime deltas.
9. **Owner visual sign-off.** Fix unintended regressions. Only then update reference captures for intentional runtime output changes.
10. **Cut over production runtime.** Switch documented/default tooling to stable 12 once the gates and export smoke are green.
11. **Treat Android separately.** Add packaging/device gates without coupling them to the desktop cutover.

## 6. Recommendation by requested decision

### Migrate now / after milestone / stay 11.5?

**Stay on 11.5 until stable LÖVE 12.0 exists; then migrate as an infrastructure task rather than waiting for a Second Rite content milestone.**

The compatibility evidence is encouraging enough that the migration should be planned, not feared. The reason not to cut over today is upstream release stability plus a real G5 renderer delta—not evidence that Second Rite fundamentally depends on 11.5.

### Should external-project preview wait for LÖVE 12?

**No. Implement #247 on LÖVE 11.5 now.**

The staging route solves a present-day editor architecture requirement and gives Test Play an export-parity property worth keeping. After stable 12, interactive launches can prefer direct mounting without deleting the exporter staging mechanism itself.

## 7. Follow-up boundary

- #251 owns the eventual stable-runtime migration.
- #247 owns external-project Test Play/Preview on the current 11.5 production runtime.
- #253 owns the G6 `map-properties` repeatability defect discovered by the controlled comparison.

The stable-runtime migration should be blocked on an **official LÖVE 12.0 stable release**, not on speculative dates or a moving upstream development build.
