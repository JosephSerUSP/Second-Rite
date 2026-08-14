'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const test = require('node:test');

const Adapter = require('../js/second-rite-editor-adapter.js');
const Contract = require('../js/thestra-viewport-contract.js');
const Fidelity = require('../js/three-world-fidelity-core.js');
const ROOT = path.resolve(__dirname, '..', '..', '..');

function close(actual, expected, message) {
    assert.ok(Math.abs(actual - expected) < 1e-9,
        `${message}: expected ${expected}, got ${actual}`);
}

function lightingScene(roles) {
    return {
        bounds: { width: roles.length, height: 1 },
        cells: roles.map((role, x) => ({ cell: { x, y: 0 }, role }))
    };
}

test('3D renderable adapter multiplies authoritative vertex colors by resolved map light', async () => {
    const originalColors = [
        0.8, 0.6, 0.4, 0.7,
        0.8, 0.6, 0.4, 0.7,
        0.8, 0.6, 0.4, 0.7
    ];
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
            colors: originalColors.slice()
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
    const surface = result.surfaces[0];
    const color = surface.colors;

    assert.deepStrictEqual(surface.unlitColors, originalColors,
        'Studio must retain source/model colors so live authoring can relight the existing mesh without LÖVE');

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

test('3D renderable adapter retains unlit colors even when no resolved grid is present', () => {
    const originalColors = [0.2, 0.3, 0.4, 0.5];
    const bundle = {
        surfaces: [{ positions: [1, 1, 0], colors: originalColors.slice() }]
    };
    assert.strictEqual(Adapter.applyVertexLighting(bundle), bundle);
    assert.deepStrictEqual(bundle.surfaces[0].colors, originalColors);
    assert.deepStrictEqual(bundle.surfaces[0].unlitColors, originalColors);
});

test('Studio mirrors runtime 0.76 orientation modulation before static light', () => {
    const bundle = {
        surfaces: [
            {
                source: { kind: 'cell', surface: 'north-wall' },
                positions: [1, 1, 0], colors: [1, 0.5, 0.25, 1]
            },
            {
                source: { kind: 'cell', surface: 'east-wall' },
                positions: [1, 1, 0], colors: [1, 0.5, 0.25, 1]
            },
            {
                source: { kind: 'cell', surface: 'opening', axis: 'y' },
                positions: [1, 1, 0], colors: [1, 0.5, 0.25, 1]
            },
            {
                source: { kind: 'cell', surface: 'opening', axis: 'x' },
                positions: [1, 1, 0], colors: [1, 0.5, 0.25, 1]
            }
        ]
    };

    Adapter.applyVertexModulation(bundle, []);
    close(bundle.surfaces[0].colors[0], 0.76, 'north wall red');
    close(bundle.surfaces[0].colors[1], 0.38, 'north wall green');
    close(bundle.surfaces[1].colors[0], 1, 'east wall is not side-darkened');
    close(bundle.surfaces[2].colors[0], 0.76, 'y opening red');
    close(bundle.surfaces[3].colors[0], 1, 'x opening is not side-darkened');
    close(Adapter.surfaceOrientationFactor({ source: { surface: 'south-wall' } }), 0.76,
        'south wall factor');
});

test('Three resolved world material ignores scene relighting but preserves emission stage', () => {
    const source = [
        'void main() {',
        '  vec4 diffuseColor = vec4( 1.0 );',
        '  vec3 totalEmissiveRadiance = vec3( 0.25 );',
        '  vec3 outgoingLight = vec3( 99.0 );',
        '  #include <opaque_fragment>',
        '}'
    ].join('\n');
    const rewritten = Fidelity.rewriteFragmentShader(source);
    assert.match(rewritten, /outgoingLight = diffuseColor\.rgb \+ totalEmissiveRadiance;/,
        'resolved world output must be source\/vertex color plus emission, not Three light response');
    assert.ok(rewritten.indexOf(Fidelity.STATIC_WORLD_LINE)
        < rewritten.indexOf(Fidelity.OPAQUE_FRAGMENT_MARKER),
    'fidelity override must happen immediately before Three writes the opaque fragment');
    assert.throws(() => Fidelity.rewriteFragmentShader('void main() {}'), /opaque_fragment/,
        'a Three shader contract change must fail loudly instead of silently restoring bright world lighting');

    assert.strictEqual(Fidelity.isResolvedWorldMaterial({
        isMeshStandardMaterial: true, vertexColors: true, metalness: 0, roughness: 0.9
    }), true);
    assert.strictEqual(Fidelity.isResolvedWorldMaterial({
        isMeshStandardMaterial: true, vertexColors: false, metalness: 0, roughness: 0.9
    }), false, 'editor-only normally-lit Standard materials must not be patched');
});

test('live authoring bake mirrors runtime ambient, falloff and wall occlusion', () => {
    const scene = lightingScene(['floor', 'wall', 'floor']);
    const source = { x: 0, y: 0, radius: 4, falloff: 2, color: [1, 0, 0] };
    const light = Contract.bakeAuthoringLighting(scene, [source]);

    assert.ok(light[0][0][0] > Contract.DEFAULT_LIGHT_AMBIENT[0],
        'source-side vertex must brighten immediately');
    close(light[0][0][1], 0.12, 'red source leaves green at ambient');
    close(light[0][3][0], 0.12, 'wall blocks red contribution behind it');
    close(light[0][3][1], 0.12, 'blocked vertex keeps green ambient');
    close(light[0][3][2], 0.12, 'blocked vertex keeps blue ambient');

    const gentle = Contract.bakeAuthoringLighting(scene, [Object.assign({}, source, { falloff: 1 })]);
    const steep = Contract.bakeAuthoringLighting(scene, [Object.assign({}, source, { falloff: 4 })]);
    assert.ok(gentle[0][1][0] > steep[0][1][0],
        'authored falloff must affect the browser-side bake with runtime exponent semantics');
});

test('live authoring lighting samples the baked vertex field bilinearly', () => {
    const light = [
        [[0, 0, 0], [1, 0, 0]],
        [[0, 1, 0], [1, 1, 0]]
    ];
    const sample = Contract.sampleAuthoringLighting(light, 0.5, 0.5);
    close(sample[0], 0.5, 'bilinear red');
    close(sample[1], 0.5, 'bilinear green');
    close(sample[2], 0, 'bilinear blue');
});

test('Light-mode preview is frame-local and does not wait for a runtime bundle refresh', () => {
    const source = fs.readFileSync(
        path.join(ROOT, 'tools', 'editor', 'js', 'three-editor-viewport.js'), 'utf8'
    );
    assert.match(source, /Contract\.bakeAuthoringLighting\(sceneModel, sources\)/,
        'viewport must bake current semantic lightObjects in the browser');
    assert.match(source, /syncLiveAuthoringLighting\(\);[\s\S]*renderer\.render/,
        'live lighting must be applied in the animation frame before render');
    assert.match(source,
        /moveGizmo\.addEventListener\('objectChange',[\s\S]*moveGesture\.semantic\.kind === 'light'[\s\S]*markLiveLightingDirty\(\)/,
        'dragging a light must dirty the live preview before the authored move commits');
    assert.match(source, /thestraAuthoritativeColors/,
        'viewport must retain the runtime-resolved color field for restoration outside Light authoring');
});

test('lighting authoring bootstrap shelves Paint/Blur and colocates Vertex Shading with lamps', () => {
    const source = fs.readFileSync(
        path.join(ROOT, 'tools', 'editor', 'js', 'vertex-shading.js'), 'utf8'
    );
    assert.match(source, /setLightTool\('object'\)/,
        'Light authoring must force the live semantic Lamp tool instead of legacy vertex Paint');
    assert.match(source, /light-blur-hint/);
    assert.match(source, /light-brush-radius/);
    assert.match(source, /clearMapLight/);
    assert.match(source, /hide\(lampRadio\.closest\('\.field-row-stacked'\)\)/,
        'legacy Paint\/Blur selector row must be hidden');
    assert.match(source, /vertex-shading-section/);
    assert.match(source, /palette\.appendChild\(shading\)/,
        'Vertex Shading controls must live in the visible Light\/environment palette');
    assert.match(source, /import\('\/js\/three-world-fidelity\.js'\)/,
        'static world fidelity must begin loading before the Three workspace backend');
});

test('runtime bridge still exports resolved runtimeLight for non-authoring presentation truth', () => {
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
