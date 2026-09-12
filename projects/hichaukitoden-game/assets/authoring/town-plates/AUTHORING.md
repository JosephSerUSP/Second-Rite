# St. Maria plate authoring protocol

This directory is the durable handoff for generated town plates. Map data and
the projected camera guide own geometry. The live modelled-screen sheet owns
the general visual language. Generated output never becomes a reference input.

Generated images are diagnostic or candidate outputs only. They must not be
used as positive style, camera, geometry, composition, or location references
for later generations. The only visual reference set is the tagged in-house
live capture of modelled maps 17, 28, and 29. The spatial reference is rendered
from authored Blender geometry through the calibrated game camera.

The Port experiments established one important limit: asking a single image
generation to solve style, location storytelling, five trigger meanings,
projected geometry, horizon placement, weather, and cleanup at once produces
plausible pictures whose gameplay meaning is unreliable. More iterations do
not repair that ambiguity. Authoring is therefore staged, and a failed early
stage stops the batch.

## Authoring packet

Run the town consistency check before deriving any image:

```powershell
python tools/towngen/check_town.py
```

The primary model input is a Blender spatial scaffold rendered through the
calibrated perspective camera. It contains real floor depth, continuous
projected rulers, the actor scale, and one universal triangular-prism map pin
at each trigger origin. Every transition uses the same shape: blue means an
edge exit, red means a door, yellow means an upward route, and magenta marks
actor scale. A pin's point marks where interaction begins; its volume never
describes the destination, route, building, stair, arch, ship, or finished
silhouette. A compact legend lives in the UI-covered bottom strip.

The 2D shape-neutral spatial fields remain useful projection audits and a
fallback for diagnosing anchor math. They are not the preferred generation
input because raster corridors convey less depth than projected Blender forms.

```powershell
python tools/asset-gen/make_town_position_maps.py `
  --output out/towngen/map-derived-spatial-fields `
  --maps all --scale 1 --annotate --spatial-fields
```

`--scale 1` is intentional. The audit is drawn directly at final plate
resolution, so no resampling can blur its construction lines or move a trigger.
The annotated `XX-spatial-field.png` and text-free
`XX-spatial-field-clean.png` are review counterparts.

Blender does not require sculpting a location. A reusable recipe creates only
the shared camera-aware scaffold and generic semantic shapes from map data; a
map-specific recipe declares the event classes and their extents. Camera
background images remain viewport aids only: they are never projected onto
floor or wall surfaces or baked into the spatial render.

For the current Port proof, `img2imgguide.blend` is the owner-authored baseline
and is never overwritten by the builder. The builder reads the generated Port
layout for anchor positions, preserves the baseline camera, and writes a
separate, hand-editable source document:

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.1\blender.exe' `
  --background projects/hichaukitoden-game/assets/authoring/environments/img2imgguide.blend `
  --python tools/towngen/build_port_blender_reference.py -- `
  --output projects/hichaukitoden-game/assets/authoring/environments/st_maria_port_spatial_reference.blend `
  --render out/towngen/port/blender-spatial-reference/port-spatial-final-clean-1065x240.png `
  --style-reference out/towngen/style-reference/style-reference.png `
  --layout out/towngen/blockouts-reconciled/port.json

python tools/towngen/review_candidates.py derive-working-guide `
  --source out/towngen/port/blender-spatial-reference/port-spatial-final-clean-1065x240.png `
  --out out/towngen/port/blender-spatial-reference/port-spatial-working-clean-2160x720.png

python tools/towngen/review_candidates.py annotate-spatial `
  --screen port `
  --source out/towngen/port/blender-spatial-reference/port-spatial-working-clean-2160x720.png `
  --out out/towngen/port/blender-spatial-reference/port-spatial-working-semantic-2160x720.png
