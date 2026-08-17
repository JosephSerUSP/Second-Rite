# Thestra Projects

A **Project** is one authored/runnable game. Studio/runtime installation and the opened Project are separate roots; a Project is currently recognized by its `data/` directory, with Project-owned assets conventionally under `assets/`.

There is no Campaign-style alternate active-content root inside a Project.

## Create a new Project

Create a sparse Project:

```text
npm run project -- create projects/labs/my-game
```

or use **File -> New Project…** in Electron-hosted Thestra Studio.

New Project does **not** copy Second Gate. It is locally sparse, not semantically empty. The bootstrap owns only the minimum Project identity/startup structure:

- `system.json` pinned to installed RTP revision `1.0`;
- one Project-owned title Scene;
- one Project-owned Map Scene;
- one tiny safe starter Map;
- explicitly empty Project-owned RPG databases, including Units and Troops.

Reusable semantic registry data plus the declared Scene, Flow, and progression defaults remain inherited through the pinned RTP manifest rather than being copied locally. These defaults are the **Thestra house baseline**: deliberately useful and JosephSeraph-shaped where a design direction is necessary, but still versioned, inspectable, replaceable, and non-Second-Gate-specific.

The bootstrap deliberately contains no Second Gate maps, creatures, items, writing, art, branding, combat ruleset, or St. Maria content.

### Fragmented catalog rule for authors and agents

Not every fragmented resource uses the same physical shape. Check `data/authored_storage_manifest.json` rather than guessing from another catalog.

**Ordered collections** such as Maps, Scenes, and Units use an `index.json` that owns their ordered fragment list.

**Keyed registries** such as Tilesets are different:

- deliberately empty registry: its directory contains only `index.json` with `{ "files": [] }`;
- populated registry: one JSON fragment per record, keyed by each record's own `id`, and **no `index.json`**.

The empty keyed-registry index is a marker, not a list to append to. When the first record is authored, remove that marker. Studio's authored-storage writer does this automatically. A hand-written/agent-authored registry that keeps `index.json` beside real record fragments is invalid and runtime validation rejects it rather than silently hiding or reordering authored records.

## Open a Project in Studio

From a checkout/install:

```text
npm start -- --project path/to/game
```

The target is validated before Studio launches. Studio resolves one Project root for the lifetime of the process.

Inside the Electron-hosted Studio, **File -> Open Project…** chooses a Project directory and performs a clean application relaunch against that root. Studio does not hot-swap `PROJECT_ROOT` underneath already-loaded editors, resource versions, or preview services.

## Play a Project directly

To launch the actual game without opening Studio first:

```text
npm run project -- play path/to/game
```

This is the shell form of the ordinary Test Play boundary. An external Project is staged through `tools/editor/project-play.js`, combining installed runtime code with exactly that Project's `data/` and `assets/`; inherited authored defaults from its pinned RTP revision are materialized into the temporary hermetic player stage. The temporary stage is removed when LÖVE exits. Same-root Second Gate development remains on the existing direct/no-copy path.

On Windows, the default executable is `C:\Program Files\LOVE\love.exe`. Set `LOVE_PATH` when LÖVE is installed elsewhere. Other platforms resolve `love` from `PATH` unless `LOVE_PATH` is set.

## Inspect a Project

```text
npm run project -- info path/to/game
npm run project -- info path/to/game --json
```

The JSON form is intended for agents/tooling.

### Inspect an inherited authored default

Use `authored` to see who currently supplies a supported authored default without copying it into the Project:

```text
npm run project -- authored path/to/game progression
npm run project -- authored path/to/game progression --json
```

For a fresh RTP-1.0 Project, progression reports provider `rtp`, provider id `thestra-rtp`, revision `1.0`, and logical path `data/progression.json`. Installing a newer Studio/RTP revision does not change this answer: the Project's `system.rtp.revision` pin remains authoritative until an explicit migration changes it.

### Make an inherited default local

When a Project needs to diverge from an inherited single-file authored default, materialize the exact resolved value locally:

```text
npm run project -- make-local path/to/game progression
```

