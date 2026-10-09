# Basement loop verification — 2026-10-09

The ordinary Hospital Project now binds twelve route areas through the complete
basement fuse/key/wire/power return loop. These are repeated original lit proxy
rooms, not source-measured Hospital architecture. Wards and combat are outside
this bounded construction unit; #1465 remains open for the rest of M1.

Door Events read package-owned blue-door anchors. Interaction Events read a
separate source-authored workstation anchor. The adopted service-room Blender
document was directly edited to mark its central workstation top; exported
candidate captures were reviewed before product adoption. Room identity and
power objectives are displayed in the HUD. Destination choices support Leave
and Cancel, and parallel first-visit/powered elevator paths share one choice.

Inventory owns Autopsy Key, Blue Cardkey and the three fuse identities. Persistent
pickup history prevents duplicate collection. Installed fuses, wire repair and
ward availability are distinct Game Variables, while power has one powerState
owner. Prototype retention keeps keys/fuses carried after use/installation;
source-confirmed retirement/consumption is still required before fidelity
acceptance. Installation and repair cannot repeat. No combat or resource tuning
is inferred from these traversal results.

Actual-host input starts at the title and drives the route without position,
inventory or flag injection. It checks menu cancellation, the powerless elevator,
locked Autopsy/Blue Cardkey gates, duplicate pickup, missing installation, missing
wire repair, pre-power and restored-power save/load, pickup revisit after save,
and powered elevator travel in both directions without replaying the crash.
The same probe must fail when a disposable stage severs elevator transfers or
bypasses the fusebox guard. The preparation command retains logs, three native
captures and timings under out/hospital-basement/final.

The shared hasItem condition previously converted every item id to a number,
so string Project ids could never open their authored gates. It now preserves
string ids while retaining numeric-id behavior. Tests cover both; shipping G1,
full staged units, G3 and G4 passed locally. Production Battle owners are
unchanged. No golden references were recaptured or owner play accepted.

The previous commit's dedicated Hospital CI and main gates passed. Broader
Studio and item-source failures are recorded in #1494/#1495; parent comparison
is pending, so this report does not classify them as baseline failures. Remote
checks for this new revision remain separate from local verification.
