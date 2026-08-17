# Experiment C — Map-contextual tileset authoring (#547)

**Branch:** `exp/tileset-map-context`, branched from `main` `084b881dc17a813a5512df9c22706cba5811b6d2`.

**Status: DISPOSABLE PROTOTYPE. This is not a merge request and not a winner
claim.** It was built without reading the interaction design of
`exp/tileset-atlas-workbench` or `exp/tileset-live-specimen`, so its evidence is
independent. The owner should compare all three before ratifying anything.

---

## Interaction hypothesis

> The author should not have to imagine what a Tileset does in a fake isolated
> context. The most trustworthy specimen is **the real Map already using it**.

So the loop is:

```text
click a visible wall/floor/door/fixture in the Map
  -> the surface names the semantic owner that produced it (role + variant)
  -> edit that owner in place, with the Map still on screen
  -> the editor marks provisionally what the edit owns, immediately
  -> the authoritative runtime corrects the picture asynchronously
```

Tileset Studio is not redesigned here. Instead the Map workspace grows a
contextual **Environment** panel that is simultaneously a semantic library (the
palette board), a contextual Inspector, a source picker and a weighted-variant
editor — while the Map keeps spatial meaning.

## How to run it

The experiment is **off by default**, so committed editor canon renders exactly
as it does on `main`.

1. `npm ci --ignore-scripts && node tools/editor/sync-three-vendor.js`
2. Start Studio normally (`npm start`), or for a browser host:
   `node tools/editor/server.js` plus `node tools/editor/runtime-bridge-server.js`
   (the second process is the authoritative renderable path; without it the Map
   has no runtime geometry and nothing can be traced).
3. Open the editor with `?exp=tileset-map-context` — this persists the opt-in
   flag. `?exp=off` clears it. In Electron, set
   `localStorage.thestraExpTilesetMapContext = '1'` and reload.
4. The Map workspace toolbar grows an **Environment** button. `Floor 1: Entry
   Hall` on `dungeon_default` is the useful fixture: it has walls, floors, an
   opening and fixtures.

Re-run the recorded gauntlet with:

```bash
node tools/editor/capture-tileset-map-context-experiment.js
```

> That driver **saves authored tileset data** as part of gauntlet 13. Run
> `git checkout -- data/` afterwards. Note that saving one record rewrites the
> whole `data/tilesets/` registry directory, so the diff is wider than the edit.

Focused harness (12/12 passing), including negative controls asserting the
prototype contains no second variant resolver and no authored-object transport:

```bash
node --test tools/editor/test-tileset-map-context-experiment.js
```

---

## What is runtime-truthful vs faked

This is the most important table in this document.

| Behaviour | Source of truth |
|---|---|
| Which variant a cell resolved to | **Runtime.** `source.variantId` on the authoritative Map Renderable Bundle |
| Which Tileset a Map resolved to | **Runtime.** new `bundle.tileset` identity block |
| Realized variant distribution ("chose it in N of M cells here") | **Runtime.** census counted off the compiled bundle |
| Wall join halves actually active on the clicked face | **Runtime.** `leftJoin` / `rightJoin` provenance |
| Fixture identity on a surface | **Runtime.** `source.featureId` |
| Visible geometry, lighting, relief, packing | **Runtime.** bundle unchanged |
| Which variants exist, weights, rules, emission | **Authored.** re-read from `/api/tilesets` |
| Authored share of a pool | Derived arithmetic over authored weights only |
| Variant thumbnails | **Editor approximation.** a 2D crop of the source PNG at the variant's region — the right pixels, but not the runtime's shading, relief or join composition |
| Provisional marking after an edit | **Explicitly editor-owned.** an additive magenta overlay, never a repaint of the bundle |
| Effect of an edit on the real picture | **Runtime only.** the prototype never re-textures the Map itself |

**Nothing was faked to make a task look easy.** The prototype refuses to
simulate a weighted draw, refuses to pack an atlas, and refuses to claim an
owner when provenance does not name one. A guarded assertion in the harness
fails if `cellHash`, `Math.random`, `resolveWeightedVariant` or the runtime salt
constants ever appear in the prototype.

---

## Gauntlet results

