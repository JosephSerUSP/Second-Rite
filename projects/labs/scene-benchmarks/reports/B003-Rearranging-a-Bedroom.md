### Experiment
B003 — Rearranging a Bedroom

### Result
* complete

### Authored Surface
- `b003_bedroom.json` (Custom Scene, using `windows` draw mode)
- `index.json` (Registered Scene)
- `title.json` (Added to title menu hooks)
- `terms.json` (Added option and destination terms)

### SCRIPT / Native Escape Hatches
- None. The room state, swapping logic, and narrative revelation were implemented entirely using standard `IF` and `SET_VAR` event commands.

### Missing Reusable Semantics
- None. The existing variables and branching commands are sufficient for managing persistent spatial arrangements and narrative feedback based on composition.

### Awkward But Expressible
- The object swapping logic is verbose since we must check the source location of the moved item and manually swap it with the destination item using a temporary variable `temp_item`.
- Modifying list contents dynamically requires maintaining multiple arrays in `terms.json` and switching between them using dynamic `listId` formulation (e.g. `term:b003.{v.menu_type}`). It is elegant, but heavily relies on string concatenation behavior inside bindings.

### Tooling / Discoverability Gaps
- The ability to dynamically change the `listId` of a list window based on a formula like `term:b003.{v.menu_type}` is a powerful feature of the UI layer, but writing the cursor management logic (knowing how many elements exist) and managing the "state machine" (options vs destinations) can be error-prone to manually script in JSON. A higher-level state management visual editor would help here.

### Backend Leakage
- None.

### Project Leakage
- None.

### Author Legibility
- The implementation is completely constructed from basic primitives: variables represent state (`desk_item`, `bed_item`, etc.), conditions trigger logic based on these variables, and `SET_VAR` manipulates the text dynamically. An RPG Maker author would easily understand this pattern, as it maps directly to using variables and conditional branches for room interaction.

### Reusable Successes
- The `windows` layout system paired with text binding (`{v.desk_item}`) automatically handles keeping the presentation synchronized with the logical state.
- Dynamic list bindings (`listId`) successfully allow reusing a single window definition for both the main menu and destination menu seamlessly.

### Architecture Recommendation
- no architecture change indicated

### Owner Playtest

**Status:** READY FOR OWNER PLAYTEST

**Instructions:**
1. `npm run lab:benchmarks`
2. Select "B003  Rearranging a Bedroom" from the title screen.
3. Select an object to move from the options menu.
4. Select a destination for the object. The item currently at the destination will swap with the moving object.
5. Use "Assess Room" to see the narrative feedback dynamically react to your arrangement.
6. Press B to return to the launcher menu at any time.

**Observations:**
- (Pending owner observations)

**Result:**
- (Pending owner result)
