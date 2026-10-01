# Passage House portal correspondence — 2026-10-01

The dark fanlight was partly a geometry/bake error. Its receiver faced into the hall and overlapped the timber header; reveal receivers extended behind the jambs. The detailed jambs and header also lacked exported structural geometry. More samples or an exposure offset would not repair these conditions.

Revision 12 turns the fanlight outward, clips its lower edge above the header, closes the reveal returns and retains simple box receivers for the timber frame. Rich bevel detail remains in the source. A reusable explicit `sr_bake_preserve` property protects structural receiver faces from enclosure culling without treating them as open sheets. Closed source mesh winding is repaired by the shared geometry helper when the scaffold is constructed.

The exporter now accepts an authored `--bake-bindings` contract. Its preflight samples four points per bound front-facing triangle against the batched source and reports missing or wrong source hits before baking. Seven portal bindings produced 112 samples with zero missing/wrong hits. Tests deliberately move a receiver away and bind it to the wrong source: both fail with named diagnostics. This is sampled geometric evidence for flat receivers, not exhaustive texel correspondence or visual acceptance. Smooth bound faces are rejected by this diagnostic.

A separate real Cycles control found identical irradiance with receiver shadow visibility enabled and disabled (mean 0.9938074561650865). No receiver-shadow workaround or lighting/exposure change was adopted. The current detailed-source view also shows shadow in the passage recess; the native result remains darker and requires visual review. Existing textures and overall art still need owner judgment.

## Evidence and cost

Candidate evidence lives under `review/portal-correction/`: the previous package/native frames, current Classic/Wide frames with Walker and menu, detailed-source before/after views, and sampled correspondence reports. Main `review/runtime/` now contains current frames. Historical module and whole-source studies retain their original provenance.

Current scaffold SHA-256: `74100329fb6478916e028173fac4805c4f815adc9138dc10fa31a709dafa753e`. It was intentionally regenerated as revision 12; the registered authority remains scaffold. Previous revision 11 source SHA-256 was `2484856271cfba2b321515a7bf674f2aa5a728efaaf52844e93a6f8e3094c7ec` and is retained in Git history. Adopted sources were not edited.

Current package: 3,727 triangles, 2,731 vertices, 1024-square atlas, rasterized UV occupancy 92.04%. This adds 52 triangles over revision 11. Whole-process production export took 64.8 seconds with Cycles 128 samples, OptiX and neutral 0 EV. No revision 12 warm repeat was measured; earlier revision 11 first/repeat timings were 66.6/64.9 seconds. Frame preview timing and bake/export timing are different measurements.

## Verification and boundary

G1 returned `VALIDATE OK`; staged units returned `ALL UNIT TESTS OK`, with seven native Effekseer world-effect assertions unavailable. All 25 focused Blender tests passed, including geometry preservation, recipe/source parity, correspondence negative controls and selected-to-active baking. Source-manifest checks passed. Town checks verified ten generated maps and 35 door edges/arrival anchors. Current source build, export and source inspection used the Python-network-denying Blender wrapper; this does not disable machine networking.

Map 32 remains staged only. Shipping topology, the authored elevation profile, camera calibration/tracking and lighting were not changed by this correction. No goldens were recaptured. Issue #1301 remains open for broader surface/angle review and remaining entrance appearance. These checks do not constitute owner PLAYED acceptance or permission to promote the candidate.
