'use strict';

const ID = /^[a-z0-9][a-z0-9_-]{0,63}$/;
const RUN_STATES = new Set(['queued', 'running', 'cancelling', 'partial', 'complete', 'failed']);
const MODES = new Set(['scene', 'town']);

function fail(path, message) { throw new Error(`${path}: ${message}`); }
function object(value, path) { if (!value || typeof value !== 'object' || Array.isArray(value)) fail(path, 'must be an object'); return value; }
function array(value, path) { if (!Array.isArray(value)) fail(path, 'must be an array'); return value; }
function string(value, path) { if (typeof value !== 'string' || !value.trim()) fail(path, 'must be a non-empty string'); return value; }
function id(value, path) { string(value, path); if (!ID.test(value)) fail(path, 'must match [a-z0-9][a-z0-9_-]{0,63}'); return value; }
function integer(value, path, min, max) { if (!Number.isInteger(value) || value < min || value > max) fail(path, `must be an integer from ${min} to ${max}`); return value; }

function contract(value, path, expected = 1) {
    object(value, path);
    if (value.contractVersion !== expected) fail(`${path}.contractVersion`, `must be ${expected}`);
}

function validateDossier(value, path = 'dossier') {
    contract(value, path); id(value.id, `${path}.id`); string(value.displayName, `${path}.displayName`);
    array(value.facts || [], `${path}.facts`).forEach((fact, i) => {
        object(fact, `${path}.facts[${i}]`); if (!['source', 'hypothesis'].includes(fact.kind)) fail(`${path}.facts[${i}].kind`, 'must be source or hypothesis');
        string(fact.text, `${path}.facts[${i}].text`);
        if (fact.kind === 'source') array(fact.sourceRefs || [], `${path}.facts[${i}].sourceRefs`).forEach((ref, j) => validateSourceRef(ref, `${path}.facts[${i}].sourceRefs[${j}]`));
    });
    if (value.sourceRefs !== undefined) array(value.sourceRefs, `${path}.sourceRefs`).forEach((ref, i) => validateSourceRef(ref, `${path}.sourceRefs[${i}]`));
    array(value.privateKnowledge || [], `${path}.privateKnowledge`).forEach((x, i) => string(x, `${path}.privateKnowledge[${i}]`));
    array(value.goals || [], `${path}.goals`).forEach((x, i) => string(x, `${path}.goals[${i}]`));
    array(value.behavioralTensions || [], `${path}.behavioralTensions`).forEach((x, i) => string(x, `${path}.behavioralTensions[${i}]`));
    object(value.relationships || {}, `${path}.relationships`);
    for (const [target, rel] of Object.entries(value.relationships || {})) {
        id(target, `${path}.relationships.${target}`); object(rel, `${path}.relationships.${target}`);
        const dimensions = array(rel.dimensions || [], `${path}.relationships.${target}.dimensions`), keys = new Set();
        dimensions.forEach((dimension, i) => {
            object(dimension, `${path}.relationships.${target}.dimensions[${i}]`); id(dimension.key, `${path}.relationships.${target}.dimensions[${i}].key`);
            integer(dimension.initial ?? 0, `${path}.relationships.${target}.dimensions[${i}].initial`, -5, 5);
            if (keys.has(dimension.key)) fail(`${path}.relationships.${target}.dimensions`, 'dimension keys must be unique'); keys.add(dimension.key);
        });
    }
    array(value.routines || [], `${path}.routines`).forEach((routine, i) => {
        object(routine, `${path}.routines[${i}]`); string(routine.time, `${path}.routines[${i}].time`); string(routine.activity, `${path}.routines[${i}].activity`);
    });
    return { ...value, facts: value.facts || [], privateKnowledge: value.privateKnowledge || [], goals: value.goals || [], behavioralTensions: value.behavioralTensions || [], relationships: value.relationships || {}, routines: value.routines || [] };
}

function validateSourceRef(value, path) {
    object(value, path); string(value.path, `${path}.path`); string(value.sha256, `${path}.sha256`);
    if (/^[\\/]|(^|[\\/])\.\.([\\/]|$)/.test(value.path)) fail(`${path}.path`, 'must be a relative Project path');
    if (!/^[a-f0-9]{64}$/.test(value.sha256)) fail(`${path}.sha256`, 'must be a lowercase SHA-256');
    if (value.pointer !== undefined) string(value.pointer, `${path}.pointer`);
    return value;
}

