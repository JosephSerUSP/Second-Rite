# Jules Creative Lab

This document controls recurring Jules creative-authoring experiments against the current Thestra Engine / Thestra Studio repository.

The scheduled Jules prompts should remain comparatively stable. **Change this document when we want to change what Jules explores.**

This is an **experimental-intent document, not an implementation-status record**. `docs/ENGINE-STATE.md`, current code, and other authority rules in `AGENTS.md` remain authoritative about what exists now.

The purpose of these experiments is to pressure-test Thestra by repeatedly using it to make real, bounded game artifacts.

A successful run may produce either:

- a convincing authored prototype; or
- strong evidence that the current authoring model cannot yet express the idea cleanly.

Do not distort engine architecture merely to make an experiment succeed.

---

## Task lanes

Recurring tasks select only from their assigned family unless their prompt explicitly says otherwise:

- **Creative Scene Probe:** families `B`, `C`, and `D`.
- **Canonical Authorability Benchmark:** family `A`.
- **Project Author Benchmark:** family `P`.
- **Project-Generator-As-User Audit:** family `U`.

This prevents a broad random pool from starving important experiment classes.

---

## Playable benchmark ownership and owner-playtest contract

Scene-level Creative Lab artifacts from families `A`, `B`, `C`, and `D` belong to the neutral Project at `projects/labs/scene-benchmarks/`. They must **not** be registered in root Second Gate `data/`, root Second Gate developer menus, or Second Gate golden fixtures merely because an experiment succeeds.

The benchmark Project is itself an ordinary Thestra Project. It must use the normal Project lifecycle, pinned RTP, authored Scene/Event semantics, staging, validation, and runtime launch boundaries. Do not create a benchmark-specific runtime, Scene host, input path, or privileged solver.

When a Creative Lab specimen needs player-facing graphics, keep the visual
source and evidence inside that specimen's Project. Use the Project-targeted
`tools/asset-gen` command for model-backed assets or its retained JSON raster
lane for small functional art, then include the Project contact sheet and
exact-engine captures in the specimen evidence. Creative Lab work must not use
root Second Gate `assets/` as an art scratch area.

Every landed Scene-level specimen must:

- be reachable from the benchmark Project's authored launcher;
- expose immediately understandable controls;
- provide a restart/reset path when the game concept has restartable state;
- provide a clean return-to-launcher path;
- keep its human-readable report under `projects/labs/scene-benchmarks/reports/`;
- remain absent from the launcher until a playable implementation actually lands.

The repository convenience command `npm run lab:benchmarks` may launch this Project, but it must remain only a wrapper around the ordinary arbitrary-Project launch path.

Project-author benchmarks in family `P` remain separate Projects under `projects/labs/`; they are not folded into the Scene benchmark cartridge. Generator-as-user audits in family `U` should likewise create or inspect an isolated Project rather than falling back to root Second Gate content.

### Evidence states

A benchmark report distinguishes machine evidence from human playtesting:

1. `AUTHORED`
2. `MACHINE VALIDATED`
3. `READY FOR OWNER PLAYTEST`
4. `OWNER PLAYTESTED`

An autonomous agent may advance a specimen through `READY FOR OWNER PLAYTEST`. **Only the owner may claim `OWNER PLAYTESTED`.** Validation, boot smoke, scripted input, screenshots, or an agent's own architectural inspection are not substitutes for the owner's play experience.

Every landed report must therefore include an **Owner Playtest** section containing:

- current playtest status;
- launch/control instructions;
- owner observations, initially pending;
- the post-playtest result, initially pending.

Architectural friction is experimental evidence, not an automatic implementation order. A single specimen should not freeze a new generic semantic vocabulary merely to make itself cleaner. Prefer repeated pressure across meaningfully different experiments before concluding that a reusable engine capability is warranted, and never add game-specific commands such as `PONG_*`, `SNAKE_*`, or `SOKOBAN_*` merely to make a benchmark pass.

