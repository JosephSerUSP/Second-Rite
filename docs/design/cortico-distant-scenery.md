# Cortico background billboard candidate

The background is authored as real source topology, but it is not shipped as a
row of runtime houses. The recipe duplicates the adopted Cortico lodging,
padaria, shrine and facade modules into a coherent deeper town row, renders
that topology through the canon pitched camera, and places the result on a
world-space textured plane. This gives the map architectural continuity and
depth without competing with the interactive action plane.

This is deliberately different from actor/event sprites. The background plane
is world geometry and responds to camera pitch. Actor/event sprites use the
runtime camera-up billboard path, which keeps their feet stable and does not
keystone them.

The output is still a candidate. It must be explicitly imported by the pilot
owner and reviewed as a candidate; it is not runtime proof and it does not
alter the adopted source or game.

## Build and review

From the repository root, with Blender 5.1.2:

    "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" --background --factory-startup --python tools/blender/recipes/distant_scenery.py -- --source C:\Users\josep\.codex\worktrees\6d7d\Hichaukitoden\projects\hichaukitoden-game\assets\authoring\environments\st_maria_cortico.blend --out-dir out/cortico-background-billboard

The source is opened read-only. The command writes a topology-authoring blend,
an 866x240 rendered billboard texture, a scratch study blend with the
world-space card and floor bridge, west/centre/east 426x240 renders, and a
provenance manifest. The review camera uses the canon runtime pitch -17.5
degrees as Blender +17.5 for this camera basis and preserves the adopted
eye/lens.

## Presentation contract

- BACKGROUND_TOPOLOGY_CANDIDATE is a top-level review collection. Its review
  camera and organizational empties deliberately stay outside TH_SOURCE.
- Every building module is explicit source topology copied from named adopted
  source objects; there are no random silhouette profiles or synthetic shape
  scatter.
- Modules occupy X 22..34, behind the adopted primary architecture, and the
  source-derived render covers Y -32..32.
- The runtime-facing candidate is a world-space textured billboard at X=36.0;
  it is not a camera-space fullscreen card and is tagged
  `sr_camera_space=false` and `sr_reacts_to_pitch=true`.
- The grounded floor bridge runs from X=-13.0 through X=36.05 at Z=0. It
  reaches the bottom frame intersection, the action plane and the billboard
  base, so the floor does not stop before the distant layer.
- Candidate objects are not collision, anchors, preview actors or gameplay
  data. The study actor is excluded from the background render.

## Owner review and integration

1. Review the topology-authoring blend and the west/centre/east card renders.
2. If accepted, integrate the world-space billboard and floor bridge into the
   pilot's render source while keeping them out of collision, anchors, preview
   actors and gameplay data. Do not ship the authoring topology as a runtime
   house row.
3. Export the package through the pilot's canonical environment exporter and
   inspect the emitted geometry, material and texture. Do not infer correct
   flattening from metadata alone.
4. Validate the resulting package in Classic and Wide with visible actor,
   continuous floor, traversal, door and NPC interaction evidence.

No adopted source, camera, runtime renderer, collision, map data or global sky
behavior is changed by this candidate. If integration exposes an exporter or
camera-space defect, keep it separate from the art decision; the answer is not
to reintroduce flattened random shapes.
