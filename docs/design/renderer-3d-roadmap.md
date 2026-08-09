# Renderer — Polygonal 3D, Kit Pieces, and Effekseer: Design Intent

This document captures the architectural argument and art-direction intent behind the renderer work. It extends `widescreen-performance-study.md`, which studied resolution scaling of the earlier raycaster but deliberately did not ask whether the world renderer itself should become polygonal.

## 1. Scope

The renderer may become substantially more capable without changing the game's world model.

The following remain gameplay/engine constraints rather than renderer problems:

- the map is authored as a 2D cell grid;
- player movement is tile-locked;
- facing is cardinal;
- step-triggered events remain ordinary event logic;
- save/runtime state should not acquire free-camera or analog-world semantics merely because presentation uses real geometry.

The goal is presentation power: silhouette, depth, lighting, effects, and stronger environmental composition without turning the renderer project into an engine redesign.

## 2. Why polygonal geometry

A raycaster is excellent at axis-aligned walls, one floor plane, one ceiling plane, and camera-facing sprites. Its structural limitations are exactly where the desired art direction wants more expressive power:

| Capability | Design direction |
|---|---|
| Non-orthogonal architecture — arches, columns, diagonals | **Wanted** |
| Real mesh props and architectural fixtures | **Wanted selectively** |
| Surface normals and directional shading | **Wanted** |
| Z-level gameplay — stairs/pits/multi-height navigation | **Out of scope** |
| Free analog camera/movement | **Out of scope** |
| Full 3D creature roster | **Deferred** |

The visual payoff is not polygon count by itself. Geometry is useful because silhouette and normals let architecture read as architecture: an arch, jamb, pillar, or fixture can catch light differently from the flat wall behind it.

## 3. Renderer seam and ownership

World rendering is presentation-only. The renderer consumes authoritative session/map state and writes pixels; gameplay does not read rendering results back into movement, collision, quest logic, or saves.

That boundary should survive renderer changes.

A world-renderer implementation may own:

- prepared/cached map geometry,
- view/projection matrices,
- world-space lighting/fog,
- material/UV resolution,
- depth-tested world fixtures,
- camera-facing billboards,
- world-space effect handles.

It must not become the authority for:

- collision,
- event triggering,
- quest state,
- battle resolution,
- or persistent actor position beyond the engine's existing world model.

Battle battler placement is screen-space composition layered over the world backdrop; changing the world projection may require authoring adjustments, but should not make battle placement depend on world projection constants.

## 4. Keep the low-resolution framebuffer

Real geometry should still render into the game's logical low-resolution world surface rather than directly at native window resolution.

That is an art-direction choice, not merely a performance optimization. The low framebuffer:

- keeps polygonal geometry in the same visual register as hand-authored pixel art;
- makes low-poly silhouettes feel deliberate rather than like a separate rendering style;
- preserves the existing logical-coordinate UI/presentation model;
- prevents widescreen/native output from multiplying CPU-side geometry work unnecessarily.

Resolution/aspect-ratio changes should expand or reshape what the world camera sees without forcing UI geometry into a new coordinate system.

## 5. Hybrid kit-piece geometry

### Structural bulk stays procedural

Do not turn every wall, floor, and ceiling cell into a bespoke model. Procedural textured surfaces remain the cheap structural bulk and preserve the usefulness of the existing tileset atlases.

Spend models where silhouette or depth earns its cost:

- doors and arches,
- structural openings/gates,
- wall features such as sconces, banners, rubble, or torches,
- floor fixtures such as pillars, altars, braziers, and scenery stairs,
- special environmental mechanisms.

### Models are tileset variants

A model-backed kit piece should remain part of the same authored variant-pool concept as an atlas-backed piece. The author chooses a structural role and variant; the renderer decides whether that resolved variant is represented by textured procedural geometry or a model.

This keeps weighting, predicates, feature injection, light emission, and editor authoring in one system rather than creating a second map-decoration database for meshes.

### Static model format

For static kit pieces, OBJ/MTL is intentionally sufficient. Skinning, scene hierarchy, and a broad glTF runtime are not prerequisites for an arch, pillar, doorframe, or altar.

Rigid node-hierarchy motion remains a useful future extension for environmental mechanisms such as a portcullis, rotating machinery, or collapsing structure; it should not drag skeletal creature rendering in with it.

