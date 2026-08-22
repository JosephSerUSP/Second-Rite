# Player-equivalent action and observation membrane

Thestra exposes a deliberately narrow seam for deterministic player policies,
record/replay tooling, and later agent playtesting. The seam exists to make it
structurally difficult for automation to become a privileged debug client.

## Actions

The canonical action vocabulary is the same fixed logical controller vocabulary
owned by `engine.input_map`:

```text
A B X Y L R START SELECT UP DOWN LEFT RIGHT
```

Physical keyboard input is resolved to one of those buttons first. Automation
uses the same button value directly. Both paths converge at
`scene_host.buttonpressed()` **before** the button becomes an authored Scene hook
such as `on_select` or `on_down`.

A policy must not call Scene hooks, movement functions, Event commands, menu
setters, or other gameplay-semantic operations directly. A button for which the
current host has no semantic mapping is simply unhandled; the membrane does not
invent a command to make every controller button useful.

Press is the only controller operation implemented by the first slice. The run
record already has explicit `press` / `hold` / `release` phases so the transport
format does not need to change when honest held-input ownership is implemented.

## Observations

Player observation is derived from presentation truth, not by serializing
`GameSession` and deleting known secrets afterward.

`presentation.player_projection` begins with
`window_renderer.resolveDataState()`, which already owns filtering, formatting,
visibility, cursor state, and resolved rows. The membrane then **reduces** that
presentation result. It currently exports only facts it can prove are visible:

- current visible Scene identity;
- open window identities/styles;
- plain fully visible labels from simple `term:` / `static:` list windows;
- the selected/highlighted state of those visible labels.

When clipping, scrolling, rich text, reveal timing, or complex cells cannot be
proven exactly from presentation-owned facts, the first version under-exposes
rather than guessing. Adding an observation field therefore requires a
presentation-owned proof of visibility; reading hidden engine state is not an
acceptable shortcut.

Representative filtered rows, offscreen labels, hidden windows, unrevealed
text, and Scene backing variables are planted by the executable negative
fixture and must remain absent from the observation payload.

## Run record

`thestra.player-run` version 1 records:

- explicit Project/runtime identity;
- starting condition and optional deterministic seed;
- ordered frame-bounded logical input events;
- corresponding player-visible observations;
- final outcome/checkpoint metadata;
- an optional `experientialJournalRef` that lets later player-only notes attach
  to the same timeline without mixing hidden authoritative trace data into the
  observation stream.

The run record validates its logical-button vocabulary against the same
`engine.player_controls` seam used by the controller.

## Deliberate first-slice limits

This slice proves Scene-owned controls and presentation-derived observation. It
does not yet claim:

- exploration movement or dialogue-input convergence;
- held/released directional timing;
- battle or inventory/management automation;
- save/relaunch lifecycle;
- framebuffer capture in the observation record;
- an LLM/model/provider integration;
- a Second Gate walkthrough policy.

Those are follow-ups over the same membrane, not permission to add semantic
shortcuts.

Refs #366 #375 #381.
