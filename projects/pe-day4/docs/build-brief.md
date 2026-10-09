# First Hospital build brief

This is implementation intent for #1463/#1465, not a delivery-status checklist.
Use the ordinary Project under `projects/pe-day4`; do not fork the Day 1 host or
invent a Hospital-specific engine. The continuous-surface dependency is draft
PR #1403. The preparation branch is stacked on its reviewed-play checkpoint;
integration into main remains a separate review action.

## First complete unit: basement power loop

Build the basement as a connected place before expanding to wards or the roof:
landing A -> corridor B -> storage / morgue -> locked autopsy room / inner room
-> corridor C -> Blue Cardkey gate into D -> office / fusebox -> powered return
to A -> functioning elevator back to 1F. This unit uses ten basement areas from
`reference/route.json`, plus the entry/1F areas.

The route source places the Blue Cardkey panel between C and D. C is approachable
before possessing the card. Follow that dependency rather than copying the old
early-gated B-to-C interpretation. Do not add an invisible shortcut for tests.

Each room needs an authored visible entrance/exit, a grounded player silhouette,
readable interaction subjects and collision matching beauty geometry. Introduce
new Blender source documents for Hospital rooms, with explicit spatial
collections; the two neutral starter documents are a kit, not Hospital layouts.
Keep baked UVs perspective-correct. Use lit floor/wall volumes and distinguish
powered/unpowered presentation without making navigation unreadable.

Reference flags are abstract contract predicates, not a requirement to duplicate
inventory into boolean variables. Bind possession to the inventory owner, and
bind mutually exclusive power predicates to the single `powerState` variable,
as the starter does. Keep installed-fuse state distinct from possession.

Pickups use existing inventory commands and one-time Event/self-state. Keys gate
ordinary IF/CHOICE/LOAD_MAP programs. Power, repaired wires, installed fuses and
opened routes use existing persistent Game Variables/pages. The route contract
must distinguish possessing a fuse from installing it; once installed, returning
to the shelf must not duplicate it. Retirement/consumption policy stays explicit
until source-confirmed. Elevator crash is one-shot; restoring power must never
allow it to reset the building to the first-visit state.

The first native proof walks the full loop through ordinary input, checks locked
doors before collecting their keys, revisits changed rooms, and round-trips a
pre-power and a restored-power save. Severing a required key/fuse/transfer must
make the proof fail. No direct actor-position or flag assignments after start.

## Runtime boundaries

| Need | Existing seam | Work required for this slice |
|---|---|---|
| Continuous motion, collision, arrival and saves | Package walkSurface + traversal provider + ordinary LOAD_MAP | Author room packages and visible Events |
| Persistent power, keys and one-time changes | IF/CHOICE, inventory commands, Game Variables, Event pages/self-state | Compose programs in Project data |
| Lit fixed-camera presentation | Adopted Blender sources, shared export, existing WorldCamera | Author Hospital composition; measure source references |
| Characters | chara-compiler GLB + shared skeletal presentation | Author appropriate silhouettes and clips; retain provenance |
| Action commitment/contact/recovery | action_timeline + action_execution + arena_host | Measure reference timing/arbitration before calibration |
| Multiple spatial enemies and PE actions | Current gauntlet is one enemy / one basic Attack | Design bounded host extensions for #1466; do not call this complete |
| Ammo, magazines, BP and Tune-Up | Inventory/equipment and persistent state are available | Bind PE policy and add only justified missing primitives in #1467 |
| One boss across two arenas | Current active arena rejects ordinary Map transfer | Design encounter-preserving relocation for #1468; never end/restart a fake second boss |
| Escape deadline | Existing authored timers/Scene update vocabulary | Prove success and deadline failure under deterministic input |

Production `runtime/engine/battle.lua` and `runtime/engine/scenes/battle.lua`
remain owner-supervised. No preparation change requires editing them. Active
arena saves remain explicitly rejected; persistence proofs can save before
triggering an uncleared encounter and after clearing it. Any different save
policy requires its own source evidence and design.

## Reference measurements before mechanical acceptance

The source-facts contract intentionally leaves these bindings unresolved:
level-18 HP/PE, M9-2/N Jacket parameters, loaded-versus-carried ammunition,
handgun commitment/contact/recovery, menu pause behavior and enemy advancement
during player execution. Existing original-game stills are composition evidence,
not timing measurements. Use `reference/capture-plan.json` for the evidence pass.

There are also conflicting Hospital enemy HP values across independent guides.
Do not average them, silently prefer the lower values, or copy Day 1 tuning.
Resolve version/variant identity from original-game data or controlled capture.
Spiderwoman phase-versus-total HP and the 35-second escape report remain
explicitly unresolved/weak where tagged in facts.json.

M1 traversal can progress with original proxy art and prototype stats. M2 enemy
behavior can progress independently of full economy, but its honest resource
completion gate depends on the minimum M3 magazine/equipment binding. Do not
sign off that gate before resource rules exist. M4 follows those semantics.

Keep graph reachability, actual-input traversal, mechanical resource completion,
save/load, visual review and owner play as separate evidence. The starter's
snapshot identity load proves none of the missing PE combat semantics.

The owner-selected endpoint includes the normal gondola Spider fight after the
rooftop escape. Safe arrival clears the escape timer; only the separate final
encounter victory completes Hospital. Preserve that distinction in M4 proofs.
