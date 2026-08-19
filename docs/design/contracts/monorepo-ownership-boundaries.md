# Monorepo ownership boundaries

Status: durable architecture intent for #382. This document defines ownership, target boundaries, and migration invariants. It is deliberately **not** a census of the current checkout or a migration-status tracker. Dated evidence belongs in `docs/reports/monorepo-ownership-census-2026-08-13.md` and the current-main refresh `docs/reports/monorepo-ownership-census-2026-08-17.md`; current implementation truth remains `docs/ENGINE-STATE.md` and reviewed behavior remains `docs/SPEC.md`.

## Settled repository/product direction

For the foreseeable future this is **one monorepo**.

Developer-facing repository identity should eventually return to **Hichaukitoden**, but a GitHub repository rename is a separate operation and is not part of #382's migration slices.

The durable product identities are:

- **Thestra** — reusable runtime/player semantics and presentation primitives;
- **Thestra Studio** — editor/authoring application;
- **Second Gate** — player-facing game, authored as one ordinary Thestra Project;
- **Thestra RTP/default authored layer** — reusable versioned authored resources/defaults resolved by Projects;
- **shared development/verification tooling** — exporter, staging, CI, goldens, production tools and cross-boundary tests.

The in-repo Second Gate Project may use the developer-facing physical identity `projects/hichaukitoden-game/`. Repository splitting is deferred until concrete distribution, release, licensing, or maintenance pressure justifies it.

Historical reports, archives, experiments, creative references and developer convenience material may be retained, but they are not product ownership domains merely because they are checked in.

## Ownership model

A playable game is a **Project**. Routes, stories, chapters, difficulty variants, and other experiences inside one game are ordinary Project logic when that is the natural authoring model. The removed Campaign-root mechanism is not an alternative Project/root ontology. Future package/dependency, localization, mod, randomizer, or shared-content composition semantics are separate design questions and must not be invented as compatibility machinery for this reorganization.

The runtime owns reusable gameplay execution and player-facing presentation primitives. The Thestra default authored/resource layer owns reusable authored resources and templates intentionally supplied by Thestra. Studio owns authoring UX, editor/server/host behavior, and Studio-specific resources. Runtime must not depend on Studio implementation. Studio works with distinct installation/runtime/default ownership and opened-Project ownership; Second Gate contributes only material semantically classified as Project-specific.

Export, golden gates, CI, delegation, experiments, build recipes, and cross-boundary tests may validate several owners without becoming part of any one shipped owner.

## Target layout family

```text
Hichaukitoden/             # eventual developer-facing repository identity
  runtime/                 # installed reusable Thestra runtime primitives
    main.lua
    engine/
    presentation/
    ... runtime support

  rtp/                     # current concrete Thestra default authored/resource layer
                           # `defaults/` remains a conceptual label, not a required rename

  studio/                  # Thestra Studio application
    main.js
    ... Studio-owned package/editor/launcher/resources

  projects/
    hichaukitoden-game/    # ordinary in-repo Project; player-facing game is Second Gate
      data/
      assets/
    labs/                  # other ordinary in-repo Projects/fixtures where useful

  tools/                   # shared dev/build/verification/production tooling
  tests/                   # cross-boundary and owner-specific tests
  docs/                    # authorities, durable design, reports/archive
```

Literal subdirectory names may change during implementation. The explicit runtime, Studio, Project, and default/RTP ownership boundaries are architectural. Current `rtp/` already implements the versioned default authored/resource layer; it should not be renamed merely to make the filesystem resemble a conceptual diagram.

`docs/SPEC.md`, `docs/ENGINE-STATE.md`, and other repository-level authorities remain repository-level while they span multiple ownership domains. Moving Second Gate must not bury or duplicate those authorities inside the Project.

## Project portability and hermetic-export invariant

The in-repo Second Gate Project must be ordinary. Its directory must be copyable elsewhere and then openable, validatable, Test Playable, and exportable through an installed compatible Thestra environment using the same contract as any external Project.

During authoring, a Project may resolve an explicitly versioned compatible Thestra default authored/resource layer. RTP/defaults are **not** a separately installed player dependency. Normal exported games remain hermetic: resolved runtime/defaults, explicit packages where added, and Project-local material are materialized into the shipped game. Players do not install shared RTP/defaults or Studio to run a normal export.

The copied Project must not depend on checkout-owned Second Gate game content or repository-relative guesses. Editor chrome never silently borrows Project assets. Runtime support modules never live inside Project `data/` merely to make the checkout runnable. Test Play/export must resolve the same ownership graph as external Projects.

A permanent architecture test must copy `projects/hichaukitoden-game/` to a temporary external location and exercise normal Project open, validation, Test Play/staging, and hermetic export from that copy. Before the physical move, the same gate may construct an equivalent temporary Project from the current Project-owned source paths; it must then be repointed to the real Project directory rather than retained as a parallel fixture.

## Authored data, runtime support, and Thestra defaults

