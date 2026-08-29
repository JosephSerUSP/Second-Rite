'use strict';

const crypto = require('crypto');
const path = require('path');
const fs = require('fs');
const { runEpisode, hash, actorPrompt, directorPrompt } = require('./simulation');
const { validateScenarioCard, validateTownSchedule, validateDossier, validateRunManifest, validatePreservedExperiment } = require('./schemas');
const { proposeScenarios } = require('./proposals');

const CRITIC_SCHEMA = { type: 'json_schema', json_schema: { name: 'npc_gauntlet_critique', strict: true, schema: {
    type: 'object', additionalProperties: false, properties: { annotations: { type: 'array', items: {
        type: 'object', additionalProperties: false, properties: {
            specimenId: { type: 'string' }, notes: { type: 'string' }, tags: { type: 'array', items: { type: 'string' } },
            scores: { type: 'object', additionalProperties: false, properties: {
                recognizability: { type: 'integer', minimum: 1, maximum: 5 }, relationshipSpecificity: { type: 'integer', minimum: 1, maximum: 5 },
                unresolvedFriction: { type: 'integer', minimum: 1, maximum: 5 }, generativity: { type: 'integer', minimum: 1, maximum: 5 },
                genreDefaults: { type: 'integer', minimum: 1, maximum: 5 }, scopeInflation: { type: 'integer', minimum: 1, maximum: 5 },
            }, required: ['recognizability', 'relationshipSpecificity', 'unresolvedFriction', 'generativity', 'genreDefaults', 'scopeInflation'] },
        }, required: ['specimenId', 'notes', 'tags', 'scores'],
    } } }, required: ['annotations'],
} } };
const storage = require('./storage');
const FAILURE_TAGS = ['premature-reconciliation', 'therapeutic-voice', 'self-explained-motives', 'tidy-arcs', 'protagonist-magnetism', 'exposition-dialogue', 'catchphrase-only-characterization'];

function safeId(value) { return String(value).toLowerCase().replace(/[^a-z0-9_-]+/g, '_').replace(/^_+|_+$/g, '').slice(0, 64) || 'run'; }
function manifestId(experiment) { return safeId(experiment.id || `run_${Date.now()}`); }
function randomizeLabels(specimens, seed) {
    const labels = specimens.map((_, i) => `Specimen ${String.fromCharCode(65 + (i % 26))}${Math.floor(i / 26) || ''}`);
    let x = parseInt(hash(seed).slice(0, 8), 16) >>> 0;
    for (let i = labels.length - 1; i > 0; i--) { x = (1664525 * x + 1013904223) >>> 0; const j = x % (i + 1); [labels[i], labels[j]] = [labels[j], labels[i]]; }
    return labels;
}

function expectedCalls(experiment, scenarios) {
    const repeats = Number(experiment.repetitions || 1);
    const actorCount = Array.isArray(experiment.actorModels) ? experiment.actorModels.length : 1;
    const variantCount = Array.isArray(experiment.promptVariants) && experiment.promptVariants.length ? experiment.promptVariants.length : 1;
    // Episode cards own their turn bound; an experiment-level hint must not
    // under-estimate a card and accidentally approve an unsafe hard cap.
    const turns = scenario => Number(scenario.maxTurns || 8);
    if (experiment.mode === 'town') {
        const schedule = experiment.schedule || { slots: [] };
        // A town specimen chooses at most one eligible card per slot.  The
        // actor-model axis and repetitions multiply the complete schedule.
        return actorCount * variantCount * repeats * (schedule.slots || []).reduce((sum, slot) => {
            const eligible = scenarios.filter(s => (slot.scenarioIds || []).includes(s.id));
            return sum + 2 * (eligible.length ? Math.max(...eligible.map(turns)) : 0);
        }, 0);
    }
    return actorCount * variantCount * repeats * scenarios.reduce((sum, scenario) => sum + 2 * turns(scenario), 0);
}

