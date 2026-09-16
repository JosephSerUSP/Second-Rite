# PLAY_GAUNTLET

Run from the repository root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\PLAY_GAUNTLET.ps1 -Mode lab
```

The lab mode runs A002, A003, and C003 twice from disposable copies: once with
the authored `goldenScript`, then with the same timing and gameplay input
neutralized. A002's historical wait-only loss is reported as
`NOT-PLAYED-CONTROL-EQUIVALENT`; A003 and C003 retain their mandated `PLAYED`
status. Evidence is written to `artifacts/gauntlet/play-gauntlet-lab.json`.

The existing #704 unidentified-gear candidates are launched with
`-Mode candidate -Candidate A|B|C`, and checked with `-Mode validate`. Owner
ratings use `-Mode rate`. Two independent `openrouter/free` critiques can be
collected with `-Mode critics`; they remain in a hidden pending artifact until
the owner rating is saved.

Owner-play causal checklist for each candidate: acquire an unidentified relic
from the authored chest/event, leave it unidentified, inspect its preview in
the equipment screen, deliberately equip it, observe the concealed property or
CURSE in play, then use the candidate's authored appraisal, Divination, or
purification route and finish the authored slice. Record the result in the
owner rating; the launcher does not silently substitute a static validation for
that play.
