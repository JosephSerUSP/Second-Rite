# Thestra Projects

A **Project** is one authored/runnable game. Studio/runtime installation and the opened Project are separate roots; a Project is currently recognized by its `data/` directory, with Project-owned assets conventionally under `assets/`.

There is no Campaign-style alternate active-content root inside a Project.

## Open a Project

From a checkout/install:

```text
npm start -- --project path/to/game
```

The target is validated before Studio launches. Studio resolves one Project root for the lifetime of the process.

Inside the Electron-hosted Studio, **File -> Open Project…** chooses a Project directory and performs a clean application relaunch against that root. Studio does not hot-swap `PROJECT_ROOT` underneath already-loaded editors, resource versions, or preview services.

## Inspect a Project

```text
npm run project -- info path/to/game
npm run project -- info path/to/game --json
```

The JSON form is intended for agents/tooling.

## Fork a Project for isolated work

A Project fork copies only the source Project's `data/` and `assets/` trees into a new root. It does not clone the repository, editor, runtime, reports, or arbitrary source-root files.

```text
npm run project -- fork . projects/labs/my-game
npm start -- --project projects/labs/my-game
```

The target must not already exist. Missing parent folders are created. A target may live elsewhere in the same monorepo (for example `projects/labs/...`), but may not be placed inside the source Project's `data/` or `assets/` trees.

**Fork Project is an isolation operation, not a claim that the new game is blank.** On current main it starts from the named source Project's authored data/assets.

This is useful today for:

- Jules experiments that should produce reviewable Project content without editing Second Gate;
- goal-mode agents that need a private game root before iterating;
- humans making a deliberate Project variant.

## Generate a game into an explicit Project root

The existing staged Project generator can target a reviewable root instead of `tmp/`:

```text
node tools/campaign-gen/generate-project.js \
  --project projects/labs/mist-isle \
  "A melancholy island of drowned bells..."
```

The wrapper chooses the destination; the existing generator still owns outline/content stages, real-engine validation, and repair.

The generated Project can then be opened normally:

```text
npm start -- --project projects/labs/mist-isle
```

## Agent rule of thumb

For an agent asked to create or radically experiment with a separate game inside this repository:

1. establish an explicit Project root first;
2. make content edits only beneath that Project root;
3. run validation/Test Play through the installed Thestra runtime/staging boundary;
4. never use root Second Gate `data/` or `assets/` as scratch space.

For a compatibility fork:

```text
npm run project -- fork . projects/labs/<slug>
```

For full prompt-driven generation:

```text
node tools/campaign-gen/generate-project.js --project projects/labs/<slug> "<goal/pitch>"
```

## New sparse Project status

`npm run project -- create <target>` and Studio's **New Project…** intentionally do **not** copy Second Gate and call it blank.

A truly sparse Project needs the neutral inherited engine/Scene/Flow authored defaults owned by issue #390. Until that baseline is on current main, sparse creation fails with `SPARSE_PROJECT_UNAVAILABLE` and explains why. **Fork Project** remains available for explicit isolation.

The Project lifecycle API already separates `sparse` and `fork` creation modes, so #390 can make sparse creation real without changing Studio, Luna/Jules, or CLI callers.

## Security / ownership boundary

Project selection is not exposed as an arbitrary browser/server filesystem endpoint. The browser editor receives only a bounded Electron preload bridge when running under Electron; CLI callers use the filesystem lifecycle module directly. Browser-only/golden Studio hosting does not gain Project-root mutation authority.

Related: #237, #299, #390, #392, #479.
