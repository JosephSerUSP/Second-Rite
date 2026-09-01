'use strict';

const crypto = require('crypto');
const { extractJson } = require('../../shared/llm');
const { validateDossier, validateScenarioCard, normalizeParticipants } = require('./schemas');

const ACTOR_SCHEMA = {
    type: 'json_schema', json_schema: { name: 'npc_action', strict: true, schema: {
        type: 'object', additionalProperties: false,
        properties: {
            action: { type: 'string', enum: ['speak', 'ask', 'offer', 'refuse', 'observe', 'leave'] },
            speech: { type: 'string' }, target: { type: ['string', 'null'] },
        }, required: ['action', 'speech', 'target'],
    } },
};
const DIRECTOR_SCHEMA = {
    type: 'json_schema', json_schema: { name: 'episode_resolution', strict: true, schema: {
        type: 'object', additionalProperties: false,
        properties: {
            continue: { type: 'boolean' }, nextSpeaker: { type: ['string', 'null'] }, terminationReason: { type: ['string', 'null'] },
            publicFacts: { type: 'array', items: { type: 'object', additionalProperties: false, properties: {
                text: { type: 'string' }, salience: { type: 'integer', minimum: 1, maximum: 5 }, participants: { type: 'array', items: { type: 'string' } },
            }, required: ['text', 'salience', 'participants'] } },
            privateFacts: { type: 'array', items: { type: 'object', additionalProperties: false, properties: {
                to: { type: 'string' }, text: { type: 'string' }, salience: { type: 'integer', minimum: 1, maximum: 5 },
            }, required: ['to', 'text', 'salience'] } },
            relationshipUpdates: { type: 'array', items: { type: 'object', additionalProperties: false, properties: {
                from: { type: 'string' }, to: { type: 'string' }, dimension: { type: 'string' }, delta: { type: 'integer', minimum: -1, maximum: 1 }, evidence: { type: 'string' },
            }, required: ['from', 'to', 'dimension', 'delta', 'evidence'] } },
        }, required: ['continue', 'nextSpeaker', 'terminationReason', 'publicFacts', 'privateFacts', 'relationshipUpdates'],
    } },
};

function hash(value) { return crypto.createHash('sha256').update(String(value)).digest('hex'); }
function seedNumber(seed) { return parseInt(hash(seed).slice(0, 8), 16) >>> 0; }
function random(seed) { let x = seedNumber(seed) || 1; return () => { x = (1664525 * x + 1013904223) >>> 0; return x / 0x100000000; }; }
function clip(text, max = 4000) { return String(text || '').slice(0, max); }
function modelSpec(value, fallbackTemperature) {
    if (typeof value === 'string') return { model: value, temperature: fallbackTemperature };
    return { temperature: fallbackTemperature, ...(value || {}) };
}

function dossierFor(id, dossiers, scenarioParticipant) {
    if (scenarioParticipant && scenarioParticipant.type === 'playerProxy') {
        return { contractVersion: 1, id, displayName: scenarioParticipant.displayName || 'Player Proxy', facts: [], privateKnowledge: scenarioParticipant.privateKnowledge || [], goals: scenarioParticipant.goals || [], behavioralTensions: [], relationships: {}, routines: [] };
    }
    const dossier = dossiers[id]; if (!dossier) throw new Error(`missing dossier for participant '${id}'`);
    return validateDossier(dossier, `dossiers.${id}`);
}

function relationshipDimensions(dossier, target) {
    const rel = dossier.relationships && dossier.relationships[target];
    return new Map((rel && rel.dimensions || []).map(d => [d.key, d]));
}

function initialState(participants, dossiers, scenarioParticipants) {
    const state = { publicFacts: [], privateFacts: {}, memories: {}, relationships: {}, events: [], turn: 0 };
    Object.defineProperty(state, '_episodeRelationshipDeltas', { value: {}, enumerable: false, writable: true });
    for (const participant of participants) {
        state.memories[participant.id] = [];
        state.privateFacts[participant.id] = [];
        state.relationships[participant.id] = {};
        const dossier = dossierFor(participant.id, dossiers, scenarioParticipants.find(x => x.id === participant.id));
        for (const [target, rel] of Object.entries(dossier.relationships || {})) {
            state.relationships[participant.id][target] = {};
            for (const dimension of rel.dimensions || []) state.relationships[participant.id][target][dimension.key] = dimension.initial ?? 0;
        }
    }
    return state;
}

