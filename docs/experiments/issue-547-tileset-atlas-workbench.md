# Issue #547 — Tileset Atlas Workbench experiment

Branch: `exp/tileset-atlas-workbench`

Status: **disposable interaction prototype**. This branch is evidence for owner comparison, not a merge recommendation.

## Run it

1. Check out `exp/tileset-atlas-workbench`.
2. Install dependencies as usual (`npm install` when needed).
3. Start Thestra Studio with `npm start` (or the normal Project-specific Studio command).
4. While Studio is running, open `http://127.0.0.1:8080/tileset-atlas-workbench.html` in a browser.
5. For a useful authored fixture, select `stillnight_bellroot_vigil` when working in the repository Project.

The workbench uses the existing Studio HTTP authority:
- `GET /api/tilesets`
- `POST /api/tilesets/save`
- the texture inventory returned by `/api/tilesets`
- `GET /data`
- `POST /api/map-inspection`

It does not add a Tileset compiler or change runtime Tileset resolution.

## Interaction thesis tested

The center of the tool is not a record list. It is the environment vocabulary:

**WALL / FLOOR / CEILING / DOOR / FEATURES**

Each assigned semantic variant is a visual card. Clicking a card selects the real authored record. “Replace visual” and “Add variant” enter a source-picking mode in the large atlas browser. Exact atlas coordinates remain inspectable but are not needed for ordinary assignment.

Walls expose **LEFT JOIN / MAIN FACE / RIGHT JOIN** as a visual structural relationship before showing the underlying `leftEdge`, `middle`, and `rightEdge` values.

Weighted roles display both authored weight and normalized share. Features expose placement chance and common placement rules without requiring predicate JSON. Exact `where` JSON remains in Advanced.

Warm emission authors the same existing light shape used by current Tilesets (`color`, `radius`, `falloff`), with the current Studio warm default `[1, 0.58, 0.22]`.

## Shared gauntlet

- [x] **1. Inspect unfamiliar Tileset.** Opening a Tileset immediately produces grouped visual cards and the source image.
- [x] **2. Replace wall Surface.** Select wall card → MAIN FACE (or a join) → click source tile.
- [x] **3. Add second + third weighted wall variant.** `+ Add variant` twice; select source tiles; edit weight in Inspector.
- [x] **4. Add floor/ceiling.** Each role has the same source-first Add flow.
- [x] **5. Author/inspect door.** Door is a first-class visual group with Add/Replace and exact Inspector values.
- [x] **6. Create/edit one feature.** FEATURES has Add, source replacement, semantic identity, role/model exact fields, probability, placement, and light.
- [x] **7. Assign warm emission/light when supported.** `Warm emission` authors the existing light object; `No light` removes it.
- [x] **8. Alter probability/placement rule without raw JSON.** Chance slider plus Anywhere/Beside floor/Beside wall presets.
- [x] **9. Inspect exact advanced predicate afterward.** Advanced exact values shows and can apply exact `where` JSON.
- [x] **10. See an assembled trustworthy result.** Trust View shows the exact authored selections without inventing resolution. `Runtime inspect a real Map` delegates to the existing LÖVE `/api/map-inspection` authority with seed `547` after save. It intentionally refuses to synthesize a speculative Map when no real Project Map advertises the selected Tileset.
- [x] **11. Save/discard/switch safely.** Save uses the existing versioned `/api/tilesets/save` path. Discard restores the baseline. Switching a dirty Tileset forces Save / Discard / Cancel decisions. Browser close also receives a dirty warning.

## What became dramatically easier

- **Orientation.** An unfamiliar Tileset reads as an environment kit rather than a JSON-backed database table.
- **Variant authoring.** The physical action is “pick this picture for WALL,” not “type an atlas coordinate into a field.”
- **Weights.** A value such as `60` becomes “60 weight · 60% of this pool” beside the visual it controls.
- **Wall structure.** The author can reason about main face and joins without learning `middle`, `leftEdge`, and `rightEdge` first.
- **Feature placement.** Common placement intent and probability are ordinary controls; predicate JSON moves to verification/escape-hatch status.
- **Light.** A warm emission can be attached as a meaningful visual-property action, while exact values remain inspectable.

## What remained awkward

### Standalone PNG Surface sources

The current Tileset records inspected on `main` still persist one top-level `texture` and per-variant atlas coordinates. The Studio endpoint inventories other PNGs, but a variant record has no observed per-variant source path to save.

The prototype therefore shows standalone PNG files beside the atlas, but **does not make them falsely assignable as per-variant sources**. Clicking a non-active PNG explains the limitation. If/when an authoritative Surface resource seam owns standalone source identity, this exact visual picker is the place to bind it; the prototype should not invent that seam.

### Trustworthy assembled visual preview

The browser can display exact assigned images, but it intentionally does not reimplement weighted selection, structural packing, or Map assembly. Runtime inspection is only offered against a real saved Map using the existing LÖVE bridge. This preserves truth, but is less immediate than the ideal “unsaved Tileset → authoritative live assembled room” loop.

A future production design needs an engine-owned transient Tileset-overlay preview seam (or another existing authoritative seam), not copied resolver logic in Studio.

### Structural profiles

The current authored fixture exposes the historic wall shape (`middle` / edge arrays). The visual LEFT JOIN / MAIN FACE / RIGHT JOIN affordance makes that survivable, but the workbench cannot expose richer named structural-profile relationships that are not present in the inspected persisted record.

## Schema knowledge still required

Ordinary work no longer requires coordinates or predicate JSON, but advanced authors still need to understand:

- semantic `id` stability;
- feature `role` when using unusual roles;
- model path when a feature is model-backed;
- arbitrary predicates beyond the common placement presets;
- exact edge offset values in the historic wall representation;
- that changes are authored data and runtime preview reflects saved authority.

That is an appropriate Inspector boundary; it should not be the default workflow.

## Ideas worth stealing even if this prototype loses

1. **Semantic groups as the primary canvas.** WALL/FLOOR/CEILING/DOOR/FEATURES communicate the environment vocabulary immediately.
2. **Assigned visuals are the selection surface.** No parallel row selection and preview selection.
3. **Add means enter visual source-picking mode.** The source browser is a verb target, not a passive image.
4. **Weights shown as authored number + pool share.** Preserve exactness and readability together.
5. **Friendly structural names first, exact schema second.**
6. **Common feature placement presets + exact predicate underneath.**
7. **Meaningful lighting actions (“Warm emission”) with exact numeric values still available.**
8. **Truth boundary is visible.** A UI should say when it is only showing authored selections and use the runtime bridge for resolved facts instead of quietly growing a second compiler.
9. **Dirty switching is part of interaction design.** It should be impossible to lose a vocabulary edit just because another Tileset was selected.

## Capture

`docs/experiments/issue-547-tileset-atlas-workbench-capture.svg` is a compact interaction capture of the implemented three-pane workbench using the Stillnight Bellroot Vigil fixture vocabulary. It is visual evidence of the interaction layout, not a claim that browser rendering is runtime resolution.
