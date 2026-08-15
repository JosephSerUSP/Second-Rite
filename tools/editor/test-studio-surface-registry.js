'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');
const {
    SURFACES,
    SURFACE_IDS,
    SECONDARY_NATIVE_SURFACE_IDS,
    getSurfacePolicy,
    requireSurfacePolicy,
} = require('./studio-surface-registry');

test('EditorSurface registry distinguishes semantic identity from host policy', () => {
    assert.deepEqual(SURFACE_IDS, ['main', 'database', 'engine', 'tileset']);
    assert.equal(SURFACES.main.category, 'workspace');
    assert.equal(SURFACES.main.secondary, false);
    assert.equal(SURFACES.main.multiplicity, 'singleton');

    for (const id of ['database', 'engine', 'tileset']) {
        assert.equal(SURFACES[id].category, 'editor');
        assert.equal(SURFACES[id].multiplicity, 'singleton');
        assert.equal(SURFACES[id].productionHost, 'native');
        assert.equal(SURFACES[id].browserTestHost, 'dom-modal');
    }
    assert.equal(SURFACES.database.closePolicy, 'resource-transaction');
    assert.equal(SURFACES.engine.closePolicy, 'resource-transaction');
    assert.equal(SURFACES.tileset.closePolicy, 'record-transaction');
    assert.equal(SURFACES.database.displayName, 'Database');
    assert.equal(SURFACES.engine.displayName, 'Engine Editor');
    assert.equal(SURFACES.tileset.displayName, 'Tileset Studio');
});

test('secondary native ids are derived from registry policy', () => {
    assert.deepEqual(SECONDARY_NATIVE_SURFACE_IDS, ['database', 'engine', 'tileset']);
    assert.equal(getSurfacePolicy('database'), SURFACES.database);
    assert.equal(getSurfacePolicy('engine'), SURFACES.engine);
    assert.equal(getSurfacePolicy('tileset'), SURFACES.tileset);
    assert.equal(getSurfacePolicy('missing'), null);
    assert.throws(() => requireSurfacePolicy('missing'), /Unknown EditorSurface/);
});

test('surface registry policies are immutable', () => {
    assert.equal(Object.isFrozen(SURFACES), true);
    assert.equal(Object.isFrozen(SURFACES.main), true);
    assert.equal(Object.isFrozen(SURFACES.database), true);
    assert.equal(Object.isFrozen(SURFACES.engine), true);
    assert.equal(Object.isFrozen(SURFACES.tileset), true);
    assert.equal(Object.isFrozen(SECONDARY_NATIVE_SURFACE_IDS), true);
});
