# Design-document status drift report

18 findings across the in-scope design documents. High-confidence findings are
explicit statements of current implementation, completion, or shipped state.
Uncertain findings are present-tense descriptions that may be design context,
but read sufficiently like runtime facts to record for review.

| file:line | quoted text | why it reads as status | confidence | resolution |
|---|---|---|---|---|
| `docs/design/authored-data-storage.md:115-137` | “Tileset Studio now exercises that contract end to end.” | “now” and the following numbered migration proof report a completed editor/runtime migration. | high | **resolved — true, relocated.** `tools/editor/server.js:247-326`, `tools/editor/authored-storage.js:279-295,393-421`, and `tools/editor/test-authored-storage.js:65-90` confirm compound tokens, stale-write rejection, record-local writes and fragment creation. The design doc now states the contract and activation criteria; this report retains the implementation fact. |
| `docs/design/content-engine-gaps.md:51` | “Seven weapons and one actor carried `CRI` while nothing in the engine ever rolled a critical, so the values are untested guesses now live as authored” | Reports the live data and engine behavior, including which implementation exists. | high | **deliberately left** — excluded load-bearing gap ledger. |
| `docs/design/content-engine-gaps.md:80-90` | “Expressible now …”; “`BATTLE` still starts only the current map's generic encounter”; “only Titania currently has matching art” | The mismatch column is a current implementation audit, not an intended behavior description. | high | **deliberately left** — excluded load-bearing gap ledger. |
| `docs/design/content-engine-gaps.md:127-148` | “Implemented, gated or unit-tested, and described in `SPEC.md` §1.9 (26.07.2026).” | A dated completion heading and proof claims record delivery status. | high — load-bearing ledger; left unchanged | **deliberately left** — excluded load-bearing status ledger. |
| `docs/design/content-engine-gaps.md:150-168` | “Battle mathematics, SPEC §1.11 (26.07.2026). Unlike the item slice, this one changed the golden logs” | Historical shipped-change narrative records implementation and verification. | high — load-bearing ledger; left unchanged | **deliberately left** — excluded load-bearing history. |
| `docs/design/content-engine-gaps.md:170-180` | “Note this was BROKEN by the growth change … and fixed here” | Explicitly reports a code change and its repair. | high — load-bearing history; left unchanged | **deliberately left** — excluded load-bearing history. |
| `docs/design/floor-ceiling-shader.md:8-18` | “Status: implemented and verified (19.07.2026) for the ceiling half … mechanically done … NOT added” | A dated status block directly reports implementation state. | high — load-bearing status note; left unchanged | **deliberately left** — excluded load-bearing status note. |
| `docs/design/floor-ceiling-shader.md:147-168` | “1. **Done.** … 6. **Not done.** Floor art … 7. **Not done.** `map.heights` scaffold” | A completion checklist tracks delivery in a design document. | high — load-bearing history; left unchanged | **deliberately left** — excluded load-bearing history. |
| `docs/design/fog-presets-and-panorama.md:8-14` | “Status: implemented (20.07.2026).” | Direct dated implementation-status declaration. | high — load-bearing status note; left unchanged | **deliberately left** — excluded load-bearing status note. |
| `docs/design/future-issues.md:44-121` | “~~…~~ FIXED (22.07.2026)” and similar entries | Completed checklists and dates track delivery in a design document. | high — load-bearing issue history; left unchanged | **deliberately left** — excluded load-bearing issue history. |
| `docs/design/item-atlas-expansion.md:148-178` | “These names are approved atlas entries, not implemented database records.” | Explicitly states which content has and has not shipped. | high — load-bearing atlas boundary; left unchanged | **deliberately left** — excluded load-bearing atlas boundary. |
| `docs/design/raycaster-tileset-lighting.md:8-13` | “Status: implemented (19.07.2026), first atlas … landed and verified” | Direct dated implementation and verification claim. | high — load-bearing status note; left unchanged | **deliberately left** — excluded load-bearing status note. |
| `docs/design/raycaster-tileset-lighting.md:141-188` | “**Authoring — done** … before this landed … **done differently than planned** … landed the rendering substrate” | Completion language and a shipped-substrate account report current/history state. | high — load-bearing history; left unchanged | **deliberately left** — excluded load-bearing history. |
| `docs/design/unit-actor-battler.md:74-98` | “`Battler.new` currently initializes … The Summoner-as-Battler design has been removed. The identity audit currently finds **zero Unit references**” | Describes live code and audit output rather than a desired architecture. | high — architectural audit; left unchanged | **deliberately left** — excluded architectural audit. |
| `docs/game design/Permadeath.md:78-87` | “`engine/scenes/battle.lua` handles `reap` but not `ward_save`, so a save is currently silent … does not exist yet” | Reports current engine/presentation gaps and owner-supervised pending work. | high — load-bearing open-work note; left unchanged | **deliberately left** — excluded owner-supervised open-work note. |
| `docs/game design/itemCreation.md:219-232` | “cooking currently has six”; “Only one promotion key exists”; “`CRAFT_YIELD_RATE` exists … it currently does not” | The open-work section uses live counts and runtime capability claims. | uncertain | **deliberately left — uncertain, load-bearing where it is.** The section is explicitly `Open`; `engine/craft.lua:222-252` confirms the live reach trait and normalized element direction, and `data/passives.json:268-281` confirms the `artisan` trait. Removing those facts would make the open-work list less informative, so the report's uncertain judgement is preserved. |
| `docs/design/skill-costs.md:18-21` | “`mpCost` exists on 33 of the 44 rows … Skill MP cost has been decorative since it was authored.” | A current-data audit and historical implementation claim appear in a design proposal. | uncertain | **resolved — false/stale.** Current `data/skills.json` uses charges/Overcast/cooldowns instead; `engine/usability.lua:185-210` delegates skill availability to `skill_cost`, and `engine/skill_cost.lua:1-13` makes Overcast the only skill path to shared MP. The stale audit was replaced with design rationale rather than inverted into pending work. |
| `docs/design/project-editor-runtime-boundaries.md:20-21` | “This is the cheapest invariant to lock in, and it is done: see the gate below.” | “it is done” asserts that the runtime/editor dependency gate has shipped. | high | **resolved — true, relocated.** `tests/test_runtime_boundaries.lua:65-93` enforces the dependency rule and `:95-121` carries a negative control. The design sentence now assigns authority to the gate without asserting completion; this report retains the verified status fact. |

