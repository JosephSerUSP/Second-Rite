# Validation record

## Passed

- External Project staging succeeded through the ordinary Thestra Test Play
  boundary.
- `lovec <staged-project> validate` completed with `VALIDATE OK` on
  2026-08-17.
- The New Game title hook points to Project-local common event `44`,
  **Glasswake Opening**.
- The authored route is structurally traversable through the existing map exit
  chain: St. Maria (1) → Entry Hall (2) → Chasm Crossing (3) → Rusted Choir
  (4). Map 4's Red Dragon Guardian retains the event after its victory and its
  defeated-state branch contains the ending choice and `GLASSWAKE COMPLETE`.
- JSON parsing and `git diff --check` passed locally.

## Structured smoke traversal

The project was smoke-checked as authored data rather than claiming an
autonomous visual playthrough: New Game → common event 44 → map 1, the existing
dungeon entrance event → map 2, each generated floor exit to the next map,
and map 4's boss event → defeated branch → two authored endings. Validation
resolves all referenced commands, maps, items, troops, and the nested ending
command lists.

## Untested seam

No human-like input bot currently completes a full external-project campaign
route. The owner should therefore treat encounter balance, controller feel,
and the final in-game text cadence as playtest questions rather than certified
by this structural smoke. No debug cheat is required by the authored path.
