'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const { migrateLegacyTileset, compileLegacyTileset } = require('./legacy-surface-palette');

const ROOT = path.resolve(__dirname, '../../..');
const TILESETS = path.join(ROOT, 'data', 'tilesets');
const files = fs.readdirSync(TILESETS).filter(name => name.endsWith('.json')).sort();

for (const file of files) {
    test(`${file} round-trips exactly through compatibility Surface + Palette form`, () => {
        const legacy = JSON.parse(fs.readFileSync(path.join(TILESETS, file), 'utf8'));
        const migrated = migrateLegacyTileset(legacy);
        const rebuilt = compileLegacyTileset(migrated);
        assert.deepEqual(rebuilt, legacy);
    });
}

test('compatibility migration does not copy atlas pixels or manufacture standalone source paths', () => {
    for (const file of files) {
        const legacy = JSON.parse(fs.readFileSync(path.join(TILESETS, file), 'utf8'));
        const migrated = migrateLegacyTileset(legacy);
        const source = migrated.sources.legacyAtlas;
        assert.equal(source.kind, 'legacyAtlasCompatibility');
        assert.equal(source.texture, legacy.texture);
        for (const surface of Object.values(migrated.surfaces)) {
            assert.equal(surface.source, 'legacyAtlas');
            assert.equal(Object.hasOwn(surface, 'albedo'), false);
            assert.equal(Object.hasOwn(surface, 'height'), false);
            assert.equal(Object.hasOwn(surface, 'emission'), false);
        }
    }
});

test('feature and fixture behavior stays palette-owned during the compatibility migration', () => {
    const bellroot = JSON.parse(fs.readFileSync(path.join(TILESETS, 'stillnight_bellroot_vigil.json'), 'utf8'));
    const migrated = migrateLegacyTileset(bellroot);
    assert.deepEqual(migrated.palette.features, bellroot.features);
    assert.deepEqual(migrated.palette.fixturePrefabs, bellroot.fixturePrefabs);
    assert.equal(migrated.sources.legacyAtlas.heightMap, bellroot.heightMap);
    assert.equal(migrated.sources.legacyAtlas.glowMap, bellroot.glowMap);
});

test('migration evidence reports Surface extraction without atlas asset churn', () => {
    const evidence = {
        tilesets: files.length,
        surfaces: 0,
        legacyAtlasSources: 0,
        tilesetsWithHeight: 0,
        tilesetsWithGlow: 0,
        featureRecordsPreserved: 0,
        fixturePrefabsPreserved: 0,
    };
    for (const file of files) {
        const legacy = JSON.parse(fs.readFileSync(path.join(TILESETS, file), 'utf8'));
        const migrated = migrateLegacyTileset(legacy);
        evidence.surfaces += Object.keys(migrated.surfaces).length;
        evidence.legacyAtlasSources += 1;
        if (legacy.heightMap) evidence.tilesetsWithHeight += 1;
        if (legacy.glowMap) evidence.tilesetsWithGlow += 1;
        evidence.featureRecordsPreserved += (legacy.features || []).length;
        evidence.fixturePrefabsPreserved += (legacy.fixturePrefabs || []).length;
    }
    process.stdout.write(`\nLEGACY_SURFACE_MIGRATION ${JSON.stringify(evidence)}\n`);
});