function ensureStateParticipants(state, participants, dossiers, scenarioParticipants) {
    state.publicFacts ||= []; state.privateFacts ||= {}; state.memories ||= {}; state.relationships ||= {}; state.events ||= []; state.turn = Number.isInteger(state.turn) ? state.turn : 0;
    for (const participant of participants) {
        state.privateFacts[participant.id] ||= [];
        state.memories[participant.id] ||= [];
        state.relationships[participant.id] ||= {};
        const dossier = dossierFor(participant.id, dossiers, scenarioParticipants.find(x => x.id === participant.id));
        for (const [target, rel] of Object.entries(dossier.relationships || {})) {
            state.relationships[participant.id][target] ||= {};
            for (const dimension of rel.dimensions || []) if (state.relationships[participant.id][target][dimension.key] === undefined) state.relationships[participant.id][target][dimension.key] = dimension.initial ?? 0;
        }
    }
    return state;
}

function validateDirectorResolution(resolution, participants) {
    if (!resolution || typeof resolution !== 'object' || Array.isArray(resolution)) throw new Error('director returned no resolution object');
    if (typeof resolution.continue !== 'boolean') throw new Error('director resolution.continue must be boolean');
    if (resolution.nextSpeaker !== null && typeof resolution.nextSpeaker !== 'string') throw new Error('director resolution.nextSpeaker must be a participant id or null');
    if (resolution.terminationReason !== null && typeof resolution.terminationReason !== 'string') throw new Error('director resolution.terminationReason must be a string or null');
    if (!resolution.continue && (!resolution.terminationReason || !resolution.terminationReason.trim())) throw new Error('director must provide a terminationReason when continue is false');
    if (!Array.isArray(resolution.publicFacts) || !Array.isArray(resolution.privateFacts) || !Array.isArray(resolution.relationshipUpdates)) throw new Error('director resolution fact and relationship fields must be arrays');
    const ids = new Set(participants.map(x => x.id));
    resolution.publicFacts.forEach((fact, i) => {
        if (!fact || typeof fact !== 'object' || typeof fact.text !== 'string' || !fact.text.trim() || fact.text.length > 2000) throw new Error(`director public fact ${i} is invalid`);
        if (!Number.isInteger(fact.salience) || fact.salience < 1 || fact.salience > 5) throw new Error(`director public fact ${i} salience must be 1..5`);
        if (!Array.isArray(fact.participants) || fact.participants.some(x => !ids.has(x))) throw new Error(`director public fact ${i} names an unknown participant`);
    });
    resolution.privateFacts.forEach((fact, i) => {
        if (!fact || typeof fact !== 'object' || !ids.has(fact.to) || typeof fact.text !== 'string' || !fact.text.trim() || fact.text.length > 2000 || !Number.isInteger(fact.salience) || fact.salience < 1 || fact.salience > 5) throw new Error(`director private fact ${i} is invalid`);
    });
    resolution.relationshipUpdates.forEach((update, i) => {
        if (!update || typeof update !== 'object' || !ids.has(update.from) || !ids.has(update.to) || update.from === update.to || typeof update.dimension !== 'string' || !Number.isInteger(update.delta) || update.delta < -1 || update.delta > 1 || typeof update.evidence !== 'string') throw new Error(`director relationship update ${i} is invalid`);
    });
    return resolution;
}

function selectMemories(memories, actorId, involvedIds = [], limit = 8) {
    return (memories[actorId] || []).map((memory, index) => ({ ...memory,
        score: (memory.salience || 1) * 10 + index + (memory.participants || []).filter(x => involvedIds.includes(x)).length * 7,
    })).sort((a, b) => b.score - a.score).slice(0, limit).map(({ score, ...memory }) => memory);
}

function relationText(state, actorId) {
    return Object.entries(state.relationships[actorId] || {}).map(([target, dimensions]) => `${target}: ${Object.entries(dimensions).map(([key, value]) => `${key}=${value}`).join(', ')}`).join('\n') || '(none)';
}

