# Monorepo ownership boundaries

Status: architecture recommendation for #382. This document defines semantic ownership and a migration sequence; it does **not** claim that the target physical layout has already landed.

## 1. Decision frame

The repository currently co-locates four different things: the Second Gate game Project, the reusable Thestra runtime, Thestra Studio, and the development/verification workspace. That co-location is historical convenience, not an ownership model.

The governing semantic decisions are already stronger than the physical tree:

- **Project is the independently runnable/authored game identity.** Routes, stories and chapters inside one game are ordinary Project logic. The removed Campaign-root mechanism is not an alternative Project ontology. Future package/dependency composition is a separate design problem.
- Studio has an **install root** and an **opened Project root**. An external Project contributes its authored `data/` and Project assets while installed runtime code comes from the Thestra installation.
- Test Play/export share one materialization contract: installed runtime + one Project. Same-root development is currently a no-copy optimization, not evidence that Project and runtime are one owner.
- Runtime must not depend on Studio/editor implementation.

Therefore the reorganization must make the in-repo Second Gate game an ordinary Project rather than inventing a privileged repository-project format.

## 2. Current ownership census

Ownership below is semantic, derived from consumers and packaging behavior rather than directory names.

| Current path / subtree | Semantic owner | Disposition / evidence |
| --- | --- | --- |
| `data/**/*.json` and fragment directories | **Second Gate Project** today | Authored game/database content. `Project/data` is the current minimum Project identity and the editor writes these resources. Some JSON such as `engine.json` describes reusable command/schema vocabulary, but it is currently authored/overridable Project data; JSON extension alone does not decide ownership. Preserve that semantic distinction until a future shared-package/default model explicitly changes it. |
| `data/authored_storage.lua`, `data/json.lua`, `data/loader.lua`, `data/authored_storage_manifest.json` | **Thestra runtime** | Concrete mixed-ownership defect. Export copies these from the installation through `dataRuntimeFiles`, then overlays Project JSON. They must leave the Project data namespace before the Project directory moves. |
| `assets/**` | **Mostly Second Gate Project; some unresolved/library candidates** | The exporter takes `assets` from `projectDir`, proving current packaging semantics are Project-owned. Do not reclassify generic-looking textures/icons/models as runtime merely by appearance. Asset-production/source libraries that are intentionally reusable should be separated only after reference/consumer audit. |
| `engine/**` | **Thestra runtime** | Reusable gameplay/runtime semantics. Owner-supervised Battle files remain subject to existing policy; a path move alone must not become a behavioral edit. |
| `presentation/**` | **Thestra runtime** | Player-facing reusable presentation consumed by the LÖVE runtime. It is installation/runtime material, not Studio chrome. |
| root `main.lua` | **Thestra runtime** | Runtime entry point and an explicit exporter `rootFiles` member. |
| root `conf.lua` | **mixed development/runtime configuration** | Development launch config belongs with runtime development; export already substitutes `tools/export/release-conf.lua`. Decide the runtime config seam before relocating it rather than treating the filename as Project content. |
| root `main.js`, `package.json`, `package-lock.json`, `runEditor.bat`, Studio launcher/icon host inputs | **Thestra Studio** | Electron host/application and normal Studio development launch. PR #364 is active in this area and should land or be explicitly superseded before a physical Studio move. |
| `tools/editor/**` | **Thestra Studio** | Editor UI/server/project-root and Test Play frontend. Project-specific previews legitimately read the opened Project; editor chrome must remain installation-owned. |
| `tools/export/**` | **shared dev/verification tooling with a cross-boundary contract** | Exporter is not runtime code and not Project content. It owns the canonical materialization boundary between installed runtime and Project. |
| `tools/golden/**`, `.github/workflows/**`, `tests/**` | **shared dev/verification tooling** | Gates and CI validate several owners. Keep project-independent; tests/fixtures should state which boundary they exercise rather than moving wholesale under a product owner. |
| `tools/delegate/**`, `.github/ISSUE_TEMPLATE/**`, agent/bootstrap policy | **shared development infrastructure** | Repository workflow, not shipped runtime/Project/Studio. |
| `tools/effekseer/**` | **runtime build/dependency tooling** | Builds/verifies native support consumed by runtime/export, but the build tooling itself is development-owned. The produced DLL is generated/disposable installation/build material. |
| `tools/asset-gen/**`, `tools/asset-production/**`, `tools/blender/**`, `tools/asset-language/**`, loose asset-generation scripts | **Project authoring library / shared production tooling, mixed** | These create assets rather than run the game. Some recipes may be Second Gate-specific, some reusable. Audit inputs/outputs before moving; do not infer ownership from `tools/`. |
| `tools/campaign-gen/**` | **historical/deprecated tooling pending #369** | Its Campaign vocabulary is no longer runtime ontology. #369 owns migration of useful generator behavior toward Project semantics; do not organize the monorepo around this stale name. |
| `tools/analysis/**`, experiment/lab directories | **shared development/research tooling** | Non-runtime analysis. Individual labs can be game-specific while the harness is reusable; keep evidence/results explicit. |
| `docs/ENGINE-STATE.md`, `docs/SPEC.md` | **cross-boundary current-state/spec authorities** | Keep at repository architecture level while one SPEC spans runtime/editor/contracts. They should not be buried inside the Second Gate Project. |
| `docs/game design/**`, `docs/walkthrough/**`, game-specific commercial/design material | **Second Gate Project documentation** | Game/content intent, walkthrough and product-specific design. It may live adjacent to, but need not ship inside, the runnable Project root. |
| `docs/design/**` | **mixed** | Contains both reusable runtime/Studio architecture and Second Gate mechanics/content. Taxonomize semantically before or alongside physical doc moves; do not treat this directory as one owner. |
| `docs/reports/**`, `docs/archive/**` | **historical/research/reference** | Reports are dated evidence; archive is explicitly non-authoritative. Preserve provenance rather than promoting either to current architecture. |
| `docs/asset-pipeline/**` | **Project authoring library / shared production documentation, mixed** | Classify by the pipeline/tool it documents; not automatically Second Gate content. |
| `inspiration/**` | **historical/research/reference, primarily Second Gate** | Creative/reference material, not runtime dependency. |
| `phase4-v2-preview/**` | **historical/research/reference unless a live consumer proves otherwise** | Name and role indicate retained preview/evidence rather than production ownership; verify consumers before any deletion. |
| `tmp/**`, `dist/**`, screenshot actual/output trees, generated host/runtime caches | **generated/disposable** | Should remain ignored and outside durable ownership roots unless a specific artifact is deliberately checked in as evidence. |
| `userPerform/**` | **shared developer convenience tooling** | Local wrappers around canonical gates/workflows, not product/runtime content. |
| `.census-bootstrap/**` | **generated/bootstrap residue; unresolved retention need** | Not a product owner. Determine whether any current workflow consumes it; if not, remove in a bounded hygiene issue rather than carrying it into a target architecture. |
| `.claude/**`, `CLAUDE.md`, `AGENTS.md` | **shared development/agent infrastructure** | Repository operation instructions and skills, not Project/runtime/Studio. |
| `BIBLE.md` | **Second Gate reference unless content audit says otherwise** | Game-specific naming/content reference belongs conceptually with Second Gate docs, not runtime. |
| native binaries/shims and dependency caches | **runtime dependency outputs / generated** | Ownership follows the runtime feature; source/build recipes remain tooling. Do not place generated binaries in the Project merely because export needs them. |