## Files checked and found clean

I reviewed these in-scope files with the full-file status-candidate scan and
surrounding-prose inspection, and found no sentence that asserts implementation
status rather than describing intent, constraints, or clearly framed rationale:

- `docs/design/battler-inspection.md`
- `docs/design/battle-windows-brief.md`
- `docs/design/combat-state-resources.md`
- `docs/design/creature-naming.md`
- `docs/design/elemental-combat-grammar.md`
- `docs/design/event-driven-content.md`
- `docs/design/image-authored-geometry.md`
- `docs/design/portrait-art-direction.md`
- `docs/design/renderer-3d-roadmap.md`
- `docs/design/semantic-tiles-and-baked-lighting.md`
- `docs/design/skill-costs.md` (except the uncertain lines reported above)
- `docs/design/split-scenes-and-maps.md`
- `docs/design/summoner-rework.md`
- `docs/design/surface-junctions.md`
- `docs/design/tileset-and-events-redesign.md`
- `docs/design/ui-text-style.md`
- `docs/design/visual-language.md`
- `docs/design/widescreen-performance-study.md`
- `docs/game design/Summoner.md`
- `docs/game design/idea_wall.md`

The high-confidence balance-language candidates in
`docs/design/vertical-slice-balance.md` were reviewed separately. A mechanical
rewrite was rejected because the named behaviours are implemented; the design
document remains unchanged by this pass rather than being made to read as
pending work.

I did not inspect, edit, or treat as findings anything under `docs/archive/`,
`docs/SPEC.md`, `docs/ENGINE-STATE.md`, or `AGENTS.md` beyond the requested
instructions.
