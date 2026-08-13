# Pong authored Scene Template pressure test — 2026-08-13

## Scope

This is a bounded architecture/evidence slice under #325 and #385. It asks whether a simple Pong-like mode can be authored primarily from Thestra's reusable semantic primitives plus Scene JSON/Event Programs, without `engine/scenes/pong.lua` or Pong-specific commands.

No production Battle code was changed. No final RTP directory or package machinery is proposed here.

## Result

**The experiment stops before an honest executable Pong fixture.** Current Thestra proves several important authored-Scene capabilities, but two gaps appear before Pong can be represented without smuggling the game into `SCRIPT` or native Scene code:

1. authored Scene updates have no explicit deterministic simulation-time contract; and
2. generic authored Scenes have no reusable Scene-local 2D actor/spatial model with motion + overlap/bounds queries and corresponding minimal presentation.

A Pong implementation today could be faked by putting the simulation in a Scene-local Lua `SCRIPT`, counting host updates as time, and/or adding presentation/native special cases. That would answer the wrong architectural question, so this report treats the failed prototype as evidence and opens bounded generic follow-ups #386 and #387.

## Current capabilities proven present

### Authored Scene identity, lifecycle, stack, and hooks — present

`data/loader.lua` loads Scenes as the authored `scenes` collection. `engine/scene_host.lua` resolves a Scene by id/name/kind, owns a Scene stack, and executes authored `on_enter`, `on_exit`, `on_frame`, and logical-input hooks. A Scene kind does not require a native module: the host attempts `engine.scenes.<kind>` only to obtain optional registered window definitions and explicitly permits kinds without a module.

This is enough to model Pong as an ordinary distinct Scene identity rather than a native gameplay engine.

### Scene-local transient variables — present

Each pushed Scene instance owns `state.v = {}`. `runHook` scopes `ctx.v` to that table, and `SCENE_EVENT` push/goto may seed variables before `on_enter`. Existing authored Scenes use `SET_VAR`, formulas over `v`, and hooks extensively.

Pong score, ball coordinates/velocity, paddle coordinates, phase (`serve`, `playing`, `won`), and simple AI state are therefore conceptually valid Scene-local authored state. They do not require new Pong-specific storage.

### Ordinary logical player controls — present

`engine/input_map.lua` defines the canonical logical controller vocabulary and maps `UP`/`DOWN` to `on_up`/`on_down`. `scene_host.keypressed` resolves a physical key through the input map before dispatching the authored Scene hook. This matches the player-equivalent direction in #366/#375: Pong should consume the same logical controls, not direct semantic shortcuts.

For Pong, discrete `on_up`/`on_down` is already sufficient for a minimal specimen if paddle movement is intentionally step-based per press. A richer held-input contract may later matter, but it is not the first blocker for the normalized specimen.

### Authored branching, arithmetic, score/reset/win policy — present

The shared Event Program substrate already supports Scene hooks, `SET_VAR`, formulas, `IF`, and `SCENE_EVENT`. Existing Scene fragments demonstrate nontrivial state machines in authored JSON. Therefore score increments, point reset, win checks, deterministic opposing-paddle policy, and exit/transition behavior are **authored policy**, not candidates for native Pong primitives.

### Generic window UI — present but insufficient as the playfield

Authored Scenes can use `draw: "windows"`, declarative windows, text/lists/gauges, cursor state, and generic window events. This is sufficient for a score label or end-state text. It is not evidence of a reusable spatial gameplay-actor presentation model: paddles and a ball should not be disguised as menu windows merely to claim success.

### Wait/timer state — present but not a deterministic simulation clock

`scene_host` owns `waitTimer`; `wait` events set it and `update(dt)` decrements it before running `on_frame`. This is useful Scene scheduling behavior, but it suspends the hook while waiting. It does not expose a reusable authored fixed tick or elapsed-time value for continuous deterministic motion.

## Pong requirement audit

