# Passage House courtyard refinement (2026-10-01)

Revision 8 keeps the previous revision's continuous lodging wing, covered passage, roof lightwell and backstreet skyline. It refines the openings and materials after owner feedback that the scene remained rough, especially its windows. This is a staged visual candidate, not shipping content or owner PLAYED acceptance.

## Art direction and geometry

The shared window family now produces slender casements, pane divisions, panelled shutters and small hinges. The courtyard uses recessed blue-green glazing and sage-painted joinery. Jambs, sill and shutter silhouettes survive export; shallow panels, rails and hardware bake from editable source geometry. Grilles in the shared family now consist of spaced iron bars rather than an opaque plate. Shared door panels can form a two-by-two arrangement, and their base height is parameterized so the courtyard consumes its upper landing datum.

The lodging entrance uses warm timber and a restrained authored bounce light under its roof. Its receiver matches the actual door leaf instead of extending across the surrounding wall. Limewash has broader, quieter variation and the cobbled paving has less contrast. EEVEE remains at 0 EV; the light rig supplies the adjustment. Grass remains omitted. The scene is still stylized and sparse: this pass improves joinery and hierarchy, not every remaining artistic weakness.

The package contains **6,718 triangles**, **4,039 vertices** and one 1024×1024 atlas. This is 166 triangles (2.53%) above the previous revision's 6,552, mainly to retain opening depth and shutter silhouettes. Reported package size is 786,707 bytes. UV face coverage, rasterized at atlas resolution, is **67.178%**; this measures allocated coverage, not useful visible detail. The final source is 1,417,166 bytes with SHA-256 `1406e45686efa4adc663889e034ebf388023d82933d737555624ed83319ed893`. Per-file hashes and frame metadata are in the candidate's `review/measurements.json`.

Native Classic (256×240) and Wide (426×240) captures include Walker and the menu at lane positions 0.5, 2, 5, 8 and 11.5 m. Current frames are in `review/runtime/`, source renders in `review/source/`, and before/after images in `review/comparison-classic.png` and `review/comparison-wide.png`. Inspection shows the warm entry and thinner sage windows remain readable in the actual compositor. Native captures retain the Project's current night sky; the courtyard lighting is static and baked. No golden references were recaptured.

## Reproducible workflow

The advertised fresh-build command now composes all context in one recipe run. Five successive source-mutation scripts have been replaced by `courtyard_context.py`, called by `passage_house_courtyard.py` before its sole save. The registered source remains a scaffold; adopted sources are untouched. A real Blender regression builds into a temporary path and compares mesh coordinates, face connectivity, transforms, material bindings, bake roles and modifier types against the registered scaffold. It also verifies that the registered source bytes were not changed. This is semantic geometry parity, not byte-identical `.blend` files or a complete shading equivalence proof.

Two reusable tooling defects were corrected. The receiver test now checks named required receivers and role behavior rather than assuming exactly four receivers in the entire scene. The exterior exporter records the actual runtime-serialized camera contract; it no longer requires a nonexistent `projectionFrame` field or labels every export as candidate Map 32. Atlas projection uses the same existing runtime camera resolver, with pitch -17.5 degrees, 48 px Walker height and flat-ground feet at y=128.

The source registry declares EEVEE supersampling 2 for this scaffold. The final offline export took 79.7 seconds on its first measured run; the subsequent fresh-process export took 76.5 seconds. These are local wall times, including launch, mesh preparation, projection and packaging. Supersampling costs more than the previous single-sample projection and should be judged against native output quality.

## Verification and limits

Final candidate staging, native capture, source profile review, staged G1 (`VALIDATE OK`) and full staged units (`ALL UNIT TESTS OK`) passed. Profile review checks every control point, intermediate samples and both door landings. Units exercise the bounded lane, reciprocal transfers, arrivals, slope endpoints and editor profile/history behavior. Seven Effekseer world-effect assertions were unavailable because the native shim was absent. Targeted Python contracts, the two candidate/history/geography Node tests, the source-manifest check, curated vendor-library check and 35-edge town check also passed; detailed outcomes are in `review/measurements.json`.

Fresh source generation and final exports ran through `offline_blender.py`, which rejects network socket access inside Blender. The curated library remains repository-local; upstream files and global preferences are unchanged. This is a build-level networking denial, not a machine-wide firewall test.

Map 32 remains candidate-only. The profile `(0,0), (2,0), (8,0.30), (12,0.30)`, Cortiço doorway identity, intro arrival into map 25 and existing camera calibration remain unchanged. The staged datums are courtyard -0.34378736413887334 m and lodging -0.04378736413887335 m relative to Cortiço's datum. Shipping topology and town generator are unchanged. Draft PR #1296 remains stacked on #1294. Promotion requires owner visual/traversal review and must update the owning generator or authored-map authority.

Agent-Signature:
  platform: Codex desktop
  model: platform-selected/unknown
  role: implementation
  task: "PR #1296 courtyard art direction and reproducible scaffold refinement"
  base: d336ab02
