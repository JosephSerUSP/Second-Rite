'use strict';

const crypto = require('crypto');
const { validateDossier, validateLivingTown } = require('./schemas');

const PLAN_SCHEMA = { type: 'json_schema', json_schema: { name: 'living_town_plan', strict: true, schema: {
    type: 'object', additionalProperties: false, properties: {
        kind: { type: 'string', enum: ['move', 'work', 'seek', 'help', 'rest', 'linger', 'avoid'] },
        destination: { type: ['string', 'null'] }, target: { type: ['string', 'null'] }, obligationId: { type: ['string', 'null'] },
        talk: { type: 'boolean' }, reason: { type: 'string' }, approach: { type: 'string' }, expectedOutcome: { type: 'string' },
    }, required: ['kind', 'destination', 'target', 'obligationId', 'talk', 'reason', 'approach', 'expectedOutcome'],
} } };

const BEAT_SCHEMA = { type: 'json_schema', json_schema: { name: 'living_town_encounter_beat', strict: true, schema: {
    type: 'object', additionalProperties: false, properties: {
        physicalAction: { type: 'string' }, speech: { type: 'string' }, privateInterpretation: { type: 'string' }, nextIntention: { type: 'string' },
    }, required: ['physicalAction', 'speech', 'privateInterpretation', 'nextIntention'],
} } };

function hash(value) { return crypto.createHash('sha256').update(String(value)).digest('hex'); }
function seededIndex(seed, length) { return length ? (parseInt(hash(seed).slice(0, 8), 16) >>> 0) % length : -1; }
function clone(value) { return JSON.parse(JSON.stringify(value)); }
function locationMap(definition) { return new Map(definition.locations.map(location => [location.id, location])); }
function displayName(dossiers, id) { return dossiers[id] && dossiers[id].displayName || id; }
function openObligations(state, npcId) { return state.npcs[npcId].obligations.filter(item => item.status === 'open'); }
function blockIndex(definition, id) { return definition.timeBlocks.findIndex(block => block.id === id); }

function canonText(dossier) {
    const canon = dossier.canon || {};
    return [
        canon.core && `Core: ${canon.core}`, canon.wants && `Wants: ${canon.wants}`, canon.fears && `Fears: ${canon.fears}`,
        canon.defenses && `Under pressure: ${canon.defenses}`, canon.contradictions && `Contradictions: ${canon.contradictions}`,
        canon.boundaries && `Canon boundaries: ${canon.boundaries}`, canon.tells && canon.tells.length && `Behavioral tells: ${canon.tells.join('; ')}`,
        canon.antiTropes && canon.antiTropes.length && `Avoid these readings: ${canon.antiTropes.join('; ')}`,
    ].filter(Boolean).join('\n') || '(author canon is not yet supplied; remain conservative)';
}

function activePressures(definition, blockId) {
    const now = blockIndex(definition, blockId);
    return definition.ambientPressures.filter(pressure => blockIndex(definition, pressure.startsAt) <= now && blockIndex(definition, pressure.deadline) >= now);
}

function chanceRoll(seed, id) { return parseInt(hash(`${seed}:pressure:${id}`).slice(0, 8), 16) / 0xffffffff; }

function materializeDefinition(definition, seed) {
    const copy = clone(definition);
    copy.chanceEvents = (copy.ambientPressures || []).filter(item => item.chance !== undefined).map(item => ({ id: item.id, chance: item.chance, activated: chanceRoll(seed, item.id) < Number(item.chance) }));
    const activeIds = new Set(copy.chanceEvents.filter(item => item.activated).map(item => item.id));
    copy.ambientPressures = (copy.ambientPressures || []).filter(item => item.chance === undefined || activeIds.has(item.id));
    return copy;
}

