'use strict';

const { extractJson } = require('../../shared/llm');
const { validateScenarioCard } = require('./schemas');

const SCENARIO_SCHEMA = { type: 'json_schema', json_schema: { name: 'scenario_cards', strict: true, schema: {
    type: 'object', additionalProperties: false, properties: { scenarios: { type: 'array', items: {
        type: 'object', additionalProperties: false, properties: {
            id: { type: 'string' }, title: { type: 'string' }, premise: { type: 'string' },
            participants: { type: 'array', items: { type: 'object', additionalProperties: false, properties: {
                id: { type: 'string' }, type: { type: 'string', enum: ['npc', 'playerProxy'] }, displayName: { type: ['string', 'null'] },
                goals: { type: 'array', items: { type: 'string' } }, privateKnowledge: { type: 'array', items: { type: 'string' } },
            }, required: ['id', 'type', 'displayName', 'goals', 'privateKnowledge'] } },
            maxTurns: { type: 'integer', minimum: 1, maximum: 50 }, pressures: { type: 'array', items: { type: 'string' } },
            constraints: { type: 'array', items: { type: 'string' } }, allowedFacts: { type: 'array', items: { type: 'string' } },
        }, required: ['id', 'title', 'premise', 'participants', 'maxTurns', 'pressures', 'constraints', 'allowedFacts'],
    } } }, required: ['scenarios'],
} } };

async function proposeScenarios({ gateway, dossiers, axes, count = 3, model, temperature = 0.9, signal }) {
    if (!Number.isInteger(count) || count < 1 || count > 20) throw new Error('scenario proposal count must be an integer from 1 to 20');
    const prompt = [
        'Propose bounded NPC social-simulation scenario cards for an authoring gauntlet.',
        `Generate exactly ${count} distinct cards. Vary one meaningful pressure at a time. Do not resolve the conflict neatly or invent facts not present in the dossiers.`,
        `Pressure axes: ${(axes || []).join('; ') || '(mundane pressure, embarrassment, being wrong)'}`,
        `Dossiers:\n${JSON.stringify(dossiers, null, 2)}`,
        'Return only JSON matching the schema. Every participant must be present in the dossiers or be an explicitly described playerProxy.',
    ].join('\n\n');
    const response = await gateway.call({ role: 'scenario-generator', model, temperature, responseFormat: SCENARIO_SCHEMA, signal,
        messages: [{ role: 'system', content: 'You design controlled social simulation inputs. Return only schema-valid JSON.' }, { role: 'user', content: prompt }] });
    const value = response.value || extractJson(response.content);
    if (!Array.isArray(value.scenarios)) throw new Error('scenario generator returned no scenarios');
    if (value.scenarios.length !== count) throw new Error(`scenario generator returned ${value.scenarios.length} cards; expected ${count}`);
    const normalized = value.scenarios.map((scenario, i) => {
        const validated = validateScenarioCard(scenario, `scenarios[${i}]`);
        for (const participant of validated.participants) if (participant.type !== 'playerProxy' && !dossiers[participant.id]) throw new Error(`scenarios[${i}]: unknown NPC participant '${participant.id}'`);
        return validated;
    });
    return normalized;
}

module.exports = { SCENARIO_SCHEMA, proposeScenarios };
