// #299/#369: the old AI generator writes campaign-shaped trees, which are no
// longer runnable/authored roots. Keep its Studio entry visibly unavailable
// until #369 makes it produce explicit fixture Projects; do not preserve a
// Campaign activation compatibility path in the meantime.
(function() {
    const migrationMessage = 'AI test-game generation is temporarily disabled while #369 migrates it to explicit fixture Projects. Campaign roots can no longer be activated or Test Played.';

    function disableLegacyControls() {
        const modal = document.getElementById('campaign-gen-modal');
        if (!modal) return;

        const activate = document.getElementById('cg-activate-btn');
        if (activate) activate.remove();
        const testPlay = document.getElementById('cg-testplay-btn');
        if (testPlay) testPlay.remove();
        const generate = document.getElementById('cg-generate-btn');
        if (generate) {
            generate.disabled = true;
            generate.title = migrationMessage;
        }
        const cancel = document.getElementById('cg-cancel-btn');
        if (cancel) cancel.style.display = 'none';

        const consoleEl = document.getElementById('cg-console');
        if (consoleEl) consoleEl.textContent = migrationMessage + '\n';
        const status = document.getElementById('cg-status-chip');
        if (status) {
            status.textContent = 'migration pending';
            status.className = 'cg-chip';
        }

        modal.querySelectorAll('input, select, textarea').forEach(el => { el.disabled = true; });
    }

    window.openCampaignGenModal = function() {
        const modal = document.getElementById('campaign-gen-modal');
        if (modal) modal.classList.add('active');
        disableLegacyControls();
    };

    window.closeCampaignGenModal = function() {
        const modal = document.getElementById('campaign-gen-modal');
        if (modal) modal.classList.remove('active');
    };

    // Inline handlers remain in the legacy markup until #369 replaces the
    // generator surface. They are deliberately inert, not compatibility APIs.
    window.validateCgName = () => false;
    window.cgInputsChanged = () => {};
    window.cgProviderChanged = () => {};
    window.cgRefilterModels = () => {};
    window.cgApplyAllModel = () => {};
    window.cgApplyAllModelText = () => {};
    window.cgToggleStageModels = () => {};
    window.startCampaignGen = () => { if (typeof showToast === 'function') showToast(migrationMessage); };
    window.cancelCampaignGen = () => {};

    if (typeof ESCAPE_MODAL_CLOSERS !== 'undefined') {
        ESCAPE_MODAL_CLOSERS.unshift(['campaign-gen-modal', () => closeCampaignGenModal()]);
    }

    document.addEventListener('DOMContentLoaded', disableLegacyControls);
})();
