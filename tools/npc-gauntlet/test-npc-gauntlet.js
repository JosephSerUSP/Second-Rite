'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const http = require('node:http');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');
const policy = require('./lib/model-policy');
const schemas = require('./lib/schemas');
const simulation = require('./lib/simulation');
const gateway = require('./lib/gateway');
const experiment = require('./lib/experiment');
const sources = require('./lib/sources');
const storage = require('./lib/storage');
const server = require('./server');

function catalogue() { return [{ id: 'meta/demo:free', name: 'Demo Free', pricing: { prompt: '0', completion: '0', request: '0' }, supported_parameters: ['response_format'] }]; }
function dossier(id, target) { return { contractVersion: 1, id, displayName: id, facts: [{ kind: 'source', text: `${id} is observant`, sourceRefs: [{ path: 'docs/characters.md', sha256: 'a'.repeat(64) }] }], privateKnowledge: [`${id} knows a private fact`], goals: ['keep dignity'], behavioralTensions: ['wants help but refuses to ask'], relationships: { [target]: { dimensions: [{ key: 'respect', initial: 0 }] } }, routines: [] }; }
function scenario() { return { contractVersion: 1, id: 'test_scene', title: 'A small disagreement', premise: 'Two people need to decide who gets the last chair.', participants: ['alice', 'bob'], maxTurns: 2, pressures: ['embarrassment'], constraints: ['No violence'], allowedFacts: [] }; }

test('model policy accepts only Luna or verified OpenRouter free variants', () => {
    assert.equal(policy.decision({ provider: 'openai', model: 'gpt-5.6-luna' }).allowed, true);
    assert.equal(policy.decision({ provider: 'openai', model: 'gpt-5.6-sol' }).allowed, false);
    assert.equal(policy.decision({ provider: 'deepseek', model: 'deepseek-chat' }).allowed, false);
    assert.equal(policy.decision({ provider: 'openrouter', model: 'meta/demo:free', catalogue: catalogue() }).allowed, true);
    assert.equal(policy.decision({ provider: 'openrouter', model: 'meta/demo', catalogue: catalogue() }).allowed, false);
    assert.equal(policy.decision({ provider: 'openrouter', model: 'meta/unknown:free', catalogue: catalogue() }).allowed, false);
    assert.equal(policy.decision({ provider: 'openrouter', model: 'openai/gpt-4o:free', catalogue: [{ id: 'openai/gpt-4o:free', pricing: { prompt: '0', completion: '0' }, supported_parameters: ['response_format'] }] }).allowed, false);
    assert.equal(policy.decision({ provider: 'openrouter', model: 'openrouter/free', catalogue: catalogue() }).allowed, false);
    assert.equal(policy.decision({ provider: 'openrouter', model: 'openrouter/free', catalogue: catalogue(), exploratory: true }).allowed, true);
    assert.equal(policy.decision({ provider: 'openrouter', model: 'community/actual:free', catalogue: [{ id: 'community/actual:free', pricing: { prompt: '0', completion: '0', request: '0' }, supported_parameters: ['response_format'] }], fromDynamicRouter: true }).allowed, true);
});

test('schemas reject malformed dossiers, scenarios, and invalid relationship bounds', () => {
    assert.throws(() => schemas.validateDossier({ contractVersion: 1, id: 'Bad ID' }), /id/);
    assert.throws(() => schemas.validateScenarioCard({ contractVersion: 1, id: 'x', title: 'x', premise: 'x', participants: ['a'], maxTurns: 2 }), /two or three/);
    assert.throws(() => schemas.validateDossier({ ...dossier('alice', 'bob'), relationships: { bob: { dimensions: [{ key: 'respect', initial: 9 }] } } }), /from -5 to 5/);
});