function initialState(definition) {
    const state = { block: null, npcs: {}, publicEvents: [], privateMemories: {}, daySummaries: [] };
    for (const npcId of definition.npcIds) {
        const authored = definition.initialNpcState[npcId];
        const activePressureIds = new Set((definition.ambientPressures || []).map(item => item.id));
        state.npcs[npcId] = { location: authored.location, home: authored.home || authored.location, energy: authored.energy, cash: authored.cash || 0, obligations: (authored.obligations || []).map(item => ({ ...item, effort: item.effort || 1, progress: 0, status: item.triggeredBy && !activePressureIds.has(item.triggeredBy) ? 'dormant' : item.startsAt && item.startsAt !== definition.timeBlocks[0].id ? 'pending' : 'open' })) };
        state.privateMemories[npcId] = [];
    }
    return state;
}

function plannerPrompt({ definition, dossier, state, npcId, block, promptVariant = '' }) {
    const self = state.npcs[npcId], locations = locationMap(definition), here = locations.get(self.location);
    const visibleHere = definition.npcIds.filter(id => id !== npcId && state.npcs[id].location === self.location).map(id => displayName({ [id]: { displayName: id } }, id));
    const obligations = openObligations(state, npcId).map(item => `- ${item.id}: ${item.description}; at ${item.location}; deadline ${item.deadline}; priority ${item.priority}; progress ${item.progress}/${item.effort}; completes by ${item.completion === 'arrive' ? 'arriving at the location (do not choose work)' : 'work'}${item.cashReward ? `; earns ${item.cashReward} cash` : ''}${item.cashCost ? `; costs ${item.cashCost} cash` : ''}${item.payTo ? ` paid to ${item.payTo}` : ''}`).join('\n') || '(none)';
    const pressures = activePressures(definition, block.id).map(item => `- ${item.id} at ${item.location}: ${item.description} Stakes: ${item.stakes}`).join('\n') || '(none)';
    const memories = (state.privateMemories[npcId] || []).slice(-4).map(item => `- ${item}`).join('\n') || '(none)';
    return [
        `Choose ${dossier.displayName}'s next practical intention for ${block.label}. Return only the requested JSON.`,
        'This is an agent simulation, not a scene-writing exercise. Protect time, energy, work, avoidance, and incomplete obligations. Do not choose an action merely because it would make entertaining dialogue. An ordinary or antisocial choice is valid. Public material consequences outrank private assumptions.',
        `AUTHOR CANON (highest authority):\n${canonText(dossier)}`,
        `Current location: ${self.location} (${here.name}). Home: ${self.home}. Energy: ${self.energy}/5. Cash: ${self.cash}. Adjacent destinations: ${(here.neighbors || []).join(', ') || '(none)'}.`,
        `Open obligations:\n${obligations}`,
        `Active town pressures:\n${pressures}`,
        `People visibly here: ${visibleHere.join(', ') || '(none)'}. Known town roster: ${definition.npcIds.filter(id => id !== npcId).join(', ')}.`,
        `Recent private interpretations:\n${memories}`,
        `Stable public facts:\n${definition.publicFacts.map(fact => `- ${fact}`).join('\n') || '(none)'}`,
        `Recent public consequences:\n${state.publicEvents.slice(-6).map(event => `- ${event.summary}`).join('\n') || '(none)'}`,
        ...(block.dayEnd ? [`This is the final block of ${block.day || 'the day'}. Ending at home (${self.home}) permits full overnight recovery; ending elsewhere permits only 1 energy of recovery.`] : []),
        'Choose exactly one action. move names an adjacent destination and does no work this block. work names an open obligation only when you are already at its location and does not include travel. seek names another NPC and moves toward them. help names a co-located NPC and helps their local obligation. avoid names another NPC. rest and linger stay put. All irrelevant destination, target, and obligationId fields must be null. Set talk=true only if speaking serves the intention. reason is private causal reasoning, approach is the concrete method, and expectedOutcome is a modest prediction—not narration.',
        ...(promptVariant && promptVariant !== 'baseline' ? [`Experiment guidance: ${promptVariant}`] : []),
    ].join('\n\n');
}