function actorPrompt({ actor, dossier, scenario, state, transcript, participants, promptVariant, context = {} }) {
    const visible = state.publicFacts.map(x => `- ${x.text}`).join('\n') || '(none)';
    const privateFacts = state.privateFacts[actor.id].map(x => `- ${x.text}`).join('\n') || '(none)';
    const memories = selectMemories(state.memories, actor.id, participants.map(x => x.id)).map(x => `- ${x.text}`).join('\n') || '(none)';
    const canon = dossier.canon || {};
    const relationshipCanon = dossier.relationshipCanon || {};
    const canonLines = [
        canon.core && `Core personality: ${canon.core}`, canon.voice && `Voice: ${canon.voice}`,
        canon.wants && `Wants: ${canon.wants}`, canon.fears && `Fears: ${canon.fears}`,
        canon.defenses && `Defenses: ${canon.defenses}`, canon.contradictions && `Contradictions: ${canon.contradictions}`,
        canon.boundaries && `Canon boundaries: ${canon.boundaries}`,
        canon.tags && canon.tags.length && `Tags: ${canon.tags.join(', ')}`,
        canon.references && canon.references.length && `Character references: ${canon.references.join(', ')}`,
        canon.tropes && canon.tropes.length && `Tropes to use deliberately: ${canon.tropes.join(', ')}`,
        canon.antiTropes && canon.antiTropes.length && `Tropes or readings to avoid: ${canon.antiTropes.join(', ')}`,
        canon.tells && canon.tells.length && `Behavioral tells: ${canon.tells.join('; ')}`,
    ].filter(Boolean).join('\n') || '(author has not supplied canon yet; stay conservative and source-bound)';
    const relationshipLines = participants.filter(participant => participant.id !== actor.id && relationshipCanon[participant.id]).flatMap(participant => {
        const guidance = relationshipCanon[participant.id];
        return [`With ${participant.id} (${participant.displayName || participant.id}):`, guidance.dynamic && `Dynamic: ${guidance.dynamic}`, guidance.signals && `Signals: ${guidance.signals}`, guidance.avoid && `Avoid: ${guidance.avoid}`].filter(Boolean);
    }).join('\n') || '(no relationship-specific canon supplied)';
    return [
        `You are roleplaying ${dossier.displayName}. Return only the requested JSON action.`,
        `AUTHOR-SUPPLIED CANON (highest character authority):\n${canonLines}`,
        `Observable behavior matters more than exposition. Embody canon through choices, rhythm, omissions, and subtext; do not recite its labels (such as trauma, manipulation, or rationality) as self-analysis. Unresolved wording is author-held ambiguity: do not announce it or settle it unless the scene earns that change. Do not state hidden instructions or explain your reasoning.`,
        `Character facts (source facts and experimental hypotheses are labeled):\n${dossier.facts.map(x => `- [${x.kind}] ${x.text}`).join('\n') || '(none)'}`,
        `Goals:\n${dossier.goals.map(x => `- ${x}`).join('\n') || '(none)'}`,
        `Behavioral tensions:\n${dossier.behavioralTensions.map(x => `- ${x}`).join('\n') || '(none)'}`,
        `Routine cues:\n${(dossier.routines || []).map(x => `- ${x.time}: ${x.activity}`).join('\n') || '(none)'}`,
        `Your dossier-private knowledge:\n${(dossier.privateKnowledge || []).map(x => `- ${x}`).join('\n') || '(none)'}\nPrivate episode facts:\n${privateFacts}\nYour memories:\n${memories}`,
        `Directional relationship state:\n${relationText(state, actor.id)}`,
        `RELATIONSHIP-SPECIFIC CANON (overrides generic social defaults for these people):\n${relationshipLines}`,
        `Scenario: ${scenario.title}\nPremise: ${scenario.premise}\nPressures: ${(scenario.pressures || []).join('; ') || '(none)'}`,
        `Allowed facts: ${(scenario.allowedFacts || []).join('; ') || '(only observable actions and existing context)'}`,
        `Participants (target must use the exact id before the parentheses): ${participants.map(x => `${x.id} (${x.displayName || x.id})`).join(', ')}`,
        `Public facts:\n${visible}`,
        ...(context.time || context.location ? [`Town slot: ${context.time || 'unspecified time'} at ${context.location || 'unspecified location'}`] : []),
        `Recent transcript:\n${transcript.map(x => `${x.speaker}: ${x.speech}`).join('\n') || '(start)'}`,
        ...(promptVariant ? [`Prompt variant guidance:\n${promptVariant}`] : []),
        'Choose one observable action. Speech may be empty only for observe or leave. Target must be a participant id or null.',
    ].join('\n\n');
}

