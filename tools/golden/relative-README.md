# Hosted relative visual checks

`relative-capture.py` and `compare-relative.py` are CI adapters around the canonical gate recorder. They do not replace G5 or G6 and never update committed golden references.

`relative-capture.py` points the recorder at a detached worktree. G5 needs two recorder passes because the absolute Classic comparison normally stops the canonical PowerShell gate before Wide on a hosted runner; the first pass reconstructs only a disposable Classic reference tree inside that worktree, and the second reaches the canonical crop check and Wide capture. G6 reconstructs the complete capture from the recorder's matching committed references plus its differing actual frames.

`compare-relative.py` consumes base A, base B, and candidate capture trees. It compares decoded RGBA pixels, names base-repeat instability, excludes unstable frames from the candidate verdict, and fails only for candidate differences on repeat-stable frames.

The permanent operator interface is `.github/workflows/relative-golden-ab.yml` via `workflow_dispatch`.
