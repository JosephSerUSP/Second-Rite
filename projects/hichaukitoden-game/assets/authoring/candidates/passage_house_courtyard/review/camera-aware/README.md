# Camera-aware atlas controls

Common revision 16 scaffold and native Classic logical camera. Complete offline
packages and fourteen native frames each are retained at biases 0, 0.5 and 1.
The selected staged package uses 0.5. Shipping topology is unchanged.

`--atlas-layout view --atlas-view-bias 0` gives uniform world-area density;
`1` follows peak visible area over eleven calibrated lane poses. Hidden islands
retain a density floor, and weighting does not delete geometry. `legacy` remains
a separate historical control, with fixed ground allocation; it is not identical
to the world-uniform endpoint.

The source saves `export_atlas_view_bias=0.5` and `export_atlas_size=1024`.
Omitting those CLI overrides consumes these authored settings. Saved render and
viewport quality are Cycles 64, denoised, 0 EV, Classic 256x240. The atlas is a
separate 1024 bake product. GPU availability/backend selection remains local to
the launching process; global preferences are never saved.

`comparison.json` reports peak-demand area-equivalent density before guarded UV
corner alignment, not directional 1:1 projection. The peak endpoint approaches
one texel per screen pixel in area, but oblique UV anisotropy remains a limitation.
General envelope/expected-demand work remains Issue #877; window correspondence
remains Issue #1301. Lower-frame visual interest still needs owner review.
