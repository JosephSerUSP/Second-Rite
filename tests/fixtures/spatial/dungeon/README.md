# Procedural dungeon

Source: the real Second Gate floor 2 dimensions, anchors and generation profile,
plus system dungeon policy, captured at the revision in `../provenance.json`.
The fixture enables generated openings and omits campaign Event population,
recruits and tileset art injection. `exploration.generateDungeon` performs the
carving; no JavaScript dungeon generator substitutes for it.

Required survivors: all 17x17 tokens, room and corridor records, all cell/edge
identities, authored and generated openings, and connected open topology.
The compact 1,880-byte input remains the authoring source; expanded bodies and
topology are derived inspection products. `o` is a structural opening, not an
authoritative door-state or traversal-policy field.

`entry_room.center` is a physical semantic feature derived from the first
explicit authored anchor room. The JSON-owned `entry_guide` Event references it
with an offset. Its identity/placement expression stays in `gameplay.json`.
Changing that offset does not modify the physical scene. Moving the structural
feature changes the joined placement without rewriting the Event source.

Cell/edge IDs are coordinate-addressed; the entry feature has an explicit
semantic ID. Stability is claimed for the same source, seed and generator, not
for arbitrary room reordering, changed seeds, or structural redesigns. Existing
generator Event behavior remains unchanged in production.
