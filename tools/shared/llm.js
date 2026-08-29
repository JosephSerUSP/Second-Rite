// Shared, dependency-free LLM transport used by campaign generation and the
// NPC Gauntlet Lab.  Callers own policy; this module only speaks provider APIs.
'use strict';

function sleep(ms, signal) {
    return new Promise((resolve, reject) => {
        const timer = setTimeout(resolve, ms);
        if (!signal) return;
        if (signal.aborted) { clearTimeout(timer); const error = new Error('aborted'); error.name = 'AbortError'; reject(error); return; }
        signal.addEventListener('abort', () => { clearTimeout(timer); const error = new Error('aborted'); error.name = 'AbortError'; reject(error); }, { once: true });
    });
}

async function chat({ baseUrl, apiKey, model, temperature, messages, onChunk,
    maxRetries = 3, responseFormat, signal, maxTokens, fetchImpl = fetch }) {
    maxRetries = Math.max(1, Number(maxRetries) || 1);
    let lastErr;
    for (let attempt = 1; attempt <= maxRetries; attempt++) {
        try {
            const body = {
                model, temperature, messages, stream: true,
                // Keep the campaign generator's existing usage request.  Some
                // OpenAI-compatible gateways ignore it; OpenRouter returns
                // prompt/completion/cost data when supported.
                usage: { include: true },
                ...(maxTokens ? { max_tokens: maxTokens } : {}),
                ...(responseFormat ? { response_format: responseFormat } : {}),
            };
            const res = await fetchImpl(`${baseUrl}/chat/completions`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${apiKey}`,
                },
                body: JSON.stringify(body),
                signal,
            });
            if (res.status === 429 || res.status >= 500) {
                lastErr = new Error(`HTTP ${res.status}: ${await res.text()}`);
                lastErr.code = res.status === 429 ? 'RATE_LIMIT' : 'TRANSIENT_PROVIDER';
                if (attempt < maxRetries) await sleep(attempt * 5000, signal);
                continue;
            }
            if (!res.ok) { const error = new Error(`HTTP ${res.status}: ${await res.text()}`); error.code = 'PROVIDER_ERROR'; throw error; }

            const decoder = new TextDecoder();
            let buffer = '', content = '', usage = null, resolvedModel = model,
                responseId = null;
            for await (const raw of res.body) {
                buffer += decoder.decode(raw, { stream: true });
                let nl;
                while ((nl = buffer.indexOf('\n')) !== -1) {
                    const line = buffer.slice(0, nl).trim();
                    buffer = buffer.slice(nl + 1);
                    if (!line.startsWith('data:')) continue;
                    const payload = line.slice(5).trim();
                    if (payload === '[DONE]') continue;
                    let evt;
                    try { evt = JSON.parse(payload); } catch { continue; }
                    if (evt.id) responseId = evt.id;
                    if (evt.model) resolvedModel = evt.model;
                    const delta = evt.choices && evt.choices[0] && evt.choices[0].delta
                        && evt.choices[0].delta.content;
                    if (delta) { content += delta; if (onChunk) onChunk(delta); }
                    if (evt.usage) usage = normalizeUsage(evt.usage);
                }
            }
            if (buffer.trim().startsWith('data:')) {
                const payload = buffer.trim().slice(5).trim();
                if (payload && payload !== '[DONE]') {
                    try {
                        const evt = JSON.parse(payload);
                        if (evt.id) responseId = evt.id;
                        if (evt.model) resolvedModel = evt.model;
                        const delta = evt.choices && evt.choices[0] && evt.choices[0].delta && evt.choices[0].delta.content;
                        if (delta) { content += delta; if (onChunk) onChunk(delta); }
                        if (evt.usage) usage = normalizeUsage(evt.usage);
                    } catch { /* ignore malformed trailing frame */ }
                }
            }
            if (!content) { const error = new Error('empty completion (streamed nothing)'); error.code = 'EMPTY_RESPONSE'; throw error; }
            return { content, usage, model: resolvedModel, responseId };
        } catch (err) {
            if (err && err.name === 'AbortError') throw err;
            lastErr = err; if (!lastErr.code) lastErr.code = 'NETWORK_ERROR';
            if (attempt < maxRetries) await sleep(attempt * 5000, signal);
        }
    }
    throw lastErr;
}

async function geminiChat({ apiKey, model, temperature, messages, onChunk,
    maxRetries = 3, responseFormat, signal, fetchImpl = fetch }) {
    maxRetries = Math.max(1, Number(maxRetries) || 1);
    let systemInstruction = null;
    const contents = [];
    for (const msg of messages) {
        if (msg.role === 'system') { systemInstruction = msg.content; continue; }
        contents.push({ role: msg.role === 'assistant' ? 'model' : 'user', parts: [{ text: msg.content }] });
    }
    const body = {
        contents,
        generationConfig: {
            temperature: temperature || 0.7,
            ...(responseFormat && responseFormat.type === 'json_schema'
                ? { responseMimeType: 'application/json', responseSchema: responseFormat.json_schema.schema }
                : {}),
        },
        ...(systemInstruction ? { systemInstruction: { parts: [{ text: systemInstruction }] } } : {}),
    };
    let lastErr;
    for (let attempt = 1; attempt <= maxRetries; attempt++) {
        try {
            const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:streamGenerateContent?alt=sse`;
            const res = await fetchImpl(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'x-goog-api-key': apiKey },
                body: JSON.stringify(body), signal,
            });
            if (res.status === 429 || res.status >= 500) {
                lastErr = new Error(`HTTP ${res.status}: ${await res.text()}`);
                if (attempt < maxRetries) await sleep(attempt * 5000, signal);
                continue;
            }
            if (!res.ok) { const error = new Error(`HTTP ${res.status}: ${await res.text()}`); error.code = 'PROVIDER_ERROR'; throw error; }
            const decoder = new TextDecoder();
            let buffer = '', content = '', usage = null;
            for await (const raw of res.body) {
                buffer += decoder.decode(raw, { stream: true });
                let nl;
                while ((nl = buffer.indexOf('\n')) !== -1) {
                    const line = buffer.slice(0, nl).trim(); buffer = buffer.slice(nl + 1);
                    if (!line.startsWith('data:')) continue;
                    const payload = line.slice(5).trim(); if (!payload) continue;
                    let evt; try { evt = JSON.parse(payload); } catch { continue; }
                    const candidate = evt.candidates && evt.candidates[0];
                    const text = candidate && candidate.content && candidate.content.parts
                        && candidate.content.parts.map(p => p.text || '').join('');
                    if (text) { content += text; if (onChunk) onChunk(text); }
                    if (evt.usageMetadata) usage = normalizeUsage({
                        promptTokenCount: evt.usageMetadata.promptTokenCount,
                        candidatesTokenCount: evt.usageMetadata.candidatesTokenCount,
                        totalTokenCount: evt.usageMetadata.totalTokenCount,
                    });
                }
            }
            if (buffer.trim().startsWith('data:')) {
                const payload = buffer.trim().slice(5).trim();
                if (payload) {
                    try {
                        const evt = JSON.parse(payload), candidate = evt.candidates && evt.candidates[0];
                        const text = candidate && candidate.content && candidate.content.parts && candidate.content.parts.map(p => p.text || '').join('');
                        if (text) { content += text; if (onChunk) onChunk(text); }
                        if (evt.usageMetadata) usage = normalizeUsage({ promptTokenCount: evt.usageMetadata.promptTokenCount, candidatesTokenCount: evt.usageMetadata.candidatesTokenCount, totalTokenCount: evt.usageMetadata.totalTokenCount });
                    } catch { /* ignore malformed trailing frame */ }
                }
            }
            if (!content) { const error = new Error('empty completion (Gemini returned nothing)'); error.code = 'EMPTY_RESPONSE'; throw error; }
            return { content, usage, model, responseId: null };
        } catch (err) {
            if (err && err.name === 'AbortError') throw err;
            lastErr = err; if (!lastErr.code) lastErr.code = 'NETWORK_ERROR';
            if (attempt < maxRetries) await sleep(attempt * 5000, signal);
        }
    }
    throw lastErr;
}

