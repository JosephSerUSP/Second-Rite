# Thestra RTP authored-layer audit — 2026-08-13

Status: dated evidence for #385. This report records current-main evidence at `12f53777d883510ab2cb133beea7cf15d434b31f`; it is not a live-status authority. Durable decisions extracted from the audit live in `docs/design/thestra-rtp-authored-layer.md`.

## Question and classification vocabulary

The working **RTP** is a Thestra-supplied authored layer between reusable Lua/LÖVE semantic primitives and a concrete Project. It is not a separately installed player dependency. This audit classifies by semantic ownership and actual consumers, not by filename, JSON-ness, or generic-looking art.

Classification terms:

1. **native/runtime primitive** — reusable implementation substrate or semantic capability;
2. **RTP baseline/default candidate** — baseline authored composition/resource an ordinary Project may inherit and override;
3. **RTP optional template candidate** — reusable authored composition deliberately instantiated/forked, not automatically inherited;
4. **Second Gate Project-owned** — concrete game content/policy/presentation;
5. **Studio-only chrome/tool asset** — authoring UI resource, never player-facing merely because Studio uses it;
6. **shared authoring/production library** — source/library material for authoring, not automatically a runtime dependency;
7. **future Package candidate** — intentionally reusable dependency beyond baseline RTP;
8. **unresolved/mixed** — current resource combines roles or lacks enough evidence for safe ownership.

## Current boundary evidence

The current exporter already exposes the physical defect that motivates #382/#385: `engine/` and `presentation/` are runtime directories, `assets/` is Project-owned wholesale, while `data/authored_storage.lua`, `data/authored_storage_manifest.json`, `data/json.lua`, and `data/loader.lua` are special-cased as runtime files inside Project-shaped `data/`. Those four files are implementation support, not authored Project content. Their current location must not be used as precedent for classifying authored JSON.

`tools/editor/server.js` now has distinct install and Project roots. Saved-data previews and Test Play run through the same exporter-compatible staging boundary for external Projects, but asset inventory endpoints (`/api/assets`, `/api/models`, `/api/effects`, `/api/fonts`, tileset textures) deliberately enumerate the opened Project. This is correct for Project resources, but it means Studio currently has no separate RTP resource provider: a generic authoring surface can only see what the Project happens to contain.

The external-Project fixture proves root separation, not a viable blank RPG Project: it creates only `data/system.json` plus one fake sprite. New Project therefore remains a stronger missing test of the default authored layer.

## Authored data classification