Measured on `Floor 1: Entry Hall` (`dungeon_default`), 1500x940 viewport,
authoritative renderable bridge live. Frames in
`issue-547-map-context-capture/`, machine-readable log in `capture-report.json`.

| # | Task | Result | Evidence |
|---|---|---|---|
| 1 | Open an unfamiliar Map and understand its wall/floor/ceiling vocabulary | **Yes.** The palette board names every job (WALL 1, WALL TOP 0, FLOOR 1, CEILING 1, DOOR 1, WALL FIXTURE 1, FLOOR FIXTURE 3) with a thumbnail, authored weight, pool share, and **how many cells of this Map actually use it** | `01-vocabulary-of-this-place.png` |
| 2 | Click a visible wall and reach its semantic owner | **Yes.** A wall face at cell 15,16 reported `Wall face (south side)` -> job `Wall` -> owner `dungeon_wall_1`, and tinted all 113 cells that variant owns | `02-clicked-wall-reaches-owner.png` |
| 3 | Replace its Surface without typing coordinates | **Yes.** `Replace this look…` opens the source image; one click assigns. `rawCoordinateUses = 0` | `03`, `04` |
| 4 | Add second/third weighted variants | **Yes.** Two more wall variants added and assigned by pointing; weight authored with a slider (`dungeon_wall_1=100 dungeon_default_wall=35 dungeon_default_wall_2=100`) | `05-weighted-variants-authored-and-realized.png` |
| 5 | Inspect deterministic variant choices | **Yes — the strongest result.** Authored 43% / 15% / 43% shown beside the engine's realized census. Before the save: `113 of 113` cells still on the old variant. After the authoritative correction: `55 / 10 / 43 of 108`. No weighted draw is simulated; the census is counted off the compiled bundle | `05`, `13` |
| 6 | Author floor / ceiling | **Partly by clicking.** Floor: clicked cell 15,13 -> `dungeon_floor_1`. Ceiling: **not clickable** from an interior camera in the `authoring` geometry profile; reached from the palette board instead | `06`, `07` |
| 7 | Author a door / opening | **No, not by clicking.** This Map exposes exactly one opening surface and a wall face always won the raycast at its projected position. Reached from the palette board instead | `08-opening-owner.png` |
| 8 | Select a visible fixture and edit its Surface/model | **Yes.** A wall torch reported `Wall face (east side) · fixture` -> job `Wall fixture` -> owner `wall_torch`; the fixture wins over the wall it stands on | `09-fixture-behaviour-editor.png` |
| 9 | Add emission/light and see it in context | **Authored, not seen immediately.** `Warm emission` authors colour/radius/falloff. Emitted light is generated per *placed* fixture by the runtime, so it appears only with the authoritative correction — the panel says so rather than faking a glow | `10-emission-and-placement-rule.png` |
| 10 | Edit placement probability/rule without raw JSON | **Yes.** Chance 33% -> 40% on a slider; rule changed from `Prefab rule: wall_beside_floor` to `Beside open floor`. `rawJsonUses = 0` | `10` |
| 11 | Reach exact predicate representation as an advanced path | **Yes.** The Advanced box showed the real persisted record including `"where": { "adjacent": "floor" }`, editable and re-appliable | `11-advanced-exact-record.png` |
| 12 | Inspect structural/height/relief behaviour | **Yes, as a report.** `Main face assigned`, `Join halves left + right`, `This face: flat run, no joins here` (runtime provenance), `Relief: height map, wall scale 0.12`. The prototype reports relief; it does not author height maps | `12-structure-and-relief.png` |
| 13 | Save / discard / switch without stale cross-window state | **Yes.** Dirty `true -> false` across an awaited save; the record travels with its `_storageVersion` so a stale write is refused; switching Map with unsaved work prompts before following the Map | `13` |
| 14 | Open another Map using the same Tileset and understand committed refresh | **Yes for the palette, no for the picture.** On `Floor 2: Chasm Crossing` the palette correctly showed the committed edit (`w35 · 15%`, `dungeon_default_wall_2 · 43 here`) re-read from the Project authority. The Map picture could **not** be compiled — see the 64 MiB finding — and the panel said so in red instead of pretending | `14`, `15` |
| 15 | Distinguish provisional feedback from authoritative correction | **Yes, and it was exercised for real.** Magenta additive overlay plus `PROVISIONAL — runtime has not corrected them yet`; then `Authoritative runtime geometry applied (6818 ms)`; and on the failing second Map, `RUNTIME CORRECTION FAILED — the Map is showing STALE geometry` | `04`, `13`, `14` |

