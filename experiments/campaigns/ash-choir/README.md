# ASH CHOIR

> EXPERIMENTAL / MACHINE-AUTHORED / NOT CANON.

## HOW TO PLAY

From this repository, double-click [`PLAY_CAMPAIGN.cmd`](PLAY_CAMPAIGN.cmd),
choose **New Game**, and follow the town's ordinary route. The launcher mirrors
the shared Second Gate art into this isolated Project and then uses the normal
Thestra Test Play lifecycle.

The direct equivalent is:

```text
npm run project -- play experiments/campaigns/ash-choir
```

Use arrow keys to move and select, Enter to confirm/interact, and Escape to
cancel or skip a cinematic. Save/load is available through the Map menu.

## EXPECTED LENGTH

About **45–75 minutes** for a first ending. The game is intentionally compact:
two expeditions, three distinct floors, one optional creature contract, one
mandatory return-to-town resupply beat, and a final threshold with two endings.

## KNOWN ROUGH EDGES

- Dungeon room placement is procedural. The authored rooms are guaranteed to
  be placed legally, but the minimap is the best way to find them.
- The final battle uses the live battle/strain rules and has machine-authored
  balance. If it feels too easy or too severe, record that in the journal.
- The generic engine currently returns an authored ending to a quiet map
  epilogue rather than closing the process. This campaign treats that as its
  final St. Maria beat; it is a Thestra gap, not a campaign-specific command.
- Shared art is intentionally reused from the current Second Gate Project and
  is mirrored locally by the launcher rather than duplicated in this branch.

## Premise

Each descent leaves gray writing on the contracts of the creatures who made it
back. St. Maria calls it ash. The Labyrinth calls it a receipt. Return twice,
then decide whether the ember at the center of the Ash Choir belongs to the
town, the contract, or nobody.

## Major sections

| Section | Place | Purpose |
| --- | --- | --- |
| Arrival | St. Maria | Saban, the Crossing Writ, and three town voices |
| First expedition | Gray Threshold → Salt Gallery | Recruitment temptation, MP pressure, charges and loot |
| Return beat | Alicia / Agnes | A remembered expedition changes what the town offers |
| Second expedition | Gray Threshold → Salt Gallery → Ash Choir | Revisit, remix, escalation and the proper Stratum climax |
| Ending | Ash Choir → St. Maria | Carry the ember home or break it over the contract |

## Complete walkthrough (spoilers)

1. Finish the arrival film and explore St. Maria. Speak to Registrar Celina to
   receive the Crossing Writ; Alicia, Agnes, Laura and the Scholar each add a
   different angle on the town's relationship with Summoners.
2. At the Gate Guard, begin the first expedition. On Floor 1, find the Gray
   Ledger and choose whether to take its Ether Seed. Find the Contract in the
   Seam and either recruit the Pixie or leave it space. Continue down to Floor
   2, then use the entrance stairs to climb back through Floor 1 to town.
3. On the return, speak to Alicia. Her Ash Supper supplies a Town Portal and,
   if you tell her what happened, Bell Salt. The Portal is the retreat tool;
   Bell Salt restores local skill charges, while MP remains the strategic
   expedition horizon.
4. Speak to Agnes, then return to the Gate Guard and begin the second
   expedition. Revisit the Gray Ledger and Salt Gallery if desired. The Salt
   Mirror offers Bell Salt; the Listening Stair trades 35 MP for a name from
   Saban's erased contract. Use a Town Portal if the walk home is becoming a
   worse risk than the discovery.
5. Reach Floor 3 and find the Ash Choir. You may mark the threshold and retreat
   or enter the guardian battle. Victory supplies the final ember and opens the
   ending.
6. Choose **Carry the ember back to St. Maria** or **Break the ember over the
   contract**. Read the `ASH CHOIR — END` card, then visit Agnes or Alicia for
   the short epilogue reaction. Complete [`OWNER-JOURNAL.md`](OWNER-JOURNAL.md)
   before opening the critic directory.

The route is a campaign-specific interpretation of current Second Gate
systems, not a canon claim. The Ash Choir, the gray receipt/ember reading, the
compressed two-expedition pacing, the Pixie contract scene, and both endings
are experimental authorship.

## Validation and evidence

See [`VALIDATION.md`](VALIDATION.md) for exact commands and results. The
campaign is intended to be machine-validated and ready for owner playtest; the
owner journal is deliberately blank until a human has played it.

Critic reports, when API configuration permits, are held in
[`critics/`](critics/) until the owner rating is written.
