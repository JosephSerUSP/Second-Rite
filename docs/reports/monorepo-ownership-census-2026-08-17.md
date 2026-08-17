# Monorepo ownership census and migration program — 2026-08-17

Status: current-main evidence refresh and implementation program for #382.

This report **continues** the accepted 2026-08-13 census from PR #383. It does not replace that dated report as historical evidence. The earlier branch `agent/382-monorepo-ownership-boundaries` is no longer present; PR #383 merged its durable design and census. This refresh was performed against current `main` at:

```text
084b881dc17a813a5512df9c22706cba5811b6d2
chore: remove accidental empty temp file
```

The #383 merge commit (`cd5f29b8138f7223622802e5acc8d97a66e2c1ef`) is 787 commits behind this snapshot. The repository has therefore changed too much for the old path/count evidence or its active-PR list to remain migration authority.

Current implementation truth remains `docs/ENGINE-STATE.md`, reviewed behavior remains `docs/SPEC.md`, and durable ownership intent remains `docs/design/monorepo-ownership-boundaries.md`.

## Owner direction now settled

The architecture decision that was still partly open in the earlier report is now settled for the foreseeable future:

- keep **one monorepo**;
- developer-facing repository identity should eventually return to **Hichaukitoden**, but **do not rename the GitHub repository in this migration**;
- **Thestra** is the reusable runtime;
- **Thestra Studio** is the editor/authoring application;
- **Second Gate** is the player-facing game;
- the in-repo Second Gate Project may use the developer-facing root name `projects/hichaukitoden-game/`;
- Second Gate must be an ordinary Thestra Project, not the container that owns runtime/Studio;
- repository splitting is deferred until concrete distribution, release, licensing, or maintenance pressure justifies it.

The conceptual target family remains:

```text
Hichaukitoden/
  runtime/
  defaults/ or current rtp/ family
  studio/
  projects/
    hichaukitoden-game/
  tools/
  tests/
  docs/
```

Literal folder names below the ownership roots are not canon. In particular, current `rtp/` is already a real, versioned default authored/resource layer; there is no architectural value in renaming it to `defaults/` merely to match a diagram.

## Executive result

The semantic architecture is substantially more ready for physical separation than it was on 2026-08-13:

1. **RTP/defaults are now concrete.** `rtp/revisions/**` exists and recent work decomposed reusable authored defaults from Second Gate policy.
2. **Ordinary in-repo Projects already exist.** `projects/labs/**` contains independent Projects such as `sol-game-01`, each with its own `data/` and `assets/`.
3. **Sparse external Project lifecycle exists.** New Project, pinned RTP resolution, Make Local, validation, Test Play and hermetic staging/export have all advanced past the old #385 gate.
4. **Source authored storage and compiled runtime data are now deliberately separated.** External Project staging compiles semantic runtime resources, and same-root Test Play uses a compiled semantic snapshot instead of consuming raw authored fragments directly.
5. **Neutral authored-storage tooling has left Studio-private ownership.** `tools/data/**` is now a shared tooling seam; `tools/editor/**` contains compatibility/consumer surfaces rather than being the only data authority.

But two physical ownership problems remain severe:

- the runtime-data exception inside Project-shaped `data/` has **grown from four files to eleven runtime/support paths**;
- repository root is still the implicit Second Gate Project for several launch/default paths, so game/runtime/Studio ownership is still physically collapsed even though external Project semantics are much stronger.

This makes the dependency order clearer than in the first report:

```text
#698 runtime support leaves Project-shaped data/
   |
   v
#699 semantic roots + copied-Second-Gate portability gate
   |
   +------------------+
   |                  |
   v                  v
#700 Second Gate      #701 explicit runtime/
Project move
   |
   +------------------+
          |
          v
     #702 explicit studio/
          |
          v
     #703 docs/reference/dev-root cleanup
```

#701 and #702 need the semantic-root contract from #699 but do not mechanically require every other physical move first. In practice, #700 should be prioritized once its active asset/content conflicts clear because every new root `data/` or `assets/` game-content branch increases its future conflict cost.

---

# 1. Current ownership census

## Repository/runtime entry layer

### `main.lua`

**Semantic owner:** Thestra runtime.