| Current material | Classification | Evidence / disposition |
|---|---|---|
| `data/authored_storage.lua`, `data/json.lua`, `data/loader.lua`, `data/authored_storage_manifest.json` | native/runtime primitive | Runtime implementation/support; exporter explicitly special-cases them. Move out of Project `data/` in the #382 migration before treating the Project root as physically clean. |
| `data/engine.json` | **unresolved/mixed** | It is authored and Studio-editable, but it combines reusable semantic registries/help with Second Gate policy. Formula/command vocabulary includes generic interpreter semantics while metadata, disciplines, crafting, creature/recruit/permadeath concepts are game-specific. Do not move the file wholesale into either runtime/RTP or Second Gate. Split/classify by semantic subsystem later. |
| `data/system.json` | Second Gate Project-owned current instance | Values name Second Gate units (`Saban`/`moa`), maps, items, summoner economy, dungeon profiles, PSX rendering choices, battle tuning and specific fonts. A future RTP may provide a baseline system/default document, but the current file is a concrete Project configuration, not that neutral baseline. |
| `data/scenes/title.json` | **unresolved/mixed** | The menu/save/options/quit composition is a strong RTP baseline candidate, but the current scene embeds `assets/title/st_maria_title_psx.png`, `SECOND RITE`, `Thestra no Jijou`, SeraphCircle copyright, common event 42 and map 8. Do not promote the current file wholesale. Extract/author a neutral baseline and let Second Gate override branding/start policy. |
| ordinary menu scenes (`items`, `status`, `options`, `controls`, `save_menu`, portions of `game_over`) | RTP baseline/default candidates, pending per-scene dependency audit | These are reusable RPG-facing compositions built from Scene/window/Event Program substrate. Each must be checked for Second Gate terms, database IDs, formulas and assets before extraction. Current location alone does not make them Project-only. |
| `map`, `battle`, `recruit`, `reserve`, `ritual`, `datalog`, `quest_log`, developer scenes | unresolved/mixed or Second Gate-owned by current content | These surfaces contain stronger game-policy/domain assumptions or developer-only behavior. Battle/map may contain reusable RPG composition, but #325 requires preserving native Battle semantics while separating authored policy; no Battle owner-supervised source changes belong in this audit. Developer scenes are not automatically RTP merely because they are authored Scenes. |
| `data/flows/battle.json` | **unresolved/mixed; predominantly Second Gate Project policy today** | Lifecycle slots are reusable, but current programs encode barriers, `ON_PERMADEATH`, `SYMBIOSIS`, `PARASITE`, `GOLD_DIGGER`, sacrifice/reaping, Second Gate reward/flee/state-cleanup policy. RTP should own baseline lifecycle compositions only after generic behavior is separated from game policy. |
| `data/flows/exploration.json` | Second Gate Project-owned current composition | Explicitly implements manifested-party MPD expedition economy, death wards and creature history. The lifecycle hook itself is reusable runtime vocabulary; this concrete program is game policy. |
| `commonEvents`, Items, Skills, Units, Troops, States, Passives, Quests, Shops, Lore | Second Gate Project-owned by default | #325 owner direction says concrete RPG database resources normally remain Project-owned. Promote only a demonstrated reusable default/template resource, never an entire database because it looks generic. |
| `data/sounds.json` | RTP baseline/default candidate | Current procedural cues are generic RPG/UI operations (`UI_SELECT`, `UI_CANCEL`, `DAMAGE`, `HEAL`, `ITEM_GET`, `BATTLE_START`, etc.) and contain no observed Second Gate asset dependency. They are good candidates for inherited baseline authored sound vocabulary, while Projects remain free to override. |
| `data/animations.json` | unresolved/mixed | `system.*` authored tracks such as damage flash/shake/death/heal are plausible baseline compositions; the same database also references Project effect libraries. Classify entries individually rather than promoting the monolith. |
| `data/iconKeyProfiles.json` | RTP baseline/default candidate | One neutral technical profile used by icon rendering; suitable as baseline authored configuration if consumers confirm it is not game-specific. |
| `data/iconPalettes.json` | unresolved/mixed | Palette mechanism is reusable; the concrete named palette library may be useful baseline authoring material, but it is aesthetic authored content rather than a required primitive. Candidate for RTP baseline or optional library only after ownership/provenance review. |
| `tools/editor/templates/scenes/blank.json` | RTP optional template candidate | Semantically an authored Scene starter, not editor chrome. Current storage under Studio is accidental ownership if Projects are meant to instantiate/fork it. |
| `tools/editor/templates/scenes/crafting.json` | unresolved/mixed; future RTP template or Package candidate after decoupling | It is an authored reusable Scene template, but explicitly clones Second Gate Item Creation, depends on current `engine.json` disciplines and stock window IDs, and embeds project-specific crafting semantics. Do not call it Studio chrome; do not ship it as a baseline default. |

## Player-facing assets and preview dependencies

### UI frame / windowskin resources

`assets/system/` contains `windowskin_*`, cursor/target/waiting UI images, `system_fadeBG.png`, `iconset.png` and other player-facing system art. Presentation consumers treat these as game UI assets, not Studio chrome. The default windowskin/frame family is therefore a strong **RTP baseline/default candidate** if provenance permits reuse. Second Gate may later override it with its own art direction. Missing required frame resources should fail visibly rather than silently borrow Second Gate files.

### Iconset and icon vocabulary

The runtime rule that all icons render through `ui.drawIcon` makes the icon sheet a player-facing semantic resource, not editor chrome. However, `assets/system/README.md` documents vocabulary including evolution, passive categories, status effects and creature races (Fey/Divine/Demon/etc.), which mixes generic RPG concepts with Second Gate ontology. Therefore:

- the **ability to resolve/draw an icon by stable semantic identity** is runtime/RTP contract territory;
- the current `iconset.png` plus current numeric vocabulary is **unresolved/mixed**, not safely wholesale RTP;
- a neutral baseline icon vocabulary/sheet is a legitimate RTP baseline goal;
- Studio toolbar icons under `tools/editor/Assets/**` are separately **Studio-only chrome** and must never become player-facing defaults.

### Fonts

Studio's `/api/fonts` endpoint enumerates `Project/assets/fonts` and presentation loads Project-selected fonts. The current folder contains a heterogeneous font library, including owner-authored and third-party faces. Semantic ownership cannot be inferred from “font used by UI.” Treat the current folder as **shared authoring/production library + Project resources, unresolved per file** until provenance and intended distribution are explicit. An RTP should ship only a deliberately selected, redistributable baseline font set. `system.json` references specific current fonts, which is further evidence that the current selection is Second Gate presentation rather than a neutral Thestra baseline.