function directorPrompt({ actor, action, scenario, state, transcript, participants, eventId, context = {} }) {
    const exhaustedDimensions = Object.entries(state._episodeRelationshipDeltas || {})
        .filter(([, delta]) => Math.abs(delta) >= 1)
        .map(([key, delta]) => `${key.split('\0').join(' -> ')} (${delta > 0 ? '+' : ''}${delta})`);
    return [
        'You are the neutral episode director. Resolve one observable action into plausible facts.',
        'Return only the requested JSON. Do not add facts outside the scenario constraints. Only your resolved updates become state.',
        `Event id: ${eventId}\nScenario: ${scenario.title}\nPremise: ${scenario.premise}\nThe scene must last at least ${scenario.minTurns} turns and no more than ${scenario.maxTurns}.\nConstraints: ${(scenario.constraints || []).join('; ') || '(none)'}`,
        `Allowed facts: ${(scenario.allowedFacts || []).join('; ') || '(only observable actions and existing context)'}`,
        `Acting participant: ${actor.id}\nAction: ${JSON.stringify(action)}`,
        ...(context.time || context.location ? [`Town slot: ${context.time || 'unspecified time'} at ${context.location || 'unspecified location'}`] : []),
        `Participants: ${participants.map(x => x.id).join(', ')}`,
        `Public facts so far:\n${state.publicFacts.map(x => `- ${x.id}: ${x.text}`).join('\n') || '(none)'}`,
        `Transcript:\n${transcript.map(x => `${x.speaker}: ${x.speech}`).join('\n') || '(none)'}`,
        `Relationship state:\n${participants.map(x => `${x.id}: ${relationText(state, x.id)}`).join('\n')}`,
        `Relationship dimensions already changed this episode and unavailable for another update:\n${exhaustedDimensions.join('\n') || '(none)'}`,
        'Every relationship update must reference this event id as evidence, use an existing declared dimension, and change one direction by at most one point.',
        'Do not emit another update for any unavailable dimension; an empty relationshipUpdates array is valid.',
    ].join('\n\n');
}

function validateAction(action, participants) {
    if (!action || !['speak', 'ask', 'offer', 'refuse', 'observe', 'leave'].includes(action.action)) throw new Error('actor returned an invalid action');
    if (typeof action.speech !== 'string' || action.speech.length > 2000) throw new Error('actor speech must be a string of at most 2000 characters');
    if (action.target !== null && !participants.some(x => x.id === action.target)) throw new Error(`actor targeted unknown participant '${action.target}'`);
    return action;
}

function applyResolution(resolution, state, participants, dossiers, eventId, scenario, actingParticipantId = null) {
    validateDirectorResolution(resolution, participants);
    if (!state._episodeRelationshipDeltas) Object.defineProperty(state, '_episodeRelationshipDeltas', { value: {}, enumerable: false, writable: true });
    const participantIds = new Set(participants.map(x => x.id));
    for (const fact of resolution.publicFacts || []) {
        if (!fact.text || fact.text.length > 2000) throw new Error('director public fact is invalid');
        if ((fact.participants || []).some(x => !participantIds.has(x))) throw new Error('director public fact names an unknown participant');
        const record = { id: `${eventId}.public.${state.publicFacts.length}`, text: fact.text, salience: fact.salience, participants: fact.participants || [], eventId };
        state.publicFacts.push(record);
        for (const participant of participants) state.memories[participant.id].push(record);
    }
    for (const fact of resolution.privateFacts || []) {
        if (!participantIds.has(fact.to) || !fact.text || fact.text.length > 2000) throw new Error('director private fact is invalid');
        const record = { id: `${eventId}.private.${state.privateFacts[fact.to].length}`, text: fact.text, salience: fact.salience, participants: [fact.to], eventId };
        state.privateFacts[fact.to].push(record); state.memories[fact.to].push(record);
    }
    for (const update of resolution.relationshipUpdates || []) {
        if (!participantIds.has(update.from) || !participantIds.has(update.to) || update.from === update.to) throw new Error('director relationship update has invalid participants');
        if (!Number.isInteger(update.delta) || update.delta < -1 || update.delta > 1 || update.evidence !== eventId) throw new Error('director relationship update is not bounded or lacks event evidence');
        const source = dossierFor(update.from, dossiers, participants.find(x => x.id === update.from));
        const dimensions = relationshipDimensions(source, update.to);
        if (!dimensions.has(update.dimension)) throw new Error(`director used undeclared relationship dimension '${update.dimension}'`);
        const deltaKey = `${update.from}\0${update.to}\0${update.dimension}`;
        const episodeDelta = (state._episodeRelationshipDeltas[deltaKey] || 0) + update.delta;
        if (episodeDelta < -1 || episodeDelta > 1) throw new Error(`director relationship change exceeds the per-episode bound for '${update.dimension}'`);
        state._episodeRelationshipDeltas[deltaKey] = episodeDelta;
        state.relationships[update.from] ||= {}; state.relationships[update.from][update.to] ||= {};
        const prior = state.relationships[update.from][update.to][update.dimension] ?? dimensions.get(update.dimension).initial ?? 0;
        state.relationships[update.from][update.to][update.dimension] = Math.max(-5, Math.min(5, prior + update.delta));
    }
    if (resolution.nextSpeaker !== null && !participantIds.has(resolution.nextSpeaker)) throw new Error('director selected an unknown next speaker');
    if (state.turn + 1 < scenario.minTurns) {
        resolution.continue = true;
        resolution.terminationReason = null;
        if (resolution.nextSpeaker === null) {
            const current = participants.findIndex(participant => participant.id === actingParticipantId);
            resolution.nextSpeaker = participants[(Math.max(current, 0) + 1) % participants.length].id;
        }
    }
    if (resolution.continue && state.turn >= scenario.maxTurns) resolution.continue = false;
    return resolution;
}

