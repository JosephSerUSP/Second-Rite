# Second Rite — Living Spec

The single current-state authority for architecture and design rules.
`BIBLE.md` (root) points here; everything under `docs/archive/` is a
**historical** record of how each overhaul round got us here — read those
for context, never as instructions. If code and this document disagree,
that is a bug in one of them: fix it or flag it, don't silently pick one.

Last consolidated: 2026-07-24 (legacy-purge round; battle/ritual/reserve
scenes now windows-drawn, Summoner economy live).

---

## 0. Why this engine is shaped this way

**Eventing is the backbone.** This engine is a deliberate recreation of building
whole systems out of RPG Maker 2003-style event blocks -- by an author with 20+
years in that engine -- except the blocks are far more powerful and **the engine
itself is made of them**. Battle phases (`data/flows.json`), scene logic
(`data/scenes.json` hooks), recovery sites and quest handling
(`data/commonEvents.json`), map events and traps are all command lists an author
can open and change without touching Lua.

Everything in Sec.1 follows from that goal rather than the reverse:

- A feature belongs in the command language first. If it can be a command list,
  that IS the implementation -- not a prototype of one.
- When Lua is unavoidable, add a **reusable primitive** data can compose (a
  registry command, a ref/scope, a formula token), never a one-off special case.
  `FOR_EACH`'s `neighbor` ref serves any adjacency trait; `x.trait.<CODE>` made
  every trait readable from data at once.
- Don't build a bespoke mechanism where an event already suffices: traps are
  plain events with a step trigger, so there is no "trap system" to maintain.
- Widening the command language lifts every author at once -- including the
  campaign generator, which emits the same commands.

---

## 1. Architecture

### 1.1 Data drives the engine

- **All game content lives in `data/*.json`** — actors, items, skills,
  passives, states, roles, elements, maps, events, commonEvents, quests,
  shops, sounds, themes, terms, animations, scenes, flows, system, engine.
  `data/loader.lua` loads them; Lua never hardcodes content.
- **`data/engine.json` is the registry**: command definitions (id, params,
  contexts, interactive flag), effect types, trait codes, meta keys,
  formula tokens. Adding a command/effect/trait means a registry entry +
  a handler — the validator and the editor pick it up from the registry.
- **Flows are the single source of truth for phase logic.**
  `data/flows.json` maps phases (`battle.victory`, `battle.defeat`,
  `battle.encounter_check`, …) to command lists run in immediate mode by
  `engine/interpreter.lua`. There are no legacy Lua fallback blocks; hosts
  call `flow.run(phase, ctx)` unconditionally and the validator requires
  the phases they depend on to exist and execute.
- **One command language, one interpreter** (`engine/interpreter.lua`).
  Map events, common events, battle phases, and scene hooks all compile
  through it. Interactive commands (TEXT, CHOICE, …) compile to dialogue
  graphs; non-interactive runs compile to immediate-mode blocks
  (RUN_IMMEDIATE bridges mixed lists).
- **Formulas, not scripts** (`engine/formula.lua`): numeric/boolean params
  accept sandboxed expressions over registry-declared tokens
  (`session.encounterRate`, `enemy.maxHp`, …). The sandbox rejects any
  environment access (`os.*` etc.).
- **SCRIPT is a sandboxed escape hatch, rationed.** Default battle phases
  are zero-SCRIPT (the validator enforces it); elsewhere SCRIPT usage is
  counted and reported at every validate run so growth is visible.
  `engine.json scripting.allowRawAccess` defaults to false and the
  validator asserts that.

### 1.2 Presentation

- **Scenes are data** (`data/scenes.json`): `{id, name, kind, draw, hooks,
  scripts, windows}`. **Every scene declares how it draws** — there is no
  host-side fallback (24.07.2026); an unrecognized `draw` is a hard error in
  `scene_host.draw` and a G1 failure:
  - `"draw": "windows"` — rendered entirely from the `windows` array by
    `presentation/window_renderer.lua`. 14 of 15 scenes, battle included
    (the old "legacy-drawn holdout frozen pending Summoner rework" state is
    over). Such a scene may also set `"backdrop": "map"` to show the world
    behind its windows, VN-style.
  - `"draw": "world"` — a world view named by `world` (registry:
    `presentation/world_renderer.lua`), with the scene's windows layered on
    top by the same window renderer. Only `map` (`world: "map"`, the
    polygonal world renderer) uses this. Its world-space surfaces use hardware
    depth testing; the renderer clears only depth before later 2D presentation
    layers so battlers, effects and windows remain screen-space overlays.
    Camera-independent topology (floor/wall/opening cell lists plus wall-event
    and material lookups) is cached per session. Exposed wall faces then cache
    their resolved material, atlas UV orientation, edge overlays, event sprite
    composites and texture canvases per atlas. Map loads, `MUTATE_TILE`,
    `ERASE_EVENT`, and `SET_MAP_PRESENTATION` advance explicit revisions.
    Baked map light remains a static vertex attribute; player-light distance,
    fog visibility/banding and their nonlinear falloff now run in the world
    vertex shader from camera uniforms. Resolved walls, floors and ceilings own
    persistent three-level surface quadtrees; the live camera selects the same
    distance/area subdivision nodes the earlier stream-mesh path built. Selected
    nodes update an index list on one resident mesh per texture, so ordinary
    structural geometry is drawn in texture batches without rebuilding vertex
    buffers. A surface crossing the near plane deliberately falls back to the
    dynamic clipped path. Those clipped leaves are accumulated into one stream
    mesh per texture and surface category for the frame, rather than submitted
    as one GPU draw per leaf. These stream meshes are resident, grow to the next
    power-of-two capacity when necessary, and receive new vertices/draw ranges
    in place instead of being created and destroyed each frame. Root points,
    UVs and baked-light colors also live with the cached surface descriptor.
    Openings, billboards, visibility and near-plane
    clipping remain camera-dependent per-frame work rather than stale cached
    approximations. `lovec . profile-3d <mapId> <frames>` profiles this live
    path against a deterministic generated-map topology and reports structural
    batches, dynamic sources, dynamic mesh draws, timing percentiles and memory.
    Image-authored source geometry is cached by source revision, compiler
    version and geometry-quality key. Changing quality retains earlier valid
    variants, so an A -> B -> A quality sequence recompiles only B; a 128-entry
    least-recently-used bound prevents continuous custom quality values from
    growing the compiled cache indefinitely. Per-session prepared world
    structures still invalidate when their quality key changes.
    The
    old `town` scene — legacy-drawn, unreachable,
    superseded by the town *map* — was deleted in the purge.
- **The Summoner rework is live**: per-round MP drain in battle
  (`engine/battle.lua`), per-step field drain (`engine/exploration.lua`),
  sacrifice with level-scaled EXP/rewards (`SACRIFICE_EXP_RATE` trait),
  species unlock flags, and the shared `ritual` scene
  (summon/promote/sacrifice) plus `reserve` scene.
- **`presentation/renderer.lua` is live shared presentation, not a legacy
  renderer** — despite the name it holds window-content drawers that
  `window_renderer` dispatches to (enemy row, battle log, victory panel),
  cross-cutting FX services (damage popups, text reveal, battle anims), and
  coordinate helpers. Treat it as a shared library; do not "migrate off" it.
- **The engine never requires presentation.** Where a command or SCRIPT api
  call needs presentation (is the battle log still revealing? re-point at a
  swapped session?), the host injects hooks via
  `interpreter.bindPresentation` (bound in `main.lua`); unbound, every hook
  degrades to a no-op/false so headless runs work.
- **Animations are data** (`data/animations.json`): typed track lists
  (tint, blend, transform, shake, particles, force_field, gradient_map,
  screen_flash). `system.*` reserved entries (damage_flash, shake, death,
  …) must exist and hard-validate; assignable entries soft-validate so new
  track types can ship data-first. An entry may author an `anchor` saying
  where on its target it attaches — see §2.4.
- **Battler placement is one module** (`presentation/battler_geometry.lua`):
  battler → rect, rect + anchor spec → point. Popups, animations, reticles,
  slot indicators and the enemy info block all read it. See §2.4.
- **Targeting is one resolver** (`engine/targeting.lua`): declarative
  target specs on skills/items, expanded by `targeting.expand` for both AI
  and player paths. `expand` errors on unknown specs; the validator gates
  every spec in data.

### 1.3 Campaign roots (18.07.2026, "no-move" design)

- **`data/` IS the default campaign.** `campaigns/<name>/` directories are
  drop-in alternates carrying the same file set. Nothing else moves.
- Active root resolution (data/loader.lua `resolveRoot`): CLI arg
  `campaign=<name>` > `campaign.json` pointer at the repo root
  (`{"active": "<name>"}`) > `data/`. The dev server's `/data`/`/save`
  endpoints and `engine/config.lua` follow the same root.
- G1 validates whatever root is active. Golden logs (G2/G3) are recorded
  against the default campaign only — run gates with `data/` active.
- **Non-default `campaigns/<name>/` roots are disposable test artifacts**
  of the generation pipeline (21.07.2026 decision). They are not held to
  sync parity with `data/` — a scene/menu feature landing in the default
  campaign does not obligate porting it to `thestra_no_jijou_2/3/4` etc.
  Regenerate them from the pipeline when needed instead of hand-syncing.

### 1.4 Scene layout convention: context-help bar + bottom dock

Every `"draw": "windows"` menu scene shares one skeleton instead of each
scene inventing its own chrome:

