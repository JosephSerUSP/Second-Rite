# Item model fabrication batch: items 63–72

Date: 2026-08-09

## Scope

This batch continues directly after items 53–62 and gives the next ten unmodeled items deterministic low-poly runtime meshes:

| ID | Item | Model | Design cue |
|---:|---|---|---|
| 63 | Silver Rod | `assets/models/items/silver_rod.obj` | slim octagonal metal rod, gold collar, compact crystal head |
| 64 | Mage Staff | `assets/models/items/mage_staff.obj` | crooked forked wooden staff enclosing a crystal |
| 65 | Sage Staff | `assets/models/items/sage_staff.obj` | symmetric ceremonial branching crown and larger crystal |
| 66 | Ether Staff | `assets/models/items/ether_staff.obj` | iron shaft with an open ritual-gold halo around a suspended crystal |
| 67 | War Staff | `assets/models/items/war_staff.obj` | blunt quarterstaff with iron cross-head, spikes and cloth binding |
| 68 | Rune Knife | `assets/models/items/rune_knife.obj` | short knife with gold furniture and three raised crystal runes |
| 69 | Spell Sword | `assets/models/items/spell_sword.obj` | balanced sword with ritual-gold fuller and crystal pommel |
| 70 | Glass Blade | `assets/models/items/glass_blade.obj` | smoked-glass blade reinforced by a dark metal spine |
| 71 | Comet Edge | `assets/models/items/comet_edge.obj` | long slightly curved artifact blade with comet-like crystal nodes |
| 72 | Flame Saber | `assets/models/items/flame_saber.obj` | curved saber with a subdued wax/crystal flame ridge |

The deterministic builder is `tools/asset-production/build_item_models_63_72.py`. In a normal checkout it writes the OBJ files plus `item_batch_63_72.mtl`, validates each mesh, and assigns the ten model paths in `data/items.json`. It refuses to overwrite a different pre-existing assignment.

## Creative process

The first four items are a magic-weapon tier progression rather than four recolored sticks. Silver Rod is deliberately compact and manufactured. Mage Staff becomes irregular and organic. Sage Staff regains symmetry as a more deliberate ceremonial object. Ether Staff moves into unmistakably supernatural construction with an open halo and suspended crystal, so the tier-five silhouette reads before its material does.

The remaining six establish a physical/magical weapon vocabulary. War Staff is blunt and practical; Rune Knife concentrates magical detail into a tiny blade; Spell Sword integrates that vocabulary into a conventional sword. Glass Blade changes the material premise, Comet Edge pushes the silhouette into an artifact-like asymmetry, and Flame Saber uses a curved profile plus a restrained flame ridge rather than relying on a bright emissive effect the runtime material format does not promise.

All geometry is intentionally coarse and spends triangles on silhouette, negative space, and material boundaries. The models are designed for the small rotating item viewer and Second Rite's PSX-oriented presentation rather than close-up sculptural inspection.

## Mechanical checks performed

The direct builder completed for all ten models and checked:

- every OBJ contains vertices, triangular faces and the expected `mtllib` declaration;
- every face index is in range and every triangle is non-degenerate;
- every `usemtl` value belongs to the repository semantic material vocabulary used by this batch;
- each mesh is centered to its generated bounds;
- the item-assignment routine only accepts an absent model or the exact expected path;
- a neutral 3D contact-sheet inspection confirmed the tier progression and silhouettes remain distinguishable.

| Item | Vertices | Triangles |
|---|---:|---:|
| Silver Rod | 50 | 84 |
| Mage Staff | 92 | 156 |
| Sage Staff | 98 | 168 |
| Ether Staff | 148 | 252 |
| War Staff | 58 | 96 |
| Rune Knife | 66 | 104 |
| Spell Sword | 58 | 92 |
| Glass Blade | 50 | 80 |
| Comet Edge | 79 | 122 |
| Flame Saber | 71 | 110 |

This execution environment does not provide LÖVE/lovec or Blender, so the repository G1/unit/golden gates and a Blender rebuild were not run here. The generated text assets are re-fetched from the GitHub branch after publishing and compared by Git blob SHA to guard against connector transport corruption.