Current evidence: it is the LÖVE runtime entrypoint and immediately requires the data loader plus reusable `engine/**` and `presentation/**` modules. It belongs with the installed runtime, not with Second Gate Project data.

**Migration:** later moves under the explicit runtime root in #701.

### `engine/**`

**Semantic owner:** Thestra runtime.

This is reusable gameplay/session/Scene/Event/formula/resource/validation/runtime behavior. Recent additions since the earlier census include player-equivalent/controller/state/progression/event-animation/update-contract and other reusable runtime modules.

**Migration:** later moves wholesale under #701 after runtime data-support cleanup and semantic roots are explicit.

### `presentation/**`

**Semantic owner:** Thestra runtime presentation.

It is player-facing runtime presentation, not Studio chrome. Long-lived PR #257 directly touches this area, so its eventual root move is conflict-sensitive.

**Migration:** #701.

### root `conf.lua`

**Semantic owner:** currently mixed development-runtime configuration + Second Gate identity.

It contains CI/runtime error-handler behavior but also hardcodes LÖVE identity/title as `SecondRite` / `Second Rite`. It therefore cannot simply be called generic runtime-owned configuration.

**Required repair:** #699 must decide/materialize Project-owned release/development identity instead of carrying a hidden Second Gate default in installed tooling. #701 may then move the truly reusable runtime configuration portion.

---

# 2. Current `data/`: Project semantic data plus runtime implementation

## Authored Project data

**Semantic owner:** primarily the current root Second Gate Project, with explicit RTP/default composition where already implemented.

Current examples include:

- monolith authored JSON such as `system.json`, `items.json`, `skills.json`, `states.json`, `roles.json`, `terms.json`, `shops.json`, `progression.json`, etc.;
- fragment/registry roots such as `maps/**`, `units/**`, `flows/**`, `scenes/**`, `tilesets/**`;
- newly added resources such as `animationControllers.json` and `models.json`.

The important current distinction is no longer "JSON = Project". Some effective authored values are composed from Project + pinned RTP/defaults, but the Project's authored overlay/policy still belongs to the Project.

After #698, the physical `data/` namespace can finally become truthful: authored source data in a Project, or compiled semantic data in a staged player.

## Runtime/support files still buried in `data/`

**Semantic owner:** Thestra runtime, currently in the wrong physical namespace.

Current `tools/export/runtime-manifest.json` lists eleven special runtime/support paths under `data/`:

```text
authored_storage.lua
authored_storage_resolved.lua
authored_storage_manifest.json
semantic_resources.lua
json.lua
loader.lua
rtp_authored_defaults.lua
vendor/lunajson/decoder.lua
vendor/lunajson/encoder.lua
vendor/lunajson/LICENSE
vendor/lunajson/README.md
```

This is the clearest first physical migration slice. The exporter currently has to say, in effect, "Project data belongs to the Project except for these eleven installed-runtime files inside it." That exception should disappear rather than grow.

Known consumers include:

- `main.lua` requiring `data.loader`;
- internal `data.*` Lua requires;
- `data/authored_storage.lua` hardcoding `data/authored_storage_manifest.json`;
- `tools/data/authored-storage-physical.js` deriving the same manifest from root `data/`;
- `tools/export/runtime-manifest.json`;
- `tools/export/export-game.js` copying `dataRuntimeFiles` from the runtime install into staged `data/`;
- `tools/export/runtime-data-compiler.js` pruning/replacing source-storage runtime files during compilation;
- `tools/export/runtime-data-snapshot.js` doing corresponding source/snapshot cleanup.

**Migration:** #698.

---

# 3. Project/default boundary is now substantially real

## `rtp/**`

**Semantic owner:** Thestra default authored/resource layer.

This path did not exist as a mature concrete boundary in the first census. Current `rtp/revisions/**` and resolver work make it the actual implementation of the conceptual `defaults/` family.

Do not rename it merely for diagram symmetry. Its important properties are versioned identity, explicit resolution, deterministic materialization, and no silent fallback to Second Gate content.

## `projects/**`

**Semantic owner:** in-repo independent Thestra Projects/labs.

