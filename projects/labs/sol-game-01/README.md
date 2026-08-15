# DEAD AIR AT 05:17

A 10–15 minute first-person narrative routing puzzle authored as an independent sparse Thestra Project.

## Premise and objective

At 05:17, an overnight municipal telephone exchange receives three calls from facilities that no longer exist on any current map. Their trunk labels were stripped during maintenance. The player must listen to each caller, consult the surviving operator log, and route all three lines correctly before the master board will reveal a fourth carrier.

When the fourth carrier stabilizes, the player makes the game's irreversible final decision: broadcast the composite voice to the sleeping city, or archive it privately on the evidence reel.

## Core interaction loop

Explore the exchange -> listen/read -> infer a caller's facility -> set that line's trunk -> return to the master board -> inspect carrier lamps -> revise routes if needed.

The game deliberately uses no battles, units, roles, skills, elements, states, passives, shops, quests, or economy. Those databases remain empty because this game does not need them.

## Thestra capabilities used

- Project lifecycle sparse bootstrap pinned to RTP 1.0
- Project-owned title/map startup identity
- first-person Maps and wall Events
- Project-owned tileset and wall-event sprite presentation
- `TEXT` and `CHOICE`
- persistent session `SET_FLAG`
- `CONDITIONAL_BRANCH`
- `LOAD_MAP`
- inherited neutral engine command registry and reusable RTP defaults

No `SCRIPT` commands and no new native engine primitives are used.

## Rules / puzzle grammar

The operator log on the main floor states:

- NORTH trunk -> MERIDIAN OBSERVATORY
- EAST trunk -> BREAKWATER LIGHT
- WEST trunk -> SLEEP CLINIC

Each booth's call identifies one facility indirectly. Setting the matching trunk makes that line's hidden carrier flag steady. The master board exposes only lamp state, not the answer.

Correct routing:

- Line A -> NORTH (Meridian Observatory)
- Line B -> EAST (Breakwater Light)
- Line C -> WEST (Sleep Clinic)

## Walkthrough: New Game to ending

1. From the title screen choose **Take the Shift**.
2. On the main floor, inspect the Emergency Terminal and the Operator Log.
3. Enter Booth A. Listen to Line A and inspect its service card. Set the route dial to NORTH, then return.
4. Enter Booth B. Listen and inspect. Set Line B to EAST, then return.
5. Enter Booth C. Listen and inspect. Set Line C to WEST, then return.
6. Inspect the Master Board. All three lamps should read **steady**.
7. Choose one final action:
   - **Broadcast the composite voice** -> `END — BROADCAST`
   - **Archive it on the evidence reel** -> `END — ARCHIVE`
8. On the ending map, walk north and bump the final wall event to read the epilogue.

Wrong routes are not softlocks. Every dial can be changed repeatedly and the board reports which carrier lamps are dark.

## Aesthetic / scope

The first authored revision intentionally tried an almost asset-free presentation. Exact-engine review captures proved that experiment failed: all six maps collapsed into nearly identical gray bands and the wall interactions were effectively invisible.

The current candidate therefore carries a deliberately tiny **Project-owned visual vocabulary** rather than borrowing Second Gate assets:

- one 2×2 exchange tileset atlas for service ceiling, panel/cable wall, worn floor, and steel door language;
- small wall-fixture sprites for terminals, booth entries, handsets, service cards, route dials, the master board, operator log, exits, and the two ending targets;
- the inherited generic RTP font for text.

These are navigation/readability assets, not an attempt at a finished art pass. The goal is that a human can recognize where the authored interactions are while the game retains an austere late-night municipal-exchange character.

## Visual review evidence

This Project is **not** considered ready for owner playtest merely because it validates or keeps a LÖVE process alive. The original candidate exposed exactly that mistake: sparse startup crashed on a stale hidden-Summoner assumption while LÖVE's graphical error screen kept the process alive long enough for the old boot smoke to report success.

Current repository policy (`docs/agentic/PLAYABLE-GAME-EVIDENCE.md`) requires the exact candidate to pass fail-closed boot and publish real-engine Scene/Map review captures. Those captures must be inspected for actual human legibility. The Project-owned tileset/fixture pass exists because the first such captures demonstrated that the no-art version was not meaningfully playable.

Readiness states:

- **AUTHORED:** yes
- **MACHINE VALIDATED:** pending exact-head current-main rerun after the visual/readability pass
- **READY FOR OWNER PLAYTEST:** no, until fail-closed boot + current visual review pass
- **OWNER PLAYTESTED:** no; only the owner may assert this

## Ownership

Everything under this Project that constitutes game content was authored for DEAD AIR AT 05:17. Root Second Gate `data/` and `assets/` are not runtime dependencies or content sources. The only inheritance is the pinned Thestra RTP semantic/default layer described by the Project architecture.
