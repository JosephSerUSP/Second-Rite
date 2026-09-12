# Nominally 2D room in XYZ

The fixture has ground, an elevated platform, and a platform at the same height
but a different Y depth. All are ordinary 3D boxes. Exit and trigger features
are bounded volumes. The JSON-owned guide Event is placed in XYZ; gameplay
constrains motion to Y=0. Progression (`double_jump`), trigger behavior and room
destination remain exclusively in `gameplay.json`.

The camera fixture uses the existing `rpg_ortho` WorldCamera profile, resolved by
actual LÖVE code: orthographic, 45-degree pitch, projection scale
`[sqrt(0.5), 1]`. This is the already-tested anisotropic RPG correction from
`tests/test_chest_3d.lua`, not a newly invented vertical world-coordinate scale.
It demonstrates a stylized oblique 2.5D room; it does not claim to reproduce a
specific side-on metroidvania composition. Orthographic policy is a view input,
never physical-scene authority. No alternate XY map ontology is introduced.

The experiment verifies numerical spatial/presentation separation, not a rendered
gameplay traversal or collision-controller implementation.
