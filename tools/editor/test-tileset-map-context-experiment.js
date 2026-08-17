// Focused harness for the #547 Map-contextual tileset experiment.
//
// This guards the parts that would silently lie: reaching the semantic owner of
// a runtime surface, keeping realized (engine) and authored (weight) shares
// distinguishable, and the truth boundary that this prototype never resolves a
// weighted variant itself.
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const path = require('path');

const Model = require('./js/tileset-map-context-model.js');

function sampleRecord() {
    return {
        id: 'sample_env',
        name: 'Sample Environment',
        texture: 'assets/tilesets/sample.png',
        tileWidth: 64,
        tileHeight: 64,
        base: {
            walls: [
                { id: 'wall_a', role: 'base_wall', middle: [1, 0], leftEdge: [1, 1, 0], rightEdge: [1, 1, 32], weight: 60 },
                { id: 'wall_b', role: 'base_wall', middle: [1, 2], leftEdge: [1, 3, 0], rightEdge: [1, 3, 32], weight: 20 },
            ],
            floors: [{ id: 'floor_a', role: 'base_floor', atlas: [3, 0], weight: 100 }],
            ceilings: [{ id: 'ceil_a', role: 'base_ceiling', atlas: [0, 0], weight: 100 }],
            wallTops: [],
        },
        doors: [{ id: 'door_a', role: 'door', atlas: [2, 0], weight: 100 }],
        features: [
            { id: 'sconce', role: 'wall_feature', atlas: [4, 0], injectProbability: 0.2 },
            { id: 'puddle', role: 'floor_feature', atlas: [4, 1], injectProbability: 0.1 },
        ],
    };
}

test('a clicked runtime surface reaches its owning semantic pool', () => {
    assert.equal(Model.roleFromProvenance({ kind: 'cell', surface: 'north-wall', x: 3, y: 4 }).key, 'wall');
    assert.equal(Model.roleFromProvenance({ kind: 'cell', surface: 'floor', x: 3, y: 4 }).key, 'floor');
    assert.equal(Model.roleFromProvenance({ kind: 'cell', surface: 'ceiling', x: 3, y: 4 }).key, 'ceiling');
    assert.equal(Model.roleFromProvenance({ kind: 'cell', surface: 'wall-top', x: 3, y: 4 }).key, 'wall_top');
    assert.equal(Model.roleFromProvenance({ kind: 'cell', surface: 'opening', x: 3, y: 4 }).key, 'door');
    // A doorway carved into a wall cell is authored as a door, not as the wall.
    assert.equal(Model.roleFromProvenance({ kind: 'cell', surface: 'east-wall', doorFace: true, x: 1, y: 1 }).key, 'door');
    // A fixture standing on a surface wins the selection: it is what is visible.
    assert.equal(Model.roleFromProvenance({ kind: 'cell', surface: 'south-wall', featureId: 'sconce', x: 1, y: 1 }).key, 'wall_feature');
    assert.equal(Model.roleFromProvenance({ kind: 'cell', surface: 'floor-feature', featureId: 'puddle', x: 1, y: 1 }).key, 'floor_feature');
    // Non-tileset provenance must not be claimed.
    assert.equal(Model.roleFromProvenance({ kind: 'event', id: 7 }), null);
    assert.equal(Model.roleFromProvenance(null), null);
});

test('a doorway attributes to the door pool, not the wall it was cut into', () => {
    // Regression: the realized census on a real Map showed 3 of 4 door-role
    // surfaces owned by `dungeon_wall_1`, because a doorway face carries the
    // wall's variantId in `variantId` and the actual owner in `doorVariantId`.
    const doorway = {
        kind: 'cell', surface: 'east-wall', doorFace: true,
        x: 4, y: 5, variantId: 'wall_a', doorVariantId: 'door_a',
    };
    assert.equal(Model.roleFromProvenance(doorway).key, 'door');
    assert.equal(Model.ownerVariantId(doorway), 'door_a');
    const census = Model.realizedCensus([doorway]);
    assert.deepEqual(census.door.byVariant, { door_a: 1 });
    assert.equal(census.wall, undefined, 'a doorway must not be counted as a wall');

    // A plain wall still reports the wall variant.
    assert.equal(Model.ownerVariantId({ kind: 'cell', surface: 'east-wall', x: 1, y: 1, variantId: 'wall_a' }), 'wall_a');
    // A fixture still wins over whatever it stands on.
    assert.equal(Model.ownerVariantId({
        kind: 'cell', surface: 'east-wall', x: 1, y: 1, variantId: 'wall_a', featureId: 'sconce',
    }), 'sconce');
    // A doorway with no resolved door variant is unknown, not the wall.
    assert.equal(Model.ownerVariantId({
        kind: 'cell', surface: 'east-wall', doorFace: true, x: 1, y: 1, variantId: 'wall_a',
    }), null);
});

