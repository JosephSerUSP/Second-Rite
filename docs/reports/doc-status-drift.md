# Design-document status drift report

51 findings across the in-scope design documents.

| file:line | quoted text | why it reads as status |
|---|---|---|
| `docs/design/split-scenes-and-maps.md:18` | “- direct scripts that currently assume `<root>/maps.json` or” | Uses 'currently' to assert present implementation behavior or state. |
| `docs/design/combat-state-resources.md:120` | “Most of the previous excess vitality is now ordinary HP capacity; only 5 HP is” | Uses 'now' to describe completed balance adjustments. |
| `docs/design/monorepo-ownership-boundaries.md:68` | “The default layer is a versioned Thestra-authored library, not merely a fallback directory. It may include baseline/default compositions and reusable Scene/Event/etc. templates built on the same authored substrate available to Projects. Project-specific material must not be promoted into this layer merely because Studio currently borrows it for preview or authoring. Future package semantics remain separate under #325 even if implementation later discovers shared infrastructure.” | Uses 'currently' to assert present implementation behavior or state. |
| `docs/design/monorepo-ownership-boundaries.md:74` | “Before wholesale relocation, #385 must classify default-layer candidates by consumer and authoring intent. Project-specific material stays Project-owned even when Studio currently uses it incidentally. Conversely, a genuinely Thestra-supplied baseline resource need not remain Second Gate-owned merely because it originated under a Project-shaped path. Unresolved assets stay unresolved until evidence establishes ownership.” | Uses 'currently' to assert present implementation behavior or state. |
| `docs/design/monorepo-ownership-boundaries.md:147` | “- Second Gate-specific material is not moved into defaults merely because Studio currently borrows it;” | Uses 'currently' to assert present implementation behavior or state. |
| `docs/design/editor-ui-standard.md:10` | “how it currently does. Where the editor disagrees with this document, the editor” | Uses 'currently' to assert present implementation behavior or state. |
| `docs/design/fog-presets-and-panorama.md:75` | “A map's `fog` field is now either:” | Uses 'now' to describe an implemented schema change. |
| `docs/design/fog-presets-and-panorama.md:82` | “Preset resolution happens in `getFogConfig`, which now takes the `session`” | Uses 'now' to state that an engine API has changed. |
| `docs/design/fog-presets-and-panorama.md:102` | “Changes button — editing an atlas's row layout is now a form instead of” | Uses 'now' to report that a UI feature has been migrated. |
| `docs/design/elemental-combat-grammar.md:422` | “and what it currently **wields**.” | Uses 'currently' to assert present implementation behavior or state. |
| `docs/design/floor-ceiling-shader.md:9` | “`dungeon_001`'s `ceilingRow` now renders as a real perspective-correct” | Uses 'now renders' to claim current engine behavior. |
| `docs/design/floor-ceiling-shader.md:13` | “declares `floorRow`) — mechanically done, visually unconfirmed until floor” | Directly asserts that implementation work is 'mechanically done'. |
| `docs/design/floor-ceiling-shader.md:17` | “explicitly deferred this: floors and ceilings are currently flat vertical” | Uses 'currently' to assert present implementation behavior or state. |
| `docs/design/floor-ceiling-shader.md:100` | “now, consumed only once this shader lands. `floorRow` stays unset on both” | Uses 'now' to describe the status of dormant data. |
| `docs/design/floor-ceiling-shader.md:147` | “1. **Done.** Manifest: `floorRow`/`ceilingRow` reading in `getAtlas()`.” | Uses 'Done' to record completion of an implementation step. |
| `docs/design/floor-ceiling-shader.md:148` | “2. **Done.** Light-as-texture: `getLightTexture(mapData)` in” | Uses 'Done' to record completion of an implementation step. |
| `docs/design/floor-ceiling-shader.md:155` | “3. **Done, shared for both planes.** One shader (`FLOOR_CEIL_SHADER_SRC`)” | Uses 'Done' to record completion of an implementation step. |
| `docs/design/floor-ceiling-shader.md:159` | “4. **Done.** Ceiling gated on `ceilingStyle ~= "sky"` and `atlas.ceilingRow`” | Uses 'Done' to record completion of an implementation step. |
| `docs/design/floor-ceiling-shader.md:162` | “5. **Done.** Fallback wiring: `ensureFloorCeilShader()` wraps compilation” | Uses 'Done' to record completion of an implementation step. |
| `docs/design/floor-ceiling-shader.md:166` | “6. **Not done.** Floor art. Both current atlases still lack a `floorRow` —” | Uses a 'Not done' status marker which tracks implementation delivery. |
| `docs/design/floor-ceiling-shader.md:168` | “7. **Not done.** `map.heights` scaffold — still just planned (see” | Uses a 'Not done' status marker which tracks implementation delivery. |
| `docs/design/editor-renderable-bundle.md:95` | “The authoritative editor bridge accepts the map currently in Studio memory, not only the last version saved to disk. That snapshot is input to one transient runtime load and must never be silently written back to authored storage. The runtime loader/compiler remains the implementation; the snapshot merely substitutes the one map record for that invocation.” | Uses 'currently' to assert present implementation behavior or state. |
| `docs/design/raycaster-tileset-lighting.md:21` | “tile type. Town is currently faked as a static-image-plus-menu scene” | Uses 'currently' to assert present implementation behavior or state. |
| `docs/design/raycaster-tileset-lighting.md:84` | “(interact), not freely, mirroring how wall collision already works in” | Uses 'works' to assert existing implementation behavior. |
| `docs/design/raycaster-tileset-lighting.md:141` | “- **Authoring — done**: a third editor layer ("Light", alongside Map and” | Uses 'done' to assert that authoring work has been completed. |
| `docs/design/raycaster-tileset-lighting.md:164` | “`lovec . preview-map <mapId> [x] [y] [dir]` (added in `main.lua`, alongside” | Completion checkbox tracking delivery status. |
| `docs/design/thestra-rtp-authored-layer.md:168` | “- mixed authored semantic registries are not moved wholesale merely because they currently live under `data/`;” | Uses 'currently' to assert present implementation behavior or state. |
| `docs/design/thestra-rtp-authored-layer.md:170` | “- Second Gate branding, game policy and content are not promoted into RTP merely because Studio currently depends on them;” | Uses 'currently' to assert present implementation behavior or state. |
| `docs/design/thestra-rtp-authored-layer.md:172` | “- shared authoring/production sources do not become shipped Project resources by directory accident.” | Uses 'shipped' to record that a change was delivered. |
| `docs/design/content-engine-gaps.md:80` | “&#124; Monster remains are usable ingredients but never outputs &#124; Expressible now (`craftable: false` alone), but the existing Obsidian Shard / Melted Wax / Ectoplasm are still inert `junk` &#124; Migrate the three to real equipment/consumable forms; validate no inert `junk` remains &#124;” | Uses 'now' to assert new engine capabilities. |
| `docs/design/content-engine-gaps.md:90` | “&#124; Every new species has its own portrait and battler &#124; Actor data is authored, but only Titania currently has matching art; the others deliberately use existing battlers as visible placeholders &#124; Author and import the roster's portrait/battler set, then replace each placeholder key &#124;” | Uses 'currently' to assert present implementation behavior or state. |
| `docs/design/content-engine-gaps.md:158` | “&#124; Healing bands use MAT plus target MaxHP &#124; The two authored heals now use the agreed scale (`a.mat * 0.60 + b.maxHp * 0.15`, and 0.90/0.22 for the strong band) &#124;” | Uses 'now' to assert that balance changes were applied. |
| `docs/design/content-engine-gaps.md:176` | “`level` is optional now, so an item-only promotion is authorable -- an entry” | Uses 'now' to assert a schema rule change. |
| `docs/design/content-engine-gaps.md:200` | “14 on both sides now gates it. Tested in `tests/test_growth.lua`.” | Uses 'now' to report an implemented runtime restriction. |
| `docs/design/content-engine-gaps.md:202` | “Summoner MP and MPD, same date (SPEC S1.11). A step now costs exactly the” | Uses 'now' to report a completed mechanical change. |
| `docs/design/content-engine-gaps.md:239` | “creatures, and boss resistance policy -- are answered by data now rather than by” | Uses 'now' to assert an architectural migration. |
| `docs/design/content-engine-gaps.md:252` | “States and control, same date (SPEC S1.10). States now carry a LIST of” | Uses 'now' to claim an implemented schema change. |
| `docs/design/content-engine-gaps.md:273` | “`APPLY_EFFECT` now rolls `HIT * (1 - EVA)` once per target before any effect” | Uses 'now' to describe live engine math. |
| `docs/design/content-engine-gaps.md:279` | “`state.id == "regen"` / `"poison"` with rates from `system.json`. It now sums” | Uses 'now' to describe live engine math. |
| `docs/design/content-engine-gaps.md:286` | “the 5-8% band in `creature-parameters.md` are now expressible. Tested in” | Uses 'now' to claim that capabilities are implemented. |
| `docs/design/future-issues.md:33` | “started as a renderer for 24×24 battler sprites but is now used as the general-purpose” | Uses 'now' to report the current implementation scope of a module. |
| `docs/design/future-issues.md:46` | “`partyGridOrigin` now calls `ui.panelContentOrigin` directly instead of” | Uses 'now' to report a refactored code path. |
| `docs/design/future-issues.md:53` | “context-help-bar convention~~ FIXED (30.07.2026), merged to main (05.08.2026)” | Uses a 'FIXED' date stamp to record completion of a task. |
| `docs/design/future-issues.md:65` | “`ritual_title` keeps its per-mode text for `v.state == 1` but now branches” | Uses 'now' to assert updated conditional logic in a scene. |
| `docs/design/future-issues.md:72` | “`quest_log`'s `quest_help` text is now a formula keyed on `v.questCount`,” | Uses 'now' to report that a UI feature has been migrated. |
| `docs/design/future-issues.md:91` | “Both rebuilt on `buildRowListEditor`. Pages now render as list rows” | Uses 'now render' to claim a delivered editor UI change. |
| `docs/design/future-issues.md:121` | “Sanctioned update of `tools/golden/battle.log` and `scene_*.log` golden references following the actor stat rebalance. G2 (`check.ps1`) and G3 (`check-ui.ps1`) now pass 100% clean.” | Uses 'now pass' to assert that tests currently succeed. |
| `docs/game design/itemCreation.md:220` | “discipline plus per-element reagents; cooking currently has six. The map in” | Uses 'currently' to assert present implementation behavior or state. |
| `docs/game design/itemCreation.md:230` | “- Whether alignment *depth* should strengthen a crafter's pull. It currently does” | Uses 'currently' to assert present implementation behavior or state. |
| `docs/game design/Summoner.md:8` | “MP is now the central resource of the whole game, not just a spell-cost meter. Active creatures continuously drain it just by being on the field. Creature spells cost it. Summoning a creature spends it. Sacrificing a creature refunds some of it back, scaled by the sacrificed creature's level. If MP hits zero mid-battle, the bond between summoner and creatures frays — active creatures start suffering per-round damage or penalties (the old MP-exhaustion-damage concept, redirected from the summoner onto the party). A battle is lost only when every active creature is dead; MP running dry is dangerous pressure, not an instant loss.” | Uses 'now' to describe the live game mechanics. |
| `docs/game design/Permadeath.md:79` | “`reap` but not `ward_save`, so a save is currently silent — the creature just” | Uses 'currently' to assert present implementation behavior or state. |

## Files checked and found clean

I reviewed these in-scope files with the full-file status-candidate scan and
surrounding-prose inspection, and found no sentence that asserts implementation
status rather than describing intent, constraints, or clearly framed rationale:

- `docs/design/actor-roster-expansion.md`
- `docs/design/authored-data-storage.md`
- `docs/design/battle-windows-brief.md`
- `docs/design/battler-inspection.md`
- `docs/design/commercial-identity.md`
- `docs/design/creature-naming.md`
- `docs/design/creature-parameters.md`
- `docs/design/event-driven-content.md`
- `docs/design/image-authored-geometry.md`
- `docs/design/item-atlas-expansion.md`
- `docs/design/portrait-art-direction.md`
- `docs/design/project-editor-runtime-boundaries.md`
- `docs/design/renderer-3d-roadmap.md`
- `docs/design/semantic-tiles-and-baked-lighting.md`
- `docs/design/skill-costs.md`
- `docs/design/summoner-rework.md`
- `docs/design/surface-junctions.md`
- `docs/design/thestra-editor-scene.md`
- `docs/design/tileset-and-events-redesign.md`
- `docs/design/ui-text-style.md`
- `docs/design/unit-actor-battler.md`
- `docs/design/vertical-slice-balance.md`
- `docs/design/visual-language.md`
- `docs/design/widescreen-performance-study.md`
- `docs/game design/idea_wall.md`

I did not inspect, edit, or treat as findings anything under `docs/archive/`,
`docs/SPEC.md`, `docs/ENGINE-STATE.md`, or `AGENTS.md` beyond the requested
instructions.
