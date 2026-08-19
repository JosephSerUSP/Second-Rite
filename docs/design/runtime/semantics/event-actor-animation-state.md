# Map Event actor animation state

## Decision

Map Events need a stable runtime actor identity before top-down/overhead cameras make animated NPCs visible as first-class world inhabitants.

The engine now separates four facts that were easy to collapse into one sprite name:

```text
stable world root
+ locomotion (idle / moving)
+ facing (N / E / S / W)
+ optional semantic override (one-shot / held pose)
                    ↓
            semantic clip resolution
                    ↓
         presentation-specific asset/frame
```

`engine/event_actor.lua` owns only the facts above. It does **not** own sprite files, Blender Actions, sheet layout, frame timing, camera pitch, projection, billboard geometry, render offsets, pathfinding or collision.

That boundary is deliberate: changing a Map from the current first-person view to an overhead camera must not change how an Event decides whether it is idle, walking, facing east, or temporarily gesturing.

## Stable root versus animated visual

The actor root is the Event's world-space anchor. It is distinct from whatever presentation later does to the visible sprite/model.

```text
Event actor root                 Presentation
(x, y)                           bob / shake / pivot / squash / frame offsets
   │                                  │
   ├── movement/collision             └── visual only
   └── camera-follow anchor
```

A camera following the Event should observe the stable root, not the animated artwork. Otherwise a walk bob, gesture pivot, damage shake or mismatched sprite frame can make the camera jitter even though the actor did not move in world space.

`setRoot()` therefore does not infer facing or locomotion. A movement/path system may update the stable root at its own cadence and publish motion separately through `setMotion()`.

## State axes

### Locomotion

The first vocabulary is intentionally tiny:

- `idle`
- `moving`

The semantic resolver maps those to `idle` and `walk` clips. The movement system says **what the actor is doing**; presentation does not receive a hard-coded `walk_left.png` command from gameplay.

Stopping preserves the last facing. Cardinal motion updates facing. Diagonal motion currently fails loud rather than inventing an eight-direction movement rule while the Map gameplay contract is still cardinal.

### Facing

Runtime facing is canonical `N`, `E`, `S`, or `W`. Author-facing aliases such as `north`, `left`, `up`, etc. normalize at the boundary.

This four-direction runtime contract does not prevent an asset from supplying more rendered angles later. Directional interpolation/selection is a presentation concern unless gameplay itself gains diagonal movement.

### Overrides

An override masks the resolved locomotion clip without destroying the underlying locomotion/facing state.

Two forms exist:

- **one-shot** — e.g. `gesture`, `surprised`, `cast`; optional duration;
- **held pose** — e.g. `kneel`, `sit`, `sleep`; persists until explicitly cleared.

Example:

```text
moving east → walk / E
play one-shot "gesture"
           → gesture / E
complete gesture
           → walk / E
```

A timed one-shot can expire through `event_actor.update(dt)`. If no duration is supplied, it is completion-driven and remains active until `completeOverride()` is called. This is important because the engine should not guess the duration/FPS of a baked animation asset.

Only the current Map's timed overrides advance. Off-map actors do not run hidden animation clocks.

## Relationship to the tiny-character experiment (#599)

PR #599 is useful concrete production evidence for this abstraction without becoming a runtime dependency.

Its three deliberately different 24×24 character approaches all converge on the same semantic Blender Action vocabulary:

- `Idle`
- `Walk`
- `Gesture`

and its rendering experiment strongly favors baked directional spritesheets for these tiny characters. That is exactly the split this runtime state supports: the engine can resolve **walk + east** while a later presentation adapter chooses the appropriate baked character sequence and frame.

The runtime does not import #599's `.blend` files, generated PNGs, frame counts, action naming prefixes, or experimental manifest. Those remain authoring/product evidence. A Project's actual character visual should be free to map the same semantic state to a spritesheet, realtime model, or another representation.

## Camera work boundary

The concurrent world-camera work (#590/#592/#595) owns projection, camera pose, view profile and framing. This Event actor slice intentionally does not modify `presentation/viewport_3d.lua`.

The durable meeting point should stay narrow:

```text
camera / renderer asks Event actor:
    rootX, rootY
    facing
    locomotion / resolved semantic clip

camera never asks:
    current sprite frame
    animation bob offset
    Blender Action name
```

Likewise, `engine.event_actor` knows nothing about orthographic, perspective, first-person, top-down or RPG-corrected projection.

## Runtime ownership and persistence

`session.eventActorRuntime` is lazily allocated and transient. It is scoped by Map identity + Event id and is deliberately absent from save serialization.

That means:

- idle/walk/gesture clocks are never save-game authority;
- held temporary presentation poses are not accidentally persisted;
- authored Event/page state and persistent `eventOverrides` keep their existing ownership;
- if future NPC movement needs a moved root to survive leaving/reloading a Map, that root must be promoted deliberately into Map/Event state rather than gaining persistence because an animation cache happened to be serialized.

This is an important distinction between **actor runtime state** and **world mutation**.

## Next integration slice

After the camera branch settles, presentation can consume this module without changing its semantics:

1. resolve the effective Event page;
2. query/create its Event actor runtime state;
3. use the stable root for world placement/camera targeting;
4. map `(clip, facing)` to the Event's character visual;
5. advance the visual's own frames;
6. signal `completeOverride()` when a completion-driven one-shot ends.

Only then should Event Program commands be promoted for authoring actions such as facing an Event, playing a one-shot, waiting for it, or holding/clearing a pose. Those commands should call this generic actor contract rather than each becoming a bespoke renderer hook.