---

## Selection policy

Experiments have stable IDs.

Unless a section explicitly defines another policy, eligible experiments within a task lane are ordered lexicographically by stable ID.

For deterministic daily selection:

1. take the current UTC date as `YYYY-MM-DD`;
2. convert it to an integer `YYYYMMDD`;
3. compute `index = YYYYMMDD % eligible_count`;
4. select the zero-based experiment at `index`.

This intentionally produces deterministic pseudo-variation rather than true randomness. A rerun on the same UTC date should select the same experiment.

### Eligibility

An experiment is eligible when:

- `status: active`;
- it is not excluded by a current repository constraint;
- its cooldown has elapsed, if one is defined.

If the selected experiment is ineligible, advance circularly through the sorted list until an eligible experiment is found.

Never substitute an experiment merely because another one appears easier.

For a cooldown, prefer an explicit field such as `cooldown-until: YYYY-MM-DD` rather than prose that requires interpretation.

---

# A — Canonical Reimplementation

Repeated periodically. The important thing is comparison against previous attempts.

## A001 — Pong

**status:** active  
**kind:** canonical  
**pressure:** continuous movement, collision, logical input, scoring, Scene-local state, lifecycle/reset, presentation

Implement a recognizable two-paddle Pong game.

Required behavior:

- player-controlled paddle;
- opposing paddle;
- ball movement;
- paddle collision;
- upper/lower boundary interaction;
- scoring;
- reset after score;
- visible score;
- restartable lifecycle.

Do not require sophisticated physics.

Do not add Pong-specific engine commands.

## A002 — Breakout

**status:** active  
**kind:** canonical  
**pressure:** collections, repeated similar entities, destruction, collision querying, level state, spawning/removal

Implement a recognizable Breakout-like game.

Required behavior:

- player paddle;
- moving ball;
- destructible brick field;
- collision;
- loss/reset condition;
- clear/win condition.

The brick representation should pressure-test authored collections/entity-like composition without requiring a full ECS.

## A003 — Snake

**status:** active  
**kind:** canonical  
**pressure:** grid movement, timing, ordered collections, growth, collision, reset

Implement a simple Snake game.

Required behavior:

- grid-constrained movement;
- direction input;
- collectible target;
- body growth;
- self/boundary loss condition;
- restart.

## A004 — Sokoban

**status:** active  
**kind:** canonical  
**pressure:** discrete state, occupancy queries, push rules, board reset, win predicates

Implement a compact Sokoban puzzle.

Required behavior:

- player movement;
- crates;
- walls;
- goals;
- valid/invalid pushing;
- completion detection;
- reset.

---

# B — Creative Scene Probes

Usually attempted once, then repeated only when particularly informative.

## B001 — Fishing Tension

**status:** active  
**kind:** creative-probe  
**pressure:** time-varying state, player reaction, gauges, success/failure windows

Create a fishing minigame where a fish produces changing line tension.

The player must react to keep tension inside an acceptable range until the catch completes.

Avoid feature-specific engine primitives.

## B002 — Argument as Combat

**status:** active  
**kind:** creative-probe  
**pressure:** semantic reuse, noncombat resource systems, dialogue-driven state, UI

Create a confrontation Scene mechanically shaped like combat but concerning an argument.

Possible resources include:

- patience;
- trust;
- embarrassment;
- conversational position.

Do not force use of native Battle if a normal authored Scene better expresses the design.

The experiment should test whether Thestra semantics compose beyond their obvious genre context.

## B003 — Rearranging a Bedroom

**status:** active  
**kind:** creative-probe  
**pressure:** object manipulation, persistent arrangement, conditions, narrative revelation

Create a compact Scene in which the player rearranges objects in a room associated with an absent or dead character.

Different spatial or categorical arrangements reveal different text/events.

The prototype need not contain polished narrative writing. The architectural interest is whether authored object state and compositional conditions remain legible.

## B004 — Rain / Distance / Embarrassment

