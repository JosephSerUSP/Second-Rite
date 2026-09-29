# Blender tooling audit — map pipeline, Blender 5.2, Geometry Nodes (2026-09-28)

Scope: the Blender side of map/environment authoring (`tools/blender/`,
`tools/blender/recipes/`, the bake/export path, the live bridge), whether
Blender 5.2 LTS offers anything we should adopt, and whether Geometry Nodes
(GN) should take over procedural generation of houses, trees and ground cover,
which today is done in bpy-free Python and handed to Blender as finished mesh.

This is a report, not status. Where it says something is true of the code, it
names the file.

Note on sources: blender.org was unreachable from the audit environment, so the
5.2 facts below come from the release coverage linked at the end rather than
the release notes themselves. Where only a headline was available, this report
says so rather than guess at the detail.

## 1. What the pipeline is today

```
pure Python (no bpy)                      Blender                          runtime
-----------------------                   -------                          -------
house_grammar/recipe.py  ─┐
  → records.MeshRecord    ├─ emit_blender.py ─┐
tree_generator.py         │  (from_pydata)    │
  → tree_mesh.py         ─┤                   ├─ .blend (scaffold → SOURCE once
grass.py                 ─┘                   │   the owner adopts it)
  + terrain_surface.py (bpy raycast adapter) ─┘
                                              │
exterior.py / interior.py / furnishings.py ───┘  (bmesh/primitives in-scene)
                                              │
                   town_environment_pipeline.py: Cycles bake → OBJ + MTL + atlas PNG
                   export_room_environment.py / export_exterior_environment.py
                                                                  → LÖVE (never sees Blender)
```

The split is deliberate and documented in the module docstrings:

- **Generators are bpy-free** so they run in the ordinary unit gate
  (`tools/blender/tests/test_house_grammar_*.py`, `test_tree_mesh.py`,
  `test_grass.py`) with no spawned Blender.
- **The grammar validates eagerly** (`GrammarError` naming the field) and
  **quantises to a 1 µm weld grid**, so outputs are fingerprintable.
- **Camera predicates run before anything renders** (`house_grammar/staging.py`:
  readable size, tall-or-continuous occluder rule, dock coverage).
