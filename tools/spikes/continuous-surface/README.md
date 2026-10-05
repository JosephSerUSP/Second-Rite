# Continuous-surface traversal spike

Issue: #1402  
Parent architecture pressure case: #695

This is the first executable lane of the continuous survival-RPG gauntlet. It
proves a **small traversal semantic**, not a new Map ontology and not a physics
engine.

The runtime candidate lives at:

`runtime/engine/continuous_surface.lua`

The spike draws one neutral authored room and lets the player move through it
with WASD / arrows. The room is deliberately non-grid-shaped, includes concave
walkable geometry and thin polygon obstacles, and uses no Second Gate content.

## What the semantic owns

- authored XY walk regions (one or more polygons);
- authored XY obstacle polygons;
- XYZ actor state with constant authored ground Z;
- normalized digital diagonals and preserved analog magnitude;
- frame-rate-independent movement distance;
- bounded micro-steps plus exact obstacle-edge crossing checks;
- modest wall sliding;
- deterministic serialize/restore of traversal state.

## What it explicitly does not own

- Map lifecycle;
- cameras or rendering;
- Events / interactions;
- encounter scheduling;
- pathfinding or generated navmeshes;
- rigid-body physics;
- gravity, jumping or moving platforms;
- elevation changes between walk regions;
- battle execution.

Those boundaries are deliberate. The point of this spike is to establish the
smallest reusable movement capability needed by the chapter-shaped gauntlet
before deciding how a Map opts into it.

## Run

From repository root on Windows:

```text
"C:\Program Files\LOVE\lovec.exe" tools\spikes\continuous-surface
```

The spike runs its deterministic assertions at boot, prints
`CONTINUOUS_SURFACE_SPIKE_OK tests=<n>` on success, then opens the interactive
room.

Headless-ish assertion-only run:

```text
"C:\Program Files\LOVE\lovec.exe" tools\spikes\continuous-surface --test-only
```

(The LÖVE process still initializes normally; it quits immediately after the
assertions.)

## Why polygons first

A chapter-sized fixed-camera survival RPG needs continuous room movement, but it
does not yet justify Recast-style generated navigation or a general collision
world. Authored polygons are inspectable, deterministic, diffable and easy to
produce from Blender or Studio later.

The current contract therefore treats the walk surface as a union of polygons
and obstacles as polygons. `maxStep` is part of the authored semantic so
collision resolution stays bounded and predictable. Thin obstacle crossings are
checked against polygon edges exactly so a low frame rate cannot tunnel through
a narrow wall.

## Next integration question

If this movement semantic holds up, the next PR should decide the host boundary:

- how a Map names the provider and supplies the authored surface;
- how an environment package / Blender source contributes or references that
  surface without becoming gameplay authority;
- where the live provider state sits in `GameSession`;
- how ordinary world-space Events query player proximity;
- how save/load serializes the provider through the existing save boundary;
- how Studio previews/edits the exact same semantic without a JS reimplementation.

Do not wire this by mutating `bounded_lane` into a two-dimensional system. That
provider remains the intentionally specialized side-view lane capability.