function normalizeUsage(usage) {
    if (!usage) return null;
    const numeric = value => Number.isFinite(Number(value)) ? Number(value) : 0;
    const prompt = Math.max(0, numeric(usage.prompt_tokens ?? usage.input_tokens ?? usage.promptTokenCount ?? 0));
    const completion = Math.max(0, numeric(usage.completion_tokens ?? usage.output_tokens ?? usage.candidatesTokenCount ?? 0));
    const total = Math.max(prompt + completion, numeric(usage.total_tokens ?? usage.totalTokenCount ?? prompt + completion));
    return { ...usage, prompt_tokens: prompt, completion_tokens: completion, total_tokens: total,
        ...(usage.cost !== null && usage.cost !== '' && Number.isFinite(Number(usage.cost)) && Number(usage.cost) >= 0 ? { cost: Number(usage.cost) } : {}) };
}

async function chatForProvider(args) {
    if (args.providerType === 'gemini') return geminiChat(args);
    return chat(args);
}

function extractJson(text) {
    const fenced = text.match(/```(?:json)?\s*([\s\S]*?)```/i);
    const candidate = fenced ? fenced[1] : text;
    const start = candidate.search(/[\[{]/);
    if (start === -1) throw new Error('no JSON found in model reply');
    const open = candidate[start], close = open === '{' ? '}' : ']';
    let depth = 0, inStr = false, esc = false;
    for (let i = start; i < candidate.length; i++) {
        const c = candidate[i];
        if (esc) { esc = false; continue; }
        if (c === '\\') { esc = true; continue; }
        if (c === '"') { inStr = !inStr; continue; }
        if (inStr) continue;
        if (c === open) depth++;
        else if (c === close && --depth === 0) return JSON.parse(candidate.slice(start, i + 1));
    }
    throw new Error('unbalanced JSON in model reply');
}

module.exports = { chat, geminiChat, chatForProvider, extractJson, normalizeUsage };
