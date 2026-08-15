'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const { paletteForCellSurface, paletteForWallFace, exposedWallFaces } = require('./zone-palette-policy');

const ROOT = path.resolve(__dirname, '../../..');
const fixture = JSON.parse(fs.readFileSync(
    path.join(ROOT, 'docs', 'experiments', 'tileset-format', 'resource-model-c-zone-policy.json'),
    'utf8'
));
const map = fixture.map;

test('floor/ceiling surface policy is cell-zone-owned with default fallback', () => {
    assert.equal(paletteForCellSurface(map, 2, 1), 'cathedral_default');
    assert.equal(paletteForCellSurface(map, 8, 1), 'flooded_crypt');
    assert.equal(paletteForCellSurface(map, 2, 4), 'overgrown_cloister');
});

test('one logical wall may resolve different palettes on opposite exposed faces', () => {
    const west = paletteForWallFace(map, 6, 1, 5, 1);
    const east = paletteForWallFace(map, 6, 1, 7, 1);
    assert.deepEqual(west.logicalWall, east.logicalWall);
    assert.equal(west.palette, 'cathedral_default');
    assert.equal(east.palette, 'flooded_crypt');
    assert.equal(west.zone, null);
    assert.equal(east.zone, 'crypt');
});

test('wall-face palette ownership is determined by facing traversable space, not arbitrary wall-cell zone data', () => {
    const mutated = structuredClone(map);
    mutated.zoneGrid[1][6] = 'garden';
    const west = paletteForWallFace(mutated, 6, 1, 5, 1);
    const east = paletteForWallFace(mutated, 6, 1, 7, 1);
    assert.equal(west.palette, 'cathedral_default');
    assert.equal(east.palette, 'flooded_crypt');
});

test('fixture resolves every exposed wall face without shared-edge ambiguity', () => {
    const faces = exposedWallFaces(map);
    assert.equal(faces.length, 36);
    const counts = new Map();
    for (const face of faces) counts.set(face.palette, (counts.get(face.palette) || 0) + 1);
    assert.deepEqual(Object.fromEntries([...counts.entries()].sort()), {
        cathedral_default: 20,
        flooded_crypt: 9,
        overgrown_cloister: 7,
    });

    const byWall = new Map();
    for (const face of faces) {
        const key = face.logicalWall.join(',');
        const set = byWall.get(key) || new Set();
        set.add(face.palette);
        byWall.set(key, set);
    }
    const multiPaletteWalls = [...byWall.entries()]
        .filter(([, palettes]) => palettes.size > 1)
        .map(([wall, palettes]) => ({ wall, palettes: [...palettes].sort() }));
    assert.deepEqual(multiPaletteWalls, [
        { wall: '6,1', palettes: ['cathedral_default', 'flooded_crypt'] },
        { wall: '6,2', palettes: ['cathedral_default', 'flooded_crypt'] },
        { wall: '6,4', palettes: ['cathedral_default', 'overgrown_cloister'] },
    ]);
});

test('sparse semantic material overrides remain a later, explicit override layer', () => {
    assert.equal(map.materialOverrides['4,3'], 'ritual_door');
    assert.equal(paletteForCellSurface(map, 4, 3), 'cathedral_default');
    // The zone policy chooses ambient palette only. A semantic material override
    // intentionally remains separate so it can bypass ambient weighted choice.
});

test('print zone face ownership evidence', () => {
    const faces = exposedWallFaces(map);
    const evidence = {
        exposedFaces: faces.length,
        byPalette: {},
        oppositeFaceExample: {
            wall: [6, 1],
            west: paletteForWallFace(map, 6, 1, 5, 1).palette,
            east: paletteForWallFace(map, 6, 1, 7, 1).palette,
        },
    };
    for (const face of faces) evidence.byPalette[face.palette] = (evidence.byPalette[face.palette] || 0) + 1;
    process.stdout.write(`\nZONE_PALETTE_POLICY ${JSON.stringify(evidence)}\n`);
});
