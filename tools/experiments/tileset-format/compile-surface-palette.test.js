'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const { compilePalette } = require('./compile-surface-palette');

const ROOT = path.resolve(__dirname, '../../..');
const model = JSON.parse(fs.readFileSync(
    path.join(ROOT, 'docs', 'experiments', 'tileset-format', 'resource-model-a-surface-palette.json'),
    'utf8'
));

test('representative single-atlas palettes compile down to current runtime-shaped data', () => {
    for (const id of ['dungeon_default_v2', 'bellroot_v2', 'showcase_v2']) {
        const compiled = compilePalette(model, id);
        assert.equal(compiled.directlyRepresentable, true, `${id}: ${JSON.stringify(compiled.normalization)}`);
        assert.equal(compiled.normalization.length, 0);
    }
});

test('Bellroot preserves weighted semantic ids while atlas coordinates become compatibility output', () => {
    const compiled = compilePalette(model, 'bellroot_v2').legacy;
    assert.deepEqual(compiled.base.walls.map(entry => [entry.id, entry.weight]), [
        ['bellroot_wall_pilaster', 60],
        ['bellroot_wall_rubble', 40],
    ]);
    assert.deepEqual(compiled.base.walls[0].middle, [1, 1]);
    assert.deepEqual(compiled.base.walls[1].middle, [1, 0]);
    assert.equal(compiled.texture, 'assets/textures/Stillnight_BellrootVigil.png');
    assert.equal(compiled.heightMap, 'assets/textures/Stillnight_BellrootVigil_heightmap.png');
    assert.equal(compiled.glowMap, 'assets/textures/Stillnight_BellrootVigil_glow.png');
    assert.equal(compiled.heightMapScale.wall, 0.14);
});

test('geometry-backed Surface coexists with one atlas-backed role without a renderer ontology change', () => {
    const compiled = compilePalette(model, 'showcase_v2');
    assert.equal(compiled.directlyRepresentable, true);
    assert.equal(compiled.legacy.base.walls[0].geometry, 'assets/geometry/limestone_wall');
    assert.deepEqual(compiled.legacy.base.floors[0].atlas, [0, 1]);
    assert.equal(compiled.sourceCounts.albedo, 1);
});

test('mixing two independent authored image families identifies normalization rather than undefined merge precedence', () => {
    const mixed = structuredClone(model);
    mixed.palettes.mixed_family_probe = {
        walls: [{ id: 'bellroot_wall', surface: 'bellroot_pilaster', weight: 50 }],
        floors: [{ id: 'dungeon_floor', surface: 'dungeon_flagstone', weight: 50 }],
    };
    const compiled = compilePalette(mixed, 'mixed_family_probe');
    assert.equal(compiled.directlyRepresentable, false);
    assert.equal(compiled.sourceCounts.albedo, 2);
    assert.ok(compiled.normalization.some(item => item.reason === 'multiple-albedo-sources'));
    assert.ok(compiled.normalization.some(item => item.reason === 'multiple-height-sources'));
    assert.equal(compiled.normalization.some(item => item.reason === 'merge-precedence'), false);
});

test('print compatibility seam evidence', () => {
    const evidence = {};
    for (const id of ['dungeon_default_v2', 'bellroot_v2', 'showcase_v2']) {
        const compiled = compilePalette(model, id);
        evidence[id] = {
            directlyRepresentable: compiled.directlyRepresentable,
            sourceCounts: compiled.sourceCounts,
            normalization: compiled.normalization,
        };
    }
    const mixed = structuredClone(model);
    mixed.palettes.mixed_family_probe = {
        walls: [{ id: 'bellroot_wall', surface: 'bellroot_pilaster', weight: 50 }],
        floors: [{ id: 'dungeon_floor', surface: 'dungeon_flagstone', weight: 50 }],
    };
    const mixedResult = compilePalette(mixed, 'mixed_family_probe');
    evidence.mixed_family_probe = {
        directlyRepresentable: mixedResult.directlyRepresentable,
        sourceCounts: mixedResult.sourceCounts,
        normalizationReasons: mixedResult.normalization.map(item => item.reason),
    };
    process.stdout.write(`\nSURFACE_PALETTE_COMPATIBILITY ${JSON.stringify(evidence)}\n`);
});