function beginBlock({ definition, dossiers, state, block }) {
    const events = [];
    if (block.dayStart) for (const npcId of definition.npcIds) {
        const npc = state.npcs[npcId], prior = npc.energy, atHome = npc.location === npc.home;
        npc.energy = Math.min(5, npc.energy + (atHome ? Number(block.energyRecovery ?? 3) : 1));
        if (npc.energy !== prior) events.push(addEvent(state, block, 'overnight-recovery', [npcId], `${displayName(dossiers, npcId)} began ${block.day || 'the day'} with ${npc.energy}/5 energy after ${atHome ? 'sleeping at home' : `spending the night away from home at ${npc.location}`}.`, []));
    }
    for (const npcId of definition.npcIds) for (const obligation of state.npcs[npcId].obligations) {
        if (obligation.status === 'pending' && obligation.startsAt === block.id) {
            obligation.status = 'open';
            events.push(addEvent(state, block, 'obligation-started', [npcId], `${displayName(dossiers, npcId)} now had to attend to “${obligation.description}”.`, [obligation.id]));
        }
    }
    return events;
}

function endDay({ definition, dossiers, state, block }) {
    if (!block.dayEnd) return null;
    const events = state.publicEvents.filter(event => event.blockId && definition.timeBlocks.find(item => item.id === event.blockId)?.day === block.day);
    const completed = events.filter(event => event.type === 'obligation-completed').map(event => event.summary);
    const missed = events.filter(event => event.type === 'deadline-missed' || event.type === 'pressure-consequence').map(event => event.summary);
    const encounters = events.filter(event => event.type === 'encounter').length;
    const summary = { day: block.day || block.label, completed, missed, encounters, materialEvents: events.filter(event => !['movement', 'encounter', 'overnight-recovery', 'obligation-started'].includes(event.type)).length };
    state.daySummaries.push(summary);
    for (const npcId of definition.npcIds) state.privateMemories[npcId] = (state.privateMemories[npcId] || []).slice(-8);
    return summary;
}

function validatePlan(plan, { definition, state, npcId }) {
    if (!plan || typeof plan !== 'object' || !['move', 'work', 'seek', 'help', 'rest', 'linger', 'avoid'].includes(plan.kind)) throw new Error(`${npcId} returned an invalid living-town plan`);
    for (const field of ['reason', 'approach', 'expectedOutcome']) if (typeof plan[field] !== 'string' || !plan[field].trim()) throw new Error(`${npcId} plan.${field} must be a non-empty string`);
    if (typeof plan.talk !== 'boolean') throw new Error(`${npcId} plan.talk must be boolean`);
    const ids = new Set(definition.npcIds), locations = locationMap(definition), self = state.npcs[npcId];
    if (plan.destination !== null && !locations.has(plan.destination)) throw new Error(`${npcId} chose unknown destination '${plan.destination}'`);
    if (plan.target !== null && (!ids.has(plan.target) || plan.target === npcId)) throw new Error(`${npcId} chose invalid target '${plan.target}'`);
    if (plan.obligationId !== null && !openObligations(state, npcId).some(item => item.id === plan.obligationId)) throw new Error(`${npcId} chose unknown open obligation '${plan.obligationId}'`);
    if (plan.kind === 'move' && (!plan.destination || !locations.get(self.location).neighbors.includes(plan.destination))) throw new Error(`${npcId} move must name an adjacent destination`);
    if (plan.kind !== 'move' && plan.destination !== null) throw new Error(`${npcId} ${plan.kind} must leave destination null`);
    if (!['seek', 'help', 'avoid'].includes(plan.kind) && plan.target !== null) throw new Error(`${npcId} ${plan.kind} must leave target null`);
    if (plan.kind !== 'work' && plan.obligationId !== null) throw new Error(`${npcId} ${plan.kind} must leave obligationId null`);
    if (plan.kind === 'work') {
        if (!plan.obligationId) throw new Error(`${npcId} work must name an open obligation`);
        const obligation = openObligations(state, npcId).find(item => item.id === plan.obligationId);
        if (obligation.completion === 'arrive') throw new Error(`${npcId} must reach ${obligation.location} rather than work on arrival obligation '${obligation.id}'`);
        if (obligation.location !== self.location) throw new Error(`${npcId} must move to ${obligation.location} before working on '${obligation.id}'`);
        if (self.energy <= 0) throw new Error(`${npcId} cannot work at zero energy`);
        if (Number(obligation.cashCost || 0) > self.cash) throw new Error(`${npcId} cannot afford the ${obligation.cashCost} cash required by '${obligation.id}'`);
    }
    if (['seek', 'help', 'avoid'].includes(plan.kind) && !plan.target) throw new Error(`${npcId} ${plan.kind} must name another NPC`);
    if (plan.kind === 'help' && state.npcs[plan.target].location !== self.location) throw new Error(`${npcId} must seek ${plan.target} before helping them`);
    return plan;
}