**status:** active  
**kind:** creative-probe  
**pressure:** translating abstract design language into authored mechanics

Create a tiny playable experience whose primary dynamic state consists of:

- distance;
- embarrassment;
- rain.

Interpret these concepts mechanically.

Do not introduce engine concepts named specifically after them.

The purpose is to test whether existing generic semantics can carry an unusual design vocabulary.

## B005 — Lockpicking

**status:** active  
**kind:** creative-probe  
**pressure:** input state, timing, feedback, bounded simulation

Create a short lockpicking Scene with at least:

- player-controlled manipulation;
- feedback;
- failure pressure;
- success detection.

The exact lockpicking model is open.

## B006 — Dialogue Portrait Stage

**status:** superseded
**kind:** creative-probe  
**pressure:** presentation composition, pictures, formula transforms, dialogue state

Create a dialogue Scene involving:

- multiple portraits;
- changing speaker emphasis;
- portrait movement or transformation;
- choices;
- state-dependent presentation.

Favor authored presentation semantics rather than bespoke rendering code.

## B007 — Tactics Microboard

**status:** active  
**kind:** creative-probe  
**pressure:** grid queries, selection, movement ranges, multiple units, turns

Create a tiny tactics board.

Keep scope intentionally small:

- small grid;
- a few units;
- selecting a unit;
- legal movement;
- one simple action;
- alternating turns or equivalent lifecycle.

This is NOT permission to build a tactics subsystem.

## B008 — Riviera-Style Exploration Screen

**status:** active  
**kind:** creative-probe  
**pressure:** Scene-driven exploration, contextual actions, presentation, stateful choices

Create a Scene where exploration is presented as a composed set of contextual interaction opportunities rather than free map walking.

The player should inspect or interact with several locations/items, with availability changing according to state.

## B009 — Parasite-Eve-Like Positioning Proof

**status:** active  
**kind:** creative-probe  
**pressure:** real-time positioning surrounding discrete actions

Create a minimal non-production combat-like experiment in which:

- an actor can reposition continuously or semi-continuously;
- actions remain discrete;
- spatial relation matters.

Do not modify production Battle internals unless separately authorized.

This experiment may intentionally use an independent authored Scene.

## B010 — Falling Blocks

**status:** active  
**kind:** creative-probe  
**pressure:** grids, repeated timed update, piece state, collision, row queries

Create a very small falling-block puzzle proof.

It need not reproduce a commercial ruleset.

---

# C — Mutation Experiments

These begin from a conceptual benchmark but deliberately distort one assumption.

## C001 — Four-Paddle Pong

**status:** active  
**kind:** mutation  
**source:** A001  
**pressure:** whether composition survives topology change

Implement Pong with four independently meaningful arena boundaries/paddles.

The point is not novelty. The point is whether a clean two-paddle implementation generalized naturally or encoded hidden assumptions.

## C002 — Splitting Ball Pong

**status:** active  
**kind:** mutation  
**source:** A001  
**pressure:** multiplicity, spawning, collections

Implement Pong where a game event can split one ball into multiple active balls.

## C003 — Breakout With Moving Bricks

**status:** active  
**kind:** mutation  
**source:** A002  
**pressure:** whether repeated objects can possess independent authored behavior

Build on the Breakout concept but allow at least some bricks to move.

Do not add brick-specific native behavior.

---

# D — Genre Translation Experiments

Implement substantially similar mechanics through different Thestra hosts or semantic arrangements.

## D001 — Sokoban as Map Events

**status:** active  
**kind:** genre-translation  
**source:** A004

Implement the essence of Sokoban through Map/Event authoring rather than a standalone Scene.

Record what becomes easier or harder.

## D002 — Sokoban as Scene

**status:** active  
**kind:** genre-translation  
**source:** A004

Implement the essence of Sokoban as an authored Scene.

Compare architectural shape with D001 when evidence exists.

## D003 — Breakout as RPG Encounter Metaphor

