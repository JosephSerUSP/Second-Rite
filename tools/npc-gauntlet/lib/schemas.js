'use strict';

const ID = /^[a-z0-9][a-z0-9_-]{0,63}$/;
const RUN_STATES = new Set(['queued', 'running', 'cancelling', 'partial', 'complete', 'failed']);
const MODES = new Set(['scene', 'town', 'living-town']);

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
    if (value.canon !== undefined) {
        object(value.canon, `${path}.canon`);
        for (const key of ['core', 'voice', 'wants', 'fears', 'defenses', 'contradictions', 'boundaries']) {
            if (value.canon[key] !== undefined) string(value.canon[key], `${path}.canon.${key}`);
        }
        for (const key of ['tags', 'references', 'tropes', 'antiTropes', 'tells']) {
            if (value.canon[key] !== undefined) array(value.canon[key], `${path}.canon.${key}`).forEach((x, i) => string(x, `${path}.canon.${key}[${i}]`));
        }
    }
    if (value.relationshipCanon !== undefined) {
        object(value.relationshipCanon, `${path}.relationshipCanon`);
        for (const [target, guidance] of Object.entries(value.relationshipCanon)) {
            id(target, `${path}.relationshipCanon.${target}`); object(guidance, `${path}.relationshipCanon.${target}`);
            for (const key of ['dynamic', 'signals', 'avoid']) if (guidance[key] !== undefined) string(guidance[key], `${path}.relationshipCanon.${target}.${key}`);
        }
    }
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
    const maxTurns = integer(value.maxTurns ?? 8, `${path}.maxTurns`, 1, 50);
    const minTurns = integer(value.minTurns ?? 1, `${path}.minTurns`, 1, maxTurns);
    array(value.pressures || [], `${path}.pressures`).forEach((x, i) => string(x, `${path}.pressures[${i}]`));
    array(value.constraints || [], `${path}.constraints`).forEach((x, i) => string(x, `${path}.constraints[${i}]`));
    array(value.allowedFacts || [], `${path}.allowedFacts`).forEach((x, i) => string(x, `${path}.allowedFacts[${i}]`));
    return { ...value, participants, minTurns, maxTurns, pressures: value.pressures || [], constraints: value.constraints || [], allowedFacts: value.allowedFacts || [] };
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

