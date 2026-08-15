(function () {
    'use strict';

    const bridge = window.thestraStudio;
    if (!bridge) return;

    const surface = new URLSearchParams(window.location.search).get('surface') || 'main';
    window.thestraSurfaceKind = surface;

    // Electron main: preserve the existing toolbar/menu commands, but redirect
    // their Database entrypoint to the registered native EditorSurface. Browser
    // hosting never loads this adapter and therefore keeps the DOM modal path.
    if (surface === 'main') {
        window.openDatabaseModal = function () {
            bridge.openSurface('database').catch(error => {
                console.error('Failed to open Database surface:', error);
                if (typeof showToast === 'function') showToast('Failed to open Database window: ' + error.message);
            });
        };
        return;
    }

    if (surface !== 'database') return;

    document.body.classList.add('thestra-surface-database');
    document.title = 'Database - Thestra Studio';

    const modal = document.getElementById('db-modal');
    if (!modal) throw new Error('Database surface requested but #db-modal is missing');
    modal.setAttribute('data-fixed-dialog', 'true');
    modal.classList.add('active');

    // In a native host, Database's own Cancel/Escape semantics become a native
    // close request. The BrowserWindow close handshake below decides whether it
    // can actually be destroyed.
    window.closeDatabaseModal = function () {
        return bridge.closeSurface('database');
    };

    // The modal's legacy OK handler starts an async save and immediately closes.
    // Native hosting can make that lifecycle exact without changing the shared
    // Database markup: await the actual authored transaction, then request close.
    const okButton = modal.querySelector('.dialog-footer .win98-btn-success');
    if (okButton) {
        okButton.onclick = async function () {
            if (typeof saveData !== 'function') return;
            const clean = await saveData();
            if (clean) bridge.closeSurface('database');
        };
    }

    let closeInFlight = false;
    bridge.onCloseRequest(async payload => {
        if (!payload || payload.surfaceId !== 'database') return;
        if (closeInFlight) {
            bridge.resolveCloseRequest('database', false);
            return;
        }
        closeInFlight = true;

        let allow = false;
        try {
            // A native editor can still contain lightweight staged dialogs.
            // Give those their normal discard/cancel behavior first; refusing a
            // child-dialog close also refuses Alt+F4 for the host window.
            if (typeof window.thestraPrepareForSurfaceClose === 'function'
                    && !window.thestraPrepareForSurfaceClose('db-modal')) {
                return;
            }

            const changed = typeof window.changedDbResourceNames === 'function'
                ? window.changedDbResourceNames()
                : [];
            if (changed.length === 0) {
                allow = true;
                return;
            }

            const action = await bridge.chooseCloseAction('database');
            if (action === 'discard') {
                allow = true;
            } else if (action === 'save' && typeof saveData === 'function') {
                allow = await saveData();
            }
        } catch (error) {
            console.error('Database close request failed:', error);
            allow = false;
        } finally {
            closeInFlight = false;
            bridge.resolveCloseRequest('database', allow);
        }
    });

    // Preload injects this adapter only after surface-host.css has positively
    // loaded. Reveal the native window only after the real Studio /data boot has
    // also completed, rather than depending on Electron's global page-loading
    // state (which can remain active while project preview assets stream).
    const hostStyles = document.getElementById('thestra-surface-host-styles');
    if (!hostStyles) {
        throw new Error('Database surface requested but host stylesheet is missing');
    }

    let readySent = false;
    function signalSurfaceReady() {
        if (readySent) return;
        readySent = true;
        bridge.surfaceReady('database').catch(error => {
            console.error('Failed to show Database surface:', error);
        });
    }

    const boot = window.thestraDatabaseBootState;
    if (boot && boot.done) {
        signalSurfaceReady();
    } else {
        window.addEventListener('thestra-database-boot-ready', signalSurfaceReady, { once: true });
    }
}());