**status:** active  
**kind:** genre-translation  
**source:** A002

Translate the structure of Breakout into an RPG-like encounter.

Preserve meaningful structural correspondences without requiring literal bricks/paddle graphics.

The experiment tests semantic plasticity rather than genre fidelity.

---

# P — Project Author Benchmarks

These are broader than Scene probes.

A Project benchmark must be isolated from Second Gate unless explicitly stated otherwise.

## P001 — Tiny JRPG Vertical Slice

**status:** active  
**kind:** canonical-project

Build a small completable RPG Project containing:

- title/start flow;
- one settlement;
- one small dungeon;
- at least three NPC interactions;
- one shop;
- treasure;
- one progression condition;
- combat using supported production semantics;
- one boss;
- one authored custom Scene unrelated to core Battle;
- save/load;
- ending;
- scripted or otherwise reproducible completion evidence.

Target approximately 10–20 minutes of conceptual playtime.

Do not add engine functionality solely for this Project.

## P002 — Seven Minutes Until Dawn

**status:** active  
**kind:** project-probe

Build a compact Project centered on a time-limited situation.

Requirements:

- one principal location;
- time or step pressure;
- world/NPC state changes;
- several discoveries;
- at least two mutually exclusive outcomes;
- at least one inventory or resource interaction;
- ending resolution.

Combat is optional.

## P003 — The Locksmith

**status:** active  
**kind:** project-probe

Build a tiny mostly-noncombat Project involving:

- inventory;
- dialogue conditions;
- locks or puzzles;
- persistent world changes;
- branching progression;
- at least two endings or resolutions.

Use supported authored semantics.

---

# U — Project-Generator-As-User Audit

## U001 — New Project From Supported Surfaces

**status:** active  
**kind:** tooling-audit

Act like a new Thestra author.

Starting through the supported Project/Studio creation workflow, attempt to create an isolated tiny game without manually relying on hidden repository implementation knowledge.

The finished artifact should include:

- a new Project;
- one playable map or equivalent starting experience;
- one interactive Event;
- one Scene;
- state;
- presentation;
- resource references;
- runnable entry point.

If normal authoring surfaces cannot accomplish a required step, record exactly where the user must escape into repository internals.

Do not repair the engine during this audit unless separately authorized.

---

# Current experimental priorities

Prefer experiments that pressure-test:

1. authored Scene semantics;
2. Scene state versus persistent state;
3. reusable queries;
4. collections/multiple similar runtime elements;
5. formula-driven presentation;
6. logical input;
7. Project isolation;
8. backend-neutral authored semantics;
9. Studio authorability.

These priorities describe experimental intent, not claims about implementation status, and may change as architecture matures.

---

# Temporary exclusions

Record temporary constraints here rather than editing scheduled Jules prompts.

Examples:

- do not pressure-test production Battle during an active owner-supervised Battle rewrite;
- do not recapture G5/G6 for unrelated creative experiments;
- do not use unfinished experimental state commands until their parent issue lands.

Keep exclusions evidence-based and remove them when they expire.

---

# Adding experiments

New experiments should have:

- stable ID;
- short title;
- status;
- kind;
- architectural pressure;
- bounded behavioral description.

Prefer game ideas over architecture-test descriptions.

Good:

> Make a fishing game where the player manages line tension.

Less useful:

> Test whether arrays work.

The architectural pressure belongs in metadata; the experiment itself should resemble something a game developer might genuinely try to make.

---

# Retiring experiments

Do not delete historically significant experiments merely because Thestra now handles them easily.

Canonical experiments should usually remain available as regression/longitudinal benchmarks.

Creative probes may be marked:

- `active`
- `cooldown`
- `retired`
- `superseded`

Preserve stable IDs.

---

# Principle

The Creative Lab asks a recurring question:

> What happens when someone arrives at today's Thestra and simply tries to make a game?

The answer — including inconvenience, failure, surprising elegance, and architectural resistance — is the experimental result.