test('episode actors cannot mutate state; director facts and directional relationships do', async () => {
    const calls = [];
    const fake = { call: async ({ role }) => {
        calls.push(role);
        if (role === 'actor') return { value: { action: 'speak', speech: 'I will wait.', target: 'bob' } };
        return { value: {
            continue: false, nextSpeaker: null, terminationReason: 'resolved',
            publicFacts: [{ text: 'Alice waited instead of taking the chair.', salience: 4, participants: ['alice', 'bob'] }],
            privateFacts: [{ to: 'alice', text: 'Bob noticed the restraint.', salience: 3 }],
            relationshipUpdates: [{ from: 'alice', to: 'bob', dimension: 'respect', delta: 1, evidence: 'seed.turn.0' }],
        } };
    } };
    const result = await simulation.runEpisode({ scenario: scenario(), dossiers: { alice: dossier('alice', 'bob'), bob: dossier('bob', 'alice') }, gateway: fake, models: { actor: 'gpt-5.6-luna', director: 'gpt-5.6-luna' }, seed: 'seed' });
    assert.deepEqual(calls, ['actor', 'director']);
    assert.equal(result.state.relationships.alice.bob.respect, 1);
    assert.equal(result.state.privateFacts.alice.length, 1);
    assert.equal(result.state.events.length, 1);
});

test('experiment runner writes resumable specimen artifacts for scene mode', async () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'npc-lab-run-'));
    try {
        let count = 0;
        const fake = { guard: { snapshot: () => ({ calls: count, tokens: count * 4, usd: 0 }) }, call: async ({ role }) => {
            count++;
            if (role === 'actor') return { value: { action: 'speak', speech: 'I will wait.', target: 'bob' } };
            return { value: { continue: false, nextSpeaker: null, terminationReason: 'done', publicFacts: [{ text: 'A fact.', salience: 2, participants: ['alice', 'bob'] }], privateFacts: [], relationshipUpdates: [] } };
        } };
        const result = await experiment.runExperiment({ experiment: { contractVersion: 1, id: 'run_test', mode: 'scene', scenarioIds: ['test_scene'], actorModels: ['gpt-5.6-luna'], directorModel: 'gpt-5.6-luna', repetitions: 1, maxTurns: 2, budget: { maxUsd: 1 } }, scenarios: [scenario()], dossiers: { alice: dossier('alice', 'bob'), bob: dossier('bob', 'alice') }, gateway: fake, runDir: root, seed: 'run' });
        assert.equal(result.manifest.state, 'complete'); assert.equal(result.manifest.specimens[0].status, 'complete'); assert.ok(fs.existsSync(path.join(root, 'specimen_001.json'))); assert.equal(JSON.parse(fs.readFileSync(path.join(root, 'run.json'))).state, 'complete');
    } finally { fs.rmSync(root, { recursive: true, force: true }); }
});

test('critic requires human review and returns annotations without ranking', async () => {
    const manifest = experiment.createManifest({ contractVersion: 1, id: 'critic_test', mode: 'scene', actorModels: ['gpt-5.6-luna'], repetitions: 1 }, [scenario()], [], 'critic');
    const specimen = { specimenId: manifest.specimens[0].id, blindLabel: manifest.specimens[0].blindLabel, result: { transcript: [] } };
    assert.rejects(() => experiment.runCritic({ manifest, specimens: [specimen], gateway: { call: async () => ({}) }, model: 'gpt-5.6-luna' }), /human ratings/);
    experiment.addRating(manifest, { specimenId: specimen.specimenId, scores: { recognizability: 3, relationshipSpecificity: 3, unresolvedFriction: 3, generativity: 3, genreDefaults: 3, scopeInflation: 3 }, notes: 'reviewed' });
    const result = await experiment.runCritic({
        manifest, specimens: [specimen], model: 'gpt-5.6-luna',
        gateway: { call: async () => ({ model: 'gpt-5.6-luna', value: { annotations: [{ specimenId: specimen.specimenId, notes: 'observed', tags: [], scores: { recognizability: 3, relationshipSpecificity: 3, unresolvedFriction: 3, generativity: 3, genreDefaults: 3, scopeInflation: 3 } }] } }) },
    });
    assert.equal(result.annotations.length, 1); assert.equal(result.annotations[0].specimenId, specimen.specimenId);
});

