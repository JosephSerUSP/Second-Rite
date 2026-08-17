#!/usr/bin/env node
// Goal -> ordinary sparse Thestra Project.
//
// The historical folder name `campaign-gen` is retained for compatibility;
// Campaign is not a runtime or Project ontology here. Generation owns exactly
// one Project root and never reads Second Gate game data as grammar/context.
'use strict';

const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');
const { chatForProvider, extractJson } = require('./lib/llm');
const ctxlib = require('./lib/context');
const fixtures = require('./fixture-project');
const projectPlay = require('../editor/project-play');

const HERE = __dirname;
const CONFIG = JSON.parse(fs.readFileSync(path.join(HERE, 'config.json'), 'utf8'));
const REQUIRED_STAGES = new Set(['plan', 'ruleset', 'outline', 'startup']);
const OPTIONAL_STAGES = ['units', 'items', 'quests', 'maps', 'events'];
const STAGE_ORDER = ['plan', 'ruleset', 'outline', ...OPTIONAL_STAGES, 'startup'];
const PLAN_FILE = 'game-plan.json';

// ---------------------------------------------------------------------------
// CLI
// ---------------------------------------------------------------------------
const args = process.argv.slice(2);
const opts = {
    prompt: [], name: null, stage: null, resume: false, dryRun: false,
    model: null, provider: null, clean: false, responses: null,
};
for (let i = 0; i < args.length; i++) {
    if (args[i] === '--name') opts.name = args[++i];
    else if (args[i] === '--stage') opts.stage = args[++i];
    else if (args[i] === '--resume') opts.resume = true;
    else if (args[i] === '--dry-run') opts.dryRun = true;
    else if (args[i] === '--model') opts.model = args[++i];
    else if (args[i] === '--provider') opts.provider = args[++i];
    else if (args[i] === '--responses') opts.responses = path.resolve(args[++i]);
    else if (args[i] === '--clean') opts.clean = true;
    else opts.prompt.push(args[i]);
}
opts.prompt = opts.prompt.join(' ');

if (!opts.name || !/^[a-z0-9_]+$/.test(opts.name)) {
    console.error('Usage: node gen.js --name <snake_case_name> [--stage s] [--resume] [--dry-run] [--clean] [--provider <id>] [--model <id>] [--responses <dir>] "<goal prompt>"');
    process.exit(2);
}
if (opts.stage && !STAGE_ORDER.includes(opts.stage) && opts.stage !== 'repair') {
    console.error(`Unknown stage '${opts.stage}'. Available: ${STAGE_ORDER.join(', ')}`);
    process.exit(2);
}

const DIR = fixtures.fixtureProjectPath(ctxlib.REPO, opts.name);
const STATE_PATH = fixtures.fixtureStatePath(ctxlib.REPO, opts.name);
const PLAN_PATH = path.join(DIR, PLAN_FILE);

// ---------------------------------------------------------------------------
// Provider resolution (unchanged/provider-neutral).
// ---------------------------------------------------------------------------
function resolveProvider() {
    const id = opts.provider
        || process.env.CAMPAIGN_GEN_PROVIDER
        || Object.keys(CONFIG.providers).find(k => CONFIG.providers[k].default)
        || 'openrouter';
    const p = CONFIG.providers[id];
    if (!p) throw new Error(`Unknown provider '${id}'. Available: ${Object.keys(CONFIG.providers).join(', ')}`);
    return { id, ...p };
}

