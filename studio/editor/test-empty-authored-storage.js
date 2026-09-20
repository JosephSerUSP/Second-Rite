'use strict';

const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const test = require('node:test');
const lifecycle = require('./project-lifecycle');
const storage = require('./authored-storage');

function withSparseProject(fn) {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'thestra-empty-storage-'));
    try {
        const project = path.join(root, 'blank');
        lifecycle.createSparseProject({ target: project, name: 'Blank' });
        return fn(project, path.join(project, 'data'));
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
    }
}

test('Studio reads explicitly empty ordered and keyed Project catalogs', () => {
    withSparseProject((_project, dataRoot) => {
        const units = storage.loadOrderedCollection(dataRoot, 'units');
        assert.deepEqual(units.entries, []);
        assert.equal(units.storage, 'fragments');

        const tilesets = storage.loadRegistry(dataRoot, 'tilesets');
        assert.deepEqual(tilesets.records, {});
        assert.equal(tilesets.storage, 'fragments');
        assert.ok(storage.versionToken(dataRoot, 'units'));
        assert.ok(storage.versionToken(dataRoot, 'tilesets'));
    });
});

test('Studio can add the first record to an explicitly empty catalog', () => {
    withSparseProject((_project, dataRoot) => {
        storage.writeResource(dataRoot, 'units', [{ id: 'first_unit' }]);
        const units = storage.loadOrderedCollection(dataRoot, 'units');
        assert.deepEqual(units.entries.map(entry => entry.id), ['first_unit']);
        assert.deepEqual(JSON.parse(fs.readFileSync(path.join(dataRoot, 'units', 'index.json'), 'utf8')).files,
            ['first_unit.json']);

        storage.writeRegistryRecord(dataRoot, 'tilesets', { id: 'first_tileset' });
        const tilesets = storage.loadRegistry(dataRoot, 'tilesets');
        assert.deepEqual(Object.keys(tilesets.records), ['first_tileset']);
        assert.ok(!fs.existsSync(path.join(dataRoot, 'tilesets', 'index.json')),
            'keyed registry empty marker must disappear when the first record is authored');
    });
});

test('Studio can deliberately clear populated catalogs back to explicit empty state', () => {
    withSparseProject((_project, dataRoot) => {
        storage.writeResource(dataRoot, 'units', [{ id: 'first_unit' }]);
        storage.writeResource(dataRoot, 'units', []);
        assert.deepEqual(storage.loadOrderedCollection(dataRoot, 'units').entries, []);
        assert.deepEqual(JSON.parse(fs.readFileSync(path.join(dataRoot, 'units', 'index.json'), 'utf8')), { files: [] });

        storage.writeRegistryRecord(dataRoot, 'tilesets', { id: 'first_tileset' });
        storage.writeResource(dataRoot, 'tilesets', {});
        assert.deepEqual(storage.loadRegistry(dataRoot, 'tilesets').records, {});
        assert.deepEqual(JSON.parse(fs.readFileSync(path.join(dataRoot, 'tilesets', 'index.json'), 'utf8')), { files: [] });
    });
});

test('explicit empty catalog markers are Project-only and do not relax other validation', () => {
    const nonProjectRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'thestra-non-project-storage-'));
    try {
        assert.throws(() => storage.writeResource(nonProjectRoot, 'units', []),
            /ordered collection 'units' must be a non-empty array: <write units>/);
    } finally {
        fs.rmSync(nonProjectRoot, { recursive: true, force: true });
    }

    withSparseProject((_project, dataRoot) => {
        assert.throws(() => storage.writeResource(dataRoot, 'flows', {}),
            /semantic config 'flows' is missing module 'battle': <write flows>/);
    });
});
