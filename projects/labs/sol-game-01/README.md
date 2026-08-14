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

Presentation is deliberately asset-light: concrete geometry, empty rooms, text, switchboard language, and the inherited generic RTP font. The absence of character sprites/audio is intentional rather than borrowed placeholder content. The game is meant to feel like an austere lost late-night adventure, not a Second Gate variant.

## Ownership

Everything under this Project that constitutes game content was authored for DEAD AIR AT 05:17. Root Second Gate `data/` and `assets/` are not runtime dependencies or content sources. The only inheritance is the pinned Thestra RTP semantic/default layer described by the Project architecture.
