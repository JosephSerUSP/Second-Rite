# Second Gate town: experimental prerendered branch

This report records the complete implementation path for the experimental
Second Gate town branch. It is intentionally written as an engineering handoff:
the `.blend` scene, the bake contract, the runtime compositor, the verification
steps, and the known compromises are all documented here so the experiment can
be evaluated or replaced without reconstructing the chat history.

## Scope and intended result

The branch turns the supplied Meshy old-stone-village scene into a playable
Second Gate exterior. The church in the middle of the square is the entrance to
the Labyrinth of Thestra. The scene is meant to be bright enough to read as a
town, while retaining authored fog, a sky/ceiling treatment, a player walker,
NPC events, and a doorway into the existing labyrinth map.

This is an experiment, not a claim that the final town renderer is solved. The
chosen presentation is full pre-rendering with live gameplay actors and event
logic composited between depth-derived background and foreground layers.

## Branch and source material

- Branch: `codex/second-gate-town-experimental-20260821`
- Source model: `Meshy_AI_Old_Stone_Village_Squ_0821061722_texture_obj.zip`
- Authoring scene: `projects/hichaukitoden-game/assets/authoring/town/second_gate_town_annotation.blend`
- Exterior data: `projects/hichaukitoden-game/data/maps/16.json`
- Existing interior target: map `2`, reached through the church entrance event
- Optional side-door target: map `17`, the apothecary interior

The source mesh is retained in the project as an authoring/render asset. Its
direct package is approximately 830k triangles and 112 MB for the render OBJ,
which became an important input to the final presentation decision: loading and
drawing it as a live 3D scene was too expensive and too difficult to make match
the intended 2D presentation.

Because that dense fallback OBJ is larger than GitHub's normal 100 MB blob
limit, it is tracked with Git LFS in this experimental branch. The playable
map does not load it; the Blender source scene and the layered prerender cache
are the intended runtime-authoring path. A checkout that needs the fallback
mesh must have Git LFS enabled.

## Authoring contract for Blender

The `.blend` file is the human-editable source of truth for the look of the
town. The bake script deliberately requires these named objects:

| Object | Purpose |
| --- | --- |
| `CAMERA_PLAYER_VIEW` | The authored camera and final lighting/composition authority. |
| `Meshy_Village_Source` | The imported village geometry and materials. |
| `SPAWN_PLAYER` | Player anchor used for scale and placement calibration. |
| `WALKABLE_MAIN` | The bounded walkable lane used to derive the runtime traversal range. |
| `WALKER_SPRITE` | A visible proxy for checking the player’s scale and foot placement. |

The authored lane is horizontal in the Blender scene. The runtime maps its
forward/back travel coordinate onto the authoring scene's X axis using a scale
of `8.0`; the authoring lane therefore remains easy to inspect from the
Blender viewport while the game still exposes one-dimensional town movement.
The current camera uses the user-authored `Shift Y = -0.15`. That shift moves
the player projection upward to approximately `(210, 136.4)` in the 420x240
render, leaving the lower portion available for the persistent interface.

When changing the scene, edit the camera, lighting, materials, proxy, or
walkable object in Blender and rerun the bake. Do not hand-edit the generated
PNG layers or their generated metadata.

## Implementation history

### 1. Direct environment and map integration

The Meshy model was first packaged with a collision mesh, environment metadata,
anchors, and a map-16 entry. The first playable version established the key
content contract: the church square is safe, the church is central, and the
event commands are data-driven. The map includes merchant, guard, citizen,
church entrance, bell, and apothecary-side-door interactions.

The initial live-3D attempts exposed several problems: the model could appear
side-on or from the back, the apparent player scale was wrong, the camera saw
too little ground, the map was expensive to render, and the live sprite and
mesh projection could drift apart. These were useful diagnostics, but the
architecture was not a good fit for the scene.

### 2. Authoring scene and playable lane

The Blender annotation scene was introduced so the camera and player proxy
could be judged in the same viewport as the village. The lane is explicit,
bounded, and anchored to the church-square coordinates. Runtime movement uses
the existing bounded-lane traversal service; event positions and doorway
interactions remain authored in map data rather than embedded in renderer code.

The live player path was also made interpolated: movement has a presentation
position separate from the resolved traversal coordinate, and the walker uses
its normal frame animation. Camera tracking and actor movement consequently no
longer snap from tile to tile.

### 3. Switch to full pre-rendering

The scene was then changed to a camera-baked presentation. The bake script
renders a sequence of camera-centered samples along the lane rather than asking
LÖVE to draw the 830k-triangle environment every frame. The current output is:

