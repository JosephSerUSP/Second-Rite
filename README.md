# Repository orientation

This repository is the **Thestra installation**: reusable LÖVE/Lua runtime and presentation code, Thestra Studio, RTP/authoring infrastructure, tests, gates, and development evidence. The runnable authored game is the ordinary Project at [`projects/hichaukitoden-game/`](projects/hichaukitoden-game/); its player-facing title is **Second Gate**.

The physical monorepo still contains both installation and Project while ownership boundaries continue to mature. Path proximity is not semantic ownership.

## Start here

Repository documents have an explicit authority split. Do not infer current implementation state from old plans or design prose.

1. [`AGENTS.md`](AGENTS.md) — contributor/agent orientation, safety rules, gates, and repository workflow.
2. [`docs/ENGINE-STATE.md`](docs/ENGINE-STATE.md) — generated current-state inventory; highest prose authority for what exists now.
3. [`docs/SPEC.md`](docs/SPEC.md) — reviewed living Thestra behavior/architecture contract.
4. [`docs/design/`](docs/design/) — Thestra runtime/presentation/RTP/Project/Studio design intent; not implementation-status ledgers.
5. [`projects/hichaukitoden-game/docs/`](projects/hichaukitoden-game/docs/) — **Second Gate game-design authority**: game vision, systems, world, characters/creatures, balance intent, and art direction.
6. [`docs/reports/`](docs/reports/) — dated evidence/history for particular investigations.
7. [`docs/archive/`](docs/archive/) — frozen repository history; never current authority.

For concrete Second Gate authored content, inspect the Project's `data/` and `assets/`. For actionable unfinished work, use GitHub Issues. Commercial/release/store/franchise strategy is intentionally outside source-tree authority in the private Second Gate Studio workspace.

When prose disagrees with generated `ENGINE-STATE.md` about engine/editor implementation, treat the generated state as current truth and investigate the discrepancy rather than silently choosing a convenient source. Project game-intent prose likewise does not make an unimplemented mechanic exist.

The game/commercial documentation split is recorded in [`docs/reports/second-gate-document-authority-audit-2026-08-18.md`](docs/reports/second-gate-document-authority-audit-2026-08-18.md).

## Local prerequisites

For ordinary development you need:

- **LÖVE** available locally. The Windows helper scripts assume the standard installation under `C:\Program Files\LOVE\`.
- **Node.js + npm** for Thestra Studio, Project launch/staging, and editor tooling. Install locked dependencies with `npm ci`.
- **PowerShell** for the Windows golden-gate wrappers.
- **Python + Chrome** only when running editor screenshot/golden tooling described in `AGENTS.md`.

CI and repository workflows are the authority for pinned/reproducible tool versions. Do not update runtimes or regenerate visual references merely to make a local mismatch disappear.

## Run

### Second Gate

On Windows:

```bat
run.bat
```

The helper launches the Project through the canonical Project CLI. Equivalent repository-root command:

```text
node studio/editor/project-cli.js play projects/hichaukitoden-game
```

The repository root itself is **not** a runnable game. Do not use bare `love .` / `lovec .` commands as if root owned Project data.

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

Executable game gates run against a **staged Project**, not the repository root. Follow [`AGENTS.md`](AGENTS.md) for the current staging and gate commands; CI uses the same canonical Project-export boundary.

The full deterministic/golden suite is documented in `AGENTS.md` and [`docs/SPEC.md`](docs/SPEC.md). In particular:

- G2/G3 guard deterministic battle/UI traces.
- G4 verifies generated `ENGINE-STATE.md` currency.
- G5 guards rendered game frames.
- G6 guards rendered Studio/editor frames.

**Never recapture or regenerate G5/G6 references simply to make a failing gate green.** Committed visual references are owner-controlled evidence. Relative hosted A/B workflows can establish whether a candidate changed rendering, but they do not authorize replacing accepted references.

## Source tree

| Path | Role |
| --- | --- |
| `engine/` | reusable runtime semantics and authoritative domain behavior |
| `presentation/` | reusable rendering, UI, animation, and presentation consumers of engine truth |
| `projects/hichaukitoden-game/` | Second Gate Project: authored `data/`, `assets/`, and game-design `docs/` |
| `studio/editor/` | Thestra Studio application and authoring tooling |
| `tools/export/` | Project staging/export and hermetic materialization tooling |
| `tools/golden/` | deterministic and visual verification infrastructure |
| `tools/delegate/` | delegated-agent task/provenance workflow |
| `tests/` | unit/characterization/regression tests |
| `.github/workflows/` | hosted verification and experiment workflows |
| `docs/` | Thestra specification/state/design, dated technical evidence, and repository archive |

The physical monorepo is still being made to reflect semantic Project/runtime/Studio boundaries. Treat current path placement as implementation reality, not permission to collapse those owners together; `docs/SPEC.md` and relevant open Issues own the technical boundary contract.

## Golden/reference ownership

Golden artifacts are evidence, not disposable test output. A red visual gate means “investigate the difference,” not “accept whatever was just rendered.” See `AGENTS.md` for absolute vs relative G5/G6 workflow and the owner-signoff rule.

## Licensing

Repository-wide licensing is intentionally not inferred from npm package metadata. The code/data/asset licensing boundary is an explicit owner decision tracked in issue #354. Until that policy is resolved and published, do not assume `package.json` grants repository-wide permission over authored game data, assets, reports, or third-party material.
