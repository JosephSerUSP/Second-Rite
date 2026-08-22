'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const test = require('node:test');

const ROOT = path.resolve(__dirname, '..', '..', '..');
const Inspector = require('../js/map-inspector.js');
const source = fs.readFileSync(path.join(ROOT, 'studio', 'editor', 'js', 'map-inspector.js'), 'utf8');
const bootstrap = fs.readFileSync(path.join(ROOT, 'studio', 'editor', 'js', 'event_presentation.js'), 'utf8');

const payload = {
    maps: [{
        id: 7,
        title: 'Inspector Lab',
        events: [{ id: 4, name: 'Bell', x: 2, y: 3, scriptId: 'ring' }],
        lightObjects: [{ x: 5, y: 6, radius: 4, falloff: 2, color: [1, 0.5, 0.25] }],
        overrides: [{ x: 8, y: 9, visual: 'moss' }]
    }],
    system: { spawn: { mapId: 7, x: 1, y: 2 } }
};

test('selection context resolves the existing authored object instead of cloning selection truth', () => {
    assert.strictEqual(Inspector.selectionContext(payload, 0, null).source, payload.maps[0]);
    assert.strictEqual(Inspector.selectionContext(payload, 0, { kind: 'event', id: 4 }).source, payload.maps[0].events[0]);
    assert.strictEqual(Inspector.selectionContext(payload, 0, { kind: 'light', index: 0 }).source, payload.maps[0].lightObjects[0]);
    assert.strictEqual(Inspector.selectionContext(payload, 0, { kind: 'override', index: 0 }).source, payload.maps[0].overrides[0]);
    assert.strictEqual(Inspector.selectionContext(payload, 0, { kind: 'spawn' }).source, payload.system.spawn);
    assert.equal(Inspector.selectionContext(payload, 0, { kind: 'light', index: 99 }).kind, 'environment',
        'stale selection must fall back to the current Map context');
});

test('Inspector sizing and Lamp numeric validity fail closed', () => {
    assert.equal(Inspector.clampWidth(10), Inspector.MIN_WIDTH);
    assert.equal(Inspector.clampWidth(9999), Inspector.MAX_WIDTH);
    assert.equal(Inspector.clampWidth('nope'), Inspector.DEFAULT_WIDTH);
    assert.equal(Inspector.numericInputIsValid('lamp-radius', ''), false);
    assert.equal(Inspector.numericInputIsValid('lamp-radius', '0'), false);
    assert.equal(Inspector.numericInputIsValid('lamp-radius', '3.5'), true);
    assert.equal(Inspector.numericInputIsValid('lamp-falloff', '0.1'), true);
});

test('browser Inspector adopts authoritative property surfaces and existing editors', () => {
    assert.match(source, /\['light-object-settings', 'override-settings', 'vertex-shading-section'\]/,
        'Lamp, Override, and Vertex Shading panels must be moved rather than reimplemented');
    assert.match(source, /originalSelectSemantic = host\.selectSemantic/,
        'Inspector must consume the Editor Scene selection seam');
    assert.match(source, /originalSelectSemantic\.apply\(this, arguments\)/,
        'existing selection mutation must run before Inspector rendering');
    assert.match(source, /openEventModal/,
        'Event editing must route to the existing staged Event editor');
    assert.match(source, /openMapProperties/,
        'Map editing must route to the existing Map Properties surface');
    assert.match(source, /event\.stopImmediatePropagation\(\)/,
        'invalid live numeric input must be stopped before inline authored mutation');
});

test('Inspector is persistent, resizable/collapsible, and loaded after the 3D workspace', () => {
    assert.match(source, /id = 'thestra-map-inspector'/);
    assert.match(source, /id = 'thestra-map-inspector-splitter'/);
    assert.match(source, /setPointerCapture/);
    assert.match(source, /collapsed = !collapsed/);
    assert.match(source, /localStorage\.setItem\('thestra-map-inspector-width'/);
    assert.match(bootstrap, /loadScript\('\/js\/thestra-editor-workspace\.js'\)[\s\S]*loadScript\('\/js\/map-inspector\.js'\)/,
        'Inspector must load after workspace-owned Vertex Shading exists');
});