### Generic animation/model/battler/sprite previews

The animation HTTP seam now preserves “no sprite” as a legitimate preview state; it specifically removed the earlier hardcoded missing Pixie fallback. This is the correct direction: generic preview must not silently require a Second Gate creature. Where a preview genuinely needs a representative target/model/sprite to communicate scale or animation, that dependency should be an explicit RTP **preview/default placeholder resource** with fail-visible semantics, not an implicit Project lookup and not Studio chrome merely because Studio triggers the preview.

Model/effect/image pickers currently enumerate the opened Project. That is correct for selecting Project resources, but generic preview fixtures must be resolved separately from Project inventory. Existing Second Gate battlers/models/sprites remain Project-owned unless a specific asset is deliberately adopted as a neutral Thestra placeholder with provenance cleared.

### Baseline sounds, animations/effects, tilesets/textures

- procedural `sounds.json` cues are strong RTP baseline candidates;
- generic `system.*` animation compositions are RTP candidates, but effect-file dependencies must be audited entry-by-entry;
- current `assets/effects/**` is **unresolved/mixed**: the editor even documents per-library folders such as `SecondRite/`, so path/library identity is evidence against wholesale RTP ownership;
- current tileset JSON/textures and dungeon/world textures are **Second Gate Project-owned or shared authoring-library material by default**. A neutral starter tileset can be an optional RTP template/resource later, but silent fallback to a dungeon texture would mask a broken Project;
- `tools/editor/server.js` currently creates a new tileset by copying `template_tileset.png`, falling back to `dungeon_001.png`. That fallback is a concrete ownership smell: a generic Studio authoring operation can borrow a Project dungeon texture. The future contract should use an explicit RTP template asset or create an empty/fail-visible resource, never borrow arbitrary Project art.

### Title art, portraits, battlers, cinematics, event/location art, MIDI

Current title art, portraits, battlers, cinematics, event/location art and music are **Second Gate Project-owned** unless a specific file has a separately established shared-library role. They must not become RTP merely because they are currently convenient preview material.

### `assets/authoring/**`

This subtree is a **shared authoring/production library** candidate, not automatically Project runtime content. #382 should preserve it outside `projects/second-gate/` when evidence shows source/reference/production ownership rather than shipped-game ownership. RTP inclusion requires an explicit authored dependency, not directory proximity.

## Per-resource resolution semantics

A single “missing file -> RTP” fallback is unsafe. Resolution should be semantic:

| Resource kind | Authoring resolution | Missing behavior |
|---|---|---|
| baseline UI composition/frame/cursor/default procedural UI sound | Project local override -> explicit Package override/contribution where contract allows -> **pinned RTP baseline** | fail visibly if the declared baseline cannot resolve |
| optional RTP Scene/Event/template | explicit template/library selection from pinned RTP; once instantiated, either retain explicit source provenance or materialize as Project-owned | absence is normal until selected; never auto-instantiate |
| Project identity/content (maps, concrete Units/Items/Skills, branded title art/text, narrative, game-specific economy) | Project local; explicit Package only when deliberately depended upon | fail validation; **no RTP fallback** |
| package-owned resource | Project explicit local fork/override only through declared contract -> pinned Package | fail if dependency/revision missing; do not fall through to similarly named RTP/Project resource by accident |
| Studio chrome | Studio installation only | fail Studio UI visibly; never enter player resource resolution/export |
| preview placeholder | explicit preview resource from pinned RTP when the preview contract needs one | preview fails visibly or renders a deliberate neutral placeholder; never borrow Second Gate content |
| authoring/production source library | explicit authoring tool/library lookup | not part of player resolution unless deliberately imported/materialized |

Stable resource identity and source provenance should be inspectable. Precedence must not arise from filesystem enumeration or mysterious last-wins behavior.

## New Project model comparison

