'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const editorRoot = __dirname;
const html = fs.readFileSync(path.join(editorRoot, 'tileset-atlas-workbench.html'), 'utf8');
const js = fs.readFileSync(path.join(editorRoot, 'js', 'tileset-atlas-workbench.js'), 'utf8');

test('experimental workbench script parses and is reachable from its static page', () => {
    assert.doesNotThrow(() => new vm.Script(js, { filename: 'tileset-atlas-workbench.js' }));
    assert.match(html, /js\/tileset-atlas-workbench\.js/);
    assert.match(html, /DISPOSABLE #547/);
});

test('picture-first workbench keeps the semantic role vocabulary primary', () => {
    for (const role of ['WALL', 'FLOOR', 'CEILING', 'DOOR', 'FEATURES']) {
        assert.match(js, new RegExp(`label:'${role}'`));
    }
    assert.match(js, /LEFT JOIN/);
    assert.match(js, /MAIN FACE/);
    assert.match(js, /RIGHT JOIN/);
    assert.match(js, /Warm emission/);
    assert.match(js, /Beside floor/);
});

test('save and preview delegate to existing Studio/runtime authorities', () => {
    assert.match(js, /fetch\('\/api\/tilesets'/);
    assert.match(js, /fetch\('\/api\/tilesets\/save'/);
    assert.match(js, /fetch\('\/api\/map-inspection'/);
    assert.match(js, /seed:547/);
    assert.match(js, /will not synthesize a speculative #694 Map shape/);
});

test('standalone PNG experiment does not fabricate per-variant source persistence', () => {
    assert.match(js, /one texture source/);
    assert.match(js, /will not fake per-variant source ownership/);
    assert.doesNotMatch(js, /surfaceTexture\s*=/);
    assert.doesNotMatch(js, /atlasId\s*=/);
});

test('dirty navigation preserves explicit save, discard, and cancel paths', () => {
    assert.match(js, /Save changes to/);
    assert.match(js, /Discard the unsaved changes/);
    assert.match(js, /Cancel keeps this Tileset open/);
    assert.match(js, /beforeunload/);
});
