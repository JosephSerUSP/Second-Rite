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

    return { transitionPlan };
}));