function validateLivingTown(value, path = 'livingTown') {
    contract(value, path); id(value.id, `${path}.id`); string(value.title, `${path}.title`);
    const blocks = array(value.timeBlocks, `${path}.timeBlocks`), blockIds = new Set();
    if (blocks.length < 2 || blocks.length > 40) fail(`${path}.timeBlocks`, 'must contain 2..40 blocks');
    blocks.forEach((block, i) => {
        object(block, `${path}.timeBlocks[${i}]`); id(block.id, `${path}.timeBlocks[${i}].id`); string(block.label, `${path}.timeBlocks[${i}].label`);
        if (block.day !== undefined) string(block.day, `${path}.timeBlocks[${i}].day`);
        if (block.phase !== undefined) string(block.phase, `${path}.timeBlocks[${i}].phase`);
        if (block.dayStart !== undefined && typeof block.dayStart !== 'boolean') fail(`${path}.timeBlocks[${i}].dayStart`, 'must be boolean');
        if (block.dayEnd !== undefined && typeof block.dayEnd !== 'boolean') fail(`${path}.timeBlocks[${i}].dayEnd`, 'must be boolean');
        if (block.energyRecovery !== undefined) integer(block.energyRecovery, `${path}.timeBlocks[${i}].energyRecovery`, 0, 5);
        if (blockIds.has(block.id)) fail(`${path}.timeBlocks`, 'block ids must be unique'); blockIds.add(block.id);
    });
    const locations = array(value.locations, `${path}.locations`), locationIds = new Set();
    if (locations.length < 2 || locations.length > 16) fail(`${path}.locations`, 'must contain 2..16 locations');
    locations.forEach((location, i) => {
        object(location, `${path}.locations[${i}]`); id(location.id, `${path}.locations[${i}].id`); string(location.name, `${path}.locations[${i}].name`);
        if (locationIds.has(location.id)) fail(`${path}.locations`, 'location ids must be unique'); locationIds.add(location.id);
    });
    locations.forEach((location, i) => array(location.neighbors || [], `${path}.locations[${i}].neighbors`).forEach((neighbor, j) => {
        id(neighbor, `${path}.locations[${i}].neighbors[${j}]`); if (!locationIds.has(neighbor)) fail(`${path}.locations[${i}].neighbors[${j}]`, 'must name a declared location');
    }));
    const npcIds = array(value.npcIds, `${path}.npcIds`), npcSet = new Set();
    if (npcIds.length < 2 || npcIds.length > 8) fail(`${path}.npcIds`, 'must contain 2..8 NPCs');
    npcIds.forEach((npcId, i) => { id(npcId, `${path}.npcIds[${i}]`); if (npcSet.has(npcId)) fail(`${path}.npcIds`, 'must not contain duplicates'); npcSet.add(npcId); });
    object(value.initialNpcState, `${path}.initialNpcState`);
    for (const npcId of npcIds) {
        const statePath = `${path}.initialNpcState.${npcId}`, state = object(value.initialNpcState[npcId], statePath);
        id(state.location, `${statePath}.location`); if (!locationIds.has(state.location)) fail(`${statePath}.location`, 'must name a declared location');
        if (state.home !== undefined) { id(state.home, `${statePath}.home`); if (!locationIds.has(state.home)) fail(`${statePath}.home`, 'must name a declared location'); }
        integer(state.energy, `${statePath}.energy`, 1, 5);
        if (state.cash !== undefined) integer(state.cash, `${statePath}.cash`, 0, 100);
        array(state.obligations || [], `${statePath}.obligations`).forEach((obligation, i) => {
            const obligationPath = `${statePath}.obligations[${i}]`; object(obligation, obligationPath); id(obligation.id, `${obligationPath}.id`); string(obligation.description, `${obligationPath}.description`);
            id(obligation.location, `${obligationPath}.location`); if (!locationIds.has(obligation.location)) fail(`${obligationPath}.location`, 'must name a declared location');
            if (obligation.startsAt !== undefined) { id(obligation.startsAt, `${obligationPath}.startsAt`); if (!blockIds.has(obligation.startsAt)) fail(`${obligationPath}.startsAt`, 'must name a declared time block'); }
            if (obligation.triggeredBy !== undefined) id(obligation.triggeredBy, `${obligationPath}.triggeredBy`);
            if (obligation.completion !== undefined && !['work', 'arrive'].includes(obligation.completion)) fail(`${obligationPath}.completion`, 'must be work or arrive');
            id(obligation.deadline, `${obligationPath}.deadline`); if (!blockIds.has(obligation.deadline)) fail(`${obligationPath}.deadline`, 'must name a declared time block');
            integer(obligation.priority, `${obligationPath}.priority`, 1, 5); integer(obligation.effort ?? 1, `${obligationPath}.effort`, 1, 3);
            if (obligation.cashReward !== undefined) integer(obligation.cashReward, `${obligationPath}.cashReward`, 0, 20);
            if (obligation.cashCost !== undefined) integer(obligation.cashCost, `${obligationPath}.cashCost`, 0, 20);
            if (obligation.payTo !== undefined) { id(obligation.payTo, `${obligationPath}.payTo`); if (!npcSet.has(obligation.payTo)) fail(`${obligationPath}.payTo`, 'must name a declared NPC'); }
        });
    }
    for (const npcId of Object.keys(value.initialNpcState)) if (!npcSet.has(npcId)) fail(`${path}.initialNpcState.${npcId}`, 'does not appear in npcIds');
    array(value.ambientPressures || [], `${path}.ambientPressures`).forEach((pressure, i) => {
        const pressurePath = `${path}.ambientPressures[${i}]`; object(pressure, pressurePath); id(pressure.id, `${pressurePath}.id`); string(pressure.description, `${pressurePath}.description`);
        id(pressure.location, `${pressurePath}.location`); if (!locationIds.has(pressure.location)) fail(`${pressurePath}.location`, 'must name a declared location');
        id(pressure.startsAt, `${pressurePath}.startsAt`); id(pressure.deadline, `${pressurePath}.deadline`);
        if (!blockIds.has(pressure.startsAt) || !blockIds.has(pressure.deadline)) fail(pressurePath, 'startsAt and deadline must name declared time blocks');
        string(pressure.stakes, `${pressurePath}.stakes`);
        if (pressure.chance !== undefined && (!Number.isFinite(Number(pressure.chance)) || Number(pressure.chance) < 0 || Number(pressure.chance) > 1)) fail(`${pressurePath}.chance`, 'must be a number from 0 to 1');
        if (pressure.satisfiedBy !== undefined) id(pressure.satisfiedBy, `${pressurePath}.satisfiedBy`);
        if (pressure.consequence !== undefined) string(pressure.consequence, `${pressurePath}.consequence`);
    });
    const pressureIds = new Set((value.ambientPressures || []).map(item => item.id));
    for (const npcId of npcIds) for (const [i, obligation] of (value.initialNpcState[npcId].obligations || []).entries()) {
        if (obligation.triggeredBy && !pressureIds.has(obligation.triggeredBy)) fail(`${path}.initialNpcState.${npcId}.obligations[${i}].triggeredBy`, 'must name a declared ambient pressure');
    }
    array(value.publicFacts || [], `${path}.publicFacts`).forEach((fact, i) => string(fact, `${path}.publicFacts[${i}]`));
    return { ...value, ambientPressures: value.ambientPressures || [], publicFacts: value.publicFacts || [] };
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
    validateTownSchedule, validateLivingTown, validateRunManifest, validateModelPolicyDecision, validatePreservedExperiment, normalizeParticipants };
