// Fixture Project generator window. Generated output is a disposable, ordinary
// Project at tmp/generated-projects/<name>/; it never changes Studio's open Project.
(function() {
    const $ = id => document.getElementById(id);
    const STAGES = ['outline', 'units', 'items', 'quests', 'maps', 'events', 'validate'];
    let runStatus = 'idle', runName = '', logOffset = 0, pollTimer = null, config = null, catalogue = null;

    function validName() { return /^[a-z0-9_]+$/.test($('cg-name').value); }
    function render() {
        const running = runStatus === 'running';
        const ready = runStatus === 'success' && runName;
        $('cg-status-chip').textContent = runStatus;
        $('cg-status-chip').className = 'cg-chip cg-chip-' + runStatus;
        $('cg-generate-btn').disabled = running || !validName() || !$('cg-pitch').value.trim();
        $('cg-cancel-btn').style.display = running ? 'inline-flex' : 'none';
        $('cg-testplay-btn').disabled = !ready;
        $('cg-success-hint').style.display = ready ? 'block' : 'none';
        if (ready) $('cg-walkthrough-path').textContent = `tmp/generated-projects/${runName}/WALKTHROUGH.md`;
    }
    function append(text) {
        const out = $('cg-console'); out.textContent += text;
        if (out.textContent.length > 400000) out.textContent = out.textContent.slice(-300000);
        out.scrollTop = out.scrollHeight;
    }
    function strip() {
        $('cg-stage-strip').innerHTML = STAGES.map(stage => `<span class="cg-stage">${stage}</span>`).join('<span class="cg-stage-arrow">›</span>');
    }
    function provider() { return [...document.getElementsByName('cg-provider')].find(x => x.checked).value; }
    window.validateCgName = function() {
        const error = $('cg-name-error'); error.style.display = $('cg-name').value && !validName() ? 'block' : 'none'; render(); return validName();
    };
    window.cgInputsChanged = render;
    window.cgProviderChanged = function() {
        const active = provider(); ['openrouter', 'deepseek', 'gemini'].forEach(name => { $(`cg-api-key-${name}-row`).style.display = name === active ? 'flex' : 'none'; });
    };
    function modelOptions(selected) {
        const query = ($('cg-model-filter').value || '').toLowerCase();
        const available = (catalogue || []).filter(model => !query || `${model.id} ${model.name || ''}`.toLowerCase().includes(query));
        return `<option value="">(stage default)</option>${available.slice(0, 200).map(model => `<option value="${model.id}"${model.id === selected ? ' selected' : ''}>${model.name || model.id} — ${model.id}</option>`).join('')}`;
    }
    function renderModels() {
        const prior = {};
        STAGES.slice(0, -1).forEach(stage => { const input = $(`cg-model-${stage}`); if (input) prior[stage] = input.value; });
        const rows = STAGES.slice(0, -1).map(stage => {
            const fallback = config && config.stages && config.stages[stage] && config.stages[stage].model;
            return `<div class="cg-model-row"><label>${stage}</label><select id="cg-model-${stage}" class="win98-select" style="flex:1; min-width:0;">${modelOptions(prior[stage] || '')}</select><span class="field-help">${fallback || ''}</span></div>`;
        }).join('');
        $('cg-models-body').innerHTML = `<div class="cg-model-row"><label>All stages</label><select id="cg-model-all" class="win98-select" style="flex:1; min-width:0;" onchange="cgApplyAllModel()">${modelOptions('')}</select></div><div id="cg-stage-models" style="display:none;">${rows}</div>`;
    }
    window.cgRefilterModels = function() { renderModels(); };
    window.cgApplyAllModel = function() { const value = $('cg-model-all').value; STAGES.slice(0, -1).forEach(stage => { $(`cg-model-${stage}`).value = value; }); };
    window.cgApplyAllModelText = window.cgToggleStageModels = function() { const box = $('cg-stage-models'); box.style.display = $('cg-models-expand').checked ? 'block' : 'none'; };
    async function loadModels() {
        if (!config) { try { config = await (await fetch(`${API_URL}/campaign-gen/config`)).json(); } catch {} }
        if (!catalogue) { try { catalogue = await (await fetch(`${API_URL}/campaign-gen/models`)).json(); } catch { catalogue = []; } }
        renderModels();
    }
    window.openCampaignGenModal = async function() { $('campaign-gen-modal').classList.add('active'); strip(); render(); await loadModels(); };
    window.closeCampaignGenModal = function() { $('campaign-gen-modal').classList.remove('active'); };
    if (typeof ESCAPE_MODAL_CLOSERS !== 'undefined') ESCAPE_MODAL_CLOSERS.unshift(['campaign-gen-modal', () => closeCampaignGenModal()]);
    function stopPoll() { if (pollTimer) { clearInterval(pollTimer); pollTimer = null; } }
    async function poll() {
        try {
            const reply = await fetch(`${API_URL}/campaign-gen/status?from=${logOffset}`); const state = await reply.json();
            if (state.chunk) append(state.chunk); if (Number.isInteger(state.len)) logOffset = state.len;
            if (state.status !== 'running') { runStatus = state.status; stopPoll(); } render();
        } catch (error) { append(`! lost generator connection: ${error.message}\n`); runStatus = 'failed'; stopPoll(); render(); }
    }
    window.startCampaignGen = async function() {
        if (!validName() || !$('cg-pitch').value.trim() || runStatus === 'running') return;
        const selected = provider(), key = $(`cg-api-key-${selected}`).value.trim();
        const payload = { name: $('cg-name').value, pitch: $('cg-pitch').value.trim(), provider: selected };
        if (key) payload[`${selected}ApiKey`] = key;
        const models = {};
        STAGES.slice(0, -1).forEach(stage => { const value = $(`cg-model-${stage}`).value; if (value) models[stage] = value; });
        if (Object.keys(models).length) payload.models = models;
        const stage = $('cg-stage-select').value; if (stage) payload.stage = stage;
        if ($('cg-resume').checked) payload.resume = true;
        const response = await fetch(`${API_URL}/campaign-gen/start`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
        const result = await response.json(); if (!response.ok || !result.success) { append(`! ${result.message || 'start failed'}\n`); return; }
        runName = payload.name; runStatus = 'running'; logOffset = 0; $('cg-console').textContent = `> generating tmp/generated-projects/${runName}/\n`; render(); stopPoll(); pollTimer = setInterval(poll, 700); poll();
    };
    window.cancelCampaignGen = async function() { await fetch(`${API_URL}/campaign-gen/cancel`, { method: 'POST' }); };
    window.testGeneratedFixtureProject = async function() {
        if (!runName) return;
        const response = await fetch(`${API_URL}/campaign-gen/test-play`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: runName }) });
        const result = await response.json(); if (!response.ok || !result.success) append(`! Test Play failed: ${result.message || 'unknown error'}\n`);
    };
    document.addEventListener('DOMContentLoaded', () => { strip(); render(); });
})();
