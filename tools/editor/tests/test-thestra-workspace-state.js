'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const WorkspaceState = require('../js/thestra-workspace-state.js');
const ROOT = path.resolve(__dirname, '..', '..', '..');

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

(function testMutationInvalidationIsExplicit() {
    assert.deepStrictEqual(WorkspaceState.mutationPlan('topology'), {
        semanticRefresh: true,
        bundleRefresh: true,
        clearBundleImmediately: true
    });
    assert.deepStrictEqual(WorkspaceState.mutationPlan('event-move'), {
        semanticRefresh: false,
        bundleRefresh: true,
        clearBundleImmediately: false
    });
    assert.deepStrictEqual(WorkspaceState.mutationPlan('light-move'), {
        semanticRefresh: false,
        bundleRefresh: true,
        clearBundleImmediately: false
    });
    assert.deepStrictEqual(WorkspaceState.mutationPlan('light-property'), {
        semanticRefresh: true,
        bundleRefresh: true,
        clearBundleImmediately: false
    });
    assert.deepStrictEqual(WorkspaceState.mutationPlan('authoritative-property'), {
        semanticRefresh: true,
        bundleRefresh: true,
        clearBundleImmediately: false
    });
    assert.throws(() => WorkspaceState.mutationPlan('mystery'), /Unknown Thestra map mutation kind/);
})();

(function testWorkspaceUsesFrameLocalFeedbackBeforeBackgroundAuthoritySync() {
    const source = fs.readFileSync(
        path.join(ROOT, 'tools', 'editor', 'js', 'thestra-editor-workspace.js'), 'utf8'
    );
    assert.match(source, /onPaintCell[\s\S]*handleMutationResult\([\s\S]*'topology'/,
        'map painting must be classified as topology');
    assert.match(source, /onMoveEvent[\s\S]*'event-move'/,
        'event movement must use its explicit background-sync class');
    assert.match(source, /onMoveLight[\s\S]*'light-move'/,
        'light movement must use its explicit background-sync class');
    assert.match(source, /light-object-[\s\S]*scheduleMutation\('light-property'\)/,
        'light inspector edits must use their explicit background-sync class');
    assert.match(source, /clearBundleImmediately[\s\S]*setRenderableBundle\(null\)/,
        'topology edits must expose semantic fallback before runtime compilation completes');
    assert.match(source, /bundleSerial \+= 1[\s\S]*scheduleBundleRefresh\(\)/,
        'a newer authored mutation must invalidate an in-flight bundle before debounce starts');
    assert.match(source, /refreshAuthoritativeBundle\(\{ clearFirst: false \}\)\.catch\(console\.error\)/,
        'refreshAll must kick runtime synchronization asynchronously after semantic rendering');
})();

(function testFallbackStatusDoesNotDependOnBridgeAvailability() {
    assert.strictEqual(WorkspaceState.fallbackStatusLabel(), 'runtime unavailable · fallback');
})();

console.log('Thestra workspace transition/invalidation tests OK');