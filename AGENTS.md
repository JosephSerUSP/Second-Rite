# Agent orientation — Second Rite

A LÖVE2D (Lua) first-person dungeon RPG with a summoner/creature economy, plus a
vanilla-JS+Node editor under `studio/editor`. Read this first; it is deliberately
short.

## Document authority (in order)

| Question | Source | Trust |
|---|---|---|
| What exists right now? | `docs/ENGINE-STATE.md` | **Generated + G4-gated. Highest.** |
| How does it work, and why? | `docs/SPEC.md` | Living spec, review-enforced |
| What are we trying to build? | `docs/design/`, `projects/*/docs/` | Intent only — **not status** |
| What have we committed to do next? | GitHub Issues | Open commitments — **not a status record** |
| How do gates/branches/reviews work? | `docs/SPEC.md` §3 and §5 | Process |
| Anything under `docs/archive/` | frozen plans | **Never authoritative** |

**When prose and `ENGINE-STATE.md` disagree, ENGINE-STATE.md is right** — it is
generated from the live engine. When prose and *code* disagree, that is a bug in
one of them: fix it or flag it, never silently pick one.

Design docs describe intent. They must not assert implementation status; if you
need to state status, put it in `SPEC.md` (reviewed) or let the generator report
it. This rule exists because four documents once asserted false facts (battle
"frozen", permadeath "not implemented", Item Creation "quite early") and cost a
full wasted planning pass. Nor may they track delivery with checklists; that is
an Issue's job.

## Gates — run these; they are the safety net

`lovec` is LÖVE's console binary. On this machine use the full path:
`"C:\Program Files\LOVE\lovec.exe"`.

**Invoking the `.ps1` gates bare fails** with `UnauthorizedAccess` under the
default execution policy. Always run them as
`powershell -NoProfile -ExecutionPolicy Bypass -File tools\golden\check.ps1`
(this is what `userPerform/*.bat` does).

**The repository root is not a game.** Since #700 the checkout is only the
Thestra installation: it owns no `data/`, and the runnable game is an ordinary
Project at `projects/hichaukitoden-game/`. So `lovec . validate` — and every
other bare `lovec .` gate command — **cannot work**; it dies with
`Could not find ordered collection 'units' at data/units/index.json`.

Executable gates run against a **staged Project**, built through the one
canonical exporter boundary:

```
node tools/ci/stage-project-gates.js --output <gateRoot>
lovec <gateRoot> validate
```

The `.ps1` gates below do that staging for you and delete the stage afterwards.
Pass `-GameRoot <dir>` to reuse an existing stage instead (this is what CI does,
so one stage serves every gate); a caller-supplied root is never deleted.

| Gate | Command | Guards |
|---|---|---|
| G1 | `tools/golden/check-validate.ps1` → `VALIDATE OK` | Every id cross-reference, command trees vs registry, formula compilation, targeting specs, scene draw modes, zero-SCRIPT battle phases |
| G2 | `tools/golden/check.ps1` | Battle simulation log byte-identity, per fixture in the Project's `data/goldenBattles.json` |
| G3 | `tools/golden/check-ui.ps1` | Per-scene UI trace identity |
| G4 | `tools/golden/check-state.ps1` | `docs/ENGINE-STATE.md` matches the live engine |
| G5 | `tools/golden/check-screens.ps1` → `SCREENS OK` | Rendered frame byte-identity, per scene and per goldenScript step |
| G6 | `tools/golden/check-editor.ps1` → `EDITOR SCREENS OK` | Rendered frame byte-identity for every `studio/editor` tab and modal |
| unit | `lovec <gateRoot> unittest` → `ALL UNIT TESTS OK` | Behavior the golden gates can't see |
| save | `lovec <gateRoot> savetest` → `SAVETEST OK` | Save/load round-trip |

`unit` and `save` have no `.ps1` wrapper: stage once with
`node tools/ci/stage-project-gates.js --output <gateRoot>` and run both against
that root, the way the required CI lane does.

`lovec <gateRoot> reachability` is a **report, not a gate** (always exits 0): content that
resolves but that nothing can produce or trigger — unsellable shops, items no
craft yields, creatures no pool grants. See SPEC §3.1 for why that is advisory
while paired-data coherence is a G1 failure.

- G2/G3/G5/G6 red = a **regression** (behavioral for G2/G3, visual for G5/G6).
  Investigate. Never regenerate a golden log or recapture screenshots to
  silence a diff; regeneration is an owner-signed action.
