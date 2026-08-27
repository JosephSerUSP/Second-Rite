'use strict';

const config = require('../config.json');
const LUNA = config.modelPolicy.openaiModels[0];
const OPENROUTER_BASE = 'https://openrouter.ai/api/v1';

function normalizePricing(pricing) {
    if (!pricing || typeof pricing !== 'object') return null;
    const values = Object.entries(pricing).map(([key, value]) => ({ key, value, number: (value === null || value === '' || typeof value === 'boolean') ? NaN : Number(value) }));
    if (!values.length || values.some(x => !Number.isFinite(x.number))) return null;
    return Object.fromEntries(values.map(x => [x.key, x.number]));
}

function isZeroPriced(pricing) {
    const normalized = normalizePricing(pricing);
    return !!normalized && Object.values(normalized).every(value => value === 0);
}

function modelRecord(catalogue, model) {
    if (!Array.isArray(catalogue)) return null;
    // A refreshed catalogue is the availability evidence for the exact model
    // variant the caller selected.  Do not silently substitute a paid base
    // model for a missing `:free` variant.
    return catalogue.find(item => item && item.id === model) || null;
}

function supportsStructured(record) {
    if (!record) return false;
    const supported = record.supported_parameters || record.supportedParameters || [];
    return supported.includes('response_format') || supported.includes('structured_outputs');
}

function decision({ provider, model, catalogue = [], exploratory = false, fromDynamicRouter = false, now = Date.now() }) {
    const p = String(provider || '').toLowerCase();
    const requested = String(model || '');
    const base = {
        contractVersion: 1, provider: p, requestedModel: requested,
        resolvedModel: requested, catalogueAt: new Date(now).toISOString(), allowed: false,
        freePriceEvidence: null, reason: '', exploratory: !!exploratory,
    };
    if (p === 'openai') {
        if (requested === LUNA) {
            return { ...base, allowed: true, reason: 'permitted OpenAI model', resolvedModel: LUNA };
        }
        return { ...base, reason: `OpenAI model '${requested}' is not permitted; only ${LUNA} is allowed` };
    }
    if (p !== 'openrouter') {
        return { ...base, reason: 'only OpenAI Luna or OpenRouter free models are permitted' };
    }
    if (requested === LUNA || requested === `openai/${LUNA}`) {
        const record = modelRecord(catalogue, requested) || modelRecord(catalogue, `openai/${LUNA}`);
        if (!record || !/gpt[- ]?5\.6[- ]?luna/i.test(`${record.id} ${record.name || ''}`)) {
            return { ...base, reason: 'OpenRouter must identify the upstream model exactly as gpt-5.6-luna' };
        }
        if (!supportsStructured(record)) return { ...base, reason: 'OpenRouter GPT-5.6 Luna does not advertise structured output support' };
        return { ...base, allowed: true, resolvedModel: record.id, reason: 'permitted GPT-5.6 Luna through OpenRouter' };
    }
    if (requested === 'openrouter/free') {
        if (!exploratory) return { ...base, reason: 'dynamic openrouter/free is only allowed for explicitly exploratory runs' };
        return { ...base, allowed: true, resolvedModel: null,
            reason: 'exploratory OpenRouter free router; resolved model must be recorded from the response' };
    }
    if (!requested.endsWith(config.modelPolicy.openRouterFreeSuffix)) {
        return { ...base, reason: 'non-Luna OpenRouter models must use an explicit :free variant' };
    }
    if (requested.startsWith('openai/')) {
        return { ...base, reason: 'OpenAI models other than gpt-5.6-luna are not permitted' };
    }
    const record = modelRecord(catalogue, requested);
    const pricing = record && normalizePricing(record.pricing);
    base.freePriceEvidence = pricing ? { modelId: record.id, pricing } : null;
    if (!record) return { ...base, reason: `OpenRouter model '${requested}' is absent from the refreshed catalogue` };
    if (!pricing || !isZeroPriced(record.pricing)) {
        return { ...base, reason: `OpenRouter model '${requested}' does not have verified zero pricing` };
    }
    if (!supportsStructured(record)) {
        return { ...base, reason: `OpenRouter model '${requested}' does not advertise structured output support` };
    }
    return { ...base, allowed: true, reason: 'verified zero-priced OpenRouter :free model' };
}

async function fetchCatalogue({ apiKey, fetchImpl = fetch, baseUrl = OPENROUTER_BASE, signal } = {}) {
    if (!apiKey) throw new Error('OPENROUTER_API_KEY is required to refresh the model catalogue');
    const response = await fetchImpl(`${baseUrl}/models`, {
        headers: { Authorization: `Bearer ${apiKey}` }, signal,
    });
    if (!response.ok) throw new Error(`OpenRouter catalogue HTTP ${response.status}: ${await response.text()}`);
    const body = await response.json();
    if (!Array.isArray(body.data)) throw new Error('OpenRouter catalogue response has no data array');
    return body.data;
}

function assertAllowed(args) {
    const result = decision(args);
    if (!result.allowed) {
        const error = new Error(result.reason);
        error.code = 'MODEL_POLICY_DENIED';
        error.decision = result;
        throw error;
    }
    return result;
}

function providerFor({ provider = 'openrouter', model = LUNA } = {}) {
    if (provider === 'openai') return {
        id: 'openai', type: 'openai-compatible', baseUrl: 'https://api.openai.com/v1',
        apiKeyEnv: 'OPENAI_API_KEY', model,
    };
    return { id: 'openrouter', type: 'openai-compatible', baseUrl: OPENROUTER_BASE,
        apiKeyEnv: 'OPENROUTER_API_KEY', model };
}

module.exports = { LUNA, OPENROUTER_BASE, decision, assertAllowed, fetchCatalogue,
    normalizePricing, isZeroPriced, modelRecord, providerFor, supportsStructured };