Current `projects/labs/**` proves that the repository already accepts multiple Project roots. `projects/labs/sol-game-01/` visibly has its own `data/` and `assets/`, which is strong current evidence that `projects/hichaukitoden-game/` is an extension of an established Project model rather than a speculative new root ontology.

Current root Second Gate is the outlier: it remains a Project only because repository root is still treated as its default Project root.

**Migration:** #700 makes Second Gate a sibling Project rather than the checkout container.

---

# 4. Export, staging and Test Play boundary after recent merges

The current materialization contract is much stronger than the 2026-08-13 report recorded.

## External Project

`tools/editor/project-play.js` stages an external Project through the installed runtime using the shared runtime exporter/compiler path. Runtime implementation comes from the install; Project authored data/assets come from the Project; RTP/defaults are resolved/materialized; semantic runtime data is compiled.

This is the ownership shape #382 wanted.

## Same-root current Second Gate

Same-root Test Play is no longer raw-data direct. It creates an ignored Project-relative compiled snapshot under the Project, materializes the semantic runtime data there, and launches with `THESTRA_RUNTIME_DATA_ROOT` pointing to that compiled snapshot while runtime/assets stay direct.

That is an optimization, not a separate semantic model.

After Second Gate moves to `projects/hichaukitoden-game/`, `installRoot === projectRoot` will intentionally become false. The current code will therefore naturally choose the staged/external-style path unless a later explicit in-repo optimization is added. Correct ownership is more important than preserving root equality.

## Runtime data compiler

`tools/export/runtime-data-compiler.js` now makes the source/semantic/compiled boundary explicit for fragment-backed resources. It emits ordinary semantic JSON runtime resources and provenance, then removes source-only storage representations from staged players.

This means #698 can move source-side runtime support code out of Project `data/` without undoing the semantic compiler. The target should be cleaner:

```text
runtime-owned code/support
        +
resolved Project/default authored sources
        |
        v
compiled staged data/*.json
```

rather than runtime code being copied back into staged `data/` as a special exception.

## Remaining export identity leak

`tools/export/release-conf.lua` is shared exporter-owned physically but hardcodes:

```text
t.identity = "SecondRite"
t.window.title = "Second Rite"
```

and export copies it as the distributed `conf.lua`. Root developer `conf.lua` has the same identity/title.

That is no longer acceptable as an invisible installed default once arbitrary Projects are a supported product boundary. #699 must make release/development identity an explicit Project/runtime input and prove a non-Second-Gate Project is not exported under Second Gate identity.

---

# 5. Studio ownership after recent merges

## root `main.js`

**Semantic owner:** Thestra Studio host.

It imports Studio identity/window/IPC/project/watcher/runtime-bridge modules from `tools/editor/**`, owns Electron windows, and selects a Project through `--project` / environment state.

Its current `STUDIO_ROOT` and Project bootstrap still reflect repository-root installation layout.

## root `package.json` / `package-lock.json`

**Semantic owner:** currently primarily Studio/development application package metadata, with shared repository scripts mixed in.

They should move with/after the Studio application only after scripts that are truly repository-wide are separated or can resolve the explicit Studio root. Do not force shared tools into Studio just to preserve relative package scripts.

## `tools/editor/**`

**Semantic owner:** Thestra Studio application/editor implementation and Studio-only resources, except where files are now compatibility consumers of neutral shared services.

The current area is much richer than in the first census: Project lifecycle/New Project, watcher, multi-window surfaces, runtime bridge, Playwright and other host/editor infrastructure now live here.

## `tools/data/**`

**Semantic owner:** shared cross-boundary authored-data tooling.

This is a significant improvement since the first report. It should remain shared when Studio later moves; Studio may consume it, but Studio should not own/copy it.

## `tools/export/**`

**Semantic owner:** shared build/materialization/export tooling.

It crosses runtime/default/Project boundaries deliberately and should remain outside Studio/runtime shipped ownership.

**Studio migration:** #702, after #699 and after active Studio PRs #692/#693 are resolved.

---

# 6. Assets and production-source ownership

## root `assets/**`

**Current exporter owner:** Project. The runtime manifest's `projectDirectories` includes `assets`, so the current Second Gate Project/export boundary treats the whole root as Project assets.

