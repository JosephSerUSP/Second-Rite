# Reusable Event animation controllers

## Decision

Event animation behavior is authored as reusable presentation-only state machines in:

```text
data/animationControllers.json
```

This is deliberately separate from both gameplay movement and `data/animations.json`:

```text
Map Event gameplay / event_actor
  root + facing + locomotion
            ↓ public facts
animation controller
  semantic visual state + transition policy
            ↓
Event presentation
  semantic animation + facing + backend
            ↓
sprite / model representation
```

The controller chooses **meaning** (`idle`, `walk`, `talk`, `cast`, `sleep`, ...). It does not choose a sprite filename, OBJ, Blender Action, sheet layout, frame number, transform, collision rule, or movement route.

## Authored schema

A controller is a reusable record keyed by id:

```json
{
  "townsperson": {
    "id": "townsperson",
    "initial": "idle",
    "states": {
      "idle": { "animation": "idle", "loop": true },
      "move": { "animation": "walk", "loop": true },
      "interact": { "animation": "talk", "loop": false }
    },
    "transitions": [
      { "from": "idle", "to": "move", "when": "event.moving" },
      { "from": "move", "to": "idle", "when": "not event.moving" },
      { "from": "*", "to": "interact", "when": "signal.interact" },
      { "from": "interact", "to": "idle", "when": "animation.finished" }
    ]
  }
}
```

The first vocabulary is intentionally narrow:

- `event.moving`
- `event.interacting`
- `event.enabled`
- `animation.finished`
- `signal.<semantic-name>`
- `not <fact>`

Unknown/content-specific native hooks fail at validation instead of quietly becoming a second Event API.

Positive `signal.*` transitions are evaluated before ambient observed facts. Authored order is deterministic within that deliberate-signal class and within ordinary fact transitions. At most one transition fires per update, so cycles cannot spin in one frame.

## Deliberate Event choreography

Event Programs get one generic presentation sentence:

```json
{ "cmd": "ANIMATION_SIGNAL", "signal": "wave" }
```

Omitting `eventId` sends the signal to the Map Event whose Program is currently running. An optional numeric `eventId` can address another Event on the current Map for deliberate choreography.

The command crosses the interpreter's existing presentation hook. The engine does not know what `wave`, `pray`, `open`, or any other signal means, and the signal mutates no gameplay state. A signal is simply a transient fact that an authored controller may consume. Signaling an Event with no resolved controller is a no-op.

## Event / Page / Common Event ownership

`animationController` is a normal presentation field and follows the existing Event presentation precedence:

1. the resolved Event Page may override it;
2. explicit `false` suppresses inherited controller presentation;
3. otherwise the Event/base value is used;
4. when absent there, a linked Common Event may provide it.

This matches `model` / `sprite` / `interactionFocus` instead of inventing a controller-only inheritance system.

An Event with no resolved `animationController` keeps the pre-#591 presentation behavior.

## Runtime instance lifetime

Authored controller definitions are reusable. Runtime controller instances are not.

Each active Map Event receives its own ephemeral instance keyed by current Map + Event id. The instance stores only presentation state:

- current controller state;
- state-local elapsed time;
- pending generic signals;
- animation-completion edge;
- transient interaction observation.

It never stores gameplay coordinates, Variables, inventory, Page conditions, or other persistent truth.

### Page changes

If Page resolution changes presentation fields but resolves to the **same controller id**, the ephemeral controller instance is preserved. This avoids twitch-resetting an NPC merely because another Page overlay became active.

If the resolved controller id changes (including a different archetype), the presentation instance resets to the new controller's `initial` state.

### Map transfer / reload

Only the current Map controller bucket is retained. Crossing to another Map discards the old bucket. Returning creates fresh controller instances; stale one-shots or queued signals cannot resurrect after a transfer.

The controller runtime is not save-game authority, matching `session.eventActorRuntime`.

## Deterministic advancement

Controllers advance only from explicit `dt` supplied by the renderer cadence. They do not read `love.timer`, system time, or wall-clock timestamps.

This makes transition tests and Studio preview repeatable. Studio's controller editor uses the same transition vocabulary and a fixed-dt preview.

## One-shot completion

A non-looping controller state does not guess the duration of a concrete asset. Presentation reports completion through the backend-neutral `completeAnimation` seam, which exposes the `animation.finished` fact on the next controller update.

That allows the same authored controller to back:

- a baked directional sprite sequence;
- a realtime model animation;
- another future visual representation.

The representation owns when its animation is actually finished; the controller owns what semantic state follows.

## Studio surface

The Event presentation fieldset receives the same three-way policy used by other inheritable presentation fields:

- **Inherit**
- **Use** a controller id
- **Suppress**

The controller editor exposes:

- controller id;
- initial state;
- state list;
- semantic animation per state;
- loop/one-shot flag;
- transition list and condition/signal source;
- deterministic preview for movement, generic signals, and animation completion;
- current-state highlighting.

The editor writes the same `animationControllers` resource that runtime loads. There is no editor-only controller format.

## Non-goals

#591 does not:

- create another locomotion/facing substrate;
- make movement type an animation contract;
- teach gameplay concrete sprite/model frames;
- persist temporary animation state in saves;
- recapture G5/G6 goldens;
- define eight-direction gameplay movement;
- require every Event to use a controller.
