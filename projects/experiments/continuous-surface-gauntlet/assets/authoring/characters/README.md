# Gauntlet character source

`surveyor.spec.json` is the Project's character recipe, adopted from
`chara-compiler`'s `animagrid_girl_skinned` catalog preset. Its parts, painted UVs,
materials and rig are authored by the existing compiler library, not recreated
by this experiment. `surveyor.build.json` records the compiler revision, recipe,
library hashes, source animation hash and build report. The authored animation
source is the owner's Rio `.blend`, read without saving, through the compiler's
Mixamo retargeter. The older AnimaGrid `idle` clip is static and is not used.

Rebuild through the external tool:

```powershell
python tools/characters/build_gauntlet_character.py --compiler V:/Projects/tools/chara-compiler
```

It leaves `.blend` intermediates, generic GLB and runtime products under
`out/continuous-character/rebuild/`. It never modifies the compiler, its library,
the source `.blend`, or another game Project. Review that output before adopting
the GLB and build record here and the runtime products under
`assets/characters/surveyor/`. These generated `.blend` files are compiler caches;
they are not adopted environment/item sources.

The committed GLB is a portable compiler product, not a second character recipe.
It lets CI verify the runtime conversion without access to private drives or
Blender. The conversion preserves hierarchy, inverse binds, four deform weights,
authored UV0, material-slot identity and LINEAR/STEP TRS tracks. Unsupported input
fails instead of approximating it. Additional UV_DEV layers remain in the GLB.

```powershell
python tools/characters/compile_character.py projects/experiments/continuous-surface-gauntlet/assets/authoring/characters/surveyor.glb --out projects/experiments/continuous-surface-gauntlet/assets/characters/surveyor --check
```

The pure Lua skin consumer evaluates quaternions and hierarchy once, then emits
ordinary world triangle groups through the existing shader, depth buffer and
streaming mesh pool. Placement uses the shared Model Instance transform. Studio
receives the same Lua-resolved geometry in its Map renderable bundle; it does
not parse GLB or perform a second animation evaluation. Its authoring preview is
a fixed idle sample, while Test Play uses runtime animation.

`traversal.actorAppearance` selects the Project asset, world height and stride.
Idle uses the presentation clock. Walk phase follows resolved travel distance,
so blocked input returns to idle. Heading and foot position come from the
existing neutral traversal pose, including the single door-pose decoration.
No gameplay state is reconstructed or changed by posing.

This is one experimental player appearance. NPC animation authoring, additional
actions, blends and a shipping creature-roster conversion are outside this slice.
