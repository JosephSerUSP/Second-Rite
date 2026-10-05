# Consumable model rework — 2026-10-05

Six legacy consumables from the 149–158 batch were re-authored from scratch rather than edited from the old shared bottle/profile generator:

- **Potion** — squat smoked-glass apothecary bottle with wax closure and cloth neck band.
- **Hi-Potion** — taller medicine phial with a ritual-gold structural harness and tiered stopper.
- **X-Potion** — crystalline biconic reliquary with an emphatic gold equator and foot.
- **Mega-Potion** — broad canteen/grenade-like vessel with belt, side fittings, and hanging tag.
- **Healing Water** — clear pilgrim-gourd/flask with cloth binding and dark-wood stopper.
- **Ether** — narrow ampoule/retort with gold calibration rings, cloth marker, and crystal needle cap.

## Intent

The previous batch differentiated most consumables by changing one rotational profile, material, side count, and optional bands/tags. This pass instead gives each item a recognisable object grammar and silhouette while preserving the existing low-poly semantic material vocabulary.

## Runtime contract

- Existing item paths are preserved; `data/items.json` is untouched.
- The same OBJ bytes are mirrored into the game Project and editor fixture.
- Every face carries UV indices.
- Only existing materials from `item_batch_149_158.mtl` are used.
- Geometry is centred and non-degenerate.
- Pairwise silhouette comparison among these six peaks at approximately **0.780 IoU**, below the corpus gate's **0.85** limit for new work.

## Source-authority note

These six belong to the legacy batch that predates per-item adopted Blender sources. This pass deliberately improves the runtime meshes now; it does **not** manufacture placeholder `.blend` authority without a Blender-backed authoring session. A later source migration should preserve these silhouettes and material decisions rather than reverting to the old batch bottle grammar.
