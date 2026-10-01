# Passage House courtyard — owner-directed architectural revision (2026-09-30)

The owner rejected the first candidate on visual grounds: the lodging wall broke into isolated pieces, the door appeared to open into sky, and the windows and door were repeated custom geometry. This revision rebuilds the lodging as a continuous covered building and uses shared adjustable opening families. The original report and screenshots are retained as rejected v1 under `review/rejected-v1/` and [the prior report](passage-house-courtyard-rejected-v1-2026-09-30.md).

## What changed

The lodging now has continuous masonry bays around real door and window openings, a structural stone head over the door, side returns, a rear wall, a pitched tiled roof and a closed vestibule behind the entry. The approach remains an open-to-sky court; sky at the outer edge belongs to the exterior beyond the lodging wing. The door sits under the supported covered passage and carries raised timber panels baked onto its receiver. Windows, shutters and frames use the same family builder.

`tools/blender/recipes/opening_families.py` is the shared adjustable door/window implementation. The established `Exterior.doorway()` and `Exterior.window()` now delegate to it, and the courtyard recipe composes it with map-specific width, height, sill, shutters, grille, panels and material choices. A focused two-case contract checks dimensional morphing, anchors, panel materials, shutter options and source-bake roles in `tools/blender/tests/test_opening_families.py`.

Shallow joinery remains detailed in editable source geometry and bakes to the four simple receiver cards. Runtime geometry carries the wall, true openings, building and passage roofs, posts and profile paving. The map-32 ground profile, arrival anchors, movement/camera calibration, menu layout and Cortiço/lodging transition identities remain as before; shipping maps and the town generator remain unchanged.

## Current package and visual evidence

The final source SHA-256 is `17b2dd657a4b82832ab2238a4d4d8eec12e5ea156c2edda7a15de645376b8483` (1,041,966 bytes). The named source remains a registered scaffold. Its exported package contains 1,450 triangles and 969 vertices, with a 1024×1024 atlas; the complete package is 891,931 bytes. Per-file hashes, native frame hashes and pixel deltas versus rejected v1 are in `projects/hichaukitoden-game/assets/authoring/candidates/passage_house_courtyard/review/measurements.json`. Those deltas show the captures changed; they do not measure visual quality.

Current editable-source renders are in `projects/hichaukitoden-game/assets/authoring/candidates/passage_house_courtyard/review/source/`. Runtime captures at Classic 256×240 and Wide 426×240 are in `.../review/runtime/`, at positions 0.5, 2, 5, 8 and 11.5. I inspected both sizes across all five positions, including the upper landing. The lodging reads as one continuous roofed frontage; the door and shutters remain visible at native size, and the remaining sky appears beyond the court/building edge. No goldens were recaptured.

## Verification and limits

The final source-manifest check passed. The pinned Blender 5.2.2 source build, EEVEE export at 0 EV with authored lighting, final canonical candidate stage, and Classic/Wide native compositor captures passed. The courtyard datum remains `-0.34378736413887334` m and the lodging datum remains `-0.04378736413887335` m, derived by the shared generated world-view semantics.

Final verification passed: staged G1 (`VALIDATE OK`); staged units (`ALL UNIT TESTS OK`, including 973 courtyard runtime assertions); 45 source/vendor/receiver/EEVEE/opening-grammar Python checks; the two candidate/history/geography Node tests; the 35-edge town check; the source-manifest check; the curated vendor-library check; and final source review, EEVEE export and canonical staging. Local Effekseer was unavailable, leaving seven world-effect assertions unexercised. These render and data checks are not owner PLAYED or traversal acceptance. The PR remains a draft stacked on #1294; promotion still requires owner visual/traversal review and must update the owning authored-map authority rather than generated shipping output.

Agent-Signature:
  platform: Codex desktop
  model: platform-selected/unknown
  role: implementation
  task: "PR #1296 owner-directed Passage House architectural revision"
  base: 53e74ded