For progression this creates Project-owned `data/progression.json`. Re-running `authored` then reports provider `project`; editing that file does not mutate the shared RTP source. Running `make-local` again is idempotent and does not overwrite the Project's local changes.

`make-local` is a generic lifecycle operation, but only resource classes with a safe single-file ownership/materialization contract are registered. Progression is the first such fixture. Do not infer that fragmented registries, Scenes, or Flows can be copied safely through this command until their storage-aware materializers are explicitly registered.

## Fork an existing Project

A Project fork copies only the source Project's `data/` and `assets/` trees into a new root. It does not clone the repository, editor, runtime, reports, or arbitrary source-root files.

```text
npm run project -- fork . projects/labs/second-gate-variant
npm start -- --project projects/labs/second-gate-variant
```

The target must not already exist. Missing parent folders are created. A target may live elsewhere in the same monorepo (for example `projects/labs/...`), but may not be placed inside the source Project's `data/` or `assets/` trees.

**Fork Project is an explicit variant/isolation operation, not New Project.** Use it when inheriting the source Project's authored content is intentional.

## Generate a game into an explicit Project root

The existing staged Project generator can target a reviewable root instead of `tmp/`:

```text
npm run generate-project -- --project projects/labs/mist-isle \
  "A melancholy island of drowned bells..."
```

The wrapper chooses the destination; the existing generator still owns outline/content stages, real-engine validation, and repair.

**Current generator caveat:** its prompt ruleset still assumes Second Gate's roles/elements/skills and therefore its bootstrap remains an explicit compatibility fork for now. New Project itself inherits the Thestra house baseline instead. Project-gen must author or select its own core RPG ruleset before it can safely switch to sparse bootstrap; do not silently reintroduce Second Gate rules into a new Project.

The generated Project can be opened normally:

```text
npm start -- --project projects/labs/mist-isle
```

or played directly:

```text
npm run project -- play projects/labs/mist-isle
```

## Agent rule of thumb

For an agent asked to create a separate game inside this repository:

1. establish an explicit Project root first;
2. make content edits only beneath that Project root;
3. inspect inherited defaults before localizing them rather than copying RTP files by hand;
4. run validation/Test Play through the installed Thestra runtime/staging boundary;
5. never use root Second Gate `data/` or `assets/` as scratch space;
6. preserve each resource's authored-storage representation rather than inventing or copying another catalog's index shape;
7. for player-facing visuals, establish `art/asset-gen.json`, keep source/specs under `art/source/`, and use `tools/asset-gen/gen.py --project <root> ...` so prompts, provenance, contact sheets and promoted assets stay Project-owned.

For a small functional visual vocabulary, prefer the deterministic raster lane:

```text
python tools/asset-gen/gen.py --project projects/labs/<slug> \
  raster art/source/visual-vocabulary.json
python tools/asset-gen/gen.py --project projects/labs/<slug> \
  raster art/source/visual-vocabulary.json --check
```

Finish the visual review through the real runtime. The reusable capture helper
stages the selected Project and calls the engine's `preview-map` path; it does
not reproduce the renderer in Python or JavaScript:

```text
node tools/asset-gen/capture_project.js --project projects/labs/<slug> \
  --capture main-floor=1,6,4,N
```

Keep the resulting captures and capture manifest beneath the Project's `art/review/`.

For a blank game or new experiment:

```text
npm run project -- create projects/labs/<slug>
```

For a deliberate Second Gate-derived variant:

```text
npm run project -- fork . projects/labs/<slug>
```

For current prompt-driven generation:

```text
npm run generate-project -- --project projects/labs/<slug> "<goal/pitch>"
```

The last command is still compatibility-fork based until the project-generator ruleset stage is generalized; that limitation is generator policy, not Project lifecycle policy.

## Security / ownership boundary

Project selection is not exposed as an arbitrary browser/server filesystem endpoint. The browser editor receives only a bounded Electron preload bridge when running under Electron; CLI callers use the filesystem lifecycle module directly. Browser-only/golden Studio hosting does not gain Project-root mutation authority.

Related: #237, #299, #390, #392, #479, #548, #555.
