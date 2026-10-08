# THE THIRD BELL — owner campaign journal

Fill this in **after** you reach an ending. Ratings are 1–5, where 3 is
"fine, I have played worse". Short answers can be one line; the one-liners are
worth more to me than the numbers.

There are critic reports for this campaign in this directory. **Do not open
them until this journal is filled in** — they will bias the ratings, which is
the only thing here that cannot be reconstructed later.

---

## Ratings (1–5)

| | Score |
|---|---|
| Opening hook | |
| Town interest | |
| Dungeon curiosity | |
| Encounter variety | |
| Expedition tension | |
| Pacing | |
| Memorable weirdness | |
| Desire to keep playing | |
| Ending satisfaction | |

## Short answers

**Favourite room or floor**

**Favourite NPC beat**

**Favourite creature or encounter**

**Weakest section**

**The moment I most wanted to return to town**

**The moment I felt most rewarded for exploring**

**An idea I would steal for canon**

**A thing I never want in canon**

---

## WOULD I PLAY A LONGER VERSION OF THIS CAMPAIGN?

> yes / maybe / no

**Why:**

---

## Free notes

Anything else. Bugs, softlocks, text that landed wrong, a fight that was
absurd, a room you walked past and never found. Note where you were.

- **Floor 1 Player Experience (2026-08-18 Playtest)**:
  - Opening / 1F looks identical to base Second Gate with no perceivable changes at start.
  - Floor 1 map layout is broken/awkward: recruit NPC events do not function (`recruits` array was empty in `maps/2.json`, resulting in silent failure on interact).
  - Fixed-coordinate event spawns (e.g. `spawn: "Fixed"` at `(10,10)`) frequently land inside solid stone walls/fixtures due to procedural generation.
  - Staircase discovery issue: down-staircase is a wallEvent with bump trigger only (pressing interact/Z does nothing), leading to feeling stuck and unable to reach 2F.

