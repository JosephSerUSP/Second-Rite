# Monorepo ownership census — 2026-08-13

Point-in-time evidence for #382 / PR #383. This report records the checkout and open-work state inspected on 2026-08-13. It supports `docs/design/monorepo-ownership-boundaries.md` but is **not** a current-state authority. For current implementation truth use `docs/ENGINE-STATE.md`, `docs/SPEC.md`, and live code.

Audit base for the original census: `main@12f53777d883510ab2cb133beea7cf15d434b31f` or newer current truth where noted. No production move is performed here.

## Current ownership census

| Current path / subtree | Semantic owner observed | Evidence / disposition |
| --- | --- | --- |
| `data/**/*.json` and fragment directories | Second Gate Project | Current Project contract requires `data/`; editor/authored-data semantics treat JSON resources as authored Project data. `data/engine.json` defines engine vocabulary but is currently authored/overridable Project data, not runtime-owned merely because of its subject. |
| `data/authored_storage.lua`, `data/json.lua`, `data/loader.lua`, `data/authored_storage_manifest.json` | Thestra runtime | Mixed-ownership defect. Exporter explicitly copies these through `dataRuntimeFiles` before authored JSON is overlaid. |
| `assets/**` | Mostly Second Gate Project; unresolved library/runtime candidates remain | Exporter currently sources `assets` from `projectDir`. Generic-looking resources cannot be reclassified without consumer/reference evidence. |
| `engine/**`, `presentation/**`, root `main.lua` | Thestra runtime | Runtime/player code and presentation; exporter takes these from installed runtime. |
| root `conf.lua` | mixed runtime-development configuration | Development config is root-coupled while release export substitutes `tools/export/release-conf.lua`; seam should be decided before relocation. |
| root `main.js`, package metadata, `runEditor.bat`, launcher/icon host inputs | Thestra Studio | Electron host and normal Studio development launch. |
| `tools/editor/**` | Thestra Studio | Editor/server/project-root/Test Play frontend. |
| `tools/export/**` | shared tooling / cross-boundary contract | Canonical installed-runtime + Project materialization implementation. |
| `tools/golden/**`, `.github/workflows/**`, `tests/**` | shared verification tooling | Cross-owner gates and fixtures. |
| `tools/delegate/**`, agent/bootstrap policy | shared development infrastructure | Repository workflow, not shipped product. |
| `tools/effekseer/**` | runtime build/dependency tooling | Build/verification recipe is tooling; produced runtime dependency belongs to installation/build output. |
| asset-generation/production/blender/language tooling | mixed authoring library / production tooling | Inputs and outputs need per-tool consumer audit before physical ownership moves. |
| `tools/campaign-gen/**` | stale/historical generator surface pending #369 | Campaign vocabulary no longer defines Project ontology; useful behavior must migrate separately. |
| analysis/experiment/lab directories | shared development/research tooling, sometimes game-specific | Harness and results should state scope explicitly. |
| `docs/ENGINE-STATE.md`, `docs/SPEC.md` | repository-level authorities | Cross-boundary current-state/spec authority; should not be buried inside Second Gate. |
| `docs/game design/**`, walkthrough and game-specific product/design prose | Second Gate documentation | Project/game intent, though documentation need not ship inside runnable Project root. |
| `docs/design/**` | mixed subject ownership | Runtime/Studio architecture and Second Gate design coexist; #360/#367 reinforce that this directory is intent, not current status. |
| `docs/reports/**`, `docs/archive/**` | evidence/history | Reports are dated evidence; archive is non-authoritative. |
| `docs/asset-pipeline/**` | mixed production/authoring documentation | Classify by documented pipeline rather than directory name. |
| `inspiration/**`, `BIBLE.md` | primarily Second Gate reference | Creative/game reference, not runtime dependency. |
| `phase4-v2-preview/**` | likely retained historical/research evidence | Verify consumers before deletion; do not promote it into target architecture from name alone. |
| `tmp/**`, `dist/**`, screenshot actual/output trees, generated host/runtime caches | generated/disposable | Keep outside durable ownership roots unless deliberately checked in as evidence. |
| `userPerform/**` | shared developer convenience tooling | Wrappers around repository workflows. |
| `.census-bootstrap/**` | unresolved bootstrap/generated residue | No product owner established; bounded hygiene audit should decide retention. |
| `.claude/**`, `CLAUDE.md`, `AGENTS.md` | shared agent/development infrastructure | Repository operation policy. |
| native binaries/shims/dependency caches | runtime dependency output / generated | Feature ownership follows runtime; source/build recipes remain tooling. |

## Concrete mixed boundary: `data/`

At audit time `tools/export/runtime-manifest.json` contains:

```json
{
  "rootFiles": ["main.lua"],
  "runtimeDirectories": ["engine", "presentation"],
  "projectDirectories": ["assets"],
  "dataRuntimeFiles": [
    "authored_storage.lua",
    "authored_storage_manifest.json",
    "json.lua",
    "loader.lua"
  ],
  "authoredDataExtensions": [".json"]
}
```

This is direct evidence that current physical `data/` mixes two owners. The exporter must special-case four runtime files inside the namespace otherwise treated as authored Project data. That exception is the strongest reason to repair semantic ownership before moving Second Gate.

