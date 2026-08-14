# Repository orientation

This repository contains a runnable authored game Project together with the reusable Thestra runtime, presentation layer, Thestra Studio authoring application, and the development/verification tooling used to build them. The game’s display name is authored data rather than a repository identifier; follow the naming contract in [issue #288](../../issues/288) and the current authored terms instead of introducing product-name constants in code or paths.

## Start here

Repository documents have an explicit authority order. Do not infer current implementation state from old plans or design prose.

1. [`AGENTS.md`](AGENTS.md) — contributor/agent orientation, safety rules, gates, and repository workflow.
2. [`docs/ENGINE-STATE.md`](docs/ENGINE-STATE.md) — generated current-state inventory; highest authority for what exists now.
3. [`docs/SPEC.md`](docs/SPEC.md) — reviewed living behavior/architecture contract.
4. [`docs/design/`](docs/design/) and [`docs/game design/`](docs/game%20design/) — intent, constraints, and rationale; not implementation-status ledgers.
5. [`docs/reports/`](docs/reports/) — dated evidence/history for particular investigations.
6. [`docs/archive/`](docs/archive/) — frozen historical plans; never current authority.

When prose disagrees with generated `ENGINE-STATE.md`, treat the generated state as current truth and investigate the discrepancy rather than silently choosing a convenient source.

## Local prerequisites

For ordinary development you need:

- **LÖVE** available locally. The Windows helper scripts assume the standard installation under `C:\Program Files\LOVE\`.
- **Node.js + npm** for Thestra Studio and editor tooling. Install the locked dependencies with `npm ci`.
- **PowerShell** for the Windows golden-gate wrappers.
- **Python + Chrome** only when running the editor screenshot/golden tooling described in `AGENTS.md`.

CI and the repository workflows are the authority for pinned/reproducible tool versions. Do not update runtimes or regenerate visual references merely to make a local mismatch disappear.

## Run

### Game/runtime

On Windows:

```bat
run.bat
```

Equivalent direct launch when LÖVE is already on your path:

```text
love .
```

### Thestra Studio

Install dependencies once:

```text
npm ci
```

Then launch:

```bat
runEditor.bat
```

or:

```text
npm start
```

`npm run start:electron` is the raw-Electron fallback for debugging the Studio host itself.

## Verify

The smallest ordinary nonvisual checks are:

```text
lovec . validate
lovec . unittest
lovec . savetest
```

On the owner Windows setup, `lovec` is normally:

```text
C:\Program Files\LOVE\lovec.exe
```

The full deterministic/golden suite is documented in [`AGENTS.md`](AGENTS.md) and [`docs/SPEC.md`](docs/SPEC.md). In particular:

- G2/G3 guard deterministic battle/UI traces.
- G4 verifies generated `ENGINE-STATE.md` currency.
- G5 guards rendered game frames.
- G6 guards rendered Studio/editor frames.

**Never recapture or regenerate G5/G6 references simply to make a failing gate green.** Committed visual references are owner-controlled evidence. Relative hosted A/B workflows can establish whether a candidate changed rendering, but they do not authorize replacing the accepted references.

## Source tree

| Path | Role |
| --- | --- |
| `engine/` | reusable game/runtime semantics and authoritative domain behavior |
| `presentation/` | rendering, UI, animation, and other presentation consumers of engine truth |
| `data/` | current authored Project data plus remaining authored/runtime support surfaces governed by the Project/RTP boundary work |
| `assets/` | current game/runtime asset corpus; ownership/provenance is resource-specific |
| `tools/editor/` | Thestra Studio editor application and authoring tooling |
| `tools/export/` | Project staging/export and hermetic materialization tooling |
| `tools/golden/` | deterministic and visual verification infrastructure |
| `tools/delegate/` | delegated-agent task/provenance workflow |
| `tests/` | unit/characterization/regression tests |
| `.github/workflows/` | hosted verification and experiment workflows |
| `docs/` | living specification, generated state, design intent, dated evidence, and archive |

The physical monorepo is still being made to reflect the semantic Project/runtime/Studio boundaries. Treat current path placement as implementation reality, not as permission to collapse those owners together; [`docs/SPEC.md`](docs/SPEC.md) and the relevant open issues own the boundary contract.

## Golden/reference ownership

Golden artifacts are evidence, not disposable test output. A red visual gate means “investigate the difference,” not “accept whatever was just rendered.” See `AGENTS.md` for the absolute vs relative G5/G6 workflow and the owner-signoff rule.

## Licensing

Repository-wide licensing is intentionally not inferred from the npm package metadata. The code/data/asset licensing boundary is an explicit owner decision tracked in [issue #354](../../issues/354). Until that policy is resolved and published, do not assume the `package.json` license field grants repository-wide permission over authored game data, assets, reports, or third-party material.