test('memory retrieval is deterministic and salience/relevance weighted', () => {
    const memories = { alice: [{ id: 'old', text: 'old', salience: 1, participants: [] }, { id: 'relevant', text: 'relevant', salience: 2, participants: ['bob'] }, { id: 'high', text: 'high', salience: 5, participants: [] }] };
    assert.deepEqual(simulation.selectMemories(memories, 'alice', ['bob'], 2).map(x => x.id), ['high', 'relevant']);
});

test('budget guard stops calls at hard caps and records usage', () => {
    const guard = new gateway.BudgetGuard({ maxCalls: 1, maxTokens: 5, maxUsd: 0.1 }); guard.beforeCall(); guard.afterCall({ prompt_tokens: 2, completion_tokens: 2, total_tokens: 4, cost: 0.01 });
    assert.equal(guard.snapshot().calls, 1); assert.throws(() => guard.beforeCall(), /request cap/);
});

test('blind labels are deterministic and reveal is blocked until human rating', () => {
    const manifest = experiment.createManifest({ contractVersion: 1, id: 'x', mode: 'scene', actorModels: ['gpt-5.6-luna'], repetitions: 1 }, [scenario()], [], 'same');
    assert.deepEqual(manifest.specimens.map(x => x.blindLabel), experiment.createManifest({ contractVersion: 1, id: 'x', mode: 'scene', actorModels: ['gpt-5.6-luna'], repetitions: 1 }, [scenario()], [], 'same').specimens.map(x => x.blindLabel));
    assert.throws(() => experiment.reveal(manifest), /rating/);
    experiment.addRating(manifest, { specimenId: manifest.specimens[0].id, scores: { recognizability: 4, relationshipSpecificity: 4, unresolvedFriction: 3, generativity: 4, genreDefaults: 2, scopeInflation: 1 }, notes: 'specific' });
    experiment.reveal(manifest); assert.equal(manifest.revealed, true);
});

test('source discovery ignores archive and compiles cited live dialogue', () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'npc-lab-source-'));
    try {
        fs.mkdirSync(path.join(root, 'data'), { recursive: true }); fs.mkdirSync(path.join(root, 'docs', 'archive'), { recursive: true });
        fs.writeFileSync(path.join(root, 'data', 'maps.json'), JSON.stringify({ speaker: 'Alicia', text: 'Please wait.' }));
        fs.writeFileSync(path.join(root, 'docs', 'archive', 'old.md'), 'speaker: Fake');
        const candidates = sources.npcCandidates(root); assert.equal(candidates[0].displayName, 'Alicia');
        const compiled = sources.compileDossierCandidate(root, candidates[0]); assert.equal(compiled.facts[0].kind, 'source'); assert.equal(compiled.facts[0].sourceRefs[0].sha256.length, 64);
    } finally { fs.rmSync(root, { recursive: true, force: true }); }
});

test('HTTP app serves local health and never writes Project data for read-only routes', async t => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'npc-lab-http-')); const installRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'npc-lab-out-'));
    t.after(() => { fs.rmSync(root, { recursive: true, force: true }); fs.rmSync(installRoot, { recursive: true, force: true }); });
    fs.mkdirSync(path.join(root, 'data'), { recursive: true }); fs.writeFileSync(path.join(root, 'data', 'maps.json'), JSON.stringify({ speaker: 'Alicia', text: 'Hello.' }));
    const before = storage.sha256File(path.join(root, 'data', 'maps.json')), app = server.createApp({ projectRoot: root, installRoot }), listener = http.createServer(app.handler);
    await new Promise((resolve, reject) => { listener.once('error', reject); listener.listen(0, '127.0.0.1', resolve); });
    t.after(() => listener.close()); const port = listener.address().port;
    const get = route => new Promise((resolve, reject) => http.get({ hostname: '127.0.0.1', port, path: route }, response => { let body = ''; response.setEncoding('utf8'); response.on('data', x => body += x); response.on('end', () => resolve({ status: response.statusCode, body: JSON.parse(body) })); }).on('error', reject));
    assert.equal((await get('/api/health')).body.success, true); assert.equal((await get('/api/sources')).body.candidates[0].displayName, 'Alicia'); assert.equal(storage.sha256File(path.join(root, 'data', 'maps.json')), before);
});