function validateExperiment(experiment, scenarios, dossiers) {
    if (!experiment || experiment.contractVersion !== 1) throw new Error('experiment.contractVersion must be 1');
    if (!['scene', 'town'].includes(experiment.mode)) throw new Error('experiment.mode must be scene or town');
    if (experiment.id !== undefined && (typeof experiment.id !== 'string' || !/^[a-z0-9][a-z0-9_-]{0,63}$/.test(experiment.id))) throw new Error('experiment.id must match [a-z0-9][a-z0-9_-]{0,63}');
    if (!Array.isArray(experiment.actorModels) || !experiment.actorModels.length) throw new Error('experiment.actorModels must not be empty');
    const validateModelSpec = (spec, label) => {
        if (typeof spec === 'string') { if (!spec.trim()) throw new Error(`${label} must name a model`); return; }
        if (!spec || typeof spec !== 'object' || typeof spec.model !== 'string' || !spec.model.trim()) throw new Error(`${label} must be a model string or {model, provider}`);
    };
    experiment.actorModels.forEach((spec, i) => validateModelSpec(spec, `experiment.actorModels[${i}]`));
    validateModelSpec(experiment.directorModel, 'experiment.directorModel');
    if (experiment.repetitions !== undefined && (!Number.isInteger(experiment.repetitions) || experiment.repetitions < 1 || experiment.repetitions > 1000)) throw new Error('experiment.repetitions must be an integer from 1 to 1000');
    if (experiment.concurrency !== undefined && (!Number.isInteger(experiment.concurrency) || experiment.concurrency < 1 || experiment.concurrency > 4)) throw new Error('experiment.concurrency must be an integer from 1 to 4');
    if (experiment.promptVariants !== undefined) {
        if (!Array.isArray(experiment.promptVariants) || !experiment.promptVariants.length || experiment.promptVariants.length > 20) throw new Error('experiment.promptVariants must contain 1..20 variants');
        experiment.promptVariants.forEach((variant, i) => { if (typeof variant !== 'string' || variant.length > 4000) throw new Error(`experiment.promptVariants[${i}] must be a string of at most 4000 characters`); });
    }
    if (experiment.maxTurns !== undefined && (!Number.isInteger(experiment.maxTurns) || experiment.maxTurns < 1 || experiment.maxTurns > 50)) throw new Error('experiment.maxTurns must be an integer from 1 to 50');
    if (experiment.temperature !== undefined && (!Number.isFinite(Number(experiment.temperature)) || Number(experiment.temperature) < 0 || Number(experiment.temperature) > 2)) throw new Error('experiment.temperature must be 0..2');
    if (experiment.directorTemperature !== undefined && (!Number.isFinite(Number(experiment.directorTemperature)) || Number(experiment.directorTemperature) < 0 || Number(experiment.directorTemperature) > 2)) throw new Error('experiment.directorTemperature must be 0..2');
    if (experiment.budget !== undefined) {
        if (!experiment.budget || typeof experiment.budget !== 'object' || Array.isArray(experiment.budget)) throw new Error('experiment.budget must be an object');
        for (const key of ['maxUsd', 'maxCalls', 'maxTokens']) if (experiment.budget[key] !== undefined && (!Number.isFinite(Number(experiment.budget[key])) || Number(experiment.budget[key]) < 0)) throw new Error(`experiment.budget.${key} must be a non-negative number`);
    }
    if (experiment.scenarioIds !== undefined && (!Array.isArray(experiment.scenarioIds) || experiment.scenarioIds.some(x => typeof x !== 'string' || !/^[a-z0-9][a-z0-9_-]{0,63}$/.test(x)))) throw new Error('experiment.scenarioIds must be an array of valid ids');
    const ids = new Set(experiment.scenarioIds || []);
    if (experiment.mode === 'town' && experiment.schedule) for (const slot of experiment.schedule.slots || []) for (const id of slot.scenarioIds || []) ids.add(id);
    const availableIds = new Set(scenarios.map(s => s.id));
    for (const selectedId of ids) if (!availableIds.has(selectedId)) throw new Error(`experiment references unknown scenario '${selectedId}'`);
    const selected = scenarios.filter(s => ids.has(s.id)).map(s => validateScenarioCard(s));
    if (experiment.mode === 'scene' && !selected.length) throw new Error('scene experiment must select at least one scenario');
    selected.forEach(s => validateScenarioCard(s));
    if (experiment.mode === 'town') validateTownSchedule(experiment.schedule);
    for (const scenario of selected) for (const participant of scenario.participants) {
        if (participant.type !== 'playerProxy') validateDossier(dossiers[participant.id], `dossiers.${participant.id}`);
    }
    return selected;
}

