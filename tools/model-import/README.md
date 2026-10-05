# Shared static Model consumers

Model recipes live in the Project's `data/models.json`. The existing importer
normalizes OBJ/GLB geometry to Z-up/map-cell units, stable material slots and
source/recipe provenance. `sourceUnitsToMapCells` is physical world scale;
the item turntable independently fits the same geometry to its window.

An OBJ migration recipe can explicitly select `appearance: "obj-mtl"` to compile
its existing native material binding. The compiler executes the runtime's one
Lua MTL grammar locally through the pinned Fengari host. It hashes MTL and
texture dependencies and transports resolved color/texture/pass facts with
stable slots. This is a source adapter, not a second authored Surface library.
It cannot override a recipe's semantic Surface identity. Surface realization,
hierarchy and animation remain separate work under #668/#669.

Canonical export/Test Play/gate staging compiles registered Models into
`assets/generated/models/` with a content-addressed manifest. Source-path
consumers of a bound recipe resolve to its Model identity; other OBJ sources
remain on the explicit migration adapter. Geometry-only recipes are not promoted
over existing visual sources, and an unbound slot fails when asked to render.
Do not edit generated bundles.

The `item.lantern` recipe exercises item inspection, native world rendering,
Studio item preview and Studio Event model acquisition. Both renderers acquire
the compiled bundle; Studio requests fresh compilation through
`/api/model-bundle?path=...`. Its Three preview preserves source colors and UVs
but is an authoring preview. Overlay materials require native preview rather
than silently disappearing.

World placements resolve into `engine.geometry.model_instance`: stable identity,
Model reference, XYZ translation, row-major orthonormal orientation, positive
uniform scale, provenance and explicit baked-lighting policy. Grid Events and
wall fixtures adapt their existing authored fields. Environment visuals use the
same acquisition/placement machinery while retaining collision, anchors,
prerender and traversal ownership in the environment adapter.

Run `npm run test:model-import`. Native consumer/pixel checks run as
`test_model_resource` in the normal staged unit suite. To retain its proof,
create an output directory and set `THESTRA_MODEL_PROOF_OUTPUT` before the unit
run, then run `node tools/model-import/check-native-proof.js <output-directory>`.
The retained image and JSON prove actual native/Three facts without reparsing
the source Model. Golden references remain owner-controlled.