`Project/data` is the Project-local authored-data ownership boundary in source Projects and the semantic runtime-data boundary in compiled/staged players. Runtime-owned Lua, JSON parser/loader implementation, storage adapters, runtime support manifests, bundled parser implementation, or equivalent code do not belong inside that namespace.

The migration must extract runtime-owned support from the current mixed root `data/` before physically moving Second Gate. Export should copy a coherent runtime subtree and materialize resolved authored data without a special exception that reopens Project `data/` for runtime implementation files.

Authored JSON is not Project-owned merely because it is JSON. Current RTP/default resolution already proves that authored resources may be Project-local, inherited defaults, or explicit local overrides. Subject matter and file format do not decide ownership; authoring intent, consumers, override/resolution semantics, and portability do.

The default layer is a versioned Thestra-authored library, not merely a fallback directory. It may include baseline/default compositions and reusable Scene/Flow/Event/etc. resources built on the same authored substrate available to Projects. Project-specific material must not be promoted into this layer merely because Studio currently borrows it for preview or because it is useful as an example. Future package semantics remain separate under #325 even if implementation later discovers shared infrastructure.

## Project/runtime release identity

A generic installed runtime/exporter must not silently impose Second Gate's product identity on unrelated Projects.

Development and release configuration may contain runtime-owned LÖVE/process defaults, but game identity such as title, application/save identity, icon/branding where applicable, and other Project-specific release metadata must be an explicit Project/default/runtime input with clear ownership. A shared exporter file that hardcodes `SecondRite` is not a durable generic-runtime contract merely because it is physically under shared tooling.

The copied-Project portability gate must include release identity so an external non-Second-Gate Project cannot pass structural staging while accidentally shipping as Second Gate.

## Asset ownership

Neither `assets = Project` nor generic visual appearance is an ownership rule. Assets may be Second Gate Project content, Thestra-supplied defaults, Studio-only chrome/resources, shared production inputs, or retained reference material.

Second Gate-specific material stays Project-owned even when Studio currently uses it incidentally. Conversely, a genuinely Thestra-supplied baseline resource need not remain Second Gate-owned merely because it originated under a Project-shaped path.

Authoring sources and player/runtime assets also need not have identical packaging behavior. For example, a Blender source may remain semantically owned by the Second Gate Project/production source even if normal player export should eventually omit that source file. Do not move Project-owned source art into RTP or Studio merely to reduce export size; solve packaging separately from semantic ownership.

## Root abstractions and same-checkout ergonomics

Consumers operate on semantic roots rather than rediscovering repository topology. Useful vocabulary includes:

- repository/install root;
- runtime root;
- default/RTP root or resolver;
- Studio root;
- opened Project root;
- Project data root;
- Project asset root;
- disposable stage/snapshot root.

A shared provider/configuration seam should derive these roots. Individual consumers must not walk a fixed number of parents or assume repository root equals Project root.

After Second Gate moves under `projects/hichaukitoden-game/`, `installRoot === projectRoot` will intentionally be false. Do not preserve equality with aliases, symlinks, compatibility roots, duplicate `data/`/`assets/` trees, or misleading normalization.

The durable invariant is **ergonomic behavior equivalent to the canonical installed-Thestra + Project contract**. An in-repo development mode may avoid a full copy when it can compose runtime/defaults and Project safely. Incremental/cached temporary staging or semantic snapshots are acceptable. The optimization must never collapse ownership again.

## Export and staging contract

There is one canonical materialization contract:

```text
installed compatible Thestra runtime/defaults
        + explicit packages where added
        + one Project
        -> resolved runnable staged/exported game
```

Source authored representation is an author/build concern; compiled runtime representation is a consumer concern. Test Play/preview and export may have different lifecycle/performance needs, but they must agree on semantic ownership and resolution.

Normal export is self-contained and never requires a player-installed RTP/default layer. Reorganization must not introduce a second staging implementation, Campaign alias, special Second Gate overlay, hidden fallback to Second Gate checkout content, or a list equivalent to "Project data except these runtime files".

Repository physical layout and shipped player archive layout need not be identical. For example, repository `runtime/main.lua` may still materialize as player-root `main.lua` if that is the established LÖVE package contract.

## Studio boundary

Thestra Studio is an installed authoring application, not part of a Project and not part of the player runtime.

Studio may consume shared `tools/data/**`/export/root-resolution services, but those services do not become Studio-owned merely because Studio calls them. A later physical Studio move must distinguish Studio-private app resources from shared cross-boundary tooling.

Studio chrome must never depend on Second Gate assets. Project-aware previews may of course render resources from the currently opened Project when that is the feature being authored; that is not permission for generic Studio identity/icons/UI chrome to borrow game content.

Runtime must never import or require Studio implementation.

## Documentation taxonomy

Document location expresses authority and subject, not delivery state. Durable categories should distinguish:

- Second Gate game/content/design;
- Thestra runtime/default-layer architecture;
- Thestra Studio architecture/authoring UX;
- cross-boundary contracts;
- shared tooling/verification/production contracts;
- dated reports/evidence;
- frozen archive/history/reference.

