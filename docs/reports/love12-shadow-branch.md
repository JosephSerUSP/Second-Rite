# LÖVE 12 shadow branch

Branch: `compat/love12`
Tracking issue: #251
Permanent draft comparison PR: #257

This branch is a long-lived compatibility and visual-comparison laboratory for LÖVE 12. It is intentionally not the production migration branch and its generated golden changes must not be merged into `main`.

## Purpose

Keep a controlled counterfactual available while production remains on LÖVE 11.5:

> same Second Rite revision, same hosted runner and software renderer, different LÖVE runtime.

The branch exists so renderer changes can be inspected visually rather than inferred from hashes or aggregate pixel counts. It also gives us a place to keep small LÖVE-12-only compatibility experiments without pretending that the unreleased runtime is production-ready.

## Golden review protocol

`.github/workflows/love12-shadow.yml` refreshes the comparison as a paired commit sequence:

1. `review: capture LÖVE 11.5 baseline`
2. `review: capture LÖVE 12 candidate`

Both captures run on the same `windows-latest` job with the same pinned Mesa software OpenGL build. The candidate commit's direct parent is therefore the baseline capture from the same environment.

To review a refresh, open the newest **candidate** commit on GitHub and inspect its changed PNGs. GitHub's image diff compares those LÖVE 12 frames directly with the immediately preceding 11.5 frames.

The paired visual capture currently covers:

- all canonical G5 Classic frames;
- the curated G5 Wide set defined by `tools/golden/screens.py`.

Each refresh first performs **two consecutive LÖVE 11.5 G5 captures** and writes `docs/reports/love12-shadow-control.md`. Any path that moves there is same-runtime nondeterminism and must not be attributed to LÖVE 12. The candidate report, `docs/reports/love12-shadow-current.md`, records decoded-pixel counts and the exact changed frame list.

### Why G6 is temporarily separate

#259 is complete: the hosted editor capture can once again finish all G6 frames. The remaining reason not to fold G6 into this **native GitHub image-diff** laboratory is #253: `map-editor/map-properties.png` still changes between same-runtime repeat captures.

The canonical relative G6 workflow introduced by #276 handles that correctly by reading the repeat control first, naming unstable frames, and excluding them from the candidate verdict. This shadow branch serves a different purpose: its candidate commit is meant to be inspected directly with GitHub's PNG before/after UI. Until #253 is deterministic, a moving baseline frame would make that native image review ambiguous.

So G6 is no longer blocked from hosted regression testing; it is only deferred from this particular native-image presentation until its baseline is stable.

## Golden ownership rule

Nothing about this branch weakens the normal golden rule.

Generated images here are **review evidence**, not accepted references. A LÖVE 12 frame looking correct, harmless, or even better does not authorize an automatic recapture on `main`. When the stable migration happens, any accepted G5/G6 reference change still requires owner review and sign-off.

## Runtime pin

The initial candidate is the same development build used by the #246 migration spike:

- upstream commit `853f1cad4bb65d63f02dbcd3fa31b0c622d3abbc`;
- upstream Actions run `31261258544`;
- Windows x64 artifact from that run.

This pin is deliberately temporary. LÖVE 12 is still a development target at the time this branch was created. When a newer comparison point is intentionally chosen, update the pin explicitly. When 12.0 becomes stable, replace the development artifact with the official release archive and a SHA-256 digest before treating this branch as migration evidence.

## Relationship to `main`

`main` remains the production line and stays on LÖVE 11.5 until the stable migration decision in #251.

When the shadow branch is refreshed from `main`, keep the experiment narrow: synchronize current production code, make only compatibility changes needed to run under the candidate runtime, then regenerate the paired visual capture. Do not let ordinary feature development accumulate here independently of `main`.

## Relationship to the migration PR

The permanent draft PR attached to this branch is an observation window, not a merge candidate. The eventual stable LÖVE 12 migration should be proposed separately once #251 is unblocked. At that point the shadow branch provides evidence and known fixes, but the real migration PR should contain only intentional runtime/tooling changes plus owner-approved golden updates.
