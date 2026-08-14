# Project Generator

Prompt → full playable Thestra Project, with the real engine validator used as the repair oracle.

## Agent/reviewable Project quick start

For Luna, Jules, or any task that should create a separate game **inside the repository without editing Second Gate**, prefer an explicit Project target:

```text
set OPENROUTER_API_KEY=sk-or-...
npm run generate-project -- --project projects/labs/mist-isle "A melancholy island where drowned bells still ring at low tide."
```

Then open that Project normally:

```text
npm start -- --project projects/labs/mist-isle
```

The target must not already exist. Its parent folders may be created automatically. The generator writes only into the generated Project root after bootstrap; root Second Gate `data/` and `assets/` remain the source Project, not scratch space.

`tools/campaign-gen/generate-project.js` is only the destination/lifecycle wrapper. The proven generation stages remain in `gen.js`.

## Disposable fixture quick start

The original fixture mode remains useful for disposable experiments:

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

## Important bootstrap truth

On current main, generator bootstrap is an explicit **Project fork**: it copies the source Project's `data/` and `assets/` through the shared Project lifecycle service, then overwrites/generated content stage by stage.

That gives strong write isolation, but it does **not** mean the generated game begins from a neutral blank Thestra baseline. Issue #390 owns extracting reusable engine/Scene/Flow authored defaults from Second Gate. When that neutral baseline lands, the lifecycle provider can switch generator bootstrap to sparse creation without changing the `--project` command or Studio Project API.

Do not describe the current compatibility fork as a blank/new Project.

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

## How it works

1. A separate Project root is materialized through the shared Project lifecycle service. Current compatibility mode is an explicit fork of source Project `data/` + `assets/`; #390 will provide the neutral sparse baseline.
2. Stages run in order — `outline → units → items → quests → maps → events` — each one an LLM call whose prompt embeds machine-readable contracts (command registry, ruleset ids, id manifest of everything generated so far, schema-by-example). The outline stage writes `WALKTHROUGH.md` first; later stages derive from it.
3. After the last stage, the validate-repair loop runs the real engine validator against the installed runtime staged with the generated Project and feeds failures verbatim to the repair model until `VALIDATE OK` (bounded rounds).

## Flags

The underlying `gen.js` supports:

- `--dry-run` — print assembled prompts, no API calls
- `--stage <s>` — run exactly one stage
- `--resume` — skip stages recorded as done in `fixture-state.json`
- `--clean` — remove exactly the named **disposable fixture** Project
- `--provider <id>` — `openrouter`, `deepseek`, or `gemini`
- `--model <id>` — override the model for all stages

The explicit-target wrapper adds:

- `--project <target>` — required explicit Project destination; folder basename becomes generator name

For safety, the explicit-target wrapper rejects `--clean`; reviewable/custom Project roots are never auto-deleted by generator cleanup.

## Configuration

`config.json` defines LLM providers, per-stage model/temperature, and validator settings. Prompt templates live in `prompts/*.md`; `{{TOKENS}}` are filled by `lib/context.js`.

## Editor integration

The existing generator window still targets disposable `tmp/generated-projects/<name>/` fixtures and can Test Play them without changing Studio's open Project.

Project selection itself is now a separate first-class Studio capability: Electron-hosted Studio can inspect/open/fork Projects from the File menu, while CLI/agents use the same filesystem lifecycle contract. A future generator UI can choose an explicit destination without inventing another root-selection protocol.

See `tools/editor/PROJECTS.md` and issues #390, #392, #479.
