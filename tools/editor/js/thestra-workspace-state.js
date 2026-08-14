(function (root, factory) {
    if (typeof module === 'object' && module.exports) module.exports = factory();
    else root.ThestraWorkspaceState = factory();
}(typeof self !== 'undefined' ? self : this, function () {
    'use strict';

    function transitionPlan(previousMode, nextMode, loadedMapIndex, currentMapIndex) {
        const enteringThree = nextMode !== 'legacy';
        const switchingCameras = previousMode !== 'legacy' && enteringThree;
        return {
            cameraOnly: switchingCameras && loadedMapIndex === currentMapIndex,
            reloadScene: enteringThree && (!switchingCameras || loadedMapIndex !== currentMapIndex)
        };
    }

    // The workspace can continue authoring semantically whether the optional
    // runtime bridge is absent, rejects this origin, or reports a compile
    // failure. Keep that rendered state deterministic; the detailed cause is
    // preserved as the toolbar status tooltip by the workspace host.
    function fallbackStatusLabel() { return 'runtime unavailable · fallback'; }

    return { transitionPlan, fallbackStatusLabel };
}));
