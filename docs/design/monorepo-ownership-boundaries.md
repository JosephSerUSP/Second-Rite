# Monorepo ownership boundaries

Status: durable architecture intent for #382. This document defines ownership, target boundaries, and migration invariants. It is deliberately **not** a census of the current checkout or a migration-status tracker. Dated evidence supporting these recommendations belongs in `docs/reports/monorepo-ownership-census-2026-08-13.md`; current implementation truth remains `docs/ENGINE-STATE.md` and reviewed behavior remains `docs/SPEC.md`.

## Ownership model

The monorepo has four durable product/workspace ownership domains: **Second Gate Project**, **Thestra runtime**, **Thestra Studio**, and **shared development/verification tooling**. Thestra also needs a versioned **default authored/resource layer** (working term: RTP) between native runtime primitives and Projects. Historical reports, archives, experiments, and creative references may be retained, but they are not product ownership domains merely because they are checked in.

A playable game is a **Project**. Routes, stories, chapters, difficulty variants, and other experiences inside one game are ordinary Project logic when that is the natural authoring model. The removed Campaign-root mechanism is not an alternative Project/root ontology. Future package/dependency, localization, mod, randomizer, or shared-content composition semantics are separate design questions and must not be invented as compatibility machinery for this reorganization.

The runtime owns reusable gameplay execution and player-facing presentation primitives. The Thestra default authored/resource layer may own reusable JSON compositions, assets, and templates built from those primitives. Studio owns authoring UX, editor/server/host behavior, and Studio-specific resources. Runtime must not depend on Studio implementation. Studio works with distinct installation/runtime/default ownership and opened-Project ownership; Second Gate contributes only material semantically classified as Project-specific.

Export, golden gates, CI, delegation, experiments, build recipes, and cross-boundary tests may validate several owners without becoming part of any one shipped owner.

## Target layout family

```text
/
  runtime/                 # installed reusable Thestra runtime primitives
    main.lua
    engine/
    presentation/
    support/               # runtime-owned storage/loader support

  defaults/                # working physical family for Thestra RTP/default authored layer
                            # final name/layout follows #385 classification

  studio/                  # Thestra Studio application
    main.js
    package.json
    package-lock.json
    editor/
    launcher/
    resources/

  projects/
    second-gate/           # ordinary in-repo Project identity
      data/                # only material classified as Project-local
      assets/              # only material classified as Project-local

  tools/                   # shared dev/build/verification/production tooling
  tests/                   # cross-boundary and owner-specific tests
  docs/                    # authorities, durable design, reports/archive
```

Literal subdirectory names may change during implementation. The explicit runtime, Studio, and Project roots are architectural; the physical home/name of the default authored layer is gated by #385. `projects/second-gate/` remains the target Project identity because it makes Second Gate visibly a consumer of Thestra rather than the container that owns Thestra, but its eventual contents must be semantically classified before wholesale relocation.

`docs/SPEC.md` and `docs/ENGINE-STATE.md` remain repository-level authorities while they span multiple ownership domains. Moving Second Gate must not bury or duplicate those authorities inside the Project.

## Project portability and hermetic-export invariant

The in-repo Second Gate Project must be ordinary. Its directory must be copyable elsewhere and then openable, validatable, Test Playable, and exportable through an installed compatible Thestra environment using the same contract as any external Project.

During authoring, a Project may resolve an explicitly versioned compatible Thestra default authored/resource layer. This working RTP concept is **not** a separately installed player dependency. Normal exported games remain hermetic: the resolved runtime, depended-upon defaults, explicit packages where added, and Project-local material are materialized into the shipped game. Players do not install a shared RTP or Studio to run a normal export.

The copied Project must not depend on checkout-owned **Second Gate game content** or repository-relative guesses. Editor chrome never silently borrows Project assets; runtime support modules never live inside Project `data/` merely to make the checkout runnable; and Test Play/export must resolve the same ownership graph as external Projects.

A permanent architecture test should copy the in-repo Project to a temporary external location and exercise normal Project open/validation/staging/export from that copy.

## Authored data, runtime support, and Thestra defaults

`Project/data` is the Project-local authored-data ownership boundary. Runtime-owned Lua, JSON parser/loader support, storage adapters, runtime support manifests, or equivalent implementation modules do not belong inside that namespace.

The migration must extract runtime-owned support from the current mixed `data/` before physically moving Second Gate. Export should copy a coherent runtime subtree and then materialize resolved authored data without a special exception that reopens the Project data namespace for runtime implementation files.

Authored JSON is not Project-owned merely because it is JSON. Registries/configuration such as the current `data/engine.json` are authored data in the current architecture, but #385 must classify whether particular authored compositions ultimately belong to Second Gate, to the Thestra default authored/resource layer, or elsewhere. Subject matter and file format do not decide ownership; authoring intent, consumers, override/resolution semantics, and portability do.

The default layer is a versioned Thestra-authored library, not merely a fallback directory. It may include baseline/default compositions and reusable Scene/Event/etc. templates built on the same authored substrate available to Projects. Project-specific material must not be promoted into this layer merely because Studio currently borrows it for preview or authoring. Future package semantics remain separate under #325 even if implementation later discovers shared infrastructure.

## Asset ownership

Neither `assets = Project` nor generic appearance is an ownership rule. Some authored assets may ultimately be Thestra-supplied defaults; others are Second Gate-specific, Studio-only chrome/preview resources, reusable authoring-library material, or unresolved.

Before wholesale relocation, #385 must classify default-layer candidates by consumer and authoring intent. Project-specific material stays Project-owned even when Studio currently uses it incidentally. Conversely, a genuinely Thestra-supplied baseline resource need not remain Second Gate-owned merely because it originated under a Project-shaped path. Unresolved assets stay unresolved until evidence establishes ownership.