test('the owning variant is found in the pool the provenance names', () => {
    const record = sampleRecord();
    const provenance = { kind: 'cell', surface: 'west-wall', x: 5, y: 6, variantId: 'wall_b' };
    const role = Model.roleFromProvenance(provenance);
    const variant = Model.findVariant(record, role.key, provenance.variantId);
    assert.ok(variant);
    assert.equal(variant.id, 'wall_b');
    assert.deepEqual(variant.middle, [1, 2]);
    // Feature pools are filtered by role, so a wall fixture is never offered as
    // a floor fixture.
    assert.deepEqual(Model.poolFor(record, 'wall_feature').map(v => v.id), ['sconce']);
    assert.deepEqual(Model.poolFor(record, 'floor_feature').map(v => v.id), ['puddle']);
});

test('authored share and engine-realized share stay separate facts', () => {
    const record = sampleRecord();
    const shares = Model.poolShares(Model.poolFor(record, 'wall'));
    assert.equal(shares[0].weight, 60);
    assert.equal(Math.round(shares[0].share * 100), 75); // 60 of 80
    assert.equal(Math.round(shares[1].share * 100), 25);

    // The realized census counts CELLS off the compiled bundle. One wall cell
    // emitting four faces plus a height mesh must count once.
    const provenance = [
        { kind: 'cell', surface: 'north-wall', x: 1, y: 1, variantId: 'wall_a' },
        { kind: 'cell', surface: 'south-wall', x: 1, y: 1, variantId: 'wall_a' },
        { kind: 'cell', surface: 'east-wall', x: 1, y: 1, variantId: 'wall_a' },
        { kind: 'cell', surface: 'west-wall', x: 2, y: 1, variantId: 'wall_b' },
        { kind: 'cell', surface: 'floor', x: 4, y: 4, variantId: 'floor_a' },
    ];
    const census = Model.realizedCensus(provenance);
    assert.equal(census.wall.total, 2);
    assert.equal(census.wall.byVariant.wall_a, 1);
    assert.equal(census.wall.byVariant.wall_b, 1);
    const realized = Model.realizedShare(census, 'wall', 'wall_a');
    assert.equal(realized.cells, 1);
    assert.equal(realized.total, 2);
    // Realized 50% deliberately disagrees with authored 75%: that difference is
    // the point of showing both, so it must not be smoothed away.
    assert.equal(Math.round(realized.share * 100), 50);
    assert.equal(Model.realizedShare(census, 'wall', 'wall_missing').cells, 0);
});

test('visual assignment produces the persisted shape without typed coordinates', () => {
    const record = sampleRecord();
    const wall = Model.findVariant(record, 'wall', 'wall_a');
    const ok = Model.assignVisual(wall, 'wall', { row: 5, col: 2, columns: 8 });
    assert.deepEqual(ok, { ok: true, assigned: 'wall-triptych' });
    assert.deepEqual(wall.middle, [5, 2]);
    assert.deepEqual(wall.leftEdge, [5, 3, 0]);
    assert.deepEqual(wall.rightEdge, [5, 3, 32]);

    // A wall needs a join column to its right; refusing is better than writing
    // an out-of-range region.
    assert.equal(Model.assignVisual(wall, 'wall', { row: 5, col: 7, columns: 8 }).reason,
        'wall-needs-join-column');

    const floor = Model.findVariant(record, 'floor', 'floor_a');
    assert.deepEqual(Model.assignVisual(floor, 'floor', { row: 2, col: 3 }), { ok: true, assigned: 'single-cell' });
    assert.deepEqual(floor.atlas, [2, 3]);
    assert.equal(Model.assignVisual(floor, 'floor', { row: -1, col: 0 }).reason, 'bad-cell');
});

test('new variants match the schema the runtime already reads', () => {
    const record = sampleRecord();
    const id = Model.suggestVariantId(record, 'wall', 'wall_a');
    assert.equal(id, 'wall_a_2', 'must not collide with an existing authored id');
    const variant = Model.newVariant('wall', id);
    assert.equal(variant.role, 'base_wall');
    assert.equal(variant.weight, 100);
    assert.ok(Array.isArray(variant.leftEdge) && variant.leftEdge.length === 3);
    assert.equal(Model.newVariant('wall_feature', 'x').role, 'wall_feature');
    assert.equal(Model.newVariant('floor_feature', 'x').role, 'floor_feature');
    assert.equal(Model.newVariant('floor', 'x').role, 'base_floor');

    // Adding through the backing array keeps pool membership truthful.
    Model.backingArray(record, 'wall').push(variant);
    assert.equal(Model.poolFor(record, 'wall').length, 3);
    Model.backingArray(record, 'wall_feature').push(Model.newVariant('wall_feature', 'brazier'));
    assert.equal(Model.poolFor(record, 'wall_feature').length, 2);
    assert.equal(Model.poolFor(record, 'floor_feature').length, 1);
});

