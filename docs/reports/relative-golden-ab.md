# Relative visual A/B evidence

The hosted relative workflow compares a candidate against a base ref on one pinned runner. It is regression evidence, not owner-signed golden correctness.

The sequence is base capture A, base capture B repeat control, then candidate. Decoded RGBA pixels are compared. Any frame that differs between the two base captures is named as unstable and excluded from the candidate verdict; a candidate-only difference on a repeat-stable frame is the regression signal.

G5 compares Classic and Wide separately and still runs the canonical center-crop invariant. The hosted runner has no Effekseer shim, so this answers whether the candidate changed rendering relative to the base under the same shimless renderer stack. It cannot answer whether either side matches the owner-machine committed goldens.

G6 uses the same recorder and repeat-control architecture. Browser/font/host drift therefore cancels when it is common to base and candidate, while live nondeterminism remains visible in the repeat control instead of being mistaken for a candidate regression.

Never recapture committed G5/G6 references because this workflow is red or green. Absolute G5/G6 remains owner-bound.
