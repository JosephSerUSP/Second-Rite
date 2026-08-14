'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const test = require('node:test');

const ROOT = path.resolve(__dirname, '..', '..', '..');
const viewport = fs.readFileSync(path.join(ROOT, 'tools', 'editor', 'js', 'three-editor-viewport.js'), 'utf8');

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
    assert.match(viewport, /topControls\.enableRotate = true/,
        'orthographic projection must remain orbitable into User Orthographic views');
});

test('Blender-like mouse and numpad integration preserves authored left click', () => {
    assert.match(viewport, /controls\.mouseButtons\.LEFT = null/,
        'left click remains owned by map authoring');
    assert.match(viewport, /controls\.mouseButtons\.MIDDLE = THREE\.MOUSE\.ROTATE/,
        'MMB must orbit like Blender');
    assert.match(viewport, /action === 'toggle-projection'[\s\S]*requestProjectionToggle\(\)/);
    assert.match(viewport, /\['front', 'back', 'right', 'left', 'top', 'bottom'\]/);
    assert.match(viewport, /\['orbit-down', 'orbit-left', 'orbit-right', 'orbit-up'\]/);
    assert.match(viewport, /action === 'opposite-view'/);
});

test('toolbar no longer presents Top and Orthographic as the same fact', () => {
    assert.match(viewport, /projectionOrthoButton\.textContent = 'Orthographic'/);
    assert.match(viewport, /orientation is independent/);
    assert.doesNotMatch(viewport, /Numpad 1: perspective|Numpad 7: top; Numpad 5: toggle/,
        'old hard Perspective/Top camera help must not survive');
});