| Requirement | Classification | Evidence / consequence |
| --- | --- | --- |
| Ordinary Scene lifecycle | 1 — already expressible | Scene stack + `on_enter`/`on_exit`/`on_frame` hooks are generic. |
| Scene-local score/phase/positions | 1 — already expressible | Scene instance `v` + `SET_VAR`/formulas. |
| Logical UP/DOWN | 1 — already expressible | `input_map` -> `on_up`/`on_down`; ordinary player path. |
| Human paddle policy | 4 — authored policy | Step/clamp paddle position in input hooks; no native Pong command. |
| Opposing paddle policy | 4 — authored policy | Deterministic tracking rule belongs in Event composition. |
| Score / point reset / win condition | 4 — authored policy | Arithmetic + branching + Scene-local state are sufficient. |
| Minimal score/end presentation | 1 — already expressible | Generic text/window presentation is adequate. |
| Deterministic continuous update | 3 — missing reusable semantic primitive | `on_frame` exists, but no authored fixed-tick/elapsed-time contract; frame-count simulation would be cadence-dependent. Follow-up #386. |
| Generic paddle/ball entities and motion | 3 — missing reusable semantic primitive | No generic Scene-local 2D actor/spatial collection was found in the inspected Scene substrate. Follow-up #387. |
| Bounds query/clamp | 2/3 — composition once spatial state exists | Numeric clamp is available, but a reusable actor/playfield spatial contract is missing. Do not create `PONG_BOUNDS`. |
| Paddle/ball collision | 3 — missing reusable semantic primitive | No generic authored Scene overlap query found. Small AABB-style overlap belongs with generic 2D Scene actors, not Pong. Follow-up #387. |
| Bounce direction/angle | 4 — authored policy | Once overlap is queryable, velocity reflection/variation is Pong policy. |
| Optional sound | not required for first proof | Existing audio commands can be evaluated after the spatial/timing blockers; sound must not block the architecture specimen. |

Classification key: (1) current reusable capability; (2) small generic authored-composition improvement; (3) genuinely missing reusable semantic primitive; (4) authored policy that must not become a primitive.

## Why `SCRIPT` is not a successful answer

Current Scenes may contain named sandboxed Lua scripts, and the Item Creation Scene demonstrates that this escape hatch can perform substantial Scene-local computation. That proves an escape hatch exists; it does **not** prove the semantic substrate can author Pong.

Implementing ball integration, collision, and deterministic timing inside a `pongSimulation` script would merely move a bespoke native-ish game implementation from `engine/scenes/pong.lua` into an opaque authored Lua string. It would not establish reusable author-facing words, inspectable composition, or the #325 principle that new gameplay sentences should normally be composed from reusable capabilities.

`SCRIPT` may remain a rationed escape hatch, but it is deliberately not used to manufacture a green result here.

## Smallest generic gaps

### #386 — deterministic authored Scene update timing

The first missing temporal contract should be generic and headless-testable. The design may be a fixed logical tick, safe elapsed-time exposure, scheduler semantics, or a deliberately small combination. The important invariant is that authored simulation must not accidentally mean "once per rendered update".

This capability is independently useful for minigames, timed interactions, ambient Scene behavior, and future authored scheduler/ATB experiments.

### #387 — authored 2D Scene actors + simple overlap

The spatial gap should start much smaller than a physics engine: Scene-local actor identity, position/extent, generic motion/state mutation, bounds/overlap query, and a minimal generic primitive/sprite presentation seam. Headless state/query semantics must not depend on presentation.

Pong then supplies policy over those primitives: where paddles begin, how the opponent tracks, how velocity changes on contact, when a point scores, and what score wins.

## Scene Template contract pressure test

Pong is useful specifically because it should be **optional reusable authored composition**, not a Thestra default RPG Scene.

### Thestra Default Scene

A baseline inherited RPG composition supplied by the pinned Thestra RTP revision. Ordinary Projects may resolve it without first instantiating a copy and may intentionally override/Make Local according to the eventual #385 resolution model. Examples are baseline title/menu compositions, not Pong.

### Thestra Scene Template

An optional RTP library composition. Pong belongs here *after* the generic gaps are filled. A Project deliberately instantiates/forks it; it is not automatically active merely because the RTP contains it.

Provisional contract supported by this specimen:

