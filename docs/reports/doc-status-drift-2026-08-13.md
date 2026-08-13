# Design-document status drift report — 2026-08-13

Status: **dated point-in-time audit evidence**, not a living repository-status source.

Audited revision: `6a30018655566699fc5e948ba4113cb16f8eb7de` (`main`, after merged #367, #393 and #378).

Authority rule: `docs/ENGINE-STATE.md` owns what exists, `docs/SPEC.md` owns reviewed engine behavior, and `docs/design/**` plus `docs/game design/**` own durable intent/constraints rather than implementation status or delivery tracking. Historical `docs/reports/**` remain historical.

## Why this refresh exists

The first #377 audit was intentionally held behind #367 because it mixed the six-document #329/#360 cleanup corpus with genuinely additional drift. #367 is now merged, so this report was regenerated against the resulting current main rather than preserving pre-merge rows.

The six documents cleaned by #367 no longer contribute findings here:

- `docs/design/project-editor-runtime-boundaries.md`
- `docs/design/skill-costs.md`
- `docs/design/surface-junctions.md`
- `docs/design/tileset-and-events-redesign.md`
- `docs/design/unit-actor-battler.md`
- `docs/design/vertical-slice-balance.md`

The newly merged `docs/design/thestra-rtp-authored-layer.md` was also checked. Its `Status: durable architecture intent` label describes the document's authority, while current inventory evidence is deliberately delegated to its dated report; no implementation-status drift is recorded for it.

The intervening #378 merge added only `tools/balance/**` experiment-lab files, so it did not alter any audited design/game-design document or change the findings below.

## Remaining reproducible status-authority drift

The table groups related statements rather than treating every sentence in a status ledger as a separate issue. Locations are anchors at the audited revision.

| Document / anchor | Reproducible drift | Why it belongs elsewhere |
|---|---|---|
| `docs/design/raycaster-tileset-lighting.md:8-21`, `:141`, `:177-188` | Declares `Status: implemented`, describes what the raycaster/Town/editor already do, marks authoring work `done`, and carries a shipped/historical implementation-order section. | Durable renderer/tileset intent can stay, but delivered-state evidence and completion history belong in SPEC/ENGINE-STATE, tests, Issues, or a dated report. |
| `docs/design/floor-ceiling-shader.md:8-17`, `:147-168` | Opens with `implemented and verified`, reports current ceiling/floor behavior, then tracks `Done` / `Not done` implementation steps. | This is a delivery/status ledger embedded in a design plan. Keep shader/data-model rationale; move historical landing evidence out of design authority. |
| `docs/design/fog-presets-and-panorama.md:8` and nearby implementation narrative | Declares `Status: implemented (20.07.2026)` and explains the refactor as delivered current behavior rather than only as the intended compositing contract. | The design should state the fog/panorama contract without being a second current renderer census. |
| `docs/design/content-engine-gaps.md:51`, `:80-99`, `## Closed` from about `:127` onward | Mixes current-content census (`now live`, `currently`, `existing`), current capability claims (`Expressible now`), test/gate claims, dated “Implemented” sections, migration history, and large `Was blocked -> Now expressible as` tables. | The approved content requirements are useful design intent, but the `Closed` ledger is explicitly delivery history. It should become dated evidence / issue history or be reduced to durable requirements with current mechanics referenced to SPEC. |
| `docs/design/future-issues.md:33-121` | Contains multiple `FIXED` headings, “now calls/branches/renders” implementation descriptions, post-merge verification claims, and a sanctioned G2/G3 golden-update record. | Completed technical-debt history is neither future intent nor current authority. Open durable problems may remain as design rationale, but completed delivery records belong in Issues/reports. |
| `docs/game design/itemCreation.md:220-231` | The `Open` section reports current authored counts (`cooking currently has six`, one promotion key for many lines), current schema restrictions, sole trait holders, and current alignment-depth behavior. | Preserve desired crafting-space coverage and unresolved design questions; move live content/schema census to authoritative/current evidence or Issues. |
| `docs/game design/Permadeath.md:18-79` | `How it works`, `system.json defaults`, authored examples, and `Open work` describe current command/flow implementation and explicitly say `ward_save` presentation is currently silent / a displayed-status system does not exist yet. | The KO-at-battle-end and death-ward semantics are durable game design. Current handlers, authored instances, missing surfaces, and owner-supervised delivery state should not live as current truth here. |
| `docs/design/editor-renderable-bundle.md:95-101` | The transient-snapshot section states what the authoritative bridge currently accepts, names the live adapter/host wiring, cites a PR implementation consequence, and carries an `Until #237...` implementation blocker that has since been superseded by external-Project work. | Keep the resolved-bundle and transient-snapshot contract; remove or historicalize implementation census and stale delivery sequencing. |

## Findings deliberately not carried forward

- All rows from the six #367 documents were removed rather than marked “resolved” in the finding table.
- `docs/design/combat-state-resources.md` was re-read and the earlier candidate phrase “previous excess vitality is now ordinary HP capacity” is **not** repository status: it describes the result of a hypothetical HP arithmetic example. It is a false positive and is omitted.
- `docs/design/content-engine-gaps.md`'s Mirror Armor wording (“no claim of reflection unless reflection is implemented”) is conditional design language, not an assertion that reflection is or is not currently implemented; it is not counted independently.
- Historical dated reports were not reclassified as drift merely because they contain historical implementation facts. Their point-in-time status is their purpose.

## Cleanup shape suggested by the evidence

A later bounded cleanup should preserve the useful intent in these documents while removing the parallel status authority. In particular:

- convert `Done` / `FIXED` / `Closed` delivery ledgers into durable design statements or dated historical evidence;
- keep genuinely open product/design questions, but put actionable delivery work in GitHub Issues;
- replace current implementation/configuration claims with references to `docs/SPEC.md`, `docs/ENGINE-STATE.md`, tests, or dated reports where that evidence is worth preserving;
- do not rewrite historical reports to match the present;
- do not use the cleanup to change runtime behavior, authored data, or golden references.

This report does not edit any of the documents above. It is intended to be the evidence source for one later bounded documentation-authority cleanup issue/PR.

Agent-Signature:
  platform: ChatGPT
  model: GPT-5.6 Sol
  role: documentation-audit
  task: "PR #377 post-#367 drift refresh"
  base: 6a300186