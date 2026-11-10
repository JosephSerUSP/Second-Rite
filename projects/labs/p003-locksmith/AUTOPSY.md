### Experiment
P003 — The Locksmith

### Result
complete

### Authored Surface
Authored Map with Events, Items, and sparse Project setup.

### SCRIPT / Native Escape Hatches
None used.

### Missing Reusable Semantics
None needed for this small experiment.

### Awkward But Expressible
Map events without dedicated graphics require reading text to know what they are. Using items as quest flags works via CONDITIONAL_BRANCH, but having a proper lock/key primitive could be nice, although item-checking is adequate.

### Tooling / Discoverability Gaps
No project creation CLI command is exposed, meaning one has to run an internal script or author JSON by hand to set up a sparse project outside of Studio.

### Backend Leakage
None. The game uses standard authored JSON files.

### Project Leakage
The project is entirely contained in `projects/labs/p003-locksmith` and relies only on the sparse RTP.

### Author Legibility
Yes, a competent RPG Maker-style event author would completely understand the use of `CONDITIONAL_BRANCH` to check for `item:2` and `item:1` on the door, and the use of `CHANGE_ITEMS` on the chest and NPC.

### Reusable Successes
The existing item database and event conditional branching system flawlessly support lock/key puzzles and branching inventory-based progression.

### Architecture Recommendation
tooling improvement indicated
