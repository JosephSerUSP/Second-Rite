# Cortico background topology candidate

The first candidate used disconnected opaque silhouette shapes. That direction
is rejected. This replacement is a source-derived full-model composition: it
duplicates the adopted Cortico lodging, padaria, shrine and facade modules into
a coherent deeper town row, including their actual walls, roofs, openings,
materials and proportions. It also extends the source ground as a real volume.

The output is still a candidate. It must be explicitly imported by the pilot
owner and flattened through the existing exterior exporter; it is not runtime
proof and it does not alter the adopted source or game.

## Build and review

From the repository root, with Blender 5.1.2:

    "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" --background --factory-startup --python tools/blender/recipes/distant_scenery.py -- --source C:\Users\josep\.codex\worktrees\6d7d\Hichaukitoden\projects\hichaukitoden-game\assets\authoring\environments\st_maria_cortico.blend --out-dir out/cortico-background-topology

The source is opened read-only. The command writes a source-derived library,
scratch study blend, west/centre/east 426x240 renders, and a provenance
manifest under out/cortico-background-topology/. The review clone uses the
canon runtime pitch -17.5 degrees as Blender +17.5 for this camera basis,
preserves the adopted eye/lens, and uses only a local principal-point shift to
keep the source composition readable.

## Topology contract

- BACKGROUND_TOPOLOGY_CANDIDATE is a top-level review collection. Its review
  camera and organizational empties deliberately stay outside TH_SOURCE.
- Every building module is explicit mesh topology copied from named adopted
  source objects; there are no silhouette profiles, alpha cards, fullscreen
  planes, or synthesized background colors.
- Modules occupy X 22..34, behind the adopted primary architecture, and the
  real ground volume covers Y -32..32.
- Candidate meshes are tagged sr_representation=full_model,
  sr_background_topology=true, and sr_export=false until owner review.
- Candidate objects are not collision, anchors, preview actors, or gameplay
  data. The study actor is excluded from export.

## Owner integration and flattening

1. Append BACKGROUND_TOPOLOGY_CANDIDATE from the library. Link or move only
   its accepted mesh objects into TH_SOURCE, retaining authored world
   transforms; leave the review camera and organizational empties outside
   TH_SOURCE because scene preflight accepts only renderable source types there.
2. Review the source camera at west, centre and east positions. Save the
   adopted source only as an explicit owner action.
3. On accepted building and ground meshes only, set sr_export=true; keep them
   outside TH_COLLISION, TH_ANCHORS, TH_PREVIEW_ACTORS and gameplay data.
4. Run the pilot's scene preflight and export_exterior_environment.py. The
   exporter should copy the real TH_SOURCE modules into TH_RENDER, join them,
   UV them and bake their source appearance into the runtime atlas. Inspect
   the export log for skipped objects and inspect the emitted OBJ/MTL and atlas;
   do not infer flattening from the manifest alone.
5. Validate the resulting package in Classic and Wide at west/centre/east,
   with visible actor, ground, existing traversal, door and NPC interaction.

No camera, runtime renderer, collision, map data or global sky behavior is
changed by this candidate. If the pilot's bake exposes an atlas-transfer or
camera-space defect, that is a separate owner-supervised issue rather than a
reason to reintroduce flattened random shapes.