Current main also contains substantial `assets/authoring/**` source material, including Blender item sources added after the first census. This introduces a packaging-quality distinction that should not be confused with semantic ownership:

- an authoring `.blend` may still be **Second Gate Project production source**;
- it does not need to be a **runtime player asset** merely because it is under the Project's source tree.

#700 should move the Project-owned asset tree coherently unless implementation evidence first classifies a subtree as Studio/default/shared-production owned. A later exporter/package cleanup may exclude non-player authoring sources from distribution without moving their semantic ownership out of the Project.

Do not block #700 on inventing a universal asset library. Do not promote Second Gate assets into RTP merely because they are useful examples.

---

# 7. Shared verification, workflow and developer roots

## `tests/**`

**Semantic owner:** shared verification plus owner-specific tests. Keep repository-level unless an individual test is a shipped product resource (normally it is not).

## `.github/workflows/**`

**Semantic owner:** shared repository automation.

Many new ownership-sensitive workflows were added after the first census, including authored defaults/storage, lab Project validation, Project lifecycle/watcher, sparse Project, player membrane, runtime-data boundary, Studio host/Playwright, Blender/model pipelines, etc. Physical moves must update these path consumers rather than moving workflows into product roots.

## `tools/golden/**`, `userPerform/**`

**Semantic owner:** shared verification / developer-owner convenience.

`userPerform/**` still contains G1-G6 wrappers and related convenience scripts. It is not a product owner and should be retaxonomized later under #703 rather than mixed into the Project move.

## `inspiration/**`

**Semantic owner:** retained research/reference, not runtime/Project default authority.

Current main still contains `inspiration/assets`, `inspiration/data`, and `inspiration/doc`. Their names resemble product paths but they are reference material and must not be picked up by Project/default discovery merely because of those names.

## `phase4-v2-preview/**`

**Semantic owner:** historical/generated visual review evidence.

Retain, archive, or delete based on evidence, but do not treat it as runtime or Project ownership.

## old `campaign-gen/` and root `experiments/`

Neither exists on this current-main snapshot. Do not create migration work to move paths that are already gone. Active PR #599/#614 may introduce large `experiments/**` evidence roots; their retention/archive policy should be decided as those PRs are resolved.

---

# 8. Documentation ownership

The durable rule remains correct: document location expresses authority/subject, not delivery state.

Current main still has:

- repository authorities such as `docs/SPEC.md`, `docs/ENGINE-STATE.md`, `docs/AUTHORING-STATE.md`;
- mixed-domain architecture/design under `docs/design/**`;
- explicitly game-facing `docs/game design/**`;
- dated evidence under `docs/reports/**`;
- agentic, asset-pipeline, commercial, and other topical groups.

Do not make docs taxonomy a prerequisite for product-root correctness. After runtime/Project/Studio roots settle, #703 can retaxonomize docs/reference/convenience paths once, with #677 reconciled first.

---

# 9. Active PR conflict census — current snapshot

Open PR state was refreshed after the implementation issues were created.

| PR | Current area | Conflict with ownership moves |
|---|---|---|
| #697 branch-hygiene safety | `.github/workflows/branch-hygiene.yml`, `tools/branch-hygiene/**` | Low. Independent tooling; should not block #698/#699/#700. |
| #693 animated sprite paint readiness | `tools/editor/js/widgets.js`, G6 harness | High for #702 Studio move; low for #698/#700. |
| #692 lighting parity | Studio test + `studio-host.yml` + runtime tests/fixture | Moderate/high for #702; low for Project move. |
| #614 128×128 town characters | `data/maps/1.json`, `assets/authoring/characters/**`, `assets/sprites/**`, proposed experiment evidence | **Direct high conflict with #700.** Resolve/rebase before Project move. |
| #677 Stratum revisit docs | `docs/game design/**` | Direct conflict only with #703 docs taxonomy. |
| #599 24×24 character pipeline | `assets/authoring/characters/**`, Blender tools, proposed experiment evidence | **Direct high conflict with #700 assets and later #703 experiment cleanup.** |
| #257 LÖVE 12 shadow | `presentation/retro_mesh_shader.lua`, workflows/reports and extensive G5 evidence | **Direct high conflict with #701 runtime/presentation move.** It is deliberately long-lived and should not block #698/#699/#700. |

