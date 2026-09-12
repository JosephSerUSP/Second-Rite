'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const test = require('node:test');

const ROOT = path.resolve(__dirname, '..', '..', '..');
const viewport = fs.readFileSync(path.join(ROOT, 'studio', 'editor', 'js', 'three-editor-viewport-base.js'), 'utf8');
const navigation = fs.readFileSync(path.join(ROOT, 'studio', 'editor', 'js', 'three-authoring-tools.js'), 'utf8');

test('projection and orientation are independent in the Three viewport', () => {
    assert.match(viewport, /function projectionName\(\)/);
    assert.match(viewport, /let orientation = 'user'/);
    assert.match(viewport, /function matchOrthographicToPerspective\(\)/,
        'Perspective -> Orthographic must preserve the current view transform/framing');
    assert.match(viewport, /function matchPerspectiveToOrthographic\(\)/,
        'Orthographic -> Perspective must preserve orientation/target/framing');
    assert.match(viewport, /prepareProjectionDestination\(nextMode\)/);
    assert.match(viewport, /setAxisView\(name\)/);
    assert.match(viewport, /orbitStep\(action\)/);
    assert.match(viewport, /oppositeView\(\)/);
    assert.match(navigation, /control\.enableRotate = !planar/,
        'the shared authoring navigator must keep non-planar scenes orbitable');
});

test('Blender-like mouse and numpad integration preserves authored left click', () => {
    assert.match(navigation, /control\.mouseButtons\.LEFT = null/,
        'left click remains owned by map authoring');
    assert.match(navigation, /control\.mouseButtons\.MIDDLE = THREE\.MOUSE\.PAN/,
        'middle drag must pan with the game camera on planar maps');
    assert.match(navigation, /event\.altKey && !planar \? THREE\.MOUSE\.ROTATE : THREE\.MOUSE\.PAN/,
        'Alt+middle may orbit only fully 3D maps');
    assert.match(viewport, /action === 'toggle-projection'[\s\S]*requestProjectionToggle\(\)/);
    assert.match(viewport, /\['front', 'back', 'right', 'left', 'top', 'bottom'\]/);
    assert.match(viewport, /\['orbit-down', 'orbit-left', 'orbit-right', 'orbit-up'\]/);
    assert.match(viewport, /action === 'opposite-view'/);
    assert.match(viewport, /offset\.x = -offset\.x;\s*offset\.z = -offset\.z;/,
        'opposite view in user orientation must preserve vertical elevation and world up');
    assert.match(viewport, /newPitch = Math\.min\(Math\.PI \/ 2 - 0\.001,\s*currentPitch \+ radians\)/,
        'orbit step pitch must clamp polar angles to prevent pole inversion');
    assert.match(viewport, /top\.zoom = Math\.max\(0\.001, baseHeight \/ Math\.max\(visibleHeight, 0\.001\)\)/,
        'selection framing must update orthographic zoom to fit selected object');
    assert.match(viewport, /function zoomStep\(action\)/,
        'zoomStep must drive discrete +/- viewport scaling');
    assert.match(viewport, /action === 'zoom-in' \|\| action === 'zoom-out'/,
        'onCameraKeyDown must dispatch zoomStep on +/- actions');
});

test('toolbar no longer presents Top and Orthographic as the same fact', () => {
    assert.match(viewport, /projectionOrthoButton\.textContent = 'Orthographic'/);
    assert.match(viewport, /orientation is independent/);
    assert.doesNotMatch(viewport, /Numpad 1: perspective|Numpad 7: top; Numpad 5: toggle/,
        'old hard Perspective/Top camera help must not survive');
});

test('unified Blender smoothview animation drives discrete viewport navigation', () => {
    assert.match(viewport, /function animateCameraTo\(/,
        'must provide unified smooth camera transitions');
    assert.match(viewport, /startQuaternion\.clone\(\)\.slerp\(endQuaternion,\s*eased\)/,
        'smoothview must slerp orientation on spherical orbit arc');
    assert.match(viewport, /controls\.target\.lerpVectors\(startTarget,\s*endTarget,\s*eased\)/,
        'smoothview must interpolate pivot target');
    assert.match(viewport, /prefers-reduced-motion/,
        'smoothview must respect OS reduced-motion preferences');
});