---

## Measurements

**Mode/context changes.** The human path for "click a wall, retexture it, add two
weighted variants, save" is **4** context changes: open the Environment panel ->
click the wall (the selection *is* the mode change) -> enter source-pick ->
return. Each further variant costs 1 more (it drops straight into source-pick).
Reaching a role that is not clickable from the current camera costs 1 extra
(open the palette board). There is **no separate window, no modal, and no tab
switch**; the Map never leaves the screen. The instrumented counter reported 30
for the whole automated run because it counts every probe click the driver made,
including misses — that is not the human figure.

**Raw coordinates typed: 0.** Every visual assignment was made by pointing at a
source region. The persisted `middle` / `leftEdge` / `rightEdge` triple is
derived, and the panel talks about `Main face` and `Join halves`.

**Raw JSON required: 0** for every common path in the gauntlet, including
placement rules, chance and emission. The Advanced box was *read* for task 11 to
prove the exact predicate stays reachable; nothing in tasks 1-10 or 12-15 needed
it.

**Latency, edit to useful visual feedback.**

| Feedback | Measured |
|---|---|
| Provisional marking of the surfaces an edit owns | same frame, no await — a local overlay |
| Panel numbers (authored share, pool membership, structure) | same frame |
| **Authoritative corrected picture** | **6818 ms** measured in-page (save -> new bundle installed); 8466 ms wall clock including the save round-trip. Map 2, 17x17, cold LÖVE subprocess |

That 6.8 s is the existing cold-LÖVE authoritative path from #487, not something
this prototype added. The prototype's contribution is that the 6.8 s is spent
*with the answer already visible provisionally*, and that the arrival of the
authoritative version is announced and timed rather than silent.

---

## Where Map context clearly helped

1. **"Which of my variants is actually used, and where?"** The isolated editor
   cannot answer this at all. Map context answers it exactly: authored share
   beside engine-realized cell counts. `authored 15% of the pool · runtime chose
   it in 10 of 108 cells here` makes weights concrete in a way no preview can.
2. **Reaching the owner of something you can see.** "That wall looks wrong" ->
   click it -> the owning variant is named and selected. No searching a list by
   id, no guessing which of three wall entries produced that face.
3. **Discovering what a Map's environment is made of.** The palette board reads
   as a place's vocabulary, and the per-variant "N here" instantly separates what
   matters in this Map from what is merely authored.
4. **Catching authored facts only a real Map reveals.** `WALL TOP · 0 — nothing
   authored for this job yet`, and a clicked wall top reporting `owner: not
   identified`, exposed that `dungeon_default` never authored a wall top and the
   runtime substitutes a legacy grey material. An isolated specimen would have
   drawn *a* wall top and hidden this.
5. **Fixtures.** A fixture's whole authored behaviour is *where it lands and how
   often*. Editing chance and rule while looking at the 18 places it actually
   landed is qualitatively better than editing a probability field in a form.

## Where Map context made Tileset editing worse

1. **Not everything visible is clickable, and not everything authorable is
   visible.** Ceilings are absent from the interior `authoring` profile;
   openings existed but a wall face won the raycast every time; wall tops are
   only visible from above. Map context therefore **cannot be the only entry
   point** — the palette board had to carry tasks 6 and 7. This is direct
   evidence for the owner's instinct that a Map-only model is both too unfamiliar
   and insufficient.
2. **A brand-new variant has no context yet.** The moment you add a variant it
   owns zero surfaces, so the Map has nothing to show, and the strongest feature
   of this approach goes quiet exactly when you are creating something. Until the
   6.8 s correction lands, a new variant is as abstract here as in a form.
3. **Bulk work is bad.** Setting up an environment from scratch means clicking
   `+ Variant` repeatedly with nothing to click on. A sheet-oriented overview is
   plainly better for that, matching the owner's "familiar palette board for bulk
   setup" direction.
4. **The panel is cramped.** A 328 px contextual panel forced the palette board
   into a one-card-per-row strip. The palette board wants real width; it does not
   belong inside a contextual Inspector.