- **G5 is the only gate that can see the world view.** G1 validates data, G2
  diffs battle logs, G3 diffs UI *events* — a renderer or presentation change
  can break none of them and still be badly wrong. Frames that differ are
  written to `tools/golden/screens-actual/` for side-by-side inspection
  against `tools/golden/screens/`. G5 byte-compares pixels, so a GPU or
  driver change can legitimately shift it; that is an owner call, not a
  silent recapture.
- **G6 is the only gate that can see the editor.** G1 validates the data the
  editor writes; nothing looked at the editor itself, so a form that renders no
  fields, a modal that opens empty, or a tab that throws before it paints
  stayed invisible until a human happened to open that exact tab. G6 boots
  `studio/editor/server.js` on a port of its own, drives a headless Chrome
  through every tab and modal listed in `STEPS` (`tools/golden/editor-screens.py`),
  and byte-compares the frames against `tools/golden/editor-screens/`; differing
  frames land in `tools/golden/editor-screens-actual/`. It is **read-only** —
  no step calls `saveData()`, which matters because the editor writes form
  edits straight through to `data/*.json`. Adding an editor tab or modal means
  adding a step; the gate reports an unclaimed reference as `ORPHANED`.
  Needs `node`, `python`, the `websocket-client` package, Chrome
  (`CHROME_PATH` overrides the search), and the retained Three.js surface under
  `studio/editor/vendor/three/`. That vendor directory is gitignored: in a fresh
  worktree run `npm ci --ignore-scripts` and then
  `node studio/editor/sync-three-vendor.js` before G6. If it is absent, G6 must
  fail immediately as `dependency-missing`, not time out on an unrelated frame.
  Like G5 it is a claim about one machine and one Chrome build: a font or browser
  update can legitimately shift it, and that is an owner call, not a silent
  recapture.