The most time-sensitive physical move is #700 once #698/#699 and #614/#599 are resolved. New Second Gate work naturally keeps editing root `data/**` and `assets/**`; each such branch increases the eventual rename/rebase surface.

The Studio move #702 should wait for #692/#693 rather than forcing currently active editor work through a path-only rebase.

The runtime move #701 should explicitly accommodate #257's long-lived shadow workflow instead of using it as a reason to postpone every other ownership repair.

---

# 10. Migration slices

## Slice A — #698: extract runtime data support from Project-shaped `data/`

**Exact paths:** the eleven `dataRuntimeFiles` listed above, moving into a coherent runtime-owned namespace (preferably under existing `engine/**` so a later `runtime/` move can lift it wholesale).

**Owner before:** runtime implementation physically embedded in Project-shaped data.

**Owner after:** Thestra runtime; Project `data/` becomes authored/compiled semantic data only.

**Prerequisite:** none of the later physical root moves; preserve landed #390/#392/#667 semantics.

**Hardcoded consumers:** `main.lua`; internal `data.*` requires; authored-storage manifest lookup; runtime manifest; exporter; compiler/snapshot pruning/provider placement; `tools/data/authored-storage-physical.js`; conformance workflows/tests.

**Export/runtime implications:** eliminate `dataRuntimeFiles`; runtime supplies its loader/provider/support coherently; compiled staged `data/` remains semantic JSON/provenance. Preserve `THESTRA_RUNTIME_DATA_ROOT` as semantic-data selection.

**Studio implications:** neutral `tools/data/**` follows the runtime-owned schema/support manifest rather than opened-Project `data/`; no UX redesign.

**Tests:** runtime-data boundary, authored-storage conformance, source validate/unit/save, same-root snapshot Test Play, sparse/external Project stage/export, relative gates.

**Likely conflicts:** low on current open PR set.

**G5/G6:** no reference recapture expected; path-only harness updates if necessary.

**Rollback:** one reviewable move + consumers, revert atomically; no permanent mirrors.

**Status:** **safe to start from current main**, after rechecking newly opened PRs.

---

## Slice B — #699: centralize semantic roots + prove copied Second Gate portability

**Exact primary paths:** `tools/editor/project-root.js`, `project-play.js`, lifecycle/bootstrap paths in root `main.js`, `tools/export/export-game.js`, runtime snapshot/RTP root consumers, package/launcher/workflow/test defaults, plus `conf.lua` / `tools/export/release-conf.lua` identity boundary.

**Owner before:** root semantics distributed across Studio/export/shared tooling, often relying on repository root == Project root.

**Owner after:** root selection is an explicit cross-boundary contract; Project/runtime/RTP/Studio/stage roots are semantic inputs.

**Prerequisite:** #698, so copied Project data contains no runtime implementation.

**Hardcoded consumers:** all root derivations/defaults above plus tests/workflows/launchers.

**Export/runtime implications:** keep one materialization pipeline; prove non-Second-Gate Project release identity does not silently become `SecondRite`; correctness cannot depend on installRoot/projectRoot equality.

**Studio implications:** explicit opened Project root converges with existing `--project` lifecycle; no Studio relocation yet.

**Tests:** permanent test copies current Second Gate Project-owned `data` + `assets` to temp external root, opens/validates/Test Plays/stages/exports through installed Thestra with no checkout game-content reads. Later repoint it directly at `projects/hichaukitoden-game/`.

**Likely conflicts:** low/moderate; active Studio work is adjacent but does not currently own core root-provider files.

**G5/G6:** no reference recapture.

**Rollback:** bounded root-contract/portability PR; revert rather than aliases.

**Status:** can follow #698 immediately.

---

## Slice C — #700: move Second Gate into `projects/hichaukitoden-game/`

**Exact paths:** root Project-owned `data/**` after #698 and root Project-owned `assets/**` -> `projects/hichaukitoden-game/data/**` and `projects/hichaukitoden-game/assets/**`.

**Owner before:** Second Gate Project content at repository root.

**Owner after:** ordinary in-repo Project sibling to `projects/labs/**`.

