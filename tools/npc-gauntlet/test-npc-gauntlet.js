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
const livingTown = require('./lib/living-town');
const gateway = require('./lib/gateway');
const experiment = require('./lib/experiment');
const sources = require('./lib/sources');
const storage = require('./lib/storage');
const server = require('./server');
const sharedLlm = require('../shared/llm');

function catalogue() { return [{ id: 'meta/demo:free', name: 'Demo Free', pricing: { prompt: '0', completion: '0', request: '0' }, supported_parameters: ['response_format'] }]; }
function dossier(id, target) { return { contractVersion: 1, id, displayName: id, facts: [{ kind: 'source', text: `${id} is observant`, sourceRefs: [{ path: 'docs/characters.md', sha256: 'a'.repeat(64) }] }], privateKnowledge: [`${id} knows a private fact`], goals: ['keep dignity'], behavioralTensions: ['wants help but refuses to ask'], relationships: { [target]: { dimensions: [{ key: 'respect', initial: 0 }] } }, routines: [] }; }
function scenario() { return { contractVersion: 1, id: 'test_scene', title: 'A small disagreement', premise: 'Two people need to decide who gets the last chair.', participants: ['alice', 'bob'], maxTurns: 2, pressures: ['embarrassment'], constraints: ['No violence'], allowedFacts: [] }; }
function livingDefinition() { return { contractVersion: 1, id: 'test_town', title: 'A working day', timeBlocks: [{ id: 'morning', label: 'Morning' }, { id: 'evening', label: 'Evening' }], locations: [{ id: 'shop', name: 'Shop', neighbors: ['square'] }, { id: 'square', name: 'Square', neighbors: ['shop'] }], npcIds: ['alice', 'bob'], initialNpcState: { alice: { location: 'shop', energy: 3, obligations: [{ id: 'repair', description: 'Repair the shutter', location: 'shop', deadline: 'evening', priority: 5, effort: 2 }] }, bob: { location: 'shop', energy: 3, obligations: [] } }, ambientPressures: [], publicFacts: [] }; }

test('shared transport uses each provider\'s streamed usage contract', async () => {
    const bodies = [];
    const fetchImpl = async (_url, options) => {
        bodies.push(JSON.parse(options.body));
        return new Response('data: {"choices":[{"delta":{"content":"{}"}}],"usage":{"prompt_tokens":1,"completion_tokens":1,"total_tokens":2}}\n\ndata: [DONE]\n', { status: 200, headers: { 'Content-Type': 'text/event-stream' } });
    };
    const request = { apiKey: 'test', model: 'model', temperature: 0, messages: [], maxRetries: 1, fetchImpl };
    await sharedLlm.chat({ ...request, baseUrl: 'https://api.openai.com/v1' });
    await sharedLlm.chat({ ...request, baseUrl: 'https://openrouter.ai/api/v1' });
    assert.deepEqual(bodies[0].stream_options, { include_usage: true });
    assert.equal(bodies[0].usage, undefined);
    assert.deepEqual(bodies[1].usage, { include: true });
    assert.equal(bodies[1].stream_options, undefined);
});

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