### The important mixed boundary: `data/`

`tools/export/runtime-manifest.json` currently says, in effect:

```text
runtime: main.lua + engine/ + presentation/ + four files inside runtime/data
project: assets/ + authored JSON recursively under Project/data
```

That `dataRuntimeFiles` exception is the clearest sign that physical layout contradicts semantics. The semantic repair must happen **before** moving Second Gate into a dedicated Project directory:

1. give runtime-owned authored-storage/JSON/loader support a runtime-owned module/config location;
2. make runtime consumers resolve those support modules from the installed runtime, while authored resources resolve only through `Project/data`;
3. make the exporter copy a coherent runtime subtree rather than reopen `runtime/data` to pick exceptions;
4. mechanically prove that no runtime helper is required inside a Project's `data/`.

This is not a license to move `data/engine.json` or other authored JSON merely because its subject is the engine. Its current semantics are Project-authored registry/configuration and it must be judged separately if a future shared-default/package model is designed.

## 3. Recommended target layout

Recommended family:

```text
/
  runtime/                 # installed reusable Thestra player/runtime
    main.lua
    conf/ or equivalent
    engine/
    presentation/
    support/               # authored-storage/json/loader support now buried in data/

  studio/                  # Thestra Studio application
    main.js
    package.json
    package-lock.json
    editor/
    launcher/
    resources/

  projects/
    second-gate/           # the ordinary in-repo Project
      data/
      assets/

  tools/                   # project-independent dev/build/verification/production tools
    export/
    golden/
    delegate/
    ...

  tests/                   # cross-boundary and owner-specific tests, if retained as one suite
  docs/
    architecture/          # runtime/Studio/cross-boundary durable design
    second-gate/           # game/content/design/walkthrough docs
    tooling/               # verification/production/tool contracts where useful
    reports/
    archive/
```

