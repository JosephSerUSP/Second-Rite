# Thestra Scene Benchmarks

A neutral, playable Thestra Project that preserves small Scene-level authorability experiments outside Second Gate.

Play directly from the repository root:

```text
npm run lab:benchmarks
```

That command uses the same generic Project Test Play staging boundary as Studio; it does not open Studio first or introduce a lab-specific runner. To open the benchmark Project for editing instead, use `npm start -- --project projects/labs/scene-benchmarks`.

The launcher is ordinary Project-authored Scene data. Selecting a specimen pushes that Scene; `B` / Escape returns to the launcher. No benchmark-specific runtime or engine path exists.

## Current playable specimens

- **A003 — Snake** — real-time grid movement, ordered collection growth/collision, timing.
- **D002 — Sokoban as Scene** — discrete grid state, mutable collections, occupancy/push rules.

A001 Pong and A002 Breakout remain active benchmark definitions in `docs/agentic/JULES-CREATIVE-LAB.md`, but they are not listed here until an implementation actually lands.

## Benchmark lifecycle

Machine evidence may advance a specimen through `AUTHORED` and `MACHINE VALIDATED` to `READY FOR OWNER PLAYTEST`. Only the owner may mark it `OWNER PLAYTESTED`. Reports live under `reports/` and preserve both architectural evidence and owner observations.

This Project pins Thestra RTP revision `1.0` and is intentionally independent of root Second Gate authored content.
