'use strict';

const fs = require('fs');
const http = require('http');
const path = require('path');
const crypto = require('crypto');
const { URL } = require('url');
const storage = require('./lib/storage');
const sources = require('./lib/sources');
const schemas = require('./lib/schemas');
const policy = require('./lib/model-policy');
const gatewayLib = require('./lib/gateway');
const experiments = require('./lib/experiment');
const proposals = require('./lib/proposals');
const config = require('./config.json');

const HERE = __dirname;
const PUBLIC = path.join(HERE, 'public');

function parseArgs(argv) {
    const out = { project: null, port: config.defaults.port, host: config.defaults.host };
    for (let i = 0; i < argv.length; i++) {
        const arg = argv[i];
        if (arg === '--project') out.project = argv[++i];
        else if (arg.startsWith('--project=')) out.project = arg.slice(10);
        else if (arg === '--port') out.port = Number(argv[++i]);
        else if (arg.startsWith('--port=')) out.port = Number(arg.slice(7));
        else if (arg === '--host') out.host = argv[++i];
        else if (arg === '--help' || arg === '-h') out.help = true;
        else throw new Error(`unknown option '${arg}'`);
    }
    if (out.help) return out;
    if (!out.project) throw new Error('--project is required');
    if (!Number.isInteger(out.port) || out.port < 1 || out.port > 65535) throw new Error('--port must be 1..65535');
    if (!['127.0.0.1', 'localhost'].includes(out.host)) throw new Error('NPC Gauntlet Lab only binds to localhost');
    return out;
}