function shortestNext(definition, from, to) {
    if (from === to) return from;
    const locations = locationMap(definition), queue = [[from, null]], visited = new Set([from]);
    while (queue.length) {
        const [current, first] = queue.shift();
        for (const neighbor of locations.get(current).neighbors || []) {
            if (visited.has(neighbor)) continue;
            const next = first || neighbor; if (neighbor === to) return next;
            visited.add(neighbor); queue.push([neighbor, next]);
        }
    }
    return from;
}

function addEvent(state, block, type, participants, summary, causes = []) {
    const event = { id: `${block.id}.event.${state.publicEvents.length + 1}`, blockId: block.id, type, participants, summary, causes };
    state.publicEvents.push(event); return event;
}

function completeIfReady(obligation, state, block, owner, helper = null) {
    if (obligation.progress < obligation.effort) return false;
    obligation.status = 'complete';
    const ownerState = state.npcs[owner], reward = Number(obligation.cashReward || 0), cost = Number(obligation.cashCost || 0);
    ownerState.cash += reward - cost;
    if (obligation.payTo) state.npcs[obligation.payTo].cash += cost;
    const cashText = [reward ? `${owner} earned ${reward} cash` : '', cost ? `${owner} spent ${cost} cash${obligation.payTo ? ` paid to ${obligation.payTo}` : ''}` : ''].filter(Boolean).join('; ');
    addEvent(state, block, 'obligation-completed', helper ? [owner, helper] : [owner], `${obligation.description} was completed${helper ? ` with help from ${helper}` : ''}${cashText ? ` (${cashText})` : ''}.`, [obligation.id]);
    return true;
}

