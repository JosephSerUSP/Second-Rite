# Branch & Pull Request Hygiene Report

This report summarizes stale branches and pull requests based on recent repository activity.

### 1. Branches whose diff against main is empty
- `agent/385-thestra-rtp-authored-layer-current`
- `agent/400-authored-state-scopes`
- `agent/400-authored-state-scopes-current`
- `agent/414-scene-portability-audit`
- `agent/purge-campaign-protocol`
- `docs/396-remove-status-ledgers`
- `codex/161a-dispatch-relative-ab`

These branches are safe to delete as their content has fully landed in main.

### 2. Branches that are the head of a MERGED pull request but still exist
- `jules/doc-status-drift-2026-08-13-4496567766745375071`
These branches are safe to delete as their content has fully landed via squash merge.

### 3. Branches with no pull request, no commits in 14 days, and a non-empty diff against main
No branches found.

### 4. Open pull requests that are behind main
- PR #412 (`agent/398-st-maria-permission-save-roundtrip`) is behind main by 1 commit.
- PR #406 (`docs/396-remove-status-ledgers-current`) is behind main by 1 commit.
- PR #388 (`agent/pong-scene-template-pressure-test`) is behind main by 1 commit.
- PR #364 (`agent/258-branded-windows-launcher`) is behind main by 1 commit.
- PR #349 (`jules/branch-hygiene-2026-08-12-18177356593608998692`) is behind main by 1 commit.
- PR #336 (`codex/archive-g6-relative-investigation`) is behind main by 1 commit.
- PR #334 (`codex/stew-item-model-refinement`) is behind main by 1 commit.
- PR #280 (`issue-277-interactive-scene-editing`) is behind main by 1 commit.
- PR #279 (`issue-277-thestra-editor-scene`) is behind main by 1 commit.
- PR #257 (`compat/love12`) is behind main by 1 commit.
- PR #256 (`agent/fix-thestra-windows-app-icon`) is behind main by 1 commit.

### 5. Open pull requests in draft with no commits in 14 days
No open pull requests in draft have been inactive for over 14 days.