5. **The panel overlaps the thing it is about.** Floating over the viewport, it
   covers roughly a fifth of the Map, sometimes including the surface just
   clicked. Docking it properly is a layout problem this prototype did not solve.
6. **Selection is ambiguous where surfaces stack.** A cell can emit a floor quad,
   a height mesh, a wall top and four faces. Clicking picks the nearest, often
   not the one meant. The automated driver needed up to 24 verified attempts to
   reach a specific role; a human would feel that as "I keep selecting the wrong
   thing".

---

## Findings that are about the engine, not the prototype

Each was confirmed with the engine files reverted to `main`.

1. **The authoritative renderable channel has a hard payload ceiling and reports
   it as a runtime refusal.** `runtime-bridge-server.js` gives `execFile` a
   64 MiB `maxBuffer`, and the bundle is JSON on stdout. `Floor 2: Chasm
   Crossing` (23x23) produces **81,023,277 bytes (77 MiB)** and therefore
   *cannot be corrected at all*. The user-visible message is `LÖVE did not
   return a renderable bundle`, which reads as an engine failure rather than a
   transport limit. Direct LÖVE succeeds for the same Map, which is how the
   ceiling was isolated. Adding a single `wallTops` variant to `dungeon_default`
   pushes even the 17x17 `Entry Hall` over the same line. Reproduce by starting
   `node tools/editor/runtime-bridge-server.js` and POSTing `data/maps/3.json`
   to `http://127.0.0.1:8082/api/map-renderable`.

2. **`dungeon_default`'s wall authors no `leftEdge` / `rightEdge`.** The autotile
   join vocabulary exists in some tilesets (`stillnight_bellroot_vigil`) and is
   simply absent in the default one, where the runtime falls back to a legacy
   row/column path. A Map-context reading honestly reports `This face: flat run,
   no joins here`.

3. **`dungeon_default` authors no `wallTops` at all**, and the runtime silently
   substitutes a flat grey structural material. Nothing in the current editor
   surfaces that.

4. **A doorway face's provenance names the wall it was cut into.** Found because
   the realized census attributed 3 of 4 door-role surfaces to `dungeon_wall_1`.
   The bundle carries both facts (`variantId` = the wall, `doorVariantId` = the
   door), so this was a consumer bug in the prototype — now fixed and
   regression-tested — but any future consumer will hit the same trap.

5. **Saving one tileset record rewrites the whole `data/tilesets/` registry
   directory.** A one-variant edit produces a 14-file diff.

6. **G6 is red on this machine on 9 frames, none of them caused by this branch,
   and `database/units.png` is nondeterministic.** Established by one-variable
   runs rather than assumption:

   | Tree | `database/units.png` | other 8 frames |
   |---|---|---|
   | clean `main`, runs 1 and 2 | matched | MISMATCH |
   | this branch, 3 runs | MISMATCH | MISMATCH |
   | this branch with the experiment not even loaded | MISMATCH | MISMATCH |
   | this branch with both shared editor files reverted | MISMATCH | MISMATCH |
   | **editor tree byte-identical to `main`** (only `presentation/*.lua` differ, which the editor never executes) | **MISMATCH** | MISMATCH |

   The pixel diff is 384 pixels in one 44x38 region: the animated **Small
   Battler** sprite preview is mid-animation in the reference and blank in the
   actual. It is an animation-phase sample, and it began failing partway through
   the session on an unmodified editor tree. This is the #253/#259 class of live
   editor nondeterminism and belongs in its own issue. **No golden was
   recaptured.**

   Chasing this did produce one genuine improvement: the experiment's two script
   loads were originally appended unconditionally to the Map bootstrap chain.
   They are now fetched **only when the opt-in flag is set**, so a disabled
   experiment cannot perturb boot timing at all, and the harness asserts it.

---

## Implementation debt

**Changes outside the disposable prototype files** — small, and the honest cost
of this approach:

- `presentation/viewport_3d.lua` — resolved wall faces carry `variantId`,
  `featureId`, `doorVariantId`, `doorFace`, `leftJoin`, `rightJoin`. Facts only;
  no renderer behaviour reads them; derived from the same inputs as the rest of
  the cached face.
