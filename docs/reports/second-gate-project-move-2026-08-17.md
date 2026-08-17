# Second Gate Project move — 2026-08-17

Issue: #700  
Dependency spine: #698 → #699 → #700

## Result

Second Gate is now an ordinary in-repository Thestra Project at:

`projects/hichaukitoden-game/`

Its Project-owned trees are:

- `projects/hichaukitoden-game/data/**`
- `projects/hichaukitoden-game/assets/**`

The repository/install root no longer owns `data/` or `assets/` compatibility copies.

The physical move reused the existing Git tree objects for both directories. The migration did not regenerate, rewrite, or recapture game assets merely to change ownership topology.

## Root contract

`tools/semantic-roots.js` now treats the default Project as explicit policy:

`projects/hichaukitoden-game`

Installation/repository, runtime, RTP/defaults, Studio, and Project roots remain separate semantic inputs. In normal checkout use the default Project is deliberately **not** the installation root.

The runtime installation is allowed to be non-Project-shaped. A future runtime/Studio relocation therefore changes their own semantic roots rather than reintroducing game content at repository root.

## Verification architecture

Repository verification no longer assumes that the repository itself is runnable game content.

`tools/ci/stage-project-gates.js` uses the canonical exporter/staging boundary to materialize the default Project with installed Thestra. Repository-only Lua test fixtures are then added to that disposable verification tree for the `unittest` command; they are not added to player exports or Project source.

The required verification lane runs G1, unit, save, G2, G3, G4, and reachability against that staged Project. Repository-owned golden references and `docs/ENGINE-STATE.md` remain outside the Project.

G5 likewise stages the explicit default Project before executing the existing real renderer screenshot/crop commands. No canonical G5/G6 recapture is authorized merely because directories moved.

## Portability ratchet

`tools/editor/second-gate-portability-smoke.js` now proves all of the following:

- installation root is not a Project;
- root `data/` and `assets/` are absent;
- the relocated default Project owns both trees;
- only Project-owned material is copied to a temporary external root;
- installed Thestra stages and validates that external copy;
- normal `.love` export succeeds;
- changing only the copied Project's `data/project.json` changes exported application/save/window identity;
- installed Second Gate naming does not leak into the rewritten external Project.

This is the permanent topology ratchet. It must not be replaced with aliases, symlinks, compatibility copies, or a Second Gate-specific staging pipeline.

## Consumers migrated in this slice

The move updates or exercises explicit Project ownership in:

- Studio Project bootstrap/root tests;
- Project create/fork/generator compatibility bootstrap;
- exporter/default/RTP materialization;
- required repository verification;
- G2/G3/G4/G5 launch paths;
- Model import production fixtures and hosted consumer;
- authored-default production fixture;
- sparse/default-Project validation;
- player-membrane proof;
- encounter lab;
- Blender Map export;
- Studio Playwright root-change triggers;
- runtime-data-boundary triggers;
- developer `run.bat` convenience launch.

A case-sensitivity portability defect surfaced during the move: Second Gate owned `04B_03__.TTF` while its semantic logical font path is `.ttf`. Project font lookup now resolves `.ttf` extension casing portably and fails loud on ambiguous case-colliding files; staged output keeps the canonical logical path.

## Deliberately preserved boundaries

- Same-root Test Play's compiled-data snapshot remains an optimization when runtime and Project roots truly coincide; equality is not an ownership definition.
- Root `conf.lua` remains current developer/runtime configuration and is not exported as Project release identity. Project release identity remains owned by `data/project.json` through #699.
- Runtime and Studio physical consolidation remain later #701/#702 work.
- No game mechanics, authored content semantics, or Battle behavior are changed by #700.

## Historical asset PR disposition

Before the move, stale root-path asset PRs #599 and #614 were closed as preserved reference branches rather than rebased through the ownership migration. Their reusable pipeline/presentation findings remain available, but their historical root `assets/**` implementations are not part of the new ownership contract.

## Handoff to #701 / #702

Do not infer Project ownership from the new nested path. Use the semantic root provider.

Runtime consolidation should treat `projects/hichaukitoden-game/` as an external consumer of installed Thestra even though both currently live in one monorepo. Studio consolidation should likewise preserve explicit Project selection rather than acquiring a relative dependency on the relocated game's directory.
