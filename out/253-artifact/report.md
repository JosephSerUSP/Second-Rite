# Relative G6 same-runner A/B

This is a **relative regression check**, not an absolute golden-correctness check. It compares base and candidate on the same hosted runner and does not use an Effekseer shim. A green result never licenses recapturing committed goldens.

- base: `03570ccd6ec4b5d892e24303694244cb1bfc2109`
- candidate: `03570ccd6ec4b5d892e24303694244cb1bfc2109`
- repeat control is read first; unstable control frames are excluded from candidate verdicts

| surface | base A -> base B differing | repeat changed pixels | base B -> candidate differing | candidate changed pixels | unstable frames excluded | stable candidate diffs |
|---|---:|---:|---:|---:|---:|---:|
| editor | 1 | 922 | 0 | 0 | 1 | 0 |

## Verdict

**NO CANDIDATE-ONLY DIFF ON STABLE FRAMES; 1 repeat-control frame(s) are inconclusive and excluded.**

## Repeat-control unstable frames

- `editor/map-editor/map-properties.png`

