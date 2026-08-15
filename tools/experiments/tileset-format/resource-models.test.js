'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');

const ROOT = path.resolve(__dirname, '../../..');
const EXP = path.join(ROOT, 'docs', 'experiments', 'tileset-format');

function load(name) {
    return JSON.parse(fs.readFileSync(path.join(EXP, name), 'utf8'));
}

function collectPaletteSurfaceRefs(model) {
    const refs = [];
    for (const [paletteId, palette] of Object.entries(model.palettes || {})) {
        for (const role of ['walls', 'floors', 'ceilings', 'doors']) {
            for (const entry of palette[role] || []) {
                if (entry.surface) refs.push({ paletteId, role, surface: entry.surface, entry });
            }
        }
    }
    return refs;
}

function importedRecords(model, tileset, role) {
    const records = [];
    for (const libraryId of tileset.imports || []) {
        const library = model.libraries && model.libraries[libraryId];
        for (const entry of (library && library[role]) || []) {
            records.push({ libraryId, entry });
        }
    }
    return records;
}

function zoneBoundaryEdges(zoneGrid) {
    let count = 0;
    const pairs = new Set();
    for (let y = 0; y < zoneGrid.length; y += 1) {
        for (let x = 0; x < zoneGrid[y].length; x += 1) {
            const here = zoneGrid[y][x] || '';
            for (const [dx, dy] of [[1, 0], [0, 1]]) {
                const row = zoneGrid[y + dy];
                if (!row || x + dx >= row.length) continue;
                const there = row[x + dx] || '';
                if (here === there || (!here && !there)) continue;
                count += 1;
                pairs.add([here || '(default)', there || '(default)'].sort().join(' <-> '));
            }
        }
    }
    return { count, pairs: Array.from(pairs).sort() };
}

test('candidate A contains packing coordinates inside Surface sources, not palette roles', () => {
    const model = load('resource-model-a-surface-palette.json');
    const refs = collectPaletteSurfaceRefs(model);
    assert.ok(refs.length >= 3, 'fixture should exercise several semantic Surface references');

    for (const ref of refs) {
        assert.ok(model.surfaces[ref.surface], `missing Surface ${ref.surface}`);
        assert.equal(Object.hasOwn(ref.entry, 'atlas'), false);
        assert.equal(Object.hasOwn(ref.entry, 'region'), false);
        assert.equal(Object.hasOwn(ref.entry, 'image'), false);
    }

    const atlasBacked = Object.values(model.surfaces).filter(surface => surface.source?.kind === 'atlasRegion');
    assert.ok(atlasBacked.length >= 2);
    for (const surface of atlasBacked) {
        assert.ok(surface.source.image);
        assert.ok(surface.source.region);
    }
});

test('candidate A demonstrates actual Surface reuse across environment palettes', () => {
    const model = load('resource-model-a-surface-palette.json');
    const refs = collectPaletteSurfaceRefs(model);
    const users = refs.filter(ref => ref.surface === 'dungeon_flagstone').map(ref => ref.paletteId).sort();
    assert.deepEqual(users, ['dungeon_default_v2', 'showcase_v2']);
});

test('candidate B exposes merge semantics before it can resolve its tiny import graph', () => {
    const model = load('resource-model-b-imports.json');
    const tileset = model.tilesets.dungeon_imported;
    const importedWalls = importedRecords(model, tileset, 'walls');
    const importedIds = new Set(importedWalls.map(record => record.entry.id));
    const localIds = new Set((tileset.walls || []).map(entry => entry.id));
    const collisions = Array.from(localIds).filter(id => importedIds.has(id)).sort();

    assert.deepEqual(collisions, ['stone_wall']);
    assert.equal(Object.keys(model.requiredMergeQuestions || {}).length, 6);

    const prefabOwners = new Map();
    for (const [libraryId, library] of Object.entries(model.libraries || {})) {
        for (const prefab of library.fixturePrefabs || []) prefabOwners.set(prefab.id, libraryId);
    }
    const crossLibraryDependencies = [];
    for (const [libraryId, library] of Object.entries(model.libraries || {})) {
        for (const feature of library.features || []) {
            const owner = feature.prefab && prefabOwners.get(feature.prefab);
            if (owner && owner !== libraryId) crossLibraryDependencies.push(`${libraryId}->${owner}:${feature.prefab}`);
        }
    }
    assert.deepEqual(crossLibraryDependencies, ['torch_pack->stone_core:wall_beside_floor']);
});

test('candidate C replaces merge precedence with measurable shared-zone boundary ownership', () => {
    const model = load('resource-model-c-zone-policy.json');
    const map = model.map;
    assert.deepEqual(Object.keys(map.zones || {}).sort(), ['crypt', 'garden']);
    assert.ok(Object.keys(map.materialOverrides || {}).length > 0, 'fixture must retain sparse semantic overrides');

    const boundary = zoneBoundaryEdges(map.zoneGrid);
    assert.ok(boundary.count > 0, 'zone-local policy must actually create shared boundaries to resolve');
    assert.ok(boundary.pairs.some(pair => pair.includes('crypt')));
    assert.ok(boundary.pairs.some(pair => pair.includes('garden')));
});

test('print comparable resource-model pressure metrics', () => {
    const a = load('resource-model-a-surface-palette.json');
    const b = load('resource-model-b-imports.json');
    const c = load('resource-model-c-zone-policy.json');
    const aRefs = collectPaletteSurfaceRefs(a);
    const usageCounts = new Map();
    for (const ref of aRefs) usageCounts.set(ref.surface, (usageCounts.get(ref.surface) || 0) + 1);
    const bTileset = b.tilesets.dungeon_imported;
    const importedIds = new Set(importedRecords(b, bTileset, 'walls').map(record => record.entry.id));
    const collisions = (bTileset.walls || []).filter(entry => importedIds.has(entry.id)).length;
    const boundary = zoneBoundaryEdges(c.map.zoneGrid);

    const metrics = {
        surfacePalette: {
            surfaces: Object.keys(a.surfaces || {}).length,
            palettes: Object.keys(a.palettes || {}).length,
            reusedSurfaceIds: Array.from(usageCounts.values()).filter(count => count > 1).length,
        },
        imports: {
            imports: bTileset.imports.length,
            localImportedIdCollisions: collisions,
            unresolvedMergeQuestions: Object.keys(b.requiredMergeQuestions || {}).length,
        },
        zonePolicy: {
            namedZones: Object.keys(c.map.zones || {}).length,
            boundaryEdgesNeedingOwnership: boundary.count,
            boundaryKinds: boundary.pairs,
        },
    };
    process.stdout.write(`\nRESOURCE_MODEL_METRICS ${JSON.stringify(metrics)}\n`);
});
