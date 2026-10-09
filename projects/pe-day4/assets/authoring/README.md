# Original starter kit source authority

These are independent copies of the original continuous-surface test kit at
commit `ba412982`. The service-room arrival was subsequently edited directly in
its adopted Blender document to clear the foreground door occlusion and exported
through the same pipeline; native arrival review precedes product adoption.
No original-game art, maps, dialogue, models or animation
data is used. Runtime Project assets are self-contained.

The two adopted Blender documents retain their explicit render/collision,
walkable/obstacle, anchor and lighting collections. Their exported package
provenance pins source and product hashes. Edit the adopted documents directly;
never rebuild them from the old OBJ. Repeated use across four proxy areas does
not imply source-measured room shapes or cameras.

Check sources and lit products:

```text
python tools/blender/environment_sources.py --check --root projects/pe-day4
python projects/experiments/continuous-surface-gauntlet/tools/check_lighting.py --project projects/pe-day4
```

The shared fixture export tool accepts this Project explicitly; it reads these
sources and writes a candidate without altering them:

```text
python tools/blender/run.py projects/experiments/continuous-surface-gauntlet/tools/light_environments.py -- --project projects/pe-day4 --output out/hospital-lighting
```

Review native frames before adopting candidate products. Perspective-correct UVs
are required for baked textures. Geometry owns the visible door anchor and walk
surface; Map Events own the transfer meaning.

Surveyor is an original chara-compiler fixture. Its GLB, build provenance, recipes
and derived runtime JSON are included. It is a temporary traversal silhouette,
not an Aya likeness. Hospital character production must use the same compiler
boundary and retain source/recipe hashes. The private locomotion source remains
outside the repository and is not required to validate the adopted product.
