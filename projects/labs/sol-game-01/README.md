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

Exact-head evidence for the current Project now satisfies that gate:

- Project-local validation completed with `VALIDATE OK`;
- fail-closed ordinary boot remained alive through the smoke window without entering LÖVE's error handler;
- the title plus all six Maps produced real-engine review PNGs;
- those captures were inspected after the visual vocabulary pass and the final title correction: the title is legible, Maps are materially distinguishable, and the walkthrough's interaction targets have visible authored fixtures.

Readiness states:

- **AUTHORED:** yes
- **MACHINE VALIDATED:** yes
- **READY FOR OWNER PLAYTEST:** yes
- **OWNER PLAYTESTED:** no; only the owner may assert this after personally playing the game

## Reproducible visual-authoring proof (#531)

The current vocabulary is intentionally programmatic, not canonical Second
Gate art. Its retained source is
`art/source/dead-air-visual-vocabulary.json`, with Project direction and the
image-model prompt seam in `art/asset-gen.json` and `art/prompts/`.

Regenerate the complete vocabulary and verify it without writing:

```text
python tools/asset-gen/gen.py --project projects/labs/sol-game-01 \
  raster art/source/dead-air-visual-vocabulary.json
python tools/asset-gen/gen.py --project projects/labs/sol-game-01 \
  raster art/source/dead-air-visual-vocabulary.json --check
```

The source emits the 128x128 exchange atlas, ten 32x48 wall fixtures, a
48x16 lamp pictogram strip, and a 40x24 grayscale interaction mask. The
non-standard 48x16 and 40x24 outputs are deliberate proof that the raster lane
does not force the global image-model classes.

Review evidence is retained beside the source:

- [contact sheet](art/review/visual-contact-sheet.png)
- [raster provenance](art/provenance/raster-manifest.json)
- [exact-engine capture manifest](art/review/in-engine-captures.json)
- [main floor capture](art/review/captures/main-floor.png)
- [Booth A capture](art/review/captures/booth-a.png)
- [broadcast ending capture](art/review/captures/broadcast-ending.png)
- [archive ending capture](art/review/captures/archive-ending.png)

Recapture those frames through the real Project staging/runtime and raycaster:

```text
node tools/asset-gen/capture_project.js --project projects/labs/sol-game-01 \
  --capture main-floor=1,6,4,N \
  --capture booth-a=2,4,5,N \
  --capture broadcast-ending=5,3,3,N \
  --capture archive-ending=6,3,3,N
```

The captures prove readability in context rather than only in the source PNGs:
the main floor exposes the terminal, Booth A exposes the handset, and the two
ending maps expose the distinct broadcast/archive fixtures. The limitations
are intentional: the helper captures deterministic camera frames, not a full
player-input walkthrough, and the raster lane supplies no anti-aliased or
model-backed texture authoring. Owner playtest remains pending.

## Ownership

Everything under this Project that constitutes game content was authored for DEAD AIR AT 05:17. Root Second Gate `data/` and `assets/` are not runtime dependencies or content sources. The only inheritance is the pinned Thestra RTP semantic/default layer described by the Project architecture.
