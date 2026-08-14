// Shared, ephemeral dragging for editor dialogs.  A dialog's normal position
// remains the overlay's centred layout: moving it only adds inline geometry
// for the current open instance, and that geometry is cleared on close/open.
(function () {
    'use strict';

    const FIXED_DIALOG_SELECTOR = '[data-fixed-dialog]';
    const INTERACTIVE_SELECTOR = 'button, input, select, textarea, a, [data-no-window-drag]';

    function resetPosition(dialog) {
        dialog.style.position = '';
        dialog.style.left = '';
        dialog.style.top = '';
        dialog.style.margin = '';
    }

    function clamp(value, minimum, maximum) {
        return Math.min(Math.max(value, minimum), Math.max(minimum, maximum));
    }

    function makeDraggable(overlay) {
        if (overlay.matches(FIXED_DIALOG_SELECTOR)) return;
        const dialog = overlay.querySelector(':scope > .window');
        if (!dialog || dialog.dataset.dragEnabled === 'true') return;
        dialog.dataset.dragEnabled = 'true';

        const titleBar = dialog.querySelector(':scope > .title-bar');
        if (!titleBar) return;

        titleBar.addEventListener('pointerdown', event => {
            if (event.button !== 0 || event.target.closest(INTERACTIVE_SELECTOR)) return;

            const rect = dialog.getBoundingClientRect();
            const offsetX = event.clientX - rect.left;
            const offsetY = event.clientY - rect.top;
            dialog.style.position = 'fixed';
            dialog.style.left = `${rect.left}px`;
            dialog.style.top = `${rect.top}px`;
            dialog.style.margin = '0';

            function move(moveEvent) {
                const width = dialog.getBoundingClientRect().width;
                const height = dialog.getBoundingClientRect().height;
                // Keep the full title bar reachable; an oversized body may
                // still extend below the viewport, as it can when resized.
                const left = clamp(moveEvent.clientX - offsetX, 0, window.innerWidth - width);
                const top = clamp(moveEvent.clientY - offsetY, 0, window.innerHeight - Math.min(height, titleBar.offsetHeight));
                dialog.style.left = `${left}px`;
                dialog.style.top = `${top}px`;
            }

            function stop() {
                window.removeEventListener('pointermove', move);
                window.removeEventListener('pointerup', stop);
                window.removeEventListener('pointercancel', stop);
            }

            window.addEventListener('pointermove', move);
            window.addEventListener('pointerup', stop, { once: true });
            window.addEventListener('pointercancel', stop, { once: true });
            event.preventDefault();
        });
    }

    function initialise() {
        document.querySelectorAll('.modal-overlay').forEach(makeDraggable);

        // Dialogs are already opened and closed by many independently owned
        // editor modules.  Watching their existing `active` convention keeps
        // this behavior central and ensures positions are never remembered.
        new MutationObserver(records => {
            records.forEach(record => {
                const overlay = record.target;
                if (!(overlay instanceof HTMLElement) || !overlay.classList.contains('modal-overlay')) return;
                makeDraggable(overlay);
                if (overlay.classList.contains('active')) {
                    const dialog = overlay.querySelector(':scope > .window');
                    if (dialog) resetPosition(dialog);
                }
            });
        }).observe(document.body, {
            subtree: true,
            attributes: true,
            attributeFilter: ['class']
        });
    }

    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initialise, { once: true });
    else initialise();
}());