- 41 slices from runtime Y `-2.0` through `13.0`
- slice spacing `0.375`
- 420x240 source images, matching the authoring render
- authored fog and lighting already present in the rendered pixels
- a generated collision/environment contract for runtime loading

Each sample produces three related images:

1. `scene_NNN.png`: the complete opaque camera view used to keep the panorama
   visually stable while panning;
2. `background_NNN.png`: the rear layer drawn before live actors;
3. `foreground_NNN.png`: the occluding layer drawn after live actors.

The foreground mask is derived from the Blender depth render. The sky is not
allowed to become a foreground occluder: depth ordering is used to separate
objects from the player depth, and transparent PNG alpha is written in the
same image orientation as the game renderer.

### 4. Fix the two major compositing mistakes

Two visual bugs were found by inspecting the proof frames rather than trusting
the generated files:

- Blender's `Image.pixels` depth rows were read in bottom-up order. Reversing
  the rows in `_read_depth` corrected the vertically inverted foreground mask,
  which had previously put sky in the foreground and removed the objects that
  should occlude the player.
- The camera-shift correction initially made fixed landmarks travel in the same
  direction as the player. The bake now applies the opposite sign to the
  camera `shift_x` correction, so the environment pans in the expected
  direction.

The runtime no longer crossfades between full scene images. It holds an
authored central slice, pans that slice using the residual movement from the
nearest baked camera sample, and draws the nearest lane slice as an opaque
underlay to cover the exposed edge. Live NPCs and the player are drawn between
the background and foreground layers. The matching foreground underlay and
central foreground are then drawn after actors, preserving practical
occlusion while avoiding a visible crossfade.

## Runtime behavior

Map 16 uses the bounded lane from runtime Y `-2.0` to `13.0`, with the player
depth fixed at the authored lane depth. Movement speed is `0.75`; camera
tracking, movement interpolation, and walker animation are configured in the
map's `town_sideview` camera profile. The central church entrance is at runtime
Y `5.5` and loads map `2` after its event text. The bell sets
`town_bell_rung`; the church text changes after that flag is set.

The map also keeps the authored town fog contract:

- fog color `[0.3, 0.42, 0.54]`
- start distance `12`
- distance `64`
- minimum factor `0.72`
- eight PSX-style bands

The prerendered pixels carry the authored sky, light, and fog appearance. The
runtime still retains the map-level fog definition so the environment contract
and the map remain explicit and inspectable.

## Verification performed

The project was staged through the canonical exporter boundary and checked with
the executable validation gate:

```powershell
node tools/ci/stage-project-gates.js --output out/experimental-stage-town-shifty
& 'C:\Program Files\LOVE\lovec.exe' out/experimental-stage-town-shifty validate
```

Observed result:

```text
VALIDATE OK
```

The deterministic town proof runner was then used against the same staged
project:

```powershell
python tools/golden/capture-town-proof.py `
  --game-root out/experimental-stage-town-shifty `
  --output out/town-proof-shifty
```

Observed result:

```text
THESTRA_TOWN_PROOF OK frames=7
```

The captured proof covered the standing exterior, movement to both sides,
return movement, doorway interaction, interior transition, and foreground
occlusion. The full staged unit suite also passed during the composite-town
verification run:

```text
ALL UNIT TESTS OK
```

The latest live proof was launched from a staged copy with the `town-proof`
mode, so it enters the Second Gate proof scene rather than the repository root
or an unrelated default map.

## Files and responsibilities

| Path | Responsibility |
| --- | --- |
| `projects/hichaukitoden-game/assets/authoring/town/second_gate_town_annotation.blend` | User-editable Blender scene. |
| `tools/blender/bake_town_prerender.py` | Blender-side render, depth split, projection sampling, and metadata generation. |
| `projects/hichaukitoden-game/assets/environments/town_church_prerender/` | Generated layered PNGs and environment metadata consumed by the game. |
| `runtime/presentation/viewport_3d.lua` | Loads the layered cache and composites camera slices, actors, and occlusion. |
| `runtime/engine/bounded_lane.lua` | Resolves bounded movement and traversal coordinates. |
| `projects/hichaukitoden-game/data/maps/16.json` | Town identity, fog, camera profile, anchors, and event commands. |
| `tools/golden/capture-town-proof.py` | Deterministic proof capture for this experiment. |

## Known limitations and review risks

This is intentionally a reviewable experiment with several known tradeoffs:

- The generated prerender package is large: the 41-slice PNG cache is roughly
  17 MB, and the editable source scene retains the original high-poly asset.
- The presentation is a hybrid rather than a true 3D scene: actors are live,
  while the environment is baked. Geometry that moves independently of the
  bake will not receive true runtime lighting or depth interaction.