test('author canon outranks derived evidence and minimum turns keep a UX scene alive', async () => {
    const alice = { ...dossier('alice', 'bob'), canon: { core: 'Tender but never ingratiating', tags: ['guarded warmth'], antiTropes: ['therapist voice'] }, relationshipCanon: { bob: { dynamic: 'careful rivalry', signals: 'offers practical help', avoid: 'instant reconciliation' } } };
    const prompt = simulation.actorPrompt({ actor: { id: 'alice' }, dossier: schemas.validateDossier(alice), scenario: schemas.validateScenarioCard({ ...scenario(), minTurns: 2 }), state: simulation.initialState([{ id: 'alice' }, { id: 'bob' }], { alice, bob: dossier('bob', 'alice') }, [{ id: 'alice' }, { id: 'bob' }]), transcript: [], participants: [{ id: 'alice' }, { id: 'bob' }] });
    assert.match(prompt, /AUTHOR-SUPPLIED CANON \(highest character authority\)/);
    assert.match(prompt, /Participants \(target must use the exact id.*alice \(alice\), bob \(bob\)/);
    assert.match(prompt, /RELATIONSHIP-SPECIFIC CANON.*careful rivalry/s);
    assert.ok(prompt.indexOf('Tender but never ingratiating') < prompt.indexOf('Character facts'));
    const fake = { call: async ({ role }) => role === 'actor'
        ? { value: { action: 'speak', speech: 'Still here.', target: 'bob' } }
        : { value: { continue: false, nextSpeaker: null, terminationReason: 'too_soon', publicFacts: [], privateFacts: [], relationshipUpdates: [] } } };
    const result = await simulation.runEpisode({ scenario: { ...scenario(), minTurns: 2 }, dossiers: { alice, bob: dossier('bob', 'alice') }, gateway: fake, models: { actor: 'gpt-5.6-luna', director: 'gpt-5.6-luna' }, seed: 'minimum' });
    assert.equal(result.transcript.length, 2);
    assert.deepEqual(result.transcript.map(turn => turn.speaker), ['alice', 'bob']);
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

test('town mode snapshots each slot state instead of aliasing the final day state', async () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'npc-lab-town-'));
    try {
        let count = 0;
        const fake = { guard: { snapshot: () => ({ calls: count, tokens: count * 4, usd: 0 }) }, call: async ({ role }) => {
            count++;
            if (role === 'actor') return { value: { action: 'speak', speech: 'Still here.', target: 'bob' } };
            return { value: { continue: false, nextSpeaker: null, terminationReason: `slot_${count}`, publicFacts: [{ text: `Fact ${count}.`, salience: 2, participants: ['alice', 'bob'] }], privateFacts: [], relationshipUpdates: [] } };
        } };
        const town = { contractVersion: 1, id: 'test_day', title: 'Test day', slots: [
            { time: 'morning', location: 'shop', scenarioIds: ['test_scene'], availableParticipantIds: ['alice', 'bob'] },
            { time: 'evening', location: 'forge', scenarioIds: ['test_scene'], availableParticipantIds: ['alice', 'bob'] },
        ] };
        const result = await experiment.runExperiment({ experiment: { contractVersion: 1, id: 'town_test', mode: 'town', scenarioIds: ['test_scene'], schedule: town, actorModels: ['gpt-5.6-luna'], directorModel: 'gpt-5.6-luna', repetitions: 1, concurrency: 1, budget: { maxUsd: 1 } }, scenarios: [scenario()], dossiers: { alice: dossier('alice', 'bob'), bob: dossier('bob', 'alice') }, gateway: fake, runDir: root, seed: 'town' });
        const episodes = result.specimens[0].result.episodes;
        assert.equal(episodes.length, 2);
        assert.equal(episodes[0].state.events.length, 1);
        assert.equal(episodes[1].state.events.length, 2);
        assert.notEqual(episodes[0].state, episodes[1].state);
    } finally { fs.rmSync(root, { recursive: true, force: true }); }
});

test('living town resolves material plans and creates encounters only from colliding intentions', async () => {
    const definition = schemas.validateLivingTown(livingDefinition());
    assert.equal(livingTown.shortestNext(definition, 'shop', 'square'), 'square');
    let calls = 0;
    const fake = { call: async ({ role, messages }) => {
        calls++;
        const prompt = messages[1].content;
        if (role === 'town-encounter') return { value: { physicalAction: 'keeps a hand on the shutter', speech: '', privateInterpretation: 'The help is useful.', nextIntention: 'Finish the repair.' } };
        const isAlice = /Choose alice's/.test(prompt), isMorning = /for Morning/.test(prompt);
        if (!isMorning) return { value: { kind: 'linger', destination: null, target: null, obligationId: null, talk: false, reason: 'The work is done.', approach: 'Stays with the ordinary routine.', expectedOutcome: 'The block passes quietly.' } };
        if (isAlice) return { value: { kind: 'work', destination: null, target: null, obligationId: 'repair', talk: false, reason: 'The shutter is due.', approach: 'Fits the repaired hinge.', expectedOutcome: 'The repair advances.' } };
        return { value: { kind: 'help', destination: null, target: 'alice', obligationId: null, talk: true, reason: 'A second pair of hands will finish sooner.', approach: 'Holds the shutter in place.', expectedOutcome: 'The repair is completed.' } };
    } };
    const result = await livingTown.runLivingTown({ definition, dossiers: { alice: dossier('alice', 'bob'), bob: dossier('bob', 'alice') }, gateway: fake, model: 'gpt-5.6-luna', seed: 'living' });
    assert.equal(result.blocks[0].state.npcs.alice.obligations[0].status, 'complete');
    assert.equal(result.blocks[0].encounters.length, 1);
    assert.equal(result.blocks[1].encounters.length, 0);
    assert.equal(result.blocks[0].encounters[0].beats.every(beat => beat.speech === ''), true);
    assert.equal(calls, 6);
});

