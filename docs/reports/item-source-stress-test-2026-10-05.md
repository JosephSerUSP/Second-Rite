# Item-source tooling stress test — 2026-10-05

PR #1400 is being used as a **tooling probe**, not as an assertion that its six consumable designs are final art. The weak visual result is useful evidence: the first pass mostly exercised profile/revolve plus simple Curve attachments, so it proved source authority while barely touching the richer Blender-native construction vocabulary that the source contract advertises.

## Stress matrix

| Capability | Before this pass | Stress action | Result / boundary |
|---|---|---|---|
| Editable profile + Screw | exercised by the six consumables | keep as baseline | supported; generated Screw UV behaviour was already fixed during #1400 |
| Hidden Curve bevel/profile object | used by prior migrations, but scratch-copy self-containment was not asserted | translated-root regression | internal profile targets are now remapped to scratch duplicates |
| Boolean cutter | documented and used in prior content | translated-root regression | internal cutter targets are now remapped to scratch duplicates |
| Mirror origin | documented fabrication vocabulary | translated-root regression | internal mirror-object targets are now remapped |
| Curve modifier target | documented ARRAY/Curve-style composition | translated-root regression | internal target is now remapped |
| Constraint target | ordinary Blender construction relation | translated-root regression | internal target is now remapped |
| Geometry Nodes interface object input | advertised open-ended source vocabulary | generic modifier ID-property remap + report visibility | remapped when Blender exposes the object on the modifier; node-tree-internal references remain a visible boundary |
| Geometry Nodes node-tree object reference | advertised open-ended source vocabulary | source-graph report scans node/socket object references | **reported, not rewritten yet**; shared node groups must not be mutated silently |
| Collection-instance Empties | advertised source vocabulary | translated-root realization regression | **supported** by realizing scratch instances before OBJ selection; authoritative collections remain untouched |
| External object references | previously invisible | source-graph report | retained rather than silently rewritten and marked `external` for audit |
| Read-only source authority | established before #1400 | regression export after richer graph duplication | preserved; the source graph remains untouched |

## Failure exposed

`second_rite_asset_core.duplicate_hierarchy()` copied objects and their datablocks, then recentered those duplicates, but Blender pointer relationships inside copied modifiers, constraints and Curve data continued to target the **original** source objects. A Boolean cutter or Curve bevel profile could therefore live in a different coordinate frame from the temporary object being exported. A source could appear correct at an origin-aligned root while becoming wrong when the root moved.

The fix makes the scratch hierarchy self-contained for object-valued RNA pointers and modifier ID-properties when the referenced object is itself under the export root. The regression deliberately uses a non-zero root transform and simultaneously exercises a Boolean cutter, Curve bevel object, Mirror origin, Curve modifier target and constraint target.

## Auditability upgrade

`compile_item_blends.py --report-dir <dir>` now exposes the Blender-side structural report for ordinary batch/check runs. Reports include modifier/constraint vocabularies, hidden-construction counts and object-valued dependency edges classified as `internal` or `external`. This is intentionally diagnostic rather than a new source grammar: a `.blend` remains free-form Blender authority.

The report also scans Geometry Nodes node/socket object references. Those references are **not yet remapped**, because modifying a shared node group would violate the read-only-source principle and safely duplicating nested node graphs is a separate capability. The tooling should show that limit instead of pretending Geometry Nodes are universally safe.

## What #1400 should do next

The six consumables should now be treated as six adversarial authoring experiments, with each redesign chosen to force a different Blender-native construction relation rather than six variations of profile/revolve. The next useful probes are Geometry Nodes object/collection inputs, real instancing, Boolean stacks with hidden guides, anisotropic Curve/GN profiles, and mixed direct-mesh + procedural assemblies. Visual quality remains a review signal: if a supposedly broad toolset keeps producing lathed bottles, the authoring affordances are still too narrow or too opaque.


## Instance stress follow-up

The next adversarial probe confirmed a concrete contract mismatch: ordinary Blender collection instances are represented by `EMPTY` objects, while the runtime exporter selected only geometry object types. The instance carrier was therefore excluded before OBJ export, despite instances being part of the documented authoring vocabulary.

The export scratch phase now makes visible Blender instances real **only on the duplicated graph**, then selects the resulting geometry. A pinned-Blender regression uses a translated item root, a scaled/offset collection-instance Empty, and a reusable collection that is not part of the root hierarchy. It verifies runtime geometry and placement, and it verifies that object/collection counts plus the authoritative instance reference and transform are unchanged after export cleanup.

This deliberately does not claim universal instancing support. Geometry Nodes instances are evaluated through modifier output and remain a separate stress axis; nested collection-instance graphs and linked-library collections should receive their own probes before being described as guaranteed.
