# Elevated tactical battlefield

`source.json` is an experimental 6x6 procedural lattice input, not a new shipping
Map format. The adapter emits explicit XYZ site positions at Z=0 and Z=1,
three gap sites, a bridge over one gap, a blocked site, an explicit stair
connection, primitive platforms/steps, and a deployment volume.

`resolved_structure.json` owns inspectable lattice sites and physical adjacency
connections. The common scene contains bodies and features but no tactical
neighbor/cost/jump fields. `gameplay.json` owns deployment selection and the
movement policy. `resolved_moves.json` is calculated by the separate tactical
consumer: blocked/gap sites are excluded, level cardinal neighbors are allowed,
and declared connections permit elevation transitions. Costs depend on the
consumer policy. Increasing `maxStep` permits additional climbs without changing
any spatial output. Removing art does not change legal moves.

This is a tiny test system, not FFT movement implementation. The closed lattice
companion is evidence that source-specific structural capabilities remain useful;
it is not silently normalized into arbitrary mesh raycasts.
