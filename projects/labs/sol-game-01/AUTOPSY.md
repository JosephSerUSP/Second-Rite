# Thestra pressure-test autopsy — DEAD AIR AT 05:17

## What worked naturally

The neutral sparse Project is enough to start a complete non-combat game. Maps plus ordinary Event Programs express the whole loop: narrative observation, routing choices, persistent progression flags, conditional feedback, room transitions, and two authored endings. Leaving irrelevant RPG databases empty keeps the Project small and makes the game grammar legible.

`TEXT`, `CHOICE`, `SET_FLAG`, `CONDITIONAL_BRANCH`, and `LOAD_MAP` are a surprisingly sufficient adventure-game vocabulary. The same event substrate that supports RPG content can author a compact first-person puzzle without a bespoke native scene.

## What was awkward but possible

Map Events are an effective interaction surface, but an asset-free Project has limited authored affordance for making invisible wall interactions visually self-describing. This game therefore uses spatially obvious wall endpoints, labels, short rooms, and terminal-like interaction placement rather than importing placeholder art.

Persistent flags are excellent for small progression state, but composing a status readout for several independent flags requires explicit conditional blocks. That is acceptable at this scale and would become ceremony in a larger puzzle game.

A map Event cannot emit `SCENE_EVENT` because that command is Scene-context only. The endings therefore use dedicated Project-owned ending Maps instead of a custom ending Scene transition from an Event. This is coherent, but the boundary is visible to the author.

## What was genuinely missing

No reusable engine primitive was required to finish this game. The most concrete gap exposed by the experiment is verification ergonomics: repository CI validates the neutral sparse lifecycle, but a newly committed `projects/labs/**` game had no existing path-specific gate that stages, validates, and boots every lab Project automatically. This PR adds a small generic lab-Project validation/boot workflow rather than changing engine semantics.

A future authored visual treatment for generic, resource-free wall Events could improve legibility, but this game does not prove that a native primitive is required.

A full ordinary-input autonomous play proof is still bounded by the player-equivalent work tracked in #366. This experiment does not add a privileged solver or direct-state test path merely to claim deeper play coverage.

## Second Gate leakage audit

Project-owned game content contains no Second Gate:

- ids or character names
- setting/lore/story
- creatures or units
- roles or elements
- skills, states, or passives
- battle/troop grammar
- maps
- economy/items/shops/quests
- game-specific art/audio
- game-specific system policy

The RPG databases are intentionally empty. The Project inherits only pinned RTP 1.0 semantics/defaults, including the engine registry and generic font/default Scene/Flow resources. `category: "facility"` and all map/event terminology are Project-authored.

## Portability

The Project owns `data/` and `assets/` under `projects/labs/sol-game-01/`, pins RTP revision `1.0`, and references no repository-root Second Gate content. It opens through the ordinary Studio/runtime Project boundary:

`npm start -- --project projects/labs/sol-game-01`

The same Project root stages through `tools/editor/project-play.js` without being the repository root. Exact-head CI confirmed Project inspection reported `sameAsInstall:false` before validation and boot.

## Validation / boot evidence

Authored JSON was mechanically checked for parseability, rectangular layouts, in-bounds events/spawns, unique map/Event ids, reachable map references, and the expected two ending paths before publication.

PR #507's `lab project validation` workflow stages `projects/labs/sol-game-01` through the same `project-play.stageProject` / exporter boundary used by Studio. On head `055f985a441ffe460ba09a6cc3bb299f2061be1a`, the workflow:

1. identified the Project as external to the install root;
2. staged it hermetically;
3. ran LÖVE 11.5 as `lovec . validate` and required `VALIDATE OK`;
4. launched the staged game again with **no CLI validation/preview mode**;
5. kept that ordinary runtime alive for four seconds and failed on any early process exit/crash.

The exact-head log reported:

- Project root: `projects/labs/sol-game-01`
- `sameAsInstall:false`
- `VALIDATE OK`
- `BOOT SMOKE OK`
- workflow conclusion: success

The validator required no authored repair pass after publication.

This establishes staged runtime integrity and title/startup liveness. It is deliberately not mislabeled as a full player-input playthrough; #366 remains the proper generic path for that stronger proof.

No G5/G6 references are recaptured.
