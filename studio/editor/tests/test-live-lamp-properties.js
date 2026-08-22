'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const test = require('node:test');

const ROOT = path.resolve(__dirname, '..', '..', '..');

function source(relative) {
    return fs.readFileSync(path.join(ROOT, relative), 'utf8');
}

test('legacy Lamp property controls enter the frame-local light-property invalidation seam', () => {
    const lightingUi = source('studio/editor/js/vertex-shading.js');
    const workspace = source('studio/editor/js/thestra-editor-workspace.js');

    for (const id of ['lamp-color', 'lamp-radius', 'lamp-falloff', 'lamp-material']) {
        assert.match(lightingUi, new RegExp(`['\"]${id}['\"]`), `${id} must be bridged`);
    }
    assert.match(lightingUi, /light-object-live-property-proxy/,
        'bounded legacy Lamp UI must reuse the workspace light-property mutation contract');
    assert.match(lightingUi, /dispatchEvent\(new Event\('input', \{ bubbles: true \}\)\)/,
        'Lamp input must invalidate live 3D lighting immediately');
    assert.match(workspace, /id\.startsWith\('light-object-'\)[\s\S]*scheduleMutation\('light-property'\)/,
        'workspace must consume the existing light-property invalidation contract');
});

test('normal Light authoring no longer exposes explicit Bake Lighting workflow', () => {
    const lightingUi = source('studio/editor/js/vertex-shading.js');

    assert.match(lightingUi, /button\[onclick\*="bakeMapLighting"\]/,
        'environment-lighting ownership should locate the obsolete legacy action');
    assert.match(lightingUi, /if \(bake\) bake\.remove\(\)/,
        'obsolete Bake Lighting action must be removed from the artist-facing palette');
});
