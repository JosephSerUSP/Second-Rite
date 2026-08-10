# Current LÖVE 12 shadow capture

**DO NOT MERGE THESE GENERATED GOLDENS.** This branch is a visual-comparison laboratory for #251, not an accepted G5/G6 recapture.

- baseline runtime: `LOVE 11.5 (Mysterious Mysteries)`
- candidate runtime: `LOVE 12.0 (Bestest Friend)`
- candidate upstream commit: `853f1cad4bb65d63f02dbcd3fa31b0c622d3abbc`
- candidate upstream Actions run: `31261258544`
- renderer on both sides: identical Mesa 26.1.6 software OpenGL on the same `windows-latest` runner
- baseline commit: `5acb0c6cdf3ef714892432c5ca0ba2f0a0fffb5f`
- nonvisual compatibility diagnostics: `G1 validate=PASS; unit=FAIL(1); save=PASS; G2 battle trace=PASS; G3 UI smoke=PASS; G4 engine state=PASS`
- refresh workflow: https://github.com/JosephSerUSP/Second-Rite/actions/runs/31398333427

## Decoded-pixel comparison

| set | differing PNGs | total PNGs | changed RGBA pixels | total pixels | changed |
|---|---:|---:|---:|---:|---:|
| G5 Classic | 8 | 144 | 15944 | 8847360 | 0.18% |
| G5 Wide | 8 | 34 | 15944 | 3476160 | 0.46% |

## How to review

Open the newest commit named **`review: capture LÖVE 12 candidate`** and inspect its PNG changes. Its parent is the immediately preceding LÖVE 11.5 capture made on the same runner, so GitHub's image diff is a runtime-to-runtime comparison rather than a cross-machine comparison.

Check `docs/reports/love12-shadow-control.md` first. Any path that moved between the two 11.5 control captures is nondeterministic and cannot be blamed on LÖVE 12.

> G6 is temporarily excluded from this native-image paired capture because #253 still makes `map-editor/map-properties.png` nondeterministic in the same-runtime repeat control. #259 is fixed and hosted G6 now completes; the canonical relative G6 workflow can exclude unstable frames, while this native PNG review waits for a deterministic baseline.

Nonvisual diagnostics in this shadow report are observations, not waived gates. The eventual #251 migration PR must make every required compatibility gate pass.

Accepted golden references on `main` remain owner-signed. Nothing in this branch changes that rule.

## Changed paths

### G5 Classic

- `menu/title/00-initial.png`
- `menu/title/01-after-down.png`
- `menu/title/02-after-return.png`
- `menu/title/03-after-return.png`
- `menu/title/04-after-escape.png`
- `menu/title/05-after-down.png`
- `menu/title/06-after-up.png`
- `menu/title/07-after-escape.png`

### G5 Wide

- `menu/title/00-initial.png`
- `menu/title/01-after-down.png`
- `menu/title/02-after-return.png`
- `menu/title/03-after-return.png`
- `menu/title/04-after-escape.png`
- `menu/title/05-after-down.png`
- `menu/title/06-after-up.png`
- `menu/title/07-after-escape.png`

