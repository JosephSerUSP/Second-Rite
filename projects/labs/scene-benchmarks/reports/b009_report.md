# B009 — Carnegie Hall 3D encounter

Evidence date: 2026-10-06. Machine validated prototype; owner playtest and canonical visual acceptance remain open.

## Observed implementation

The scene renders an original low-poly Carnegie Hall fan-study environment, Aya and a mutated rat as native perspective meshes. Camera and formula-bound model transforms are authored on an inline `modelScene` window. Geometry source is the adopted `assets/authoring/environments/b009_encounter.blend`; exports and hashes are under `assets/models/b009/`.

Held logical input is read by the reusable `READ_INPUT` event command. The fixed-tick event program normalizes diagonal movement, builds ATB, checks inclusive Euclidean range, applies pistol damage and resolves the rat's telegraphed target-area attack. Victory and defeat freeze gameplay; replay reinitializes state. The scene has zero SCRIPT commands and does not modify the production Battle owner.

The Studio Scene editor renders the native encounter preview and exposes camera/model JSON through the shared schema form. The benchmark now supplies ordinary Project identity metadata, which its Studio loading route requires.

## Visual walkthrough

[Open the runtime walkthrough](b009-3d/index.html): initial view, movement, wind-up, pistol hit, victory, defeat, and two clearly labeled asset inspection cameras. JSON beside each frame preserves its resolved scene state. Captures were driven through real Scene/input updates in a disposable staged Project; these are renderer evidence, not owner-performed gameplay.

## Verification

Production G1, G2, G3, G4 and full staged unit suite passed. B009 tests exercise held/released input, diagonal speed, frame partition invariance, exact circular range, rejected out-of-range shots, damage/evade, terminal outcomes and replay. Lab validation, source-authority checks and JavaScript syntax checks passed.

Absolute G5 was red (including an unsuccessful surface-crop run); G6 matched 34 of 47 frames, with 12 mismatches and one missing reference. References were not recaptured. Existing reference issues do not establish that every difference is baseline. Native Effekseer assertions were unavailable in this worktree. Owner playtest is pending.

## Remaining quality limits

The characters have simple transform motion, not skeletal locomotion or authored recoil/attack animation. Movement uses an aisle rectangle rather than collision against chairs or mesh navigation. Carnegie Hall geometry is a recognizable fan-study auditorium, not a measured architectural reconstruction. Encounter sound and richer lighting/presentation remain follow-up work. Do not describe this prototype as a finished Parasite Eve recreation.

Refs #1407 for the original behavioral and visual audit findings.
