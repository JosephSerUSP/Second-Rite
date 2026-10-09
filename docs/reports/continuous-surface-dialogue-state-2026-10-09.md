# Dialogue state and dock transition checkpoint

The actual gauntlet host emitted `sceneState.dialogueCursorIdx` formula errors when dialogue closed. Native stack traces located the outgoing dock clear pass: it evaluated dialogue definitions against the incoming Map's empty Scene State. Rapidly reopening the same variant during its pending collapse also failed to retarget the transition, allowing stale transition completion to associate dialogue with Map state.

The dock now retains the outgoing Scene definition, state and context for closing content. Retargeting compares the requested variant with the active transition destination, including a nil destination. The GraphWalker host seeds complete dialogue window state before entry and mirrors its owned cursor during TEXT and CHOICE. New conversations reset the cursor to one. No formula fallback or error suppression was added.

The native main-host proof passes door/investigation/combat/report/save-load and a CHOICE-first conversation, wrapped navigation, selected-branch execution and reopening. Its final log has no formula warnings. The fixture is cloned before adding test choices; shared loader content is not changed. Two dock regression assertions fail against the previous implementation and pass with the fix. Full shipping units pass with native Effekseer coverage, shipping and experiment G1 pass, and G3 passes.

Absolute G5 remains red: current references differ and the center-crop check fails. Existing issues #1454 and #1331 track this baseline. A local same-machine comparison against parent 1250686a captured 161 Classic and 161 Wide frames on each revision; all 322 decoded RGBA frames match exactly. The parent also fails the crop check. This comparison is no canonical correctness claim or reference approval, and no goldens were recaptured. Evidence is in gitignored `out/dialogue-cursor/`.

This resolves the actual-play dialogue-state failure in #1486. Measured combat-reference timing remains separate work in #1485.