**Prerequisite:** #698 + #699 + resolve/rebase #614/#599.

**Hardcoded consumers:** Studio default Project root, exporter defaults, Project watcher/lifecycle/server, asset/model/Blender tools, generator/lab tools, package/launch scripts, `userPerform/**`, workflows, golden/tests/docs with root `data/`/`assets/` assumptions.

**Export/runtime implications:** in-repo Project now follows installed-runtime + Project staging shape; same-root direct optimization no longer applies by accidental equality. Export remains hermetic.

**Studio implications:** repository development explicitly selects the Project; generic Studio chrome remains independent of its assets.

**Tests:** copied-Project portability gate now copies this directory directly; lab Projects continue to pass; watcher/Test Play/export gates pass; G1-G4/unit/save/relative gates.

**Likely conflicts:** **highest and increasing** because #614/#599 and future game-content branches touch the exact paths.

**G5/G6:** harness paths may move; no canonical recapture merely for relocation.

**Rollback:** single bounded history-preserving move, no root mirrors.

**Status:** not safe until #698/#699 and active game-asset PR resolution; then should be prioritized.

---

## Slice D — #701: consolidate Thestra runtime under explicit `runtime/`

**Exact paths:** `main.lua`, `engine/**`, `presentation/**`, and the runtime support namespace created by #698; `conf.lua` only after its Second Gate identity portion is resolved by #699.

**Owner before:** reusable runtime at repository root.

**Owner after:** explicit Thestra runtime root.

**Prerequisite:** #698 + #699; explicit plan for #257.

**Hardcoded consumers:** exporter/runtime manifest, Studio runtime bridge, root launchers, `userPerform/**`, workflows, tests, golden harnesses, tools importing runtime modules, docs.

**Export/runtime implications:** repository runtime root may be `runtime/`, while exported player may still materialize the conventional LÖVE root (`main.lua`, `engine/`, `presentation/`, etc.). Repository organization and shipped archive organization need not be identical.

**Studio implications:** receive runtimeRoot explicitly; do not move Studio here.

**Tests:** source runtime, external/lab Project validation/Test Play/export, all runtime/unit/save/golden-relative gates.

**Likely conflicts:** high with #257 presentation/G5 shadow work.

**G5/G6:** no recapture; path updates only.

**Rollback:** history-preserving move + mechanical path updates, revert atomically.

**Status:** semantically ready after #698/#699 but schedule around #257/relevant runtime PRs.

---

## Slice E — #702: consolidate Thestra Studio under explicit `studio/`

**Exact paths:** root `main.js`; Studio package metadata where appropriate; `tools/editor/**` and its Studio-only `Assets/**` -> explicit Studio app root. Keep `tools/data/**`, `tools/export/**`, golden/build/asset-production tools shared.

**Owner before:** Studio split between root app/package and generic tools subtree.

**Owner after:** explicit Studio application root with shared dependencies remaining shared.

**Prerequisite:** #699; resolve/rebase #692/#693; preferably after the higher-pressure Project move.

**Hardcoded consumers:** Electron relative requires/preload/icons, package scripts, Studio root env, workflows, Playwright/tests, G6 harness, root launchers/docs.

**Export/runtime implications:** none of Studio enters player export; runtime remains independent.

**Studio implications:** preserve project lifecycle, multi-window surfaces, watcher, runtime bridge, installed/native host identity.

**Tests:** Studio host, Playwright, watcher/lifecycle/surface tests, external/lab/in-repo Project open/Test Play.

**Likely conflicts:** high until #692/#693 land.

**G5/G6:** G6 launch paths move, canonical imagery does not.

**Rollback:** one move PR, no forwarding copies.

**Status:** defer until current Studio PRs settle.

---

## Slice F — #703: docs/reference/developer-root retaxonomy

**Exact paths:** `docs/design/**`, `docs/game design/**`, reports/topical docs as evidence warrants; `inspiration/**`; `phase4-v2-preview/**`; `userPerform/**`; loose reference/convenience roots discovered during implementation.

**Owner before:** mixed authority/reference/developer convenience at historically evolved paths.

**Owner after:** clear game/runtime/Studio/cross-boundary/report/archive/developer-tooling taxonomy.

