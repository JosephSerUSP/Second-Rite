# Relative visual A/B evidence

The hosted relative workflow compares a candidate against a base ref on one pinned runner. It is regression evidence, not owner-signed golden correctness.

The sequence is base capture A, base capture B repeat control, then candidate. Decoded RGBA pixels are compared. Any frame that differs between the two base captures is named as unstable and excluded from the candidate verdict; a candidate-only difference on a repeat-stable frame is the regression signal.

G5 compares Classic and Wide separately and still runs the canonical center-crop invariant. The hosted runner has no Effekseer shim, so this answers whether the candidate changed rendering relative to the base under the same shimless renderer stack. It cannot answer whether either side matches the owner-machine committed goldens.

G6 uses the same recorder and repeat-control architecture. Browser/font/host drift therefore cancels when it is common to base and candidate, while live nondeterminism remains visible in the repeat control instead of being mistaken for a candidate regression.

Never recapture committed G5/G6 references because this workflow is red or green. Absolute G5/G6 remains owner-bound.

## First complete hosted proof

GitHub Actions run `31391808745` compared base `4e1af00952a963f3667d1babed54a160b22eef5a` against candidate `750f832ea1fa0d3cc183658380f800b5ee76aebf` on the same pinned Windows runner stack.

- G5 Classic: 144 frames captured for each side; base A -> base B = **0 differing frames / 0 changed pixels**; base B -> candidate = **0 / 0**.
- G5 Wide: 34 frames captured for each side; base A -> base B = **0 / 0**; base B -> candidate = **0 / 0**.
- G5's canonical Classic/Wide center-crop invariant passed during every materialized capture.
- G6 editor: all 38 frames captured for base A, base B, and candidate; repeat control = **0 differing frames / 0 changed pixels**; candidate = **0 / 0**.
- No G6 frame was unstable or excluded in this run. The earlier `map-editor/map-properties.png` nondeterminism from #253 therefore did not reproduce here, but this run by itself does not establish that issue's historical root cause.
- The previously reproducible `database/items.png` non-settling failure from #259 no longer occurs after model previews honor the standard reduced-motion preference used by deterministic G6 capture.

The proof also exposed one runner-integration requirement: the editor server resolves animation-preview LÖVE through `LOVE_PATH`, not through `PATH`. The workflow therefore points `LOVE_PATH` at the same pinned LÖVE installation used by the gate runner; that lets the real `/preview-anim` readiness contract complete rather than weakening G6's readiness condition.
