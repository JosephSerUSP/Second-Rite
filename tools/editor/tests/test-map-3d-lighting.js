'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const test = require('node:test');

const Adapter = require('../js/second-rite-editor-adapter.js');
const ROOT = path.resolve(__dirname, '..', '..', '..');

function close(actual, expected, message) {
    assert.ok(Math.abs(actual - expected) < 1e-9,
        `${message}: expected ${expected}, got ${actual}`);
}

test('3D renderable adapter multiplies authoritative vertex colors by resolved map light', async () => {
    const bundle = {
        materials: [],
        light: [
            [[1, 0, 0], [0, 1, 0]],
            [[0, 0, 1], [1, 1, 1]]
        ],
        surfaces: [{
            positions: [
                1, 1, 0,
                1.5, 1.5, 0,
                2, 1, 0
            ],
            colors: [
                0.8, 0.6, 0.4, 0.7,
                0.8, 0.6, 0.4, 0.7,
                0.8, 0.6, 0.4, 0.7
            ]
        }]
    };
    const response = {
        ok: true,
        status: 200,
        json: async () => bundle
    };

    const result = await Adapter.loadRenderable(
        { id: 1 },
        { fetchImpl: async () => response },
        'http://example.test/api/map-renderable'
    );
    const color = result.surfaces[0].colors;

    close(color[0], 0.8, 'corner red');
    close(color[1], 0, 'corner green');
    close(color[2], 0, 'corner blue');
    close(color[3], 0.7, 'corner alpha is preserved');

    close(color[4], 0.4, 'bilinear red');
    close(color[5], 0.3, 'bilinear green');
    close(color[6], 0.2, 'bilinear blue');
    close(color[7], 0.7, 'bilinear alpha is preserved');

    close(color[8], 0, 'second corner red');
    close(color[9], 0.6, 'second corner green');
    close(color[10], 0, 'second corner blue');
    close(color[11], 0.7, 'second corner alpha is preserved');
});

test('3D renderable adapter leaves bundles without resolved lighting unchanged', () => {
    const bundle = {
        surfaces: [{ positions: [1, 1, 0], colors: [0.2, 0.3, 0.4, 0.5] }]
    };
    assert.strictEqual(Adapter.applyVertexLighting(bundle), bundle);
    assert.deepStrictEqual(bundle.surfaces[0].colors, [0.2, 0.3, 0.4, 0.5]);
});

test('runtime bridge exports resolved runtimeLight rather than rebuilding lighting in Studio', () => {
    const source = fs.readFileSync(
        path.join(ROOT, 'presentation', 'editor_renderable_bridge.lua'), 'utf8'
    );
    assert.match(source, /resolvedMap\.runtimeLight or resolvedMap\.light/);
    assert.match(source, /result\.light\s*=/);
});

test('retired 2D map canvas is hidden before map editor/bootstrap work can paint', () => {
    const source = fs.readFileSync(
        path.join(ROOT, 'tools', 'editor', 'js', 'event_presentation.js'), 'utf8'
    );
    const hide = source.indexOf("legacyMapCanvas.style.visibility = 'hidden'");
    const domReady = source.indexOf("window.addEventListener('DOMContentLoaded'");
    assert.ok(hide >= 0, 'legacy canvas hide is missing');
    assert.ok(domReady >= 0, 'Thestra bootstrap DOMContentLoaded hook is missing');
    assert.ok(hide < domReady, 'legacy canvas must be hidden synchronously before async bootstrap');
});