**Prerequisite:** preferably #700/#701/#702 so paths are documented once; resolve #677; account for #599/#614 experiment evidence if those branches land.

**Hardcoded consumers:** doc links, workflows, report generators, scripts, AGENTS/instructions.

**Export/runtime implications:** none; reference/history must remain outside player export.

**Studio implications:** none beyond links/scripts.

**Tests:** link/path checks, script/workflow resolution; no semantic runtime changes.

**Likely conflicts:** docs #677; experiment evidence #599/#614.

**G5/G6:** no recapture.

**Rollback:** history-preserving path moves, revert; no duplicate documentation authority.

**Status:** intentionally late/independent cleanup.

---

# 11. What is safe now

### Safe to migrate now

The first physical ownership repair is **#698 runtime data-support extraction**. It has a coherent semantic owner, a finite known path set, and no direct current open-PR conflict in those paths.

The current semantic compiler/staging architecture makes this safer now than it was when #382 was first reported: source data representation is already treated as a build-boundary concern, so moving loader/storage implementation out of Project data does not require redesigning Project semantics.

### Safe to prepare immediately after #698

#699 can centralize root semantics and install the copied-Second-Gate portability gate without physically moving the game. That test is the safety proof for #700.

### Not safe to mass-move yet

Do **not** move root `data/**` + `assets/**` to the Project while #614/#599 are unresolved and before #698/#699 land.

Do **not** move `tools/editor/**` while #692/#693 are active.

Do **not** move `presentation/**` casually around the long-lived #257 shadow branch; plan its rebase/evidence paths explicitly.

---

# 12. Top three migration slices

1. **#698 — extract runtime support from Project `data/`.**
   - Smallest coherent physical ownership repair.
   - Removes the exporter's worst ownership exception.
   - Low current conflict.

2. **#699 — explicit semantic roots + Second Gate portability gate.**
   - Converts the intended architecture into a mechanical proof before large moves.
   - Also catches the still-hidden Second Gate `conf.lua`/release identity leak.

3. **#700 — move Second Gate to `projects/hichaukitoden-game/`.**
   - The defining ownership move.
   - Should follow the two safety prerequisites and current asset-PR reconciliation.
   - Once ready, it should be prioritized because conflict cost increases with every new root game-content branch.

#701/#702 are important, but they are lower urgency than making Second Gate stop being the checkout root. The repository can temporarily have explicit Project ownership while runtime/Studio remain root-level, provided #699 makes their semantic roots explicit.

---

# 13. Acid-test completion criterion

The migration program should not declare the Second Gate Project boundary complete merely because `git mv` succeeds.

The permanent proof is:

1. locate `projects/hichaukitoden-game/` as one ordinary Project;
2. copy that Project directory to a temporary location outside the checkout;
3. use an installed/current Thestra runtime + pinned/default resources to open and validate it;
4. open it in Studio without Studio chrome borrowing checkout Second Gate assets;
5. Test Play it through the same staging/materialization contract used by external Projects;
6. export a hermetic player;
7. run/validate that exported player without the source checkout;
8. prove no runtime module came from Project `data/`, no Project game content came from Studio/runtime roots, and no exported identity was silently inherited from Second Gate-specific installed tooling.

When that passes, the repository structure finally reflects the architecture already established semantically:

> Second Gate is a Project **using Thestra**, not the directory that contains Thestra.

---

## Implementation issues created from this refresh

- #698 — Extract Thestra runtime data support from Project-shaped `data/`
- #699 — Centralize semantic roots and prove Second Gate Project portability
- #700 — Move Second Gate into `projects/hichaukitoden-game` as an ordinary Project
- #701 — Consolidate Thestra runtime under an explicit runtime root
- #702 — Consolidate Thestra Studio under an explicit studio root
- #703 — Retaxonomize repository docs, reference material, and developer convenience roots

These issues are deliberately dependency-sized. They should not be recombined into one overnight move.

Agent-Signature:
  platform: ChatGPT Web
  model: GPT-5.6 Sol
  role: current-main ownership refresh / migration planning
  issue: "#382"
  base: 084b881dc17a813a5512df9c22706cba5811b6d2
