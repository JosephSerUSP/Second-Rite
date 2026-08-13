# Thestra RTP baseline resources

This directory is an **installed authoring/runtime source**, not a player-installed dependency.
Projects select one exact revision through `data/system.json` -> `rtp.revision`. Resolution is typed: there is no directory overlay and no "latest installed" fallback.

`revisions/A/resources.json` is the provenance-bearing allowlist for player-facing binary/assets introduced by issue #391. A resource is listed only when its source, authorship, redistribution status, generic/RTP role, and player-facing role are evidenced. Files which are convenient but whose redistribution status is unresolved are deliberately absent.

The first baseline is intentionally incomplete. Missing generic preview art may use an explicit no-resource representation where the preview semantics support one, or fail visibly. Studio must never substitute Second Gate Project content or `tools/editor/Assets/**` chrome.

During Test Play/preview/export, only the RTP resources actually selected by the opened Project are materialized into the hermetic staged player tree. The player build therefore does not need an installed RTP.