`docs/design/**` (or a later semantically split successor) contains intent, constraints, rationale, and acceptance invariants only. It must not contain current ownership censuses, current open-PR conflict lists, migration completion checklists, or claims that a path currently does or does not exist.

`docs/reports/**` contains dated point-in-time evidence. Reports may support a design decision but never outrank `ENGINE-STATE.md`, `SPEC.md`, or live code.

Repository-wide authorities must not be moved into the Second Gate Project merely because current examples/content dominate them.

## Issue taxonomy

GitHub scope labels should be orthogonal to workflow/type labels:

- `scope:second-gate` — game content, balance, narrative, game-specific art/design;
- `scope:runtime` — reusable Thestra player/game semantics and default-layer contracts where applicable;
- `scope:studio` — Studio authoring UX/host/editor;
- `scope:tooling` — CI, exporter implementation, golden/delegation/build/analysis infrastructure;
- `scope:contract` — intentionally cross-boundary interfaces and ownership seams.

Agent-state, owner-review, bug, design, and other workflow/type labels remain separate dimensions. An issue may carry multiple scope labels when its acceptance contract genuinely crosses owners; `scope:contract` is not a substitute for naming concrete owners.

When a Second Gate design need requires a reusable primitive, split it into linked issues only when responsibilities and acceptance tests genuinely differ. The game issue owns desired player/content behavior; runtime or Studio owns the reusable substrate/editor capability.

## Dependency principles for migration

Physical moves follow semantic repairs, not the reverse:

1. Extract runtime-owned implementation from Project-shaped `data/` so the exporter no longer needs a `dataRuntimeFiles`-style ownership exception.
2. Make runtime/default/Studio/Project/stage roots explicit and install a copied-Second-Gate portability gate, including release identity.
3. Resolve/rebase active branches that directly edit root Second Gate `data/**` / `assets/**` before moving the Project.
4. Move Second Gate into `projects/hichaukitoden-game/` as an ordinary Project with no root compatibility mirror.
5. Move reusable runtime under an explicit runtime root once active runtime/presentation branches have an explicit rebase plan.
6. Relocate Studio under an explicit Studio root after active Studio work settles, keeping neutral shared tooling outside Studio ownership.
7. Retaxonomize docs/reference/developer roots independently after product roots stabilize.
8. Delete obsolete path assumptions after consumers migrate; do not leave indefinite dual-read/fallback paths.

The earlier #385 semantic-classification gate is complete enough for this program: its RTP/default/New Project/Make Local follow-ups have landed. Future semantic questions remain owned by their own issues; #382 must not reopen #385 as a permanent excuse to defer physical ownership.

The bounded implementation issues created by the current-main refresh are:

- #698 runtime data-support extraction;
- #699 semantic roots + copied-Project portability/release-identity gate;
- #700 Second Gate Project physical move;
- #701 explicit runtime root;
- #702 explicit Studio root;
- #703 docs/reference/developer-root cleanup.

They are intentionally separate and should not be recombined into one mass move.

## Durable acceptance invariants

The eventual reorganization is complete only when:

- one monorepo remains the development model until concrete pressure justifies splitting;
- Project remains the independently runnable/authored game identity;
- `projects/hichaukitoden-game/` is an ordinary Project whose player-facing game is Second Gate;
- that Project can be copied externally and opened/validated/Test Played/exported through installed compatible Thestra without checkout-specific magic;
- Thestra supplies a versioned default authored/resource layer without creating a separately installed player RTP;
- normal exports are hermetic and players do not install shared defaults or Studio;
- runtime never depends on Studio/editor modules;
- editor chrome never silently borrows Project assets;
- Project `data/` contains Project-local authored/compiled semantic data, not runtime implementation support;
- exporter/staging does not need an exception equivalent to `dataRuntimeFiles`;
- generic installed runtime/export tooling does not silently impose Second Gate release identity on unrelated Projects;
- default-layer JSON/assets/templates are not classified by file type or path alone;
- Second Gate-specific material is not moved into defaults merely because Studio currently borrows it;
- runtime/default/Studio/Project/stage roots and resolution are semantic inputs rather than directory guesses;
- same-checkout development remains ergonomic without pretending install and Project roots are identical;
- authored-storage/resource-reference semantics remain fail-loud, Project-aware, and deterministic;
- G1-G4, unit/save, and relative visual gates remain meaningful through the move;
- G5/G6 owner-signed references are not recaptured merely because paths moved;
- Battle owner-supervised files are not behaviorally edited as collateral path cleanup;
- no Campaign compatibility alias, symlink tree, alternate Project root, root `data/`/`assets/` mirror, or premature package equivalence is introduced;
- a future GitHub/repository rename to Hichaukitoden is treated as identity/operations work separate from these physical ownership migrations.

Dated census/reports record evidence and current conflict/dependency ordering. Implementation status belongs in the bounded Issues and current authorities, not in this durable design.
