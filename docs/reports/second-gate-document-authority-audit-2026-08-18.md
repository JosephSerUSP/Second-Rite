# Second Gate document-authority audit — 2026-08-18

Issue: #778

This report records the bounded authority audit that separated **Second Gate game design**, **Thestra/Studio technical design**, **private commercial strategy**, and **historical provenance**.

It is evidence about the migration, not a new design authority. Current Second Gate intent lives in `projects/hichaukitoden-game/docs/`; current engine/editor status remains in `docs/ENGINE-STATE.md` and reviewed architecture in `docs/SPEC.md`.

## Decision rules

1. **Project live** — durable Second Gate game intent is rewritten into a small number of Project-local live documents.
2. **Project archive** — game-specific legacy prose with useful rationale, stale numbers, status language, or superseded proposals is preserved verbatim under `projects/hichaukitoden-game/docs/archive/legacy-repo-design/` and removed from repo-level live design.
3. **Retain repo-level** — reusable Thestra runtime/presentation/RTP/Project/Studio architecture remains under `docs/design/`, even when Second Gate appears as a motivating fixture.
4. **Externalize commercial** — release, store, pricing, marketing, franchise, and studio strategy moves out of source-tree authority into the private Second Gate Studio workspace. Exact historical originals remain recoverable from Git history.
5. **Archive only** — fragments that do not deserve current design authority are preserved as history without a live rewrite.

The audit deliberately prefers **few strong live Project documents** over preserving the old one-file-per-proposal topology.

## New live Project authorities

- `projects/hichaukitoden-game/docs/game-vision.md`
- `projects/hichaukitoden-game/docs/gameplay/summoning-and-expedition.md`
- `projects/hichaukitoden-game/docs/gameplay/combat.md`
- `projects/hichaukitoden-game/docs/gameplay/items-and-crafting.md`
- `projects/hichaukitoden-game/docs/world/strata-and-return.md`
- `projects/hichaukitoden-game/docs/characters-and-creatures.md`
- `projects/hichaukitoden-game/docs/art-direction.md`

Numeric/current authored truth remains in Project `data/`; unresolved work remains in GitHub Issues. Legacy prose does not override either.

## `docs/game design/` disposition

| Legacy file | Classification | Disposition |
| --- | --- | --- |
| `Permadeath.md` | Project game design + stale status language | Preserve exact source in Project archive; durable loss/aftermath intent synthesized into `gameplay/summoning-and-expedition.md` |
| `Summoner.md` | Project game design + superseded/active MP details | Preserve exact source in Project archive; durable Summoner/contract/expedition intent synthesized into `gameplay/summoning-and-expedition.md`; current MP experiments stay in #372/#373 |
| `idea_wall.md` | idea fragment | Archive only; no live authority created |
| `itemCreation.md` | Project item/crafting design + old implementation notes | Preserve exact source in Project archive; durable intent synthesized into `gameplay/items-and-crafting.md` |
| `sao-paulo-metro-stratum.md` | Project world/stratum design | Preserve exact source in Project archive; durable Metro/world intent synthesized into `world/strata-and-return.md` |
| `stratum-revisit-spiral.md` | Project campaign/progression proposal | Preserve exact source in Project archive; stable revisit principle synthesized into `world/strata-and-return.md`; unresolved owner review remains #677 |

The directory is reduced to a compatibility `README.md` pointing to the Project authority.

## `docs/commercial/` disposition

| Legacy file | Classification | Disposition |
| --- | --- | --- |
| `README.md` | commercial index | Remove from live source tree after private migration |
| `release-plan.md` | release/commercial strategy | Migrate a dated provenance summary to private Second Gate Studio; remove live repo copy |
| `proof-build.md` | commercial proof/test strategy | Migrate a dated provenance summary to private Second Gate Studio; remove live repo copy |
| `store-positioning.md` | store/marketing strategy | Migrate a dated provenance summary to private Second Gate Studio; remove live repo copy |
| `gates-franchise-strategy.md` | catalog/franchise strategy | Migrate a dated provenance summary to private Second Gate Studio; remove live repo copy |

Private migration destination: **Second Gate — Studio → Legacy Commercial Source — GitHub migration 2026-08-18**. Those Notion pages are condensed provenance summaries with source blob identifiers, not replacements for Git history. Exact originals remain in repository history.

## `docs/design/` disposition

### Move out of live repo design

| File | Classification | Disposition |
| --- | --- | --- |
| `actor-roster-expansion.md` | Second Gate roster/content proposal | Project archive; durable roster principles → `characters-and-creatures.md` |
| `battle-windows-brief.md` | Second Gate battle presentation + implementation brief | Project archive; durable presentation intent → `gameplay/combat.md` / `art-direction.md`; reusable implementation remains governed by Thestra technical docs |
| `commercial-identity.md` | mixed game identity + commercial strategy | **Split**: durable game identity → live Project docs; commercial/source framing → private Studio migration; remove live repo copy; do not duplicate exact mixed source into public Project archive |
| `creature-naming.md` | Second Gate creature naming language | Project archive; durable naming principles → `characters-and-creatures.md` |
| `creature-parameters.md` | Second Gate creature/balance design with concrete numbers | Project archive; durable role principles → `characters-and-creatures.md` / `gameplay/combat.md`; current numbers remain Project data |
| `elemental-combat-grammar.md` | Second Gate combat design | Project archive; durable grammar → `gameplay/combat.md` |
| `item-atlas-expansion.md` | Second Gate item/content proposal | Project archive; durable item identity → `gameplay/items-and-crafting.md`; exact atlas/content values remain authored data/history |
| `portrait-art-direction.md` | Second Gate art direction | Project archive; durable portrait principles → `art-direction.md` |
| `skill-costs.md` | Second Gate balance/cost design with concrete numbers | Project archive; stable balance principle → `gameplay/combat.md`; current numbers remain Project data |
| `summoner-rework.md` | Second Gate Summoner/resource redesign | Project archive; durable role/pressure → `gameplay/summoning-and-expedition.md`; active resource experiments remain Issues |
| `ui-text-style.md` | Second Gate game-UI writing/presentation standard | Project archive; durable UI language → `art-direction.md` / `gameplay/combat.md` |
| `vertical-slice-balance.md` | Second Gate balance/test protocol with historical assumptions | Project archive; use as provenance only; current authored numbers/data and current test Issues own reality |
| `visual-language.md` | Second Gate visual-production brief | Project archive; durable visual direction → `art-direction.md` |