function normalizeParticipants(value, path = 'participants') {
    return array(value, path).map((participant, i) => {
        if (typeof participant === 'string') return { id: id(participant, `${path}[${i}]`), type: 'npc' };
        object(participant, `${path}[${i}]`); id(participant.id, `${path}[${i}].id`);
        if (participant.type !== undefined && !['npc', 'playerProxy'].includes(participant.type)) fail(`${path}[${i}].type`, 'must be npc or playerProxy');
        if (participant.displayName !== undefined && participant.displayName !== null) string(participant.displayName, `${path}[${i}].displayName`);
        for (const key of ['goals', 'privateKnowledge']) if (participant[key] !== undefined) array(participant[key], `${path}[${i}].${key}`).forEach((item, j) => string(item, `${path}[${i}].${key}[${j}]`));
        return { ...participant, type: participant.type || 'npc' };
    });
}

function validateScenarioCard(value, path = 'scenario') {
    contract(value, path); id(value.id, `${path}.id`); string(value.title, `${path}.title`); string(value.premise, `${path}.premise`);
    const participants = normalizeParticipants(value.participants, `${path}.participants`);
    if (participants.length < 2 || participants.length > 3) fail(`${path}.participants`, 'must contain two or three participants');
    if (new Set(participants.map(x => x.id)).size !== participants.length) fail(`${path}.participants`, 'participant ids must be unique');
    integer(value.maxTurns ?? 8, `${path}.maxTurns`, 1, 50);
    array(value.pressures || [], `${path}.pressures`).forEach((x, i) => string(x, `${path}.pressures[${i}]`));
    array(value.constraints || [], `${path}.constraints`).forEach((x, i) => string(x, `${path}.constraints[${i}]`));
    array(value.allowedFacts || [], `${path}.allowedFacts`).forEach((x, i) => string(x, `${path}.allowedFacts[${i}]`));
    return { ...value, participants, maxTurns: value.maxTurns ?? 8, pressures: value.pressures || [], constraints: value.constraints || [], allowedFacts: value.allowedFacts || [] };
}

function validateTownSchedule(value, path = 'townSchedule') {
    contract(value, path); id(value.id, `${path}.id`); string(value.title, `${path}.title`);
    array(value.slots, `${path}.slots`).forEach((slot, i) => {
        object(slot, `${path}.slots[${i}]`); string(slot.time, `${path}.slots[${i}].time`); string(slot.location, `${path}.slots[${i}].location`);
        const scenarioIds = array(slot.scenarioIds, `${path}.slots[${i}].scenarioIds`);
        scenarioIds.forEach((x, j) => id(x, `${path}.slots[${i}].scenarioIds[${j}]`));
        if (new Set(scenarioIds).size !== scenarioIds.length) fail(`${path}.slots[${i}].scenarioIds`, 'must not contain duplicates');
        const available = slot.availableParticipantIds || slot.availableParticipants;
        if (available !== undefined) array(available, `${path}.slots[${i}].availableParticipantIds`).forEach((x, j) => id(x, `${path}.slots[${i}].availableParticipantIds[${j}]`));
        if (slot.eligibleScenarioIds !== undefined) array(slot.eligibleScenarioIds, `${path}.slots[${i}].eligibleScenarioIds`).forEach((x, j) => id(x, `${path}.slots[${i}].eligibleScenarioIds[${j}]`));
        if (slot.notes !== undefined) string(slot.notes, `${path}.slots[${i}].notes`);
    });
    if (value.routines !== undefined) {
        object(value.routines, `${path}.routines`);
        for (const [participant, routines] of Object.entries(value.routines)) {
            id(participant, `${path}.routines.${participant}`); array(routines, `${path}.routines.${participant}`).forEach((routine, i) => {
                object(routine, `${path}.routines.${participant}[${i}]`); string(routine.time, `${path}.routines.${participant}[${i}].time`); string(routine.activity, `${path}.routines.${participant}[${i}].activity`);
            });
        }
    }
    if (value.availability !== undefined) {
        object(value.availability, `${path}.availability`);
        for (const [participant, slots] of Object.entries(value.availability)) {
            id(participant, `${path}.availability.${participant}`); array(slots, `${path}.availability.${participant}`).forEach((x, i) => string(x, `${path}.availability.${participant}[${i}]`));
        }
    }
    return value;
}

