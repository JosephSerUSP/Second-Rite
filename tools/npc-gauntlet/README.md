# NPC Gauntlet Lab

The NPC Gauntlet Lab is an upstream authoring-research tool. It runs bounded
NPC roleplay experiments against a frozen Project research dossier and keeps
generated material outside canonical `data/`. It supports directed scene
repetitions, directed town schedules, and a separate living-town simulation.

Living-town mode begins from locations, time blocks, energy, obligations,
deadlines, and ambient pressures. Every NPC independently chooses whether to
move, work, seek, help, avoid, rest, linger, or talk. Code resolves those plans
against one material world state; a brief embodied exchange is requested only
when compatible plans place NPCs together. There are no required encounters or
minimum dialogue turns. Multi-day definitions may schedule obligations with
`startsAt`, mark explicit day boundaries for overnight energy recovery and
daily consolidation, and attach deterministic seed-selected chance pressures.
Cash rewards, purchases, and payments between NPCs are resolved by code rather
than invented during dialogue. Definitions live under
`docs/research/npc-gauntlets/towns/` and remain noncanonical research inputs.

## Start

```text
npm run npc-gauntlet -- --project projects/hichaukitoden-game
```

The server binds to `127.0.0.1` by default. `node tools/npc-gauntlet/cli.js
sources --project <root>` prints live dialogue candidates without writing.

## Model allowlist

The lab accepts only OpenAI `gpt-5.6-luna` or an explicitly verified
zero-priced OpenRouter `:free` variant. Direct Gemini, DeepSeek, Anthropic, and
other providers are intentionally unavailable here. The OpenRouter catalogue
is refreshed during preflight; a model must advertise structured output and
zero prompt/completion/request pricing. `openrouter/free` is accepted only for
explicit exploratory runs because it chooses the model dynamically. The
checked-in [config.json](./config.json) is the policy/defaults source used by
the server and gateway.

Set `OPENAI_API_KEY` for Luna or `OPENROUTER_API_KEY` for free OpenRouter
models. Keys are read from the environment and are never written to research
files or run artifacts.

## Research boundary

Versionable dossiers and accepted scenarios live under
`<Project>/docs/research/npc-gauntlets/`. Proposals and bulk run output live in
ignored `out/npc-gauntlets/`. Use the Preserve action after human review to
copy selected specimens and findings into the Project research area. Nothing
updates Project `data/`, engine code, or runtime dialogue automatically.

## Architecture references

The separation between actor prompts, a single state-owning director, and a
bounded episode loop is informed by [Concordia](https://github.com/google-deepmind/concordia)
and [SOTOPIA environments](https://docs.sotopia.world/concepts/environments).
Memory retrieval follows the observation/recency/salience pattern described by
Stanford's [Generative Agents](https://arxiv.org/abs/2304.03442); the lab keeps
retrieval deterministic and local in v1. The model gateway follows
[OpenRouter free variants](https://openrouter.ai/docs/guides/routing/model-variants/free)
and the structured-output capability advertised for
[GPT-5.6 Luna](https://developers.openai.com/api/docs/models/gpt-5.6-luna).

## Workflow and contracts

1. Discover live `docs/` and `data/` sources, compile a dossier, and edit facts
   versus hypotheses in the Dossiers tab.
2. Generate scenario proposals into the ignored editorial queue; only an
   accepted `ScenarioCard` is written under `docs/research/npc-gauntlets/`.
3. Submit an experiment JSON for preflight. The response contains model-policy
   decisions, refreshed catalogue evidence, source hashes, estimated calls,
   warnings, and a short-lived approval token.
4. Start or resume a run. Directed episodes write structured actor events and
   director resolutions. Living-town runs write independent plans, deterministic
   material consequences, and only the encounters those plans caused. `partial`
   runs resume completed specimen files without replaying them.
5. Rate blind specimens, optionally run a critic, reveal identities, and use
   Preserve to export a compact research bundle.

All persisted objects carry `contractVersion: 1`: `NpcDossier`, `ScenarioCard`,
`TownSchedule`, `LivingTown`, `RunManifest`, `PreservedExperiment`, and
`ModelPolicyDecision`. The HTTP surface is local-only (`/api`), and no route
writes Project `data/`.