Names are less important than the three explicit roots: **runtime installation**, **Studio application**, and **Project**. `projects/second-gate/` is recommended over leaving the game at repository root because it makes the strongest invariant visible: Second Gate is one consumer of Thestra, not the container that owns Thestra.

### Copy/open invariant

The target passes the conceptual test only if this works:

```text
copy projects/second-gate -> C:/elsewhere/second-gate
open C:/elsewhere/second-gate in installed Studio
Test Play / export
```

and the copied Project requires **no checkout-owned game content**. It may require the installed Thestra runtime/Studio, exactly as any external Project does. In particular:

- every authored reference required by Second Gate resolves inside its copied Project or through an explicitly defined runtime resource contract;
- no editor chrome comes from `projects/second-gate/assets`;
- no runtime Lua/support module comes from `projects/second-gate/data`;
- no `../..` repository guess is necessary to find Project content;
- export materializes the same runtime + Project combination used for any external Project.

A test fixture should literally copy the Project directory to a temporary external location and exercise open/validate/Test Play staging/export from there. This should become a permanent architecture ratchet before the final root move is considered complete.

### Same-checkout ergonomics

The current no-copy fast path is based on `installRoot === projectRoot`; that equality will intentionally stop being true once Second Gate is nested under `projects/second-gate`. Do **not** preserve it with aliases or by pretending the roots are equal.

Instead make the optimization semantic: an explicitly configured in-repo Project may launch through a development runtime mode that mounts/resolves installed runtime + Project without a full asset copy, provided it is behaviorally equivalent to the canonical staging contract. If LÖVE 11.5 constraints make direct composition impossible, temporary staging is acceptable; ergonomics should be recovered through incremental/cached staging rather than collapsing ownership again.

## 4. Path-coupling inventory

These couplings must be addressed deliberately during migration:

1. **Install root derivation:** `tools/editor/project-root.js` derives `INSTALL_ROOT` by walking two parents from `tools/editor`. Moving Studio changes that assumption.
2. **Default Project selection:** absent `SECOND_RITE_PROJECT`, `PROJECT_ROOT` currently equals `INSTALL_ROOT`. The target needs an explicit development default such as configured `projects/second-gate`, not identity of install and Project roots.
3. **Same-root Test Play:** `project-play.js` optimizes only literal root equality. Target layout needs a new explicit fast-path contract or accepts staging.
4. **Exporter source layout:** `runtime-manifest.json` assumes root `main.lua`, `engine`, `presentation`, release config under `tools/export`, Project `assets`, and runtime support under `runtime/data`.
5. **Exporter defaults:** `export-game.js` currently derives its default repository/project directory from its own location. CLI defaults must distinguish runtime/install and Project roots.
6. **Runtime `data/` module requires:** Lua loaders/support currently share the authored data namespace. These are semantic couplings, not merely paths, and must be repaired first.
7. **Effekseer/native lookup:** runtime/export assumptions around `presentation/effekseer.lua`, shim location and symbol verification must follow runtime installation ownership.
8. **Studio server/static paths:** editor APIs should continue using `inProject(...)` for authored resources and `inInstall(...)`/Studio resources for chrome. Any direct repository-relative reads found during implementation must be migrated to the appropriate root API.
9. **CI/golden commands:** workflows invoke repository-root `lovec . ...` and scripts assume current root layout. They must gain explicit runtime + Project inputs before the final move, or run against a materialized development tree produced by the canonical contract.
10. **G5/G6 reference paths:** reference ownership and commands are repository tooling concerns. Moving code must not imply recapturing owner-signed references; path-only changes should prove decoded output unchanged where possible.
11. **Package/Electron cwd:** root package metadata and `main.js` make repository root the Studio app today. PR #364 also deliberately launches the live checkout. Relocation must preserve live-checkout development while changing the app root intentionally.
12. **Loose scripts/docs:** root and `tools/` scripts may contain hardcoded `data/`, `assets/`, `engine/`, `presentation/` paths. Each must be classified by semantic input before bulk rewriting; a grep result is an inventory, not an ownership decision.

