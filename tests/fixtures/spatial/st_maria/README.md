# St. Maria Praca

The captured, committed `st_maria_praca_modelled.blend` is source evidence for
the exported environment. Its SHA-256, render OBJ, collision OBJ, environment
metadata and map 17 JSON are recorded in `../provenance.json`. The adopted blend
is never regenerated or mutated. Dirty town work is not used as this snapshot.

Geometry owns the exported mesh/collision. The real runtime OBJ parser converts
its Y-up transport coordinates to existing Z-up world coordinates once. The
fixture derives `lane_surface.center` from the collision bounds; this geometry
feature is independent of Event proxies and `TH_ANCHORS` names. It is a useful
surface reference, not a claim that a named socket was already authored in the
blend. The collision vertices remain inspectable in `../runtime-evidence.json`.

Map 17 owns the Child Event at `[7.8, 12.717, 0]`, its behavior, transfer logic,
traversal policy and camera. The selected physical surface center is approximately
`[7.8, 11.8495, 0]`. Both are in the same world frame. Exported anchors are NOT
imported as Event authorities. `gameplay.json` retains map-owned transfer and
camera evidence outside the resolved physical scene.

A Blender proxy would be reconstructed from Event identity and `worldPosition`
in map JSON whenever reopened. An editor move would transactionally update that
same JSON field, with revision/conflict detection, as Studio would. Proxy
deletion would delete editor state only. That integration is documented here,
not implemented or claimed as tested.

This snapshot contains older transfer Events at Z=-1.5 while the selected Child
and collision top are at Z=0. The spike preserves this evidence; it does not
repair authored positions or claim current town playability. A binary source
hash plus exported products is provenance, not proof of a fresh matching Blender
export. Re-export/visual acceptance is deliberately outside this experiment.
