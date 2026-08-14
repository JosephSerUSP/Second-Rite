'use strict';

const assert = require('assert');
const WorkspaceState = require('../js/thestra-workspace-state.js');

(function testDirectCameraSwitchPreservesLoadedWorkspace() {
    assert.deepStrictEqual(
        WorkspaceState.transitionPlan('perspective', 'top', 2, 2),
        { cameraOnly: true, reloadScene: false }
    );
    assert.deepStrictEqual(
        WorkspaceState.transitionPlan('top', 'perspective', 2, 2),
        { cameraOnly: true, reloadScene: false }
    );
})();

(function testEnteringThreeRefreshesAChangedLegacyMap() {
    assert.deepStrictEqual(
        WorkspaceState.transitionPlan('legacy', 'perspective', 2, 3),
        { cameraOnly: false, reloadScene: true }
    );
})();

(function testSwitchingCamerasRefreshesOnlyWhenMapChanged() {
    assert.deepStrictEqual(
        WorkspaceState.transitionPlan('perspective', 'top', 2, 3),
        { cameraOnly: false, reloadScene: true }
    );
})();

console.log('Thestra workspace transition tests OK');