function json(res, status, body) { res.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' }); res.end(JSON.stringify(body)); }
function text(res, status, body, type = 'text/plain; charset=utf-8') { res.writeHead(status, { 'Content-Type': type }); res.end(body); }
function readBody(req) { return new Promise((resolve, reject) => { let body = ''; req.on('data', chunk => { body += chunk; if (body.length > 5000000) req.destroy(new Error('request body too large')); }); req.on('end', () => { try { resolve(body ? JSON.parse(body) : {}); } catch (error) { reject(new Error(`invalid JSON body: ${error.message}`)); } }); req.on('error', reject); }); }
function fail(res, error) { const status = error.code === 'MODEL_POLICY_DENIED' ? 422 : error.code === 'BUDGET_EXCEEDED' ? 409 : 400; json(res, status, { success: false, code: error.code || 'BAD_REQUEST', message: error.message, ...(error.decision ? { decision: error.decision } : {}) }); }
function slug(value) { return String(value).toLowerCase().replace(/[^a-z0-9_-]+/g, '_').replace(/^_+|_+$/g, '').slice(0, 64) || 'run'; }

function loadResearch(projectRoot) {
    const root = storage.researchRoot(projectRoot), dossierDir = path.join(root, 'dossiers'), scenarioDir = path.join(root, 'scenarios');
    const dossiers = {}, scenarios = [], schedules = [], towns = [];
    for (const file of storage.listJson(dossierDir)) { const item = storage.readJson(path.join(dossierDir, file), null); schemas.validateDossier(item, file); dossiers[item.id] = item; }
    for (const file of storage.listJson(scenarioDir)) { const item = storage.readJson(path.join(scenarioDir, file), null); schemas.validateScenarioCard(item, file); scenarios.push(item); }
    const scheduleDir = path.join(root, 'schedules');
    for (const file of storage.listJson(scheduleDir)) { const item = storage.readJson(path.join(scheduleDir, file), null); schemas.validateTownSchedule(item, file); schedules.push(item); }
    const townDir = path.join(root, 'towns');
    for (const file of storage.listJson(townDir)) { const item = storage.readJson(path.join(townDir, file), null); schemas.validateLivingTown(item, file); towns.push(item); }
    return { root, dossiers, scenarios, schedules, towns };
}
function saveDossier(projectRoot, dossier) { const normalized = schemas.validateDossier(dossier); storage.writeAtomic(path.join(storage.researchRoot(projectRoot), 'dossiers', `${normalized.id}.json`), normalized); return normalized; }
function saveScenario(projectRoot, scenario) { const normalized = schemas.validateScenarioCard(scenario); storage.writeAtomic(path.join(storage.researchRoot(projectRoot), 'scenarios', `${normalized.id}.json`), normalized); return normalized; }
function saveSchedule(projectRoot, schedule) { const normalized = schemas.validateTownSchedule(schedule); storage.writeAtomic(path.join(storage.researchRoot(projectRoot), 'schedules', `${normalized.id}.json`), normalized); return normalized; }

function modelSpecs(experiment) {
    const specs = [];
    const add = (value, fallbackProvider) => {
        const spec = typeof value === 'string' ? { model: value, provider: value === policy.LUNA ? 'openai' : fallbackProvider } : { ...(value || {}) };
        if (!spec.model) throw new Error('model specification requires model');
        spec.provider ||= spec.model === policy.LUNA ? 'openai' : fallbackProvider;
        spec.provider = String(spec.provider).toLowerCase();
        specs.push(spec); return spec;
    };
    (experiment.actorModels || []).forEach(x => add(x, 'openrouter'));
    if (experiment.mode !== 'living-town') add(experiment.directorModel, 'openrouter');
    if (experiment.criticModel) add(experiment.criticModel, 'openrouter');
    if (experiment.scenarioGeneratorModel) add(experiment.scenarioGeneratorModel, 'openrouter');
    return specs;
}
function sourceHashes(projectRoot, research) {
    const values = {};
    // Keep both authored bundle hashes and the live excerpts they cite.  A
    // partial run can therefore be resumed only against exactly the same
    // source material, not merely the same derived dossier JSON.
    for (const item of sources.discoverSources(projectRoot)) values[`source:${item.path}`] = item.sha256;
    for (const dossier of Object.values(research.dossiers)) values[`dossier:${dossier.id}`] = storage.sha256(storage.stableJson(dossier));
    for (const scenario of research.scenarios) values[`scenario:${scenario.id}`] = storage.sha256(storage.stableJson(scenario));
    for (const schedule of research.schedules || []) values[`schedule:${schedule.id}`] = storage.sha256(storage.stableJson(schedule));
    for (const town of research.towns || []) values[`town:${town.id}`] = storage.sha256(storage.stableJson(town));
    return values;
}

function assertNoInlineSecrets(value, pathName = 'experiment') {
    if (!value || typeof value !== 'object') return;
    if (Array.isArray(value)) return value.forEach((item, i) => assertNoInlineSecrets(item, `${pathName}[${i}]`));
    for (const [key, child] of Object.entries(value)) {
        if (/^(api[_-]?key|authorization|secret|password|token)$/i.test(key) || /^(OPENAI|OPENROUTER)_API_KEY$/.test(key)) {
            const error = new Error(`${pathName}.${key} is not accepted; provide credentials through environment variables`);
            error.code = 'INLINE_CREDENTIAL_REJECTED'; throw error;
        }
        assertNoInlineSecrets(child, `${pathName}.${key}`);
    }
}

async function preflight({ projectRoot, experiment }) {
    assertNoInlineSecrets(experiment);
    const research = loadResearch(projectRoot), specs = modelSpecs(experiment), needsRouter = specs.some(x => x.provider === 'openrouter');
    const catalogue = needsRouter ? await policy.fetchCatalogue({ apiKey: process.env.OPENROUTER_API_KEY }) : [];
    const decisions = specs.map(spec => policy.decision({ provider: spec.provider, model: spec.model, catalogue, exploratory: !!experiment.exploratory }));
    for (const decision of decisions) { schemas.validateModelPolicyDecision(decision); if (!decision.allowed) { const error = new Error(decision.reason); error.code = 'MODEL_POLICY_DENIED'; error.decision = decision; throw error; } }
    const selected = experiments.validateExperiment(experiment, research.scenarios, research.dossiers), calls = experiments.expectedCalls(experiment, selected), budget = experiment.budget || {};
    const hasLuna = specs.some(x => x.model === policy.LUNA || x.model === `openai/${policy.LUNA}` || x.provider === 'openai'), hasFree = specs.some(x => x.provider === 'openrouter' && (x.model.endsWith(':free') || x.model === 'openrouter/free'));
    if (specs.some(x => x.provider === 'openai') && !process.env.OPENAI_API_KEY) throw new Error('OPENAI_API_KEY is required for GPT-5.6 Luna runs');
    if (hasLuna && (!Number.isFinite(Number(budget.maxUsd)) || Number(budget.maxUsd) <= 0)) throw new Error('Luna experiments require a positive budget.maxUsd hard cap');
    if (hasFree && (!Number.isFinite(Number(budget.maxCalls)) || Number(budget.maxCalls) < calls)) throw new Error(`free-model experiments require budget.maxCalls >= estimated calls (${calls})`);
    if (hasFree && (!Number.isFinite(Number(budget.maxTokens)) || Number(budget.maxTokens) <= 0)) throw new Error('free-model experiments require a positive budget.maxTokens hard cap');
    const concurrency = Number(experiment.concurrency || 2); if (!Number.isInteger(concurrency) || concurrency < 1 || concurrency > 4) throw new Error('concurrency must be an integer from 1 to 4');
    const promptTokens = Number(experiment.estimatePromptTokens || 1800), completionTokens = Number(experiment.estimateCompletionTokens || 280), callsPerSpec = Math.ceil(calls / specs.length);
    const estimates = specs.map(spec => gatewayLib.estimateCost({ calls: callsPerSpec, promptTokens, completionTokens, provider: spec.provider, model: spec.model, catalogue }));
    const estimate = estimates.every(x => x !== null) ? estimates.reduce((sum, x) => sum + x, 0) : null;
    const hashes = sourceHashes(projectRoot, research), payload = JSON.stringify({ experiment, decisions, hashes });
    const approvalToken = crypto.createHash('sha256').update(payload + Date.now()).digest('hex');
    return { approvalToken, expiresAt: Date.now() + 600000, decisions, catalogueAt: new Date().toISOString(), sourceHashes: hashes, estimatedCalls: calls, estimatedCost: estimate, selectedScenarioIds: selected.map(x => x.id), warnings: hasFree ? ['OpenRouter :free variants can be rate-limited or become unavailable between calls.'] : [] };
}

function createApp({ projectRoot, installRoot = path.resolve(HERE, '..', '..') } = {}) {
    projectRoot = storage.assertProjectRoot(projectRoot); const approvals = new Map(), active = new Map();
    const runDirFor = id => path.join(storage.outputRoot(installRoot, projectRoot), slug(id));
    function findRun(id) {
        const root = storage.outputRoot(installRoot, projectRoot); if (!fs.existsSync(root)) return null;
        for (const dir of fs.readdirSync(root, { withFileTypes: true }).filter(x => x.isDirectory())) { const file = path.join(root, dir.name, 'run.json'); if (!fs.existsSync(file)) continue; const manifest = storage.readJson(file, null); if (manifest && manifest.id === id) return { dir: path.join(root, dir.name), manifest }; }
        return null;
    }
    const loadSpecimens = run => run.manifest.specimens.map(s => storage.readJson(path.join(run.dir, `${s.id}.json`), null)).filter(Boolean);
    async function startRun(experiment, approval, existing = null) {
        const research = loadResearch(projectRoot), id = experiment.id || `run_${Date.now()}`; if (!existing && findRun(id)) throw new Error(`run '${id}' already exists`);
        const runDir = existing ? existing.dir : runDirFor(id), controller = new AbortController(), previousUsage = existing && existing.manifest.usage;
        const catalogue = approval.catalogue || (approval.decisions.some(x => x.provider === 'openrouter') ? await policy.fetchCatalogue({ apiKey: process.env.OPENROUTER_API_KEY }) : []);
        const responseRecords = existing && existing.manifest.responses ? existing.manifest.responses.slice() : [];
        const gateway = gatewayLib.makeGateway({ catalogue, keys: { OPENAI_API_KEY: process.env.OPENAI_API_KEY, OPENROUTER_API_KEY: process.env.OPENROUTER_API_KEY }, budget: { ...(experiment.budget || {}), initial: previousUsage }, exploratory: !!experiment.exploratory,
            onUsage: usage => { const record = { at: new Date().toISOString(), role: usage.role, model: usage.model, responseId: usage.responseId || null, usage: usage.usage, policy: usage.policy }; responseRecords.push(record); const found = findRun(id); if (found) { found.manifest.usage = usage.budget; found.manifest.responses = responseRecords.slice(); storage.writeAtomic(path.join(found.dir, 'run.json'), found.manifest); } } });
        const task = { controller, dir: runDir, startedAt: Date.now() }; active.set(id, task);
        task.promise = experiments.runExperiment({ experiment: { ...experiment, id, sourceHashes: approval.sourceHashes || experiment.sourceHashes }, scenarios: research.scenarios, dossiers: research.dossiers, gateway, runDir, seed: experiment.seed || id, decisions: approval.decisions, signal: controller.signal, existingManifest: existing && existing.manifest,
            onUpdate: manifest => { manifest.responses = responseRecords.slice(); storage.writeAtomic(path.join(runDir, 'run.json'), manifest); } }).catch(() => {}).finally(() => active.delete(id));
        return { id, state: 'queued', runDir };
    }
    async function handler(req, res) {
        const url = new URL(req.url, `http://${req.headers.host || 'localhost'}`), pathname = url.pathname;
        try {
            if (req.method === 'GET' && pathname === '/api/health') return json(res, 200, { success: true, projectRoot });
            if (req.method === 'GET' && pathname === '/api/models') {
                if (!process.env.OPENROUTER_API_KEY) return json(res, 200, { success: true, models: [{ id: policy.LUNA, provider: 'openai', allowed: true }], warning: 'Set OPENROUTER_API_KEY to browse verified free variants.' });
                const catalogue = await policy.fetchCatalogue({ apiKey: process.env.OPENROUTER_API_KEY });
                const models = catalogue.filter(item => item && item.id && item.id.endsWith(':free')).map(item => ({ id: item.id, name: item.name, provider: 'openrouter', allowed: policy.decision({ provider: 'openrouter', model: item.id, catalogue }).allowed, pricing: item.pricing, supportedParameters: item.supported_parameters || [] })).filter(item => item.allowed);
                return json(res, 200, { success: true, models: [{ id: policy.LUNA, provider: 'openai', allowed: true }, ...models], warning: 'OpenRouter free variants have provider rate limits and availability changes.' });
            }
            if (req.method === 'GET' && pathname === '/api/sources') return json(res, 200, { success: true, sources: sources.discoverSources(projectRoot), candidates: sources.npcCandidates(projectRoot) });
            if (req.method === 'GET' && pathname === '/api/dossiers') return json(res, 200, { success: true, dossiers: Object.values(loadResearch(projectRoot).dossiers) });
            if (req.method === 'POST' && pathname === '/api/dossiers/compile') { const body = await readBody(req), candidate = sources.npcCandidates(projectRoot).find(x => x.id === body.id || x.displayName === body.displayName); if (!candidate) throw new Error('NPC candidate not found'); return json(res, 200, { success: true, dossier: sources.compileDossierCandidate(projectRoot, candidate, { sourcePaths: body.sourcePaths }) }); }
            if (req.method === 'POST' && pathname === '/api/dossiers') return json(res, 200, { success: true, dossier: saveDossier(projectRoot, await readBody(req)) });
            if (req.method === 'GET' && pathname === '/api/scenarios') { const data = loadResearch(projectRoot); return json(res, 200, { success: true, scenarios: data.scenarios, schedules: data.schedules, towns: data.towns }); }
            if (req.method === 'POST' && pathname === '/api/scenarios') { const body = await readBody(req); if (body.accepted === false) { const file = path.join(storage.outputRoot(installRoot, projectRoot), 'proposals', `${slug(body.id || `proposal_${Date.now()}`)}.json`); storage.writeAtomic(file, body); return json(res, 202, { success: true, accepted: false, file }); } return json(res, 200, { success: true, accepted: true, scenario: saveScenario(projectRoot, body) }); }
            if (req.method === 'POST' && pathname === '/api/schedules') return json(res, 200, { success: true, schedule: saveSchedule(projectRoot, await readBody(req)) });
            if (req.method === 'POST' && pathname === '/api/proposals') { const body = await readBody(req), research = loadResearch(projectRoot), spec = modelSpecs({ actorModels: [body.model || policy.LUNA], directorModel: body.model || policy.LUNA })[0], catalogue = spec.provider === 'openrouter' ? await policy.fetchCatalogue({ apiKey: process.env.OPENROUTER_API_KEY }) : [], gateway = gatewayLib.makeGateway({ catalogue, keys: process.env, exploratory: !!body.exploratory }); const cards = await proposals.proposeScenarios({ gateway, dossiers: research.dossiers, axes: body.axes, count: body.count || 3, model: spec.model, temperature: body.temperature || 0.9 }); const file = path.join(storage.outputRoot(installRoot, projectRoot), 'proposals', `proposal_${Date.now()}.json`); storage.writeAtomic(file, { contractVersion: 1, createdAt: new Date().toISOString(), cards }); return json(res, 200, { success: true, cards, file }); }
            if (req.method === 'POST' && pathname === '/api/runs/preflight') { const body = await readBody(req), result = await preflight({ projectRoot, experiment: body }); approvals.set(result.approvalToken, { ...result, experiment: body }); return json(res, 200, { success: true, ...result }); }
            if (req.method === 'GET' && pathname === '/api/runs') { const root = storage.outputRoot(installRoot, projectRoot), runs = []; if (fs.existsSync(root)) for (const dir of fs.readdirSync(root, { withFileTypes: true }).filter(x => x.isDirectory())) { const run = storage.readJson(path.join(root, dir.name, 'run.json'), null); if (run) runs.push({ id: run.id, state: run.state, mode: run.mode, createdAt: run.createdAt, usage: run.usage }); } return json(res, 200, { success: true, runs }); }
            if (req.method === 'POST' && pathname === '/api/runs') { const body = await readBody(req), approval = approvals.get(body.approvalToken); if (!approval || approval.expiresAt < Date.now()) throw new Error('valid, unexpired preflight approval is required'); if (JSON.stringify(approval.experiment) !== JSON.stringify(body.experiment)) throw new Error('experiment differs from preflight approval'); return json(res, 202, { success: true, ...(await startRun(body.experiment, approval)) }); }
            const match = pathname.match(/^\/api\/runs\/([^/]+)(?:\/(cancel|resume|ratings|critic|reveal|preserve))?$/);
            if (match) {
                const id = decodeURIComponent(match[1]), action = match[2], run = findRun(id); if (!run) return json(res, 404, { success: false, message: `run '${id}' not found` });
                if (req.method === 'GET' && !action) return json(res, 200, { success: true, review: experiments.reviewPayload(run.manifest, loadSpecimens(run)) });
                if (req.method === 'POST' && action === 'cancel') { const task = active.get(id); if (task) { task.controller.abort(); run.manifest.state = 'cancelling'; storage.writeAtomic(path.join(run.dir, 'run.json'), run.manifest); } return json(res, 200, { success: true }); }
                if (req.method === 'POST' && action === 'resume') { if (run.manifest.state !== 'partial') throw new Error('only partial runs may resume'); const approval = await preflight({ projectRoot, experiment: run.manifest.experiment }); if (JSON.stringify(approval.sourceHashes) !== JSON.stringify(run.manifest.sourceHashes || {})) { const error = new Error('source hashes changed since the partial run; create a new experiment instead of resuming'); error.code = 'SOURCE_HASH_MISMATCH'; throw error; } approvals.set(approval.approvalToken, { ...approval, experiment: run.manifest.experiment }); return json(res, 202, { success: true, ...(await startRun(run.manifest.experiment, approval, run)) }); }
                if (req.method === 'POST' && action === 'ratings') { const body = await readBody(req); experiments.addRating(run.manifest, body); storage.writeAtomic(path.join(run.dir, 'run.json'), run.manifest); return json(res, 200, { success: true, ratings: run.manifest.ratings }); }
                if (req.method === 'POST' && action === 'critic') {
                    const criticValue = run.manifest.experiment.criticModel;
                    const spec = typeof criticValue === 'string' ? modelSpecs(run.manifest.experiment).find(x => x.model === criticValue) : { ...(criticValue || {}) };
                    if (spec && !spec.provider) spec.provider = spec.model === policy.LUNA ? 'openai' : 'openrouter';
                    if (!spec) throw new Error('criticModel is not configured for this experiment');
                    const catalogue = spec.provider === 'openrouter' ? await policy.fetchCatalogue({ apiKey: process.env.OPENROUTER_API_KEY }) : [];
                    const criticGateway = gatewayLib.makeGateway({ catalogue, keys: { OPENAI_API_KEY: process.env.OPENAI_API_KEY, OPENROUTER_API_KEY: process.env.OPENROUTER_API_KEY }, budget: { ...(run.manifest.experiment.budget || {}), initial: run.manifest.usage }, exploratory: !!run.manifest.experiment.exploratory,
                        onUsage: usage => { run.manifest.responses ||= []; run.manifest.responses.push({ at: new Date().toISOString(), role: usage.role, model: usage.model, responseId: usage.responseId || null, usage: usage.usage, policy: usage.policy }); } });
                    run.manifest.critic = await experiments.runCritic({ manifest: run.manifest, specimens: loadSpecimens(run), gateway: criticGateway, model: spec, signal: null });
                    run.manifest.usage = criticGateway.guard.snapshot(); storage.writeAtomic(path.join(run.dir, 'run.json'), run.manifest);
                    return json(res, 200, { success: true, review: experiments.reviewPayload(run.manifest, loadSpecimens(run)) });
                }
                if (req.method === 'POST' && action === 'reveal') { experiments.reveal(run.manifest); storage.writeAtomic(path.join(run.dir, 'run.json'), run.manifest); return json(res, 200, { success: true, review: experiments.reviewPayload(run.manifest, loadSpecimens(run)) }); }
                if (req.method === 'POST' && action === 'preserve') { const body = await readBody(req), destination = experiments.preserve({ projectRoot, runDir: run.dir, manifest: run.manifest, specimens: loadSpecimens(run), findingNotes: body.findingNotes, selectedSpecimenIds: body.selectedSpecimenIds }); return json(res, 200, { success: true, destination }); }
            }
            if (req.method === 'GET' && pathname.startsWith('/api/')) return json(res, 404, { success: false, message: 'API route not found' });
            if (req.method !== 'GET' || pathname.includes('..')) return text(res, 405, 'method not allowed');
            const relative = pathname === '/' ? 'index.html' : pathname.slice(1), file = storage.safeJoin(PUBLIC, relative); if (!fs.existsSync(file) || !fs.statSync(file).isFile()) return text(res, 404, 'not found');
            const types = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8' }; return text(res, 200, fs.readFileSync(file), types[path.extname(file)] || 'application/octet-stream');
        } catch (error) { fail(res, error); }
    }
    return { handler, projectRoot, active, approvals };
}

function usage() { return 'Usage: node tools/npc-gauntlet/server.js --project <ProjectRoot> [--port 4177]\n'; }
if (require.main === module) { try { const args = parseArgs(process.argv.slice(2)); if (args.help) process.stdout.write(usage()); else { const app = createApp({ projectRoot: args.project }); http.createServer(app.handler).listen(args.port, args.host, () => console.log(`NPC Gauntlet Lab running at http://${args.host}:${args.port}`)); } } catch (error) { process.stderr.write(`NPC Gauntlet Lab failed: ${error.message}\n${usage()}`); process.exitCode = 1; } }
module.exports = { parseArgs, createApp, loadResearch, preflight, modelSpecs, sourceHashes };
