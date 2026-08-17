# Issue #547 — live assembled Tileset specimen experiment

> **Experimental / disposable branch:** `exp/tileset-live-specimen`
>
> This is interaction evidence, not a production Tileset Studio decision. Do not merge it merely because it runs.

## Thesis

The author-facing Tileset remains a recognizable environmental visual vocabulary, but the primary trustworthy editing surface is a deterministic **resolved assembled environment** rather than an atlas or a schema/list/form.

The experiment keeps current runtime truth intact:

- Tileset data remains authored in the existing schema;
- Surface/image/model references remain the authored sources;
- weighted base roles and feature placement remain current semantics;
- the existing Tileset resolver remains authoritative;
- the existing `viewport_3d` / renderable-bundle path remains authoritative for assembled presentation;
- the specimen Map is a transient preview request only and introduces no Map schema.

The editor does **not** compile a parallel environment in JavaScript.

## Run it

From a checkout:

```powershell
git fetch origin
git switch exp/tileset-live-specimen
npm ci
npm start
```

`npm start` runs the repository's existing `prestart` Three.js vendor sync. The normal Windows LÖVE default remains `C:\Program Files\LOVE\love.exe`; if LÖVE is somewhere else, set `LOVE_PATH` before starting Studio.

On Linux, point `LOVE_PATH` at the installed `love` executable when it is not already discoverable by the host.

In Studio, open **Tileset Studio** from the `🏰` toolbar/database entry, or use the Map Tileset `🎨 Edit` affordance.

The experiment is also a native Tileset Studio surface; no special prototype URL is required.

## Interaction model

The window is intentionally organized around three things:

1. **Environmental vocabulary** — compact roles at left: Wall, Floor, Ceiling, Opening / Door, Wall Feature, Floor Feature, Wall Top.
2. **Live specimen** — the large central 3D assembled environment, produced by the real runtime path from the unsaved Tileset working copy.
3. **Semantic owner / Inspector / source browser** — contextual authoring at right.

Primary intended loop:

`click visible assembled surface → see runtime semantic owner/cell → select authored variant → change source/weight/property → runtime specimen resolves again`

The atlas is therefore a **source browser**. It does not define semantic identity. Model-backed sources use the Model source tab/list where the current schema supports a model path.

## Deterministic specimen

The transient specimen uses a fixed authored layout containing:

- boundary and interior straight walls;
- inside/outside corner opportunities;
- floor and solid ceiling;
- an authored opening;
- wall/floor feature placement opportunities;
- enough structure to expose wall-top/relief behavior when the selected Tileset supplies it.

A seed control provides previous/next/cycle operations. The same Tileset working copy + seed is sent to the real runtime resolver again, rather than replaying a browser-side approximation.

The stock `dungeon_default` evidence resolved to **75,612 triangles** in the authoritative runtime bundle. Its visible vocabulary in the gauntlet was 1 wall base, 1 floor base, 1 ceiling base, 1 door, 1 wall feature, and 3 floor features.

## Runtime authority seam

The existing localhost renderable bridge now accepts an optional **transient Tileset snapshot** alongside its already-supported transient Map snapshot.

For one preview request only:

1. the host stages the existing Project runtime exactly as the normal renderable bridge already does;
2. `presentation/editor_renderable_bridge.lua` temporarily substitutes the unsaved Map and Tileset in the already-loaded Project data;
3. the normal `exploration.loadMap` path runs;
4. current Tileset resolution and `viewport_3d` presentation run;
5. `map_renderable_bundle` returns the actual compiled surface/material/light/relief bundle;
6. both transient substitutions are restored without saving authored data.

This keeps the browser from growing a second Tileset resolver/compiler.

The returned surface provenance already identifies runtime cells and semantic surface roles. A specimen click therefore selects ownership from runtime provenance. The current bundle does **not** expose the exact selected base weighted-variant ID for every baked wall/floor surface; the prototype is exact about semantic role/cell ownership, while exact authored variant selection remains explicit in the Inspector.

## Gauntlet evidence

Successful workflow run: **Tileset live specimen evidence #8**, run `31996303377`, commit `6f2070fa690f3d2cf44e15089b54cc68787b9a07`.

Artifact: `tileset-live-specimen-evidence` (`9277011879`). It contains:

- `00-surface-open.png`
- `01-live-specimen-selection.png`
- `02-weighted-wall-source-browser.png`
- `03-warm-model-feature-exact-predicate.png`
- `04-switched-tileset.png`
- `00-open-state.json`
- `gauntlet-evidence.json`

The workflow is intentionally **manual-only** after obtaining the evidence. In GitHub Actions, choose **Tileset live specimen evidence**, select `exp/tileset-live-specimen`, and run it. Headless CI uses Xvfb/Mesa for LÖVE and Electron SwiftShader for the capture host; product code is unchanged by those headless accommodations. CI bounds the seed sweep because repeated full LÖVE launches are intentionally expensive under software rendering.

### Same #547 gauntlet

