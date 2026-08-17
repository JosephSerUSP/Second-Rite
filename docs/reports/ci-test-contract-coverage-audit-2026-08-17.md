# CI / test contract coverage audit — 2026-08-17

Issue: #724  
Audited tree: `main` at `34ebfba5872b00f02d0f20697de643095b346f1c`.

This is an audit/design report only. It does not refactor workflows or product code. Open PR #728 changes several runtime-data workflow paths; those edits are in-flight proposals, not landed truth here. PR #723 changes Studio test aggregation but no workflow. The branch-only LÖVE 12 laboratory in #257 is not one of current main's workflows.

## Executive finding

Verification is strong. Ownership is historically uneven.

`verify.yml` is already the unconditional repository baseline: repository hygiene, Lua fail-fast, authored-storage/tooling checks, G1, the registered Lua unit graph, save/load, G2, G3, G4, advisory reachability and tracked-tree cleanliness. Live GitHub rulesets confirm that only status context **`gates (Windows)`** is branch-protection-required; other workflows are valuable hosted evidence but not required contexts.

The main topology risks are:

- repeated LOVE 11.5/Mesa environment policy with multiple YAML owners, plus floating distro LOVE in `player-membrane.yml`;
- path filters that describe historical files although the protected property spans runtime/Project/Studio owners;
- exact tests repeated by historical workflow families;
- two confirmed declared verification surfaces not hosted (`test:authoring-state`/currentness and `test:three-vendor`);
- a documented engine→presentation rule that has strong partial ratchets but no complete engine-wide import scan.

## Failure semantics

- **Required/blocking:** live `verify-gates` ruleset strictly requires `gates (Windows)` on the default branch.
- **Hosted red evidence:** other Actions jobs fail normally but are not live required contexts.
- **Advisory:** `reachability` is `continue-on-error`; Relative G5/G6 answers whether a candidate changed repeat-stable hosted pixels, not whether the result is correct.
- **Owner-bound:** Absolute G5/G6 are owner-signed renderer/browser/font correctness fingerprints and remain outside hosted correctness CI.

## Workflow inventory — all 19 current files

