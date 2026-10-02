# Passage House pixel corners, near enclosure and Classic camera

Revision 15 remains a scaffold and a staged map 32 candidate. Shipping topology,
map-owned elevation, adopted sources and global Blender preferences are unchanged.
Owner visual review and PLAYED acceptance remain pending.

## Changes

UV chart boundaries now align inward to **pixel corners** (`n / atlasSize`),
replacing half-pixel centres. Complete charts retain their original coordinates
when quantization collapses/flips a triangle, leaves their bounding box or
introduces shared texels. The 1024 atlas aligns 657 charts and preserves 514 unsafe
charts; no new shared-texel pairs. Four-pixel bake dilation remains in use.
This corrects the grid convention; it does not certify every window bake surface.

Veranda rafters follow the roof pitch and braces terminate below the roof.
Evaluated support vertices must stay at least 15 mm below its underside.
The scattered coping blocks are removed. A broad camera-side masonry boundary,
coping and returns enclose the court and occupy the lower native frame, outside
the traversal lane. The owner's judgment of its visual interest remains open.

A shared viewport defect applied the Classic authored camera centre (128) directly
in Wide. The camera scale already used 256 logical pixels, but the missing surface
translation shifted its framing 85 pixels left. Both mesh and plate camera paths
now translate authored composition coordinates through `surface.compositionToRender`.
Wide centres the same Classic frame at 213; Blender camera records use that same
adapter. No width-dependent zoom, tracking or gameplay geometry was added.

## Evidence

Source SHA256: `96155a7ec7609a2526c445ea037a1f105b8fadb735e50371b5774b869c7162a0`.
Evaluated source: 209,568 triangles; exported view envelope: 5,655 triangles.
Atlas: 1024 square, 87.8907203674% rasterized UV occupancy.
Cycles 64 samples, chart-isolated OIDN FAST, 0 EV.
Fresh-worker first/repeat whole processes: 53.3066 / 52.8614 seconds, measured rather
than capped; cache coldness is not certified. Mesh/collision bytes match; 21 atlas
pixels differ by at most one byte. Source/export run with Python networking denied.

Review files live under the candidate's `review/pixel-corners/`: fourteen native
Classic/Wide frames, fifteen independent source-clay/runtime-clay/atlas views,
repeat evidence and Classic/Wide crop comparison. In the compared upper world band,
Classic and Wide's central crop differ at 1–4 pixels per frame; no byte-parity claim.

G1, staged units, source registry, town checks, two candidate editor/geography tests,
19 Blender exporter/profile tests and three recipe/assembly tests pass. Seven native
Effekseer assertions remain unavailable. Source parity and support-clearance checks
also pass after regenerating Wide camera records. Presentation surface regression
coverage includes authored off-centre framing at Classic, Wide and portrait widths.

Absolute G5 remains red: ten battle/title reference mismatches at each width also
reproduce with HEAD's previous viewport in the same staged content. Classic/Wide
crop invariant passes. Baseline actual-image comparisons are recorded separately;
no goldens were recaptured. This is not an absolute-green or owner-acceptance claim.

Issue #1301 remains open for narrow window/head-strip bake correspondence and wider
render-budget evidence. This revision has not eliminated every dark strip in windows.
