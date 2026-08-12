# Document Status Drift Report

Audited revision: `2794c0a599b7f68312d8cce9bb437b01ddf4`
Audit date: 2026-08-12
Status: point-in-time audit evidence; not a living repository-status record

This report identifies sentences in design documents that assert implementation status, shipped features, or current behavior instead of restricting themselves to design intent as mandated by `AGENTS.md`.

## Findings

These findings describe status-drift statements that existed in the audited revision. Later edits may already have corrected some findings, and absence from this report does not guarantee that a document remains clean forever. Current implementation truth is governed by `docs/ENGINE-STATE.md`, the code, and the document-authority rules in `AGENTS.md`; this report is not a current implementation-status source.

For this audit, design language such as “The system should…”, “The intended architecture is…”, or “This design requires…” is legitimate intent. Claims such as “The engine currently…”, “X is now implemented…”, “done”, or “the live schema accepts…” are status assertions and are findings when they occur in intent-only design documents.

- `docs/design/project-editor-runtime-boundaries.md:45`
  - **Quote:** "### 1. Two roots, not one — **done**"
  - **Why:** The section heading asserts that the feature is done.

- `docs/design/project-editor-runtime-boundaries.md:47`
  - **Quote:** "`tools/editor/server.js` now names `PROJECT_ROOT` (the opened project: `data/`, `campaigns/`, `assets/`, `campaign.json`) and `INSTALL_ROOT` (the editor and engine: `tools/`, the shim, `dist/`, `screenshots/`, and the cwd for running LÖVE, which needs the directory holding `main.lua`)."
  - **Why:** Asserts what the implementation "now names", rather than what it *should* name.

- `docs/design/project-editor-runtime-boundaries.md:52`
  - **Quote:** "Both still resolve to the repository, so no behaviour changed; the point is that the *names* stop lying and every path join now states which root it means."
  - **Why:** States that the behaviour didn't change and what the code "now states".

- `docs/design/project-editor-runtime-boundaries.md:55`
  - **Quote:** "`tools/editor/project-root.js` now resolves both and is the only place either is derived."
  - **Why:** Asserts the current responsibility and state of a specific source file.

- `docs/design/project-editor-runtime-boundaries.md:88`
  - **Quote:** "Missing game content must be *visibly* missing: the renderer now distinguishes \"failed\" from \"still loading\", releases the callers waiting on an image that is never coming, and draws a hatched placeholder that cannot be mistaken for art the game would draw."
  - **Why:** Asserts what the renderer implementation "now distinguishes" and "draws".

- `docs/design/tileset-and-events-redesign.md:104`
  - **Quote:** "`engine/exploration.lua`'s currently-hardcoded room/corridor/injection logic moves into data files driven by the *same* rule schema as decoration placement (§3) — one rule format feeds both \"what tiles exist\" and \"where do events go\"."
  - **Why:** Characterizes the current state of `engine/exploration.lua` as "currently-hardcoded".

- `docs/design/tileset-and-events-redesign.md:135`
  - **Quote:** "1. **Attachment + wall-face rendering.** Events currently float on `(x,y)` regardless of what's at that cell and always render as a billboard sprite (`presentation/viewport_3d.lua:876-887`)."
  - **Why:** Describes how events "currently float" in the live engine implementation.

- `docs/design/unit-actor-battler.md:74`
  - **Quote:** "`Battler.new` currently initializes some persistent-creature fields as well as universal battle state."
  - **Why:** Directly reports the current initialisation behaviour of the implementation.

- `docs/design/unit-actor-battler.md:213`
  - **Quote:** "For example, the player-owned creature called **Saban** is currently built from the species-level `homunculus` Actor plus an explicit `level`, `mhp` parameter, `skills`, and equipment."
  - **Why:** Describes the current engine configuration and composition for a specific creature.

