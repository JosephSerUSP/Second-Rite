# THE THIRD BELL

> **EXPERIMENTAL / MACHINE-AUTHORED / NOT CANON.**
> One alternative interpretation of a complete Second Gate playthrough,
> authored end to end by an agent. It is a *what if*, not a proposal.

---

## HOW TO PLAY

From the repository root, run:

```bash
PLAY_CAMPAIGN.cmd
```

Then choose **New Game**. That is the whole setup.

If you would rather use the ordinary lifecycle directly, the launcher is a thin
wrapper around it (it only mirrors the shared art in first):

```bash
npm run project -- play projects/labs/third-bell
```

To open it for editing instead:

```bash
npm start -- --project projects/labs/third-bell
```

**Play it from your primary checkout**, not a worktree — worktrees are missing
the gitignored Effekseer shim, so battle effects will silently disable.

---

## EXPECTED LENGTH

**60–90 minutes** to an ending, playing at a normal pace and reading the text.

It is compressed on purpose. Second Gate's canonical ramp is three incursions
before the Vigil; this campaign takes two. Six floors, one midpoint climax, one
final threshold, three endings, done.

You can finish faster (~45 minutes) by taking the stairs and ignoring the
optional rooms, but the optional rooms are most of the point.

---

## KNOWN ROUGH EDGES

- **The ending does not return you to the title screen.** The engine's
  `QUIT_GAME` and scene-switch commands are scene-context only, and a campaign
  is not allowed to add engine commands to make its story work — so the ending
  plays its credits and then drops you into a changed St. Maria as an epilogue.
  Close the game from the menu when you are finished. This is a real Thestra
  gap, recorded separately rather than papered over.
- **Floors 3–6 are procedurally laid out from the base game's generation
  profiles.** The authored rooms spawn at random legal positions, so the
  *layouts* are not hand-composed — only the encounters, rooms and beats are.
  Expect some walking. If a floor feels empty, the authored room is elsewhere
  on it; the minimap colours it distinctly.
- **The Weighing Room, the Rusted Choir and the Half-Contract are one-shot.**
  If you walk past them you will not be offered them again on that floor.
  Nothing gated behind them blocks the ending.
- **Balance is unverified by play.** The Eternal Warden is authored to run long
  enough to reach Battle Strain. It has not been fought by a human. If it is
  absurd in either direction, that is the single most useful thing you can tell
  me.
- **No new art.** Every plate, portrait and tileset is existing Second Gate art
  reused. Nothing here was generated.
- Untested seams are listed in [`VALIDATION.md`](VALIDATION.md).

---

## What this is

A complete authored trajectory from New Game to an ending, built entirely out
of Second Gate's existing systems: no new engine commands, no bespoke campaign
logic in Lua, no new menu systems. Everything below is event data.

It inherits the canonical opening, St. Maria, the Bellroot Depths and the Vigil,
and then continues past the point where the base game stops.

**Premise, one sentence:** St. Maria rings two bells at its Vigil and something
underneath rings a third, and finding out what has been answering for eleven
years turns out to be a question about whose name is on which contract.

## Major sections

| Act | Where | Beat |
|---|---|---|
| Prologue | Carriage → Room 3 | Arrival, Saban, the Crossing Writ |
| I | Floors 1–2, two returns | The Ines mark, the first contract, the salt table; the town learns your face |
| Midpoint | St. Maria, the Chapel | **The Vigil.** Two bells are rung. A third answers. Agnes hands you the rest of the game |
| II | Floor 3 | **The Rusted Choir** — five bells, a greed ladder, and a fee taken out of your walk home |
| II | Floor 3 | The Red Dragon holds the descent |
| II | Floor 4 | **The Weighing Room** — the Vault will price your money, your creature, or your name |
| II | Floor 5 | **The Half-Contract** — where the blue chalk line ends |
| Return | St. Maria, Room 3 | The one mandatory return beat. Something has been added to your room |
| III | Floor 6 | The Garden Without Wind, the Eternal Warden, and the bell with nothing inside it |
| Ending | — | Three endings off one choice, then an epilogue St. Maria that reacts to your whole run |

## What is invented here versus what is canon

Honoured as settled: the summoner fiction, Saban, St. Maria and its cast,
MP as the expedition horizon, MPD as the price of a strong creature, Battle
Strain, the Vigil, the Ines thread, the existing floors and creature economy.

Invented for this campaign only — **do not read any of it as canon**:

- the Third Bell itself, and the reading that the Labyrinth keeps a ledger of
  summoner names that can be paid with;
- the Eternal Warden and its troop (`boss_eternal_warden`);
- the Rusted Choir, the Weighing Room, the Half-Contract room;
- three key items (Bellroot Leaf, Half-Contract, Warden's Clapper);
- Sister Agnes commissioning the player;
- every ending, and the epilogue register for Alicia, Laura and the gate guard;
- compressing the pre-Vigil ramp from three incursions to two;
- stocking Town Portal and Bell Salt in Alicia's shop.

## Where the authoring lives

- `data/` — the campaign. This is the deliverable.
- `authoring/apply-campaign.py` — provenance. Every authored edit as a
  re-runnable, readable diff of intent rather than a wall of JSON.
- `authoring/check-spine.js` — the campaign reachability audit
  (`node authoring/check-spine.js`).
- `VALIDATION.md` — what was verified, how, and what was not.
- `OWNER-JOURNAL.md` — **please fill this in after you finish.**
