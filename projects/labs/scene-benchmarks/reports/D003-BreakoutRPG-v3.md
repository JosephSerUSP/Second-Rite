### Experiment
D003 - Breakout as RPG Encounter Metaphor

### Result
complete

### Authored Surface
`projects/labs/scene-benchmarks/data/scenes/d003_breakout_rpg.json` (Authored Scene)
The implementation models the "Breakout" structure entirely through turn-based RPG state without literal X/Y coordinate physics. The paddle translates to an active "Ward" positioned in one of three lanes (Left, Center, Right), the bricks to enemy troops stacked in those lanes, and the bouncing ball to an "Energy Orb" advancing and retreating across distances.

### SCRIPT / Native Escape Hatches
None. The entire scene uses standard `SET_VAR` and `IF` command composition. It fundamentally avoids the text-grid string concatenations that dominated earlier attempts.

### Missing Reusable Semantics
- **Targeting / Collections without Arrays:** Even simplified to 3 lanes, handling each lane individually requires hardcoded `IF` conditions (`orb_col == 1`, `orb_col == 2`, etc.). If the design required 10 lanes or an arbitrary number of enemies, it would scale poorly without array iteration or dynamic variable keys.

### Awkward But Expressible
- Resolving state updates (like bouncing the orb or moving the ward) in a single turn hook (`on_select`) means meticulously stacking `IF` logic to execute physics chronologically over standard integer states (`orb_dist`, `orb_dir`). It is fully expressible but can become verbose.

### Tooling / Discoverability Gaps
No special tooling gaps for this specific metaphor logic. Constructing simple integers and checking them sequentially is what typical Studio Event pages are designed for.

### Backend Leakage
None. The logic only utilizes native math helpers (`min`, `max`) natively exposed by the formula evaluator. It should translate cleanly to any backend correctly implementing the Thestra semantic contracts for `SET_VAR` and `IF`.

### Project Leakage
None. The logic lives completely inside the benchmark boundaries.

### Author Legibility
An event-oriented game author would likely find this implementation substantially more legible than the previous 5x5 literal text-grid approach. It models combat conceptually (lane counts, positions, hits) and heavily relies on basic arithmetic, similar to how RPG Maker authors create custom combat systems with Event Variables and Switches.

### Reusable Successes
- The native math helpers `min()` and `max()` trivially handled bounding the ward's movement inside the 3 lanes.
- Text interpolation in the `windows` layer cleanly resolved ternary state into RPG-friendly strings (e.g., `{v.orb_col == 1 and 'Left' or ...}`) natively tracking real-time logic changes.
- The multi-assignment support in `SET_VAR` gracefully managed multiple simultaneous state changes without needing individual commands.

### Architecture Recommendation
no architecture change indicated

### Owner Playtest

- **Status:** READY FOR OWNER PLAYTEST
- **Launch:** Run `npm run lab:benchmarks` and select `D003 Breakout RPG`
- **Observations:** [pending]
- **Result:** [pending]
