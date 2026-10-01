# Passage House courtyard refinement (2026-10-01)

Revision 11 is a staged candidate built from connected room volumes and rich architectural assemblies. The preceding revision 8 was rejected by the owner as weak in geometry, textures and lighting; its frames and measurements remain under `review/before-assemblies/`. Shipping topology and adopted sources remain untouched.

## Architecture and baking

Closed sleeping, arrival and service volumes now share actual internal portals, foundations and coherent roofs. Window apertures contain recessed glazing, frame rebates, pane divisions, mouldings, sill and hardware. Detailed two-sided louvres rotate around real hinge pivots at partially open angles; simpler shutter targets receive their bake. Curved masonry, a glazed fanlight and a timber door define the covered entrance. Complex roof tiles remain source geometry. Neutral front, oblique, side and rear module studies, plus a roof-cut room plan, are recorded separately from runtime evidence.

The editable scene has 191,648 evaluated beauty triangles across its complete source, including off-range buildings. The runtime export has 3,541 triangles, 2,618 vertices and a 1024 atlas. These populations differ; their ratio is not a pure same-surface decimation ratio. Rasterized UV coverage is 59.307%, an allocation measurement rather than a quality score. Reported package size is 478,521 bytes. The final offline export took 106.9 seconds in a fresh Blender process; no warm-cache measurement is claimed.

Source SHA-256: `2484856271cfba2b321515a7bf674f2aa5a728efaaf52844e93a6f8e3094c7ec`. Per-file and frame hashes are in the candidate `review/measurements.json`. Module studies were made from revision 10, whose window and sleeping-wing assemblies are unchanged; that source hash is explicitly retained in the measurements.

EEVEE stays at 0 EV. Lighting comes from the authored dusk sun, sky and lamps associated with visible lantern fixtures. Automatic lighting shims remain disabled. Grass is omitted. Immutable upstream materials, relative offline dependencies and global preferences remain unchanged.

## Exit and camera correction

The Cortico return had an anchor half a metre inside the lane, so it appeared as an Up door against the sleeping-wing facade. All transfers also used a wall-door camera approach. Its anchor now sits on the lower bound, y=0, and the court wall has a visible opening aligned with the lane. The shared transition accepts a no-approach mode for edge exits: it keeps the fade and executes the event once under black without moving toward a wall. Interior-door behavior is preserved.

Camera tracking is limited to -72/+72 canonical pixels. The player continues to both bounds while the camera stops following near the ends. Pitch, lens, scale, elevation profile and datum relationships remain intact. Native Classic and Wide captures cover seven positions, including exact bounds. The lower-bound source review projects Walker's feet to x=35.428, y=128.000 and retains the 48-pixel height.

Blender formerly translated the camera to each player position, unlike runtime projection-window tracking. A LOVE helper now resolves bounded-lane poses through the actual runtime camera calibration; source review and atlas projection consume those serialized poses. Stale authored camera records fail loudly. Wide uses the runtime's canonical center, not an assumed centered wider viewport.

## Verification and limits

Staged G1 passed. The clean full staged unit suite passed, including 1,455 courtyard assertions for traversal, slope endpoints, reciprocal transfers, arrival datums, edge-exit classification and camera limits. Shared transition tests verify no depth approach throughout the edge fade and exactly one covered callback. Seven native Effekseer world-effect assertions remain unavailable.

Source/profile review passed controls, intermediate samples and both landings. Source-manifest, immutable vendor hashes and two Node profile/history/geography checks passed. Final focused Blender regression results are recorded in measurements. Source generation and export ran through network-denying `offline_blender.py`; this is process-level denial, not a whole-machine firewall claim. No goldens were recaptured.

The capture hook is now installed temporarily and restored after native rendering, so unit stages remain free of that development dependency. Inspection of the earlier failing log exposed a separate false-green boundary-suite defect; #1299 records the runner follow-up. #1298 records stale exterior-authoring brief guidance. Neither expands this candidate's shipping scope.

Map 32 remains candidate-only. The profile is `(0,0), (2,0), (8,0.30), (12,0.30)`. Cortico's existing doorway identity and location, and direct introductory arrival into map 25, remain preserved. The courtyard datum is -0.34378736413887334 m and lodging datum -0.04378736413887335 m relative to Cortico. Draft PR #1296 remains stacked on #1294. Native capture and tooling proof are distinct from owner visual/traversal and PLAYED acceptance; promotion must update the owning generator or authored-map authority.

Agent-Signature:
  platform: Codex desktop
  model: platform-selected/unknown
  role: implementation
  task: "PR #1296 architectural courtyard and edge-exit correction"
  base: b8c51316