test('placement presets round-trip against the real predicate vocabulary', () => {
    const variant = { id: 'sconce', role: 'wall_feature', injectProbability: 0.2 };
    assert.equal(Model.placementPresetOf(variant.where), 'anywhere');

    Model.applyPlacementPreset(variant, 'beside_floor');
    assert.deepEqual(variant.where, { adjacent: 'floor' });
    assert.equal(Model.placementPresetOf(variant.where), 'beside_floor');

    Model.applyPlacementPreset(variant, 'anywhere');
    assert.equal(variant.where, undefined);

    // A prefab and an inline predicate are mutually exclusive in the runtime.
    variant.prefab = 'some_prefab';
    Model.applyPlacementPreset(variant, 'beside_wall');
    assert.equal(variant.prefab, undefined);
    assert.deepEqual(variant.where, { adjacent: 'wall' });

    // An authored rule outside the presets stays 'custom' rather than being
    // silently rewritten to the nearest preset.
    variant.where = { distance: { feature: 'sconce', min: 3 } };
    assert.equal(Model.placementPresetOf(variant.where), 'custom');

    assert.equal(Model.setChancePercent(variant, 35).ok, true);
    assert.equal(variant.injectProbability, 0.35);
    assert.equal(Model.chancePercent(variant), 35);
    assert.equal(Model.setChancePercent(variant, 140).ok, false);
    assert.equal(variant.injectProbability, 0.35, 'a rejected value must not half-mutate the record');
});

test('emission authors the shape the runtime lighting path consumes', () => {
    const variant = { id: 'sconce', role: 'wall_feature' };
    Model.setEmission(variant, 'warm');
    assert.equal(variant.emitsLight.color.length, 3);
    assert.equal(typeof variant.emitsLight.radius, 'number');
    assert.equal(typeof variant.emitsLight.falloff, 'number');
    Model.setEmission(variant, 'none');
    assert.equal(variant.emitsLight, undefined);
});

test('the record transaction is local and stale-safe', () => {
    const record = sampleRecord();
    record._storageVersion = 'v1';
    const baseline = JSON.stringify(record);
    assert.equal(Model.recordIsDirty(record, baseline), false);
    record.base.walls[0].weight = 61;
    assert.equal(Model.recordIsDirty(record, baseline), true);

    const payload = Model.savePayload(record);
    // The version token travels so the server can refuse a stale write.
    assert.equal(payload._storageVersion, 'v1');
    // Legacy derived keys are not resurrected by this prototype.
    record.wallRows = [1, 2];
    assert.equal(Model.savePayload(record).wallRows, undefined);

    // Discard restores the loaded revision exactly.
    const restored = JSON.parse(baseline);
    assert.equal(restored.base.walls[0].weight, 60);
});

test('the prototype contains no second weighted-variant resolver', () => {
    const source = fs.readFileSync(path.join(__dirname, 'js', 'tileset-map-context-model.js'), 'utf8')
        + fs.readFileSync(path.join(__dirname, 'js', 'tileset-map-context.js'), 'utf8');
    // Negative control: the engine's variant choice must arrive as provenance.
    // Any cell hashing, weight-summing draw, or atlas packing here would be a
    // competing compiler, which #547 forbids.
    for (const forbidden of ['cellHash', 'Math.random', 'resolveWeightedVariant', '73856093', '19349663']) {
        assert.ok(!source.includes(forbidden),
            `prototype must not reimplement runtime resolution (found '${forbidden}')`);
    }
    // And it must actually read the engine's answer.
    assert.ok(source.includes('variantId'), 'prototype must consume engine-provided variant provenance');
});

test('the experiment is opt-in so committed editor canon is unaffected', () => {
    const source = fs.readFileSync(path.join(__dirname, 'js', 'tileset-map-context.js'), 'utf8');
    assert.ok(source.includes("localStorage.getItem(FLAG) === '1'"));
    assert.ok(/if \(!enabled\(\)\) return;/.test(source),
        'the module must bail out before touching the DOM when the flag is off');
    const bootstrap = fs.readFileSync(path.join(__dirname, 'js', 'event_presentation.js'), 'utf8');
    assert.ok(bootstrap.includes('/js/tileset-map-context.js'), 'the experiment must be reachable');
    // The experiment must not even be FETCHED by default. Two unconditional
    // script loads shifted the bootstrap enough to move an animated Database
    // sprite preview to another frame and turned G6 red.
    assert.ok(/if \(!wanted\) return null;/.test(bootstrap),
        'the bootstrap must skip loading the experiment when the flag is off');
    const gateIndex = bootstrap.indexOf('wanted');
    const loadIndex = bootstrap.indexOf("loadScript('/js/tileset-map-context-model.js')");
    assert.ok(gateIndex > 0 && loadIndex > gateIndex,
        'the flag check must precede the experiment script loads');
});

test('no authored object crosses a window boundary', () => {
    const source = fs.readFileSync(path.join(__dirname, 'js', 'tileset-map-context.js'), 'utf8');
    // The only cross-surface calls allowed are resource-identity announcement
    // and re-reading the Project authority.
    assert.ok(source.includes("announceResourceCommit(['tilesets'])"));
    assert.ok(source.includes("fetch('/api/tilesets')"), 'the record must be re-read from the Project');
    assert.ok(!/announceResourceCommit\([^)]*record/.test(source),
        'a commit announcement must carry resource identity, never the record');
    assert.ok(!/postMessage|ipcRenderer\.send/.test(source),
        'the prototype must not invent an authored-object transport');
});
