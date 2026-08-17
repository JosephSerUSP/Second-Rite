# Ash Choir — validation record

Run date: 2026-08-17

This is a Project-local record for the experimental campaign. It does not
replace the repository's owner-bound G4/G5/G6 records and it does not authorize
recapturing canonical references.

## Passed

- `node experiments/campaigns/ash-choir/authoring/apply-campaign.py`
- `node experiments/campaigns/ash-choir/authoring/check-spine.js`
  - `CAMPAIGN SPINE OK — New Game, two expeditions, return beat, climax, and two endings`
- `node tools/export/export-game.js --project experiments/campaigns/ash-choir --output tmp/ash-choir-export --stage-only`
- In the exact staged Project:
  - `lovec . validate` — `VALIDATE OK`
  - `lovec . savetest` — `SAVETEST OK`
  - `lovec . validate golden` — exit 0; all three golden battle replays completed
  - `lovec . screenshots` — exit 0; 144 screenshot captures completed
  - `lovec . preview-map 2`, `preview-map 3`, and `preview-map 4` — each emitted a complete `PREVIEW BEGIN/END` payload
- On the repository installation:
  - `lovec . unittest` — `ALL UNIT TESTS OK`

The validator reports the existing repository-wide `dungeon_entered` “set but
not read” warning, the expected sandbox-negative `os.time()` formula error,
and 86 total `SCRIPT` usages. None is a new campaign-specific validation
failure.

## Not claimed

- The canonical G5/G6 reference trees were not regenerated or modified.
  Candidate screenshots were rendered successfully, but this Project has
  intentionally different authored data and therefore is not being presented
  as byte-identical to the canonical game.
- `lovec . golden-ui` and `lovec . reachability` were attempted against the
  staged Project but did not complete in this desktop harness. They are left
  uncertified rather than treated as passes; no golden output was regenerated.
- A 10-second fail-closed boot smoke produced no runtime error before the
  process was manually terminated. It was a smoke observation, not a full
  playthrough or an automated campaign-completion proof.
- The exported Project does not carry the repository's `tests/` tree, so the
  unit gate is run from the repository installation above rather than claimed
  as a staged-Project unit run.

## Owner playtest still required

The static spine audit verifies the authored route and the live engine gates
verify schema, save/load, replay, and rendering surfaces. A human should still
play from New Game through both endings and complete
[`OWNER-JOURNAL.md`](OWNER-JOURNAL.md), especially to judge the machine-authored
battle balance, procedural room legibility, and whether the return-to-town beat
lands emotionally.