- `docs/design/surface-junctions.md:44`
  - **Quote:** "Note what is *not* the cause. The decimator was suspected twice and cleared twice: mirrored tiles decimate their seams identically (a test now pins this), and the seam machinery already reduces a mesh's own two borders in lockstep."
  - **Why:** Claims that a test "now pins this" and describes what the seam machinery "already reduces".

- `docs/design/surface-junctions.md:118`
  - **Quote:** "This is also the answer to the wall-corner seams reported alongside the floor holes: two wall runs meeting at a right angle are two surfaces sharing a corner edge, and nothing currently makes them agree about it."
  - **Why:** Diagnoses a current rendering artefact and states what the live engine "currently makes them" do.

- `docs/design/skill-costs.md:365`
  - **Quote:** "The trait registry has `CRI` (base 5%) but **no counterpart**, so there is currently no way to buy that defense."
  - **Why:** Describes the state of the trait registry and asserts a current limitation in the engine.

- `docs/design/vertical-slice-balance.md:39`
  - **Quote:** "The slice now uses a provisional flat reward of **15 EXP per ordinary victory**, reaching level 10 in 45 victories."
  - **Why:** Reports the currently configured EXP reward in the live vertical slice.

- `docs/design/vertical-slice-balance.md:44`
  - **Quote:** "### Dungeon danger now has an authored level ramp"
  - **Why:** Asserts that an authored level ramp has been added/is live.

- `docs/design/vertical-slice-balance.md:46`
  - **Quote:** "Map encounter entries now accept:"
  - **Why:** Claims that the data schema "now accept"s a specific configuration.

- `docs/design/vertical-slice-balance.md:60`
  - **Quote:** "Floors 1-3 now use the provisional 1-3, 3-6, and 6-10 bands."
  - **Why:** Asserts the current configuration used by specific floors.

- `docs/design/vertical-slice-balance.md:73`
  - **Quote:** "All dungeon maps currently inherit `combat.encounterChance = 0.1`; the authored `encounterSteps` field does not drive the live encounter check."
  - **Why:** Reports exactly what all dungeon maps currently inherit and how the live engine check works.

- `docs/design/vertical-slice-balance.md:105`
  - **Quote:** "The Floor 1 hidden-workshop reward now guarantees a Mystic Egg, Pão de Queijo, and Onigiri alongside its existing quest reward."
  - **Why:** Asserts the current contents of a specific reward.

## No findings at the audited revision

The following files had no non-exempt status-drift findings at the audited commit:

- `docs/design/actor-roster-expansion.md`
- `docs/design/authored-data-storage.md`
- `docs/design/battle-windows-brief.md`
- `docs/design/battler-inspection.md`
- `docs/design/combat-state-resources.md`
- `docs/design/commercial-identity.md`
- `docs/design/content-engine-gaps.md`
- `docs/design/creature-naming.md`
- `docs/design/creature-parameters.md`
- `docs/design/editor-renderable-bundle.md`
- `docs/design/editor-ui-standard.md`
- `docs/design/elemental-combat-grammar.md`
- `docs/design/event-driven-content.md`
- `docs/design/floor-ceiling-shader.md`
- `docs/design/fog-presets-and-panorama.md`
- `docs/design/future-issues.md`
- `docs/design/image-authored-geometry.md`
- `docs/design/item-atlas-expansion.md`
- `docs/design/portrait-art-direction.md`
- `docs/design/raycaster-tileset-lighting.md`
- `docs/design/renderer-3d-roadmap.md`
- `docs/design/semantic-tiles-and-baked-lighting.md`
- `docs/design/split-scenes-and-maps.md`
- `docs/design/summoner-rework.md`
- `docs/design/ui-text-style.md`
- `docs/design/visual-language.md`
- `docs/design/widescreen-performance-study.md`
- `docs/game design/Permadeath.md`
- `docs/game design/Summoner.md`
- `docs/game design/idea_wall.md`
- `docs/game design/itemCreation.md`