function createManifest(experiment, scenarios, decisions, seed) {
    const variants = Array.isArray(experiment.promptVariants) && experiment.promptVariants.length ? experiment.promptVariants : ['baseline'];
    const specimenCount = Number(experiment.repetitions || 1) * variants.length * (experiment.mode === 'town' ? 1 : scenarios.length) * experiment.actorModels.length;
    const specimens = Array.from({ length: specimenCount }, (_, i) => ({ id: `specimen_${String(i + 1).padStart(3, '0')}`, blindLabel: `pending_${i + 1}`, status: 'queued' }));
    const labels = randomizeLabels(specimens, seed);
    specimens.forEach((s, i) => { s.blindLabel = labels[i]; });
    return {
        contractVersion: 1, id: manifestId(experiment), state: 'queued', mode: experiment.mode,
        createdAt: new Date().toISOString(), seed, experiment: JSON.parse(JSON.stringify(experiment)),
        scenarioSnapshots: JSON.parse(JSON.stringify(scenarios)),
        modelPolicy: decisions, modelConfigHash: hash(storage.stableJson({ models: experiment.actorModels, director: experiment.directorModel, critic: experiment.criticModel, scenarioGenerator: experiment.scenarioGeneratorModel, temperature: experiment.temperature, directorTemperature: experiment.directorTemperature, promptVariants: variants })),
        promptHashes: {
            actor: hash(actorPrompt.toString()), director: hash(directorPrompt.toString()),
            critic: hash(runCritic.toString()), scenarioGenerator: hash(proposeScenarios.toString()),
        }, sourceHashes: experiment.sourceHashes || {}, specimens,
        usage: { calls: 0, tokens: 0, usd: 0 }, responses: [], events: [], ratings: [], revealed: false,
    };
}

function writeManifest(runDir, manifest) { validateRunManifest(manifest); storage.writeAtomic(path.join(runDir, 'run.json'), manifest); }

function slotAllowsScenario(slot, scenario, dossiers, schedule) {
    if (slot.eligibleScenarioIds && !slot.eligibleScenarioIds.includes(scenario.id)) return false;
    const available = slot.availableParticipantIds || slot.availableParticipants;
    if (available && scenario.participants.some(participant => participant.type !== 'playerProxy' && !available.includes(participant.id))) return false;
    const availability = schedule && schedule.availability;
    if (availability) for (const participant of scenario.participants) {
        const windows = availability[participant.id];
        if (windows && !windows.includes('*') && !windows.includes(slot.time)) return false;
    }
    return true;
}

