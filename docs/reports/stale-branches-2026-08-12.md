# Stale Branches and Pull Requests Report

Point-in-time census against `main` at `fd284a222a06d1fc8120905b7d9fbd2b8ab48251` (merged #363), on 2026-08-12. The snapshot contains 20 non-`main` remote branches and 8 open PRs.

Classification is based on content/disposition evidence: exact tip equality where available, open-PR association, merged/superseded replacement history, and the earlier #349 merge-tree result where still applicable. Ahead/behind counts and branch age are not classification criteria.

## 1. Fully landed / content-equivalent — safe to delete

- `agent/issue-291-visibility-profiles` — the earlier #349 merge-tree census found no residual merge result, and #291's canonical visibility-profile implementation subsequently landed through merged #300. The integrations since that census do not create a new branch-only deliverable here.

## 2. Branches backing currently open PRs — keep

- `agent/258-branded-windows-launcher` — PR #364; active #258 Windows launcher work created during this census.
- `jules/branch-hygiene-2026-08-12-18177356593608998692` — PR #349; this report.
- `codex/archive-g6-relative-investigation` — PR #336; evidence/archive PR remains open.
- `codex/stew-item-model-refinement` — PR #334; model refinement PR remains open.
- `issue-277-interactive-scene-editing` — PR #280; active stacked PR2 for the 3D editor.
- `issue-277-thestra-editor-scene` — PR #279; active stacked PR1 for the 3D editor.
- `agent/fix-thestra-windows-app-icon` — PR #256; still open. PR #364 explicitly plans to reconcile this identity work, so it should not be treated as stale while that relationship is unresolved.

## 3. Intentional long-lived laboratory — keep

- `compat/love12` — PR #257 is explicitly a long-lived **DO NOT MERGE** LÖVE 12 compatibility/golden-review shadow. It is observation infrastructure, not ordinary stale branch debris.

## 4. Superseded / spent experiments — safe to retire, but not because of ancestry

- `agent/issue-291-geometry-profiles` — pre-#300 #291 experiment with temporary validation/evidence workflow work; #291 is completed by merged #300 and this branch has no PR.
- `agent/161a-prepared-map-lru` — PR #297 was explicitly superseded by #312; the prepared-map implementation was later replaced and landed through merged #324.
- `codex/161a-prepared-map-lru-refresh` — PR #312 was explicitly superseded by merged #324, which corrected the lifecycle identity problem and landed the final implementation.
- `codex/161a-negative-invalidation-control` — PR #314 was a disposable negative-control branch, closed unmerged with the planted breakage removed; its #312 base is also superseded by #324.
- `codex/161a-dispatch-relative-ab` — PR #315 was a disposable workflow-dispatch branch, closed with its temporary dispatcher removed and explicitly marked never to merge.
- `audit-trait-registry-308-4963293718259087089` — PR #319 was superseded by merged #320; its useful evidence was retained in #320's reconciliation supplement.
- `jules-report-pr-313-7033640399862645222` — PR #323 was superseded by merged #320; the useful authored-usage census was retained, while conflicting classifications were deliberately not imported.

## 5. Unique work still needing review — do not delete

- `agent/tileset-resolved-surface-inspector` — no PR is associated with the branch, and it still carries a substantive resolved-surface inspector implementation plus editor/runtime-bridge integration and tests. It needs explicit review/disposition before cleanup.

## 6. Ambiguous / apparently in-flight — owner disposition before deletion

- `agent/remove-campaign-root-ontology` — currently points exactly at the census `main` tip and has no PR, so it has no unique content **at this snapshot**; treat it as a possible live task/worktree placeholder rather than deleting it automatically.
- `agent/308-next-semantic-slice` — appeared during this census, currently points exactly at `main`, and has no PR. Its timing makes it look in-flight despite having no unique content yet.
- `agent/360-design-doc-status-cleanup` — advanced during this census and has no PR yet; this is active-looking unique work, not stale cleanup material.

## Already absent — no cleanup action

The remote branches that backed newly merged #357, #358, #361, and #363 are already absent from the current remote branch list. The old report's `jules/doc-status-drift-2026-08-12-7835731813963391150` branch is also already absent.

No branches, worktrees, PRs, or unique work were deleted, closed, merged, or discarded as part of this census.

Agent-Signature:
  platform: ChatGPT
  model: GPT-5.6 Sol
  role: documentation
  task: "#349"
  base: fd284a222a06d1fc8120905b7d9fbd2b8ab48251