- **The emitter computes no geometry**; it converts the lane frame through
  `Exterior.y()` exactly once (#935) and never saves or applies modifiers.
- **Intentional symmetry stays live**: `ModifierSpec("MIRROR")` is installed as
  a real modifier rather than baked.

This is a good architecture. Most of what follows leaves it alone.

## 2. Findings in the current tooling

### 2.1 Blender version drift (high)

| Where | Version |
|---|---|
| `.github/workflows/blender-map-export.yml` | 5.0.1 (SHA-pinned) |
| `.github/workflows/blender-item-source.yml` | 5.0.1 |
| item toolkit README / `REPRODUCTION_NOTES.md` | 5.0.1 |
| owner's machine (`tools/asset-language/baseline/blender-depth-summary.json`, `st_maria` collision fixture header, live bridge README) | 5.1.2 |
| fallback search lists in `town_environment_pipeline.py`, `build_synthetic_environment.py`, `check_thestra_camera.py`, `tools/asset-gen/blendergeom.py` | 5.1 → **4.2 → 4.1** |

CI checks a different Blender from the one the owner authors in, and the
fallback lists will quietly pick up a 4.x install that cannot open the 5.x
documents. This project has already been bitten by version-dependent exporter
behaviour: 5.0's OBJ exporter deduplicated coincident UV corners
nondeterministically (`docs/reports/b-item-blend-source-migration-2026-08-15.md`).

5.2 is an **LTS** (released 14.07.2026), so it is the natural single pin.

### 2.2 Blender locator logic copied seven times, with four env-var names (medium)

`BLENDER` (`town_environment_pipeline.py`, `build_synthetic_environment.py`,
`depth_baseline.py`, `blendergeom.py`), `BLENDER_PATH` (`export_map_blend.js`,
`check_thestra_camera.py`, the map-export workflow), `BLENDER_BIN`
(`compile_item_blends.py`, `asset-production/build_world_prop.py`), and
hardcoded `C:\Program Files\...` lists in seven files. This is exactly the
copy-pasted logic the non-negotiables forbid, and it is how 2.1 happens: nothing
can pin a version when there are seven places a Blender is chosen. One locator
(Python and a thin JS twin, or the JS calling the Python) that reads one
variable and **asserts the pinned version** would fix both.

### 2.3 The tree lab meshes trees differently from what ships (high)

`tools/blender/recipes/tree_lab.py:_branch_mesh` still builds branches with a
**Skin modifier** and then `modifier_apply`s it. Everything that ships —
`replace_st_maria_tree.py` and the live bridge's tree operation
(`live_bridge/server.py`) — uses the bpy-free `tree_mesh.branch_mesh`, which was
written precisely to replace the Skin path (`tree_mesh.py` docstring). So the
owner's orbitable laboratory judges one mesh and the Praça receives another:
two meshers for one skeleton, which is a parallel implementation that can
disagree. The lab should call `tree_mesh.branch_mesh` and the Skin path should
be deleted.

### 2.4 Stale "known incomplete" in the exterior exporter (low)

`export_exterior_environment.py`'s docstring still says the atlas "packs to 9%"
and that the #1023 circular bake-image dependency is unresolved. #1023 was
closed by #1069, and `town_environment_pipeline.py:156` now keeps the image
node unlinked during the bake. The docstring should be re-measured and updated
(or the paragraph deleted). The "not yet generic" section (hardcoded
`st_maria_praca` names, the open #935 mirror question) is still accurate.

### 2.5 The live bridge caps procedural placement (context, not a defect)

`live_bridge/server.py` caps a request at 1,024 new vertices / 1,024 faces
(`MAX_NEW_VERTICES`), and `grass.GrassSpec.max_vertices` mirrors it "so a patch
stays placeable through any route". That is correct for a safety boundary, but
it means ground cover is authored as many small patches pushed through a
socket. This is the clearest place GN helps (§4.3).

## 3. Blender 5.2 LTS — what is worth having

Ranked by value to this project.

| 5.2 change | Relevance | Recommendation |
|---|---|---|
| **LTS status** | Solves 2.1: one version supported for two years. | **Adopt.** Pin CI and local to 5.2.x in one PR, with a SHA like the map-export job already does. |
| **Cycles bake fix: excessive aliasing from wrong derivatives** | Our atlases are Cycles bakes (`town_environment_pipeline.py`). Texture sampling during bake gets better — and therefore *different*. | Adopt with the pin, but expect every rebaked atlas to shift. Rebaking a shipped package is a G5-visible change and an owner call; don't rebake as a side effect of the upgrade. |
| **Python API: GN modifier inputs are now RNA properties** (not `mod["Socket_2"]`) | Nothing in the repo drives GN from Python today (grep), so there is no migration cost. | If we adopt GN (§4), write against the 5.2 API from day one. Another argument for pinning 5.2 *before* any GN work. |
| **`gpu.init()` for GPU in background mode** | Headless studies (`study_house_grammar.py`, `towngen/photograph_blend.py`) and bridge captures could use offscreen GPU drawing without a UI session. | Worth a spike; unverified what it unlocks for EEVEE renders specifically. |
| **`bpy.data.all_ids`** | The live bridge's mutation fingerprint and the read-only item compiler both want "every datablock". | Small cleanup when touching those files. |
| **Image-buffer API: format conversion, direct pixel access** | Atlas coverage metrics ("written fraction", #1023) and post-bake checks can be done in-process without round-tripping through PIL. | Opportunistic. |
| **UV: select by winding, island overlap selection, bounding-box unwrap option, UV snapping** | Minor help when hand-fixing bake receivers (#928). | Nothing to do. |
| **GN: lists, functions, Mesh Bevel node, geometry bundles, GN on empties** | See §4. Lists are explicitly minimal in 5.2 ("only a few core nodes"). | Don't build on lists/functions yet. |
| **XPBD cloth/hair physics in GN** | Could drape awnings / laundry / banners once and bake them static (the grammar has `CanopySpec`). | Niche; only if a scene asks for it. |
| **Online asset libraries** | Conflicts with the licensing-provenance inventory and the sterile town rule. | Don't, without a provenance story. |
| **Cycles texture cache (.tx)** | For scenes with many large textures; our bakes are small atlases. | Irrelevant. |

## 4. Should houses, trees and ground cover move to Geometry Nodes?

### 4.1 The test

The project already has a precise rule, earned in the Phoenix experiment
(`docs/reports/phoenix-organic-hybrid-2026-08-15.md`):

> Use Geometry Nodes when authored structure needs repeated placement/variation,
> but keep the controlling guide geometry, source element and important
> exceptions as obvious editable objects in the `.blend`.

And the C-profile migration set the default as "GN is an escalation path, not
the baseline". Applying that rule to each generator, and adding what GN would
cost against the non-negotiables:

What GN costs here:

- **Unit-gate coverage.** A node tree only evaluates inside Blender. The
  grammar's ~1,900 lines of tests run in the normal unit gate today; a GN
  equivalent can only be checked by spawning Blender.
- **Review and agent authoring.** Node trees live in the binary `.blend`. They
  do not diff, and building them from Python is verbose and brittle (and the
  5.2 RNA change just broke every script that did it the old way). Most of this
  repo is authored by agents working through text.
- **Fail-loud validation.** `GrammarError` names the offending recipe field. A
  GN graph given bad input produces wrong geometry, not an error.
- **One semantic authority.** Porting any generator means the Python and the
  node tree coexist during migration, and "keep both" is forbidden. A port has
  to be all-or-nothing per generator.
- **Version determinism.** GN output (distribution, realize order, attribute
  domains) is not promised stable across releases; we already saw OBJ output
  shift between 5.0 builds.

What GN gives:

- **Procedural handles that survive adoption.** Once the owner adopts a `.blend`
  it becomes source authority and must never be regenerated. What the emitter
  wrote is then dead mesh: changing a house means vertex editing or a
  `--force` regenerate that destroys hand work. A GN modifier keeps its inputs
  editable in the adopted document. This is the real argument for GN, and it
  is the same argument that made `ModifierSpec("MIRROR")` a live modifier.
- **Live, in-document feedback** (paint a weight, see the grass move) without a
  script run or a bridge round trip, and without the 1,024-vertex cap.
- **Instancing.** Card foliage and grass as instances of a few source cards,
  realised only at export.

### 4.2 Houses — **no**, keep the grammar

The grammar is not a placement problem. It is architecture: courses as rails,
roof profile intersection, openings cut through courses, seams (`seam.py`),
camera staging predicates. That is exactly the logic that benefits most from
unit tests, text review and named validation errors, and exactly what GN is
worst at expressing (5.2's lists and functions are a start, but the release
itself calls list support minimal). Porting it would trade the best-tested part
of the Blender tooling for an untestable binary graph.

What *is* worth doing is widening the existing live-modifier seam, on the
precedent of `MIRROR`, **only where the repetition is intentional and the
owner would plausibly tweak it after adoption**:

- a *single-purpose* GN group per such case — e.g. an `sr_array_openings` group
  that repeats a window record along a course with a count/spacing input —
  emitted through `ModifierSpec` so the grammar still owns what gets repeated
  and where;
- the grammar keeps emitting the fundamental domain, the same way mirroring
  works now.

Do not start this until a real recipe needs it. The current library has one
building (`library.py` is deliberately "alone"), and adding a GN seam for a
hypothetical need is the speculative infrastructure the repo tries to avoid.
The 5.2 **Mesh Bevel node** does not change this: at 27.4 px/m most bevels are
sub-pixel, and the ones that matter (cornices, bands) are already real
geometry.

### 4.3 Ground cover (grass, weeds, scattered litter) — **yes, pilot it**

This is the textbook case for the Phoenix rule. `grass.py` is a density/slope
scatter of cards. `terrain_surface.py` already exists only to raycast the real
ground, read a painted vertex group and clear keep-out footprints. Every one of
those maps directly onto stock nodes (distribute points on faces with a density
attribute, a normal/slope test, a proximity or raycast keep-out, instance on
points, realise before export). In GN:

- density is painted straight onto the terrain and updates live;
- the keep-out objects (walkable lane) are ordinary objects in the document;
- nothing crosses the bridge, so the 1,024-vertex cap stops shaping authoring;
- the output is realised and baked, so **the runtime still sees only OBJ + atlas**.

Cost is honest but contained: `grass.py`'s tests stop covering what ships, so
the pilot needs a headless check (vertex budget, no instance above the slope
limit, nothing inside a keep-out footprint) run by spawning Blender, the way
`tests/terrain_surface_blender.py` already does. If the pilot wins, delete
`grass.py`'s scatter and `terrain_surface.py` in the same PR (keep
`tree_mesh.card_corners`, which trees still need). If it doesn't, keep Python
and close the question. No dual path either way.

### 4.4 Trees — **split: skeleton stays Python, crown dressing could go GN later**

The skeleton (`tree_generator.py`) is space colonisation with attraction points,
kill radius, apical dominance and a seeded LCG. In GN that means a repeat zone
over a growing point cloud: possible, slow to author, impossible to unit-test,
and it would throw away presets that already work. Keep it.

The mesher (`tree_mesh.py`) is also fine where it is: it was written to get
*off* a Blender modifier (Skin) so the mesh could be tested. Moving it back into
a node graph undoes that for no gain.

The one piece that fits GN is **foliage card placement** on the finished
skeleton: instancing crossed cards along carriers with bounded roll/scale
variation is the Phoenix pattern. But `foliage_mesh` already does this in
tested Python, trees are few and hand-placed, and there is no post-adoption
tweaking pressure yet. Revisit only if the owner starts editing crowns inside
adopted documents. Fix §2.3 first; that is the tree problem that actually
exists.

### 4.5 Street dressing and repeated props — **yes, when it appears**

Rows of bollards, roof-tile variation, pot plants along a sill, market clutter:
repeated placement along an authored guide with deliberate gaps. Same rule,
same pattern as ground cover. Worth doing when a screen needs it, not before.

## 5. Recommended order

1. **Pin Blender 5.2 LTS everywhere and add one locator** (2.1 + 2.2). One PR:
   one locator that reads one env var and asserts the version; both workflows
   moved to 5.2.x with a SHA; the 4.x fallbacks deleted; the item compiler's
   `--check` re-run to see whether 5.2's OBJ exporter changes committed
   outputs. **Don't rebake shipped atlases in this PR** (the bake fix will move
   pixels).
2. **Make the tree lab use `tree_mesh.branch_mesh`** and delete the Skin path
   (2.3).
3. **Refresh the exterior exporter's docstring** against a measured bake (2.4).
4. **GN ground-cover pilot** on one exterior (4.3), written against the 5.2
   RNA API, with a headless Blender check and all-or-nothing replacement of
   `grass.py`/`terrain_surface.py`.
5. Houses and tree skeletons: **no change**. Re-open only if a recipe needs
   intentional, owner-tweakable repetition (4.2) or crowns start being edited
   after adoption (4.4).

## Sources (5.2)

- [Blender 5.2 LTS release notes (index)](https://developer.blender.org/docs/release_notes/5.2/)
- [5.2 Geometry Nodes release notes](https://developer.blender.org/docs/release_notes/5.2/geometry_nodes/)
- [5.2 Python API release notes](https://developer.blender.org/docs/release_notes/5.2/python_api/)
- [5.2 Modeling & UV release notes](https://developer.blender.org/docs/release_notes/5.2/modeling/)
- [CG Channel: Blender 5.2 LTS key features](https://www.cgchannel.com/2026/07/blender-5-2-lts-is-here-discover-its-5-key-features/)
- [80.lv: Cycles texture cache in 5.2](https://80.lv/articles/blender-5-2-lts-introduces-new-cycles-texture-cache-system)
- [Blender developers blog: Geometry Nodes physics](https://code.blender.org/2026/07/geometry-nodes-physics/)

Agent-Signature:
  platform: Claude Code (cloud session)
  model: platform-selected/unknown
  role: research
  task: "Blender tooling audit; issues #1254-#1257"
  base: 7e7e231
