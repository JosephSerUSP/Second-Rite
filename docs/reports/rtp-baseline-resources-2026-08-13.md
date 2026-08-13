# #391 — Neutral RTP preview and baseline resource report

Date: 2026-08-13
Base: `63010d0e3864a17c0a41d5d6c6ca674ad8d0f735`
Scope: issue #391 only; no #390 authored-registry ownership moves and no Battle owner-supervised files.

## Result

This change establishes revision **A** as the first deliberately provenance-gated player-facing RTP asset baseline and removes the known generic-preview dependency on Second Gate's `dungeon_001.png`.

The implementation keeps the #397 policy: Projects choose an exact `system.rtp.revision`; typed resources resolve through explicit policies; the installed RTP is an authoring/staging source only; resolved RTP bytes are copied into the hermetic player tree; a different/newer installed revision cannot silently replace the pinned one.

The baseline is intentionally small. One asset class cleared the evidence bar: **Jersey 10 Regular** as a player UI font. Missing neutral tileset art is left missing and fails visibly. Animation preview retains the already-supported no-sprite state rather than inventing a battler.

## Adopted resource

### `font.jersey10`

- **RTP path:** `rtp/revisions/A/assets/fonts/Jersey10-Regular.ttf`
- **Player logical path:** `assets/fonts/Jersey10-Regular.ttf`
- **Source:** Google Fonts `google/fonts`, `ofl/jersey10/Jersey10-Regular.ttf`.
- **Exact identity:** Git blob `6870bfd222d1fa0c32a20c1d348320bb9a04b9ed`. The pre-existing Project copy in this repository has that same blob identity; revision A reuses the exact bytes rather than making a derivative.
- **Authorship/provenance:** Google Fonts metadata names designer Sarah Cadigan-Fried and records `Copyright 2023 The Soft Type Project Authors`, sourced from `scfried/soft-type-jersey` commit `d8446c4c9c2ba14cf408c295be35213c006e19ff`.
- **Redistribution status:** SIL Open Font License 1.1. The exact upstream copyright/OFL notice is retained at `rtp/revisions/A/licenses/Jersey10-OFL.txt` and is copied into staged player output when the font is inherited.
- **Why generic:** it contains no Second Gate characters, setting, icon vocabulary, project names, or authored game content.
- **Why player-facing RTP rather than Studio chrome:** `presentation/ui.lua` loads configured player text fonts from `assets/fonts/<name>.ttf`. Studio's own toolbar/icon resources live under `tools/editor/Assets/**` and are not involved.

`rtp/revisions/A/resources.json` is the machine-readable provenance allowlist. Typed manifest entries are rejected when source/authorship/redistribution/generic/player-facing fields are absent.

## Resolution and preview behavior

### Fonts

Configured fonts now resolve as:

1. opened Project `assets/fonts/<name>.ttf`;
2. exact manifest-declared font in the Project's pinned RTP revision;
3. for legacy Projects with no RTP pin, preserve the existing LÖVE built-in fallback behavior rather than inventing inheritance.

The Studio font picker continues to show actual opened-Project fonts and additionally shows fonts declared by the exact pinned RTP revision. Project-local files win on name collision. Revision B existing beside A does not affect a Project pinned to A.

For an external Project, saved-data preview/Test Play uses the existing staging membrane, so an inherited font is materialized before the real engine renders the preview. Same resource bytes and the OFL notice are staged for export. The staged tree does not contain the installed `rtp/` source tree or Studio chrome.

### Tileset creation

The old creator logic was:

`Project template_tileset.png -> Project dungeon_001.png`

The second branch was an ownership violation: a generic authoring action could silently acquire Second Gate art merely because that Project happened to be the engine's development Project.

The new typed policy is:

1. existing opened-Project `assets/tilesets/template_tileset.png`;
2. exact manifest-declared `tileset-template` in the pinned RTP revision;
3. no resource.