- `presentation/map_renderable_bundle.lua` — those facts reach each surface's
  semantic `source`; floor/ceiling/wall-top/opening sources gained `variantId`;
  the bundle gained a `tileset` identity block. **This is the load-bearing
  change.** Without resolved variant identity in the bundle, Map-context
  authoring is impossible without building a second resolver, which #547 forbids.
  Any winning prototype that wants Map traceability needs this.
- `tools/editor/js/three-editor-viewport-base.js` — provenance rides on the
  runtime meshes; `pickRenderableProvenance` (a click also reports the nearest
  *authoritative* surface, because invisible semantic proxies otherwise win the
  raycast); `setProvisionalOverlay`; `renderableProvenance`;
  `screenPositionsForProvenance` (capture affordance).
- `tools/editor/js/thestra-editor-workspace.js` — a declared read membrane
  (`ThestraMapWorkspaceContext`) plus a `thestra-map-bundle-installed` event.

**Debt and shortcuts:**

- The panel is a floating `aside` positioned over the viewport instead of
  participating in the workspace layout, and it does not integrate with the #493
  Inspector — it sits beside it. A production version must decide whether this is
  Inspector content or its own region.
- Variant thumbnails are 2D crops of the source PNG: right pixels, wrong
  shading / relief / joins.
- No undo/redo. Discard restores the loaded revision wholesale.
- The panel uses `showToast`, which is a **modal** in this editor; using it for
  routine confirmations is wrong and it blocks the viewport.
- Per-variant source *images* are not authorable, because the persisted record
  has one top-level `texture` with per-variant regions inside it. The prototype
  refuses to fake a per-variant PNG the runtime cannot save. If #558/#666 give
  Surfaces their own identity, this picker is the natural place to bind it.
- `heightOffset`, `effect` / `effectHeight` / `effectMagnification`, `wallTops`
  authoring and fixture prefab-library editing are not exposed.
- The capture driver writes real authored data and needs `git checkout -- data/`
  afterwards.
- No G6 coverage. The experiment is deliberately behind an opt-in flag so
  committed editor canon is untouched, and **no golden was recaptured.**

---

## Worth stealing even if this prototype loses

1. **Resolved variant identity on the renderable bundle.** The highest-value idea
   here, and independent of any UI: once a visible surface can name the authored
   record that produced it, *every* prototype gets traceability, "where is this
   used", and a truthful census for free.
2. **Realized census beside authored weight.** `authored 15% of the pool ·
   runtime chose it in 10 of 108 cells here` is the honest answer to "compare
   weighted variants deterministically" — count the real map instead of
   re-rolling a fake one. Any winning design should show both numbers.
3. **Occupancy highlight on selection.** Selecting a variant tints every surface
   it owns: frame-local, engine-truthful, and it answers a question no form can.
4. **The provisional/authoritative boundary made visible and timed.** An additive
   overlay for "editor thinks", the real bundle for "runtime says", an explicit ms
   figure when the correction lands, and a red honest failure state when it does
   not. A reusable pattern for every #487 latency tier.
5. **Refusing to guess an owner.** `owner: not identified — the runtime resolved
   this surface without an authored variant id` produced three real findings. An
   editor that quietly showed a plausible variant would have hidden them.
6. **Human names in front of persisted names.** `Main face` / `Join halves`
   before `middle` / `leftEdge` / `rightEdge`; `Chance` before
   `injectProbability`; placement presets built over the *real* predicate
   vocabulary with the exact JSON one fold away.
7. **A machine-checkable truth boundary.** The harness fails if `cellHash`,
   `Math.random`, `resolveWeightedVariant` or the runtime salt constants appear in
   the prototype, and if a commit announcement ever carries the record. A cheap
   way to keep "no second compiler" from eroding.
8. **`data-exp` hooks on controls.** Driving a UI by semantic hook instead of
   index caught two real bugs that index-based automation had silently hidden.

---

## Recommendation (explicitly not a verdict)

The evidence supports a **narrower** claim than the prototype's own thesis:
Map context is excellent for *judging, tracing and adjusting* an environment that
already exists, and poor for *building* one. That matches the owner's later
direction — a familiar picture-first palette board as the primary surface, with
Map-contextual selection as an additional entry point into the same semantic
objects rather than the sole mental model.

The one thing here that should outlive the experiment regardless of which
interaction model wins is resolved variant provenance on the renderable bundle.
