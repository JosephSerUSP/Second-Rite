# Cross-Runtime Authority Audit — current-state index

**Original audit date:** 2026-08-18  
**Original audited main:** `726eabcd205cb405f2be780246068938698a9284`  
**Status:** evidence/index only; repository policy is unchanged here.

The original cross-runtime census and measurements are preserved byte-for-byte as the [audited baseline](cross-runtime-authority-audit-2026-08-18-baseline.md). Read its present-tense statements as **as-of `726eabcd` evidence**, not as a description of current production after the experiments that followed it.

## What changed after the audit

The audit proposed a destination taxonomy and the principle:

> **ONE SEMANTIC AUTHORITY, NOT NECESSARILY ONE EXECUTION HOST.**

Subsequent bounded work has now produced concrete evidence for three destination classes:

1. **Authoritative derived IR — landed.** #761 introduced compact exact Map definitions + placements and #766 landed direct Three consumption of runtime-authored `mesh-definitions-v1`. The historical compatibility expansion measured by #765 is **not** the current production Map consumer path.
2. **Genuinely LÖVE-bound authoring work — landed.** #754/#756 landed a narrow, serial, revision-scoped persistent LÖVE authority generation for compact Map renderables. Current production no longer cold-stages and cold-boots LÖVE for every compact `/api/map-renderable` request while non-transient authority inputs are unchanged. Expanded controls, Map Inspection and runtime-truth operations remain separate/cold as documented by #756.
3. **Pure deterministic shared semantics — positive experiment, not yet landed policy.** #772/#776 demonstrated one restricted TypeScript semantic leaf mechanically compiled to checked-in ordinary JavaScript and LuaJIT-target Lua for vertex shading and sprite timing. That PR is still under merge-readiness correction/review; do not describe its concrete mechanism as production until it lands.

#760/#769 also landed its geometry-budget evidence without changing production geometry ceilings. That result reinforces the distinction between **semantic/geometry quality policy** and **transport/process-host policy**: lowering a mesh ceiling is not a substitute for choosing the correct authority destination.

## Current interpretation of the baseline

The baseline remains useful for:

- the four destination classes;
- the authoring / compilation / runtime-truth clocks;
- the question **“why must this cross a process boundary?”**;
- the inventory of historical costs and duplicate semantics that motivated #772/#773;
- preserving rejected alternatives and the evidence available before the implementation experiments completed.

The following baseline statements are historical and must **not** be read as current production facts:

- that Studio still reconstructs compact Map definitions through the old compatibility expansion after #766;
- that each compact Map-renderable authoring request necessarily performs a fresh stage/snapshot plus cold LÖVE boot after #756;
- that #756/#766 are merely draft/proposed destination evidence.

## Policy ownership

This report still does **not** edit `AGENTS.md`. Issue #773 owns any architecture-policy migration and should consume **landed** evidence from #766 and #756 plus the final disposition of #772/#776. Final runtime truth remains real LÖVE/runtime execution for simulation, validation, Test Play, goldens, packaging, save/load and other operations where running the product is the semantic question.

For the full historical census, measurements, candidate taxonomy and rationale, read the [2026-08-18 audited baseline](cross-runtime-authority-audit-2026-08-18-baseline.md).
