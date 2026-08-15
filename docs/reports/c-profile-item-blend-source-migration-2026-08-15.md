# C profile item Blender-source migration — 2026-08-15

## Scope

This is the second production migration from the Batch C spatial-gesture experiment into authoritative per-item Blender source documents.

The first migration (#585) established ordinary editable Curve authority for Cerberus Fang, Water Scepter, Blackroot and Barbed Spear. This pass intentionally selected the four remaining C items because they stress the part that round Curve bevels do not express:

- **Hermes' Boots** — elliptical boot bodies, rectangular soles/wings, heavy roll, closed ankle loops.
- **Mimic Tongue** — a broad anisotropic muscular sweep with strong taper and twist.
- **Molten Manacle** — irregular cyclic cuff and chain-loop authority.
- **Phoenix Pinion** — an extremely flattened feather mass plus thin rolled vane ribbons.

The architectural question was deliberately narrow: **is Blender's native editable Curve path + editable bevel/profile object + point radius + point tilt sufficient, or does production C authoring already require Geometry Nodes?**

## Source representation

The accepted sources use Blender-native construction:

```text
3D path Curve
  + bevel_object → editable hidden 2D profile Curve
  + point.radius → taper
  + point.tilt   → roll
  + cyclic spline where appropriate
  ↓
read-only evaluated runtime OBJ/MTL
```

Profile objects remain children of the marked item export root but use `hide_render = true`. The shared exporter therefore omits them as standalone runtime geometry while Blender still evaluates them as dependencies of their visible path Curves.

The four source documents are:

```text
assets/authoring/items/hermes_boots.blend
assets/authoring/items/mimic_tongue.blend
assets/authoring/items/molten_manacle.blend
assets/authoring/items/phoenix_pinion.blend
```

Each document embeds an `AUTHORING_README` and retains semantically separate path/profile objects. The old procedural recipe is not required after source creation.

## What remains editable

The resulting documents expose the useful construction rather than a baked OBJ:

- centerline/path control points;
- per-point radius/taper;
- per-point tilt/roll;
- explicit ellipse/polygon profile Curves;
- explicit rectangular ribbon profile Curves;
- cyclic cuff and chain-link splines;
- separate grooves, veins, drool, vanes, rachis, soles, wings and ornament curves;
- canonical material assignments and source-authored runtime material-pass metadata.

Where Batch C varied anisotropic aspect or ribbon thickness independently at every point, the inherited values are preserved as custom source metadata. The visible native Blender construction uses a representative static profile for that path.

## Review methodology

Migration acceptance was visual, not merely structural.

Every candidate pass:

1. restored the current `main` canonical OBJ models;
2. rendered those four models through the real LÖVE `item-sheet` viewer;
3. created the candidate `.blend` sources;
4. compiled them through the production Blender-source compiler;
5. ran the item corpus gate;
6. reran the full production `--check` compiler and verified source SHA-256 identity;
7. rendered the compiled products through the same real item viewer;
8. compared the four-angle before/after sheets.

The accepted calibrated review is GitHub Actions run **31907947922**, artifact **9252873109**, `c-profile-item-source-migration-review`.

## Rejected first profile pass: perpendicular zero-roll frame

The first technically green profile pass was rejected visually.

Blender's native Curve bevel frame and Batch C's deterministic transported sweep frame used perpendicular zero-roll bases after the legacy C/Y-up to Blender/Z-up coordinate conversion. With anisotropic profiles this was immediately visible:

- broad Phoenix Pinion views became edge-on;
- its old edge-on view became broad;
- Hermes' ribbons and boot profiles showed the same orientation swap more subtly;
- Mimic Tongue's broad/thin presentation moved to the wrong views;
- round Molten Manacle geometry was effectively unaffected.

This was a frame calibration error, not evidence that the profile representation was insufficient. Source creation therefore applied one uniform **+90° tilt calibration** to inherited Batch-C roll values.

The calibration is migration history only. The adapter was deleted after source creation; the committed `.blend` documents contain ordinary Blender-space path coordinates and ordinary Blender tilt values. Future Blender-native authoring should use Blender's visible frame directly.

## Accepted visual result

After the uniform frame calibration:

- **Hermes' Boots** retain the paired boot silhouette, soles, ankle bands and wing gestures across the four viewer angles.
- **Mimic Tongue** retains the broad muscular mass, taper, fold/twist impression and small surface gestures.
- **Molten Manacle** is visually extremely close because its dominant profiles are round and cyclic.
- **Phoenix Pinion** again presents as a broad continuous feather mass in the same views, with its gold rachis and sparse vane gestures intact.

The remaining differences are localized to exactly the capability that was intentionally not recreated: Batch C could vary anisotropic X:Y section aspect independently at every path point, while a native Blender bevel object supplies one profile per path. Phoenix's exact swelling/highlight distribution, Tongue's width envelope and some boot-body proportions therefore differ slightly from the old resolved mesh.

At item-viewer scale those differences were judged small enough that the models still read as the same authored objects. They do **not** justify making Geometry Nodes a prerequisite for C authoring.

## Geometry and source cost

The four original Batch-C runtime models together used:

```text
965 vertices
1,047 authored face records
```

The accepted Blender-profile products use:

| Item | Vertices | Face records | Triangles |
|---|---:|---:|---:|
| Hermes' Boots | 792 | 868 | 1,120 |
| Mimic Tongue | 394 | 411 | 524 |
| Molten Manacle | 536 | 738 | 976 |
| Phoenix Pinion | 648 | 624 | 792 |
| **Total** | **2,370** | **2,641** | **3,412** |

That is approximately **2.46×** the old cohort's vertices and **2.52×** its authored-face count. The increase is real and should not be hidden: Blender's evaluated Curve/profile surfaces, caps and semantically separate pieces are less parsimonious than the hand-written experimental sweeper.

It remains small in absolute runtime terms, and it buys directly editable source documents. Future compiler/export optimization may reduce the resolved geometry without changing the authoring representation.

The source documents themselves remain compact:

| Source | Size |
|---|---:|
| `hermes_boots.blend` | 95,075 bytes |
| `mimic_tongue.blend` | 91,225 bytes |
| `molten_manacle.blend` | 91,161 bytes |
| `phoenix_pinion.blend` | 93,847 bytes |

## Validation

The accepted run reported:

```text
Hermes' Boots:   792v / 868f / 1120t — RUNTIME OBJ OK
Mimic Tongue:    394v / 411f / 524t  — RUNTIME OBJ OK
Molten Manacle:  536v / 738f / 976t  — RUNTIME OBJ OK
Phoenix Pinion:  648v / 624f / 792t  — RUNTIME OBJ OK

items with models: 207
  duplicate_geometry: 11
  no_uvs: 124
  shared_file: 1
ITEM MODELS OK

ITEM BLEND COMPILE OK: 8 source(s)
```

The `8 source(s)` check includes the four source-authority items already merged by #585. A second production `--check` compile reproduced all eight runtime products, while before/after SHA-256 hashes of the four newly created `.blend` sources were identical.

## Architectural conclusion

The second cohort answers the profile question in favor of a smaller architecture:

> **Blender-native Curve path + editable bevel/profile object + radius + tilt is the default C authoring vocabulary. Geometry Nodes is an escalation path, not the baseline.**

This gives authors and agents visible handles for path, section, taper and roll while retaining ordinary Blender composition. It covers round tubes, elliptical bodies, flattened profiles, ribbons and cyclic loops without introducing a project-specific sweep IR or a mandatory Geometry Nodes graph.

Per-point anisotropic section variation remains a legitimate future capability. It should be added only for assets whose art direction demonstrably needs it, preferably as a Blender-native enhancement that preserves the same source/product boundary.

## Implication for the A/B/C experiments

With this migration all eight Batch-C production items now have authoritative editable Blender documents. The old C Python cohort remains useful as design evidence and provenance, but its production role is finished.

C should henceforth describe an **authoring vocabulary** inside Blender:

```text
spatial path
+ explicit profile when needed
+ taper
+ roll
+ semantic child gestures
```

It composes naturally with A's revolved/semantic solids, B's fabricated plates/holes, direct modeling, modifiers and—when specifically earned—Geometry Nodes.