## Root abstractions and same-checkout ergonomics

Consumers should operate on semantic roots rather than rediscover repository topology. The useful vocabulary includes `installRoot`, `runtimeRoot`, a default/RTP authored-resource root or resolver, `studioRoot`, `projectRoot`, `projectDataRoot`, `projectAssetRoot`, and disposable `stageRoot`. A shared provider/configuration seam should derive these roots; individual consumers should not walk a fixed number of parents or assume repository root equals Project root.

After Second Gate moves under `projects/second-gate/`, `installRoot === projectRoot` will intentionally be false. Do not preserve equality with aliases, symlinks, compatibility roots, or misleading normalization.

The durable invariant is **ergonomic behavior equivalent to the canonical installed-Thestra + Project contract**. An in-repo development mode may avoid a full copy when it can compose runtime/defaults and Project safely. If LÖVE constraints require materialization, incremental/cached temporary staging is acceptable. The optimization must never collapse ownership again.

## Export and staging contract

There is one canonical materialization contract:

```text
installed compatible Thestra runtime/defaults
        + explicit packages where added
        + one Project
        -> resolved runnable staged/exported game
```

Test Play/preview and export may have different lifecycle/performance needs, but they must agree on ownership and resolution. Normal export is self-contained and never requires a player-installed RTP. Reorganization must not introduce a second staging implementation, Campaign alias, special Second Gate overlay, or hidden fallback to Second Gate checkout content.

## Documentation taxonomy

Document location expresses authority and subject, not delivery state. Durable categories should distinguish Second Gate game/content/design; runtime/default-layer architecture; Studio architecture; cross-boundary contracts; shared tooling/verification/production contracts; dated reports/evidence; and frozen archive/history.

`docs/design/**` (or a later semantically split successor) contains intent, constraints, rationale, and acceptance invariants only. It must not contain current ownership censuses, current open-PR conflict lists, migration completion checklists, or claims that a path currently does or does not exist.

`docs/reports/**` contains dated point-in-time evidence. Reports may support a design decision but never outrank `ENGINE-STATE.md`, `SPEC.md`, or live code.

## Issue taxonomy

GitHub scope labels should be orthogonal to workflow/type labels:

- `scope:second-gate` — game content, balance, narrative, game-specific art/design;
- `scope:runtime` — reusable Thestra player/game semantics and default-layer contracts where applicable;
- `scope:studio` — Studio authoring UX/host/editor;
- `scope:tooling` — CI, exporter implementation, golden/delegation/build/analysis infrastructure;
- `scope:contract` — intentionally cross-boundary interfaces and ownership seams.

Agent-state, owner-review, bug, design, and other workflow/type labels remain separate dimensions. An issue may carry multiple scope labels when its acceptance contract genuinely crosses owners; `scope:contract` is not a substitute for naming concrete owners.

When a Second Gate design need requires a reusable primitive, split it into linked issues only when responsibilities and acceptance tests genuinely differ. The game issue owns desired player/content behavior; runtime or Studio owns the reusable substrate.

## Dependency principles for migration

Physical moves follow semantic repairs, not the reverse:

1. Settle conflicting active work before broad path changes.
2. Repair mixed implementation ownership before moving roots: runtime support leaves Project-shaped `data/`.
3. Complete #385 classification sufficiently to distinguish Second Gate-local authored JSON/assets from Thestra defaults/templates and Studio-only resources before wholesale Second Gate data/asset relocation.
4. Make runtime, default-layer, Studio, Project, and stage roots/resolution explicit without repository-topology assumptions.
5. Prove copied/external Second Gate equivalence through the normal Project contract and hermetic export.
6. Move owners with history preserved using `git mv` where practical; do not add compatibility aliases for repo-owned paths.
7. Relocate Studio only after launcher/package/editor-root contracts can preserve live-checkout development.
8. Move docs/tooling by semantic owner independently where safe.
9. Delete obsolete path assumptions after consumers migrate; do not leave indefinite dual-read/fallback paths.

#385 gates semantic classification; this document does not solve its resolution, versioning, New Project, Make Local, or template-library design. #325 continues to own future explicit package/dependency semantics.

## Durable acceptance invariants

The eventual reorganization is complete only when:

- Project remains the independently runnable/authored game identity;
- `projects/second-gate/` is an ordinary Project identity whose local contents have been semantically classified;
- Thestra can supply a versioned default authored/resource layer without creating a separately installed player RTP;
- normal exports are hermetic and players do not install shared defaults or Studio;
- runtime never depends on Studio/editor modules;
- editor chrome never silently borrows Project assets;
- Project `data/` contains Project-local authored data, not runtime implementation support;
- default-layer JSON/assets/templates are not classified by file type or path alone;
- Second Gate-specific material is not moved into defaults merely because Studio currently borrows it;
- runtime/default/Studio/Project/stage roots and resolution are semantic inputs rather than directory guesses;
- same-checkout development remains ergonomic without pretending install and Project roots are identical;
- authored-storage/resource-reference semantics remain fail-loud, Project-aware, and deterministic;
- G1-G4, unit/save, and relative visual gates remain meaningful through the move;
- G5/G6 owner-signed references are not recaptured merely because paths moved;
- Battle owner-supervised files are not behaviorally edited as collateral path cleanup;
- no Campaign compatibility alias, symlink tree, alternate Project root, or premature package equivalence is introduced.

The dated census/report records the evidence and current dependency ordering that motivated this design. Implementation status belongs in follow-up Issues and current authorities, not here.