Path contracts worth centralizing/configuring are: `installRoot`, `runtimeRoot`, `studioRoot`, `projectRoot`, `projectDataRoot`, `projectAssetRoot`, and disposable `stageRoot`. Consumers should receive these roots or use one root-provider abstraction rather than rediscovering repository topology.

## 5. GitHub Issue taxonomy

Add durable **scope labels**, orthogonal to existing workflow/type labels:

- `scope:second-gate` — game content, balance, narrative, game-specific art/design;
- `scope:runtime` — reusable Thestra player/game semantics;
- `scope:studio` — Thestra Studio authoring UX/host/editor;
- `scope:tooling` — CI, exporter implementation, golden/delegation/build/analysis infrastructure;
- `scope:contract` — intentionally cross-boundary Project/runtime/Studio/export interfaces.

Keep `agent-ready`, `agent-active`, `agent-review`, `needs-owner`, `design`, `bug`, etc. as separate workflow/type dimensions. A cross-boundary issue may carry two concrete scope labels plus `scope:contract` when useful, but avoid label soup.

When a Second Gate requirement needs a reusable primitive, prefer linked issues if responsibilities and acceptance tests genuinely differ: the Second Gate issue owns desired player/content behavior; the runtime or Studio issue owns the reusable capability. Do not split a bounded change merely to satisfy taxonomy.

## 6. Documentation taxonomy

Recommended durable split:

- `docs/second-gate/**`: game mechanics/content/design, walkthrough, commercial/game-specific art direction;
- `docs/architecture/runtime/**`: reusable runtime design;
- `docs/architecture/studio/**`: editor/host/authoring design;
- `docs/architecture/contracts/**`: Project identity, staging/export, authored-storage/resource boundaries;
- `docs/tooling/**`: golden, CI, delegation, asset-production/tool contracts where prose is durable;
- `docs/reports/**`: dated evidence only;
- `docs/archive/**`: frozen/non-authoritative history.

`ENGINE-STATE.md` remains generated current-state authority and `SPEC.md` remains the reviewed living behavior authority unless a later dedicated issue deliberately splits their authority. Do not perform that split as collateral damage of path cleanup.

## 7. Dependency-ordered migration slices

### Slice A — land conflicting current work and freeze the boundary baseline

Before broad path changes, integrate or deliberately dispose of PRs touching the same surfaces. Highest conflict risk on the current open set:

- #367 edits `docs/design/project-editor-runtime-boundaries.md` and should settle durable Project wording first;
- #364 changes root Electron/launcher/package behavior and should land or be superseded before moving Studio;
- #279/#280 are large stacked `tools/editor` changes and should reach their intended owner-reviewed state before editor relocation;
- #377 changes design-document audit/report material and should be reconciled before taxonomy moves;
- #349/#336 are report/evidence PRs: low runtime risk but path-sensitive if docs move;
- #378/#379/#380 add tooling/runtime-test surfaces and should land before a large tree rewrite when practical.

#369 and #370 should complete stale Campaign generator/protocol cleanup before using repository-wide path searches as migration evidence; otherwise dead vocabulary will create false coupling.

Acceptance: current main is known, active branches are accounted for, and the migration does not strand unmerged work on obsolete paths.

### Slice B — repair runtime support hidden inside Project `data/`

Move runtime-owned authored-storage/JSON/loader support to a runtime-owned namespace and update Lua/runtime/export consumers. Remove `dataRuntimeFiles` from the exporter contract rather than renaming the exception.

Acceptance:

- a Project `data/` contains authored resources only;
- exporter runtime copy is coherent without special files extracted from `runtime/data`;
- external Project validation/Test Play/export remain green;
- no compatibility aliases/symlinks or dual-read paths.

### Slice C — make roots explicit before moving them

Introduce/extend one configured root contract for Studio, runtime, Project and staging. Change defaults so development can explicitly select the in-repo Second Gate Project without assuming Project root equals install root.

Acceptance:

- external fixture Project still opens and stages;
- in-repo Second Gate can be selected through the same Project-root API;
- bad roots fail loud;
- no consumer derives Project ownership from `__dirname` except the centralized installation/bootstrap seam.

### Slice D — establish `projects/second-gate/`

Use `git mv` for Project-owned `data/` and proven Project-owned `assets/` into the explicit Project root. Move only assets whose semantic ownership has been proven; unresolved authoring-library/runtime/editor resources get separate prior decisions.

Acceptance:

- copied external `projects/second-gate` passes the copy/open invariant;
- Test Play/export uses installed runtime + copied Project;
- no checkout-owned game content is required;
- same game behavior and authored references; no G5/G6 recapture merely for paths.

