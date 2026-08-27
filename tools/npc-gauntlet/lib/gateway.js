'use strict';

const { chatForProvider, extractJson, normalizeUsage } = require('../../shared/llm');
const policy = require('./model-policy');

class BudgetExceeded extends Error { constructor(message) { super(message); this.code = 'BUDGET_EXCEEDED'; } }

function usageCost(usage) {
    if (!usage) return 0;
    if (typeof usage.cost === 'number') return usage.cost;
    return 0;
}
function addEstimatedCost(usage, provider, model, catalogue) {
    const normalized = normalizeUsage(usage) || { prompt_tokens: 0, completion_tokens: 0, total_tokens: 0 };
    if (typeof normalized.cost === 'number') return normalized;
    let input = 0, output = 0;
    if (provider === 'openai' && model === policy.LUNA) { input = 0.20e-6; output = 1.20e-6; }
    if (provider === 'openrouter') {
        const record = policy.modelRecord(catalogue, model);
        if (record && record.pricing) { input = Number(record.pricing.prompt); output = Number(record.pricing.completion); }
    }
    if (Number.isFinite(input) && Number.isFinite(output) && (input || output)) normalized.cost = normalized.prompt_tokens * input + normalized.completion_tokens * output;
    return normalized;
}

class BudgetGuard {
    constructor(budget = {}) {
        this.maxUsd = budget.maxUsd === undefined ? Infinity : Number(budget.maxUsd);
        this.maxCalls = budget.maxCalls === undefined ? Infinity : Number(budget.maxCalls);
        this.maxTokens = budget.maxTokens === undefined ? Infinity : Number(budget.maxTokens);
        const initial = budget.initial || {};
        this.calls = Number(initial.calls || 0); this.tokens = Number(initial.tokens || 0); this.usd = Number(initial.usd || 0); this.pendingCalls = 0;
    }
    beforeCall() {
        // Reserve request capacity before an async provider call starts.  This
        // keeps a concurrent worker pool from launching four calls when only
        // one request remains in the hard cap.
        if (this.calls + this.pendingCalls >= this.maxCalls) throw new BudgetExceeded(`request cap reached (${this.maxCalls})`);
        if (this.tokens >= this.maxTokens) throw new BudgetExceeded(`token cap reached (${this.maxTokens})`);
        this.pendingCalls += 1;
    }
    afterCall(usage) {
        this.pendingCalls = Math.max(0, this.pendingCalls - 1);
        const normalized = normalizeUsage(usage) || { total_tokens: 0 };
        this.calls += 1; this.tokens += normalized.total_tokens || 0; this.usd += usageCost(normalized);
        if (this.tokens > this.maxTokens) throw new BudgetExceeded(`token cap exceeded (${this.tokens} > ${this.maxTokens})`);
        if (this.usd > this.maxUsd) throw new BudgetExceeded(`dollar cap exceeded ($${this.usd.toFixed(6)} > $${this.maxUsd})`);
    }
    releaseCall() { this.pendingCalls = Math.max(0, this.pendingCalls - 1); }
    snapshot() { return { calls: this.calls, tokens: this.tokens, usd: this.usd, maxCalls: this.maxCalls, maxTokens: this.maxTokens, maxUsd: this.maxUsd }; }
}

function makeGateway({ catalogue = [], budget, keys = {}, fetchImpl, now = Date.now(), exploratory = false, onUsage = () => {}, onChunk = () => {} } = {}) {
    const guard = budget instanceof BudgetGuard ? budget : new BudgetGuard(budget);
    const catalogueFetcher = fetchImpl ? async () => policy.fetchCatalogue({ apiKey: keys.OPENROUTER_API_KEY, fetchImpl }) : null;
    async function call({ role, model, provider, messages, responseFormat, signal, maxRetries = 3, maxTokens, temperature, seed }) {
        const activeProvider = provider || (model === policy.LUNA ? 'openai' : 'openrouter');
        let activeCatalogue = catalogue;
        if (activeProvider === 'openrouter' && !activeCatalogue.length && catalogueFetcher) activeCatalogue = await catalogueFetcher();
        const decision = policy.assertAllowed({ provider: activeProvider, model, catalogue: activeCatalogue, exploratory });
        const providerConfig = policy.providerFor({ provider: activeProvider, model });
        const requestModel = activeProvider === 'openrouter' && decision.resolvedModel ? decision.resolvedModel : model;
        const apiKey = keys[providerConfig.apiKeyEnv] || process.env[providerConfig.apiKeyEnv];
        if (!apiKey) throw new Error(`${providerConfig.apiKeyEnv} is required for ${activeProvider}`);
        guard.beforeCall();
        let result;
        try {
            result = await chatForProvider({ providerType: providerConfig.type, baseUrl: providerConfig.baseUrl,
                apiKey, model: requestModel, temperature, messages, responseFormat, signal, maxRetries, maxTokens, fetchImpl,
                onChunk: chunk => onChunk({ role, chunk }) });
        } catch (error) {
            guard.releaseCall();
            if (error && error.name === 'AbortError') error.code = 'ABORT_ERR';
            throw error;
        }
        let resolvedDecision = decision;
        if (activeProvider === 'openrouter') {
            const routedModel = result.model || model;
            if (model === 'openrouter/free' || routedModel !== model) {
                resolvedDecision = policy.assertAllowed({ provider: 'openrouter', model: routedModel, catalogue: activeCatalogue, exploratory: false });
            }
        }
        const fallbackPromptTokens = Math.ceil(messages.reduce((sum, item) => sum + String(item.content || '').length, 0) / 4);
        const fallbackCompletionTokens = Math.ceil(String(result.content || '').length / 4);
        const effectiveUsage = addEstimatedCost(result.usage || { prompt_tokens: fallbackPromptTokens, completion_tokens: fallbackCompletionTokens, total_tokens: fallbackPromptTokens + fallbackCompletionTokens }, activeProvider, result.model || requestModel, activeCatalogue);
        guard.afterCall(effectiveUsage);
        onUsage({ role, model: result.model || requestModel, responseId: result.responseId || null, usage: effectiveUsage, budget: guard.snapshot(), policy: resolvedDecision });
        let value;
        try { value = extractJson(result.content); } catch (error) { error.code = 'INVALID_STRUCTURED_OUTPUT'; throw error; }
        return { value, content: result.content, usage: effectiveUsage, model: result.model || requestModel, responseId: result.responseId, policy: resolvedDecision };
    }
    return { call, guard, refreshCatalogue: catalogueFetcher || (async () => catalogue) };
}

function estimateCost({ calls, promptTokens = 2000, completionTokens = 300, provider, model, catalogue = [] }) {
    if (provider === 'openrouter') {
        const record = policy.modelRecord(catalogue, model);
        if (!record || !record.pricing) return null;
        const input = Number(record.pricing.prompt), output = Number(record.pricing.completion);
        if (![input, output].every(Number.isFinite)) return null;
        return calls * (promptTokens * input + completionTokens * output);
    }
    if (provider === 'openai' && model === policy.LUNA) return calls * (promptTokens * 0.20e-6 + completionTokens * 1.20e-6);
    return null;
}

module.exports = { BudgetGuard, BudgetExceeded, makeGateway, estimateCost };
