# Thestra RTP baseline resources

This directory is an **installed authoring/runtime source**, not a player-installed dependency.
Projects select one exact revision through `data/system.json` -> `rtp.revision`. Resolution is typed: there is no directory overlay and no "latest installed" fallback.

## Revision identity and manifest

A revision is identified **semantically** — `1.0`, `1.1`, `2.0` — and lives at
`revisions/<version>/`. `data/system.json` -> `rtp.revision` holds that same
string verbatim. A major bump signals a change that can break an existing
Project's authored defaults; a minor bump signals additive content.

Each revision carries **exactly one** metadata file, `manifest.json`, describing
everything the revision provides. Its top-level sections mirror the three RTP
categories in `docs/design/thestra-rtp-authored-layer.md`:

| Key | Holds |
|---|---|
| `authored` | baseline/default authored compositions — engine registry, Scene and flow defaults |
| `resources` | baseline/default player-facing resources — binary assets, each carrying provenance and licensing evidence |
| `templates` | optional authored template/library content (not yet populated) |

A section is absent when the revision provides nothing in that category.

See `docs/design/thestra-rtp-authored-layer.md` for why both the identity scheme
and the single-file rule are frozen. The manifest's field-level schema is not.

## Provenance

The `resources` array is the provenance-bearing allowlist for player-facing
binaries introduced by issue #391. A resource is listed only when its source,
authorship, redistribution status, generic/RTP role, and player-facing role are
evidenced. Files which are convenient but whose redistribution status is
unresolved are deliberately absent.

The first baseline is intentionally incomplete. Missing generic preview art may use an explicit no-resource representation where the preview semantics support one, or fail visibly. Studio must never substitute Second Gate Project content or `tools/editor/Assets/**` chrome.

During Test Play/preview/export, only the RTP resources actually selected by the opened Project are materialized into the hermetic staged player tree. The player build therefore does not need an installed RTP.