- **G5/G6 have two deliberately different modes.**
  - **Absolute:** the commands in the gate table above compare against committed
    owner-signed references. G5 assumes the owner's real renderer and Effekseer
    shim; G6 carries the owner's browser/font fingerprint. Absolute red/green is
    the correctness claim and remains owner-bound.
  - **Relative:** run the GitHub Actions workflow **Relative visual A/B**
    (`.github/workflows/relative-golden-ab.yml`) with `gate` = `g5`, `g6`, or
    `all`, plus `base_ref` and `candidate_ref`. It captures base A, base B, then
    candidate on one pinned hosted runner and compares decoded RGBA pixels.
    Read the **base A -> base B repeat control first**. Any unstable control
    frame is named and excluded from the candidate verdict; this is mandatory
    for G6 because live editor nondeterminism has existed (#253/#259).
  Relative mode answers **"did this candidate alter rendering relative to the
  base ref?"**, not **"is this rendering correct?"** It runs without the native
  Effekseer shim. A green relative run never licenses recapturing G5/G6 goldens,
  and a red relative run is investigated as a candidate-vs-base regression.
- G4 red = the **doc is stale**, not the engine. Run
  `tools/golden/capture-state.ps1` and commit the result.
- `[formula] error in 'os.time()'` during G1 is the sandbox negative test, not a
  failure.

### Timing a gate or suite (#811)

Verification latency is tracked, not guessed. Put `tools/ci/time-step.js` in
front of any command to record its wall time:

```
node tools/ci/time-step.js --label "G1 validate" -- lovec <gameRoot> validate
node tools/ci/report-timings.js
```

The wrapper is transparent — same stdio, same exit code — so it never changes
whether a gate passes, and a failed timing write never turns a green step red.

**CI uses `--record` instead**, which stores a timing for a command the caller
already ran, leaving that command byte-identical to what it was before:

```
 = [System.Diagnostics.Stopwatch]::StartNew()
powershell -NoProfile -ExecutionPolicy Bypass -File tools/golden/check.ps1 -GameRoot :THESTRA_GATE_ROOT
 = 
.Stop()
node tools/ci/time-step.js --record --label "G2 battle" --ms .ElapsedMilliseconds --exit 
```

Use `--record` for anything whose environment is load-bearing, PowerShell
scripts above all: wrapping `check.ps1` in a node spawn made
`New-TemporaryFile` unresolvable on the hosted runner and turned G2 red. The
wrapper form is for local and agent use where a fresh process boundary is
harmless.
The first run of a label in a run is recorded as **cold**, later ones as
**warm**; that split is the whole point, since most of the cost being chased is
cold-start and re-staging. Records land in gitignored `out/timings/`;
`verify.yml` uploads them per run and prints the table to the job summary.

Nothing here enforces a budget. #811 defers enforcement until hosted-runner
variance is known — this reports drift, it does not fail on it. Set
`THESTRA_TIMINGS=0` to run a command with no recording.

## The core philosophy: eventing is the backbone

This project is built by an RPG Maker 2003 developer of 20+ years, and it is a
deliberate recreation of that way of working: **entire systems assembled out of
event blocks.** The difference is that here the event blocks are far more
powerful, and **the engine itself is made of them** — battle phases, scene
logic, recovery sites, quest handling and trap behavior are all command lists in
`data/*.json` that an author can open and modify without touching Lua.

That is the *reason* for the data-driven architecture below, not a side effect of
it. Practical consequences an agent must internalize:

- **Prefer expressing a feature as event commands over writing Lua.** If a
  mechanic can be a command list in a flow, scene hook, or common event, that is
  the correct implementation — not a shortcut. Several traits are implemented
  entirely in data (see `data/flows.json`).
- **When Lua is needed, add a reusable primitive, not a special case.** The right
  move is a new registry command / a new ref or scope / a new formula token that
  data can then compose — e.g. `FOR_EACH`'s `neighbor` ref serves any adjacency
  trait, and `x.trait.<CODE>` made every trait readable from data at once.
- **Don't build a bespoke mechanism where an event can already do the job.**
  Traps are ordinary events with a step trigger — anything an event can do, a
  trap can do — so there is no separate "trap system" to maintain.
- Power belongs in the command language. Widening it lifts every author,
  including the campaign generator, which emits the same commands.

## Non-negotiables

- **Data drives the engine.** Content lives in `data/*.json`; Lua never
  hardcodes content. Adding a command/effect/trait = a `data/engine.json`
  registry entry **plus** a handler. The validator and editor read the registry,
  so the registry — not a hand-written list — is the extension point.
- **Behavior in data is real implementation.** Phase logic lives in
  `data/flows.json`, scene logic in `data/scenes.json` hooks, both run by one
  interpreter. Do not add a Lua fallback "in case the data is missing" — hosts
  call `flow.run(phase, ctx)` unconditionally and the validator requires the
  phase to exist. Two paths for one behavior is the bug.
- **Formulas over scripts.** Numeric/boolean params take sandboxed formulas over
  registry-declared tokens. `SCRIPT` is a rationed escape hatch: battle phases
  are zero-SCRIPT (G1 enforces), and every validate run prints the total SCRIPT
  count so growth stays visible.
- **One semantic authority, not necessarily one execution host.** Every
  gameplay/authoring fact has one authored semantic source or mechanically
  generated contract; parallel handwritten implementations that can disagree
  are forbidden. Pure semantics may execute locally in Studio and LÖVE from
  generated outputs, derived artifacts must be consumed directly, and
  genuinely LÖVE-dependent services may be persistent and revision-scoped.
  Mutable simulation, validation, Test Play, final rendering/goldens,
  save/load and export remain actual runtime truth. A host-specific adapter may
  translate an authoritative fact for its UI or renderer, but may not redefine
  it. For every boundary ask **“Why must this cross a process boundary?”** —
  “the implementation happens to be Lua” is not enough, and “Studio wants
  immediate feedback” does not authorize a second semantic implementation. See
  SPEC §1.1.2 for the destination classes, three clocks and invalidation rules.
- **Domain transitions happen exactly once.** The subsystem that owns a gameplay
  mutation performs it to authoritative engine state; other layers may observe,
  project, format, cache or animate the resolved fact, but must not rewind,
  replay, repair, infer or independently reproduce that mutation. Battle is the
  reference seam: `Battle:resolveRound()` leaves `Battle` / `Battler` /
  `GameSession` fully resolved, while `presentation/battle_view.lua` may retain
  an earlier visual frame until its event/animation beat lands. A layer that
  needs to reveal a transition later reads a **resolved fact** the owner
  published (`engine/resolved_event.lua`) and fails loudly when one is missing —
  it never reconstructs the transition from an amount. Adding a new gameplay
  field must never require adding it to a presentation rollback list.
- **One event editor, everywhere, sharing one clipboard.** Every command list
  in the editor — map, common, scene, battle phase, troop event, quest, action
  sequence, recruit event — is `renderCommandList`, and commands copy between
  them. A new surface is a call to it, never a second editor. The context set
  is `engine.json` `commandContexts`, closed and G1-checked: **a context with
  no editor surface is a command nobody can write.** See SPEC §4.1.
- **No compatibility shims.** There is no shipped player base and saves are test
  artifacts that may break freely. When a schema changes, migrate the repo's own
  data in place and delete the old read path (SPEC §1.5). A `foo.a or foo.b`
  dual-read of our own data is carrying cost, not compatibility.
- **Fail loud, never silently.** Unknown targeting specs, draw modes, label
  jumps and registry ids raise errors rather than defaulting; the validator
  turns invisible authoring mistakes into build failures. A feature that
  silently does nothing is the worst outcome — prefer a crash or a G1 failure.
- **Enforce with gates, not vigilance.** When a rule can be checked
  mechanically, add the check (G1 for data/registry rules, unit tests for
  behavior, G4 for doc currency) instead of writing it down and hoping. Rules
  that live only in prose have already failed here once.
- **Loader data is shared and immutable.** `loader.getItem(id)` /
  `getActor(id)` hand back the one table every holder sees — `battler.equipment[slot]`
  is a *reference*, not a copy. Per-instance state belongs on the instance
  (e.g. ward charges on `battler.wardCharges`, keyed by slot), and anything
  stored there must round-trip through `engine/savegame.lua`.
- **Owner-supervised:** changes to `engine/battle.lua` and
  `engine/scenes/battle.lua` are never made autonomously.
- **No copy-pasted logic or coordinate math.** Layout/geometry lives in shared
  helpers; editor form fields come from the schema layer
  (`studio/editor/js/entity-forms.js`), not hand-written DOM. The icon picker's
  JS palette mirror is a bounded legacy technical-debt case documented in
  SPEC §4.3, not a general exception or precedent; update it with the shader
  and do not create another such pair.
- **Every icon is drawn by `ui.drawIcon`.** Nothing outside
  `presentation/ui.lua` computes iconset coordinates, builds icon quads or
  touches `iconset.png`. New icon presentation (borders, overlays, stack
  counts) goes in the one renderer, not the caller. SPEC §1.21.
- **The engine never requires presentation.** Use the
  `interpreter.bindPresentation` seam. (`engine/validator.lua` and
  `engine/cli_tools.lua` are the deliberate exceptions: they are build tools
  that validate presentation data, not runtime engine code.)
- **Presentation feel is a rule, not a preference** — rich vertical gradients for
  major menus (never flat dark overlays), panels that slide via timer states,
  gauges that interpolate instead of jumping, damage numbers with velocity and
  gravity. Review-enforced; see SPEC §2.2–2.3 before touching UI.

## GitHub Issues — durable memory, not a task tax

Issues preserve **actionable work that should survive the current task or
session**. They are a scope-control and handoff mechanism, not a requirement for
every owner request.

- **Do not interrupt a small, bounded request just to create an Issue.** Implement
  it, verify it, and report it normally.
- **Create an Issue for a meaningful out-of-scope discovery** — a concrete bug,
  design inconsistency, architectural problem, verification gap, or follow-up
  that should be addressed later. This is especially important when fixing it
  now would broaden the current task.
- Also create one when work is deliberately deferred, or when an investigation
  produces a concrete follow-up that another agent/session should be able to
  resume. A substantial branch-worthy task may get an Issue when durable scope
  or acceptance criteria would help, but do not manufacture one solely because
  a branch exists or delay an owner-requested implementation just to ticket it.
- **Do not create speculative backlog sludge.** An Issue must identify a concrete
  undesirable condition, unresolved decision, or desired invariant and be
  plausible future work. "Maybe improve/refactor X" is not enough. Check
  existing open Issues for the same problem when GitHub access permits.
- Write every Issue as a handoff to a fresh agent with no chat context: include
  the relevant current behavior/evidence, desired outcome or invariant,
  constraints/non-goals where they matter, and observable acceptance criteria.
  Prefer describing the problem and intent over prescribing an implementation
  before the code has been investigated.
- **An out-of-scope Issue does not expand the current task.** Record it and keep
  working on the original request unless the discovery blocks correctness.
  Mention the Issue number in the task report so the owner knows it exists.
- **Never track delivery with a checklist in a doc.** A `- [ ]` has no owner and
  nothing detects when it rots, so it goes on reading as "not built" long after
  the work shipped; closing an Issue is an event, ticking a box is a chore, and
  chores do not happen. Docs written before this convention (07.08.2026) still
  carry such lists and are wrong in both directions — do not add more, and never
  read an unticked box as current.
- Do not leave a repository-level source `TODO` as a substitute for an Issue.
  When implementing an existing Issue, reference its number in the branch/PR;
  use `Fixes #N` only when the change fully resolves it.

## Gotchas that cost real time

Kept short on purpose: an entry earns its place only if it caused a real bug and
no gate can catch it. **If you hit a trap that a gate could have caught, add the
gate instead of adding a line here** (that is how the item-type trap below became
a G1 check).

- **The editor dev server writes straight to `data/*.json`.** After browser
  testing, always `git diff data/` — it is not sandboxed.
- **Commands store their id under `cmd`**, always (the legacy `type` key was
  purged). Sub-command lists are always `commands`, never `script`.
- **After rewriting a JSON file programmatically, re-dump with its original
  indent** (`data/tilesets.json` is 4-space; most others are 2-space) or the
  diff becomes unreadable noise.
- **`docs/ENGINE-STATE.md` is ASCII-only on purpose** — it is byte-compared by
  both a PowerShell and a bash gate, and PowerShell 5.1 reads files as ANSI.
- **Tool availability is environment state, not a project fact.** This repo is
  worked from several harnesses and from CI, and they differ — interactive
  affordances (terminal dialogs, `git rebase -i`) are missing in most, and `gh`,
  `node`, `python` and Chrome vary. A missing CLI does not mean the operation is
  blocked, only that this path to it is: check for another before reporting it
  blocked, and never record *which* tools exist as a line in this file.

Traps that are now **gated** rather than remembered: an item carrying `effects`
with a non-`consumable` `type` is silently unusable (G1 fails it); a scene with
no draw mode (G1); a registry entry nothing implements (G4 reports it).

## Where things live

```
main.lua                 host: love.load/update/draw, CLI modes, input
main.js                  Electron shell for the editor (npm start / runEditor.bat)
engine/                  interpreter, validator, battle, flows, session,
                         savegame, scene_host, traits, effects, targeting
presentation/            window_renderer (declarative UI), world_renderer,
                         viewport_3d (raycaster), renderer (shared FX +
                         window-content drawers), animation_player
data/*.json              ALL content + engine.json registry
studio/editor/            Node + vanilla JS editor (no build step)
tools/asset-gen/         image-model art generation (Python) + its own local web
                         UI (server.py + ui/); staged, then promoted into
                         assets/ by hand. Deliberately NOT part of the editor.
                         Runs against hosted models OR the local GPU
                         (`forge.py start`, then a `forge-*` provider), which is
                         free and carries this project's retro style LoRAs. Take
                         the provider list and the current local default from
                         its README's table, not from memory — LCM trades prompt
                         adherence for speed, which is the wrong trade for
                         textures.
                         Seamless textures are scored, not eyeballed: see the
                         "Local generation" section of its README before
                         touching anything that tiles.
tools/blender/recipes/   St. Maria environment recipes. `interior.py` is the
                         shared shell/threshold/light vocabulary and
                         `furnishings.py` the shared furniture grammar; a map
                         file declares only what makes that place itself.
                         BEFORE authoring one, read
                         `docs/design/st-maria-interior-authoring.md` -- it is
                         the complete self-contained brief (colonial Portuguese
                         vocabulary, the camera contract, the character floor
                         limit, threshold direction, the no-key lighting rule).
                         A `.blend` under
                         `projects/*/assets/authoring/environments/` is
                         regenerable scaffold output UNTIL its owner adopts or
                         hand-edits it; after that it is SOURCE AUTHORITY --
                         edit it directly and never regenerate it.
                         `save_source_blend` refuses to overwrite either way,
                         so the safe default holds: `--force` is the moment you
                         must know which state the document is in.
tools/golden/            gate scripts + reference logs
tests/                   unit suites, registered in main.lua's unittest branch
userPerform/             .bat gate runners for the owner to run locally
docs/archive/            frozen history — not instructions
inspiration/             **A DIFFERENT (JavaScript) GAME** kept as reference.
                         Nothing in here describes this engine; never follow its
                         architecture docs. See inspiration/IMPORTANT.md.
```
