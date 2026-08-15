'use strict';

const fs = require('node:fs');
const path = require('node:path');

const ROOT = path.resolve(__dirname, '../../..');
const TILESETS = path.join(ROOT, 'data', 'tilesets');

function walk(value, visitor, trail = []) {
    if (Array.isArray(value)) {
        value.forEach((item, index) => walk(item, visitor, trail.concat(index)));
        return;
    }
    if (!value || typeof value !== 'object') return;
    for (const [key, child] of Object.entries(value)) {
        visitor(key, child, trail.concat(key));
        walk(child, visitor, trail.concat(key));
    }
}

function entries(value) {
    return Array.isArray(value) ? value : [];
}

function poolCounts(data) {
    return {
        walls: entries(data.base?.walls).length,
        floors: entries(data.base?.floors).length,
        ceilings: entries(data.base?.ceilings).length,
        skies: entries(data.base?.skies).length,
        doors: entries(data.doors).length,
        features: entries(data.features).length,
        fixturePrefabs: entries(data.fixturePrefabs).length,
        namedTiles: data.tiles && typeof data.tiles === 'object' && !Array.isArray(data.tiles)
            ? Object.keys(data.tiles).length : 0,
    };
}

function classifyRepresentation(record) {
    if (!record || typeof record !== 'object') return 'none';
    if (record.geometry) return 'geometry';
    if (record.model) return 'model';
    if (record.atlas || record.middle || record.leftEdge || record.rightEdge) return 'atlas';
    if (record.sprite || record.texture || record.image) return 'image-path';
    return 'implicit';
}

function censusTileset(file) {
    const data = JSON.parse(fs.readFileSync(file, 'utf8'));
    const fields = Object.keys(data).sort();
    const keyCounts = new Map();
    const paths = [];
    const coordinateFacts = [];
    const authoredBehaviorFacts = [];

    walk(data, (key, value, trail) => {
        keyCounts.set(key, (keyCounts.get(key) || 0) + 1);
        const location = trail.join('.');
        if (['atlas', 'middle', 'leftEdge', 'rightEdge'].includes(key)) {
            coordinateFacts.push({ location, key, value });
        }
        if (['texture', 'heightMap', 'glowMap', 'skyPanorama', 'model', 'geometry', 'sprite', 'image'].includes(key)
            && typeof value === 'string') {
            paths.push({ location, key, value });
        }
        if (['where', 'predicate', 'injectProbability', 'emitsLight', 'blocksMovement', 'effect', 'effectHeight', 'effectMagnification'].includes(key)) {
            authoredBehaviorFacts.push({ location, key });
        }
    });

    const representations = [];
    for (const [role, records] of Object.entries({
        walls: data.base?.walls,
        floors: data.base?.floors,
        ceilings: data.base?.ceilings,
        skies: data.base?.skies,
        doors: data.doors,
        features: data.features,
    })) {
        for (const record of entries(records)) {
            representations.push({ role, id: record.id || null, kind: classifyRepresentation(record) });
        }
    }

    const representationKinds = {};
    for (const record of representations) {
        representationKinds[record.kind] = (representationKinds[record.kind] || 0) + 1;
    }

    const materialMapFields = fields.filter(key => key === 'heightMap' || key.startsWith('heightMap') || key === 'glowMap' || key === 'glowStrength');
    const environmentFields = fields.filter(key => /^(sky|fog|ambient|ceilingStyle|parallax)/i.test(key));

    let migrationShape = 'palette-only / implicit';
    if (data.texture && (coordinateFacts.length > 0 || materialMapFields.length > 0)) {
        migrationShape = 'compatibility atlas Surfaces + Palette';
    }
    if (representationKinds.geometry || representationKinds.model) {
        migrationShape += ' + direct representation refs';
    }

    return {
        file: path.basename(file),
        id: data.id || null,
        topLevelFields: fields,
        pools: poolCounts(data),
        representationKinds,
        atlasCoordinateFacts: coordinateFacts.length,
        uniqueAssetPaths: Array.from(new Set(paths.map(item => item.value))).sort(),
        assetPathFacts: paths.length,
        materialMapFields,
        environmentFields,
        authoredBehaviorFacts: authoredBehaviorFacts.length,
        tileDimensions: {
            width: data.tileWidth ?? null,
            height: data.tileHeight ?? null,
        },
        migrationShape,
        keyCounts: Object.fromEntries([...keyCounts.entries()].sort()),
    };
}

function main() {
    const files = fs.readdirSync(TILESETS)
        .filter(name => name.endsWith('.json'))
        .sort()
        .map(name => path.join(TILESETS, name));
    const records = files.map(censusTileset);

    const topLevelFrequency = {};
    const representationKinds = {};
    const migrationShapes = {};
    const non64 = [];
    for (const record of records) {
        for (const field of record.topLevelFields) topLevelFrequency[field] = (topLevelFrequency[field] || 0) + 1;
        for (const [kind, count] of Object.entries(record.representationKinds)) {
            representationKinds[kind] = (representationKinds[kind] || 0) + count;
        }
        migrationShapes[record.migrationShape] = (migrationShapes[record.migrationShape] || 0) + 1;
        if ((record.tileDimensions.width != null && record.tileDimensions.width !== 64)
            || (record.tileDimensions.height != null && record.tileDimensions.height !== 64)) {
            non64.push({ file: record.file, ...record.tileDimensions });
        }
    }

    const summary = {
        tilesetFiles: records.length,
        topLevelFrequency: Object.fromEntries(Object.entries(topLevelFrequency).sort()),
        representationKinds: Object.fromEntries(Object.entries(representationKinds).sort()),
        migrationShapes: Object.fromEntries(Object.entries(migrationShapes).sort()),
        tilesetsWithHeight: records.filter(record => record.materialMapFields.some(field => field.startsWith('heightMap'))).map(record => record.id),
        tilesetsWithGlow: records.filter(record => record.materialMapFields.includes('glowMap')).map(record => record.id),
        tilesetsWithFixturePrefabs: records.filter(record => record.pools.fixturePrefabs > 0).map(record => record.id),
        tilesetsWithBehaviorFacts: records.filter(record => record.authoredBehaviorFacts > 0).map(record => record.id),
        tilesetsWithGeometryOrModels: records.filter(record => record.representationKinds.geometry || record.representationKinds.model).map(record => record.id),
        non64TileDimensions: non64,
        totalAtlasCoordinateFacts: records.reduce((sum, record) => sum + record.atlasCoordinateFacts, 0),
        totalUniqueAssetPathReferences: new Set(records.flatMap(record => record.uniqueAssetPaths)).size,
    };

    process.stdout.write(JSON.stringify({ summary, records }, null, 2) + '\n');
}

main();