test('multi-day living town activates seeded pressures, scheduled work, recovery, and cash transfer', () => {
    const raw = livingDefinition();
    raw.timeBlocks = [
        { id: 'morning', label: 'Monday morning', day: 'Monday', phase: 'morning', dayStart: true, energyRecovery: 2 },
        { id: 'evening', label: 'Monday evening', day: 'Monday', phase: 'evening', dayEnd: true },
    ];
    raw.initialNpcState.alice.cash = 2;
    raw.initialNpcState.alice.energy = 1;
    raw.initialNpcState.alice.obligations = [{ id: 'pay_bob', description: 'Pay Bob', location: 'shop', startsAt: 'evening', deadline: 'evening', priority: 5, effort: 1, cashCost: 2, payTo: 'bob', triggeredBy: 'bill_due' }];
    raw.initialNpcState.bob.cash = 0;
    raw.ambientPressures = [{ id: 'bill_due', description: 'The bill comes due.', location: 'shop', startsAt: 'evening', deadline: 'evening', stakes: 'Bob expects payment.', satisfiedBy: 'pay_bob', consequence: 'The bill remains unpaid.', chance: 1 }];
    const definition = livingTown.materializeDefinition(schemas.validateLivingTown(raw), 'week');
    const state = livingTown.initialState(definition);
    assert.equal(definition.chanceEvents[0].activated, true);
    assert.equal(state.npcs.alice.obligations[0].status, 'pending');
    livingTown.beginBlock({ definition, dossiers: { alice: dossier('alice', 'bob'), bob: dossier('bob', 'alice') }, state, block: definition.timeBlocks[0] });
    assert.equal(state.npcs.alice.energy, 3);
    livingTown.beginBlock({ definition, dossiers: { alice: dossier('alice', 'bob'), bob: dossier('bob', 'alice') }, state, block: definition.timeBlocks[1] });
    assert.equal(state.npcs.alice.obligations[0].status, 'open');
    const plans = {
        alice: { kind: 'work', destination: null, target: null, obligationId: 'pay_bob', talk: false, reason: 'The bill is due.', approach: 'Pays it.', expectedOutcome: 'The account is settled.' },
        bob: { kind: 'linger', destination: null, target: null, obligationId: null, talk: false, reason: 'Waits.', approach: 'Stays put.', expectedOutcome: 'Payment may arrive.' },
    };
    livingTown.resolvePlans({ definition, dossiers: { alice: dossier('alice', 'bob'), bob: dossier('bob', 'alice') }, state, plans, block: definition.timeBlocks[1], seed: 'week' });
    assert.equal(state.npcs.alice.cash, 0);
    assert.equal(state.npcs.bob.cash, 2);
    const summary = livingTown.endDay({ definition, dossiers: {}, state, block: definition.timeBlocks[1] });
    assert.equal(summary.day, 'Monday');
    assert.equal(summary.completed.length, 1);
});

test('arrival obligations complete on movement and nights away grant limited recovery', () => {
    const raw = livingDefinition();
    raw.timeBlocks = [{ id: 'evening', label: 'Monday evening', day: 'Monday', dayEnd: true }, { id: 'morning', label: 'Tuesday morning', day: 'Tuesday', dayStart: true, energyRecovery: 3 }];
    raw.initialNpcState.alice = { location: 'shop', home: 'shop', energy: 1, cash: 1, obligations: [{ id: 'visit', description: 'Attend the gathering', location: 'square', deadline: 'evening', priority: 5, effort: 1, completion: 'arrive' }] };
    const definition = schemas.validateLivingTown(raw), state = livingTown.initialState(definition), dossiers = { alice: dossier('alice', 'bob'), bob: dossier('bob', 'alice') };
    const plans = {
        alice: { kind: 'move', destination: 'square', target: null, obligationId: null, talk: false, reason: 'The gathering matters.', approach: 'Walks to the square.', expectedOutcome: 'Arrives.' },
        bob: { kind: 'linger', destination: null, target: null, obligationId: null, talk: false, reason: 'No demand.', approach: 'Waits.', expectedOutcome: 'Nothing changes.' },
    };
    livingTown.resolvePlans({ definition, dossiers, state, plans, block: definition.timeBlocks[0], seed: 'arrival' });
    assert.equal(state.npcs.alice.obligations[0].status, 'complete');
    livingTown.beginBlock({ definition, dossiers, state, block: definition.timeBlocks[1] });
    assert.equal(state.npcs.alice.energy, 2);
    assert.match(state.publicEvents.find(event => event.type === 'overnight-recovery' && event.participants.includes('alice')).summary, /spending the night away from home/);
});

test('living town experiment call estimate includes plans and bounded encounter beats', () => {
    assert.equal(experiment.expectedCalls({ mode: 'living-town', repetitions: 1, actorModels: ['gpt-5.6-luna'], townDefinition: livingDefinition() }, []), 16);
});

test('living town ratings measure agency and causality instead of directed-scene craft', () => {
    const manifest = experiment.createManifest({ contractVersion: 1, id: 'living_rating', mode: 'living-town', actorModels: ['gpt-5.6-luna'], repetitions: 1, townDefinition: livingDefinition() }, [], [], 'rating');
    const scores = Object.fromEntries(experiment.LIVING_RATING_DIMENSIONS.map(key => [key, 4]));
    experiment.addRating(manifest, { specimenId: manifest.specimens[0].id, scores, notes: 'choices caused consequences', tags: ['conversation-gravity'] });
    assert.equal(manifest.ratings[0].scores.npcAgency, 4);
    assert.throws(() => experiment.addRating(manifest, { specimenId: manifest.specimens[0].id, scores: Object.fromEntries(experiment.SCENE_RATING_DIMENSIONS.map(key => [key, 4])), notes: 'wrong rubric' }), /canonFidelity/);
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
