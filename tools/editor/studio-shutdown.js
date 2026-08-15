'use strict';

function createStudioShutdownCoordinator(options) {
    const windowManager = options.windowManager;
    const studioIpc = options.studioIpc;
    const secondarySurfaces = Array.from(options.secondarySurfaces || []);
    const logger = options.logger || console;
    let inFlight = null;

    async function attempt(mainWindow) {
        // Resolve secondary working copies first. If one cancels its native
        // Save/Discard/Cancel handshake, main remains alive and no later close
        // decision is requested. A surface that saves/discards and closes before
        // a later cancellation is safe: no authored work is silently lost.
        for (const surfaceId of secondarySurfaces) {
            if (!windowManager.has(surfaceId)) continue;
            const closed = await windowManager.closeAndWait(surfaceId);
            if (!closed) return false;
        }

        // Main owns the remaining Project-wide working copy and staged DOM
        // interactions. Its renderer resolves those through the same bounded
        // close-request channel only after all secondaries are settled.
        return new Promise(resolve => {
            studioIpc.requestClose('main', mainWindow, resolve);
        });
    }

    function requestMainClose(mainWindow, decide) {
        if (!inFlight) {
            inFlight = attempt(mainWindow)
                .catch(error => {
                    logger.error('Studio shutdown coordination failed:', error);
                    return false;
                })
                .finally(() => {
                    inFlight = null;
                });
        }
        inFlight.then(result => decide(!!result));
    }

    return Object.freeze({ requestMainClose });
}

module.exports = { createStudioShutdownCoordinator };