function resolvePlans({ definition, dossiers, state, plans, block, seed }) {
    const start = clone(state), events = [];
    for (const npcId of definition.npcIds) {
        const plan = plans[npcId], npc = state.npcs[npcId], before = npc.location;
        if (plan.kind === 'move') npc.location = plan.destination;
        else if (plan.kind === 'seek') npc.location = shortestNext(definition, before, start.npcs[plan.target].location);
        else if (plan.kind === 'avoid' && start.npcs[plan.target].location === before) {
            const options = locationMap(definition).get(before).neighbors || [], chosen = seededIndex(`${seed}:${block.id}:${npcId}:avoid`, options.length);
            if (chosen >= 0) npc.location = options[chosen];
        }
        if (npc.location !== before) events.push(addEvent(state, block, 'movement', [npcId], `${displayName(dossiers, npcId)} went from ${before} to ${npc.location}.`, [`${npcId} chose ${plan.kind}: ${plan.approach}`]));
    }
    for (const npcId of definition.npcIds) {
        const npc = state.npcs[npcId];
        for (const obligation of openObligations(state, npcId).filter(item => item.completion === 'arrive' && item.location === npc.location)) {
            obligation.progress = obligation.effort;
            events.push(addEvent(state, block, 'arrival', [npcId], `${displayName(dossiers, npcId)} reached ${npc.location} for “${obligation.description}”.`, [obligation.id]));
            completeIfReady(obligation, state, block, npcId);
        }
    }
    // Resolve owners' work before assistance so simultaneous help cannot make
    // the owner's already-valid action appear to fail.
    for (const npcId of definition.npcIds) {
        const plan = plans[npcId], npc = state.npcs[npcId];
        if (plan.kind === 'work') {
            const obligation = npc.obligations.find(item => item.id === plan.obligationId && item.status === 'open');
            if (obligation && obligation.location === npc.location && npc.energy > 0) {
                obligation.progress++; npc.energy = Math.max(0, npc.energy - 1);
                events.push(addEvent(state, block, 'work', [npcId], `${displayName(dossiers, npcId)} advanced “${obligation.description}” (${obligation.progress}/${obligation.effort}).`, [`${npcId}: ${plan.reason}`]));
                completeIfReady(obligation, state, block, npcId);
            } else events.push(addEvent(state, block, 'blocked', [npcId], `${displayName(dossiers, npcId)} could not work on the chosen obligation from ${npc.location}.`, [`${npcId}: ${plan.approach}`]));
        }
    }
    for (const npcId of definition.npcIds) {
        const plan = plans[npcId], npc = state.npcs[npcId];
        if (plan.kind === 'help') {
            const target = state.npcs[plan.target];
            if (target.location === npc.location && npc.energy > 0) {
                const eligible = openObligations(state, plan.target).filter(item => item.location === npc.location && item.completion !== 'arrive').sort((a, b) => b.priority - a.priority);
                if (eligible.length) {
                    const obligation = eligible[0]; obligation.progress++; npc.energy = Math.max(0, npc.energy - 1);
                    events.push(addEvent(state, block, 'help', [npcId, plan.target], `${displayName(dossiers, npcId)} helped ${displayName(dossiers, plan.target)} with “${obligation.description}” (${obligation.progress}/${obligation.effort}).`, [`${npcId}: ${plan.reason}`]));
                    completeIfReady(obligation, state, block, plan.target, npcId);
                } else events.push(addEvent(state, block, 'help-unneeded', [npcId, plan.target], `${displayName(dossiers, npcId)} arrived ready to help, but ${displayName(dossiers, plan.target)} had already completed the local obligation.`, [`${npcId}: ${plan.reason}`]));
            }
        } else if (plan.kind === 'rest') {
            const prior = npc.energy; npc.energy = Math.min(5, npc.energy + 1);
            events.push(addEvent(state, block, 'rest', [npcId], `${displayName(dossiers, npcId)} rested at ${npc.location} (${prior}→${npc.energy} energy).`, [`${npcId}: ${plan.reason}`]));
        }
    }
    return { start, events };
}

function chooseEncounters({ definition, state, plans }) {
    const pairs = [];
    for (let i = 0; i < definition.npcIds.length; i++) for (let j = i + 1; j < definition.npcIds.length; j++) {
        const a = definition.npcIds[i], b = definition.npcIds[j];
        if (state.npcs[a].location !== state.npcs[b].location) continue;
        if ((plans[a].kind === 'avoid' && plans[a].target === b) || (plans[b].kind === 'avoid' && plans[b].target === a)) continue;
        const aDirected = plans[a].target === b && ['seek', 'help'].includes(plans[a].kind);
        const bDirected = plans[b].target === a && ['seek', 'help'].includes(plans[b].kind);
        const aTalks = plans[a].talk && (plans[a].target === b || plans[a].target === null);
        const bTalks = plans[b].talk && (plans[b].target === a || plans[b].target === null);
        if (!(aDirected || bDirected || aTalks || bTalks)) continue;
        const initiatedBy = aDirected || aTalks ? a : b;
        pairs.push({ participants: [initiatedBy, initiatedBy === a ? b : a], location: state.npcs[a].location, causes: [
            `${a}: ${plans[a].kind} — ${plans[a].reason}`, `${b}: ${plans[b].kind} — ${plans[b].reason}`,
        ] });
    }
    const used = new Set(), selected = [];
    for (const pair of pairs) if (!pair.participants.some(id => used.has(id)) && selected.length < 2) { selected.push(pair); pair.participants.forEach(id => used.add(id)); }
    return selected;
}