| Workflow | Trigger/scope | Runner/jobs/bootstrap | Direct evidence | Contract / risk |
|---|---|---|---|---|
| `archive-adapter.yml` — Archive adapter | PR filtered to archive/export/package files; manual | Ubuntu + Windows; Node 22; `npm ci --ignore-scripts` | both `test:archive`; Windows `export-game.test.js` | Cross-OS archive/export adapter. Filter mostly bounded; OS repetition intentional. |
| `authored-defaults.yml` — authored defaults | PR + push main, filtered to defaults/RTP/export/editor-default files; manual | Windows, 10m; runner Node | syntax; authored/progression-default tests; RTP resolver; export test; clean tree | Default/RTP materialization. Mixed component + architecture claim; medium filter risk. |
| `authored-storage-conformance.yml` | PR + push main filtered to storage tools/manifest; manual | Ubuntu, 5m; runner Node/Python | JS storage test; Python storage test; py_compile | Cross-language physical-storage conformance. JS duplicates `verify`; architecture portion should be unconditional. |
| `blender-item-source.yml` | PR + push main filtered to item/Blender pipeline; manual | Ubuntu, 20m; Python + headless Blender 5.0.1 | Python OBJ/MTL tests; real saved `.blend` fixture; production compiler `--check` | Genuinely component-local item source pipeline. #671 correctly moved global backup hygiene elsewhere. |
| `blender-map-export.yml` | PR + selected pushes, filtered to Blender/map bridges; manual | Windows, 30m, concurrency; hash-pinned LOVE 11.5/Mesa/Blender | Node/Python host tests; runtime Map 8 export; Blender reopen/structure check; artifact 7d | Map→structured Blender integration. Component-local core; runtime-authority dependency broader than filter. |
| `branch-hygiene.yml` | daily schedule; manual; classifier-only PR filter | Ubuntu verify 10m + publish 5m; Python 3.12 | deterministic classifier test; live remote census; artifact 14d; schedule/manual publishes issue | Cadence/owner audit. Filter is appropriate because schedule covers changing remote state. |
| `encounter-lab.yml` | every PR + push main + manual | Windows, 15m, concurrency; hash-pinned LOVE/Mesa | Lua fail-fast; root G1; Python synthetic + real engine self-tests | Deterministic Map 2 encounter seam. Root G1/setup are duplicated prerequisites. |
| `lab-project-validation.yml` | PR mainly `projects/labs/**`, `conf.lua`, `tools/labs/**`; manual | Ubuntu discovery + Windows Project matrix, 15m; hash-pinned LOVE/Mesa | fail-closed probe; real stage; validate; preview capture; boot smoke; review evidence | Excellent executable Project evidence, **unsafe filter**: shared runtime/presentation/staging can break it. |
| `model-import.yml` | PR + push main filtered to importer/model consumer/package files; manual | Ubuntu+Windows Node matrix; Windows real-LÖVE job, 10/12m; Node 24; hash-pinned LOVE | importer tests; deterministic double import; real runtime bundle consumer | Strong source→bundle→runtime contract. Cross-OS repetition intentional; mostly bounded filter. |
| `player-membrane.yml` | every PR; manual | Ubuntu, 15m; `apt install love xvfb` | temporary harness runs `tests/player_membrane_spec.lua` | Dedicated player membrane; environment-policy outlier because LOVE is distro/floating. |
| `project-lifecycle.yml` | PR + push main filtered to Project/Electron/generator files; manual | Windows, 15m; `npm ci --ignore-scripts` | `test:project-lifecycle`; generator tests; create/fork/generate; Electron root smoke; clean tree | Project independence/lifecycle. **Unsafe architecture filter** and overlaps sparse workflow. |
| `project-watcher.yml` | PR filtered to watcher/resource-sync files; manual | Ubuntu + Windows; Node 24/npm | both `test:project-watcher`; Windows `test:studio-session` | Cross-OS watcher/session evidence. Mostly subsystem-local; leaf tests overlap host aggregate. |
| `relative-golden-ab.yml` — Relative visual A/B | PR + push main + manual refs/gate | Windows prepare/tooling/G5/G6; G5/G6 60m; concurrency; hash-pinned LOVE/Mesa | golden tool py_compile/unittests; base-A/base-B/candidate G5/G6; decoded RGBA compare; artifacts 14d | **Relative/advisory regression evidence only.** Base repeat is mandatory, not waste. |
| `runtime-data-boundary.yml` | PR + push main filtered to selected data/compiler/export/bridge files; manual | Windows, 15m; Node 24; hash-pinned LOVE/Mesa | syntax; compiler/snapshot/source-storage census/Project-play/runtime-bridge tests; clean tree | Source→semantic→compiled/Test Play boundary. **Unsafe architecture filter**. #728 is actively changing this area. |
| `shim-provenance.yml` | all pushes + all PRs + manual | Windows, 5m | PowerShell parse; clean-checkout checker; stale-shim self-test | Strong unconditional native-shim provenance invariant. |
| `sparse-project.yml` | PR + push main filtered to sparse/default/export/storage files; manual | Windows, 15m; hash-pinned LOVE/Mesa | fail-fast; root G1; `test:project-lifecycle`; fresh `sparse-project-smoke.js`; clean tree | Fresh neutral Project create→stage→validate. **Unsafe filter** and duplicate lifecycle/G1 work. |
| `studio-host.yml` | every PR + push main + manual | Windows, 20m, concurrency; Node 24/npm | icon checks; broad boundary tests; `test:studio-host`; host currentness; disposable-host/tree-clean checks | Strong native Studio integration and broad boundary owner. |
| `studio-playwright.yml` | PR filtered to selected Studio host/surface files; manual | Windows, 15m; Node 24/npm | real Electron `test:studio-playwright`; then full `test:studio-host` | Strong real EditorSurface behavior, **unsafe hand-maintained filter**; host suite is exact heavy duplicate. |
| `verify.yml` — verify | every PR + push main + manual | Ubuntu hygiene 5m; Windows syntax 5m; Windows gates 30m; concurrency; hash-pinned LOVE/Mesa | repo hygiene; fail-fast; authored-storage JS; npm boundary tests; G1; unit; save; G2; G3; G4; advisory reachability; clean tree | Unconditional repository baseline. `gates (Windows)` is the only required context. Absolute G5/G6 explicitly excluded. |

No dead/missing workflow invocation was confirmed. Earlier suspicion that `player_membrane_spec.lua` was missing was disproved by the current tests tree.

## Test / verification inventory