async function runExperiment({ experiment, scenarios, dossiers, gateway, runDir, seed = `${Date.now()}`, decisions = [], signal, onUpdate = () => {}, existingManifest = null }) {
    const validated = validateExperiment(experiment, scenarios, dossiers);
    const selected = existingManifest && Array.isArray(existingManifest.scenarioSnapshots)
        ? existingManifest.scenarioSnapshots.map(s => validateScenarioCard(s)) : validated;
    const manifest = existingManifest || createManifest(experiment, selected, decisions, seed);
    storage.ensureDir(runDir); writeManifest(runDir, manifest);
    manifest.state = 'running'; manifest.error = null; writeManifest(runDir, manifest); onUpdate(manifest);
    const specimenOutputs = [];
    try {
        const tasks = [], actorModels = experiment.actorModels, repetitions = Number(experiment.repetitions || 1);
        const variants = Array.isArray(experiment.promptVariants) && experiment.promptVariants.length ? experiment.promptVariants : ['baseline'];
        let specimenIndex = 0;
        for (const actorModel of actorModels) for (const promptVariant of variants) for (let repeat = 0; repeat < repetitions; repeat++) {
            const runs = experiment.mode === 'town' ? [{ scenario: null, schedule: experiment.schedule }] : selected.map(scenario => ({ scenario }));
            for (const item of runs) tasks.push({ actorModel, promptVariant, item, specimen: manifest.specimens[specimenIndex++] });
        }
        let cursor = 0;
        const worker = async () => {
            while (cursor < tasks.length) {
                const task = tasks[cursor++], { actorModel, promptVariant, item, specimen } = task;
                if (signal && signal.aborted) throw Object.assign(new Error('run cancelled'), { code: 'ABORT_ERR' });
                const existingFile = path.join(runDir, `${specimen.id}.json`);
                if (specimen.status === 'complete' && fs.existsSync(existingFile)) { specimenOutputs.push(storage.readJson(existingFile, null)); continue; }
                specimen.status = 'running'; writeManifest(runDir, manifest); onUpdate(manifest);
                let result, townState = null;
                if (experiment.mode === 'town') {
                    const episodes = [];
                    for (let slotIndex = 0; slotIndex < item.schedule.slots.length; slotIndex++) {
                        const slot = item.schedule.slots[slotIndex], eligible = selected.filter(s => (slot.scenarioIds || []).includes(s.id) && slotAllowsScenario(slot, s, dossiers, item.schedule));
                        if (!eligible.length) continue;
                        const chosen = eligible[(parseInt(hash(`${seed}:${specimen.id}:${slotIndex}`).slice(0, 8), 16) >>> 0) % eligible.length];
                        const episode = await runEpisode({ scenario: chosen, dossiers, gateway, models: { actor: actorModel, director: experiment.directorModel, temperature: experiment.temperature, directorTemperature: experiment.directorTemperature }, promptVariant, context: { time: slot.time, location: slot.location }, seed: `${seed}:${specimen.id}:slot:${slotIndex}`, state: townState, signal, onEvent: event => { manifest.events.push({ specimenId: specimen.id, slotIndex, ...event }); onUpdate(manifest); } });
                        townState = episode.state; episodes.push({ slot: { time: slot.time, location: slot.location }, scenarioId: chosen.id, ...episode });
                    }
                    result = { mode: 'town', episodes, state: townState };
                } else result = await runEpisode({ scenario: item.scenario, dossiers, gateway, models: { actor: actorModel, director: experiment.directorModel, temperature: experiment.temperature, directorTemperature: experiment.directorTemperature }, promptVariant, seed: `${seed}:${specimen.id}`, signal, onEvent: event => { manifest.events.push({ specimenId: specimen.id, ...event }); onUpdate(manifest); } });
                specimen.status = 'complete'; specimen.scenarioId = item.scenario && item.scenario.id;
                const output = { specimenId: specimen.id, blindLabel: specimen.blindLabel, model: actorModel, result };
                specimenOutputs.push(output); storage.writeAtomic(path.join(runDir, `${specimen.id}.json`), output);
                manifest.usage = gateway.guard.snapshot(); writeManifest(runDir, manifest); onUpdate(manifest);
            }
        };
        const concurrency = Math.min(Number(experiment.concurrency || 2), tasks.length || 1);
        // Wait for every worker to settle before writing the terminal state.
        // Promise.all would reject on the first cap/cancellation error while
        // other workers were still able to write a misleading `complete`.
        const settled = await Promise.allSettled(Array.from({ length: concurrency }, () => worker()));
        const failure = settled.find(result => result.status === 'rejected');
        if (failure) throw failure.reason;
        specimenOutputs.sort((a, b) => a.specimenId.localeCompare(b.specimenId));
        manifest.state = 'complete'; writeManifest(runDir, manifest); onUpdate(manifest);
        return { manifest, specimens: specimenOutputs };
    } catch (error) {
        manifest.usage = gateway.guard.snapshot();
        manifest.error = { code: error.code || 'RUN_FAILED', message: error.message };
        const resumable = new Set(['ABORT_ERR', 'BUDGET_EXCEEDED', 'RATE_LIMIT', 'TRANSIENT_PROVIDER', 'NETWORK_ERROR']);
        manifest.state = resumable.has(error.code) ? 'partial' : 'failed';
        writeManifest(runDir, manifest); onUpdate(manifest); throw error;
    }
}

function reviewPayload(manifest, specimens) {
    return {
        id: manifest.id, state: manifest.state, revealed: !!manifest.revealed, usage: manifest.usage,
        specimens: specimens.map(specimen => ({ specimenId: specimen.specimenId, blindLabel: specimen.blindLabel, result: specimen.result,
            ...(manifest.revealed ? { model: specimen.model } : {}) })),
        ratings: manifest.ratings || [],
        ...(manifest.revealed ? { responses: manifest.responses || [] } : {}),
        ...(manifest.revealed && manifest.critic ? { critic: manifest.critic } : {}),
    };
}

