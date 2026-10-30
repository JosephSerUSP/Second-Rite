(function (root, factory) {
    if (typeof module === 'object' && module.exports) module.exports = factory();
    else root.ThestraMapInspectionRequest = factory();
}(typeof self !== 'undefined' ? self : this, function () {
    'use strict';

    // #833: the request had no deadline, so a bridge that did not answer left
    // the editor on "Resolving through the real engine..." forever -- no error,
    // no retry, and a second click stacking another request behind the first.
    //
    // The bound is derived from the server's, not chosen: runtime-bridge-server
    // gives the Map authority BRIDGE_TIMEOUT_MS to answer, so a client that
    // gives up sooner would abandon a request the system is still legitimately
    // performing. That is exactly the bug #815 turned out to be, on the harness
    // side; repeating it here would be worse, because the user cannot rerun.
    //
    // tests/test-map-inspection-request.js fails if this stops exceeding
    // BRIDGE_TIMEOUT_MS, so the two cannot drift apart silently.
    const BRIDGE_GRACE_MS = 15000;
    const DEFAULT_TIMEOUT_MS = 60000 + BRIDGE_GRACE_MS;

    function createInspectionRequester(options) {
        const settings = options || {};
        const fetchImpl = settings.fetch;
        const timeoutMs = settings.timeoutMs || DEFAULT_TIMEOUT_MS;
        const createController = settings.createController
            || (() => (typeof AbortController === 'function' ? new AbortController() : null));
        const setTimer = settings.setTimeout || setTimeout;
        const clearTimer = settings.clearTimeout || clearTimeout;
        let inFlight = null;

        // A stacked request is not a retry. Without this, a user clicking
        // Resolve during a slow request starts a second one, and whichever
        // lands last wins -- which can be the older answer.
        function busy() {
            return inFlight !== null;
        }

        async function request(url, body) {
            if (inFlight) throw new Error('a Map inspection request is already in flight');
            const controller = createController();
            let timer = null;
            // The deadline is RACED rather than left to the abort signal.
            // Aborting is what actually cancels the request, but relying on
            // fetch to reject in response makes the guarantee only as good
            // as that behaviour. Racing means the caller always hears back.
            const deadline = new Promise((_, reject) => {
                timer = setTimer(() => {
                    if (controller) controller.abort();
                    reject(new Error(
                        'the runtime bridge did not answer within '
                        + Math.round(timeoutMs / 1000) + 's',
                    ));
                }, timeoutMs);
            });
            inFlight = { controller, timer };
            try {
                const init = {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(body),
                };
                if (controller) init.signal = controller.signal;
                const attempt = fetchImpl(url, init);
                // A late rejection from the loser of the race is expected
                // once aborted, and must not surface as an unhandled one.
                if (attempt && typeof attempt.catch === 'function') attempt.catch(() => {});
                return await Promise.race([attempt, deadline]);
            } finally {
                clearTimer(timer);
                inFlight = null;
            }
        }

        return { request, busy, timeoutMs };
    }

    return { createInspectionRequester, DEFAULT_TIMEOUT_MS, BRIDGE_GRACE_MS };
}));
