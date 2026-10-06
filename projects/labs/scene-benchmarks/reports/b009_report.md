# B009 — reference-led Carnegie Hall rat encounter

Evidence: 2026-10-06. Native runtime and behavior verification; owner playtest and canonical visual acceptance remain open.

## Reworked behavior and presentation

The rat encounter now uses an authored backstage corridor with red doors, masonry and worn floor grain, matching the supplied rat footage's room category and palette. The original auditorium mesh is preserved in the adopted Blender source. Aya has evening-dress proportions, authored walking/recoil/fallen poses; the rat follows the reference palette (crimson body, pale mottled back saddle) with wind-up/lunge poses. Textures and models are original assets, not extracted commercial content.

The compact upper-left overlay presents blue AT, numeric HP and green PE. Full AT flashes using authored time. Enter opens targeting directly; X opens command selection through an event-authored edge on the canonical logical input snapshot. Menus and aiming pause domain simulation. Blue ground and green air range lines, a red target cursor, ammunition and target count appear during aiming. Confirm spends a bullet and AT; closer targets take more damage. Out-of-range shots deterministically miss, which approximates rather than reproduces the original probability model.

The rat alternates a locked-position bite/lunge and three fire-tail projectiles. Each projectile can damage Aya only once. Heal 1 recovers 30 HP, consumes lab-tuned PE and AT; Medicine 1 consumes stock and AT. Victory offers EXP 2 and one-time Ammo +6 collection before replay. Defeat renders Aya's fallen pose. Terminal gameplay stops while visual flash/damage timers finish. All domain behavior remains a zero-SCRIPT Scene event program; production Battle owners are untouched.

Reusable presentation additions are a translucent gradient overlay shell, compact gauge geometry and formula-bound gauge colors, plus world-anchored model-Scene labels sharing the camera basis. G1 validates the new authored gauge fields and viewport labels.

## Visual and source evidence

[Native walkthrough](b009-3d/index.html) includes before/after, movement, wind-up/lunge/fire, command/aiming, impact, PE/healing/item, outcome/rewards/defeat, and isolated asset cameras. Resolved-state JSON accompanies every capture. Its manifest records image and source hashes. These captures use real Scene/controller updates in a disposable stage, not owner-performed gameplay.

[Rat reference footage at 17:15](https://www.youtube.com/watch?v=4JGJC04CcLI&t=1035s) grounds camera/backdrop/silhouette; [original manual](https://impzone.club/pdf/parasiteeve.pdf), printed pp. 14–17, grounds movement, pause, range, bullets, healing and loot. The private reference pack remains outside game assets. Adopted geometry source: `assets/authoring/environments/b009_encounter.blend`; packed source textures and OBJ/MTL/PNG hashes are retained in `assets/models/b009/provenance.json`.

## Verification boundary

Production G1/G2/G3/G4, staged units and lab validation are verified locally. B009 tests exercise held/released input, normalized movement and frame partitions, command pause, aiming, exact range, misses/no ammo, PE/item resource consumption, evasion/projectile de-duplication, terminal freeze, visual-timer completion, reward/replay, escape and projection/validation. Native play-scene reaches victory through its authored input sequence.

Absolute visual gates remain unreconciled. Earlier hosted Relative A/B failed during base A capture: G5 surface-crop timeout and G6 initial-workspace readiness; neither established a candidate verdict. Hosted lab-wide preview failed at D002 Sokoban's function-valued Scene state (existing #1244), before reaching B009. Native Effekseer assertions are unavailable and owner playtest is pending. Canonical references were preserved.

## Remaining fidelity limits

The original backgrounds have richer lighting, texture detail and composition. The encounter now defaults to the existing Wide surface (426x240, integer-centred 16:9 approximation), with a full-width 3D camera and HUD anchored to surface edges. Classic and 4:3 player choices still work. This model remains an approximation with mesh-pose animation and a rectangular movement area. Exact regional critical-hit/miss formulas, rates/costs and escape probability are unverified. AT/recovery speeds, PE cost 30, timing and damage bands are lab tuning. Encounter sound, room transitions and full Day 1 progression remain outside this one encounter. Do not claim source-game parity.

Refs #1407, #1414 and #1415; draft implementation in PR #1413.