### Visual consistency

Model art must obey the same visual discipline as authored 2D environment art:

- coherent texel density relative to tileset surfaces,
- clean kit boundaries,
- nearest/no-smoothing presentation where appropriate,
- scale authored as part of the asset/registry contract rather than corrected ad hoc per placement.

## 6. Effekseer

### What it is for

Effekseer replaces the particle-emitter part of the animation system, not the animation system as a whole.

Tracks that operate **on the battler sprite** remain owned by the game's presentation layer:

- tint,
- gradient mapping,
- battler blend mode,
- battler transform/choreography.

Screen-level presentation also remains ours:

- screen shake,
- screen flash.

Effekseer owns effects that are genuinely independent emitted geometry/particles.

### Effects are assets

An `.efk`/`.efkefc` project is an authored asset in the same category as a PNG or MIDI: opaque to G1 internally, but referenced by validated game data.

Game/editor data should own the parts that are ours:

- effect reference,
- timing,
- anchor,
- offsets,
- scale/magnification policy,
- choreography around the effect.

The editor should preview the effect through the real engine rather than reimplementing Effekseer rendering in JavaScript.

### Deterministic time

Effect simulation must advance from the same explicit deterministic time source used by previews and screenshot tests, never from an independent wall clock.

Large elapsed intervals must be handled in a way that preserves emitter simulation rather than making preview/capture/load-hitch behavior differ from ordinary frames.

### Screen-space and world-space are different roles

Battle effects can use a screen-space camera because battler anchors are logical canvas coordinates.

World effects use the real world view/projection and depth buffer. Within world effects, weather and fixtures are distinct roles:

- a torch/brazier belongs to a cell/fixture and stays there;
- ambient weather belongs to the map/camera volume rather than being duplicated on cells around the player.

The renderer must preserve pass/group isolation so world ambient effects, battle screen-space effects, and UI do not accidentally suppress or overdraw one another.

### Authoring scale

Effects should be authored for the game's visual scale, using crisp small textures and deliberate particle sizes rather than relying on enlarging a conventional high-resolution effect until it fills the low-resolution canvas.

A shared library-to-canvas magnification belongs in registry/config data. Per-effect overrides should mean an intentional scale difference, not compensation for an undefined house scale.

## 7. Wandering 3D townsfolk

3D townsfolk are an exploratory presentation direction, not a prerequisite for the renderer or the creature system.

If pursued:

- use a small number of rigid-jointed, PS1-style characters rather than introducing skeletal skinning for the whole cast;
- keep interaction/collision on the authoritative integer grid cell;
- let presentation interpolate visual wandering independently;
- degrade gracefully to the ordinary billboard event when no model exists.

The appeal is specifically the period-correct segmented look and the low content count in town, not a general mandate to convert every actor to 3D.

## 8. Explicitly deferred directions

### Skeletal 3D creatures

The limitation is production economics and visual direction, not raw engine capability. A growing creature roster would require a correspondingly large rigged/animated 3D art library, while motion is exactly where smooth model interpolation most visibly diverges from hand-authored pixel art.

Creatures therefore remain 2D by default. A singular set-piece exception would be a separate art-direction decision, not precedent for a roster conversion.

### Leaving LOVE

Changing engines to gain a different renderer would discard the much larger body of authored engine behavior, validators, gates, editor tooling, and data contracts that do not depend on the renderer.

Renderer ambition is not by itself a reason to migrate the project away from LOVE.

### Z-levels and free camera

True Z-level navigation or free analog movement changes map data, collision, events, saves, editor semantics, and the step-trigger model. It is an engine/game-design decision wearing renderer clothing.

Do not introduce it through a presentation refactor.

## 9. Design acceptance

Renderer work should preserve these invariants:

- gameplay remains authoritative outside presentation;
- the logical low-resolution framebuffer remains the visual composition surface;
- procedural surfaces and model-backed kit pieces share one tileset/variant vocabulary;
- asset references are validated even when asset internals are opaque;
- editor previews use the real rendering path;
- deterministic screenshot/effect behavior is mechanically testable;
- battle/world/UI effect passes remain isolated by explicit presentation roles;
- exploratory 3D character work does not silently expand into a full creature-rendering rewrite.

The sequencing and delivery state of these ideas belong in generated engine state and GitHub Issues, not in this document.
