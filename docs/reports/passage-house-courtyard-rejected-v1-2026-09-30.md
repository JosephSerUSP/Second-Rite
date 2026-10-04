# Passage House courtyard and offline library — 2026-09-30

The branch delivers a fresh editable courtyard scaffold, three curated offline
materials, an authored map-32 candidate and canonical staged Project. Shipping maps,
existing adopted sources and the town generator are unchanged. Promotion awaits owner
visual/traversal review. This report records local verification, not PLAYED acceptance.

## Geography and elevation

`node tools/towngen/audit_geography.js --output out/geography.json` extracts the
actual town transfer possibilities, including nested lists and common events, target
arrival positions, local lanes and profiles. It does not evaluate event conditions or
infer global heights. The captured extraction is `review/shipping-geography.json`.

The exterior chain 16 → 17 → 26 → 18 → 19 → 31 and reciprocal returns exist. The
Churchyard/Port climb, Cortiço/Port workers' stair, Praça/Quay water stair and the
Market/Padaria/Home/Cortiço connection exist. This supports the courtyard being a
Passage House annex off Cortiço, without inserting it into the island's street ring.

Confirmed unrelated contradiction: Praça event 1704 enters the padaria upstairs (24),
but that room returns to the hearth (23), not Praça. Its address also conflicts with
the approved padaria/home building between Market and Cortiço. Evidence and acceptance
criteria were added to [#1016](https://github.com/JosephSerUSP/Second-Rite/issues/1016#issuecomment-5922469281).
No speculative global elevation inconsistency was filed: only maps 26 and 31 carry
non-flat town profiles; other lane datums are local zero, and their common island datum
is undocumented. Existing [#989](https://github.com/JosephSerUSP/Second-Rite/issues/989)
remains a separate Praça source-ground issue.

Staging retains Cortiço's doorway identity and position, rewires its transfer to 32,
rewires lodging's return to 32, and adds reciprocal candidate exits. Introduction
arrival directly into 25 is preserved. Map 32 owns `(0,0),(2,0),(8,.30),(12,.30)`.
The paving consumes those segments; thresholds sit at y=.5/z=0 and y=11.5/z=.30.
Cortiço's sampled door height is -0.34378736413887334 m. Taking Cortiço's datum as zero,
that is the courtyard datum; lodging's local floor maps to -0.04378736413887335 m.
These are documented frame relationships, not a town-wide coordinate migration.

## Source, materials and geometry budget

The source is `assets/authoring/environments/passage_house_courtyard.blend`, registered
as a scaffold, never an adopted source regeneration. Its SHA256 is
`563d9c86bbe5685f77bc41d4aa15dc17fd0be0d83c52f76e6bb4883f844b7714`. Its packed Walker reference and procedural materials require no external
image download. The three original CC0 files and curated library are hashed in
`tools/blender/vendor-library/provenance.json`, including authors, URLs, listing hash,
requirements and retrieval times. The named-material loader disables automatic scripts.
No preference was changed and no asset was published. Project material adaptations
are copied datablocks in the scene, separate from upstream originals.

The composition uses limewash, terracotta, timber, restrained iron details, a tiled
wash basin and covered lodging entrance. Grass is omitted. Detailed windows/shutters,
door panels and trim stay editable in TH_SOURCE as `sr_bake_role=source`; four simple
receiver cards supply eight runtime triangles. Massing, roof edges, posts and paving
retain geometry. This source/receiver contract is reusable in the exterior EEVEE
exporter, rejects unknown roles, and rejects unsupported separate-role Cycles exports.
The new authoring brief makes baking shallow detail the default for future scenes.

Matched source comparison, same 1024 atlas, EEVEE 0 EV, authored lights, supersample 1,
no companion/probe lights:

| Measure | Full geometry control | Baked detail candidate |
|---|---:|---:|
| Triangles | 1,958 | 1,522 |
| Vertices | 1,268 | 984 |
| OBJ bytes | 174,236 | 132,082 |
| Atlas PNG bytes | 824,175 | 812,946 |
| Package bytes, exporter statistic | 999,003 | 945,620 |
| Rasterized occupied UV pixels | 89.626% | 90.762% |

The candidate removes 436 triangles (22.3%). Rasterized occupancy measures polygon
coverage at 1024², including shared borders; it is not texture usefulness. Native
world-frame mean absolute channel differences range from 0.715 to 2.536 /255; the
whole frame includes unchanged regions, so those numbers are not a substitute for
looking at doors/windows. Both versions' actual native frames are retained for review.

Full export wall time was 27.7 s on the first final export and 27.4 s on its repeat,
recorded through time-step.js. Each starts a fresh Blender process; the repeat can
benefit from machine caches. No cache flush or GPU cold-reset was claimed. Source review
uses the 64-sample review profile after cheaper draft iterations. Export leaves the
source file unchanged. `review/measurements.json` records source/package hashes.

## Verification and native review

The final staged G1 passed. Full staged units passed, including 973 courtyard runtime
checks: real movement both directions, monotonic continuous elevation, endpoints,
actual LOAD_MAP command execution, all transfers/return anchors and direct lodging
arrival. The Studio command/history test exercised profile splitting and moving,
undo/redo, and invalid ordering through real editor APIs. It is not a browser gesture
or owner editor acceptance claim.

Floor ray tests passed at all four controls, three intermediate samples and both door
landings. Native source frames project Walker at 48 px height at both widths; the upper
landing shifts feet upward with its physical rise while preserving menu clearance.
The playable compositor frames are 256×240 and 426×240 and include Walker, real menu
band and controls. Door label wall-time animation is allowed to settle before capture.
No golden was recaptured. Source renders are separate from runtime frames.

The existing Project night-sky presentation is visible behind statically baked courtyard
lighting; this candidate does not add a day/night lighting system. Minor affine texture
artifacts remain a visual review concern. Large paving initially produced severe dark
bands under the existing affine shader; depth subdivision in the source geometry
removed the severe bands without changing the map's walk profile or runtime movement.

Checks passed: source-manifest checker; town generator/35 door edges; 34 combined host
source/vendor/town tests; two Node candidate/history/geography tests; 12 receiver/exterior
Blender tests, followed by eight receiver/backend tests after dependency-check additions.
The latter also proves an intentionally unpacked image is rejected. Vendor loading,
source opening/review and export passed with Python socket connections denied inside
Blender and automatic execution disabled. This is a process-level offline check, not
proof that the whole operating system was disconnected. No build fetches assets.

Local staged units reported native Effekseer unavailable: seven effect-render assertions
were not exercised. Tool/runtime proofs remain distinct from owner PLAYED acceptance.
The branch includes the shared render-profile work from PR #1294. Its relative G5 passed;
relative G6 failed during capture readiness (generated inspection pending 65.4 s), so it
provided no candidate-vs-base pixel verdict. Do not describe that run as visual green.

G1 accepted an early candidate arrow direction W, which crashed the native renderer;
the candidate now uses left/away. The reusable validator gap is recorded as
[#1295](https://github.com/JosephSerUSP/Second-Rite/issues/1295), outside this scene's
shipping integration scope.

## Delivery and promotion

The candidate README contains offline staging/play/export/capture commands. The curated
library README explains optional manual Asset Browser registration of its `library/`
subfolder. The canonical exporter receives only a copied candidate Project. CI now runs
its G1/units and the new library/receiver/profile checks. The PR is a review candidate;
promotion must update the owning generator or authored-map authority after owner review.

Agent-Signature:
  platform: Codex desktop
  model: platform-selected/unknown
  role: implementation
  task: "Offline materials and Passage House courtyard candidate with baked surface detail"
  base: 111618a2d65566ecfd6231044167056604851cfb