function addRating(manifest, rating) {
    if (!rating || typeof rating.specimenId !== 'string' || !rating.scores || typeof rating.notes !== 'string') throw new Error('rating requires specimenId, scores, and notes');
    if (!manifest.specimens.some(specimen => specimen.id === rating.specimenId)) throw new Error(`rating names unknown specimen '${rating.specimenId}'`);
    const dimensions = ['recognizability', 'relationshipSpecificity', 'unresolvedFriction', 'generativity', 'genreDefaults', 'scopeInflation'];
    for (const dimension of dimensions) if (!Number.isInteger(rating.scores[dimension]) || rating.scores[dimension] < 1 || rating.scores[dimension] > 5) throw new Error(`rating ${dimension} must be an integer from 1 to 5`);
    if (rating.tags !== undefined && (!Array.isArray(rating.tags) || rating.tags.some(tag => !FAILURE_TAGS.includes(tag)))) throw new Error(`rating tags must be drawn from ${FAILURE_TAGS.join(', ')}`);
    manifest.ratings = (manifest.ratings || []).filter(x => x.specimenId !== rating.specimenId).concat({ ...rating, tags: rating.tags || [], createdAt: new Date().toISOString() });
}

function reveal(manifest) { if (!(manifest.ratings || []).length) throw new Error('submit at least one human rating before reveal'); manifest.revealed = true; }

async function runCritic({ manifest, specimens, gateway, model, signal }) {
    if (!(manifest.ratings || []).length) throw new Error('human ratings are required before running a critic');
    if (!model) throw new Error('criticModel is not configured for this experiment');
    const prompt = [
        'Evaluate these anonymized NPC roleplay specimens as a design critic. Do not rank them or infer their hidden model/configuration.',
        `Use the same six 1-5 dimensions as the human rubric. Tags must be chosen from: ${FAILURE_TAGS.join(', ')}. Explain observations briefly.`,
        JSON.stringify(specimens.map(s => ({ specimenId: s.specimenId, blindLabel: s.blindLabel, result: s.result })), null, 2),
    ].join('\n\n');
    const modelSpec = typeof model === 'string' ? { model } : { ...(model || {}) };
    const reply = await gateway.call({ role: 'critic', ...modelSpec, responseFormat: CRITIC_SCHEMA, signal,
        messages: [{ role: 'system', content: 'You are a post-hoc design critic. Return only valid JSON.' }, { role: 'user', content: prompt }] });
    const annotations = reply.value && reply.value.annotations;
    if (!Array.isArray(annotations)) throw new Error('critic returned no annotations');
    const ids = new Set(specimens.map(x => x.specimenId));
    annotations.forEach(annotation => { if (!ids.has(annotation.specimenId)) throw new Error(`critic named unknown specimen '${annotation.specimenId}'`); if (annotation.tags.some(tag => !FAILURE_TAGS.includes(tag))) throw new Error(`critic used unknown failure tag '${annotation.tags.find(tag => !FAILURE_TAGS.includes(tag))}'`); });
    return { createdAt: new Date().toISOString(), model: reply.model, annotations };
}

function preserve({ projectRoot, runDir, manifest, specimens, findingNotes = '', selectedSpecimenIds = [] }) {
    const available = new Set(specimens.map(x => x.specimenId));
    const requested = selectedSpecimenIds.length ? selectedSpecimenIds : specimens.map(x => x.specimenId);
    if (requested.some(id => !available.has(id))) throw new Error('preserve selection names an unknown specimen');
    const selected = new Set(requested);
    for (const specimen of specimens.filter(x => selected.has(x.specimenId))) {
        if (!fs.existsSync(path.join(runDir, `${specimen.specimenId}.json`))) throw new Error(`cannot preserve specimen '${specimen.specimenId}' before it has a transcript`);
    }
    const destination = path.join(storage.researchRoot(projectRoot), 'preserved', `${manifest.id}-${Date.now()}`);
    storage.ensureDir(destination);
    const preserved = { contractVersion: 1, id: manifest.id, preservedAt: new Date().toISOString(), findingNotes, selectedSpecimenIds: [...selected], runManifest: manifest };
    validatePreservedExperiment(preserved);
    storage.writeAtomic(path.join(destination, 'experiment.json'), preserved);
    for (const specimen of specimens.filter(x => selected.has(x.specimenId))) {
        const file = path.join(runDir, `${specimen.specimenId}.json`); fs.copyFileSync(file, path.join(destination, path.basename(file)));
    }
    return destination;
}

module.exports = { CRITIC_SCHEMA, FAILURE_TAGS, safeId, randomizeLabels, expectedCalls, validateExperiment, createManifest, runExperiment,
    reviewPayload, addRating, reveal, runCritic, preserve };
