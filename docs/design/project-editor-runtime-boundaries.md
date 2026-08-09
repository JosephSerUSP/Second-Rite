# Project / editor / runtime boundaries

Answers #237. #221 established what tree constitutes a *shipped game*; this
answers the complementary authoring question — what tree constitutes a
*project*, and what the installed editor/runtime provides around it.

Written against the repository as of 09.08.2026, after #221 landed. Every
claim about current behaviour below was checked rather than assumed.

## What is actually coupled today

Worth stating precisely, because the coupling is narrower than it looks and
the cheap wins are not where the issue's framing suggests.

**The dependency direction is already almost right.** No file under `engine/`,
`presentation/`, or `data/*.lua` requires anything from `tools/` or `tests/`.
The single edge is `main.lua`'s `unittest` branch requiring `tests.fail_fast`
— lazily, inside a CLI-mode branch a player build never enters, and `tests/`
is not in the export manifest so it cannot ship. That is one documented
exception, not a systemic problem. **This is the cheapest invariant to lock
in, and it is done: see the gate below.**

**Export is already the strict boundary.** `tools/export/runtime-manifest.json`
is an allowlist, and a test asserts a newly added repository file does not
appear in a build. Nothing in this document may introduce a second exporter or
a second idea of what ships.

**The real coupling is the editor's, and it is one thing wearing three hats.**
`tools/editor/server.js` derives `PROJECT_DIR` as `path.resolve(__dirname,
'../..')` and uses it in 38 places. Those uses split cleanly:

| Uses | What it actually means |
| --- | --- |
| `assets/` ×7 | the opened project's art — **legitimate**, a map editor must preview real textures |
| `data/`, `campaigns/`, `campaign.json` | the opened project's authored content — **legitimate** |
| `tools/` ×3, `dist/`, `effekseer_shim.dll` | the *installation* — engine tooling, output root, native runtime |

So `PROJECT_DIR` is not one concept. It is **project root** and **installation
root** collapsed into one path because they happen to coincide in this
checkout. That collapse — not asset serving — is what stops the editor opening
a project elsewhere.

## Decisions

### 1. Two roots, not one — **done**

`tools/editor/server.js` now names `PROJECT_ROOT` (the opened project: `data/`,
`campaigns/`, `assets/`, `campaign.json`) and `INSTALL_ROOT` (the editor and
engine: `tools/`, the shim, `dist/`, `screenshots/`, and the cwd for running
LÖVE, which needs the directory holding `main.lua`). Both still resolve to the
repository, so no behaviour changed; the point is that the *names* stop lying
and every path join now states which root it means. A rename could not be
reviewed while the two were spelled identically.

Still to do: `PROJECT_ROOT` becomes explicit editor state — configuration with
the current checkout as its default — rather than a value derived from
`__dirname`. That is the change that lets the Studio open a project elsewhere,
and the two named roots are what make it a small change rather than an audit of
38 call sites.

### 2. Project-owned resource resolution, editor-owned chrome

The editor already gets this mostly right and the issue's non-goal is the
operative rule: *do not mistake legitimate project-asset previews for
architectural coupling.* Map, tileset and animation previews must keep reading
the opened project.

The genuine violation is narrower: editor chrome that reaches into the
project's asset tree for its own UI. `assets/system/iconset.png` is the case —
`icon-renderer.js`, `icon-picker.js` and `icon-field.js` fall back to it for
editor iconography. An iconset is authored game content; a project that
replaces it should change the *game*, and a project that lacks one should not
break the editor's chrome. Editor-owned defaults belong beside the editor
(`tools/editor/Assets/`, which today holds exactly one file).

Resolution order for any resource the editor renders:

```
project resource  ->  shared runtime default  ->  editor-owned fallback
```

with the last step reserved for editor chrome, never for game content. A
missing *game* asset must stay visible as missing rather than silently
borrowing an editor copy — that is how a broken export ships.

### 3. The shared layer is "runtime", and it is vendored, not installed

Call it `runtime`, not RTP. The RTP analogy is useful for *versioned shared
resources* and actively harmful for *separately installed player-side
packages*: hermetic export is already the established direction (#221), and a
player-installed dependency would undo it.

So: shared runtime resources are **materialized into every build** at export
time, and the build manifest records which runtime version produced it —
`build-manifest.json` already carries `productVersion` and `sourceCommit`, so
this is a field, not a system.

Which of today's `assets/` subtrees are shared-runtime versus Second Rite
content is deliberately **not** decided here. The measurement that would decide
it (engine path conventions versus authored references) shows engine code
hardcoding *directory conventions* — `assets/sprites`, `assets/system` — while
authored data supplies the *filenames*. That is a naming contract, not
ownership, and splitting the tree on it would be guessing. It needs a pass over
what a second project would actually have to supply, which is a separate piece
of work.

### 4. What a project must contain

Minimum contract: a project root holding authored data in the shape
`data/`-or-`campaigns/<name>/` already defines, plus project metadata naming
its compatible runtime version. `campaign.json` stays a *local pointer*, not
part of the project contract — #221 already established it must not ship.

Whether the campaign *is* the project or one campaign inside a project root is
deferred. Both work with everything above, and the answer depends on whether a
project ever ships more than one campaign — a product question, not an
architectural one.

## Gates

The repo treats architecture rules as gates rather than prose. Enforceable
today, in order of cost:

- [x] **Runtime code cannot depend on editor/tooling modules.** Implemented as
      `tests/test_runtime_boundaries.lua`, with `main.lua`'s dev-mode
      `tests.fail_fast` require as the one declared exception. A new edge fails
      the suite and names the file.
- [x] **Editor-only files cannot enter an export.** Already enforced by the
      runtime manifest allowlist plus its "new unrelated file is not exported"
      test (#221).
- [ ] Project paths cannot escape the selected project root. Cheap once
      decision 1 lands and every join names a root.
- [ ] Editor chrome cannot resolve through the opened project's asset tree.
      Needs decision 2's fallback chain first.
- [ ] A minimal fixture project opens and previews from outside this
      repository. The real proof of decision 1, and the point at which the
      Developer Studio stops being a tool that only works inside its own
      checkout.

## Non-goals reaffirmed

No second exporter. No package manager. No mass repository move — the
semantic ownership above is enforceable through named roots and gates without
renaming a single directory, and a move should only follow once the boundaries
are proven, not lead.
