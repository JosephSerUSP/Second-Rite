# Thestra Projects

A **Project** is one authored/runnable game. Studio/runtime installation and the opened Project are separate roots; a Project is currently recognized by its `data/` directory, with Project-owned assets conventionally under `assets/`.

There is no Campaign-style alternate active-content root inside a Project.

## Create a new Project

Create a genuinely neutral sparse Project:

```text
npm run project -- create projects/labs/my-game
```

or use **File -> New Project…** in Electron-hosted Thestra Studio.

New Project does **not** copy Second Gate. The bootstrap owns only the minimum Project identity/startup structure:

- `system.json` pinned to installed RTP revision `1.0`;
- one neutral title Scene;
- one neutral Map Scene;
- one tiny safe starter Map;
- explicitly empty Project-owned RPG databases, including Units and Troops.

Reusable semantic registry data plus the declared `save_menu`, `items`, `status`, `controls`, and `quest` defaults remain inherited through the pinned RTP manifest rather than being copied locally.

The bootstrap deliberately contains no Second Gate maps, creatures, items, writing, art, branding, engine policy, combat ontology, or St. Maria content.

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

This is the shell form of the ordinary Test Play boundary. An external Project is staged through `tools/editor/project-play.js`, combining installed runtime code with exactly that Project's `data/` and `assets/`; the temporary stage is removed when LÖVE exits. Same-root Second Gate development remains on the existing direct/no-copy path.

On Windows, the default executable is `C:\Program Files\LOVE\love.exe`. Set `LOVE_PATH` when LÖVE is installed elsewhere. Other platforms resolve `love` from `PATH` unless `LOVE_PATH` is set.

## Inspect a Project

```text
npm run project -- info path/to/game
npm run project -- info path/to/game --json
```

The JSON form is intended for agents/tooling.

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

**Current generator caveat:** its prompt ruleset still assumes Second Gate's roles/elements/skills and therefore its bootstrap remains an explicit compatibility fork for now. New Project itself is neutral. Project-gen must author or select its own core RPG ruleset before it can safely switch to sparse bootstrap; do not silently reintroduce Second Gate rules into a new Project.

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
3. run validation/Test Play through the installed Thestra runtime/staging boundary;
4. never use root Second Gate `data/` or `assets/` as scratch space;
5. preserve each resource's authored-storage representation rather than inventing or copying another catalog's index shape.

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

Related: #237, #299, #390, #392, #479.
