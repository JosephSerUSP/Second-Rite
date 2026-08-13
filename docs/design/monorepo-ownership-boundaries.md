# Monorepo ownership boundaries

Status: durable architecture intent for #382. This document defines ownership, target boundaries, and migration invariants. It is deliberately **not** a census of the current checkout or a migration-status tracker. Dated evidence supporting these recommendations belongs in `docs/reports/monorepo-ownership-census-2026-08-13.md`; current implementation truth remains `docs/ENGINE-STATE.md` and reviewed behavior remains `docs/SPEC.md`.

## Ownership model

The monorepo has four durable ownership domains: **Second Gate Project**, **Thestra runtime**, **Thestra Studio**, and **shared development/verification tooling**. Historical reports, archives, experiments, and creative references may be retained, but they are not product ownership domains merely because they are checked in.

A playable game is a **Project**. Routes, stories, chapters, difficulty variants, and other experiences inside one game are ordinary Project logic when that is the natural authoring model. The removed Campaign-root mechanism is not an alternative Project/root ontology. Future package/dependency, localization, mod, randomizer, or shared-content composition semantics are separate design questions and must not be invented as compatibility machinery for this reorganization.

The runtime owns reusable gameplay execution and player-facing presentation. Studio owns authoring UX, editor/server/host behavior, and Studio-specific resources. Runtime must not depend on Studio implementation. Studio works with distinct installation/runtime ownership and opened-Project ownership: a Project contributes authored data and Project-owned assets; installed runtime code comes from Thestra.

Export, golden gates, CI, delegation, experiments, build recipes, and cross-boundary tests may validate several owners without becoming part of any one shipped owner.

## Target layout family

```text
/
  runtime/                 # installed reusable Thestra runtime
    main.lua
    engine/
    presentation/
    support/               # runtime-owned storage/loader support

  studio/                  # Thestra Studio application
    main.js
    package.json
    package-lock.json
    editor/
    launcher/
    resources/

  projects/
    second-gate/           # ordinary in-repo Project
      data/
      assets/

  tools/                   # shared dev/build/verification/production tooling
  tests/                   # cross-boundary and owner-specific tests
  docs/                    # authorities, durable design, reports/archive
```

Literal subdirectory names may change during implementation, but the three explicit roots are architectural: **runtime**, **Studio**, and **Project**. `projects/second-gate/` is preferred because it makes Second Gate visibly a consumer of Thestra rather than the container that owns Thestra.

`docs/SPEC.md` and `docs/ENGINE-STATE.md` remain repository-level authorities while they span multiple ownership domains. Moving Second Gate must not bury or duplicate those authorities inside the Project.

## Project portability invariant

The in-repo Second Gate Project must be ordinary. Its directory must be copyable elsewhere and then openable, validatable, Test Playable, and exportable through installed Thestra using the same contract as any external Project.

The copied Project may depend on installed Thestra. It must not depend on checkout-owned **game content** or repository-relative guesses. Therefore authored Project references resolve inside the Project or through an explicitly designed runtime resource contract; editor chrome never silently borrows Project assets; runtime support modules never live inside Project `data/` merely to make the checkout runnable; and export/Test Play use the same installed-runtime + Project composition as external Projects.

A permanent architecture test should copy the in-repo Project to a temporary external location and exercise normal Project open/validation/staging/export from that copy.

## Project data versus runtime support

`Project/data` is the authored-data ownership boundary. Runtime-owned Lua, JSON parser/loader support, storage adapters, runtime support manifests, or equivalent implementation modules do not belong inside that namespace.

The migration must extract runtime-owned support from Project `data/` **before** physically moving Second Gate. Export should copy a coherent runtime subtree and then materialize Project-authored data without a special exception that reopens the Project data namespace for runtime files.

This does **not** make every engine-related JSON file runtime-owned. Authored registries/configuration such as `data/engine.json` remain Project-authored when the Project is allowed to author or override them. Subject matter does not decide ownership; the authoring and consumption contract does. Any future proposal to turn such data into runtime defaults or shared packages requires its own semantics and migration.

## Asset ownership

Project assets are the assets required to reproduce the authored game. Generic appearance is not evidence of runtime ownership.

Before moving assets, classify them by consumer and authoring intent: Project-owned Second Gate content; Studio chrome/resources; genuinely reusable runtime resources; reusable authoring-library/source material; or unresolved. Unresolved assets stay unresolved until a consumer/reference audit establishes ownership. Path cleanup must not silently invent an RTP/shared-asset model.

## Root abstractions and same-checkout ergonomics

