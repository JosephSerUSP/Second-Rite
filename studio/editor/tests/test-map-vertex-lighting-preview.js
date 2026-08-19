'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const test = require('node:test');

const root = path.resolve(__dirname, '..', '..', '..');
const editor = fs.readFileSync(path.join(root, 'studio', 'editor', 'js', 'map-editor.js'), 'utf8');

test('map canvas renders vertex lighting as persistent surface shading', () => {
    const renderGridStart = editor.indexOf('function renderGridCells()');
    const lightingCall = editor.indexOf('renderVertexLighting(map);', renderGridStart);
    const semanticOverlayStart = editor.indexOf('// Generated semantic overlays', renderGridStart);

    assert.ok(editor.includes('function renderVertexLighting(map)'),
        'map editor needs a shared vertex-lighting render pass');
    assert.match(editor, /globalCompositeOperation\s*=\s*['"]multiply['"]/,
        'vertex lighting must modulate the map surface rather than wash over it');
    assert.ok(lightingCall > renderGridStart,
        'renderGridCells must apply vertex lighting');
    assert.ok(lightingCall < semanticOverlayStart,
        'vertex lighting must render before editor annotations so they remain legible');
    assert.doesNotMatch(editor,
        /rgba\(\$\{col\[0\]\},\$\{col\[1\]\},\$\{col\[2\]\},0\.6\)/,
        'legacy Light-layer-only translucent shading pass must stay removed');
});
