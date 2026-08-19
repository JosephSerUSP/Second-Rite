---
type: archive-index
scope: game
status: historical
---

# Legacy repo design sources

These files are **frozen historical sources** moved out of the repository-level design authority by GitHub issue #778.

They preserve rationale, experiments, old numbers, old status language, and superseded proposals that are still useful as provenance. They are **not current game-design authority**. Start from the live Project docs in [`../../README.md`](../../README.md), then consult these sources only when the history matters.

Never infer implementation status from an archived source. Verify concrete authored values against Project `data/`, and use current GitHub Issues for unresolved work.

## Former `docs/game design/`

- `Permadeath.md` — historical loss/permadeath design.
- `Summoner.md` — historical Summoner/contracts/MP design.
- `idea_wall.md` — one-line idea fragment; archive only.
- `itemCreation.md` — historical item creation/cooking/fusion design.
- `sao-paulo-metro-stratum.md` — original Metro-stratum proposal.
- `stratum-revisit-spiral.md` — detailed revisit/progression proposal; current owner review is tracked by #677.

## Former game-specific `docs/design/`

- `actor-roster-expansion.md` — roster/content proposal.
- `battle-windows-brief.md` — battle presentation brief.
- `creature-naming.md` — creature naming language.
- `creature-parameters.md` — historical parameter/role/balance model.
- `elemental-combat-grammar.md` — detailed elemental combat grammar.
- `item-atlas-expansion.md` — item/content/atlas proposal.
- `portrait-art-direction.md` — portrait production/art direction.
- `skill-costs.md` — historical skill-cost/balance design.
- `summoner-rework.md` — historical Summoner role/resource rework.
- `ui-text-style.md` — game-UI writing/presentation style.
- `vertical-slice-balance.md` — historical vertical-slice balance protocol and numbers.
- `visual-language.md` — historical visual-production brief.

`docs/design/commercial-identity.md` was deliberately **not** copied into this public Project archive because it mixed durable game identity with commercial strategy. Durable game identity was rewritten into live Project docs; the commercial/source framing was migrated to the private Second Gate Studio workspace, while the exact original remains recoverable from Git history at blob `8b8443fdef4544544f3ec96ca33359042d478bcc`.

## Why archive instead of delete history

Several legacy documents mixed durable intent with implementation status, transient numbers, or proposals that later work changed. Copying them directly into the new Obsidian-facing live docs would recreate two problems:

1. stale prose would look current merely because it had a new path;
2. Project knowledge would grow back into a large pile of narrowly scoped files.

The live docs therefore synthesize the durable design; this directory keeps the source evidence.