let envModels = {};
try { envModels = JSON.parse(process.env.CAMPAIGN_GEN_MODELS || '{}'); } catch { /* ignore */ }
function rawModelFor(stage) {
    const sc = CONFIG.stages[stage] || CONFIG.stages.repair;
    return envModels[stage] || opts.model || sc.model;
}
function normalizeModel(model, provider) {
    if (!provider) return model;
    if (provider.type === 'gemini') return model.replace(/^(google\/|gemini\/)/, '');
    if (provider.type === 'openai-compatible' && provider.id !== 'openrouter') {
        return model.replace(/^[a-zA-Z0-9_-]+\//, '');
    }
    return model;
}
function modelFor(stage) {
    const provider = resolveProvider();
    return normalizeModel(rawModelFor(stage), provider);
}

// ---------------------------------------------------------------------------
// Project bootstrap/state.
// ---------------------------------------------------------------------------
function bootstrap() {
    if (!fs.existsSync(DIR)) fixtures.bootstrapFixtureProject({ installRoot: ctxlib.REPO, name: opts.name });
}
function loadState() {
    if (fs.existsSync(STATE_PATH)) return JSON.parse(fs.readFileSync(STATE_PATH, 'utf8'));
    return { prompt: opts.prompt, done: [], repairFailures: [] };
}
function saveState(state) {
    fs.writeFileSync(STATE_PATH, JSON.stringify(state, null, 2) + '\n');
}
function loadPlan() {
    if (!fs.existsSync(PLAN_PATH)) return null;
    return JSON.parse(fs.readFileSync(PLAN_PATH, 'utf8'));
}
function stageEnabled(stage, plan) {
    if (opts.stage) return stage === opts.stage;
    if (REQUIRED_STAGES.has(stage)) return true;
    if (!plan) return true; // before plan exists, dry-run/show all contracts.
    const stages = Array.isArray(plan.stages) ? plan.stages : [];
    return stages.includes(stage);
}

// ---------------------------------------------------------------------------
// Prompt assembly. All game-specific context comes from DIR.
// ---------------------------------------------------------------------------
function textIfExists(file, fallback) {
    const target = path.join(DIR, file);
    return fs.existsSync(target) ? fs.readFileSync(target, 'utf8') : fallback;
}
function assemblePrompt(stage, state) {
    const template = fs.readFileSync(path.join(HERE, 'prompts', stage + '.md'), 'utf8');
    const fills = {
        PITCH: state.prompt,
        GOAL: state.prompt,
        PROJECT_NAME: path.basename(DIR),
        PLAN: textIfExists(PLAN_FILE, '(game plan not generated yet)'),
        OUTLINE: textIfExists('outline.json', '(outline not generated yet)'),
        RULESET: JSON.stringify(ctxlib.ruleset(DIR), null, 1),
        COMMANDS: JSON.stringify(ctxlib.commandRegistry(DIR), null, 1),
        MANIFEST: JSON.stringify(ctxlib.manifest(DIR), null, 1),
        SCHEMAS: JSON.stringify(ctxlib.schemas(), null, 1),
    };
    return template.replace(/\{\{(\w+)\}\}/g, (_, k) => fills[k] !== undefined ? fills[k] : `{{${k}}}`);
}

const totals = { prompt: 0, completion: 0, cost: 0 };
let repairResponseIndex = 0;
function recordedResponsePath(stage) {
    if (!opts.responses) return null;
    const suffix = stage === 'repair' ? `repair-${++repairResponseIndex}` : stage;
    const candidates = [`${suffix}.json`, `${suffix}.txt`];
    for (const name of candidates) {
        const candidate = path.join(opts.responses, name);
        if (fs.existsSync(candidate)) return candidate;
    }
    throw new Error(`Recorded response missing for stage '${stage}' in ${opts.responses}`);
}

async function callStage(stage, userPrompt, extraMessages = []) {
    const recorded = recordedResponsePath(stage);
    if (recorded) {
        console.log(`  [recorded / ${stage}] ${path.relative(ctxlib.REPO, recorded)}`);
        return fs.readFileSync(recorded, 'utf8');
    }

    const provider = resolveProvider();
    const sc = CONFIG.stages[stage] || CONFIG.stages.repair;
    const apiKey = process.env[provider.apiKeyEnv];
    if (!apiKey) throw new Error(`Missing API key for provider '${provider.id}': set ${provider.apiKeyEnv} in your environment.`);
    const started = Date.now();
    const model = modelFor(stage);
    const { content, usage } = await chatForProvider({
        providerType: provider.type,
        baseUrl: provider.baseUrl,
        apiKey,
        model,
        temperature: sc.temperature,
        onChunk: d => process.stdout.write(d),
        messages: [
            { role: 'system', content: 'You author one independent Thestra Project. Use only the supplied neutral engine contracts and this Project\'s own generated data. Reply with exactly the requested artifact, with no commentary outside it.' },
            { role: 'user', content: userPrompt },
            ...extraMessages,
        ],
    });
    process.stdout.write('\n');
    const secs = ((Date.now() - started) / 1000).toFixed(1);
    const providerLabel = provider.label || provider.id;
    if (usage) {
        totals.prompt += usage.prompt_tokens || 0;
        totals.completion += usage.completion_tokens || 0;
        if (typeof usage.cost === 'number') totals.cost += usage.cost;
        const cost = typeof usage.cost === 'number' ? ` | $${usage.cost.toFixed(5)}` : '';
        console.log(`  [${providerLabel} / ${stage}] ${usage.prompt_tokens} in / ${usage.completion_tokens} out tokens${cost} | ${secs}s`
            + ` || run total: ${totals.prompt} in / ${totals.completion} out`
            + (totals.cost ? ` | $${totals.cost.toFixed(5)}` : ''));
    } else {
        console.log(`  [${providerLabel} / ${stage}] done in ${secs}s (provider returned no usage data)`);
    }
    return content;
}

// ---------------------------------------------------------------------------
// Stage output handling.
// ---------------------------------------------------------------------------
function writeStageOutput(stage, reply) {
    const out = extractJson(reply);
    if (stage === 'plan') {
        if (!out.plan || typeof out.plan !== 'object' || Array.isArray(out.plan)) {
            throw new Error('plan stage must emit {"plan": {...}}');
        }
        const allowed = new Set(OPTIONAL_STAGES);
        out.plan.stages = [...new Set((out.plan.stages || []).filter(s => allowed.has(s)))];
        fs.writeFileSync(PLAN_PATH, JSON.stringify(out.plan, null, 2) + '\n');
        return [PLAN_FILE];
    }
    if (stage === 'outline') {
        if (!out.outline || typeof out.walkthrough !== 'string') {
            throw new Error('outline stage must emit {outline, walkthrough}');
        }
        fs.writeFileSync(path.join(DIR, 'outline.json'), JSON.stringify(out.outline, null, 2) + '\n');
        fs.writeFileSync(path.join(DIR, 'WALKTHROUGH.md'), out.walkthrough);
        return ['outline.json', 'WALKTHROUGH.md'];
    }

    const written = [];
    for (const [file, content] of Object.entries(out)) {
        if (!ctxlib.GENERATED_FILES.includes(file)) {
            console.warn(`  (ignoring unexpected Project file key '${file}')`);
            continue;
        }
        ctxlib.writeGeneratedResource(DIR, file, content);
        written.push(file);
    }
    if (written.length === 0) throw new Error(`stage '${stage}' emitted no allowed Project resource`);
    return written;
}

// ---------------------------------------------------------------------------
// Validator + bounded Project-only repair.
// ---------------------------------------------------------------------------
function runValidator() {
    let stageDir = null;
    try {
        const lovecBin = ctxlib.resolveLovecPath(CONFIG.validate && CONFIG.validate.lovecPath);
        stageDir = projectPlay.stageProject({ installRoot: ctxlib.REPO, projectRoot: DIR });
        const out = execFileSync(lovecBin, ['.', 'validate'], {
            cwd: stageDir,
            encoding: 'utf8',
            timeout: 120000,
        });
        return { ok: true, output: out, timedOut: false };
    } catch (err) {
        return {
            ok: false,
            output: String(err.stdout || '') + String(err.stderr || '') + (err.message ? `\n${err.message}` : ''),
            timedOut: err.code === 'ETIMEDOUT' || err.signal === 'SIGTERM' || /timed out/i.test(err.message || ''),
        };
    } finally {
        if (stageDir) projectPlay.removeStage(stageDir);
    }
}

function classifyFailure(res) {
    const text = String(res.output || '').toLowerCase();
    if (res.timedOut) return 'hang';
    if (/json|schema|must be (an?|the)|invalid authored|parse|decode/.test(text)) return 'malformed JSON/schema';
    if (/resolves to no|unresolved|references? (?:missing|unknown)|missing (?:resource|map|scene|skill|unit|item|element|role)|unknown .* id/.test(text)) {
        return 'unresolved resource reference';
    }
    if (/startup|boot|title scene|new game|load_map|initial scene|scene.*not found/.test(text)) return 'startup failure';
    return 'runtime crash';
}

function validatorProblems(output) {
    const text = String(output || '');
    const failAt = text.indexOf('VALIDATE FAIL');
    if (failAt !== -1) {
        return text.slice(failAt).split('\n')
            .filter(l => l.trim() !== '' && !/^\[validator\] warning/.test(l))
            .join('\n');
    }
    return text.split('\n')
        .filter(l => !/^\[formula\] error in 'os\.time/.test(l))
        .filter(l => /FAIL|error|missing|resolves to no|references|attempt to|invalid|unknown|timeout/i.test(l))
        .join('\n') || text.trim();
}

async function validateRepairLoop(state) {
    for (let round = 1; round <= CONFIG.validate.maxRepairRounds; round++) {
        const res = runValidator();
        if (res.ok && /VALIDATE OK/.test(res.output)) {
            console.log('VALIDATE OK');
            return true;
        }
        const category = classifyFailure(res);
        const problems = validatorProblems(res.output);
        state.repairFailures = state.repairFailures || [];
        state.repairFailures.push({ round, category, problems });
        saveState(state);
        console.log(`validate round ${round} failed [${category}]:\n${problems}\n-> asking repair model...`);

        const files = {};
        for (const f of ctxlib.GENERATED_FILES) files[f] = ctxlib.readGeneratedResource(DIR, f);
        const repairPrompt = fs.readFileSync(path.join(HERE, 'prompts', 'repair.md'), 'utf8')
            .replace('{{CATEGORY}}', category)
            .replace('{{PROBLEMS}}', problems)
            .replace('{{FILES}}', JSON.stringify(files, null, 1))
            .replace('{{COMMANDS}}', JSON.stringify(ctxlib.commandRegistry(DIR), null, 1))
            .replace('{{SCHEMAS}}', JSON.stringify(ctxlib.schemas(), null, 1));
        const reply = await callStage('repair', repairPrompt);
        const out = extractJson(reply);
        let repaired = 0;
        for (const [file, content] of Object.entries(out)) {
            if (!ctxlib.GENERATED_FILES.includes(file)) continue;
            ctxlib.writeGeneratedResource(DIR, file, content);
            console.log(`  repaired ${file}`);
            repaired += 1;
        }
        if (repaired === 0) throw new Error('repair model emitted no allowed generated-Project resource');
    }
    state.repairFailures = state.repairFailures || [];
    state.repairFailures.push({ round: CONFIG.validate.maxRepairRounds + 1, category: 'exhausted repair', problems: 'repair round budget exhausted' });
    saveState(state);
    console.error('Repair rounds exhausted; generated Project still fails validation.');
    return false;
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------
(async () => {
    if (opts.clean) {
        fixtures.cleanFixtureProject({ installRoot: ctxlib.REPO, name: opts.name });
        console.log(`Removed fixture Project: tmp/generated-projects/${opts.name}/`);
        return;
    }
    bootstrap();
    const state = loadState();
    if (!state.prompt && opts.prompt) state.prompt = opts.prompt;
    if (!state.prompt) throw new Error('goal prompt is required for a new generator run');

    let plan = loadPlan();
    const candidateStages = opts.stage ? [opts.stage] : STAGE_ORDER;
    for (const stage of candidateStages) {
        if (stage === 'repair') continue;
        if (opts.resume && state.done.includes(stage)) continue;
        if (!stageEnabled(stage, plan)) {
            console.log(`--- skip stage: ${stage} (not required by game plan) ---`);
            continue;
        }
        const prompt = assemblePrompt(stage, state);
        if (opts.dryRun) {
            console.log(`===== DRY RUN: stage '${stage}' prompt =====\n${prompt}`);
            continue;
        }
        const providerLabel = opts.responses ? 'recorded' : (resolveProvider().label || resolveProvider().id);
        const modelLabel = opts.responses ? 'offline response' : modelFor(stage);
        console.log(`--- [${providerLabel}] stage: ${stage} (${modelLabel}) ---`);
        const reply = await callStage(stage, prompt);
        const written = writeStageOutput(stage, reply);
        console.log(`  wrote: ${written.join(', ')}`);
        if (!state.done.includes(stage)) state.done.push(stage);
        saveState(state);
        if (stage === 'plan') plan = loadPlan();
    }

    if (!opts.dryRun) {
        const ok = await validateRepairLoop(state);
        saveState(state);
        console.log(ok
            ? `\nGenerated Project ready: ${DIR}  (open normally with npm start -- --project <path>)`
            : `\nGenerated Project INVALID: ${DIR} -- inspect fixture-state.json repairFailures.`);
        process.exit(ok ? 0 : 1);
    }
})().catch(err => { console.error(err); process.exit(1); });