The same evidence cuts the other way for `data/engine.json`: current Project semantics allow authored JSON under `Project/data`, and repository policy describes command/trait/schema vocabulary as data-driven. Its engine subject does not itself prove runtime ownership.

## Current Project/root coupling evidence

`tools/editor/project-root.js` currently:

- derives `INSTALL_ROOT` by walking two parents from `tools/editor`;
- treats a directory containing `data/` as the minimum Project contract;
- defaults `PROJECT_ROOT` to `INSTALL_ROOT` when `SECOND_RITE_PROJECT` is absent;
- exposes separate `inProject(...)` and `inInstall(...)` helpers.

`tools/editor/project-play.js` currently:

- stages external Projects through the exporter contract;
- skips staging only when `fs.realpathSync(installRoot) === fs.realpathSync(projectRoot)`;
- runs the staged directory otherwise.

Therefore a future `projects/second-gate/` move intentionally breaks the literal equality used by the current no-copy fast path. Preserving the old equality would be the wrong abstraction. The replacement must preserve ergonomics while keeping runtime and Project roots distinct.

## Other path-coupling inventory

The audit identified these migration-sensitive assumptions:

1. editor install-root derivation from `tools/editor` depth;
2. default Project = install root;
3. Test Play direct path keyed to literal root equality;
4. exporter manifest assumptions about root `main.lua`, `engine/`, `presentation/`, Project `assets/`, and runtime support inside `data/`;
5. exporter CLI/default directory derivation from repository-relative tool location;
6. runtime requires/loaders sharing the authored `data/` namespace;
7. Effekseer/native lookup tied to runtime/presentation paths;
8. Studio server/static reads that must remain explicit about Project versus installation ownership;
9. repository-root `lovec . ...` CI/golden commands;
10. G5/G6 reference and capture paths, which must move without owner-unsanctioned recapture;
11. Electron/package cwd and live-checkout launcher assumptions;
12. loose scripts/docs containing direct `data/`, `assets/`, `engine/`, or `presentation/` paths.

A future migration search should classify each hit by semantic input. A grep result is coupling evidence, not an ownership decision.

## Unusual-root findings

`phase4-v2-preview/`, `.census-bootstrap/`, `userPerform/`, `tmp/`, `inspiration/`, loose scripts, generated caches, and agent/bootstrap material should not be swept into runtime, Studio, or Second Gate simply because a new root layout is being created. Each either has an established repository-tooling/reference role or requires a bounded retention audit.

This is especially important for asset-production/source material: a runnable Project should contain what it needs to run, while reusable production sources may remain repository authoring-library material. No shared-asset package model has been authorized by #299.

## Open-PR/dependency census at review time

The open PR set observed during the 2026-08-13 review included #383 plus #377, #380, #379, #378, #364, #367, #349, #256, #336, #334, stacked #280/#279, and the intentional #257 LÖVE 12 shadow.

Conflict implications:

- **#367** edits durable Project/editor/runtime boundary prose and should settle the #360 authority repair before broad documentation moves.
- **#364** changes root Electron/package/launcher behavior and should land or supersede #256 before Studio relocation.
- **#279/#280** are substantial stacked `tools/editor` work and should reach owner-reviewed disposition before editor path relocation.
- **#377**, **#349**, and **#336** are report/evidence work whose paths may conflict with documentation taxonomy moves even though runtime risk is low.
- **#378/#379/#380** add tooling/test/runtime-adjacent surfaces; landing them before a tree-wide move reduces rebasing noise.
- **#334** is Project asset work and should not be stranded by an assets root move.
- **#257** is intentionally long-lived and should be rebased/adapted deliberately rather than treated as an ordinary merge dependency.

Issues #369 and #370 remain important cleanup dependencies for migration searches: stale Campaign generator/protocol vocabulary can otherwise look like live Project-root coupling. Their existence must not cause Campaign compatibility to be built into the target layout.

This list is point-in-time evidence only. Re-census open PRs immediately before any physical move.

## Recommendation supported by the evidence

The evidence supports this dependency order:

1. settle conflicting active work and Campaign cleanup;
2. extract runtime-owned support from `data/` and remove the exporter `dataRuntimeFiles` exception;
3. introduce explicit runtime/Studio/Project/stage root contracts and update staging/export/CI consumers;
4. prove copied Second Gate behaves as an ordinary external Project;
5. audit unresolved assets and authoring-library material;
6. move Second Gate authored `data/` and proven Project assets under the dedicated Project root with history preserved;
7. relocate runtime and Studio roots after their consumers no longer depend on repository-root topology;
8. move docs/tooling by semantic owner in bounded follow-ups.

No production files should move until the design is accepted and bounded implementation issues exist.

## Verification expectations for follow-up migration

Each implementation slice should run the normal hosted verification and shim provenance on its exact final head. Path-only work must not use G5/G6 recapture to hide differences. Where owner-signed absolute visuals cannot run portably, use the existing repeat-controlled relative visual A/B path to establish candidate-vs-base equivalence, while retaining owner control of absolute references.

Battle owner-supervised files are outside the scope of path cleanup unless the owner explicitly authorizes a separate behavioral change.

Agent-Signature:
  platform: ChatGPT
  model: GPT-5.6 Sol
  role: architecture-review
  task: "#382 / PR #383"
  base: 12f53777d883510ab2cb133beea7cf15d434b31f
