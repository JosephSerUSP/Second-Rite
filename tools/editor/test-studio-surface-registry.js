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
    assert.deepEqual(SURFACE_IDS, ['main', 'database']);
    assert.equal(SURFACES.main.category, 'workspace');
    assert.equal(SURFACES.main.secondary, false);
    assert.equal(SURFACES.main.multiplicity, 'singleton');

    assert.equal(SURFACES.database.category, 'editor');
    assert.equal(SURFACES.database.multiplicity, 'singleton');
    assert.equal(SURFACES.database.productionHost, 'native');
    assert.equal(SURFACES.database.browserTestHost, 'dom-modal');
});

test('secondary native ids are derived from registry policy', () => {
    assert.deepEqual(SECONDARY_NATIVE_SURFACE_IDS, ['database']);
    assert.equal(getSurfacePolicy('database'), SURFACES.database);
    assert.equal(getSurfacePolicy('missing'), null);
    assert.throws(() => requireSurfacePolicy('missing'), /Unknown EditorSurface/);
});

test('surface registry policies are immutable', () => {
    assert.equal(Object.isFrozen(SURFACES), true);
    assert.equal(Object.isFrozen(SURFACES.main), true);
    assert.equal(Object.isFrozen(SURFACES.database), true);
    assert.equal(Object.isFrozen(SECONDARY_NATIVE_SURFACE_IDS), true);
});
