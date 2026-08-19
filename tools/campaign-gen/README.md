# Project Generator

Prompt → full playable Thestra Project, with the real engine validator used as the repair oracle.

## Agent/reviewable Project quick start

For Luna, Jules, or any task that should create a separate game **inside the repository without editing Second Gate**, choose the lifecycle that matches the task.

A neutral blank Project is now first-class:

```text
npm run project -- create projects/labs/my-game
npm start -- --project projects/labs/my-game
```

The sparse Project is pinned to RTP `1.0` and contains only neutral Project-owned startup/data structure. Reusable engine registry + declared Scene/Flow defaults are inherited from RTP rather than copied from Second Gate.

For the existing prompt generator, use an explicit destination:

```text
set OPENROUTER_API_KEY=sk-or-...
npm run generate-project -- --project projects/labs/mist-isle "A melancholy island where drowned bells still ring at low tide."
```

Then open that Project normally:

```text
npm start -- --project projects/labs/mist-isle
```

The target must not already exist. Its parent folders may be created automatically. The generator writes only into the generated Project root after bootstrap; root Second Gate `data/` and `assets/` remain source, never scratch space.

`tools/campaign-gen/generate-project.js` is only the destination/lifecycle wrapper. The proven generation stages remain in `gen.js`.

## Important generator bootstrap truth

**New Project is neutral now; the current Project Generator is not yet neutral.**

The existing generator's `ruleset()` and schema examples still consume Second Gate's roles/elements/states/passives/skills. Its content stages generate units/items/maps/events *under that fixed game ruleset* rather than generating a complete RPG ruleset of their own.

Therefore generator bootstrap deliberately remains an explicit **compatibility Project fork** for now. Switching it to sparse creation before generalizing its ruleset stage would produce Projects whose generated content references Second Gate vocabulary that does not exist locally.

The next generator architecture slice should make a goal prompt author or explicitly select the Project's own core RPG ruleset (elements, roles, skills, states, passives, relevant system policy), then run the existing content stages against only:

- inherited Thestra semantic command/formula vocabulary;
- the generated Project's own rules/data;
- any deliberately selected reusable package/template.

Do not silently copy Second Gate rules into a sparse Project to make the generator pass.

## Disposable fixture quick start

The original compatibility fixture mode remains useful for disposable experiments:

```text
set OPENROUTER_API_KEY=sk-or-...
node tools/campaign-gen/gen.js --name mist_isle "A melancholy island where drowned bells still ring at low tide."
```

That writes `tmp/generated-projects/mist_isle/`.

Open any generated Project with:

```text
npm start -- --project path/to/project
```

or use the generator window's **Test Play** button for its disposable fixture output.

## Supported providers

The generator supports three LLM providers:

| Provider    | Env var               | Type               |
|-------------|-----------------------|--------------------|
| OpenRouter  | `OPENROUTER_API_KEY`   | OpenAI-compatible  |
| DeepSeek    | `DEEPSEEK_API_KEY`     | OpenAI-compatible  |
| Gemini      | `GEMINI_API_KEY`       | Google Gemini API  |

**Default:** OpenRouter. Override with `--provider` or `CAMPAIGN_GEN_PROVIDER` env.

```text
set GEMINI_API_KEY=AIza...
npm run generate-project -- --project projects/labs/mist-isle --provider gemini "A melancholy island..."
```

```text
set DEEPSEEK_API_KEY=sk-...
npm run generate-project -- --project projects/labs/mist-isle --provider deepseek "A melancholy island..."
```

Each provider reads its own env var; only the one matching the active provider needs to be set.

## How the current generator works

1. A separate compatibility Project root is materialized through the shared Project lifecycle's explicit fork operation.
2. Stages run in order — `outline → units → items → quests → maps → events` — each one an LLM call whose prompt embeds machine-readable contracts (resolved command registry, current fixed ruleset ids, id manifest of everything generated so far, schema-by-example). The outline stage writes `WALKTHROUGH.md` first; later stages derive from it.
3. After the last stage, the validate-repair loop runs the real engine validator against the installed runtime staged with the generated Project and feeds failures verbatim to the repair model until `VALIDATE OK` (bounded rounds).

This remains valuable today, but it is **content generation under a supplied game ruleset**, not yet the final "goal prompt → arbitrary new game" architecture.

## Flags

The underlying `gen.js` supports:

- `--dry-run` — print assembled prompts, no API calls
- `--stage <s>` — run exactly one stage
- `--resume` — skip stages recorded as done in `fixture-state.json`
- `--clean` — remove exactly the named **disposable fixture** Project
- `--provider <id>` — `openrouter`, `deepseek`, or `gemini`
- `--model <id>` — override the model for all stages

The explicit-target wrapper adds:

- `--project <target>` — required explicit Project destination; Project slug remains independent of the generator's legacy internal run id

For safety, the explicit-target wrapper rejects `--clean`; reviewable/custom Project roots are never auto-deleted by generator cleanup.

## Configuration

`config.json` defines LLM providers, per-stage model/temperature, and validator settings. Prompt templates live in `prompts/*.md`; `{{TOKENS}}` are filled by `lib/context.js`.

## Editor integration

The existing generator window still targets disposable `tmp/generated-projects/<name>/` compatibility fixtures and can Test Play them without changing Studio's open Project.

Project lifecycle itself is now separate and first-class: Electron-hosted Studio can create/open/fork Projects from the File menu, while CLI/agents use the same filesystem lifecycle contract. A future generalized generator UI should consume sparse Project creation rather than inventing another root-selection protocol.

See `studio/editor/PROJECTS.md` and issues #392, #479, merged #390/#481.