### Slice E — relocate/cohere reusable runtime

Move `engine`, `presentation`, `main.lua`, runtime config/support and native-runtime integration under a coherent runtime root using `git mv`. Update exporter/gates through explicit root inputs.

Acceptance: runtime can be materialized with any valid external Project without Studio modules; exporter has one runtime subtree contract; runtime-to-Studio dependency ratchet remains zero.

### Slice F — relocate Thestra Studio

After #364 and #279/#280 are settled, move Electron host/package/editor resources into a Studio root. Preserve live-checkout development launcher semantics and explicit external Project selection.

Acceptance: Studio boots independently of Second Gate's directory; blank/project-picker or configured-project startup does not borrow Project assets for chrome; external Project Test Play remains canonical.

### Slice G — docs/tooling taxonomy cleanup

Move durable docs by semantic scope and relocate low-risk loose tools/scripts where ownership is already clear. Delete proven bootstrap/disposable tracked residue in separate bounded hygiene changes.

Acceptance: links/checks are updated; reports/archive retain their non-authoritative status; no design-doc move is presented as implementation status.

### Slice H — enforce the architecture

Add mechanical ratchets after the physical migration stabilizes:

- copy/open external Second Gate test;
- Project tree contains no runtime Lua/support modules;
- runtime imports no Studio modules;
- editor chrome/static resources do not resolve from Project assets;
- exporter accepts explicit runtime + Project and produces a hermetic tree;
- repository-owned path guesses outside approved root-provider/build scripts fail a static check where practical.

## 8. Visual and owner-visible risk

Physical moves can produce large diffs without intended visual change. Do not use that as justification to recapture G5/G6. For slices that touch renderer/editor paths, run ordinary deterministic gates and relative visual A/B where applicable. Any actual intended visual change remains owner-supervised under existing golden policy.

`engine/battle.lua` and `engine/scenes/battle.lua` remain owner-supervised even during moves. A pure `git mv` should preserve content byte-for-byte; any necessary import/path edit around those files should be isolated and reviewed explicitly.

## 9. Recommended follow-up Issues

Create bounded implementation issues after owner/review acceptance of this design, rather than expanding #382:

1. **Extract runtime-owned data support from Project `data/` and remove `dataRuntimeFiles`.**
2. **Make Studio/runtime/Project roots explicit and add the external-copy Project ratchet.**
3. **Audit `assets/` semantic ownership before the Second Gate Project move.** This must trace authored references and Studio/runtime consumers, not classify by directory name.
4. **Move Second Gate authored Project into `projects/second-gate/`.** Depends on 1–3.
5. **Move reusable LÖVE runtime into a coherent runtime root and update canonical staging/gates.**
6. **Relocate Thestra Studio after launcher and 3D-editor branches settle.**
7. **Apply scope labels and documentation taxonomy without rewriting issue history.**
8. **Audit/remove generated/bootstrap residue (`.census-bootstrap`, tracked preview/tmp candidates) only where live consumers prove it disposable.**

These should remain separate because they have different failure modes and review owners. In particular, the semantic `data/` repair is not a path-only move, while the eventual Second Gate `git mv` should become close to path-only precisely because that repair happened first.

## 10. Alternatives considered

### Keep Second Gate at repository root

This minimizes path churn but leaves the root visually privileged and makes the Project/install distinction harder to enforce. It also preserves the temptation to treat repository-relative content as Project content. Not recommended as the target.

### Put runtime and Studio together under one `thestra/` root

Reasonable if distribution later treats Studio + bundled runtime as one installed product. Even then, retain explicit internal `runtime/` and `studio/` ownership and never make runtime import editor code. This is a naming/packaging alternative, not a semantic difference.

### Introduce shared packages/RTP during the move

Not recommended. #299 explicitly separated future composition/package semantics from the Project decision. First make one Project portable against one installed runtime. Shared authored packages can then be designed from concrete reuse pressure rather than used to excuse ambiguous current assets.

## 11. Architectural acceptance statement

The migration is successful when the repository can truthfully be described as:

> Thestra Studio opens a Project. Thestra runtime runs a Project. The exporter materializes that same runtime + Project contract. Second Gate happens to be the Project developed in this monorepo, and moving/copying its Project directory outside the checkout does not change what it owns.

Until that is mechanically true, physical tidiness alone is not completion.

Agent-Signature:
  platform: ChatGPT
  model: GPT-5.6 Sol
  role: documentation
  task: "#382"
  base: 12f53777d883510ab2cb133beea7cf15d434b31f