function resolveDeadlines({ definition, dossiers, state, block }) {
    const events = [];
    for (const npcId of definition.npcIds) for (const obligation of state.npcs[npcId].obligations) {
        if (obligation.status === 'open' && obligation.deadline === block.id && obligation.progress < obligation.effort) {
            obligation.overdue = true;
            events.push(addEvent(state, block, 'deadline-missed', [npcId], `${displayName(dossiers, npcId)} reached the deadline for “${obligation.description}” with ${obligation.progress}/${obligation.effort} effort completed.`, [obligation.id]));
        }
    }
    for (const pressure of definition.ambientPressures.filter(item => item.deadline === block.id)) {
        const satisfied = pressure.satisfiedBy && definition.npcIds.some(npcId => state.npcs[npcId].obligations.some(item => item.id === pressure.satisfiedBy && item.status === 'complete'));
        const summary = satisfied ? `The pressure “${pressure.description}” was answered before its deadline.` : (pressure.consequence || `The deadline passed without resolving “${pressure.description}”`);
        events.push(addEvent(state, block, satisfied ? 'pressure-resolved' : 'pressure-consequence', [], summary, [pressure.id, ...(pressure.satisfiedBy ? [pressure.satisfiedBy] : [])]));
    }
    return events;
}

function relationshipCanon(dossier, target) {
    const guidance = dossier.relationshipCanon && dossier.relationshipCanon[target];
    return guidance ? [guidance.dynamic && `Dynamic: ${guidance.dynamic}`, guidance.signals && `Signals: ${guidance.signals}`, guidance.avoid && `Avoid: ${guidance.avoid}`].filter(Boolean).join('\n') : '(no relationship-specific canon supplied)';
}

function encounterPrompt({ definition, dossiers, state, block, encounter, npcId, priorBeats }) {
    const dossier = dossiers[npcId], other = encounter.participants.find(id => id !== npcId), plan = encounter.plans[npcId];
    return [
        `Render one observable beat by ${dossier.displayName} during an encounter with ${displayName(dossiers, other)} at ${encounter.location} in ${block.label}. Return only the requested JSON.`,
        'This encounter exists because independent plans collided. It is not obligated to become witty, intimate, revealing, symmetrical, or conclusive. Physical action and silence are valid. Speech must serve the current intention; use an empty string when none is warranted.',
        `AUTHOR CANON:\n${canonText(dossier)}`,
        `RELATIONSHIP CANON WITH ${other}:\n${relationshipCanon(dossier, other)}`,
        `Your already-chosen plan: ${plan.kind}. Reason: ${plan.reason}. Method: ${plan.approach}. Expected outcome: ${plan.expectedOutcome}.`,
        `The other person's plan: ${encounter.plans[other].kind}. Observable approach: ${encounter.plans[other].approach}.`,
        `Material state: energy ${state.npcs[npcId].energy}/5; cash ${state.npcs[npcId].cash}; open obligations: ${openObligations(state, npcId).map(item => `${item.description} (${item.progress}/${item.effort}, deadline ${item.deadline})`).join('; ') || 'none'}.`,
        `Material consequences already resolved this block:\n${state.publicEvents.filter(event => event.blockId === block.id && event.type !== 'encounter').map(event => `- ${event.summary}`).join('\n') || '(none)'}`,
        `Prior beats in this brief encounter:\n${priorBeats.map(beat => `${displayName(dossiers, beat.actor)} ${beat.physicalAction}${beat.speech ? ` and says “${beat.speech}”` : ''}`).join('\n') || '(none)'}`,
        'The material consequences above are immutable. The beat may acknowledge them but cannot move anyone, transfer a scarce item, complete or undo work, or claim a conflicting outcome. privateInterpretation is what this NPC privately makes of the collision; nextIntention is what they now mean to do after this beat. Neither field is spoken aloud.',
    ].join('\n\n');
}

