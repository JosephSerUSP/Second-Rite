'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');
const Overlay = require('../js/environment-walk-surface-overlay.js');
const DirectConsumer = require('../js/three-definition-consumer.js');

function baseBundle() {
    return {
        version: 1,
        materials: [{ id: 'base', color: [1, 1, 1, 1] }],
        surfaces: [{
            id: 'base_surface', name: 'base surface', material: 'base',
            source: { kind: 'environment', surface: 'render' },
            positions: [0,0,0, 1,0,0, 0,1,0],
            uvs: [0,0, 0,0, 0,0], normals: [0,0,1, 0,0,1, 0,0,1],
            colors: [1,1,1,1, 1,1,1,1, 1,1,1,1]
        }]
    };
}

function directBundle() {
    const bundle = baseBundle();
    bundle.encoding = { kind: 'mesh-definitions-v1' };
    bundle.definitions = [];
    bundle.placements = [];
    bundle.surfaces[0].transportOrder = 1;
    return bundle;
}

const manifest = {
    provenance: { walkSurfaceAuthority: 'Blender collections TH_WALKABLE/TH_OBSTACLES' },
    walkSurface: {
        groundZ: 0.5,
        regions: [{ points: [[0,0],[3,0],[3,3],[1.5,1.5],[0,3]] }],
        obstacles: [{ points: [[1,0.5],[2,0.5],[2,1],[1,1]] }]
    }
};

test('concave walk polygons triangulate without a fan crossing the notch', () => {
    const triangles = Overlay.triangulate(manifest.walkSurface.regions[0].points, 'concave');
    assert.equal(triangles.length, 3);
    const area = triangles.reduce((sum, triangle) => {
        const [a,b,c] = triangle;
        return sum + Math.abs((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])) / 2;
    }, 0);
    assert.equal(area, 6.75);
});

test('bundle augmentation adds read-only region/obstacle fills and boundaries', () => {
    const original = baseBundle();
    const augmented = Overlay.augmentBundle(original, manifest, 'assets/environments/test/environment.json');
    assert.equal(original.surfaces.length, 1, 'source bundle must remain immutable');
    assert.equal(augmented.surfaces.length, 5);
    assert.equal(augmented.materials.length, 5);
    assert.deepEqual(augmented.inspection.walkSurface, {
        manifestPath: 'assets/environments/test/environment.json',
        regionCount: 1,
        obstacleCount: 1,
        groundZ: 0.5,
        readOnly: true,
    });
    const inspection = augmented.surfaces.slice(1);
    assert.ok(inspection.every(surface => surface.source.kind === 'walk-surface-inspection'));
    assert.ok(inspection.every(surface => surface.source.readOnly === true));
    assert.ok(inspection.every(surface => surface.positions.length % 9 === 0));
});

test('direct instance transport appends inspection literals after authoritative draw order', () => {
    const original = directBundle();
    const augmented = Overlay.augmentBundle(original, manifest, 'fixture/environment.json');
    assert.equal(original.surfaces[0].transportOrder, 1);
    assert.deepEqual(augmented.surfaces.slice(1).map(surface => surface.transportOrder), [2, 3, 4, 5]);
    const ordered = DirectConsumer.orderedRenderables(augmented);
    assert.equal(ordered.length, 5);
    assert.equal(ordered[0].value.id, 'base_surface');
    assert.deepEqual(ordered.slice(1).map(entry => entry.value.source.surface), [
        'walk-region', 'walk-region', 'walk-obstacle', 'walk-obstacle'
    ]);
});

test('viewport installation replays the authoritative bundle without creating an editing path', () => {
    const calls = [];
    const viewport = { setRenderableBundle(bundle) { calls.push(bundle); return bundle; } };
    Overlay.install(viewport);
    viewport.setRenderableBundle(baseBundle());
    viewport.setEnvironmentWalkSurfaceManifest(manifest, 'fixture/environment.json');
    assert.equal(viewport.getWalkSurfaceInfo().available, true);
    assert.equal(viewport.getWalkSurfaceInfo().readOnly, true);
    assert.equal(viewport.getWalkSurfaceInfo().regionCount, 1);
    assert.equal(calls.at(-1).surfaces.length, 1, 'manifest remains hidden until explicitly shown');

    viewport.setWalkSurfaceVisible(true);
    assert.equal(viewport.getWalkSurfaceVisible(), true);
    assert.equal(calls.at(-1).surfaces.length, 5);
    assert.equal(calls.at(-1).inspection.walkSurface.readOnly, true);

    viewport.setWalkSurfaceVisible(false);
    assert.equal(calls.at(-1).surfaces.length, 1, 'hiding restores untouched authoritative render bundle');
});

test('malformed semantic loops fail visibly rather than being guessed', () => {
    assert.throws(() => Overlay.augmentBundle(baseBundle(), {
        walkSurface: { groundZ: 0, regions: [{ points: [[0,0],[1,0],[2,0]] }], obstacles: [] }
    }, 'bad.json'), /zero area/);
});