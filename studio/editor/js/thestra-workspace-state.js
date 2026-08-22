(function (root, factory) {
    if (typeof module === 'object' && module.exports) module.exports = factory();
    else root.ThestraWorkspaceState = factory();
}(typeof self !== 'undefined' ? self : this, function () {
    'use strict';

    const MUTATION_PLANS = Object.freeze({
        topology: Object.freeze({
            semanticRefresh: true,
            bundleRefresh: true,
            clearBundleImmediately: true
        }),
        'event-move': Object.freeze({
            semanticRefresh: false,
            bundleRefresh: true,
            clearBundleImmediately: false
        }),
        'light-move': Object.freeze({
            semanticRefresh: false,
            bundleRefresh: true,
            clearBundleImmediately: false
        }),
        'light-property': Object.freeze({
            semanticRefresh: true,
            bundleRefresh: true,
            clearBundleImmediately: false
        }),
        'authoritative-property': Object.freeze({
            semanticRefresh: true,
            bundleRefresh: true,
            clearBundleImmediately: false
        })
    });

    function transitionPlan(previousMode, nextMode, loadedMapIndex, currentMapIndex) {
        const enteringThree = nextMode !== 'legacy';
        const switchingCameras = previousMode !== 'legacy' && enteringThree;
        return {
            cameraOnly: switchingCameras && loadedMapIndex === currentMapIndex,
            reloadScene: enteringThree && (!switchingCameras || loadedMapIndex !== currentMapIndex)
        };
    }

    function mutationPlan(kind) {
        const plan = MUTATION_PLANS[kind];
        if (!plan) throw new Error(`Unknown Thestra map mutation kind '${kind}'.`);
        return plan;
    }

    // Full map/inspection refreshes have two independently useful moments:
    // semantic geometry is available early, while runtime-authoritative geometry
    // catches up later. Capture/tests need to know when the LATEST full refresh
    // has reached that second moment. A token prevents an older async completion
    // from certifying a newer request as settled.
    function createReadiness() {
        let requested = 0;
        let settled = 0;
        return Object.freeze({
            begin() { requested += 1; return requested; },
            settle(token) {
                if (token === requested) settled = token;
                return requested > 0 && settled === requested;
            },
            isSettled() { return requested > 0 && settled === requested; },
            snapshot() { return { requested, settled }; }
        });
    }

    // The workspace can continue authoring semantically whether the optional
    // runtime bridge is absent, rejects this origin, or reports a compile
    // failure. Keep that rendered state deterministic; the detailed cause is
    // preserved as the toolbar status tooltip by the workspace host.
    function fallbackStatusLabel() { return 'runtime unavailable · fallback'; }

    return { transitionPlan, mutationPlan, fallbackStatusLabel, createReadiness };
}));