(function () {
    'use strict';

    const bridge = window.thestraStudio;
    if (!bridge) return;

    const surface = new URLSearchParams(window.location.search).get('surface') || 'main';
    window.thestraSurfaceKind = surface;

    let closeInFlight = false;
    function installCloseHandler(surfaceId, hostModalId) {
        bridge.onCloseRequest(async payload => {
            if (!payload || payload.surfaceId !== surfaceId) return;
            if (closeInFlight) return;
            closeInFlight = true;

            let allow = false;
            try {
                // Native editors can still host lightweight staged interactions.
                // Resolve those first through their existing close/discard
                // contract; declining a child prompt cancels the OS close too.
                if (typeof window.thestraPrepareForSurfaceClose === 'function'
                        && !window.thestraPrepareForSurfaceClose(hostModalId || null)) {
                    return;
                }

                const changed = typeof window.changedDbResourceNames === 'function'
                    ? window.changedDbResourceNames()
                    : [];
                if (changed.length === 0) {
                    allow = true;
                    return;
                }

                const action = await bridge.chooseCloseAction(surfaceId);
                if (action === 'discard') {
                    allow = true;
                } else if (action === 'save' && typeof saveData === 'function') {
                    allow = await saveData();
                }
            } catch (error) {
                console.error(`${surfaceId} close request failed:`, error);
                allow = false;
            } finally {
                closeInFlight = false;
                bridge.resolveCloseRequest(surfaceId, allow);
            }
        });
    }

    function openNativeSurface(surfaceId) {
        bridge.openSurface(surfaceId).catch(error => {
            console.error(`Failed to open ${surfaceId} surface:`, error);
            if (typeof showToast === 'function') {
                showToast(`Failed to open ${surfaceId} window: ${error.message}`);
            }
        });
    }

    // Electron main: preserve the existing toolbar/menu commands, but redirect
    // first-class editors to their registered native EditorSurfaces. Browser
    // hosting never loads this adapter and therefore keeps the DOM modal paths.
    if (surface === 'main') {
        window.openDatabaseModal = function () { openNativeSurface('database'); };
        window.openEngineModal = function () { openNativeSurface('engine'); };
        installCloseHandler('main', null);
        return;
    }

    const configs = {
        database: {
            bodyClass: 'thestra-surface-database',
            modalId: 'db-modal',
            title: 'Database - Thestra Studio',
            closeGlobal: 'closeDatabaseModal',
            mount(modal) {
                modal.classList.add('active');
            },
        },
        engine: {
            bodyClass: 'thestra-surface-engine',
            modalId: 'engine-modal',
            title: 'Engine Editor - Thestra Studio',
            closeGlobal: 'closeEngineModal',
            mount(modal) {
                if (typeof window.openEngineModal === 'function') {
                    window.openEngineModal();
                } else {
                    modal.classList.add('active');
                }
            },
        },
    };
    const config = configs[surface];
    if (!config) return;

    document.body.classList.add(config.bodyClass);
    document.title = config.title;

    const modal = document.getElementById(config.modalId);
    if (!modal) throw new Error(`${surface} surface requested but #${config.modalId} is missing`);
    modal.setAttribute('data-fixed-dialog', 'true');

    // In a native host, the editor's own Cancel/Escape semantics become a
    // native close request. The BrowserWindow close handshake decides whether
    // the renderer transaction can actually be destroyed.
    window[config.closeGlobal] = function () {
        return bridge.closeSurface(surface);
    };

    // Existing modal OK handlers start save asynchronously and immediately
    // close. Native hosting makes that lifecycle exact: await the scoped commit,
    // then request native close. Apply buttons remain ordinary in-place saves.
    const okButton = modal.querySelector('.dialog-footer .win98-btn-success');
    if (okButton) {
        okButton.onclick = async function () {
            if (typeof saveData !== 'function') return;
            const clean = await saveData();
            if (clean) bridge.closeSurface(surface);
        };
    }

    installCloseHandler(surface, config.modalId);

    const hostStyles = document.getElementById('thestra-surface-host-styles');
    if (!hostStyles) {
        throw new Error(`${surface} surface requested but host stylesheet is missing`);
    }

    let readySent = false;
    function signalSurfaceReady() {
        if (readySent) return;
        config.mount(modal);
        readySent = true;
        bridge.surfaceReady(surface).catch(error => {
            console.error(`Failed to show ${surface} surface:`, error);
        });
    }

    // The shared /data boot state predates the second native editor and keeps
    // its historical name for compatibility. Its semantics are Studio-wide:
    // authored data + editor initialization reached success or terminal-offline.
    const boot = window.thestraDatabaseBootState;
    if (boot && boot.done) {
        signalSurfaceReady();
    } else {
        window.addEventListener('thestra-database-boot-ready', signalSurfaceReady, { once: true });
    }
}());