```

The coherent 1065x240 composition is authored and rendered first. Only after
that frame is complete does tooling horizontally compress that raster to the
model's 3:1 landscape canvas (2160x720). Labels are applied only after this
transform. The model therefore sees pre-distorted geometry without Blender
exposing additional foreground or changing the camera framing. Its complete
3:1 generated frame is fitted once back to 1065x240. Never render a second
camera aspect or assemble the plate from separately projected crops.

The clean full-frame render and annotated 1065x240 preview are for human
projection inspection only. The only two visual inputs to generation are the
derived 2160x720 annotated semantic composition guide and the tagged in-house
reference screenshots. No clean guide, final-frame preview, prior candidate,
AI-generated precedent, or additional style image is supplied.
The builder refuses to overwrite its output unless `--force` is explicitly
given. Once the owner hand-edits that output, it is source authority and must
not be regenerated.

## Generation sequence

Start with one semantic proof, not a weather batch. Give the model two images
with one role each: image 1 is the tagged in-house map 17/28/29 live-capture
sheet; image 2 is the pre-distorted, annotated 2160x720 Blender event-placement
guide. Do not explain its symbols, camera, geometry, or transform in the prompt.
Use only: asset type, a brief town description, a brief screen description, and
the two role sentences, “Image 1 is the aesthetic reference. Image 2 is where
ingame events are placed.” First-pass scenes include inhabitants; removing
people is a later selected-candidate edit.

The semantic proof advances only when every authored transition:

- exists as a distinct visual affordance;
- is readable as the intended kind of route;
- reaches the actor ground rather than floating in depth;
- remains visible above the persistent UI band;
- is centred within 8 final plate pixels of its authored anchor;
- participates in one coherent projected space across the scrolling plate.

The same review also checks the authored horizon and actor-ground rows, actor
scale, uncluttered foreground around the live sprite, location plausibility,
and absence of guide marks. Passing dimensions alone is not semantic success.

Only after one semantic proof passes should the workflow spend three independent
ImageGen calls on aesthetic or weather variation. Each output receives the
source-guide overlay, gameplay-anchor overlay, Classic and Wide west/centre/east
windows, and the affordance review before a winner is recommended.

If a strong candidate misses one or two local affordances, edit that candidate
with its semantic edit guide. Image 1 remains the sole style, material, weather,
and location-vocabulary authority; image 2 continues to own camera projection,
keystoning, floor geometry, transition placement, and vertical framing. A
candidate whose perspective disagrees with image 2 cannot be repaired by a
local edit; it is a new generation and must repeat semantic review. The edit
prompt names only local architectural changes and explicitly locks everything
else.

## Image-led trigger remap

Moving gameplay to match art is a fallback, not an automatic correction. It is
available only when the image already contains every required route, each route
is readable and accessible from the actor ground, and the whole scene is
perspective-coherent. Missing stairs, blocked walkways, or decorative doors do
not become valid merely by moving trigger coordinates.

Enter each observed center in `precedent.json` under
`review.observedPlateX`, then generate a proposal:

```powershell
python tools/towngen/review_candidates.py remap-proposal `
  --screen port `
  --review projects/hichaukitoden-game/assets/authoring/town-plates/precedents/port/precedent.json `
  --out out/towngen/port/image-led-remap-proposal.json
```

The command checks composition bounds, left-to-right order, and trigger-radius
spacing and reports the corresponding runtime and legacy authoring coordinates.
It never edits `build_town.py` or map JSON. Any remap requires owner approval,
must preserve destinations and arrival topology, and is followed by rebuilding
the town and regenerating all affected guides.

## Selection, cleanup, and promotion

After owner selection, perform the focused people-removal edit and reject any
change to architecture, openings, lighting, framing, or perspective. Normalize
the complete frame once to the exact plate dimensions; never stitch independent
cameras. Run the plate checker, inspect all gameplay windows and overlays, then
run `check_town.py` and G1 before promotion. Absolute G5 references remain
owner-signed and are not recaptured by this workflow.

`staging.json` records current status, candidates, prompts, references, and
selection. It is the status record; this protocol describes the invariant
process.