### Retain as Thestra/Studio/reusable technical design

| File | Reason to retain repo-level |
| --- | --- |
| `authored-data-storage.md` | authored-storage / Project infrastructure |
| `authored-scene-semantic-boundaries.md` | reusable authored Scene semantics |
| `authored-state-scopes.md` | reusable authored state/scoping semantics |
| `battler-inspection.md` | runtime/editor Battler inspection semantics |
| `campaign-vocabulary-and-exploration-gauntlets.md` | Project/Campaign vocabulary and reusable authoring/design-research method; explicitly guards Campaign from becoming a competing Project root |
| `combat-state-resources.md` | reusable combat-state semantic primitives and authoring/runtime boundary |
| `content-engine-gaps.md` | engine/content capability ledger and technical follow-up context |
| `editor-renderable-bundle.md` | Studio/runtime renderable transport architecture |
| `editor-ui-standard.md` | Thestra Studio editor UI standard |
| `event-actor-animation-state.md` | reusable Event/Actor animation semantics |
| `event-animation-controllers.md` | reusable Event animation-control semantics |
| `event-driven-content.md` | reusable authored Event/content architecture |
| `event-self-state.md` | reusable Event-local state semantics |
| `floor-ceiling-shader.md` | renderer/shader technical design/history |
| `fog-presets-and-panorama.md` | reusable renderer/authoring design/history |
| `future-issues.md` | repository architecture/follow-up provenance rather than game bible |
| `image-authored-geometry.md` | reusable asset/geometry pipeline architecture |
| `monorepo-ownership-boundaries.md` | repository/Project ownership architecture |
| `player-equivalent-membrane.md` | reusable runtime/editor authoring boundary |
| `progression-and-house-baseline.md` | reusable Thestra RTP house-baseline architecture; explicitly distinguishes reusable baseline from concrete Second Gate policy |
| `project-editor-runtime-boundaries.md` | Project/Studio/runtime ownership architecture |
| `raycaster-tileset-lighting.md` | renderer/tileset technical design/history |
| `renderer-3d-roadmap.md` | reusable renderer roadmap/history |
| `semantic-tiles-and-baked-lighting.md` | reusable tiles/lighting semantics |
| `source-semantic-compiled-boundary.md` | source/compiled semantic ownership architecture |
| `split-scenes-and-maps.md` | reusable Scene/Map architecture |
| `studio-editor-surfaces.md` | Thestra Studio surface architecture |
| `surface-junctions.md` | Studio/runtime surface architecture |
| `thestra-editor-scene.md` | Thestra Studio/editor Scene architecture |
| `thestra-rtp-authored-layer.md` | RTP/authored-layer architecture |
| `tileset-and-events-redesign.md` | reusable tileset/Event authoring design |
| `unit-actor-battler.md` | reusable Unit/Actor/Battler semantic contract |
| `widescreen-performance-study.md` | renderer/performance technical evidence |

A new `docs/design/README.md` makes this retained scope explicit: repo-level design may use Second Gate as a fixture, but concrete game content/lore/balance/branding is not silently promoted into Thestra policy.

## Adjacent entry points and history

- `projects/hichaukitoden-game/docs/README.md` becomes the live Second Gate design index and removes the pre-audit migration warning.
- `docs/game design/README.md` remains as a compatibility redirect so older links fail toward the new Project authority rather than toward stale files.
- `docs/design/README.md` states the retained Thestra/Studio scope.
- repository `README.md` is updated to distinguish Thestra technical design from Project game design and to describe the runnable Project at its real path.
- dated historical reports/archive material is not rewritten merely to hide its old paths. Those documents are evidence about their own time.
- the exact removed commercial originals remain in Git history; a private dated migration summary preserves their reasoning for Studio work.

## Explicit non-goal: broader repository taxonomy

Issue #703 still owns broader retaxonomization of reports, references, developer-convenience roots, and other repository material. #778 resolves only the **Second Gate game/commercial authority slice**. It does not use this migration as a pretext to reorganize unrelated technical evidence.

## Resulting authority model

```text
Thestra implementation/status
  -> docs/ENGINE-STATE.md + code/tests/gates

Thestra reviewed behavior/architecture
  -> docs/SPEC.md

Thestra/Studio design intent
  -> docs/design/

Second Gate game intent
  -> projects/hichaukitoden-game/docs/

Second Gate authored current content
  -> projects/hichaukitoden-game/data/ + assets/

Second Gate commercial/studio strategy
  -> private Second Gate — Studio workspace

Historical game-design source
  -> projects/hichaukitoden-game/docs/archive/legacy-repo-design/
```

This removes the previous ambiguity in which the Thestra installation's top-level documentation also acted as the apparent game bible.