async function runLivingTown({ definition: rawDefinition, dossiers, gateway, model, seed = 'living-town', signal, promptVariant = '', onEvent = () => {} }) {
    const definition = materializeDefinition(validateLivingTown(rawDefinition), seed), validatedDossiers = {};
    for (const npcId of definition.npcIds) validatedDossiers[npcId] = validateDossier(dossiers[npcId], `dossiers.${npcId}`);
    const state = initialState(definition), blocks = [];
    for (const block of definition.timeBlocks) {
        state.block = block.id;
        const openingEvents = beginBlock({ definition, dossiers: validatedDossiers, state, block });
        const plans = {};
        for (const npcId of definition.npcIds) {
            if (signal && signal.aborted) throw Object.assign(new Error('run cancelled'), { code: 'ABORT_ERR' });
            const basePrompt = plannerPrompt({ definition, dossier: validatedDossiers[npcId], state, npcId, block, promptVariant });
            let priorPlan = null, priorError = null;
            for (let attempt = 0; attempt < 2; attempt++) {
                const correction = priorError ? `\n\nYour prior plan was rejected: ${priorError.message}\nRejected JSON: ${JSON.stringify(priorPlan)}\nReturn a corrected plan that obeys the one-action rules.` : '';
                const reply = await gateway.call({ role: 'town-planner', ...(typeof model === 'string' ? { model } : model), messages: [
                    { role: 'system', content: 'You choose one bounded NPC intention inside an agent-based town simulation. Return only valid JSON.' },
                    { role: 'user', content: basePrompt + correction },
                ], responseFormat: PLAN_SCHEMA, signal, seed: `${seed}:${block.id}:${npcId}:plan:${attempt}` });
                priorPlan = reply.value;
                try { plans[npcId] = validatePlan(reply.value, { definition, state, npcId }); priorError = null; break; } catch (error) { priorError = error; }
            }
            if (priorError) throw priorError;
            onEvent({ type: 'town-plan', blockId: block.id, npcId, plan: plans[npcId] });
        }
        const resolved = resolvePlans({ definition, dossiers: validatedDossiers, state, plans, block, seed });
        const encounterSpecs = chooseEncounters({ definition, state, plans }), encounters = [];
        for (const spec of encounterSpecs) {
            const encounter = { ...spec, plans: Object.fromEntries(spec.participants.map(id => [id, plans[id]])), beats: [] };
            for (const npcId of spec.participants) {
                const reply = await gateway.call({ role: 'town-encounter', ...(typeof model === 'string' ? { model } : model), messages: [
                    { role: 'system', content: 'You render one embodied NPC beat caused by an already-resolved town encounter. Return only valid JSON.' },
                    { role: 'user', content: encounterPrompt({ definition, dossiers: validatedDossiers, state, block, encounter, npcId, priorBeats: encounter.beats }) },
                ], responseFormat: BEAT_SCHEMA, signal, seed: `${seed}:${block.id}:${npcId}:beat` });
                const beat = { actor: npcId, ...reply.value };
                if (typeof beat.physicalAction !== 'string' || typeof beat.speech !== 'string' || typeof beat.privateInterpretation !== 'string' || typeof beat.nextIntention !== 'string') throw new Error(`${npcId} returned an invalid encounter beat`);
                encounter.beats.push(beat);
                if (beat.privateInterpretation.trim()) state.privateMemories[npcId].push(`${block.label}, ${encounter.location}: ${beat.privateInterpretation}`);
                onEvent({ type: 'town-beat', blockId: block.id, event: beat });
            }
            const summary = encounter.beats.map(beat => `${displayName(validatedDossiers, beat.actor)} ${beat.physicalAction}${beat.speech ? ` and said “${beat.speech}”` : ''}`).join(' ');
            encounter.event = addEvent(state, block, 'encounter', spec.participants, summary, spec.causes);
            encounters.push(encounter);
        }
        const deadlineEvents = resolveDeadlines({ definition, dossiers: validatedDossiers, state, block });
        const daySummary = endDay({ definition, dossiers: validatedDossiers, state, block });
        blocks.push({ block: clone(block), activePressures: clone(activePressures(definition, block.id)), plans: clone(plans), resolutionEvents: clone(openingEvents.concat(resolved.events, deadlineEvents)), encounters: clone(encounters), daySummary: clone(daySummary), state: clone(state) });
    }
    return { mode: 'living-town', definition: clone(definition), npcNames: Object.fromEntries(definition.npcIds.map(id => [id, validatedDossiers[id].displayName])), blocks, state };
}

module.exports = { PLAN_SCHEMA, BEAT_SCHEMA, activePressures, materializeDefinition, initialState, plannerPrompt, validatePlan, shortestNext, resolvePlans, chooseEncounters, resolveDeadlines, beginBlock, endDay, encounterPrompt, runLivingTown };
