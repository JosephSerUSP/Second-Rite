# Playable Game Evidence for Autonomous Authoring

This document is the review contract for autonomous tasks whose goal is to **make a playable Thestra game or minigame**. It complements `JULES-CREATIVE-LAB.md`; it does not replace Project/runtime architecture authority.

The owner must be able to understand, launch, see, and finish the artifact without reconstructing the author's intent from JSON.

## Required human-readable deliverables

Every game-sized Project authoring task must document, in the Project README or an adjacent report:

- the game's premise and objective;
- launch command / Project root;
- complete controls using player-facing logical actions or ordinary keys;
- expected first-play length;
- a **complete walkthrough from launch to a real completion/ending state**;
- restart/reset/save/load behavior where applicable;
- known limitations and any intentional omissions;
- architectural friction discovered while authoring.

For Scene-level Creative Lab specimens, the report may be shorter, but it must still explain how to launch the specimen, control it, reset it, return to the launcher, and reach its win/completion condition when one exists.

## Visual evidence is mandatory

A game is not `READY FOR OWNER PLAYTEST` merely because JSON parses, validation passes, or the process stays alive.

The authoring run must produce screenshots from the **exact candidate branch through Thestra's real presentation path**. Do not substitute mockups, editor-only sketches, hand-authored diagrams, or screenshots from another Project.

For a game-sized Project, capture at minimum:

1. title / initial state;
2. representative ordinary gameplay;
3. at least one important interaction, puzzle, dialogue, battle, or management surface;
4. a completion / ending state when the harness can reach one without privileged state mutation.

For a Scene benchmark, capture the launcher plus at least one representative in-game frame for the specimen.

CI-generated screenshot artifacts are acceptable machine evidence. Committing screenshots is optional unless the task specifically asks for durable visual documentation, but the PR must make the exact-head captures easy for the owner to inspect.

### Asset-light projects

Minimal or asset-light presentation is allowed. **Invisible, unreadable, or effectively blank presentation is not.**

If a Project intentionally uses no bespoke art/audio, the screenshots must demonstrate that its geometry, contrast, text, event affordances, and navigation remain legible enough for a human to play. "No assets by design" is not evidence that the result can actually be seen.

Independent lab Projects must not solve visual legibility by silently borrowing Second Gate Project assets. Use Project-owned assets, explicitly inherited neutral RTP resources, or renderer-native neutral presentation.

## Machine evidence versus human playtest

Keep these claims separate:

- **AUTHORED** — candidate content exists;
- **MACHINE VALIDATED** — structural/runtime gates pass;
- **READY FOR OWNER PLAYTEST** — it launches through the ordinary Project path, survives fail-closed boot smoke, has reviewable screenshots, and includes the required human-readable instructions/walkthrough;
- **OWNER PLAYTESTED** — only the owner can assert this after personally playing it.

Screenshots, deterministic controllers, validators, and AI inspection can establish readiness. They cannot impersonate the owner's play experience.

## Boot evidence must fail closed

LÖVE's normal graphical error handler keeps a crashed process alive so a human can read the error screen. Therefore process liveness alone is **not** boot-success evidence.

Automated boot smoke must opt into the repository's fail-fast CI error-handler mode (`THESTRA_CI_FAIL_ON_ERROR=1`) or another mechanically equivalent crash-detecting path. A crash screen must fail the job rather than be reported as `BOOT SMOKE OK`.

## Why this exists

The first independent Project pressure test exposed both failure modes at once: a sparse Project could crash before title because runtime startup assumed a Second Gate Summoner Unit, while the CI boot smoke still passed because LÖVE kept the crash screen process alive. It was also difficult for the owner to evaluate the deliberately asset-light game without branch screenshots.

Those are useful experimental findings. Future autonomous game-authoring runs should surface them as evidence rather than forcing the owner to discover them manually.