- **Stable template identity:** RTP-owned identity separate from any Project Scene id, e.g. a namespaced/template key rather than overloading the instantiated Scene id.
- **Parameters:** declared author-facing values for dimensions, speeds, winning score, presentation assets/styles, etc. Parameters customize instantiation; they are not arbitrary access to engine internals.
- **Dependencies:** explicit semantic capabilities and asset/template references required by the template. Validation should fail visibly when the pinned runtime/RTP cannot satisfy them.
- **Instantiation:** creates a concrete Project Scene with a new Project-local Scene id/name and materializes authored composition plus chosen parameter values. This is the safer first contract for optional templates.
- **No automatic live inheritance after instantiation:** a Project-local Pong Scene should not silently change because the installed RTP template changes. Template origin/revision may be recorded for provenance and optional explicit rebase/update tooling later.
- **Make Local / detach:** for an instantiated Scene this is effectively origin detachment: preserve the current concrete Project Scene, remove/update template provenance as appropriate, and stop presenting it as linked to the library. For genuinely inherited *default* Scenes, Make Local may instead materialize the currently resolved default; these are related UX operations but not necessarily identical storage semantics.
- **Assets:** template assets are declared dependencies. Instantiation may copy, reference the pinned RTP, or sparsely materialize according to #385's eventual resource policy; export must materialize the complete resolved game.
- **Studio origin/read-only state:** the template library entry itself is RTP-owned/read-only. The instantiated Project Scene is editable. Studio should show origin/template revision without making the Project Scene appear read-only.

### Project Scene

A concrete Scene owned by one Project. It has the Project's id namespace, may have originated from a template, and is the thing the game actually transitions to. Origin does not reduce Project ownership after instantiation.

### Future Package Scene Template

Semantically the same kind of optional reusable authored composition, but its provider is an explicit Project dependency rather than the pinned Thestra RTP. This report does not equate RTP and package storage/installation mechanics.

## Instantiate vs live inheritance

Pong pushes strongly toward **instantiate/fork by default for optional Scene Templates**.

Live inheritance is valuable for baseline defaults and for the separately proposed Map Event Template/Prefab model in #325, where many instances intentionally share a live prototype. A Scene Template has a different ergonomic purpose: it is a starting composition for a substantial runtime context that authors are expected to inspect and modify.

Automatically merging future Pong template changes into a customized Project Scene would create difficult semantic merges across Event Programs, window/entity composition, parameters, and local ids. It would also violate #385's requirement that a Project not silently change because a newer Studio/RTP is installed.

Therefore Scene Template and Map Event Template should share vocabulary only where semantics genuinely match; the word "template" alone is not enough to force live inheritance.

## Identity and versioning implication

The minimum provenance concept for an instantiated Scene is logically:

- provider identity (`thestra-rtp` now; package provider later);
- stable template identity;
- template revision compatible with / belonging to the Project's pinned RTP revision;
- chosen parameters at instantiation when useful for audit/re-instantiation.

This does not require freezing a final metadata schema in this slice. The invariant is that opening the Project under a later Studio must not silently re-resolve an instantiated Scene against a newer template.

## What an eventual executable Pong proof should demonstrate

After #386 and #387, the pressure test should resume as a development/fixture-only authored Scene outside any final RTP location and prove:

1. no `engine/scenes/pong.lua` exists;
2. no Pong-specific command exists;
3. logical player UP/DOWN travels through the ordinary input seam;
4. ball/opponent progression is deterministic and headless-testable;
5. overlap/bounds use generic spatial capabilities;
6. score/reset/win are Event-authored policy;
7. minimal presentation uses generic actor/window presentation;
8. an ordinary fixture Project can instantiate/use the composition;
9. the template remains optional library content, not an inherited default Scene.

## Conclusion

Pong validates the direction of #325/#385 but currently **fails as a pure authored-composition specimen at the reusable timing + generic 2D spatial layer**. That is a useful boundary: Thestra already has the Scene lifecycle, local state, logical controls, Event branching, transitions, and UI needed to host the policy. It should add the missing generic capabilities rather than invent Pong words or hide the game inside `SCRIPT`.

Follow-ups: #386, #387. #325 and #385 remain open.

Agent-Signature:
  platform: ChatGPT
  model: GPT-5.6 Sol
  role: research
  task: "Pong Scene Template pressure test under #325/#385"
  base: 12f53777