function validateRunManifest(value, path = 'runManifest') {
    contract(value, path); id(value.id, `${path}.id`); if (!MODES.has(value.mode)) fail(`${path}.mode`, 'must be scene or town');
    if (!RUN_STATES.has(value.state)) fail(`${path}.state`, 'unknown run state');
    array(value.specimens || [], `${path}.specimens`).forEach((specimen, i) => {
        object(specimen, `${path}.specimens[${i}]`); id(specimen.id, `${path}.specimens[${i}].id`); string(specimen.blindLabel, `${path}.specimens[${i}].blindLabel`);
        if (specimen.status !== undefined && !['queued', 'running', 'partial', 'complete', 'failed'].includes(specimen.status)) fail(`${path}.specimens[${i}].status`, 'unknown specimen state');
    });
    const ids = (value.specimens || []).map(x => x.id), labels = (value.specimens || []).map(x => x.blindLabel);
    if (new Set(ids).size !== ids.length) fail(`${path}.specimens`, 'specimen ids must be unique');
    if (new Set(labels).size !== labels.length) fail(`${path}.specimens`, 'blind labels must be unique');
    if (value.modelPolicy !== undefined) array(value.modelPolicy, `${path}.modelPolicy`).forEach((decision, i) => validateModelPolicyDecision(decision, `${path}.modelPolicy[${i}]`));
    if (value.sourceHashes !== undefined) {
        object(value.sourceHashes, `${path}.sourceHashes`);
        for (const [key, digest] of Object.entries(value.sourceHashes)) {
            string(key, `${path}.sourceHashes key`);
            if (typeof digest !== 'string' || !/^[a-f0-9]{64}$/.test(digest)) fail(`${path}.sourceHashes.${key}`, 'must be a lowercase SHA-256');
        }
    }
    if (value.usage !== undefined) {
        object(value.usage, `${path}.usage`);
        for (const key of ['calls', 'tokens', 'usd']) if (value.usage[key] !== undefined && (!Number.isFinite(Number(value.usage[key])) || Number(value.usage[key]) < 0)) fail(`${path}.usage.${key}`, 'must be a non-negative number');
    }
    return value;
}

function validateModelPolicyDecision(value, path = 'modelPolicyDecision') {
    contract(value, path); string(value.provider, `${path}.provider`); string(value.requestedModel, `${path}.requestedModel`);
    if (!['openai', 'openrouter'].includes(value.provider.toLowerCase())) fail(`${path}.provider`, 'must be openai or openrouter');
    if (typeof value.allowed !== 'boolean') fail(`${path}.allowed`, 'must be boolean'); string(value.reason, `${path}.reason`); string(value.catalogueAt, `${path}.catalogueAt`);
    if (!Object.prototype.hasOwnProperty.call(value, 'resolvedModel')) fail(`${path}.resolvedModel`, 'is required');
    if (value.resolvedModel !== null && value.resolvedModel !== undefined) string(value.resolvedModel, `${path}.resolvedModel`);
    if (value.freePriceEvidence !== null && value.freePriceEvidence !== undefined) object(value.freePriceEvidence, `${path}.freePriceEvidence`);
    return value;
}

function validatePreservedExperiment(value, path = 'preservedExperiment') {
    contract(value, path); id(value.id, `${path}.id`); string(value.preservedAt, `${path}.preservedAt`);
    if (value.findingNotes !== undefined && typeof value.findingNotes !== 'string') fail(`${path}.findingNotes`, 'must be a string');
    array(value.selectedSpecimenIds, `${path}.selectedSpecimenIds`).forEach((specimenId, i) => id(specimenId, `${path}.selectedSpecimenIds[${i}]`));
    validateRunManifest(value.runManifest, `${path}.runManifest`);
    return value;
}

module.exports = { ID, RUN_STATES, MODES, validateDossier, validateSourceRef, validateScenarioCard,
    validateTownSchedule, validateRunManifest, validateModelPolicyDecision, validatePreservedExperiment, normalizeParticipants };