- The central-slice-plus-underlay compositor is designed to eliminate the
  earlier crossfade, but it can still expose a seam if a future scene change
  moves the camera outside the baked coverage or changes the projection
  relationship.
- The authored Shift Y intentionally produces a lower strip in the raw proof
  frame. It is positioned for the game's persistent interface; evaluating the
  town image without that interface can make the frame look vertically
  unbalanced.
- The lane is one-dimensional. The full village model is not yet a freely
  navigable 2D/3D town; walkability is authored as the explicit main lane.
- The branch contains earlier authoring studies and generated comparison
  artifacts from the iterative investigation. The experimental PR should be
  reviewed as a whole, with the prerender package and the editable `.blend`
  treated as the intended deliverables.

## Blind review pass

Before opening the PR, three independent read-only reviews were run against
the branch patch. The configured environment-provided OpenAI key was used for
three separate Responses API calls with model `gpt-5.6-luna`,
`reasoning.effort=medium`, `service_tier=fast`, and `store=false`. This is the
API mapping of the requested “gpt-luna on med-fast” setting: the account exposes
the full model id `gpt-5.6-luna`, while the API names the speed setting `fast`
and the reasoning setting `medium`. The reviewers received different lenses
(rendering/gameplay, asset pipeline/integration, and maintainability/experiment
risk), did not receive one another's output, and were instructed not to edit
files. The key itself was never written to the repository or included in a
prompt.

The reviews converged on the following findings and dispositions:

| Finding | Disposition |
| --- | --- |
| The runtime’s two opaque scene images can expose a seam or discontinuity while the anchored slice is translated over the lane underlay. | Accepted as the principal experimental limitation. The current approach is intentionally retained to avoid the earlier full-frame crossfade; the proof passes, but this remains the main follow-up for a production renderer. |
| The prerender collision OBJ used the wrong world-to-OBJ coordinate conversion. | Fixed in `bake_town_prerender.py`, then rebaked. The collision envelope now uses `(world X, world Z, -world Y)` like the regular Meshy package builder. |
| The existing baked-environment test did not exercise the map-16 prerender package. | Fixed. The test still covers its original synthetic OBJ fixture and now also checks the shipped prerender manifest, all 41 layer files, dimensions, lane range, and player projection. |
| `--projection-samples` was accepted but ignored by the Blender bake. | Fixed by removing the unused option. `--slice-step` is now the single sampling control, and the generated manifest reports the actual slice count. |
| The dense Meshy fallback package records `targetFaces: 60000` while its measured output is 830,226 triangles. | Not changed in this experimental pass. Map 16 consumes the prerender package, not the dense fallback. The discrepancy is retained as a visible risk because the generator should either enforce decimation or record why it failed before that fallback is used. |
| Town anchors and event positions are repeated in the package manifest and map data. | Not changed in this experimental pass. The duplication is called out as a semantic-drift risk; a future revision should add a build-time equality check or choose one authoritative source. |

The post-review verification was rerun after the two fixes:

```text
VALIDATE OK
test_baked_environment_package: 179 passed, 0 failed
ALL UNIT TESTS OK
THESTRA_TOWN_PROOF OK frames=7
```

## Re-bake procedure after Blender edits

1. Open `second_gate_town_annotation.blend` in Blender.
2. Edit the scene, camera, lights, or proxy while preserving the named-object
   contract above.
3. Save the `.blend` in place.
4. Run:

   ```powershell
   & 'C:\Program Files\Blender Foundation\Blender 5.1\blender.exe' `
     --background `
     'projects/hichaukitoden-game/assets/authoring/town/second_gate_town_annotation.blend' `
     --python tools/blender/bake_town_prerender.py -- `
     --output `
     'projects/hichaukitoden-game/assets/environments/town_church_prerender' `
     --anchors `
     'projects/hichaukitoden-game/assets/environments/town_church/environment.json' `
     --slice-step 0.375
   ```

5. Re-run validation and the town proof capture. Review the generated diff,
   especially the masks around the sky, stairs, railings, and church entrance.

The bake is deterministic for a fixed Blender version, source scene, and
render settings. The generated cache should therefore be treated as a derived
artifact whose changes must be reviewed alongside the `.blend` change that
caused them.

## Experimental conclusion

The branch now demonstrates the requested workflow: the user can author the
town's visual composition in Blender, the player proxy and camera can be judged
there, and the resulting scene can be walked through in Second Rite with
interpolated movement, animated sprites, events, fog, church/labyrinth
identity, and practical foreground occlusion. The remaining question is not
whether the scene can be made playable, but whether this layered prerender
approach is good enough for production or should be replaced by a more robust
panorama/occlusion representation after the experiment is reviewed.
