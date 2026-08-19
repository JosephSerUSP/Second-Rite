(function () {
    'use strict';

    function installBrowserTilesetSaveBoundary() {
        if (typeof document === 'undefined' || typeof document.getElementById !== 'function') return;
        const modal = document.getElementById('tileset-studio-modal');
        const okButton = modal && modal.querySelector('.dialog-footer .win98-btn-success');
        if (!okButton || typeof window.saveTilesetStudioData !== 'function') return;
        okButton.onclick = async function () {
            const saved = await window.saveTilesetStudioData();
            if (saved && typeof window.closeTilesetStudioModal === 'function') {
                window.closeTilesetStudioModal();
            }
        };
    }

    const bridge = window.thestraStudio;
    if (!bridge) {
        installBrowserTilesetSaveBoundary();
        return;
    }

    const surface = new URLSearchParams(window.location.search).get('surface') || 'main';
    window.thestraSurfaceKind = surface;

    function surfaceTransaction(surfaceId) {
        if (surfaceId === 'tileset') return window.thestraTilesetStudioTransaction || null;
        return null;
    }

    function surfaceIsDirty(surfaceId) {
        const transaction = surfaceTransaction(surfaceId);
        if (transaction && typeof transaction.isDirty === 'function') return !!transaction.isDirty();
        const changed = typeof window.changedDbResourceNames === 'function'
            ? window.changedDbResourceNames()
            : [];
        return changed.length > 0;
    }

    async function saveSurface(surfaceId) {
        const transaction = surfaceTransaction(surfaceId);
        if (transaction && typeof transaction.save === 'function') return !!(await transaction.save());
        if (typeof saveData === 'function') return !!(await saveData());
        return false;
    }

    function discardSurface(surfaceId) {
        const transaction = surfaceTransaction(surfaceId);
        if (transaction && typeof transaction.discard === 'function') return transaction.discard() !== false;
        return true;
    }

    let closeInFlight = false;
    function installCloseHandler(surfaceId, hostModalId) {
        bridge.onCloseRequest(async payload => {
            if (!payload || payload.surfaceId !== surfaceId) return;
            if (closeInFlight) return;
            closeInFlight = true;

            let allow = false;
            try {
                if (typeof window.thestraPrepareForSurfaceClose === 'function'
                        && !window.thestraPrepareForSurfaceClose(hostModalId || null)) {
                    return;
                }

                if (!surfaceIsDirty(surfaceId)) {
                    allow = true;
                    return;
                }

                const action = await bridge.chooseCloseAction(surfaceId);
                if (action === 'discard') {
                    allow = discardSurface(surfaceId);
                } else if (action === 'save') {
                    allow = await saveSurface(surfaceId);
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

    function installNativeEscapeBoundary(hostModalId) {
        const hostOwner = `dialog:${hostModalId}`;
        window.addEventListener('keydown', event => {
            if (event.key !== 'Escape') return;
            const interactionState = window.ThestraInteractionState;
            const snapshot = interactionState && typeof interactionState.snapshot === 'function'
                ? interactionState.snapshot()
                : null;
            const owners = snapshot && Array.isArray(snapshot.owners) ? snapshot.owners : [];
            const hasNestedDialog = owners.some(owner =>
                typeof owner === 'string' && owner.startsWith('dialog:') && owner !== hostOwner
            );
            if (hasNestedDialog) return;

            event.preventDefault();
            event.stopImmediatePropagation();
        }, true);
    }

    if (surface === 'main') {
        window.openDatabaseModal = function () { openNativeSurface('database'); };
        window.openEngineModal = function () { openNativeSurface('engine'); };
        window.openTilesetStudioModal = function () { openNativeSurface('tileset'); };
        window.openTilesetStudioForCurrentMap = function () { openNativeSurface('tileset'); };
        installCloseHandler('main', null);
        return;
    }

    const originalOpenEngine = window.openEngineModal;
    const originalOpenTileset = window.openTilesetStudioModal;
    const configs = {
        database: {
            bodyClass: 'thestra-surface-database',
            modalId: 'db-modal',
            title: 'Database - Thestra Studio',
            closeGlobal: 'closeDatabaseModal',
            mount(modal) { modal.classList.add('active'); },
        },
        engine: {
            bodyClass: 'thestra-surface-engine',
            modalId: 'engine-modal',
            title: 'Engine Editor - Thestra Studio',
            closeGlobal: 'closeEngineModal',
            mount(modal) {
                if (typeof originalOpenEngine === 'function') return originalOpenEngine();
                modal.classList.add('active');
            },
        },
        tileset: {
            bodyClass: 'thestra-surface-tileset',
            modalId: 'tileset-studio-modal',
            title: 'Tileset Studio - Thestra Studio',
            closeGlobal: 'closeTilesetStudioModal',
            mount(modal) {
                if (typeof originalOpenTileset === 'function') return originalOpenTileset();
                modal.style.display = 'flex';
                return undefined;
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

    window[config.closeGlobal] = function () {
        return bridge.closeSurface(surface);
    };

    const okButton = modal.querySelector('.dialog-footer .win98-btn-success');
    if (okButton) {
        okButton.onclick = async function () {
            const clean = await saveSurface(surface);
            if (clean) bridge.closeSurface(surface);
        };
    }

    installCloseHandler(surface, config.modalId);
    installNativeEscapeBoundary(config.modalId);

    const hostStyles = document.getElementById('thestra-surface-host-styles');
    if (!hostStyles) {
        throw new Error(`${surface} surface requested but host stylesheet is missing`);
    }

    let readyStarted = false;
    function finishSurfaceReady() {
        bridge.surfaceReady(surface).catch(error => {
            readyStarted = false;
            console.error(`Failed to show ${surface} surface:`, error);
        });
    }

    function signalSurfaceReady() {
        if (readyStarted) return;
        readyStarted = true;
        let mounted;
        try {
            mounted = config.mount(modal);
        } catch (error) {
            readyStarted = false;
            console.error(`Failed to mount ${surface} surface:`, error);
            return;
        }

        // Database and Engine mount synchronously; preserve their established
        // readiness timing. Tileset's real editor load returns a Promise, so its
        // BrowserWindow remains hidden until /api/tilesets initialization ends.
        if (mounted && typeof mounted.then === 'function') {
            mounted.then(finishSurfaceReady).catch(error => {
                readyStarted = false;
                console.error(`Failed to mount ${surface} surface:`, error);
            });
            return;
        }
        finishSurfaceReady();
    }

    const boot = window.thestraDatabaseBootState;
    if (boot && boot.done) {
        signalSurfaceReady();
    } else {
        window.addEventListener('thestra-database-boot-ready', signalSurfaceReady, { once: true });
    }
}());
