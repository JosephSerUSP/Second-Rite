# PE Day 4 reference contract

This directory contains **facts and design contracts only** for the St. Francis
Hospital vertical slice (#1463/#1464). It must never contain extracted game
assets, decompiled code, manual scans, screenshots, video frames, ripped models,
backgrounds or GUI art.

The public repository may record *facts learned from* private owner reference
material. Private media remains outside the repository.

## Fact statuses

`facts.json` deliberately distinguishes evidence strength:

- `verified` — grounded directly in a primary/manual/owner-observed source.
- `corroborated` — at least two **independent source groups** agree.
- `single_source` — useful for planning, but not strong enough for an
  original-faithful numeric regression claim.
- `prototype` — a deliberate Thestra/slice assumption. It is not a claim about
  Parasite Eve.
- `unknown` — unresolved or conflicting.

A source's `independenceGroup` matters more than URL count. Two mirrors or two
pages derived from the same guide do not count as two independent sources.

## Promotion rules

1. A numeric gameplay fact may drive an `original-faithful` assertion only when
   it is `verified` or `corroborated`.
2. `single_source` facts may bootstrap implementation, but the implementation
   and test must preserve that weaker status rather than silently converting the
   value into canon.
3. `prototype` values must carry their rationale at the authored source. Tests
   may protect them as slice behavior, but must call them prototype behavior.
4. Conflicts stay visible. Add a `disagreements` entry; do not pick the most
   convenient number.
5. If a later source changes a fact, update the fact first and let dependent
   tests/data fail. Do not patch around the contract.
6. Private reference paths are intentionally absent. A checkout must not need
   the owner's private pack to validate the public fact contract.

Run:

```text
python projects/pe-day4/tools/verify_reference.py
```

The verifier checks evidence statuses/source groups, cross-file fact links,
route/state vocabulary and whether the mandatory route is statefully reachable.

## Snapshot semantics

`canonical-start.json` is **canonical for this vertical slice**, not a claim
that all original Day-4 saves have the same inventory. Days 1–3 allow player
choice, item consumption, tuning and BP expenditure; importing an arbitrary
late-Day-3 save would make mechanical acceptance irreproducible.

The snapshot therefore normalizes player-dependent history while retaining
guaranteed story/boss grants where useful. Every normalization is explicit.