Consumers should operate on semantic roots rather than rediscover repository topology. The useful vocabulary is `installRoot`, `runtimeRoot`, `studioRoot`, `projectRoot`, `projectDataRoot`, `projectAssetRoot`, and disposable `stageRoot`. A shared provider/configuration seam should derive these roots; individual consumers should not walk a fixed number of parents or assume repository root equals Project root.

After Second Gate moves under `projects/second-gate/`, `installRoot === projectRoot` will intentionally be false. Do not preserve equality with aliases, symlinks, compatibility roots, or misleading normalization.

The durable invariant is **ergonomic behavior equivalent to the canonical installed-runtime + Project contract**. An in-repo development mode may avoid a full copy when it can compose runtime and Project safely. If LÖVE constraints require materialization, incremental/cached temporary staging is acceptable. The optimization must never collapse ownership again.

## Export and staging contract

There is one canonical materialization contract:

```text
installed runtime + one Project -> runnable staged/exported game
```

Test Play/preview and export may have different lifecycle/performance needs, but they must agree on ownership and file composition. Runtime support comes from runtime ownership; authored data/assets come from the Project. Reorganization must not introduce a second staging implementation, Campaign alias, special Second Gate overlay, or hidden fallback to checkout content.

## Documentation taxonomy

Document location expresses authority and subject, not delivery state. Durable categories should distinguish Second Gate game/content/design; runtime architecture; Studio architecture; cross-boundary contracts; shared tooling/verification/production contracts; dated reports/evidence; and frozen archive/history.

`docs/design/**` (or a later semantically split successor) contains intent, constraints, rationale, and acceptance invariants only. It must not contain current ownership censuses, current open-PR conflict lists, migration completion checklists, or claims that a path currently does or does not exist.

`docs/reports/**` contains dated point-in-time evidence. Reports may support a design decision but never outrank `ENGINE-STATE.md`, `SPEC.md`, or live code.

## Issue taxonomy

GitHub scope labels should be orthogonal to workflow/type labels:

- `scope:second-gate` — game content, balance, narrative, game-specific art/design;
- `scope:runtime` — reusable Thestra player/game semantics;
- `scope:studio` — Studio authoring UX/host/editor;
- `scope:tooling` — CI, exporter implementation, golden/delegation/build/analysis infrastructure;
- `scope:contract` — intentionally cross-boundary interfaces and ownership seams.

Agent-state, owner-review, bug, design, and other workflow/type labels remain separate dimensions. An issue may carry multiple scope labels when its acceptance contract genuinely crosses owners; `scope:contract` is not a substitute for naming concrete owners.

When a Second Gate design need requires a reusable primitive, split it into linked issues only when responsibilities and acceptance tests genuinely differ. The game issue owns desired player/content behavior; runtime or Studio owns the reusable substrate.

## Dependency principles for migration

Physical moves follow semantic repairs, not the reverse:

1. Settle conflicting active work before broad path changes.
2. Repair mixed ownership before moving roots: runtime support leaves Project `data/`; unresolved assets are audited rather than guessed.
3. Make runtime, Studio, Project, and stage roots explicit without repository-topology assumptions.
4. Prove copied/external Second Gate equivalence through the normal Project contract.
5. Move owners with history preserved using `git mv` where practical; do not add compatibility aliases for repo-owned paths.
6. Relocate Studio only after launcher/package/editor-root contracts can preserve live-checkout development.
7. Move docs/tooling by semantic owner independently where safe.
8. Delete obsolete path assumptions after consumers migrate; do not leave indefinite dual-read/fallback paths.

## Durable acceptance invariants

The eventual reorganization is complete only when:

- Project remains the independently runnable/authored identity;
- Second Gate is an ordinary Project, copyable/openable outside the checkout;
- installed runtime + Project is the single play/export composition model;
- runtime never depends on Studio/editor modules;
- editor chrome never silently borrows Project assets;
- Project `data/` contains authored Project data, not runtime implementation support;
- runtime/Studio/Project/stage roots are semantic inputs rather than directory guesses;
- same-checkout development remains ergonomic without pretending install and Project roots are identical;
- authored-storage/resource-reference semantics remain fail-loud and Project-aware;
- G1-G4, unit/save, and relative visual gates remain meaningful through the move;
- G5/G6 owner-signed references are not recaptured merely because paths moved;
- Battle owner-supervised files are not behaviorally edited as collateral path cleanup;
- no Campaign compatibility alias, symlink tree, alternate Project root, or unearned package/RTP ontology is introduced.

The dated census/report records the evidence and current dependency ordering that motivated this design. Implementation status belongs in follow-up Issues and current authorities, not here.