| Task | Result / interaction evidence |
|---|---|
| Understand unfamiliar Tileset | The assembled vocabulary is visible before touching sources. Role counts are a fallback overview rather than the main canvas. |
| Replace base wall | Select/click Wall, choose its authored variant, then click an image source cell. The unsaved working copy is re-resolved through LÖVE immediately. |
| Add weighted wall variants | `+ Add` creates a real base-wall variant; weight is edited contextually. Evidence added `wall_2` with weight `35` and a distinct atlas source. |
| Floor / ceiling | Both are first-class vocabulary roles; Floor exposes current `heightOffset` relief and both re-resolve the assembled specimen. |
| Door / opening | Opening / Door is a direct semantic role backed by the current door pool; the fixed specimen contains an opening to judge in context. |
| Feature | Wall/Floor Feature roles expose their authored Surface/model source and placement properties. |
| Warm emitted light | Existing model-backed `wall_torch` was edited to `#ff9a40`, radius `5.5`, falloff `3`; the runtime specimen was re-resolved, not recolored by a fake browser preview. |
| Placement rule / probability | `injectProbability` is contextual; evidence changed the wall fixture to `0.41`. Existing fixture prefabs remain selectable. |
| Advanced exact predicate | The expert escape hatch edits the current predicate object. Evidence authored `{ all: [{ adjacent: "floor" }, { not: { adjacent: "opening" } }] }`. |
| Assembled corner / opening / feature | All are judged together in the central resolved room rather than in isolated atlas cells. Runtime-click evidence selected `Wall` at cell `9,8`, whose compiled components included wall-top, north-wall and south-wall. |
| Save / discard / switch | Save succeeded; an unsaved name probe was discarded back to the saved baseline; switching to `autotile_guide` rebuilt the specimen successfully (372 triangles). |

Determinism evidence: resolving the same seed twice produced the same wall signature. The bounded headless sweep through seed `547004` stayed renderable; it happened to produce one wall signature in that small sweep. The product UI does not artificially promise that every adjacent seed must pick a different weighted variant.

The successful run recorded **zero page/console diagnostics**.

## Qualitative findings

### Source-file / JSON exposure

**Lower for ordinary work than current main.** Wall/floor/ceiling/door, weights, probability, relief, model source, light color/radius/falloff, and movement blocking are contextual controls. The atlas is only exposed when a source is being chosen.

The deliberate exception is the **advanced exact predicate**: expert predicate JSON remains visible because the current predicate vocabulary is already precise and compositional, and hiding it behind another incomplete form would reduce exactness. Model paths are also visible as current authored source identity.

### Time to trustworthy feedback

**Trust is much higher; latency is worse.** Feedback is trustworthy because every material/source/property mutation asks the real LÖVE runtime to assemble the transient specimen. The status overlay explicitly distinguishes `REAL RUNTIME` resolution.

The cost is architectural: the current bridge launches a short-lived LÖVE authority process for a renderable request. Under software-rendered CI this becomes conspicuously slow, and even on normal hardware it cannot feel as instantaneous as current main's small 2D composite tile preview. A production version should address transport/session latency without moving resolution into JavaScript.

### Does selection ownership make sense?

**Mostly yes, with one important boundary.** Clicking the specimen gives a runtime cell and semantic surface role from authoritative provenance, which is a much stronger ownership story than clicking a source atlas first.

The bundle currently does not name every weighted base variant that produced baked wall/floor geometry. Consequently the prototype can truthfully say “this is Wall at runtime cell X,Y” and then let the author choose/edit the Wall pool variant; it should not pretend it knows an exact resolved base variant ID when provenance does not provide one.

### Can the author infer how the environment works?

**Much better than current main for assembled structure.** Straight walls, corners, opening, floor, ceiling, fixtures, model-backed surfaces, relief, and emission coexist in one stable room. Weighted changes can be cycled with seed instead of remaining abstract list weights.

The fixed neutral specimen is not a universal Map. Map-specific zone predicates or content that only makes sense in a particular authored level may still need a real Map context; this experiment deliberately does not expand Map schema to solve that.

### Expert exactness

**Preserved.** Exact weights, probabilities, predicate objects, source/model paths, relief, and emission parameters remain authored values in the existing schema. The live view is an interaction/presentation layer over them, not a simplified replacement ontology.

## Better than CURRENT main

- The **assembled environment** is the primary object of trust instead of a selected-entry 2D tile composite.
- A visible surface can lead back to its runtime semantic owner/cell.
- Atlas coordinates are demoted from mental model to contextual image-source selection.
- Weighted pools are judgeable in an assembled room under deterministic seed control.
- Current wall/floor/ceiling/opening/features, OBJ-backed fixtures, relief and emitted light can be judged together.
- The same unsaved working copy used by Save/Discard is what the runtime preview resolves.
- Ordinary editing exposes much less schema/file machinery while keeping exact expert values reachable.

## Worse than CURRENT main / unresolved

- **Feedback latency:** real authority calls are process-bound today; current main's isolated 2D preview is cheaper and more immediate even though it is less trustworthy.
- **Dense bulk editing:** current main's list/form presentation can expose many records at once; this prototype intentionally trades that density for spatial/contextual editing.
- **Exact resolved weighted-variant provenance:** runtime surface provenance identifies semantic owner/cell but not every exact baked base variant ID.
- **Predicate learnability:** exact predicate JSON is powerful but still expert-facing. A production design could add helpers without removing the exact representation.
- **Specimen coverage:** a fixed neutral room cannot prove every zone-dependent or Map-specific feature rule.
- **Source browser roughness:** the wall image picker follows the current wall atlas/edge convention and the model browser is intentionally simple. This branch is not a packing/source-management redesign.
- **Prototype code shape:** the branch replaces the existing Tileset Studio module wholesale for independent interaction evidence; it is not presented as production architecture.

## Files changed by the experiment

- `tools/editor/js/tileset-editor.js` — branch-only live specimen interaction surface.
- `tools/editor/runtime-bridge-server.js` — accepts/validates optional transient Tileset snapshots.
- `presentation/editor_renderable_bridge.lua` — temporarily overlays that snapshot while running the existing runtime assembly path.
- `tools/editor/capture-tileset-live-specimen.js` — explicit interaction/evidence gauntlet.
- `.github/workflows/tileset-live-specimen-evidence.yml` — opt-in headless capture workflow.

No runtime Tileset resolver/compiler semantics, Map schema, or Second Gate-specific neutral Studio vocabulary were added.
