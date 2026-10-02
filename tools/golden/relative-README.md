# Hosted relative visual checks

`relative-capture.py` and `compare-relative.py` are CI adapters around the canonical gate recorder. They do not replace G5 or G6 and never update committed golden references.

`relative-capture.py` points the recorder at a detached worktree and writes `relative-capture.json` with an explicit `captureComplete` state. G5 needs two recorder passes because the absolute Classic comparison normally stops the canonical PowerShell gate before Wide on a hosted runner; the first pass reconstructs only a disposable Classic reference tree inside that worktree, and the second reaches the canonical crop check and Wide capture. G6 reconstructs the complete capture from the recorder's matching committed references plus its differing actual frames.

`compare-relative.py` consumes base A, base B, and candidate capture trees. It compares decoded RGBA pixels, names base-repeat instability, excludes unstable frames from candidate pixel verdicts, and distinguishes four operational states:

- **Green** — repeat-stable base and candidate captures agree exactly.
- **Red** — complete captures contain an unreviewed/rejected visual delta: changed pixels, new targets, missing/superseded targets, or any evidence that exceeds a previous approval.
- **Orange / expected delta** — a reviewer has explicitly approved the exact Red evidence fingerprint; canonical reference reconciliation is still pending.
- **Infrastructure / inconclusive** — capture completeness failed or the repeat control is unstable. This is not promotable to Orange.

New or missing targets are therefore not automatically infrastructure failures. When `relative-capture.json` proves both sides completed, a changed scripted frame topology is ordinary Red visual evidence until reviewed.

## Manual Red → Orange promotion

After investigating a Red run, use its emitted `report.json`:

```text
python tools/golden/promote-expected-delta.py \
  --report <report.json> \
  --id <short-id> \
  --reviewer <name> \
  --rationale "<what changed and why it is expected>" \
  --reference "#<PR-or-issue>"
```

The command refuses Green, infrastructure/incomplete, or repeat-unstable evidence. It writes a durable record under `tools/golden/expected-deltas/`; commit that record and rerun the same comparison.

The approval fingerprint covers the complete decoded base/candidate capture trees plus the named pixel/topology differences. Adding the approval file itself does not change the fingerprint. Any later changed pixel, added/removed target, or other visual evidence produces a different fingerprint and is Red again rather than inheriting the old approval.

Orange is transitional. An approved reference recapture/update should make the canonical absolute gate Green; the approval record is an audit trail, not a waiver and never authorizes recapture by itself.

The permanent operator interface is `.github/workflows/relative-golden-ab.yml` via `workflow_dispatch`.
