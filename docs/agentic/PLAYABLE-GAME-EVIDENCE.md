# Playable Game Evidence for Autonomous Authoring

This document is the review contract for autonomous tasks whose goal is to **make a playable Thestra game or minigame**. It complements `JULES-CREATIVE-LAB.md`; it does not replace Project/runtime architecture authority.

The owner must be able to understand, launch, see, and finish the artifact without reconstructing the author's intent from JSON.

For player-facing visual assets, also follow `PROJECT-VISUAL-AUTHORING.md`: preserve how the assets were made, keep Project-local sources/provenance, and review them through the real renderer rather than treating opaque PNG output as sufficient authorship evidence.

## Required human-readable deliverables

Every game-sized Project authoring task must document, in the Project README or an adjacent report:

- the game's premise and objective;
- launch command / Project root;
- complete controls using player-facing logical actions or ordinary keys;
- expected first-play length;
- a **complete walkthrough from launch to a real completion/ending state**;
- restart/reset/save/load behavior where applicable;
- known limitations and any intentional omissions;
- architectural friction discovered while authoring;
- a short visual-method note when the Project authors player-facing graphics, identifying asset roles, resolution/palette intent, and the retained source/provenance path.

For Scene-level Creative Lab specimens, the report may be shorter, but it must still explain how to launch the specimen, control it, reset it, return to the launcher, and reach its win/completion condition when one exists.

## Visual evidence is mandatory

A game is not `READY FOR OWNER PLAYTEST` merely because JSON parses, validation passes, or the process stays alive.

The authoring run must produce screenshots from the **exact candidate branch through Thestra's real presentation path**. Do not substitute mockups, editor-only sketches, hand-authored diagrams, or screenshots from another Project.

For a game-sized Project, capture at minimum:

1. title / initial state;
2. representative ordinary gameplay;
3. at least one important interaction, puzzle, dialogue, battle, or management surface **after reaching it through the ordinary player action that opens it**;
4. a completion / ending state when the harness can reach one without privileged state mutation.

For a Scene benchmark, capture the launcher plus at least one representative in-game frame for the specimen.

A standalone preview of a Scene/Map proves that surface can render; it does **not** prove that gameplay can transition into it. Where the walkthrough depends on Begin, movement, bump/interact, dialogue, choices, map transfer, or another ordinary action boundary, evidence should exercise at least one representative path through that boundary. This is especially important for Project-host dependencies that can remain invisible to title-only boot or direct preview modes.

CI-generated screenshot artifacts are acceptable machine evidence. Committing screenshots is optional unless the task specifically asks for durable visual documentation, but the PR must make the exact-head captures easy for the owner to inspect.

When a Project owns several small graphics, include or generate a contact sheet so the owner can inspect the visual vocabulary itself in addition to the in-engine result.

### Asset-light projects

Minimal or asset-light presentation is allowed. **Invisible, unreadable, or effectively blank presentation is not.**

If a Project intentionally uses no bespoke art/audio, the screenshots must demonstrate that its geometry, contrast, text, event affordances, and navigation remain legible enough for a human to play. "No assets by design" is not evidence that the result can actually be seen.

Independent lab Projects must not solve visual legibility by silently borrowing Second Gate Project assets. Use Project-owned assets, explicitly inherited neutral RTP resources, or renderer-native neutral presentation.

## Machine evidence versus human playtest

Keep these claims separate:

- **AUTHORED** — candidate content exists;
- **MACHINE VALIDATED** — structural/runtime gates pass, **and the thing was actually played** (see below);
- **READY FOR OWNER PLAYTEST** — it launches through the ordinary Project path, survives fail-closed boot smoke, has reviewable screenshots, and includes the required human-readable instructions/walkthrough;
- **OWNER PLAYTESTED** — only the owner can assert this after personally playing it.

Screenshots, deterministic controllers, validators, and AI inspection can establish readiness. They cannot impersonate the owner's play experience.

### What MACHINE VALIDATED covers, and what it used to miss

For a scene specimen, `MACHINE VALIDATED` once meant: `validate` prints `VALIDATE OK`, a preview PNG decodes, and the staged game survives four seconds under `THESTRA_CI_FAIL_ON_ERROR=1`. **None of those steps plays the game.** The preview photographs a scene at rest immediately after `on_enter`; the boot smoke sits on the title screen. Nothing entered a specimen, and nothing drove one to an outcome.

That gap is not hypothetical. An owner playtest on 2026-08-24 found four broken specimens whose reports all claimed success — a crash guarded behind `v.lost or v.win`, a board with no solution, and a scene that renders nothing are each invisible to a gate that never finishes a game (#920).

Two additional checks now stand beneath the rung, both in the lab validation lane:

1. **The scene must resolve.** A specimen whose preview emits `[formula] error` fails. The runtime already printed that line and the lane discarded it; asserting that a PNG *file exists* was never an assertion that the scene *worked*.
2. **The specimen must be machine-played to a terminal state.** Every specimen declares, in its own scene data, the condition that means it finished:

   ```json
   "terminal": { "reached": "v.win == true" }
   "terminal": { "none": "conversation specimen, not a scored loop" }
   ```

   `lovec . play-scene <id>` replays the authored input script through the same `scene_host.keypressed` path real input uses, then evaluates that condition. A missing declaration fails: *"this one never ends"* is a claim an author makes on the record, so a conversation can be told apart from a game nobody can finish.

A specimen that cannot demonstrate reaching a terminal state cannot be marked `READY FOR OWNER PLAYTEST`.

Specimens failing either check while a defect is open are listed in `tools/labs/known-unplayable.json`, each against its issue. That file is a ledger of debt, not a set of exemptions: a quarantined specimen that *stops* failing also fails the gate, so entries cannot rot into permanent allowances.

This raises the floor beneath `READY FOR OWNER PLAYTEST`. It does not reach for the top of the ladder — only the owner may assert `OWNER PLAYTESTED`.

## Boot evidence must fail closed

LÖVE's normal graphical error handler keeps a crashed process alive so a human can read the error screen. Therefore process liveness alone is **not** boot-success evidence.

Automated boot smoke must opt into the repository's fail-fast CI error-handler mode (`THESTRA_CI_FAIL_ON_ERROR=1`) or another mechanically equivalent crash-detecting path. A crash screen must fail the job rather than be reported as `BOOT SMOKE OK`.

## Why this exists

The first independent Project pressure test exposed the weakness of surface-only evidence repeatedly. A sparse Project could crash before title because runtime startup assumed a Second Gate Summoner Unit, while the CI boot smoke still passed because LÖVE kept the crash screen process alive. Once title boot was repaired, ordinary play uncovered later boundaries that direct previews did not cross: entering the Map Scene, taking the first movement step, and opening an Event Program's Dialogue Scene.

The same experiment also showed that an almost asset-free game may validate while remaining visually unreadable. A tiny Project-owned atlas and fixture vocabulary made the game legible, but its original authoring operation was not retained alongside the final PNGs. Future Project authors should preserve both the rendered evidence and the visual source/provenance that produced it.

Those are useful experimental findings. Future autonomous game-authoring runs should surface them as evidence rather than forcing the owner to discover them manually.