async function runEpisode({ scenario: rawScenario, dossiers = {}, gateway, models, seed = 'default', state: providedState, signal, onEvent = () => {}, promptVariant = '', context = {} }) {
    const scenario = validateScenarioCard(rawScenario);
    const participants = normalizeParticipants(scenario.participants);
    const state = providedState || initialState(participants, dossiers, participants);
    ensureStateParticipants(state, participants, dossiers, participants);
    if (!state._episodeRelationshipDeltas) Object.defineProperty(state, '_episodeRelationshipDeltas', { value: {}, enumerable: false, writable: true });
    else state._episodeRelationshipDeltas = {};
    const transcript = [];
    let speakerIndex = 0, resolution = null;
    for (let turn = 0; turn < scenario.maxTurns; turn++) {
        state.turn = turn;
        const actor = participants.find(x => x.id === (resolution && resolution.nextSpeaker)) || participants[speakerIndex % participants.length];
        const dossier = dossierFor(actor.id, dossiers, actor);
        const actorModel = modelSpec(models.actor, models.temperature ?? 0.8);
        const actionReply = await gateway.call({ role: 'actor', ...actorModel, messages: [
            { role: 'system', content: 'You are an NPC actor in a bounded social simulation. Return only valid JSON matching the schema.' },
            { role: 'user', content: actorPrompt({ actor, dossier, scenario, state, transcript, participants, promptVariant, context }) },
        ], responseFormat: ACTOR_SCHEMA, signal, seed: `${seed}:actor:${turn}` });
        const action = validateAction(actionReply.value, participants);
        const transcriptEvent = { id: `${seed}.turn.${turn}`, speaker: actor.id, action: action.action, speech: clip(action.speech), target: action.target };
        transcript.push(transcriptEvent); onEvent({ type: 'actor', event: transcriptEvent });
        const directorModel = modelSpec(models.director, models.directorTemperature ?? 0.2);
        const directorReply = await gateway.call({ role: 'director', ...directorModel, messages: [
            { role: 'system', content: 'You are a neutral simulation director. Return only valid JSON matching the schema.' },
            { role: 'user', content: directorPrompt({ actor, action, scenario, state, transcript, participants, eventId: transcriptEvent.id, context }) },
        ], responseFormat: DIRECTOR_SCHEMA, signal, seed: `${seed}:director:${turn}` });
        resolution = applyResolution(directorReply.value, state, participants, dossiers, transcriptEvent.id, scenario, actor.id);
        state.events.push({ ...transcriptEvent, resolution });
        onEvent({ type: 'resolution', event: { id: transcriptEvent.id, resolution } });
        speakerIndex = resolution.nextSpeaker ? participants.findIndex(x => x.id === resolution.nextSpeaker) : speakerIndex + 1;
        // The director, not an actor shortcut, owns episode termination.  A
        // `leave` action is still observable input that the director may
        // resolve as either departure or an unresolved continuation.
        if (!resolution.continue) break;
    }
    return { scenarioId: scenario.id, transcript, state, ended: true };
}

function parseReply(content) {
    const value = typeof content === 'object' ? content : extractJson(content);
    return value;
}

module.exports = { ACTOR_SCHEMA, DIRECTOR_SCHEMA, hash, random, selectMemories, initialState,
    actorPrompt, directorPrompt, validateAction, validateDirectorResolution, applyResolution, runEpisode, parseReply };
