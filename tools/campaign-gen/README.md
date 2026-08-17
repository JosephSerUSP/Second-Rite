# Project Generator

Goal prompt to a complete, independent Thestra Project. The historical folder
name is retained for compatibility: **Campaign is not a Project type or runtime
root**.

```text
goal -> capability plan -> Project-owned ruleset -> outline/walkthrough
     -> only the content stages the plan needs -> startup -> validate/repair
     -> fail-closed boot proof
```

## Generate into a Project root

```text
npm run generate-project -- --project projects/labs/my-game \
  "make a tiny dungeon RPG about three botanists exploring a greenhouse"
```

The target must not exist. It is created through the ordinary sparse New
Project lifecycle, pins RTP `1.0`, and is then the only Project root generation
may write. RTP contributes semantic engine language, command/formula contracts,
and declared default Scene/Flow compositions; it does not supply Second Gate
roles, elements, skills, states, passives, units, lore, balance, item grammar,
or assets.

The first stages decide which capabilities and game grammar are actually needed.
For example, a Scene/Event adventure may deliberately leave every combat
database empty. Later stages receive only Project-local generated manifests,
neutral structural schemas, and the resolved RTP command registry.

## Validation and repair

The generator stages the Project through the same player/export boundary Studio
uses, then runs the real `lovec . validate` oracle. Failures are recorded in
`fixture-state.json` as malformed JSON/schema, unresolved resource reference,
invalid startup, unplayable boot, runtime crash, hang, or exhausted repair.
Repair can write only explicitly allowed generated resources inside the target
Project and ends after the configured bounded number of rounds. It never copies
a missing id from root Second Gate.

After structural validation, a four-second `THESTRA_CI_FAIL_ON_ERROR=1` boot
proof runs the normal staged player entrypoint. This is fail-closed liveness and
startup evidence, not a substitute for the player-equivalent input/playthrough
work tracked by #366.

## Offline proof fixtures

Recorded fixtures under `proof/` exercise the pipeline without a model key:

```text
node tools/campaign-gen/generate-project.js --project <empty-target> \
  --responses tools/campaign-gen/proof/botanists "..."
```

They are reviewable response transcripts, not runtime templates. Their sole
purpose is to prove sparse ownership, grammar divergence, validation, and boot
through the real staged player boundary.

## Options

- `--project <target>` required explicit Project destination
- `--responses <directory>` recorded JSON responses for offline proof runs
- `--stage <stage>`, `--resume`, `--dry-run`
- `--provider <id>`, `--model <id>`

The explicit-target wrapper rejects `--clean`: reviewable Project roots are
never removed automatically.