| Model | Portability | Git noise | Upgrades | Offline authoring | Understanding | Package interaction | Deterministic export |
|---|---|---|---|---|---|---|---|
| A. copy everything | Excellent after creation | High; duplicates all defaults/assets | Manual merges; copied defaults stop inheriting fixes | Excellent | Concrete but obscures which files are authored vs stock | Packages remain explicit, but copied RTP can collide conceptually | Easy once copy is complete |
| B. inherit everything | Depends on installed pinned RTP | Low | Clean explicit migration if pin changes | Good only when pinned RTP revision is locally installed | Strong provenance if Studio exposes source; weak if inheritance is invisible | Natural dependency graph | Strong if exporter resolves exact pins; dangerous if “latest installed” is allowed |
| C. hybrid/sparse materialization | Good with pinned RTP; Project remains small | Moderate/low | Baseline can upgrade while local material stays explicit | Good with locally cached/pinned RTP | Best balance if ownership is visible | Natural; same resolver can expose source provenance | Strong with lock/pin + hermetic materialization |
| D. inherited + explicit Make Local | Same as B/C until detached; excellent for detached resources | Low until intentional fork | Shared fixes continue until Make Local; divergence becomes explicit | Good with pinned RTP installed | Excellent when Studio labels source and detachment | Matches #325 package UX | Strong when source revision and local fork are explicit |

**Recommendation:** C + D. New Project should sparsely materialize only resources that define the Project's own identity/minimum contract; inherit legitimate baseline authored resources from a **pinned RTP revision**; and expose **Make Local** for inherited authored resources. Optional templates are instantiated deliberately, not inherited as active game content.

Do not make every database sparse by default. Some resources should be explicit from project creation because their absence is meaningful (project identity, starting map/content, branded title metadata if required). The exact minimal skeleton belongs to implementation follow-up after the resolver exists.

## Minimum version/pin concept

A Project that inherits RTP must declare enough information to select one reproducible authored baseline. Minimum semantics:

- an explicit **RTP revision/version identity** separate from “whatever Studio ships today”;
- a compatibility relationship to the Thestra runtime/Studio family sufficient to reject an incompatible pairing;
- explicit Package pins when Packages are used;
- a resolver that reports the providing source for each inherited resource;
- migration/update as an explicit owner/author action that changes the pin and validates the Project.

Do **not** freeze the final metadata filename/schema in #385. The invariant is behavioral: reopening the same Project under a newer Studio must continue resolving the same RTP revision until the Project is explicitly migrated.

A linked/dev mode may exist for coordinated RTP development, analogous to #325's package direction, but review/export must resolve to explicit revisions.

## Export invariant

Authoring may compose:

```text
installed compatible Thestra runtime
+ pinned RTP revision
+ pinned explicit Packages
+ Project-local authored resources
```

Export must resolve that graph and materialize one complete player game. The exported tree must contain no dependency on Studio, a globally installed RTP, the source repository, or external Package locations. Export metadata may record source revisions for provenance, but those revisions are not runtime dependencies.

The current `runtime-manifest.json` cannot yet express this graph; it only knows installed runtime directories plus wholesale Project assets/data. Do not extend it with ad-hoc fallback paths before the RTP resolver contract is implemented.

## Decisions required before `projects/second-gate/`

The following classifications are migration blockers for wholesale data/assets relocation:

1. extract the four runtime support files from Project-shaped `data/`;
2. do **not** move `data/engine.json` wholesale until its reusable semantic registries and Second Gate policy are decomposed/classified;
3. classify current Scene families enough to avoid moving baseline title/menu/options/save compositions wholesale into Second Gate or, conversely, promoting branded/game-specific scene policy into RTP;
4. classify baseline UI system assets (`windowskin_*`, cursor/target/wait indicators) and current iconset/vocabulary separately from Studio chrome;
5. establish a legitimate source for generic preview placeholders/templates so Studio does not need Second Gate assets;
6. distinguish current Project fonts/effects/animations/tilesets from any deliberately selected RTP baseline library;
7. preserve `assets/authoring/**` and similar source libraries outside the Project when they are production inputs rather than shipped Project resources.

Items/Skills/Units do **not** block the move as a class: current owner direction already favors concrete RPG database resources staying Project-owned unless a specific reusable resource is demonstrated.

## Follow-up slices

Implementation should be split into bounded issues rather than a mass move:

- RTP resolver + Project pin/provenance contract, with fail-loud resource-class semantics and hermetic staging/export materialization;
- semantic decomposition/classification of `engine.json` and baseline Scene/Flow authored defaults without touching owner-supervised Battle source;
- player-facing RTP baseline asset extraction for UI frame/icon/placeholder/sound/animation dependencies, including removal of Studio's Project-dungeon tileset fallback;
- New Project sparse bootstrap + inherited-resource provenance/Make Local UX after the resolver/default inventory exists.

Agent-Signature:
  platform: ChatGPT
  model: GPT-5.6 Sol
  role: research
  task: "#385"
  base: 12f53777d883510ab2cb133beea7cf15d434b31f
