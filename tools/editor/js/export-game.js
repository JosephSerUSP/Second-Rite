// --- EXPORT GAME WINDOW ---
// Client-side UI for the /export/* bridge in server.js, which in turn only
// spawns tools/export/export-game.js. This module contains no packaging
// knowledge: it names the target, shows what preflight said, and relays the
// exporter's own log. The opened Project is implicit because Studio has one
// Project root, not a second selectable content root.
(function() {
    let runStatus = 'idle';   // idle | running | success | failed | cancelled
    let logOffset = 0;        // next `from` byte for /export/status polling
    let pollTimer = null;
    let lastResult = null;    // { target, outputDir } of the last run
    let consolePinned = true;
    let preflightOk = false;

    const $ = id => document.getElementById(id);

    // The static markup predates #299. Remove its Campaign summary row rather
    // than letting a dead second-root concept survive as presentation-only UI.
    function removeRetiredCampaignSummary() {
        const value = $('ex-campaign');
        if (value && value.parentElement) value.parentElement.remove();
    }

    // ---------------------------------------------------------------
    // Open / close
    // ---------------------------------------------------------------
    window.openExportModal = async function() {
        removeRetiredCampaignSummary();
        $('export-modal').classList.add('active');

        // Re-sync the console the way the generator does: a mid-run reopen
        // refetches the whole log rather than showing a gap.
        $('ex-console').textContent = '';
        consolePinned = true;
        logOffset = 0;
        try {
            const res = await fetch(`${API_URL}/export/status?from=0`);
            applyStatusPayload(await res.json());
            if (runStatus === 'running' && !pollTimer) startPolling();
        } catch (e) { /* server offline; Export will surface it */ }

        await refreshExportPreflight();
    };

    window.closeExportModal = function() {
        // Never interrupts a run — polling continues headless.
        $('export-modal').classList.remove('active');
    };

    if (typeof ESCAPE_MODAL_CLOSERS !== 'undefined') {
        ESCAPE_MODAL_CLOSERS.unshift(['export-modal', () => closeExportModal()]);
    }

    window.exportTargetChanged = function() {
        refreshExportPreflight();
    };

    // ---------------------------------------------------------------
    // Preflight
    // ---------------------------------------------------------------
    window.refreshExportPreflight = async function() {
        const target = $('ex-target').value;
        let payload;
        try {
            const res = await fetch(`${API_URL}/export/preflight?target=${encodeURIComponent(target)}`);
            payload = await res.json();
        } catch (e) {
            preflightOk = false;
            renderChecks([{ label: 'Editor server', state: 'fail', detail: 'unreachable: ' + e.message }]);
            updateRunControls();
            return;
        }
        $('ex-output').textContent = payload.outputDir || 'dist/';

        // The one check the server cannot make: unsaved authored edits live
        // in this page, and the exporter only ever sees what is on disk.
        const dirty = typeof isDirty !== 'undefined' && isDirty;
        const checks = (payload.checks || []).concat([{
            label: 'No unsaved changes',
            state: dirty ? 'fail' : 'ok',
            detail: dirty
                ? 'the editor has unsaved authored changes — save the database first, or the export packages the last saved state'
                : 'disk matches the editor',
        }]);
        preflightOk = !checks.some(c => c.state === 'fail');
        renderChecks(checks, target);
        updateRunControls();
    };

    // The rendered target is stamped on the list so a caller (G6's capture
    // harness) can tell a finished re-check from the previous target's rows.
    function renderChecks(checks, target) {
        const host = $('ex-checks');
        host.innerHTML = '';
        if (target) host.setAttribute('data-target', target);
        else host.removeAttribute('data-target');
        const mark = { ok: '✓', fail: '✗', pending: '·' };
        checks.forEach(c => {
            const row = document.createElement('div');
            row.className = 'ex-check ex-check-' + c.state;
            row.innerHTML = `<span class="ex-check-mark">${mark[c.state] || '·'}</span>` +
                            `<span class="ex-check-label"></span><span class="ex-check-detail"></span>`;
            row.querySelector('.ex-check-label').textContent = c.label;
            row.querySelector('.ex-check-detail').textContent = c.detail || '';
            host.appendChild(row);
        });
    }

    // ---------------------------------------------------------------
    // Run lifecycle
    // ---------------------------------------------------------------
    window.startExport = async function() {
        if (runStatus === 'running' || !preflightOk) return;
        const payload = { target: $('ex-target').value };
        $('ex-console').textContent = '';
        logOffset = 0;
        consolePinned = true;
        try {
            const res = await fetch(`${API_URL}/export/start`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
            const result = await res.json();
            if (!res.ok || !result.success) {
                appendConsole(`! ${result.message || 'export failed to start'}\n`);
                setRunStatus('failed');
                return;
            }
            setRunStatus('running');
            startPolling();
        } catch (e) {
            appendConsole(`! connection failed: ${e.message}\n`);
            setRunStatus('failed');
        }
    };

    window.cancelExport = async function() {
        try {
            await fetch(`${API_URL}/export/cancel`, { method: 'POST' });
            appendConsole('\n> cancel requested\n');
        } catch (e) {
            appendConsole(`! cancel failed: ${e.message}\n`);
        }
    };

    window.openExportFolder = async function() {
        try {
            const res = await fetch(`${API_URL}/export/open-folder`, { method: 'POST' });
            const result = await res.json();
            if (!result.success) showToast('Could not open the export folder: ' + (result.message || 'unknown error'));
        } catch (e) {
            showToast('Could not open the export folder: ' + e.message);
        }
    };

    function startPolling() {
        stopPolling();
        pollTimer = setInterval(pollStatus, 700);
    }

    function stopPolling() {
        if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
    }

    async function pollStatus() {
        try {
            const res = await fetch(`${API_URL}/export/status?from=${logOffset}`);
            const st = await res.json();
            applyStatusPayload(st);
            if (st.status !== 'running') stopPolling();
        } catch (e) {
            stopPolling();
            appendConsole('\n! lost connection to the editor server\n');
            setRunStatus('failed');
        }
    }

    function applyStatusPayload(st) {
        if (typeof st.chunk === 'string' && st.chunk.length) appendConsole(st.chunk);
        if (typeof st.len === 'number') logOffset = st.len;
        if (st.result) lastResult = st.result;
        if (st.status && st.status !== runStatus) setRunStatus(st.status);
    }

    function setRunStatus(status) {
        runStatus = status;
        const chip = $('ex-status-chip');
        chip.textContent = status;
        chip.className = 'cg-chip cg-chip-' + status;
        updateRunControls();
        renderResultLine();
    }

    // The exporter's own success line is the authority on what was written;
    // the dialog just surfaces the last one it printed.
    function renderResultLine() {
        const line = $('ex-result-line');
        if (runStatus === 'success') {
            const text = $('ex-console').textContent;
            const match = /(?:EXPORT|STAGE) OK: (.+)/.exec(text);
            line.textContent = match ? match[1].trim() : (lastResult ? lastResult.outputDir : '');
            line.style.color = '#005500';
        } else if (runStatus === 'failed') {
            line.textContent = 'export failed — see the log below';
            line.style.color = '#aa0000';
        } else {
            line.textContent = '';
        }
    }

    function updateRunControls() {
        const running = runStatus === 'running';
        $('ex-export-btn').disabled = running || !preflightOk;
        $('ex-cancel-btn').style.display = running ? 'inline-flex' : 'none';
        $('ex-open-btn').disabled = runStatus !== 'success';
    }

    function appendConsole(text) {
        const con = $('ex-console');
        con.textContent += text;
        if (con.textContent.length > 400000) con.textContent = con.textContent.slice(-300000);
        if (consolePinned) con.scrollTop = con.scrollHeight;
    }

    document.addEventListener('DOMContentLoaded', () => {
        removeRetiredCampaignSummary();
        const con = $('ex-console');
        if (!con) return;
        con.addEventListener('scroll', () => {
            consolePinned = con.scrollTop + con.clientHeight >= con.scrollHeight - 8;
        });
    });
})();