| Entry point/family | Level | Local owner / meaning | Hosted execution |
|---|---|---|---|
| `tools/ci/test-love-boot-fail-fast.ps1` | static/syntax + negative control | malformed runtime must fail promptly | direct: `verify`, encounter lab, sparse Project |
| G1 `lovec . validate` | semantic/conformance | authored IDs/commands/formulas/targeting/Scene rules | direct required lane in `verify`; root/staged duplicates elsewhere |
| `lovec . unittest` | unit + conformance | registered Lua behavior graph | direct required lane in `verify` |
| `tests/test_suite_registration.lua` | repository invariant | every tracked `tests/test_*.lua` must be reachable from declared roots/transitive suite imports | direct through `unittest`; prevents ordinary Lua orphan suites |
| Lua `tests/test_*.lua` families | unit/integration/boundary | battle/damage/traits; Events/Scenes; save-sensitive state; geometry/cache; items/models/icons; progression; presentation surfaces; maps/transfers; formulas; runtime boundaries | direct through registered `unittest` graph, not filename accident |
| `tests/test_runtime_boundaries.lua` | boundary/conformance | runtime cannot require tools/tests; scene_host and geometry upward-dependency ratchets; explicit scene context | direct through `unittest`; broad engine→presentation claim is only partially covered |
| `lovec . savetest` | deterministic integration | save/load round trip | direct required `verify` lane |
| G2 `tools/golden/check.ps1` | deterministic golden | battle trace identity | direct required `verify` lane |
| G3 `check-ui.ps1` | deterministic golden | UI/Scene event trace identity | direct required `verify` lane |
| G4 `check-state.ps1` | repository invariant | `ENGINE-STATE.md` equals executable state | direct required `verify` lane |
| `lovec . reachability` | semantic/advisory | valid but unreachable content | direct `verify`, intentionally nonblocking |
| Absolute G5 / G6 | owner-bound visual correctness | owner-fingerprint runtime / Studio pixels | local owner only by policy |
| `tests/test_gate_record.py`, `test_relative_gate_tools.py` | harness unit/conformance | recorder/comparator and repeat-control semantics | direct Relative A/B tooling job |
| Relative G5/G6 | visual regression | same-host candidate change on repeat-stable pixels | direct Relative A/B; advisory meaning |
| JS + Python authored-storage tests | boundary/conformance | physical authored-storage agreement | direct conformance; JS duplicated in `verify` |
| runtime compiler/snapshot/source-storage census tests | boundary/integration | authored source→semantic→compiled and Test Play/transient preview | direct `runtime-data-boundary` |
| `test:project-lifecycle` | Project integration | create/open/launch/default/sparse Project behavior | direct lifecycle + duplicated sparse workflow |
| `sparse-project-smoke.js` | executable Project/runtime | fresh Project stage/validate | direct sparse workflow |
| lab Project matrix | executable Project/runtime + review evidence | discover→stage→validate→preview→boot each lab Project | direct when filtered workflow triggers |
| encounter synthetic/engine self-tests | deterministic runtime | encounter assumptions + real engine seam | direct encounter workflow |
| `test:studio-host` / host check | Studio integration | native host, surface/session/shutdown/data boot/editor-scene behavior | direct Studio host; full repeat in Playwright |
| `test:studio-playwright` | Studio integration | real Electron EditorSurface lifecycle | direct Playwright workflow |
| `test:project-watcher`, `test:studio-session` | Studio integration | watcher invalidation/session transactions | direct watcher workflow; overlapping host leaves |
| model importer tests + real LÖVE consumer | asset/import integration | source→deterministic compiled bundle→runtime | direct model workflow |
| archive tests | packaging boundary | archive adapter/export behavior | direct Linux+Windows archive workflow |
| Blender item/map tests | asset pipeline | `.blend` source/runtime export and runtime Map→Blender round trip | direct Blender workflows |
| shim provenance | repository/native invariant | absent is legal; stale native artifact is detected | direct unconditional shim workflow |
| branch-hygiene tests/census | repository operations | conservative remote-branch deletion evidence | direct classifier PRs + schedule/manual |
| global tracked `.blendN` scan | repository invariant | workstation backup files cannot be committed anywhere | direct unconditional `verify` (#671 precedent) |
| `test:authoring-state` + `authoring-state:check` | architecture/generated inventory | census schema/debt/determinism and committed-output currentness | **not hosted**; #729 |
| `test:three-vendor` | Studio dependency conformance | retained Three browser modules are closed under relative imports | **not directly hosted**; #730 |
| `tools/check-spec-ci.js` | owner/infrastructure evidence | authenticated live rulesets + `verify.yml` agree with SPEC §5.3 | intentionally opt-in; source explicitly says neither local gate nor CI |

## Contract coverage matrix

| Promise | Evidence | Status |
|---|---|---|
| Authored data valid | G1 | **strong/direct** |
| Runtime semantics valid | registered unit graph | **strong/direct** |
| Persistence round-trips | save + targeted save units | **strong/direct** |
| Battle deterministic | G2 | **strong/direct** |
| UI traces deterministic | G3 | **strong/direct** |
| Executable state doc current | G4 | **strong/direct** |
| Repository hygiene applies globally | unconditional tracked-file scan | **strong/direct** |
| New Lua tests cannot silently orphan | suite-registration invariant | **strong/direct** |
| Runtime cannot depend on dev-only tools/tests | runtime-boundary suite + export tests | **strong/direct** |
| Engine never requires presentation | scene_host + geometry ratchets | **partial**; no full engine scan, #731 |
| Authored source→semantic→compiled agrees | compiler/snapshot/census tests | **strong test; unsafe trigger**, #726 |
| Project root/staging independence | project-root/play/export + sparse smoke | **strong but duplicated; filter risk** |
| Fresh Project stays sparse | lifecycle + sparse smoke | **direct; duplicated/filter risk** |
| Lab Projects run independently | stage/validate/preview/boot matrix | **excellent evidence; unsafe filter** |
| Real Studio host works | host suite/currentness | **strong/direct; duplicated in Playwright** |
| Real EditorSurface works | Playwright/Electron | **strong test; unsafe filter** |
| Watcher/session behavior | Linux+Windows watcher/session | **strong/cross-OS** |
| Model bundle contract | importer matrix + real runtime consumer | **strong** |
| Blender source/export contracts | item + Map export workflows | **strong pipeline evidence** |
| Native shim provenance | checker + negative control | **strong/unconditional** |
| Hosted runtime visual change | Relative G5 | **relative regression only** |
| Hosted Studio visual change | Relative G6 | **relative regression only** |
| Runtime visual correctness | Absolute G5 | **owner-bound by design** |
| Studio visual correctness | Absolute G6 | **owner-bound by design** |
| Authoring census valid/current | declared census tests/check | **gap**, #729 |
| Three retained browser surface import-closed | `test:three-vendor` | **gap/directly ungated**, #730 |
| Live GitHub rulesets match documented infrastructure | `check-spec-ci.js` | **intentional owner/manual evidence** |

## G5/G6: absolute is not relative

**Absolute G5/G6** compare against committed owner-signed fingerprints tied to renderer/driver or browser/font environment. They are correctness claims. Recapture is owner-signed and must not become a hosted shortcut.

**Relative G5/G6** capture base A, base B, then candidate on one hosted environment. Unstable base-repeat frames are named/excluded. They answer only “did candidate rendering change relative to base?” A green relative run cannot certify correctness; an intentional visual change can correctly produce red relative evidence.

## Hosted gaps and incidental coverage

Confirmed currently unhosted verification:

- `npm run test:authoring-state` and `npm run authoring-state:check` — #729.
- `npm run test:three-vendor` — #730. G6 materializes Three and consumers may fail later, but that is incidental evidence, not the purpose-built import-closure assertion.

Confirmed **not** gaps:

- golden recorder/comparator tests are run directly by Relative A/B;
- ordinary `tests/test_*.lua` cannot silently exist without registration because `test_suite_registration.lua` is gated;
- `check-spec-ci.js` is explicitly authenticated owner/infrastructure evidence and intentionally not CI.

Missing architecture conformance: repository policy says engine never requires presentation, but current runtime-boundary scanning covers specific ratchets rather than every ordinary engine module. #731 owns the complete conformance check.

## Path-filter false-negative analysis

| Filtered workflow | Is the protected property actually local? |
|---|---|
| archive adapter | **mostly yes** — adapter/export inputs are bounded; retain OS matrix |
| authored defaults | **mixed** — resolver local, materialization/ownership broader |
| authored storage conformance | **mixed** — language/tool parity local, storage ownership architectural |
| Blender item source | **yes** — component pipeline; global backup invariant correctly lives in `verify` |
| Blender map export | **mostly** — Blender tool local, real runtime-authority dependency broader |
| branch hygiene | **yes for PR classifier changes**; schedule covers changing remote state |
| lab Project validation | **no** — shared runtime/presentation/staging changes can break Projects without triggering it |
| model import | **mostly** — importer/consumer owners explicit; shared parser/runtime seam should be documented |
| Project lifecycle | **no for architecture claims** — defaults/staging/export/Electron ownership spans filter |
| Project watcher | **mostly** — subsystem-local; keep repo invariants elsewhere |
| runtime data boundary | **no** — source/semantic/compiled ownership is repository architecture |
| sparse Project | **no** — stage/validate consumes runtime/presentation/export/defaults outside filter |
| Studio Playwright | **no** — actual EditorSurface lifecycle spans far more Studio/backend files than selected list |

Follow-up #726 owns this repair. The rule is: **repository invariant ⇒ unconditional CI; genuinely bounded component contract ⇒ path filtering may be valid.**

## Duplication / bootstrap ownership

### Accidental divergence risk

LOVE/Mesa is the clearest case. `verify`, encounter, runtime-data, sparse, labs, Blender Map and Relative A/B independently encode LOVE 11.5 + Mesa 26.1.6 hashes/software-renderer mechanics; model import independently pins the same LOVE archive; player membrane uses distro LOVE. Version/hash/architecture/software-renderer policy is architectural behavior, not mere YAML boilerplate. Centralize its repository owner under #725 while preserving OS-specific mechanics and Relative A/B's exact same-environment control.

### Exact/overlapping execution

- authored-storage JS: `verify` + conformance — accidental duplicate ownership once invariant vs language parity is separated;
- export/RTP tests recur in baseline/default/archive/Studio contexts — mixed; retain genuinely distinct integration contexts;
- `test:project-lifecycle`: lifecycle + sparse — accidental duplicate execution;
- root G1: baseline + encounter + sparse — baseline canonical; staged-product validation remains meaningful because it tests a different physical product;
- full `test:studio-host`: Studio host + serial repeat in Playwright — valid safety intent, accidental topology;
- watcher/session leaves also live inside broad host aggregation — diagnostic overlap;
- model/archive Linux+Windows — intentional portability redundancy;
- Relative base-A/base-B — mandatory nondeterminism control;
- branch-hygiene verify/publish split — intentional evidence/side-effect separation.

Repeated `npm ci` is generally harmless job isolation. Node version is less coherent: some workflows pin 24, archive pins 22, some use runner Node. Make version explicit when it is part of evidence; do not centralize only for cosmetic DRYness.

## Recommended target topology

### 1. Repository Verification

Unconditional parallel jobs for repository hygiene, Lua fail-fast, G1/unit/save/G2/G3/G4, advisory reachability, architecture-wide authored/runtime ownership, authoring census (#729), full engine→presentation conformance (#731), and tree cleanliness. Preserve the required status contract deliberately during migration.

### 2. Runtime / Project Contracts

Parallel jobs for Project lifecycle/staging/export, sparse Project proof, runtime-data compiler/snapshot/Test Play/bridge, lab Projects and distinct executable labs. Broad integration contracts should be unconditional unless dependency triggering is mechanically derived.

### 3. Thestra Studio

Parallel native host, watcher/session portability, Playwright/Electron, editor/boundary suites and Three vendor closure (#730). Playwright should depend on/sit beside native-host evidence rather than rerun the entire host suite serially.

### 4. Asset / Import Pipelines

Keep genuinely bounded Model import, Blender item and Blender Map pipelines path-filterable. These have the clearest semantic source/consumer owners.

### 5. Visual Regression

Keep Relative G5/G6 plus their tooling tests, base-repeat controls and artifacts. Preserve advisory meaning. Absolute G5/G6 remain owner-bound outside hosted correctness CI.

### Cadence-specific audit

Keep branch-hygiene schedule/manual publication separate: remote state and issue publication are operational cadence, not a sixth product CI subsystem.

## Migration order

1. Re-evaluate runtime-data paths after in-flight #728/#698; do not encode yesterday's roots.
2. Centralize runtime bootstrap semantics (#725).
3. Close trigger/coverage gaps without deleting current owners (#726, #729, #730, #731).
4. Confirm surviving owners and preserve/migrate the live required `gates (Windows)` context deliberately.
5. Consolidate historical workflow families only then (#727), retaining OS portability, staged-product evidence, schedules and Relative base controls.
6. Re-audit after #382 physical ownership materially changes roots; future filters should follow semantic owners rather than filenames.

## Follow-up issues

- #725 — Centralize pinned LOVE/Mesa CI bootstrap ownership
- #726 — Move architecture-wide CI invariants out of path-filtered workflows
- #727 — Consolidate duplicated historical CI workflow families by contract
- #729 — Host authoring-state census verification in CI
- #730 — Host retained Three vendor-surface contract in CI
- #731 — Enforce the full engine-to-presentation dependency boundary

The useful conclusion is not that 19 workflows are “too many.” It is that the repository now has a concrete map of **which promise is proved by which executable evidence, where that evidence runs, which evidence is owner-bound or advisory, and which current workflow boundaries are implementation history rather than architecture**.