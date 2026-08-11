# Editor 3D workspace spike — 2026-08-10

**Status:** findings recorded; approach not adopted
**Issues:** #277 (RFC), #279 / #280 (implementation), #286, #287, #289, #291
**Scope:** what the first 3D map-workspace attempt taught. Not a design decision, not an endorsement of the implementation.

## 1. Framing

The neutral-scene + Three.js map workspace (#277, implemented across #279/#280) is **one approach, deliberately not treated as canon.** It reached a usable state, was driven by hand against a real map, and produced findings worth more than the code.

This record exists so those findings survive the approach. Several alternative directions are expected before any map-editor rework is settled, and each should start from what is written here rather than rediscovering it.

Nothing below asserts that the 3D workspace should ship.

## 2. Findings that outlive the approach

These emerged from the spike but are **not properties of it**. Any map-editor rework inherits them, including one that keeps the 2D canvas.

### 2.1 The engine owns compiled geometry; the editor adapts it

The first implementation mirrored tileset merge rules in the browser and compiled its own approximation of runtime terrain. That was the wrong seam. It was corrected by #286 (split engine-neutral geometry from presentation mesh finalization) and #287 (expose an authoritative map renderable bundle over a local bridge).

The resulting split is the durable part:

- the **engine** resolves structure, compiled height geometry, material identity and provenance, once;
- the **editor** adapts that result into whatever its viewport needs;
- the browser never decides what the world looks like.

Any approach that recompiles world geometry in JavaScript will hit the same wall, and should not.

### 2.2 Selection must resolve to authored cells, never renderer identity

Picking must produce an authored coordinate — `{ kind = "cell", x, y, surface }` — and never leak mesh, node or draw-call identity into authored selection semantics.

This is the constraint whose violation would be **unrecoverable**, because renderer identity would end up embedded in authored data. It applies to a 2D canvas hit-test exactly as much as to a 3D raycast.

Verified working in the spike: clicking rendered geometry reported `Cell 7, 18` and reused the existing Map Layer inspector rather than introducing a parallel property system.

### 2.3 Geometry visibility is per-consumer, not global

**The most valuable finding.** Tracked as #291.

The compiler already performs visibility culling — it is simply implicit and hardcoded to the player's camera. Walls have no top face, because the player never sees one.

The consequence only became visible when a camera looked at a map from an angle the game never uses:

- **walls read as voids** from above — no top cap exists to see;
- **walkable cells are roofed over** — `presentation/map_renderable_bundle.lua` emits a ceiling quad at `z = 1` per walkable cell whenever `mapData.ceilingStyle ~= "sky"`.

So an overhead view of a roofed interior is close to unreadable, for two independent reasons at once.

The resolution is not a viewport toggle. The game and an authoring view want **different sets of faces**:

| | game profile | authoring profile |
|---|---|---|
| wall top caps | absent (never seen) | **present** (needed to read a map from above) |
| walkable-cell ceilings | present unless `ceilingStyle == "sky"` | **absent** (they occlude map contents) |
| map-exterior wall shell | absent | present |

Same neutral geometry description, two **finalization profiles**, answering one question — *which faces can this consumer ever see?* — against different cameras. #286's split is the natural home for that parameter.

Two consequences worth carrying forward:

- This makes the performance optimization and the editor-readability fix **the same feature**, rather than two features in tension.
- The symptom is **not uniform across maps**. Walls built from thick heightfields do read from above, because their side faces have volume; thin walls (St. Maria) render as blanks. That inconsistency makes it easy to misdiagnose as a rendering bug.

### 2.4 Ceiling occlusion and missing wall caps are facts about the data

Neither is an artifact of the chosen renderer. A different backend — or a 2D view drawing the same compiled surfaces — shows the same voids and the same roofs. Any approach must answer for them.

### 2.5 Editor camera and view state must never dirty authored data

Verified under real interaction: after driving both cameras and selecting cells, `git status -- data/` was completely clean.

This matters more here than in most editors, because the Studio live-writes form edits straight to `data/*.json`. The invariant is worth asserting explicitly in any future approach rather than assumed.

### 2.6 A vendored browser dependency surface needs a resolution test

#279 shipped a viewport that could not start: `sync-three-vendor.js` copied `three.module.js` without `three.core.js`, which it re-exports from since the Three build split. The entry point fetched `200` and then failed to instantiate.

Node-side validation could not see this — nothing in `node --check` or the semantic suites instantiates the browser module graph. The fix now walks every relative import of each copied module and fails if one does not resolve.

Generalizable: **any retained vendor surface should be tested by resolving the entry point's own imports**, not by asserting a file list.

## 3. Specific to this approach, and still open

Recorded so that alternatives are not judged in this approach's vocabulary:

- Three.js as the viewport backend.
- **Perspective and Top Orthographic as two discrete modes.** Owner feedback is that these should not be separate modes at all, but a single camera interpolating continuously between them — which is evidence the two-mode framing may have been wrong from the start rather than merely improvable.
- A front-view camera emulating the in-game viewpoint, which does not exist yet.
- Event cubes as the event representation. In their current form they are **less** informative than the 2D cells they replace: they carry neither the 2D editor's labels (`CE`, page counts) nor the event's actual graphic (3D model where one exists, billboard otherwise).
- Whether the 2D canvas is replaced at all, versus augmented.
- Whether the authoring view should be 3D-first, or 2D with 3D affordances.

## 4. Wins already on main

Independent of whether the viewport survives:

- **#286** — engine-neutral geometry split from presentation mesh finalization.
- **#287** — authoritative map renderable bundle, resolving structure, compiled geometry, **material identity** and provenance once, exposed over a local runtime bridge.

## 5. Wins not yet landed

- **#291** — hidden-face culling / per-consumer visibility profiles. Expected to remove a substantial fraction of wall side faces per map, and to compound with **#161** because a culled face is never generated, decimated, uploaded or drawn. #291 asks for a face-count before/after to replace estimates with a number.
- **OBJ material export.** `presentation/map_geometry_export.lua` is still geometry-only, but #287 means every surface now carries a resolved `material`. Writing `.mtl` is now a serializer over existing data rather than a second resolution path.
- **#290** — runtime bridge `EDITOR_PORT` fix, open at time of writing. Without it the bridge silently refuses the Studio origin and the viewport falls back to untextured proxies, which reads as "3D has no textures yet".

## 6. Method note for the next approach

Alternatives are cheap to produce and expensive to review; agent generation is nearly free, owner attention is not. Two or three alternatives against **fixed criteria** is useful; more is a way to avoid deciding.

Fix the comparison criteria before the alternatives exist — the incumbent otherwise wins on familiarity. Suggested, drawn from what this spike surfaced:

- can it read a roofed interior map at a glance?
- do event metadata and event graphics survive into the view?
- can every map-editing operation be performed in it — i.e. can the 2D canvas be deleted, or is it merely redundant?
- does selection resolve to authored cells?
- does it stay out of authored data?
- what does it cost to keep working when the engine's geometry changes?

The third is the owner's stated acceptance bar: the workspace cannot be fairly judged while 2D Edit remains a separate necessary mode.
