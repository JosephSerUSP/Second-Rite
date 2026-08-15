'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const { normalizeFixture, normalizeSurface } = require('./material-normalizer');

const ROOT = path.resolve(__dirname, '../../..');
const FIXTURE = JSON.parse(fs.readFileSync(
    path.join(ROOT, 'docs', 'experiments', 'tileset-format', 'material-source-animation-candidate.json'),
    'utf8'
));

const normalized = normalizeFixture(FIXTURE);

test('standalone semantic maps remain separately named in provenance', () => {
    const wet = normalized.surfaces.wet_stone;
    assert.deepEqual(wet.provenance, [
        { semantic: 'albedo', path: 'assets/experiments/wet_stone/albedo.png' },
        { semantic: 'emission', path: 'assets/experiments/wet_stone/emission.png' },
        { semantic: 'height', path: 'assets/experiments/wet_stone/height.png' },
    ]);
    assert.equal(wet.runtimePlan.sourcePacking, 'unspecified-runtime-optimization');
});

test('animated albedo does not multiply static height geometry work', () => {
    const water = normalized.surfaces.shallow_water;
    assert.equal(water.properties.albedo.animated, true);
    assert.equal(water.properties.albedo.frames.length, 3);
    assert.equal(water.properties.albedo.fps, 6);
    assert.equal(water.properties.albedo.clock, 'water');
    assert.equal(water.properties.height.animated, false);
    assert.equal(water.geometryBuilds.length, 1);
    assert.equal(water.runtimePlan.staticGeometryBuildCount, 1);
});

test('animated emission remains independent from static albedo', () => {
    const monitor = normalized.surfaces.flicker_monitor;
    assert.equal(monitor.properties.albedo.animated, false);
    assert.equal(monitor.properties.albedo.frames.length, 1);
    assert.equal(monitor.properties.emission.animated, true);
    assert.equal(monitor.properties.emission.frames.length, 4);
    assert.equal(monitor.properties.emission.fps, 10);
    assert.equal(monitor.properties.emission.clock, 'monitor-flicker');
    assert.deepEqual(monitor.runtimePlan.animatedSamplerFrames, { albedo: 1, emission: 4 });
});

test('ordered material layers survive normalization without becoming source channels', () => {
    const mossy = normalized.surfaces.mossy_wet_stone;
    assert.deepEqual(mossy.passes.map(pass => pass.blend), ['multiply', 'add']);
    assert.deepEqual(mossy.passes.map(pass => pass.uvSource), ['uv', 'sphere']);
    assert.deepEqual(mossy.passes.map(pass => pass.meaning), ['moss coverage', 'wet sheen']);
    assert.deepEqual(mossy.passes.map(pass => pass.image), [
        'assets/experiments/mossy_stone/moss-mask.png',
        'assets/experiments/mossy_stone/wetness.png',
    ]);
});

test('ordinary material normalization rejects animated height explicitly', () => {
    assert.throws(() => normalizeSurface('breathing_wall', {
        albedo: 'albedo.png',
        height: { frames: ['height_0.png', 'height_1.png'], fps: 4 },
    }), /animated height is animated geometry/);
});

test('print normalization evidence for the shared comparison', () => {
    const evidence = {};
    for (const [id, surface] of Object.entries(normalized.surfaces)) {
        evidence[id] = {
            geometryBuilds: surface.geometryBuilds.length,
            albedoFrames: surface.properties.albedo?.frames.length || 0,
            emissionFrames: surface.properties.emission?.frames.length || 0,
            materialLayers: surface.passes.length,
            provenanceEntries: surface.provenance.length,
        };
    }
    process.stdout.write(`\nMATERIAL_NORMALIZATION_EVIDENCE ${JSON.stringify(evidence)}\n`);
});