Revision A deliberately declares no tileset template because the current generated `template_tileset.png` has authorship evidence in repository history but no sufficiently explicit redistribution grant under the repository-wide licensing findings. When no legitimate template exists, Tileset Studio reports a visible creation error. It never substitutes `dungeon_001.png`.

An already-existing Project texture named for the new tileset remains a Project-specific resource and can be used; this is intentionally distinct from generic default generation.

### Animation preview

No neutral sprite/battler/model is adopted. Current animation preview already preserves an empty sprite as a legitimate no-resource state. Adding a Second Gate battler or unproven placeholder would make provenance and ownership worse, not better.

## Rejected / deferred candidates

| Candidate | Decision | Evidence / reason |
|---|---|---|
| Current windowskins/frame/cursor/target/wait PNGs | Deferred | They are player-facing candidates, but the provenance inventory does not establish per-file redistribution rights strongly enough to promote them into a redistributable RTP baseline. |
| `assets/system/iconset.png` | Deferred | Player-facing, but the current vocabulary includes Second Gate policy/content (including race/evolution concepts) and its mixed provenance is not yet clean enough for a generic baseline. |
| `tools/editor/Assets/**` icons | Rejected as RTP | Studio chrome. Existing ownership tests require editor chrome to remain editor-owned; no player build should receive these resources because Studio uses them. |
| Current `data/sounds.json` | Deferred | Procedural/generic in form and already supported by #397 typed staging, but the current file originated in campaign-generation history and the repository-wide license is unresolved. No rights are inferred. |
| Generic `system.*` animations/effects | Deferred | Semantically good RTP candidates, but their effect/image dependencies need independent provenance classification before adoption. |
| Neutral preview sprite/model/battler | Not needed | Animation preview supports no sprite. No other audited generic preview requires inventing one. |
| `assets/tilesets/template_tileset.png` | Deferred | Repository history shows a project-owned generator produced it, but that does not itself establish redistribution terms for RTP packaging. The typed seam exists; the resource stays Project-local until rights are explicit. |
| Other bundled fonts | Deferred | #391 does not turn a mixed font directory into a blanket RTP library. Jersey 10 is adopted because exact upstream bytes + OFL evidence are independently verifiable. |

## Deterministic fixture coverage

Tests construct a minimal Project outside the repository, pin revision A, and deliberately install a differing revision B beside it. They prove:

- the configured Jersey font resolves from A, never B;
- the real staging boundary copies the resolved font and OFL notice into the hermetic player tree;
- deleting the Project and installed RTP after staging does not break the staged resource;
- Project-local fonts override the pinned baseline for Project-specific preview semantics;
- a planted `dungeon_001.png` cannot satisfy generic tileset-template resolution;
- a Project template wins over an RTP template when one is explicitly present;
- Studio chrome is absent from the staged player tree;
- the checked-in baseline Jersey blob remains exactly `6870bfd222d1fa0c32a20c1d348320bb9a04b9ed` and its OFL notice remains present.

## Owner decisions still required

1. Decide/record redistribution terms for the procedurally generated tileset template if it should become an RTP starter asset.
2. Establish per-file provenance/redistribution evidence for the player windowskin/cursor/target/wait set before any promotion.
3. Decide the eventual generic player icon vocabulary independently from the current Second Gate iconset; Studio toolbar icons should not be the source.
4. Audit effect dependencies before promoting generic `system.*` animations.
5. Evaluate other fonts one-by-one rather than treating `assets/fonts/**` as licensed wholesale.

No new artwork was generated, no mass asset move was performed, and no G5/G6 recapture is required for this resource-resolution infrastructure change.

Agent-Signature:
  platform: ChatGPT
  model: GPT-5.6 Sol
  role: implementation
  task: "#391 neutral RTP preview and baseline player-facing resources"
  base: 63010d0e3864a17c0a41d5d6c6ca674ad8d0f735