- **Top: a "CONTEXT HELP" bar** (style `frame`, full width, docked at
  `y=0`). It never holds a fixed hint string — its `content` text is a
  formula keyed on scene state (`v.state`, `v.combatState`, …) so the same
  window reads as nav hints in one state and as contextual explanation
  (an item/equip description, victory spoils, …) in another. This replaces
  the old pattern of a separate description/info panel next to a static
  "UP/DOWN: select ENTER: use" bar — one window, state-dependent text, no
  redundant real estate. (Applied to the `items` scene's `help` window and
  `battle`'s `battle_help` window during `victory`.)
- **Bottom: a persistent dock.** "Persistent" is now literal (29.07.2026):
  the dock is **not a scene's window**. It is one surface owned by
  `presentation/dock.lua`, whose state — window tables, animation clocks,
  visibility history — lives in that module and therefore survives
  `scene_host` push/pop/goto untouched. Scenes only declare *which variant*
  they want, via `config.dock` in `scenes.json`:

  ```json
  "dock": { "variant": "party_status", "cursor": "v.mode == 4 and v.partyIdx or 0" }
  ```

  The variants themselves live in `data/engine.json`'s `dock` registry, so
  adding one is a data edit; `cursor`/`visible` on the scene's dock config
  apply to the variant's declared `primary` window, and `windows: { <id>: {…} }`
  overrides any field of any window in it. An optional `offsetY` formula
  shifts the whole dock in pixels.
  Content still binds to the **current** scene, so `v.dialogueText` and
  friends resolve exactly as they did when the scene owned these windows.

  A variant declares an ordered, arbitrary-length `shells` array plus the
  content windows that occupy those shells. Transitions use one shared
  language rather than scene-specific effects: same variant on both sides
  animates nothing; on a variant change all content clears, shared shells
  morph to their destination rectangles, removed shells collapse horizontally
  to zero width, added shells grow horizontally from zero width, and only then
  does destination content appear. Leaving for a scene with no dock collapses
  every shell. This supports today's two-pane map/battle/dialogue layouts and
  future three-or-more-pane layouts without another compositor path.

  This replaced five copy-pasted `party` windows, a runtime-opened one on
  `map`, and a third copy drawn by `frame_renderer` for battle — plus the
  three band-aids that existed because the dock used to be destroyed and
  rebuilt on every scene change (`config.windowFootprint` /
  `_seamlessWindowFootprint`, the map-specific `_skipOpenAnim` block in
  `love.update`, and `frame_renderer`'s 0.15s `dialogueEnterTime` overlap).
  All are deleted; do not reintroduce a per-scene copy of the dock.

  **Not yet folded in:** `reserve_party` and `status_dock` are still
  scene-owned windows over the same footprint, and until they move those two
  scenes cut rather than dock-morph. Neither is a simple data edit:
  `reserve_party` is read by name from Lua (`drawSwapIndicator` in
  `window_renderer.lua`), and `status_dock` binds through
  `sel('status_party')` — a *scene* window — while a dock variant's list cache
  only covers the dock's own windows. `shop_party` and `ritual_party` had no
  such coupling and are gone; both are now `party_status` with a scene-level
  `visible`/`cursor` override. (Note `ritual_party`'s `gridColumns: 2` was
  inert — that key is only read from `windowLayout`, and 2 is the default.)

  **What actually covers the dock:** not the G3 UI *trace* — those lines are
  window commands emitted by scene hooks, so a declarative window of any kind
  is invisible to them (this is why a fully declarative scene's trace is one
  line). The dock is covered by G3's per-step **draw smoke test**, which calls
  `scene_host.draw` and fails the gate if drawing throws, and by
  `tests/test_dock.lua`, which pins the parts that have no visual signature —
  above all that the dock's window table is the *same table* after a
  same-variant scene change, which is what makes its animation continuous.

  The dock's shells carry scene-specific roles:
  1. **Persistent party status** — the current/selected member's compact
     status, always visible regardless of what's happening above it.
     The creature card in that pane is **one renderer**
     (`renderer.drawBattlerCard`): sprite, elements, name, level, HP bar and
     states, drawn identically by battle's target pane and the status menu, so
     the readout a player learns while fighting is the one they get while
     planning. What it *shows* varies by caller — status opts into an EXP
     gauge, battle does not — because the rows a creature needs differ by
     where you are reading it. That is a flag on one card, never a second
     lookalike card.

     **A creature's name always carries its element icons** — "🟢Saban", never
     a bare "Saban" — and that is one function,
     `actor_status.drawCreatureName`, not a convention each surface remembers
     to follow. The sequence it owns (resolve effective elements, draw icons,
     measure, offset the name, clip the name to what is left) used to be
     hand-rolled per site, and the sites that forgot it were the tell: the
     party cell, target card and victory report drew icons; the level-up
     report and the status headline did not, so the same creature read as two
     different things depending on the menu. A name rendered from an
     interpolated `"{name}"` string can never satisfy the rule, which is why
     the status headline is a `creatureHeader` window rather than a `text`
     one. Sentences in the battle log are the deliberate exception: prose
     names a creature mid-clause, where an icon would break the line.
  2. **Context-aware content laid out like the dialogue box** — left pane
     is an info panel (portrait/name/stat summary), right pane is the
     larger, interactive pane (lists, explanations, previews — anything
     the player can act on lives here, not in the narrow left pane).
  Both variants share the dialogue scene's exact footprint and column
  split: left column width starts from `battle_layout.partyGridColWidth`
  (68px = 8.5 tiles — the same fixed cell width `actor_status.draw` uses
  everywhere else) but widens as needed. It is **15 tiles** as of
  01.08.2026: battle's target pane was already 15 while status's was 9.5,
  which is exactly the drift the rule below forbids, and the creature card
  they now share is unreadable narrower (it rendered "Saban" as "Sab").
  The right column takes the remaining width. **The
  left column's width is the authority**: if a scene's info panel needs
  more room to read cleanly, widen the shared dialogue footprint to match
  rather than shrinking the info panel's content — don't let two scenes
  drift to two different "narrow left column" widths, and don't let the
  same width live in two places either (`data/engine.json`'s windowLayout
  entry AND a scene's own `rect` both set x/y/w/h — the scene's `rect`
  always wins, so when the shared width changes, both need editing or the
  engine.json one silently does nothing).
- A scene can layer scene-specific chrome above this dock (e.g. status's
  equipment-slot header + portrait), but the dock itself — and the
  context-help bar — should look and behave the same everywhere it's used.
- Shop and Items use the `item_inspect` dock variant. Their top help bar shows
  the selected item's authored description (flavor); the dock's lower-left
  shell derives gameplay text from the item's live `effects`, `traits`, and
  Savor traits using registry labels. The untitled upper-right showcase renders
  the selected item's 3D model through `presentation/item_model_view.lua`, with
  a clear empty state. It formerly resolved an authored `keyArt` image; models
  superseded that, #227 removed the art and the authored values, and the field
  itself is gone — a data key nothing renders is a trap for the next author who
  fills it in and waits for something to appear.

### 1.4.1 Datalog

Lore is authored in `data/lore.json`, keyed by stable string id. Each entry has
a title, category, body, optional numeric order, and optional `unlocked: true`
for knowledge available from a new game. Runtime discoveries use the registered
`UNLOCK_LORE` event command; the session stores only unlocked ids and save/load
round-trips them. The `datalog` scene is an ordinary windows-drawn scene whose
`LIST_UNLOCKED_LORE` hook command materializes display rows. This keeps lore
content, discovery triggers, and menu behavior in the same data/event surfaces
as the rest of the engine.

The field main menu uses the battle command console's shared geometry and may
author no more than five top-level commands. Its current four commands are
Items, Party, Data, and Options. Party opens View, Reserve, Quests, and Notes;
Notes is the player-facing name for the `datalog` scene. Data contains Save and
Load.

### 1.5 Extensibility (round-wide rule since o7, keep it)

Every schema tolerates unknown future fields: readers ignore keys they
don't understand, validators warn rather than reject on unrecognized
*optional* fields, and new entry types arrive behind `kind`/version
discriminators.

**Scope narrowed (24.07.2026, owner decision):** this rule protects
*future* fields and shipped-player data only. Repo-owned content
(`data/*.json`, campaign roots, save files — saves are test artifacts for
now and may break freely) gets migrated in place when a schema changes;
dual-read shims for old shapes of our own data are carrying cost, not
compatibility, and should be deleted after a one-time migration.

Removed under this rule (24.07.2026):

- the deprecated command aliases (GIVE_ITEM/TAKE_ITEM/GIVE_ITEM_ID/DRAIN_MP/
  RESTORE_MP → CHANGE_ITEM/CHANGE_MP);
- the dual `type`/`cmd` command-key format — **every command stores its id
  under `cmd`**, and the editor no longer mirrors an interactive-id table to
  decide which key to write;
- the dual `script`/`commands` name for owned command lists — **`commands` is
  the only name**, on events, event pages, CHOICE options and recruitEvents
  (`scriptId` remains the distinct common-event template link described in
  §4.1; it is not an owned list);
- the redundant `tiles{}` tileset mirror (`features[]` is the sole source of
  feature ids, per §1.8) and its merge in `viewport_3d.lua`;
- the `ui.elementIcons` config + hardcoded icon table in `actor_status.lua`
  (nothing set the config and the table had drifted out of sync with
  `elements.json`; one `UNKNOWN_ELEMENT_ICON` constant remains);
- main.lua's 1,351-line inline copy of the validator — `engine/validator.lua`
  was a near-identical extraction that **nothing ever required**, so the CLI
  branch now calls `validator.run(loader)` and main.lua shrank 2,737 → 1,375
  lines;
- scene_host's legacy-Lua-draw fallback, together with the `town` scene that
  was its last user: every scene now names its draw mode (§1.2), main.lua's
  `love.draw` fallback branch is gone, and G1 gates the contract. Also gone
  with town: `renderer.drawTown`, its background image load,
  `townSelectedIdx`, ~40 lines of main.lua keypress handling,
  `system.json`'s `town.options`, the editor's `townOptions` widget, and
  `tools/golden/scene_town.log`. Save/load defaults moved `"town"` → `"map"`;
- `interpreter.lua`'s `pcall(require, "presentation.renderer")`
  engine→presentation layering violation, replaced by the injected
  `interpreter.bindPresentation` seam (§1.2). `viewport_3d.draw` also
  self-initializes now instead of trapping callers who never ran the boot
  sequence.

**Correction (26.07.2026): the purge missed three, and they are now gone.**
Three `if flow.has(phase) then ... else <legacy Lua> end` fallbacks survived
the first pass, because they predate the rule and read as deliberate ("SPEC
S4 fallback"). They were not: hosts call flow phases unconditionally and the
validator requires them, so every `else` arm was unreachable — a second
implementation kept alive by nothing but its own comment.

The round-end one proved the cost. It had already drifted: it still branched
on `state.id == "regen"` with rates from `system.json` after the live path
became `HRG`-driven (§1.13), so the two paths disagreed about what
regeneration *is*. The other two were a full duplicate flee roll (gold
penalty included) and a full duplicate weighted encounter spawner.

All three are deleted. `battle.round_end`, `battle.flee_attempt` and
`battle.battle_start` joined the validator's required-phase list in exchange:
with nothing to fall back to, a missing phase would silently skip every
end-of-round tick, make fleeing impossible, or spawn an encounter with no
enemies. That list does not merely check existence — it *runs* each phase
against a fresh session, so the three gained real smoke coverage in the
trade. `combat.regenRate` / `combat.poisonRate` went too: nothing else read
them, and the editor was still offering both as System settings that changed
nothing. The flee and encounter settings stayed, because `flows.json`
genuinely consumes those.

Map encounter entries may author `levelMin` and `levelMax` alongside `id` and
`weight`. `SPAWN_ENEMIES` resolves a level independently for every spawned
enemy and constructs the battler at that level. Omitting both fields preserves
the actor's authored default level and consumes no additional random draw.
`levelMax` requires `levelMin`; G1 rejects non-integers, inverted ranges, and
non-positive weights. The map editor authors and displays the range.

`flow.has` now has exactly one caller, the validator's required-phase check
— which is the job it should have had all along: proving a phase exists, not
choosing whether to use it.

`presentation/renderer.lua` was investigated and deliberately NOT split: it
is live shared presentation (§1.2), so a file split would be churn with
regression risk and no functional gain.

### 1.6 Map cell overrides (unified, 23.07.2026)

`mapData.overrides` is a flat array of `{x, y, visual, passable, mutateTo,
hidden}` entries (0-indexed, author-facing) — the single per-cell escape
hatch, replacing the old dead `tiles{}` grid and the lamp's free-text
`material` field (see `docs/design/tileset-and-events-redesign.md` §8.1):

- `visual` — a feature/material id resolved against the tileset's merged
  `tiles` table (same id space as `data/tilesets.json`'s `features[].id`);
  wins over generated light-object materials.
- `passable` — overrides the layout char's solidity (illusory wall = `true`
  despite `#`; one-way/blocked floor = `false` despite `.`).
- `mutateTo` — a pending structural-mutation target (`"#"`/`"."`/`"o"`),
  applied by the `MUTATE_TILE` command (`engine/exploration.lua: mutateTile`)
  and cleared once consumed.
- `hidden` (on the *event*, not the override) — an event at an overridden
  cell renders nothing until that cell's `mutateTo` has been consumed.

`engine/exploration.lua: buildOverrideIndex` indexes this once per map load
(`session.overrideIndex`, keyed 1-indexed `"x,y"` to match `session.mapGrid`).

### 1.7 Structural `opening` cell (23.07.2026)

`"o"` is a third layout char alongside `"#"`/`"."` — a doorway/gate/arch the
player walks through (design doc §2/§6), distinct from a decorative
`wall_event` door which sits on an actual `"#"` and is never passable. `"o"`
is passable by the existing `~= "#"` movement check (no change needed there)
but, unlike `"."`, carries structural renderer geometry. The polygonal world
path resolves its axis from the surrounding wall pair and draws a passable
three-piece frame (two jambs and a lintel) sampled from a deterministic weighted
pick in the tileset's door pool, or draws that variant's model when authored.
Authored via the map editor's Layout brush (`tools/editor/js/map-editor.js:
setPaintTool('opening', ...)`) or as a `MUTATE_TILE ... to="o"` runtime
mutation (hidden-passage reveal, per the override's `mutateTo`).

Procedural maps may opt into `generateOpenings:true`. During corridor carving,
the generator records cells actually cut out of walls and turns only those on a
room's outside threshold into `"o"`; room floors cannot become openings, and
entrance/exit stair walls are excluded. The result is deterministic for the map
seed, participates in generated corridor zones and ordinary fixture predicates,
and persists as part of the cached map grid. Map Properties exposes the option
only for procedural maps.

Room-count and room-size authoring lives in reusable
`system.dungeon.generationProfiles`, with one registered default selected by
`system.dungeon.generationProfile`. A procedural map may select another profile
with `generationProfile`; Map Properties lists the registered choices. The
repository's former per-map `genMinRooms`/`genMaxRooms` and system `gen*` fields
were migrated and have no compatibility read path. G1 validates profile ranges,
the default reference, every map reference, and rejects the removed fields.

### 1.8 Tileset Studio: variant pools, not cell painting (23.07.2026)

`tools/editor/js/tileset-editor.js` (design doc §7) now treats the atlas
canvas as a **coordinate picker**, not the authoring surface — a "Wall"
click used to always overwrite `base.walls[0]`, which is why `weight` fields
existed with nothing to weigh against (§0). The primary surface is now a
**Variant Pools** list per structural role (Walls/Floors/Ceilings/Wall
Fixtures/Floor Fixtures/Doors): select a pool entry (or add a new one),
*then* click the atlas to assign that entry's coordinates. Deleting/adding
goes through the real backing array (`tilesetData.base.walls`, `.floors`,
`.ceilings`, `.features` filtered by role, `.doors`), so pools can actually
hold N weighted variants now.

The redundant `tiles{}` mirror the old editor dual-wrote alongside
`features[]` (dead per §0 — nothing ever read it by map cell) is dropped on
save; `features[]` is the single source of truth. `presentation/
viewport_3d.lua`'s atlas loader no longer merges a legacy `tiles{}` at all —
the mirror was purged from both the loader and `tilesets.json` on 24.07.2026
(see §1.5).

**Base walls are a fixed 128×64 block, authored with one click.** The old
per-slot model (three independently-clickable targets — middle/leftEdge/
rightEdge — chosen via a slot radio) let an author scatter them anywhere in
the atlas, including on top of unrelated fixture cells; the engine only ever
renders leftEdge/rightEdge as 32px-wide *halves of a single cell* anyway
(`viewport_3d.lua:838-851`, offX 0 vs 32). The editor now matches that: click
a wall variant's **middle** cell in the atlas and the cell immediately to
its right is auto-assigned as both edges (offX 0/32), matching a spritesheet
laid out as `[wall middle][wall edges]` side by side — e.g. `town_test.png`
(256×128, 4×2 cells): row 0 = `[ceiling, floor, -, -]`, row 1 = `[wall
middle, wall edges, fixture 1, fixture 2]`, authored by clicking (1,0) for
the wall, then (1,2)/(1,3) for the two wall fixtures. The underlying schema
(`middle`/`leftEdge`/`rightEdge` triples) is unchanged, so existing data with
edges elsewhere in the atlas still renders — only new authoring assumes the
fixed layout.

The renderer now resolves base wall, floor, ceiling, door and opening pools by
authored positive weight. Picks are hashed from the map cell and a role-specific
salt: revisiting or reloading a cell cannot reshuffle it, rendering consumes no
gameplay RNG, and all faces of one wall cell share one variant. Omitted weights
default to one. G1 rejects non-positive weights and missing wall-middle or atlas
coordinates. Tileset wall/floor features resolve `injectProbability`
deterministically per cell and may author a recursive `where` predicate; placement
consumes no gameplay RNG. One feature occupies a cell. Placements persist in
`session.generatedFeatures`, separately from `generatedLightObjects`, so a
non-emitting fixture never acquires an implicit torch light. Wall features bake
their atlas cell into exposed wall composites; floor features draw a
depth-tested overlay above the base floor. Both roles may instead name a model:
wall models attach to visible faces, while floor models use cell centre.

`where` is a single-operator object composed from `all`, `any`, `not`,
`adjacent`, `distance`, and `zone`. Adjacency targets a tile class (`wall`,
`floor`, `opening`), a zone tag, or a feature placed earlier in tileset order;
it is cardinal unless `diagonal:true`. Distance is Manhattan distance and
explicitly targets either a zone or an earlier feature, with optional inclusive
`min`/`max`. G1 rejects malformed predicates, ranges and feature references.
The removed `requiresAdjacentFloor` field was migrated to
`where:{"adjacent":"floor"}`; there is no dual-read compatibility path.

Authored maps may declare overlapping `zones[]` as zero-indexed rectangles or
explicit cell lists, with one `id` or several `tags`. Generated dungeons persist
per-cell structural tags for `room`, `corridor`, `anchor`, `entrance`, and
`exit`. Both sources build one runtime index, so cells may carry several tags.
Tileset Studio edits predicates and Map Properties edits authored zone records.
Tilesets may define reusable `fixturePrefabs[]`. Each prefab has a unique `id`,
a validated `where` predicate, and an optional probability `{min,max,default}`
range. A feature authors either `prefab` or a custom `where`, never both; its
probability must remain inside the selected prefab's range. Tileset Studio
exposes the library and a prefab selector, and can detach a selection by copying
its predicate into the custom-rule editor. Runtime placement still evaluates
the same predicate implementation, so prefabs introduce no parallel rule path.

A map may author a sparse `tilesetOverride` instead of duplicating its base
tileset. The delta mirrors the pool structure (`base.walls/floors/ceilings/skies`,
`doors`, `features`, `fixturePrefabs`): entries merge by `id`, new ids append,
and an existing entry may be removed with `{id,remove:true}`. Nested objects
merge while coordinate/color arrays replace. `engine/tileset_resolver.lua` is
the single immutable resolver used by both fixture injection and the renderer;
loader-owned data is never modified, and overridden maps receive distinct atlas
cache identities. G1 rejects unknown delta fields, duplicate ids, malformed
removals, invalid resolved feature roles, predicates, prefab references and
probabilities. Map Properties exposes the sparse delta as JSON.

Door and fixture variants may also author an optional `model` project path
naming a static `.obj` kit piece. Tileset Studio exposes the field on those
pools and G1 requires the file to exist; a model-backed variant does not also
need atlas coordinates.
`presentation/obj_model.lua` is the single runtime loader: it supports OBJ
positions/UVs/normals, polygon triangulation, negative indices, generated face
normals, and MTL `Kd`/`map_Kd`, with nearest-filtered textures and one cached
static GPU mesh per material group. Unsupported directives, invalid indices,
degenerate faces, and missing MTL/texture files fail loudly. World kit pieces
use a cell-centred convention: OBJ `(0,0,0)` is the centre of the owning map
cell at floor level, one model unit is one cell, X/Y are the floor plane and Z
is up. Opening-axis changes rotate about that centre. Model-backed structural
openings render cached material groups through the same depth, fog, player
light and vertex-light path as procedural structure; their OBJ normals add
directional shading. Model-backed wall-event doors attach to their exposed
face, wall fixtures use that same face rule, and floor fixtures use cell centre.
Atlas-only variants continue unchanged. Base-wall/floor/ceiling model roles
remain closed; G1 rejects them rather than silently accepting a model the
renderer would ignore.

A floor feature variant may author `blocksMovement: true`, making it SOLID --
the player cannot walk through it. G1 rejects the flag on a wall feature, which
already stands on a `"#"`.

Solidity is resolved at PLACEMENT time, not at movement time, because the
predicates that place fixtures know nothing about topology: a solid fixture in a
one-wide corridor severs the map and one in an alcove mouth strands what is
behind it. Injection therefore enforces one invariant --

> blocking a cell may remove ONLY THAT CELL from the reachable set

-- which covers both failures at once, and additionally refuses the spawn, the
entrance/exit staircases and any cell carrying an event, since blocking those
severs nothing but makes something unusable. Candidates are validated
incrementally in authored order, so fixtures that are individually safe but
jointly a cut are caught too. A refused fixture is simply not placed; losing a
decoration is far cheaper than an unwinnable floor. Placement records carry
`blocks`, so solidity survives save/load without re-resolving the tileset, and a
map already in a save keeps the solidity it was generated with. An authored
per-cell `passable` override outranks a fixture that happened to land there.

Wall and floor feature variants may also author an Effekseer `.efkefc` asset,
plus optional `effectHeight` and positive `effectMagnification`. G1 verifies
the project path and parameter types, and Tileset Studio exposes the same
fields. The prepared 3D structure owns the resulting native handles: floor
effects start at cell centre, wall effects attach just outside their first
exposed face, and invalidation/map replacement stops them. They advance through
the shared deterministic Effekseer clock. World effects bridge the game's X/Y
floor and Z-up coordinates to Effekseer's X/Z floor and Y-up convention, then
draw directly through the polygonal camera while preserving its depth
attachment. Both `env_mist` and `env_rain` are deterministically sampled down a
corridor at frame 400 and visibly change the live viewport while that depth
buffer is populated.

Effect time is advanced in **one-frame sub-steps**. A single large `deltaFrame`
does not fast-forward Effekseer's simulation, it skips it — emitters fire per
simulated frame — and it also leaves the manager unable to emit for the next
effect played. Anything that advances effect time in bulk depends on this: the
screenshot harness's settle, the editor filmstrip, a load hitch.

A map may author one `ambientEffect` (`{effect, height, magnification}`) for
**weather**, which is a different role from a cell fixture rather than a
shorthand for one. It spawns a single handle per map and is moved to the camera
cell every frame at its authored height, so it always fills the view. Two
reasons it cannot be a per-cell feature: anchored to a cell it stays behind the
player, and one endless placement reaches ~1,900 live instances against a 2,000
manager budget, so a second would starve every other effect into spawning a root
that emits nothing. Cell fixtures (torches, braziers) keep one handle per
placement, which is correct and small. G1 validates the reference, the field set,
and a positive magnification; Map Properties authors it. Particles already in
flight are world-space and stay where they were emitted, so a teleport leaves a
brief gap while the new location emits — ordinary movement never notices.

Two rules follow for anything that measures a world effect, both learned by
getting them wrong (§6.5.1g of the roadmap): observe down a view with **receding
depth**, because a camera facing a near wall has every particle rejected by the
depth buffer and reports zero pixels while the effect emits healthily; and
sample while the effect is **alive**, because a finite effect past its end also
reports zero. Together those two produced a recorded claim that `env_rain`
"produces no pixels through the perspective pass" when it renders correctly.

### 1.9 Item vocabulary (26.07.2026)

The item atlas planned in `docs/design/item-atlas-expansion.md` needs an item
to answer several independent questions at once — when it may be used, what it
restores, whether Item Creation may consume or produce it — and each of those
was previously either unauthorable or silently ignored. The primitives below
exist so that atlas can be authored without content-specific Lua. They are
reusable and registry-backed; none of them names an item.

**Use occasion.** `item.scope` is the independent occasion axis:
`always` (the unauthored default), `battle`, `field`, `none`.
`engine/usability.lua` has always branched on it; what is new is that
`engine.json -> itemScopes` enumerates the four words, **G1 fails an unknown
scope**, and the editor's Use Occasion select is built from that registry.
This is a fail-loud fix, not a feature: an unrecognized scope fell through
usability's if-chain to "usable everywhere", so a typo'd `feild` read as a
restriction and behaved as none.

**Percentage recovery.** The `hp` and `mp_heal` effects take `percent`
alongside `value` — a share of the recipient's Max HP and of the summoner's
Max MP respectively. Either part may stand alone, so one effect type covers
flat, percentage and hybrid restoration. The percentage form is what keeps a
food meaningful across creatures whose Max HP differ by an order of magnitude,
and a draught meaningful as Max MP climbs.

**Permanent Max MP.** `max_mp_plus` raises `session.maxMp` (already saved),
clamped to `system.summoner.maxMpCap`, and restores what it added. Usability
refuses the item at the cap rather than consuming it for nothing, the same
guard shape full-HP and known-skill items use.

**`ITEM_EFFECT_RATE`.** RPG Maker's Pharmacology: multiplies the magnitude of
item effects. It is read from the **user**, not the recipient. Battle items use
the acting creature; field items use the best living party carrier because the
field menu has no separate user selection. Skill effects are deliberately
untouched. Permanent gains (`param_plus`, `maxHp`) are untouched too: an item
that grants +1 ATK forever grants exactly that.

**`common_event` items.** An item effect that starts an authored common event
— the Forbidden Lamp opening a scripted encounter. It cannot run the event
itself: `CALL_COMMON_EVENT` is an *interactive* command that compiles to a
dialogue node, and immediate mode refuses it, so effects have no way to hand
control to the graph walker. The effect raises a `run_common_event` request;
`scene_host` defers it alongside scene transitions (so the graph starts on a
settled stack rather than mid-hook) and asks the host through
`interpreter.bindPresentation`'s `runCommonEvent`. Unbound — the validator, the
golden harness, any headless run — the request is simply unclaimed and nothing
errors. G1 fails an effect naming a common event that does not exist, because
such an item is the only gate on the content it calls.

**Ingredient exclusion.** `meta.craftIngredient: false` keeps an item out of
Item Creation *ingredient selection*, independent of `meta.craftable: false`,
which only excludes *outputs*. Both exclusions are needed because the two
policies differ: monster remains are ingredients that are never produced, and
a promotion key is neither. `craft.isIngredient` is the one shared reading;
the crafting scene applies it through the list `filter` below, and G1 reports
the count of items outside Item Creation entirely.

**List `filter`.** `SET_LIST` (and the equivalent declarative list block)
takes a `filter` row formula that **drops** rows, where `priority` only sorts
them first. It runs before the sort, so a hidden row cannot be selected,
counted, or landed on by a cursor. Item Creation must not merely bury a
promotion key at the bottom of the ingredient list, and every future
"selectable subset of a list source" is the same problem.

### 1.10 Creature growth is seeded and accumulated (26.07.2026)

Growth is **additive, permanent, seeded per instance, and intentionally
uneven** — never recalculated from species and current level.

Each form authors budgets for three bands (levels 2–10, 11–20, 21–30) in
`actorData.growthBands`. An instance's `growthSeed` divides each budget into
uneven per-level packets (`engine/growth.lua`), which accumulate into
`battler.growth`. A stat is then simply `base + accumulated`.

What it replaced: `base * (1 + rate * multiplier * (level-1)^exponent)` — one
smooth curve every creature of a species shared exactly. Two Pixies at level 12
were the same Pixie, and **there was nothing for a promotion to preserve**,
because changing the species silently re-derived every level the creature had
ever gained. The whole promotion / Egg / Homunculus design depends on a past
that is owned rather than re-computed.

Rules the model guarantees, each with a test:

- **Deterministic.** A creature generated directly at level 20 replays the same
  history it would have lived, and a reload can never reroll a level-up.
- **No global RNG.** `growth.lua` uses its own LCG. Touching `math.random`
  would make a creature's stats depend on *when* they were computed and shift
  every battle roll after it.
- **Within budget.** Per-instance variation is about ±5%: lucky in a stat,
  never materially richer overall.
- **HP rises every level**, and not smoothly — a band has memorable spurts,
  because a level-up showing no change reads as a bug.
- **Growth stops past the last authored band** rather than extrapolating.

`mpd`, `mxa` and `mxp` do **not** grow: they are form-defined. MPD previously
grew at 0.05/level, which quietly made a creature more expensive to keep
manifested the longer you raised it — the reverse of the economy in §1.11,
where an early form stays cheap and promotion is what costs you.

**A caution about G2 here.** Every other golden fixture builds its battlers at
level 1 (`fixture.level or 1`), so this rewrite — the largest single change to
how stats are computed — moved zero golden lines. That proved *coverage*, not
correctness. The `growth` fixture fights at level 14 on both sides so the model
is gated from now on.

**Promotion never recalculates statistics.** It carries the `growthSeed` and
the accumulated `growth` record across to the new form, adds the evolution's
fixed authored `bonus`, and lets only *future* levels draw on the destination's
band budgets — automatically, since `packetFor` reads the creature's current
`actorData`. The levels a creature earned as a Pixie stay Pixie levels.

Two details that look small and are not:

- The bonus is **fixed**, so promoting early is rewarded and delaying does not
  scale it up. A player who waits has banked more of the cheaper form's growth
  instead — that is the trade, not a larger prize for patience.
- HP is clamped **after** the growth record is restored. Clamping first would
  quietly cap a promoted creature at its *unpromoted* maximum.

An evolution's `level` is **optional**. An item-gated promotion normally has no
additional level requirement: acquiring and choosing to spend the key is the
gate, and item placement and rarity are what pace it. An entry without `level`
used to be silently ineligible forever, so a Mimic that should become Pandora at
level 1 the moment the item exists could not be authored at all.

**One transformation, four callers** (`engine/transform.lua`). Promotion, Egg
hatching, Homunculus metamorphosis and the reversible Kappa curse preserve the
same things (growth record, seed, permanent gains, learned skills, name, level,
history, provenance, Favorite Food) and swap the same things (MPD, capacities,
affinities, innate skills/passives). They differ only in how the destination is
chosen, so they are one primitive rather than four copies that would drift.

`TRANSFORM_ACTOR` exposes it to data — no engine code knows what an Egg or a
Kappa is:

| `actor` | destination |
|---|---|
| `<id>` | that species |
| `"hatch"` | the actor's `hatchOutcomes` keyed by the instance's saved `provenance` (with a provenance-specific fixed bonus) |
| `"metamorph"` | deterministic nearest eligible species by permanent parameter profile |
| `"revert"` | the remembered origin form |

`reversible: true` remembers the current form. A natively recruited creature has
none and never reverts — the only difference between a native Kappa and a cursed
one. Metamorphosis is deterministic because the design shows the player its
destination *before* it happens; a random result would make that preview a lie.

`actorData.autoTransforms` applies the same primitive after level gains. A rule
may name a direct actor, `hatch`, `metamorph`, or `revert`, and gate itself with
`atLevel` or `afterOriginLevels`. Egg cracking and curse recovery are therefore
automatic without putting species names in Lua.

Homunculus classification first checks ordered `secretTransforms`. Their
formulas receive only `intrinsic.level/maxHp/atk/def/mat/mdf`, assembled from
base parameters, accumulated growth, and permanent item gains. Equipment,
states, and current HP are absent by construction. The first matching rule
wins; otherwise classification falls through to nearest `eligibleFrom` profile.

**Favorite Food** is one exact item drawn from the species' authored
`favoriteFoods` pool, fixed at creation from the growth seed (so a reload cannot
fish for a better one) and carried through every change of form. It is the
individual's, not the species'. Eating that exact item discovers the preference
and starts the item's authored `savor` traits. Savor cannot refresh while active,
is saved on the individual, and `TICK_SAVOR` reduces it after victories only.
Meals are explicitly marked `meal`, must be field-only, and food identity uses
the registered `foodTags` vocabulary.

Three general battle traits complete the content vocabulary: `TARGET_RATE`
weights random enemy AI selection (Provoke), `ELEMENT_RATE` multiplicatively
modifies damage from one named element, and `KILL_MP_RESTORE` restores flat
Summoner MP when its carrier personally kills or Executes a target.

The expanded roster uses a shared elemental skill library rather than giving
each species a private spell list. Red emphasizes escalating damage, Blue mixes
ice/water pressure with magical defense, Green mixes wind, sleep, regeneration
and growth, White owns healing/cleansing/protection, and Black owns weakening,
sleep pressure and dark offense. Creature-named actions are exceptional
identity rewards, currently Mesmerizing Light, Aqua Dish and Fairy Court.

The systemic item atlas adds 150 authored objects: 28 weapons, 28 armors,
36 accessories, 48 consumables (including twenty culturally grounded foods),
and ten promotion keys. Equipment tiers are authoring/placement metadata rather
than an automatic statistic formula. Remains remain valid ingredients while
also being wearable, and are excluded only from generated outputs. Promotion
keys are mechanically gated to have no effects, no equipment slot, and neither
input nor output membership in Item Creation.

Party meals separate creature-targeted effects from shared Summoner effects:
HP recovery and Savor resolve for every eater, while MP recovery resolves once
for the shared pool. `HEAL_RATE` supplies Healing Staff-style skill healing
without affecting items or permanent gains.

### 1.11 The Summoner MP economy (26.07.2026)

**A step costs exactly the combined MPD of the living manifested party**, with
no Summoner base cost — `party.mpd` in `formula.groupView`, charged by the
`exploration.step` flow. Living only: a creature that dies stops costing
anything. One shared query, so the traversal cost, Strain and any UI preview
cannot disagree about what the party costs. It replaced a flat
`dungeon.moveMpDrain` applied in `exploration.lua`, which charged the same 1 MP
whether the Summoner was carrying a Pixie or a Bahamut — the entire expedition
economy was invisible.

**Ordinary battle rounds cost nothing.** Taking a tactical turn is not priced.
That is a deliberate reversal: every round used to drain each ally's MPD, which
billed the expedition for simply fighting and made a heavy party unaffordable in
a way the design explicitly rejects.

**Battle Strain** is the pressure against indefinite combat instead, authored in
`battle.round_end`:

| Completed round | Cost |
|---|---|
| 1–5 | nothing |
| 6–9 | combined party MPD × 4 |
| 10–14 | × 8 |
| 15+ | × 16 |

Opening Max MP is 3000 against a cap of 9999 (`system.summoner`), the scale the
balance tables in `creature-parameters.md` are written against — 3000 MP buys
600 steps at party MPD 5.

An accessory may modify a wearer's MPD through the ordinary `PARAM_PLUS` /
`PARAM_RATE` traits and **can never push it below 1**, because `traits.getParam`
floors every parameter at 1. That is not a special case for MPD; it is why the
design's "never below 1" needed no new mechanism, and a test pins it so a future
change to that floor cannot quietly make an MPD-0 creature possible.

### 1.12 States, categories and status infliction (26.07.2026)

A state carries a **list** of categories from `engine.json -> stateCategories`
(`negative`, `positive`, `physical`, `magical`, `mental`, `common`). A list,
because a state is routinely several things at once — poison is negative *and*
common *and* physical — and each tag is a separate handle a resistance can grab.
G1 fails an unregistered category on a state or on a trait naming one, because a
resistance keyed to `negatve` protects against nothing and says so nowhere.

**`common` is earned, never inferred.** It marks an ordinary, commonplace
affliction: the family a broad protection is meant to cover, and the tag a
Ribbon-style blanket immunity keys off. Nothing is exempted by *absence* of a
tag. This matters because the obvious alternative is broken: rates multiply, so
a blanket authored against `negative` would also cover `dead` and quietly make
its wearer immune to any authored death effect. Death simply never earns
`common`.

**`FORCE_ACTION`** takes the choice away: the holder uses the skill its `dataId`
names, whatever it or the player picked, targeted by that skill's own spec. It
is applied in `Battle:buildTurnQueue` and at the head of `getAIAction`, so **one
rule binds both sides** — a berserk enemy and a berserk party creature are
compelled by the same code, and nothing in the engine knows what "berserk"
means. The battle scene additionally skips compelled creatures in the command
menu; that is presentation of the rule, not a second copy of it, because
offering a menu whose result is discarded is worse than not offering one.

The AI check comes *before* its skill roll: choosing and then discarding would
still consume battle RNG and shift every later roll in the round.

Infliction is a three-part chain, clamped to 0..1:

```text
final chance = skill chance * attacker STATUS_SUCCESS * target state rate
```

Splitting it three ways is what lets a control specialist be better at landing
conditions without rewriting every skill, and a resistant creature shrug them
off without the skill knowing who it hit. The target rate is itself the product
of every `STATE_RATE` naming the state and every `STATE_CATEGORY_RATE` naming
one of its categories — multiplicative, so a narrow and a broad resistance
compound rather than one silently winning.

**A rate is a slope, not a switch (01.08.2026).** Driving one to 0 makes a state
vanishingly unlikely on the ordinary path, but a critical hit still forces it
through. **Absolute immunity is its own trait** — `STATE_IMMUNITY` naming a
state, `STATE_CATEGORY_IMMUNITY` naming a category (a Ribbon's actual spelling)
— and it is the only thing a critical cannot bypass.

That separation replaced "a rate of 0 is immunity", which had overloaded one
number with two meanings. It **deleted** the critical-status exemption §1.13
used to carry, and it freed the stat-derived resistance curves below to reach or
pass zero without a stat quietly drifting into categorical immunity. G1 rejects
a `STATE_RATE`/`STATE_CATEGORY_RATE` authored as 0 outright, because anyone
writing that means immunity and would otherwise never learn they did not get it.

Immunity emits a `state_immune` event and a line of text rather than passing
silently, because a status that simply never appears looks identical to a bug.

**Defensive stats resist afflictions (01.08.2026).** The target's own *base*
`def` and `mdf` fold into the same product, through the `stateResistFromStat`
curves in `system.json` — DEF as the body's resilience against `physical`
afflictions, MDF as the spirit's against `magical` and `mental`. It needed no
new mechanism because the rate is already a product. This is what gives the
defensive stats a job beyond mitigation, per the wider reading of the stat names
(`mdf` is Spirit, `def` is Vitality) in `docs/design/skill-costs.md`.

Two guards, both load-bearing:

- **Base, not final.** Gear that raises a defensive stat buys damage mitigation;
  anti-affliction gear stays authorable as an explicit `STATE_RATE`, which says
  what it does. Same rule the charge economy follows (§1.20).
- **Afflictions only.** `physical` and `magical` are *shape* tags, not intent
  tags: `defending` and `provoke` are positive **and** physical, `regen` and
  `magicGuard` positive **and** magical. Without gating the curves on
  `negative`, a creature's own VIT would resist its own Defend, and the sturdier
  it got the more often bracing would silently fail. Explicit trait rates are
  deliberately *not* gated this way — an author who writes a rate against a
  positive state means it.

**Critical evasion.** Because a critical is the universal status backdoor, being
hard to crit is worth twice what it looks like: less burst damage *and* fewer
forced afflictions. `CEV` subtracts from the attacker's `CRI`. It is
trait-driven only — gear and passives buy it, no stat derives it, or DEF would
become a super-stat on top of mitigation and affliction resistance. The roll
happens even when `CEV` has driven the rate to zero, because skipping the draw
would consume one fewer `math.random` and shift every later roll in the round.

### 1.13 The damage model (26.07.2026)

Damage is **relative**: a share of the attacker's power decided by the ratio
to the defender's matching stat, per `docs/design/creature-parameters.md`.

```text
potency * power^2 / (power + defense)
```

The useful property is the share table — 100% of power at zero defense, 50% at
`defense = power`, 33% at twice, 25% at three times. It never reaches zero, so
scratch damage is real and a Pixie punching a Golem is meant to be an almost
useless action rather than an impossible one. It replaced a `val * (10 / DEF)`
divisor that got this backwards at low DEF and had no notion of potency.

Resolution order is fixed, and `resolveDamage` in `engine/effects.lua` is the
one implementation — `hp_damage` and `hp_drain` share it so a drain can never
drift from the curve:

```text
relative damage -> potency -> element -> critical x1.5 -> DAMAGE_RATE -> floor 1
```

**Elemental affinity is signed before it is multiplied (08.08.2026).**
`effects.elementMultiplier` in `engine/effects_core.lua` is the single runtime
authority. Skill element and acting-creature identity remain two independent
channels. Inside either channel every authored source/target relationship from
`data/elements.json` contributes `+1` when strong, `-1` when weak, and `0` when
neutral. The channel sums those relations first, so favorable and unfavorable
pairings cancel exactly before any multiplier is produced. A positive net score
uses that channel's diminishing strong curve from `data/engine.json::elementRules`;
a negative score uses its multiplicative weak curve and `weakFloor`; zero is
exactly `1.0`. The resolved skill and innate multipliers then multiply together.

This makes repeated colors **depth** and distinct colors **breadth** without a
named-combination rule: `Red, Green` versus Blue is innately neutral, while
`Red, Red, Green` versus Blue retains one net unfavorable relation. RGB receives
no special treatment; its clean cancellation against the RGB cycle follows from
the same signed count. Explicit target `ELEMENT_RATE` traits are applied only
after these two affinity channels as their own modifier layer. Relationship
shape stays authored in `elements.json`, all numeric strengths/decays/floors stay
in `engine.json`, and broad damage/skill retuning is deliberately a later balance
pass rather than part of this aggregation rule.

**Stat pairing.** `power` names the attacker's stat and `defense` defaults to
the stat it is paired with: `atk` meets `def`, `mat` meets `mdf`. An
exceptional skill may author `defense` to cross them. This matters more than it
sounds: before it, *every* action reduced through DEF, so a creature could
advertise ruinous MDF and never once be hit through it — Golem's entire
promised identity was unreachable. Archangel's Holy Smite against Golem went
3 → 15 on this change alone.

**Armor penetration** ignores a share of the defending stat *before* the curve,
from an effect's `penetration` plus the attacker's `PENETRATION` trait, added
then clamped at the whole stat. Applied to the defense rather than to the
damage on purpose: against a soft target it is worth almost nothing, against a
wall a great deal — which is what separates it from simply hitting harder, and
is the Pile Bunker's whole job.

**Execution.** An attacker carrying `EXECUTION_THRESHOLD` finishes a *surviving*
target left at or below that fraction of Max HP. Checked after the hit, so it
closes a wounded enemy and never gambles on a healthy one. `EXECUTION_RESIST`
**subtracts** from the threshold rather than rolling against it: that costs no
randomness (so it cannot perturb the golden stream), makes partial resistance
exact rather than a second dice roll, and lets Safety Bit be an ordinary 1.0.
It is separate vocabulary from state resistance because execution is not a
state and must not be smuggled in as one.

**Direct damage.** An effect authoring `formula` *instead of* `power` is the
direct path: the authored number lands as-is. A trap that says 20 deals 20. It
takes no critical and no `DAMAGE_RATE`, matching the rule that guarding does
not blunt authored indirect damage. These are two authored intents, not a
compatibility shim — the relative path is for actions with an attacker, the
direct path for authored consequences.

**Combat vitality.** Ordinary recovery stops at effective Max HP and never
deletes HP that is already above it. A healing effect may explicitly author
`overheal = true`; its ceiling is `overhealCap`, then
`system.combat.overhealCap`, then the engine's safe 1.5x fallback. Overheal is
real current HP, so damage consumes it normally and HP ratios remain unclamped
above 1. Temporary Max HP is a separate lifetime: an active `PARAM_PLUS maxHp`
state grants its new capacity as current HP, and expiry clamps excess HP without
damage, death or hit reactions. Formula/declarative-UI battler views expose
`maxHpParts.underlying`, `maxHpParts.active`, `maxHpParts.activeModifier`,
`hpRatio` and `overheal`, so presentation never has to infer these distinctions
from raw deltas.

**Criticals** roll in `effects.lua` rather than `battle.lua`, so every damaging
action gets them on one code path and a multi-hit action rolls per hit as the
design requires. Base rate is 5% (`traits.getRate`'s `CRI` default), multiplier
is `system.combat.criticalMultiplier` (1.5 — permadeath makes larger defaults
excessively volatile). A critical is reported on the damage event and gets its
own `critical|` line in the golden log, because a crit and an ordinary hit for
the same total are otherwise indistinguishable to G2.

Criticals also carry Brigandine's status rule: a damaging action that crits
guarantees the status attached to it, bypassing the authored chance. That is
why `APPLY_EFFECT` builds **one context per target** shared across the action's
effect list — the damage effect records the crit on it and the `add_status`
effect after it reads it. The rule has **no exemption for resistance**: a crit
forces the status through any rate, however low. The only thing that stops it is
an explicit `STATE_IMMUNITY` / `STATE_CATEGORY_IMMUNITY` trait (§1.12).

The effective critical rate is the attacker's `CRI` minus the target's `CEV`.

**Accuracy** is rolled once per target in `APPLY_EFFECT`, before any effect
resolves: `HIT` (attacker, base 100%) times `1 - EVA` (target, base 0%). A miss
skips that target's **whole** effect list, so an attack that misses cannot
still apply the status it carries, and accuracy is per target, so a multi-target
attack can connect with one creature and be dodged by the next.

Only offensive actions roll — the test is "carries damage, aimed at someone
else". A potion fed to an ally and a buff cast on oneself have nothing to
dodge, and letting them whiff would invent a failure the design never asked
for. A certain outcome takes no random draw at all, which is why adding
accuracy moved no existing golden line.

Before this, `HIT` and `EVA` were registered, `EVA` was authored on Shadow
Stalker, and nothing ever rolled either: every action always connected. Five
planned creatures (Golem, Talos, Giant, Hyperion, Kappa) are specified as
inaccurate or low-evasion, and none of that was expressible.

**Round-end HP drift** is the `HRG` trait summed across every source, applied
by `STATE_TICKS`. Negative is degeneration, so poison is not a second
mechanism — one trait, both directions, the way RPG Maker's works. A rate too
small to move a creature emits no event rather than a `+0` line. This replaced
a branch on `state.id == "regen"` / `"poison"`, which hardcoded two content ids
in the engine, left `HRG` dead everywhere it was authored, and meant only the
one id the engine named could ever regenerate — a second regenerating state
was unauthorable.

**`DAMAGE_RATE`** multiplies direct HP damage taken by its holder, and is
**multiplicative** across sources, unlike the additive rate traits — two
independent 0.5 protections must be a quarter, not zero. Defend is now
`DAMAGE_RATE 0.5` rather than doubled DEF, which was worthless against magic
and had inconsistent value under the relative curve. The same trait serves
barriers, protective equipment and vulnerability states.

### 1.14 Persistent expedition routes and Town Portal (27.07.2026)

A procedural floor is generated once per **expedition**, not once per map
transfer. `GameSession.mapStates` retains each visited dangerous map's grid,
events, fog, lighting, entrance, exit and last player position. Descending,
climbing, and portal travel restore that snapshot; a new safe-to-dangerous
departure clears the completed route and begins a fresh expedition.

Every generated floor has two physical landmarks. Common event 1 is the lower
stair and loads the next map with `LOAD_MAP arrival: entrance`. Common event 40
is the upper stair: Floor 1 returns to the safe map, while deeper floors load the
previous map with `arrival: exit`. Arrival is always on a passable adjacent
tile facing the relevant stair, never on top of its event.

`LOAD_MAP.arrival` is registry-authored (`entrance`, `exit`, `resume`).
Its `mapId` is the authored `maps[].id`; the loader resolves that id to the
current array position, so deleting or reordering map records cannot silently
retarget a warp. `PORTAL_TO_TOWN` follows the same authored-id rule.
`PORTAL_TO_TOWN` and `RETURN_TO_PORTAL` are reusable command primitives:
the first stores map, exact tile and facing before loading safety; the second
restores that point and closes the seam. Portal resume does not start a new
expedition or reroll any floor. Both the floor cache and an open portal
round-trip through `savegame.lua`.

The Town Portal item invokes the primitive through an ordinary common-event
effect. Its `meta.dungeonOnly` is registered and editor-authorable; usability
rejects it on safe maps before consumption. Cost, sources and scarcity remain
content balance rather than engine policy.

### 1.15 Stateful map presentation (27.07.2026)

`SET_MAP_PRESENTATION` changes a map's tileset, fog preset and ambient light as
one persistent event-authored state. A change applies immediately when its map
is active, survives transfers and save/load, and is validated against the
tileset and fog registries. Campaign events use this to let town-state changes
announce themselves spatially—for example, St. Maria's first festival arrives
as an unforeshadowed change in color, light and inhabitants.

### 1.16 Illustrated town interiors (28.07.2026)

`ENTER_LOCATION` selects a static image under `assets/locationArt/` as the
backdrop for the current map-event conversation. The dialogue scene keeps its
ordinary windows and command graph; only its map backdrop is replaced. Returning
to the map clears the location automatically, so exterior conversations cannot
inherit a previous room.

Location images are still frames. Door events occupy `#` cells and use their
ordinary `sprite` image as an overlay in the wall compositor, receiving the
same edge treatment, lighting, fog and raycast projection as the wall itself;
they never enter the billboard pass. Running forward into a `trigger: bump`
door starts its event without a confirm press.

That compositor is not door-specific: any map event with `wallEvent: true`
occupies a `#` cell, uses `trigger: bump`, and draws its ordinary sprite in the
wall slice rather than as a billboard. Generated up/down stairs and authored
wall fixtures use this same path. Procedural placement selects a surviving room
boundary with an adjacent passable approach cell. Dungeon interaction art is
stored as separate 64x64 sprites under `assets/sprites/dungeon_*.png`; the 3x3
generation layout is only a contact-sheet workflow, never a runtime sheet.

The threshold sequence zooms the centered wall door for 0.24 seconds and holds
that scale while the entire screen fades to black. Only at full black does it
start the conversation; it then lingers in darkness for 0.10 seconds before
uncovering the completely static interior through the subtractive fade. Leaving
burns that unchanged CG to black, after which the map returns
during a full-black hold, and the enlarged outside door settles back as the map
is uncovered. The blackout is composited into the map or illustrated-backdrop
layer; HUD and dialogue windows remain unaffected above it. The room remains
completely motionless afterward. St. Maria's initial set is the
assigned home, Alicia's bakery, Laura's forge, the Rusty Tankard and the chapel.
Their native runtime PNGs are palette-limited, game-resolution derivatives.
High-resolution generation sources are local working files and are ignored.

The blackout uses the shared subtractive fade primitive rather than an
alpha-black overlay. At progress `p`, a white fullscreen primitive is drawn
with subtract blending, producing `max(destination.rgb - p, 0)` per channel.
Dark channels therefore reach zero before highlights. Cinematics and doors
share this burn-to-black mathematics, while door zoom choreography remains
specific to doors. Drawing the subtraction during the map or illustrated
backdrop pass keeps HUD and dialogue UI outside the effect.

Dialogue `TEXT` commands may author `expression` from 1 through 5. Human
portrait sheets are five 128x192 columns; column 1 is always the default pose.
The selected column persists into the following choice until another spoken
line changes it. Expressions are complete character redraws rather than facial
swaps, and transparent silhouettes may exceed the nominal portrait rectangle
by half a tile without moving the shared bottom-window footprint.

### 1.17 String pictures and opening cinematic (28.07.2026)

`SHOW_STRING_PICTURE` creates or replaces a numbered screen-space text object.
String pictures expose pixel position, anchor, alignment, wrapping width, font,
size, palette color, opacity, scale, shadow, optional frame and one of three
layers: `backdrop` (above the world but below windows), `screen` (above ordinary
scene UI), or `top`. `MOVE_STRING_PICTURE` interpolates position, opacity and
scale; `ERASE_STRING_PICTURE` may fade before removal, while
`ERASE_ALL_STRING_PICTURES` is the unconditional cleanup operation. They are
presentation objects rather than save state and are cleared by session reset.
An authored `reveal: true` makes a string picture use the same character timing,
UTF-8-safe prefixing and `ui.textRevealDelay` setting as ordinary dialogue
`TEXT`; cinematic captions therefore arrive like SHOW TEXT instead of fading
as whole blocks.

`SHOW_IMAGE_PICTURE`, `MOVE_IMAGE_PICTURE`, `ERASE_IMAGE_PICTURE` and
`ERASE_ALL_IMAGE_PICTURES` provide the bitmap counterpart. An image picture
names an asset path, numbered slot, screen position, anchor, opacity, scale,
rotation, layer and blend mode (`alpha` or `add`); string pictures expose the
same blend choice. Move commands interpolate all numeric presentation fields.
The renderer loads nearest-filtered assets and fails loudly when a path is
missing. Additive pictures let luminous sigils and exact engine-rendered titles
mesh with the live world without baking words into generated art. This lets
common events crossfade and move cinematic plates without introducing a
cutscene-specific Lua host.

`WAIT` in map/common-event graphs compiles to a pausing node; it does not run as
part of an immediate command batch. `ENABLE_EVENT_SKIP` names a `LABEL` in the
same common event. Cancel jumps to that label even during a wait, allowing the
event author to own cleanup and final state rather than having the host abort a
script halfway through. G1 rejects missing skip labels.

New Game starts common event 42 in the empty-window `cinematic` scene. Its
authored sequence moves through nine generated plates from one retained 3x3
production sheet: distant approach, tactile travel details, the town bell,
residents reacting in the street, the Passage House courtyard and room, the
guarded approach, the Labyrinth threshold, and a final close Saban beat.
Creature appearances alternate with geography, architecture and object
inserts; every crop is composed for the 4:3 runtime canvas. Character-revealed
captions accompany the plates, followed by a St. Maria location card. The event
exposes `ESC: Skip`, and
always rejoins at `intro_cleanup`, which clears pictures, disables skipping,
loads St. Maria, and opens the static Room 3 interior. The arrival plates
establish that the player rode into St. Maria on Saban, their long-standing
mount and only summon. The player first receives control only after the Passage
House handoff establishes that this is one of five rooms kept for visiting
Summoners, that the others are empty, and that the room has been awkwardly
adapted for both travellers. Saban is never assigned by St. Maria. Leaving uses
the ordinary reverse door transition and places the player beside its exterior
door. The opening therefore reveals cinematic, room, and navigable town in that
order instead of cutting directly into free movement. The title scene uses
`assets/title/st_maria_title_psx.png` as a native-size static backdrop and
renders its title, subtitle, and copyright through the same string-picture
commands used by the introduction.

Defeat keeps the persistent battle dock in place through the battle's final
fade, then hands it to `game_over` for the dock's single close animation. The
scene reveals `assets/cinematics/game_over_talisman_psx.png` from a full
subtractive fade and applies a slow vertical drift while its title, aftermath
message and return prompt open in three timed beats. The plate remains at
exactly 1x scale throughout: cinematic pictures do not zoom because resampling
creates visible artifacts. Its `on_exit` hook clears the image picture and
subtractive fade before the title scene is entered.

Narrative image batches may be generated as exact contact sheets and split by
`tools/image/split-contact-sheet.ps1`. The tool takes grid geometry and one
name per cell and emits only an antialiased, palette-limited 256x240 runtime
plate. High-resolution generation sheets are local working files outside the
repository. The retained crops under `assets/cinematics/ideation/` supply the
four interior studies still referenced by events. The retained
`arrival_saban_contact_sheet.png` and its nine root-level crops supply the
prerendered opening.

### 1.18 Opening expedition roster and floor ramp (28.07.2026)

The opening party is authored through `system.newGame.party.fixedMembers` (in
`data/system.json`) and contains one member in slot 1 (front-left): the unit
`moa`, carried at level 3 under the instance name **Saban**. A fixed member may
carry an instance name and preferred `slot` (1--4); new-game construction
preserves them rather than assigning a random ally name or repacking — Saban is
that mechanism's own example, which is why the roster shows a name the unit
table does not have. Read the roster from `system.json`, not from here. Narratively, Saban predates the arrival: he is the player's
mount, travelling companion, and sole opening summon.

### 1.19 Explicit actor art roles and native big battlers (29.07.2026)

Every actor authors three distinct visual keys: `smallBattler` is the animated
compact sheet used by party cells and map recruitment billboards, `portrait`
is the dramatic cropped illustration used by status and other portrait
surfaces, and `bigBattler` is the uncropped full-body enemy illustration.
The former generic actor `spriteKey` no longer exists.

Big battlers render at their PNG's native pixel dimensions. The battle layout
chooses only a bottom-centre anchor for each troop member; it does not fit,
normalize, stretch, or otherwise scale artwork to the troop slot or viewport.
Authored overlap and clipping are therefore intentional presentation outcomes.
Animation transforms remain relative to that native size.

G1 requires all three actor fields and resolves their assets through the same
lookup rules used by presentation. The actor editor exposes separate pickers
and previews for all three roles.

---

### 1.20 Skill costs: charges, Overcast, availability (01.08.2026)

**No ability costs MP.** MP is the Summoner's shared expedition pool (§1.11);
charging a per-skill cost against it meant every heal a creature cast came out
of the party's remaining walking distance, and gave every caster the same
wallet. `mpCost` (and `spCost`) are removed from the data and rejected by G1 —
they were authored across most of the database and read by *nothing*, so there
was no balance behind them to preserve. Design intent and the full rationale
live in `docs/design/skill-costs.md`.

Two families, one predicate:

| Family | Resource | Question it answers |
|---|---|---|
| Magic | **Charges**, refilled at Rest | "How many more times today?" |
| Physical | **Cooldown / warmup / condition** | "Can I do it *this turn*?" |

`usability.canUseSkill` is the single authority, consulted by the player's
battle submenu, `Battle:getAIAction` **and** the status scene — so a row the
player sees greyed is a skill the AI cannot pick either, the same "one rule
binds both sides" principle `FORCE_ACTION` follows (§1.12). A known skill is
never hidden; it is shown with its reason, because a row that vanishes looks
like a bug. This is also why `conditionText` is mandatory alongside `condition`:
a formula cannot produce readable text.

**Charges** are authored as a formula against the caster (`4 + b.base.mdf / 4`),
so a promoted caster gains castings without the skill row changing, and they
live per-creature *and* per-skill on the battler — saved, like `wardCharges`,
because they are creature state. Missing key means full, so an old save or a new
summon arrives rested rather than mute.

**Overcast** is the one path from a skill to the shared pool, offered *only* at
zero charges (never as a cheaper alternative, so there is nothing to optimize)
and never to enemies, who have no Summoner. `"charges": 0` is a pool that exists
and is permanently empty — the Overcast-only shape, intended for a dragon's
Breath, which is not a daily supply but something drawn out of its Summoner.

**Rest** is `GameSession:rest()` — one definition shared by `RECOVER_PARTY` and
main.lua's callback, which previously carried two hand-copied versions of the
same reset. HP/MP reach the fielded party; **charges reach reserve and storage
too**, because rest is a location, not an activity, and a bench that stayed
spent would make swapping useless. **Promotion is a rest**; levelling is not.

**Cooldown and warmup are battle-scoped** and never enter a save: charges answer
"how much is left of the day", these answer "what can I do this turn". They are
ticked by `TICK_SKILL_TIMERS` authored into `battle.round_end`, not by a branch
beside the round counter — the end of a round is a phase made of steps, and a
new step should be a line of data.

**Base stats, not final.** Charge formulas read `b.base.*` (a lazy accessor over
`traits.getBaseParam`, mirroring `b.trait.<CODE>`). Equipment must not buy
castings; a `PARAM_RATE` debuff must not shrink a *maximum* while the creature
holds spent charges; unequipping mid-dungeon must not shift max charges under a
creature's feet. Same rule the stat-derived affliction resistance follows
(§1.12): **base stats say who a creature is, final stats say how hard it is to
hurt right now.**

### 1.21 Icons: one renderer, palettes as data (02.08.2026)

**Every icon in the game is drawn by `ui.drawIcon`.** Presentation modules
decide *which* icon, *where*, at what scale, whether it is shadowed, disabled
or tinted. They do not compute iconset coordinates, build quads, cache quads,
touch `iconset.png`, configure the palette shader, resolve palette or profile
data, or restore graphics state afterwards. That list is the whole point: it
used to be scattered, and every future icon feature — rarity borders, cooldown
overlays, stack counts, pulsing selection — is a change in one file instead of
a migration across every caller. No module outside `presentation/ui.lua` may
draw from the iconset.

**A recolour is authored as two plain fields.** `icon` stays an integer forever
and never becomes a number-or-object union; the palette rides alongside it:

```json
{ "icon": 51 }
{ "icon": 51, "iconPalette": "sapphire" }
```

The first renders in the icon's original colours; the second recolours it.

Absent or empty palette means original colours, so all pre-existing content is
already valid and no migration was needed. Two registries back it:

| File | Holds | Scope |
|---|---|---|
| `data/iconPalettes.json` | Named 4-colour ramps | Chosen per item/skill |
| `data/iconKeyProfiles.json` | Which pixels of a source icon are recolourable | **Shared by every use of that icon** |

That split is the design. Choosing ruby over sapphire is a per-item decision an
author makes constantly; deciding which pixels of icon 51 are its recolourable
region is a property *of icon 51*, calibrated once and inherited by every item
that uses it. A profile omitting a field inherits it from `default`.

**The four palette entries are control points at 0, 1/3, 2/3, 1 — not four
buckets.** The ramp is interpolated piecewise in sRGB (the space the hexes were
picked in). Quantizing was tried first and was wrong for this art: the source
icons are already colour-limited, so rounding each pixel to one of four stops
discarded most of the shading that was already in them, and with a 0.10–0.95
lightness window over four equal bands the highlight stop essentially never
fired. Interpolating preserves the source's own gradation.

**The lightness window is the calibration knob**, and it is what an author
reaches for when a recolour looks flat. It maps onto the ramp, so a window far
wider than an icon's actual shading range confines that icon to part of the
ramp. Narrowing `minimumLightness`/`maximumLightness` to the icon's real range
brings the whole ramp, highlight included, into play — one profile edit, felt
by every item using that icon.

**Resolution reads the registries through `require("data.loader")`, and there
is no hardcoded fallback copy anywhere.** Both rules are scar tissue. The
runtime originally reached for a non-existent `loader` global and the editor
for `window.dbPayload` (a `let`, so never on `window`); both silently resolved
nothing, so *no icon was ever recoloured* on either side while 190 items
authored palettes. The editor papered over its version with an inline palette
table that had already drifted from the data file. A second copy of a registry
is not a fallback, it is a slow-motion bug.

Gated by `tests/test_icons.lua`: reference resolution, palette lookup, profile
inheritance, and the ramp itself rendered through the **real compiled shader**
to a canvas and read back. The shader compiles on every gate run, because a
swallowed GLSL error would disable recolouring game-wide while looking exactly
like "no palette was set". G1 additionally rejects malformed palettes, inverted
lightness windows, unregistered `iconPalette` references, and a palette on a
non-positive icon.

**Known gap (03.08.2026):** nothing validates that an `icon` points at a cell
that actually has pixels. After the iconset was pruned of redundant recolours,
39 items pointed at deleted or out-of-range cells and rendered blank silently.
Re-authoring those onto surviving base icons plus a palette is content work; a
bounds-and-emptiness check in G1 is the insurance.

### 1.22 The trait/effect readout is a vocabulary, not a sentence (03.08.2026)

Item panes state what a thing does as **two columns**: a short noun on the
left, its one number right-aligned against the pane's inner edge, coloured by
whether the number helps or hurts the holder.

```
Heal                190
Savor
 Dmg Taken          90%
```

The readout used to be assembled from the editor's own labels, which are
authoring names, not player words. That produced `Parameter +: Atk + 23`,
`HP Restore: Value 60`, and an `Armor Penetration: 45%` that wrapped across
**three lines** in the 14-tile info pane. The registry label was doing two
jobs — naming a code for the author and describing an effect to the player —
and the second job is the one it was bad at.

**The vocabulary is data.** Every `traitCodes[]` and `effectTypes[]` entry in
`engine.json` carries a `display` block beside its authoring `label`:

| Field | Meaning |
|---|---|
| `short` | The player's word. `{d}` interpolates the subject (`{d} Risk` → "Sleep Risk") |
| `value` | How the number formats: `signed`, `percent`, `percentSigned`, `multiplier`, `multiplierSigned`, `subject`, `none` |
| `polarity` | Does more of this help (`higher`), hurt (`lower`), or neither (`none`) |
| `subject` | What `dataId` names: `param`, `state`, `stateCategory`, `element`, `skill`, `actor` |
| `icon` | Optional iconset index, drawn ahead of the label by `ui.drawIcon` |

**Tone is derived, never authored.** `polarity` plus the value's own sign
against the format's neutral point (1 for the multiplicative rates, 0 for
everything else) yields good / bad / neutral, which
`ui.toneColors` paints. This is why `DAMAGE_RATE 82%` reads green while
`STATE_RATE 150%` reads red though both numbers moved the same direction —
the author states which way the trait points, once, and every surface agrees.
Hand-colouring per item would have been 190 chances to disagree.

**Labels are budgeted at 11 characters** and truncate rather than wrap.
`tests/test_item_display.lua` enforces the budget, because a label that
overflows is not a cosmetic problem in a pane this narrow: it eats the value,
which is the column the player is actually scanning. The same suite pins the
tone rules and renders every registered code, and G1 rejects a registry entry
with a missing or malformed `display` block — a new trait cannot ship without
its player-facing word.

None of this is visible to G2 (battle logs), G3 (UI events) or G4. Only G5
sees it, and only for the frames a golden script happens to land on. The unit
suite is the real gate.

### 1.23 One map cell is 2.5 metres (04.08.2026)

**A map cell is 2.5 metres on every axis.** A wall is one cell high, a floor
tile is one cell square, and everything drawn on them is sized against that.

The engine does not know this and does not need to. `engine/geometry/plane.lua`
works in map cells and says so — scale there is "ABSOLUTE (in map cells)" — and
no metre appears anywhere in the code. The number is a *content* constant, and
until now it was never written down, so every texture and height map was
authored against whatever scale its author happened to imagine.

The constraint that fixes it is the wall. A wall is exactly one cell tall, and a
corridor a party walks down cannot have a one-metre ceiling; the moment a preset
contains architecture rather than texture — `wall_blind_arcade`, whose bays would
be 25 cm wide at one metre — the small readings become absurd. 2.5 m is the
smallest value at which the arcade, the hypocaust pilae and the flagstones are
all simultaneously plausible.

Why it matters for generation: **the eye reads scale from the feature, not from
the tile.** A square of pavement rendered with four huge slabs does not read as a
big tile, it reads as a small sample of a coarse floor, and the whole corridor
shrinks around it. Feature counts are therefore a correctness question, not a
taste one:

| feature | at 2.5 m | plausible | |
|---|---|---|---|
| flagstone (6×5 bond) | 50 cm | 40–60 cm | ok |
| cobble / sett (7×7) | 36 cm | 10–20 cm | **too coarse** |
| slab, `floor_slabs_varied` | 80 cm | 40–70 cm | **too coarse** |
| rubble boulder | 70 cm | 20–50 cm | **too coarse** |
| ashlar block, pilasters | 59 cm | 30–60 cm | ok |
| arcade bay | 62 cm | 60–120 cm | ok |
| hypocaust pila | 24 cm | 20–30 cm | ok |

The three rows marked **too coarse** were measured wrong at the time of writing
(04.08.2026) and deliberately left alone; they are re-authored when next
touched, not in a sweep. **That makes the marks themselves perishable** — a
preset fixed later leaves a row here still calling it broken, and nothing
detects that. So the durable content of this table is the *plausible* column,
which is a claim about human perception at 2.5 m and does not go stale; the
verdict column is a snapshot. Re-measure the preset before acting on a mark. A
new preset has no such excuse — check its feature size against the plausible
range before rendering it.

The same number belongs in prompts. "Broad fitted blocks" means one thing across
a metre and another across two and a half, and a model given no scale cue picks
its own.

### 1.24 2x2 Formation System, targeting shapes and Defend cover (05.08.2026)

- **`session.party[1..4]` is the single authority on formation.** Front row is
  slots 1 (left) and 2 (right); back row is 3 (left) and 4 (right). Holes are
  valid — Saban in slot 1, slot 2 empty, Pixie in slot 3 is an ordinary state,
  not something to repack. `Battler.row` is a derived property.
- **Save format `version = 2` preserves slot positions.** Payloads serialize
  `party` as `[p1 or false, p2 or false, p3 or false, p4 or false]`, which is
  what keeps the array positions intact through JSON. Version 1 saves migrate
  into slot positions automatically.
- **Targeting carries `shape` and `cover`.** A target spec's `shape` is
  `single`, `row`, `column` or `all`; its `cover` is `respect` or `bypass`.
  Cover resolves at execution time, immediately before the action runs: a
  hostile `single` + `respect` attack on a living back-row creature is
  intercepted by an active, living, unrestricted front-row protector carrying
  the `COVER_ALIGNED_BACK` trait — from the `defending` state via the `defend`
  skill at priority 100, for instance. The attack redirects to the protector
  and emits a `battle.cover_intercept` text event.
- **Recruitment is a transaction scene, not a prompt.** `OPEN_RECRUIT` opens
  the dedicated interactive `recruit` scene. Candidates persist as nodes in
  `session.recruitNodes`, indexed by a stable `sourceKey` (e.g.
  `map:1:event:4`), and support optional requirements (a gold or item cost, a
  challenge troop battle), deterministic equipment resolution, candidate
  `hpFraction` and states, and a `suggestedSlot` (1--4). On player confirmation
  it atomically builds, validates and applies one commit plan into party,
  reserve or storage, marks the candidate node completed, and sets
  `session.flags.first_recruit_complete`. `RESUME_RECRUIT` resumes a pending
  recruitment after a requirement battle.

The field Reserve scene is now an **Expedition Reserve**: four party slots plus
four reserve slots are the creatures physically committed to the trip.
Summoning and the old permanent Sacrifice command are absent from its reachable
popup and from the field command dock. Their interpreter primitives remain
available to authored content while the town-only summoning site and
inheritance/fusion replacement are designed; no field UI invokes either.

`GameSession.storage` is a distinct, save-persistent collection with 99 numbered
slots. `storeCreature` takes the first free slot and `withdrawCreature` moves an
existing instance into the first free expedition-reserve slot, refusing when
that reserve is full. While below, a populated creature context menu also offers
**Dismiss**. It transfers that exact instance to the first free town-storage
slot, making expedition room for recruitment; it refuses when storage is full
or when dismissing an active slot would leave the party empty. Dismiss is hidden
on safe maps. This is the engine foundation for a future town storage scene;
there is not yet a player-facing storage interface.

The first three Labyrinth maps author their procedural envelope. Floor 1 is
17x17 with 3--4 rooms and no random recruitment nodes; it owns a guaranteed
Cornered Pixie contract event. Floor 2 expands to 23x23 and 5--7 rooms. Floor 3
expands to 27x27 and 7--9 rooms, where the ordinary dungeon scale and recruit
pool take over. `exploration.generateDungeon` reads optional per-map room-count
and room-size bounds, falling back to global dungeon configuration when
omitted. Generated layouts remain cached for physical backtracking.

Those three maps form **Stratum I: The Bellroot Depths**. Strata are authored
campaign groupings rather than a second map type: their floors remain ordinary
maps with ordinary depth and stair rules. St. Maria's north approach separates
the guard from the threshold—the guard occupies a side alcove and handles
conversation, while a generated stone-and-iron gate is the bump-activated
entrance. An authorized first descent runs common event 43: it burns the town
to black, loads Floor 1 underneath, then slowly reveals the live polygonal world while
an additive bell-and-roots plate and exact string-picture title fade away.
Later descents retain the slow world reveal but do not replay the discovery
card.

The authored environmental encounters continue that relationship through the
deeper floors. The Cryptic Vault inventories St. Maria's ordinary possessions
and counterfeits Saban's stable; the Blood Chapel stages an unfinished Vigil
and questions which traveller is the summon; the Stillnight Sanctum turns old
Summoner records into a garden and threatens to separate what arrived together.
Each is an ordinary map event with a persistent discovery flag and changed
revisit text, so the environments participate in the narrative rather than
serving only as encounter backdrops.

## 2. Design rules (from the BIBLE — enforced by review)

### 2.1 Code sharing and reuse (CRITICAL)

No copy-pasted logic or coordinate mappings. Layout systems (party grid,
window geometry) are shared helpers used by exploration menus, battle
consoles, and target overlays alike. Math/physics (gravity, bouncing,
interpolation) lives in general update code, not scattered ad-hoc.
This applies to the editor too: form fields come from the schema layer
(`tools/editor/js/entity-forms.js`, `CONFIG_SCHEMA`), not hand-written DOM.

### 2.2 UI aesthetics

- Rich vertical gradients for major menus — never flat dark overlays.
- Micro-animations: panels slide in/out via timer states.
- Elements render as colored orb bullets from the system iconset
  (`data/elements.json` supplies the icon).

### 2.3 Battle feel

- Gauges never jump: smooth interpolation for damage and healing.
- Actors flash white/cyan on action, red on impact (system animations).
- Damage numbers launch with velocity and bounce under gravity.

### 2.4 One battler placement, and anchors (29.07.2026)

`presentation/battler_geometry.lua` is the **single authority on where a
battler is**. It maps a battler to a rect — the sprite box, plus the `frame`
box that framing UI uses (the portrait for an enemy, the whole status cell for
a party member) — and everything that attaches to a creature reads it: damage
popups, animations, target reticles, slot indicators and the enemy info block.

This rule exists because placement was previously computed in four places that
disagreed, so a popup could spawn at a fixed row y while the creature it
belonged to was elsewhere, and any layout tweak had to be repeated four times
or drift. **Never compute battler coordinates locally.**

Anything attaching to a creature does so with an **anchor spec**, resolved by
`battler_geometry.anchor(rect, spec)`:

| Field | Meaning |
|---|---|
| `point` | `center` (default) \| `feet` \| `head` \| `top_left` |
| `offsetX` / `offsetY` | pixels, applied after the point |
| `relativeOffsetX` / `relativeOffsetY` | fraction of the battler's OWN width/height |

The relative offsets are what make one authored effect correct at both scales:
`0.5` is 32px on a 64px enemy portrait and 12px on a 24px party sprite. An
animation entry authors its anchor in `data/animations.json` (`anchor`);
entries that author none take `battleLayout.animationAnchorPoint`. Damage
popups take `battleLayout.popupAnchor*`. An unknown `point` **raises** — G1
checks every animation entry and both battleLayout defaults, so a typo is a
build failure, never a silently centered effect.

The enemy info block (element icons + name + HP gauge) is data likewise:
`battleLayout.enemyInfo*` owns its width (96px default), its offsets **from the
creature's feet line** rather than an absolute row, and an on/off switch per
channel. It is **off** by default as of 31.07.2026: target selection already
shows the same name, HP and elements for the creature under the cursor, and
showing it permanently for every enemy duplicated that on top of the art.

### 2.5 When a window animates (31.07.2026)

Window open/close animation was assigned ad hoc — some popups had an open with
no close, three different effects, four different durations — which read as
inconsistency rather than as intent. The rule:

1. **Overlays animate.** A window that appears *over* what is already on
   screen — a popup, a confirm, the dock's party slots — opens and closes with
   `rescale`, **0.16s open / 0.10s close**.
2. **Siblings sharing a surface do not.** A window that replaces a peer on the
   same footprint (battle's command ↔ skill ↔ item ↔ target info) swaps
   instantly. There is nothing to reveal: the replacement is already there.
   Animating the outgoing one also re-resolves its content from live state
   while it closes, which is why the closing command window used to flash the
   skill list for a few frames.
3. **Scene furniture does not.** The panels that make up a scene's own layout
   arrive with the scene; the scene transition owns that beat, not each panel.

`dialogue_name` keeps its slide as a deliberate exception — it is a nameplate
attaching to a portrait, not a menu surface.

The motion itself is `ui.rescaleRect`: the windowskin is **rebuilt** at the
intermediate size with real 9-slice borders (never scaled as a bitmap), the
content is drawn at full size and **scissored** to it (never squashed), and
both axes advance at the same **pixel rate** — so a wide button reaches full
height almost at once and then unrolls sideways.

---

## 3. Gates (what keeps all of the above true)

| Gate | Command | Guards |
|------|---------|--------|
| G1 validate | `lovec . validate` → `VALIDATE OK` | Cross-references (every id link in data, incl. graphs/quests/scriptIds), command trees vs registry, formula compilation, targeting specs, scene windows, animation tracks, meta keys, zero-SCRIPT battle phases, required flow phases. |
| G2 golden battle | `tools/golden/check.ps1` | Battle simulation event log byte-identity, one reference per fixture (`tools/golden/battle_<key>.log`; fixtures authored in `data/goldenBattles.json`). Never regenerate to silence a red diff — regeneration is a reviewed, owner-signed action. |
| G3 golden UI | `tools/golden/check-ui.ps1` | Per-scene UI trace identity for every scene. |
| G4 engine state | `tools/golden/check-state.ps1` | `docs/ENGINE-STATE.md` matches what the engine actually reports (scene inventory + draw modes, registry counts, **registry entries with no implementation**, flow phases, content inventory). |
| G5 golden screens | `tools/golden/check-screens.ps1` → `SCREENS OK` | Rendered frame byte-identity, per scene and per goldenScript step. The only gate that can see the 3D world view. |
| G6 golden editor | `tools/golden/check-editor.ps1` → `EDITOR SCREENS OK` | Rendered frame byte-identity for every `tools/editor` tab and modal. The only gate that can see the editor. |

The `[formula] error in 'os.time()'` line during G1 is the sandbox
negative-test, not a failure. The editor runs G1 automatically after every
save (`/validate` endpoint) and surfaces problems in the UI.

**G4 is a documentation gate, and its failure mode differs from G2/G3.** A red
G2/G3 means a behavioral regression to investigate; a red G4 means the generated
doc is stale — run `tools/golden/capture-state.ps1` and commit the result. It
exists because documentation drift is a real, measured cost here: on 24.07.2026
four separate documents asserted implementation facts that had become false
(battle "frozen" on the legacy renderer, permadeath "not implemented", Item
Creation "quite early", the validator's location), which produced a wrong plan
that had to be walked back. Stale docs are worse than absent ones — they cost
rediscovery *plus* an incorrect conclusion. Hence: **prose states intent;
generated output states status.** `docs/ENGINE-STATE.md` is never hand-edited.

Its "registry entries with no implementation" section is the drift detector that
matters most: it distinguishes entries implemented in Lua, entries implemented in
data (a flow/scene consuming them), entries merely *assigned* to content with
nothing consuming them — these lie to the player, which is what `ON_PERMADEATH`
did for months while the `rebirth` passive advertised it — and entries declared
and never referenced at all.

### 3.1 Coherence vs. reachability

G1 asks whether a reference *resolves*. Two further questions do not reduce to
that, and they are answered in two different places on purpose.

**Coherent pairs are G1's job.** Where two pieces of data name each other but
only one side is ever read at runtime, the unread side is invisible dead data —
it cannot fail, it simply never happens. `elements.json` carried "White is weak
to Green" for a long time while `effects.lua` read only the attacker's lists, so
that penalty never landed on anyone; G1 now requires affinity to be reciprocal.
The same shape recurs, and each of these is now a G1 failure: a trait whose
`dataId` disagrees with the registry's `usesDataId` declaration (or names a param
`traits.getParam` never reads, or a dropped element); a `remove_status` effect
naming a state that no longer exists; a map `treasures`/`recruits`/`encounters`
pool entry that resolves to nothing (these are indexed by a random roll at
runtime, and `session:addItem` stores whatever it is handed, so a stale id became
a phantom inventory row — four such ids had two floors of chests handing out
nothing); an evolution `cost.item` that is not a `promotion_key`; a discipline
`stat` that is not a readable param; and a `flag:<name>` condition that no
`SET_FLAG` or quest reward ever writes, which is a branch the player can never
take. The reverse flag direction (written, never read) only warns: a flag may
legitimately be staged ahead of the content that reads it.

**Reachability is a report, not a gate:** `lovec . reachability`. It sweeps for
content that resolves but that nothing can produce — items no reachable shop
sells and no craft yields, shops no `OPEN_SHOP` opens, creatures no pool or
promotion path grants, states nothing applies, common events nothing calls — and
it swings the real Item Creation model over its whole possibility space
(`engine/craft.lua`, every ingredient pair × every crafter, at the ideation
centre) rather than re-implementing it. It always exits 0 **by design**: "nothing
produces this yet" is normally a design observation, and authors legitimately
build content before its source, so gating it would punish the ordinary order of
work. Read it, judge each entry, then either wire up the source or delete the
content. The repo-wide caution about "is this referenced?" sweeps applies to it
in full: ids are also resolved at runtime from pools and hooks, so each section
names the exact producers it knows about, and a new kind of producer must be
taught to the sweep rather than the sweep weakened.

Mechanical-rule enforcement map: registry/context/zero-SCRIPT/dangling-id
rules → G1; **paired-data coherence → G1; reachability → the advisory
`reachability` report**; behavioral regressions → G2; scene UI events → G3;
what the game actually renders → G5; what the editor actually renders → G6; the
aesthetic and code-sharing rules (§2) are review-enforced — call them out
in PR review when violated.

**G5 and G6 are the two pixel gates**, and they exist for the same reason: the
event- and log-based gates above them are blind to presentation. G5 covers the
game, G6 covers `tools/editor` — a form that renders no fields or a tab that
throws before it paints breaks no other gate, because G1 only ever looked at the
data the editor writes, never at the editor. Both compare pixels on one machine
and one GPU/browser: a driver, font or Chrome update can legitimately shift them,
and deciding that is an owner call, never a silent recapture. G6 is read-only by
construction (no step saves), which matters because the editor writes form edits
straight through to `data/*.json`; adding an editor tab or modal means adding a
step to `STEPS` in `tools/golden/editor-screens.py`, and the gate reports an
unclaimed reference as `ORPHANED`.

---

## 4. Editor (tools/editor)

- Vanilla JS + Node server (`server.js`), no build step. Data round-trips
  through `/data` and `/save` with stale-save (409) and shape guards.
- Database tabs are schema-driven where possible: `ENTITY_FORM_SCHEMAS`
  (entity tabs) and `CONFIG_SCHEMA` (system/engine config). A new simple
  tab should be a schema entry, not a bespoke panel. Complex editors
  (animation timeline, event commands, map painter) are custom by design.
- Previews go through the REAL engine (`lovec . preview-*`) — the editor
  never approximates rendering in the browser. **One deliberate exception:
  the icon picker** (§4.3), which recolours on a canvas in JS.
- Validation goes through the real engine too (`lovec . validate` via
  `GET /validate`) — no duplicated schema in JS.

### 4.1 One event language, one editor, one clipboard (27.07.2026)

The engine is made of event blocks (§0). It follows that **there is exactly one
way to edit a command list, everywhere one exists.** Map events, common events,
scene hooks, battle phases, troop battle events, quest hooks, action sequences
and an actor's recruit event are the *same editor* — `renderCommandList` in
`events.js` — reading the same registry and sharing one module-level clipboard.

**Map-event common-event links are templates, not command calls.** A map event
or event page with `scriptId` is linked to that common event: the linked common
event supplies the commands, and its `sprite`, `label`, and `minimapColor` are
presentation defaults when the map event does not override those fields.
This is the editor's **Link Common Event** mode and is a first-class runtime
feature. A map event or page with its own `commands` instead uses the editable
custom command list. `CALL_COMMON_EVENT` is different again: it invokes another
common event from inside a command list, but does not inherit any of that common
event's presentation properties. The obsolete field was `script`, not
`scriptId`; `commands` is the sole field for an owned command list.

`CHOICE.cancelOption` provides RPG Maker 2003-style Cancel behavior. It is an
optional one-based index into the authored options: Escape/Backspace executes
that option exactly as confirmation would. With the field absent, Cancel is
disabled. If an indexed option is hidden by its condition, Cancel is disabled
for that showing rather than entering an invisible branch.

Consequences, all of them load-bearing:

- **Commands copy between surfaces.** Ctrl+C in a battle phase and Ctrl+V in a
  troop event is a supported move, not a coincidence; that is literally how
  Battle Strain got from `flows.json` onto the base troop. A rule written in
  one place can be moved to a better one without retyping it.
- **A new surface is a call to `renderCommandList`, never a new editor.** If
  you find yourself writing a second command list UI, stop — the reason Troops
  shipped as a tab in an afternoon is that only the *container* was new.
- **The context set is closed and registry-backed.** `engine.json`
  `commandContexts` is the list; the validator checks commands against it and
  the editor builds its pickers from it. A command may only declare a context
  that exists, and every context must say where it is authored — G1 enforces
  both. This check exists because `TRANSFORM_ACTOR` spent weeks declaring
  `event` and `flow`, which matched no host context, quietly making it
  scene-only: a creature could not be transformed by a map event, and nothing
  failed. **A context with no editor surface is a command nobody can write.**
- **Pasting across contexts warns rather than silently breaking.** The
  registry knows which commands are legal where, so a cross-surface paste that
  cannot run names the offenders first — including ones nested inside branch
  bodies — instead of producing a G1 failure later that points at the
  destination rather than the paste.
- **Say so in the UI.** Every command list ends with a line naming the
  shortcut and the fact that it crosses surfaces. Seven identical editors that
  never mention each other read as seven unrelated boxes; the sharing has to be
  visible or it may as well not exist.

The generalisation: when a capability is already shared, the work is usually to
*surface* it, not to build it again.

### 4.2 A map owns its roster; a troop owns the shape of the fight (27.07.2026)

`data/troops.json` first gave every floor its own `*_wanderers` troop, whose
entire content was the weighted pool the map already had. Seven near-identical
troops, and a rename away from drift.

The split that removes them: **a map's `encounters` table is the floor's
roster — what can appear — and it stays on the map.** What a wandering
encounter *is* — how many, at what levels, under which base-troop rules — does
not vary by floor, so it is defined once as the `wandering` troop, whose one
member slot is `poolFrom: "map"`: a pool by reference rather than by value.
`combat.wanderingTroop` names it; a floor that wants something else sets
`encounterTroop`.

A map encounter entry and a troop pool entry use the *same field names*
(`actor`, `weight`, `levelMin`, `levelMax`) on purpose — a map's table is a
troop pool, so one can be pasted into the other, per §4.1.

The rule this is an instance of: **before adding a per-thing copy of a
definition, check whether the thing already owns the part that actually
varies.** Usually only the data differs and the shape does not.

### 4.3 The icon picker recolours in the browser, on purpose (02.08.2026)

This is the one place the editor approximates engine rendering rather than
round-tripping through `lovec` (§4), and it needs to stay the only one.

**Why it earns the exception:** calibrating an icon means dragging a hue or
lightness handle and watching the keyed region change under your hand. That is
a sub-second feedback loop over a single 8×8 sprite. Shipping each drag frame
to LOVE and back would make the one control that needs to feel continuous feel
like a form submission — and calibration is precisely the task that is
impossible to do blind.

**What limits the damage:** `tools/editor/js/icon-renderer.js` is the single
editor-side implementation — the picker, the database field swatch and any
future preview all delegate to it, so there is one JS copy, not one per caller.
Its `rampColor` and keying predicate are written to mirror the GLSL in
`presentation/ui.lua`, and the GPU-readback test in `tests/test_icons.lua` pins
the runtime half to specific numbers, so the thing being mirrored cannot move
unnoticed.

**Be clear about what is *not* covered.** There is no JS test runner in this
repo, so nothing gates the mirror itself: edit `rampColor` and no gate turns
red. The pairing is held by the pinned runtime numbers and by review, not by
automation. This is two implementations of one formula, which §2.1 otherwise
forbids, and it is accepted **only** because the alternative is an unusable
calibration UI. Whenever the shader's keying or ramp changes, the mirror is
part of that change, not a follow-up. Closing the gap properly means a JS
harness asserting `rampColor` against the same control points the Lua test
pins. Any *other* editor preview wanting this latitude should be refused —
use the real engine.

---

## 5. Process

- **`AGENTS.md` (repo root) is the agent entry point** — document authority,
  gate commands, non-negotiables, and the gotchas that cost real time. `CLAUDE.md`
  just points at it. Keep it short; architecture rules belong in THIS file.
- **Document authority order**: `docs/ENGINE-STATE.md` (generated, what exists) >
  this file (how and why) > GitHub Issues (what we have committed to do next) >
  `docs/design/` + `docs/game design/` (intent only, never status) >
  `docs/archive/**` (frozen, never authoritative).
- Owner-supervision rule: work touching `engine/battle.lua` /
  `engine/scenes/battle.lua` is owner-supervised, never autonomous.
- `docs/archive/plans/<round>/` directories are frozen history. New rounds add a
  directory; they do not edit old ones. When a round's rule survives, it
  gets merged into THIS file and cited from here.
- The multi-executor round workflow those directories describe — integration
  branches, candidate branches, briefs, verification debt — is **retired**. Its
  runbook is archived at `docs/archive/plans/ORCHESTRATION.md`; §5.1 and §5.2
  below are the parts of it that outlived the workflow. Current branch and
  integration practice is §5.3.

### 5.1 Judging a change before integrating it

Round-agnostic: this applies to any diff you did not write, whoever wrote it.

1. **Compliance** — does it meet what was asked, in full? Verify against the
   code, not against the PR text.
2. **Footprint vs intent** — diff size should roughly match the scope of the
   request. A ~1000-line diff for a "focused selector" is a red flag: usually it
   reformatted a whole data file or rewrote unrelated code. Reject that churn
   even when it works — it makes review impossible and buries risk. (Real case:
   five candidates for one task reformatted the whole of `engine.json` to
   deliver behavior a disciplined 140-line one delivered.)
3. **Quality** — matches surrounding style, reuses existing helpers, no dead
   code, no needless dependency.

Merging a change *plus your own fixes* is normal; say so in the merge message.
Re-run the gates **after** the merge, not just on the change in isolation — work
that is green alone can break once combined.

**Golden-master discipline.** `tools/golden/*` references are the equivalence
proof for behavior-preserving work, so such work must leave them byte-identical.
Work that *intentionally* changes behavior regenerates them and must present the
before/after diff with a line-by-line justification — and is owner-signed and
local, never delegated to an executor that would regenerate a reference out of
sight. A regenerated golden nobody read is indistinguishable from a silenced
regression.

**Verification debt.** Anyone who cannot run a gate declares it unrun, with the
reason, rather than reporting a pass. Whoever integrates the work clears the
debt by running it. An unrun gate is never merged as if it were green — see the
`savetest` failure mode noted in §3.

### 5.2 Defect patterns worth checking by reflex

Each of these is a real defect this project shipped or nearly shipped:

- **Force-path revert.** A modal that restores a snapshot on close must gate the
  restore on `!force`, or the Apply/Save path (which closes while still dirty)
  silently undoes the commit.
- **Empty-object churn.** UI that does `x.thing = x.thing || {}` on render
  stamps empty objects onto the payload; every save then rewrites files with
  noise. Materialize only on real edit; strip empties at save.
- **Bare-key vs path resolution.** Some references are bare keys resolved to a
  path at load (portrait key → `assets/portraits/<key>.png`). A preview that
  does `'/' + value` 404s for those — this is exactly what made a G6 frame look
  flaky while a real broken thumbnail sat behind it.
- **Hiding vs editing.** When you hide deprecated options from an ADD list,
  existing records using them must stay editable — re-inject the type for the
  edit dialog.
- **Alias determinism.** A consolidated command aliasing old ones must keep
  event emission identical or G2 breaks. Verify the golden, not just G1.
- **Editor Save reformats data files.** "Save Database" rewrites every
  `DATA_FILES` entry via `JSON.stringify(…, 2)`, reformatting compact
  hand-authored JSON. Before reverting a "dirty" data file, compare *content*,
  not formatting: parse both sides and diff normalized JSON.
- **A new data file goes in BOTH manifests** — `DATA_FILES` in
  `engine/server.lua` *and* `tools/editor/server.js`.

### 5.3 Branches, integration and what CI actually covers

Two things are **mechanically enforced** on `origin/main`; everything else in
this section is convention, and the difference matters.

- Ruleset `antidel` refuses branch deletion and non-fast-forward pushes. Any
  plan that rewrites published history on `main` — amend, rebase, squash,
  revert-by-reset — cannot be pushed, so say up front that it needs the owner to
  lift the rule. When a force-push is refused, replay onto the original tip
  (`git rebase --onto <original> <rewritten>`) rather than reaching for
  `--force`.
- Ruleset `verify-gates` requires the `gates (Windows)` check, strict. A
  required check **cannot be satisfied by a direct push**, because the check only
  runs after the commit lands — so requiring it would block push-to-`main`
  entirely. The ruleset therefore carries an admin bypass, which is what keeps
  the owner's direct-to-`main` workflow working. Removing that bypass would
  break it silently. Read the rejection text before diagnosing a refused push:
  the two rules fail for unrelated reasons and only one implies a rewrite.

**Convention:** scoped work goes on its own branch, prefixed by who is doing it
(`agent/`, `chatgpt/`, `codex/`) or by kind (`feat/`), plus a short topic.
`main` belongs to whoever is doing repo-wide work, and the owner tests from the
primary checkout on `main` — so finished, green work belongs there rather than
parked on a branch. Branches are not auto-deleted on merge, and all three merge
methods are enabled; **a squash-merged branch still reads as unmerged**
(`git log main..<branch>` is non-empty), so never infer from that alone that
work has not landed.

**CI covers six of the eight gates in §3, and the two it omits are the two that
can see anything.** `.github/workflows/verify.yml` runs on push to `main` and on
pull requests: G1, unit, save, G2, G3, G4. **G5 and G6 are excluded by design** —
they depend on GPU/driver and browser rendering, so a hosted runner would
manufacture false regressions. Reachability runs non-blocking, being a report
rather than a gate (§3.1). The consequence is the one to internalize: a green CI
says nothing about the 3D world view or the editor, and both must be checked on
the owner's machine before work is called done. "CI is green" is not "the gates
are green."

`node tools/check-spec-ci.js` is the **opt-in infrastructure assertion** for
the factual claims in this section. It needs an authenticated `gh` session and
network access, so it is deliberately neither a local gate nor hosted CI. It
checks the live default-branch rulesets by durable name, the strict
`gates (Windows)` requirement and bypass mode, `verify.yml` triggers and its
six-gate coverage split. A nonzero exit names the claim that is stale; update
SPEC deliberately after confirming an intended GitHub configuration change.

---

## 6. Consolidated design decisions from the pre-Issues briefs

The four briefs now kept under `docs/design/` were written before GitHub Issues
became the repo's durable-work mechanism. Their delivery checklists and
implementation diaries are not preserved here. The decisions below are the
parts whose rationale remains authoritative after delivery status is removed.

### 6.1 Summoner battle identity and loss (17.07.2026)

The player is the **Summoner**, but the Summoner is not a fifth battler. Fielded
spirits take the actions; the player directs each spirit; the Summoner stays
off-field and has no separate HP bar, spell list, or parallel command turn.
This makes the class identity an expedition/control relationship rather than a
second combat body layered beside the party.

Normal battle therefore has no summon, dismiss, sacrifice, or reserve-swap verb.
Reserve deployment is exceptional: when the manifested field wipes and reserves
remain, a reserve wave may deploy automatically. It costs no MP because its
price is structural — the previous field is lost and the party forfeits the
round while enemies continue — and exposing it as an ordinary command would turn
a desperation rule into routine party optimization.

A spirit at 0 HP remains downed while battle is unresolved so battle revival is
meaningful. A spirit still down when battle ends is permanently lost and may feed
the same sacrifice-rate economy used by ritual content. Game over is therefore
party **and** reserve exhaustion, never merely shared MP reaching zero. Row is a
persistent authored axis available to formula and presentation even when a
particular combat formula does not consume it; adding a state axis does not
oblige the UI to invent a command for manipulating it.

### 6.2 Battle presentation ownership (17.07.2026)

Battle is one composed presentation surface, not a collection of unrelated
panels. Enemy/party lanes, command console and battle log use the ordinary
window/layout data; target reticles, popups, transient wave notices and combat
effects remain cross-cutting overlays rather than being disguised as fake
windows just to fit the data model.

Battle actors are positioned relative to explicit battle-content rectangles and
shared battler geometry, not generic full-screen coordinates. Their authored
art may intentionally exceed a nominal enemy window; clipping every actor to the
window would make layout data override spatial art direction. Outer
virtual-resolution scaling remains renderer-owned so battle code never carries
a second set of scale assumptions.

Cost/gain preview is a **gauge capability**, not a battle or ritual subsystem.
Any surface showing the affected resource should be able to tint the pending
portion of the same gauge and show a compact delta. The same reuse principle is
why the larger Active/Magic/Junction/Item/Info exclusivity state machine was
dropped: Info does not need to force otherwise independent surfaces into a new
mutual-exclusion system, and item comparison is a separate concern.

### 6.3 Default + override authored behavior (17–18.07.2026)

Action sequences and quest hooks were chosen as extensions of the same eventing
architecture rather than new host-specific scripting languages: an authored
default defines ordinary behavior; an entry may select a shared named list or
carry an inline override; command validation and editing use the same registry
and command-list tooling as other event surfaces.

For **Action Sequences**, orchestration is separate from effect math.
`skill.effects` / item effects remain the source of damage, healing and status
semantics; the sequence decides *when and how often* those effects are applied.
`APPLY_EFFECT` is consequently the seam, and repeating it is the multi-hit
primitive. Animation and wait commands emit replay intent; they do not make the
authoritative simulation wait on wall-clock presentation.

For **quests**, `engine/quest.lua` is the one authoritative lifecycle owner.
Conversation graph opcodes request an offer or completion and choose the next
dialogue node from the returned outcome; they do not write
`quest:<id>:active/completed`, select hooks, or infer success from events.
`questStatus:<id>:<status>` continues to observe those two canonical flags.

The live hook contract is deliberately the existing top-level schema:
`acceptHook` and `completeHook` are inline command lists on a quest record. When
present, each **replaces** its corresponding `quest.offer` or `quest.complete`
default; there is no nested hook schema and no dual read. Completion behavior
uses the shared `QUEST_TAKE_REQUIREMENTS` and `QUEST_GRANT_REWARDS` primitives.
A failed requirement stops rewards and leaves the quest active; a successful
completion consumes/grants once, clears active, and marks completed. Repeating
completion is idempotent, so neither an authored graph loop nor a second caller
can grant rewards twice. The editor and validator expose and validate these
same two top-level fields.

Editor themes apply the same ownership rule to tooling: theme definitions are
editor-owned data under `tools/editor/`, not game runtime content. Shared theme
definitions may be committed; the active editor preference is local to the
authoring environment. The Studio surface maps stable theme tokens onto root CSS
variables instead of letting each editor panel grow its own palette constants.

### 6.4 Polygonal renderer and Effekseer boundaries (30.07.2026)

The move to polygonal world rendering is a **presentation change**, not a change
to the game's world ontology. Maps remain a 2D cell grid, movement remains
tile-locked/cardinal, and event/collision/save semantics do not acquire analog
3D state simply because the camera can draw real geometry.

The low-resolution framebuffer remains deliberate art direction. Polygonal
silhouette and normals should enter the same low-resolution visual register as
the authored pixel art rather than becoming a native-resolution layer floating
above it. Geometry is spent selectively: procedural surfaces remain the cheap
structural bulk, while doors, arches, openings, pillars, altars and similar kit
pieces may use models when silhouette or depth earns the cost. Those models stay
inside the same tileset/variant vocabulary rather than forming a second map
object system.

Effekseer replaces the **emitted-particle/effect** part of animation, not every
presentation track. Tint, gradient mapping, battler blend/transform,
choreography, screen shake and screen flash remain engine presentation concerns.
Effekseer assets run from the deterministic game/preview clock. World fixtures
and weather use world projection/depth; battle effects use screen-space
projection; the roles must be isolated by render-pass ownership rather than by
suppressing an entire later draw pass.

Full skeletal 3D creatures are deliberately deferred: a growing monster roster
would convert the renderer question into a large rigged-animation production
commitment and would pull motion away from the hand-authored 2D aesthetic. A
small number of rigid-jointed PS1-style townsfolk remains an exploratory option,
not a mandate to convert the roster. Likewise, free camera, Z-level navigation,
or leaving LOVE are engine/game-design decisions and must not enter through a
renderer refactor.

### 6.5 Sky anchoring across render surfaces (09.08.2026)

Sky art is authored against the canonical 256x240 composition and has no
vertical headroom. An expanded render surface must therefore never rescale the
sky to fill itself. The horizon — the source image's bottom edge — is anchored
at canonical composition `y = backdropH`, and whatever the surface reveals
outside that crop is filled by extension: horizontally the panorama repeats and
scrolls with the camera, vertically it extends its top row and **does not
repeat**. A vertical wrap would put the baked horizon back above the player's
head at the seam.

`viewport_3d.skyAnchor` owns that arithmetic for both the authored panorama and
the atlas sky-tile fallback, so the two cannot disagree. Both scale and horizon
are properties of the composition, not of the render target; a profile with a
non-zero `compositionOriginY` — `mobile_portrait` is the shipping one — moves
the horizon in render space while leaving it fixed in canonical space. The
parallax panorama layers are the deliberate exception: they scroll and loop on
both axes and set their own wrap mode.

### 6.6 Export staging boundary (09.08.2026)

`tools/export/runtime-manifest.json` is the authoritative allowlist for a
shippable game archive. `node tools/export/export-game.js` first runs the
engine's own `lovec . validate` preflight for the selected campaign, then stages
only the declared runtime roots, assets, runtime data helpers, and that
campaign's JSON into `dist/stage/`. It never copies the editor, test suites,
golden fixtures, generator tooling, or repository metadata. The packer creates
`dist/Second Rite.love` from that staged root and uses the release-only
`tools/export/release-conf.lua`, keeping development console settings out of a
distributed archive.

An alternate campaign is validated from `campaigns/<name>/` and then materialized
as the exported archive's single `data/` root. The runtime therefore does not
need campaign selection tooling or a checkout-relative `campaign.json` pointer
to boot the export. Windows fused executables, dependency copying, and their
smoke test are a later extension of this same staging boundary; they must consume
the staged archive rather than independently collecting source files.

For the initial Windows x64 target, the platform adapter fuses that archive
onto the configured `love.exe`, copies a small declared runtime-sidecar set,
puts the LÖVE license and notices in the player directory, and emits a ZIP of
that directory. If the staged animation data uses Effekseer, the shim is a
mandatory sidecar and export fails before archive packaging when it is absent.
The fused executable is then launched with `validate` from the player directory
as the hermetic smoke test. The release adapter must never compensate for a
missing DLL by relying on source-tree files or the runtime's development-only
degradation path.

The Developer Studio's **File → Export Game…** is one frontend for that CLI, not
a second implementation of it. `server.js` only reports preflight and spawns
`export-game.js`, exactly as it does for the campaign generator, and the dialog
relays the exporter's own log. The destination is always the project's own
`dist/`: the endpoint takes no output path, so a browser request can never
choose where the filesystem is written. Preflight answers what can be answered
instantly — campaign root, manifest sources, configured LÖVE runtime, and the
Effekseer shim where the target is one that carries it — while authored-data
validation stays the exporter's own first step rather than being paid for twice.
Unsaved authored edits are the one check the server cannot make, since the
exporter only ever sees what is on disk; the dialog raises it from the editor's
own dirty state and blocks export until it is resolved.

`tools/export/build-metadata.json` owns the few strings the exporter itself
owns — what the player-facing artifacts are *called*. It deliberately does not
own the window title: `conf.lua` already does, and build metadata must not
become a second place to change the game's name in. Every artifact name derives
from it, so no packager hardcodes a product name of its own.

Release preflight verifies the Effekseer shim by reading the DLL's PE export
table and comparing it against the symbols parsed out of
`presentation/effekseer.lua`'s own `ffi.cdef` — the same declaration the runtime
resolves at boot, rather than a copied list that can fall behind. Existence is
not currency: a stale shim loads, initialises, and dies later at the first call
to a symbol it never exported, which is precisely the failure the runtime
already refuses to defer, so the exporter refuses it too.

Every packaging run writes `build-manifest.json` beside the distributable:
product, version, target, campaign, LÖVE runtime, timestamp, staged file count,
source commit and whether the tree was dirty. It answers "which build was that?"
for a ZIP that has travelled to a tester. Unavailable git metadata is reported
as unknown rather than failing the build — an export from a source drop is still
a valid export — and the manifest carries no absolute paths, environment, or
machine identity, which is asserted by test rather than left to reviewer care.
