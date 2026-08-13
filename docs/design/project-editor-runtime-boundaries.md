# Project / editor / runtime boundaries

Answers #237. #221 established what tree constitutes a *shipped game*; this
answers the complementary authoring question — what tree constitutes a
*project*, and what the installed editor/runtime provides around it.

> **Intent, not status.** This document defines the ownership and path-boundary
> contract. `docs/ENGINE-STATE.md` is the authority on what exists;
> `docs/SPEC.md` is the reviewed authority on how the engine works.

## Boundary model

The dependency direction is one-way: runtime code must not depend on editor or
tooling modules. Development-only CLI/test seams are explicit exceptions, not a
reason to let runtime ownership leak into `tools/`.

Export is the strict shipping boundary. `tools/export/runtime-manifest.json` is
the one allowlist for a shipped tree; this design must not introduce a second
exporter or a second definition of what ships.

The editor needs distinct ownership roots even when several of them happen to
coincide in a repository checkout:

| Root | Ownership |
| --- | --- |
| **Project root** | one independently runnable authored game: Project-local resources, overrides, and Project metadata |
| **Installation root** | Studio/editor tooling, engine/runtime code, native runtime support, installed Thestra-authored resources, build output |

Project-asset access is legitimate architectural coupling: a map editor must
preview the opened project's textures and authored content. The coupling to
avoid is treating installation-owned tooling and Project-owned content as one
path namespace.

The Project boundary is semantic rather than synonymous with a file format.
Authored JSON may be Project-owned, supplied by a pinned Thestra RTP revision,
or supplied by an explicit Package. Conversely, runtime-support files do not
become Project-owned merely because they are physically near authored data.

## Decisions

### 1. Two roots, not one

Use `PROJECT_ROOT` for the opened Project and `INSTALL_ROOT` for the Studio and
runtime installation. Every path join should state which ownership domain it
belongs to rather than relying on both roots having the same value.

Root derivation belongs in one shared path-resolution seam. `SECOND_RITE_PROJECT`
is the explicit selector for opening a Project outside the installation; an
unset selector may use the installation tree as the Project for ordinary
repository-local authoring. Invalid configured Project paths must fail at boot
with the path and reason rather than producing an apparently empty Studio.

### 2. Project-owned resource resolution, inherited authored layers, editor-owned chrome

Do not mistake legitimate Project-asset previews for architectural coupling.
Map, tileset, animation, item, icon, and other game-content previews resolve
through the same semantic resource ownership rules used by the opened Project.
Editor chrome resolves from editor-owned resources.

`assets/system/iconset.png`, for example, is game-facing content when it renders
authored icon ids; it is not Studio chrome merely because the editor also needs
to display it. Whether a particular game-facing resource is Project-local or an
inherited Thestra-authored default is a separate ownership decision.

Missing game content must be visibly missing. Resource presentation must
separate **failed** from **still loading**, release callers waiting on a resource
that cannot arrive, and render a conspicuous missing-resource placeholder rather
than silently borrowing an editor-owned copy.

There is no blanket filesystem fallback chain. Resolution is defined per
resource class. Where inheritance is legitimate, the conceptual order is:

```text
Project-local resource
    -> explicit Package dependency
    -> pinned Thestra RTP revision
    -> fail visibly
```

Some Project resources are required Project identity/content and deliberately
have **no** RTP fallback. Studio chrome is not another game-resource fallback;
it resolves only from Studio-owned resources. This distinction prevents a
broken Project or export from appearing healthy because the installation happens
to contain unrelated content.

### 3. Runtime and RTP are distinct; player exports are hermetic

The installed runtime implementation and the Thestra RTP are different ownership
layers. Runtime owns reusable implementation substrate. RTP is a versioned
Thestra-authored layer of baseline/default compositions, player-facing resources,
and optional authored templates built from the same authoring semantics exposed
to Projects.

RTP is not a separately installed player dependency. A Project may resolve a
pinned RTP revision while authoring, but export materializes every depended
runtime/RTP/Package/Project resource into the shipped game. The player receives a
hermetic game and does not install a shared RTP.

Which current `assets/` or authored-data resources belong to RTP versus a
specific Project is deliberately not decided here. Directory conventions such
as `assets/sprites`, `assets/system`, or JSON storage do not by themselves
establish ownership. Classification follows semantic role and consumers.

### 4. What a Project must contain

A Project is the canonical independently runnable/authored game identity. It
contains the Project-local resources and overrides that belong to that game plus
metadata sufficient to resolve its declared runtime compatibility, pinned RTP
revision, and any explicit dependencies required by its authoring model.

A Project may be sparse when legitimate resources are inherited from its pinned
RTP or explicit Packages; therefore the Project contract is not “all authored
JSON must physically live under the Project.” Resources that define Project
identity or that have no legitimate inherited default remain explicit Project
responsibilities.

**Campaign is not an alternative Project ontology.** Routes, stories, chapters,
or equivalent game structure are ordinary Project-authored game logic. Legacy
Campaign protocol may remain temporarily in dead code while #370 removes it, but
that cleanup does not reopen whether Campaign can be the runnable root. Future
Package and RTP composition are separate concepts and must not preserve Campaign
semantics under new names.

## Verification invariants

The boundary is considered sound only while all of these remain mechanically
checkable:

- Runtime code cannot depend on editor/tooling modules except explicit
  development-only seams.
- Editor-only files cannot enter an export.
- Project-relative paths cannot escape the selected Project root.
- A minimal Project outside the installation tree can be opened without copying
  it into the repository.
- Editor chrome cannot resolve through the opened Project's asset tree, and a
  missing game resource cannot borrow an editor copy.
- Preview and Test Play use the opened Project's resolved authored resources
  while runtime code comes from the Studio installation. External-Project launch
  must never silently fall back to checkout Project content.
- A Project resolves the declared RTP revision rather than whichever newer RTP
  happens to be installed.
- Export materializes all resolved runtime/RTP/Package/Project dependencies so
  the player build has no external RTP dependency.

These are invariants for tests and gates, not a delivery checklist. Their live
coverage belongs in the test suite and repository status sources.

## Non-goals reaffirmed

No second exporter. No package manager. No mass repository move — semantic
ownership is enforceable through named roots and gates without renaming a single
directory, and a move should only follow once the boundaries justify it, not
lead.
