const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const storage = require('./authored-storage');

function writeJson(filePath, value) {
    fs.mkdirSync(path.dirname(filePath), { recursive: true });
    fs.writeFileSync(filePath, JSON.stringify(value, null, 2) + '\n', 'utf8');
}

const orderedFragments = { kind: 'ordered_collection', representation: 'fragments' };
const semanticFragments = { kind: 'semantic_config', representation: 'fragments', modules: ['battle', 'quest'] };
const root = fs.mkdtempSync(path.join(os.tmpdir(), 'second-rite-authored-storage-'));
try {
    const manifest = storage.loadManifest();
    assert.equal(storage.resourceSpec('scenes', manifest).kind, 'ordered_collection');
    assert.equal(storage.resourceSpec('scenes', manifest).representation, 'fragments');
    assert.equal(storage.resourceSpec('tilesets', manifest).kind, 'keyed_registry');
    assert.equal(storage.resourceSpec('tilesets', manifest).representation, 'fragments');
    assert.ok(storage.bulkEditableResources(manifest).includes('scenes'));
    assert.ok(!storage.bulkEditableResources(manifest).includes('tilesets'));

    writeJson(path.join(root, 'system.json'), { title: 'Fixture' });
    let loadedResource = storage.loadResource(root, 'system');
    assert.deepEqual(loadedResource.value, { title: 'Fixture' });
    assert.equal(loadedResource.storage, 'monolith');

    writeJson(path.join(root, 'scenes', 'index.json'), { files: ['fragment.json'] });
    writeJson(path.join(root, 'scenes', 'fragment.json'), { id: 'fragment', name: 'Authoritative' });
    loadedResource = storage.loadResource(root, 'scenes');
    assert.equal(loadedResource.value[0].id, 'fragment');
    assert.equal(loadedResource.storage, 'fragments');
    writeJson(path.join(root, 'scenes.json'), [{ id: 'legacy', name: 'Forbidden dual source' }]);
    assert.throws(() => storage.loadResource(root, 'scenes'), /both fragment storage and legacy monolith/);
    fs.unlinkSync(path.join(root, 'scenes.json'));

    writeJson(path.join(root, 'tilesets', 'wrong-name.json'), { id: 'alpha', name: 'Alpha' });
    writeJson(path.join(root, 'tilesets', 'beta.json'), { id: 'beta', name: 'Beta' });
    let loaded = storage.loadRegistry(root, 'tilesets');
    assert.equal(loaded.storage, 'fragments');
    assert.equal(loaded.records.alpha.name, 'Alpha');
    assert.ok(loaded.sourceById.alpha.endsWith('wrong-name.json'));

    const betaBefore = fs.readFileSync(path.join(root, 'tilesets', 'beta.json'), 'utf8');
    const fragmentVersion = storage.versionToken(root, 'tilesets');
    storage.writeRegistryRecord(root, 'tilesets', { id: 'alpha', name: 'Alpha edited' }, fragmentVersion);
    assert.equal(fs.readFileSync(path.join(root, 'tilesets', 'beta.json'), 'utf8'), betaBefore);
    assert.equal(storage.loadRegistry(root, 'tilesets').records.alpha.name, 'Alpha edited');
    assert.notEqual(storage.versionToken(root, 'tilesets'), fragmentVersion);

    assert.throws(
        () => storage.writeRegistryRecord(root, 'tilesets', { id: 'alpha', name: 'stale' }, fragmentVersion),
        err => err && err.code === 'STALE_AUTHORED_DATA'
    );

    storage.writeRegistryRecord(root, 'tilesets', { id: 'gamma', name: 'Gamma' });
    assert.equal(storage.loadRegistry(root, 'tilesets').records.gamma.name, 'Gamma');
    assert.ok(fs.existsSync(path.join(root, 'tilesets', 'gamma.json')));

    writeJson(path.join(root, 'flows', 'battle.json'), { round_start: [] });
    writeJson(path.join(root, 'flows', 'quest.json'), { offer: [] });
    const flows = storage.loadResource(root, 'flows', semanticFragments);
    assert.deepEqual(flows.value, { battle: { round_start: [] }, quest: { offer: [] } });
    const questBefore = fs.readFileSync(path.join(root, 'flows', 'quest.json'), 'utf8');
    storage.writeResource(root, 'flows', { battle: { round_start: [{ cmd: 'TEST' }] }, quest: { offer: [] } }, semanticFragments);
    assert.equal(fs.readFileSync(path.join(root, 'flows', 'quest.json'), 'utf8'), questBefore);

    writeJson(path.join(root, 'chapters', 'stale.json'), { id: 'stale' });
    storage.writeResource(root, 'chapters', [
        { id: 'opening', name: 'Opening' },
        { id: 'boss room', name: 'Boss' },
    ], orderedFragments);
    assert.ok(!fs.existsSync(path.join(root, 'chapters', 'stale.json')));
    const index = JSON.parse(fs.readFileSync(path.join(root, 'chapters', 'index.json'), 'utf8'));
    assert.deepEqual(index.files, ['opening.json', 'boss-room--626f737320726f6f6d.json']);
    let chapters = storage.loadResource(root, 'chapters', orderedFragments);
    assert.deepEqual(chapters.value.map(entry => entry.id), ['opening', 'boss room']);
    const unchangedFragment = fs.readFileSync(path.join(root, 'chapters', 'boss-room--626f737320726f6f6d.json'), 'utf8');
    const unchangedIndex = fs.readFileSync(path.join(root, 'chapters', 'index.json'), 'utf8');
    storage.writeResource(root, 'chapters', [
        { id: 'opening', name: 'Opening edited' },
        { id: 'boss room', name: 'Boss' },
    ], orderedFragments);
    assert.equal(fs.readFileSync(path.join(root, 'chapters', 'boss-room--626f737320726f6f6d.json'), 'utf8'), unchangedFragment);
    assert.equal(fs.readFileSync(path.join(root, 'chapters', 'index.json'), 'utf8'), unchangedIndex);
    chapters = storage.loadResource(root, 'chapters', orderedFragments);

    const beforeInvalid = fs.readFileSync(path.join(root, 'chapters', 'index.json'), 'utf8');
    assert.throws(
        () => storage.writeResource(root, 'chapters', [{ id: 'same' }, { id: 'same' }], orderedFragments),
        /duplicate id 'same'/
    );
    assert.equal(fs.readFileSync(path.join(root, 'chapters', 'index.json'), 'utf8'), beforeInvalid);

    const snapshots = path.join(root, 'snapshots');
    const snapshot = storage.snapshotResource(root, 'chapters', snapshots, orderedFragments);
    assert.deepEqual(JSON.parse(fs.readFileSync(snapshot, 'utf8')), chapters.value);

    writeJson(path.join(root, 'tilesets', 'index.json'), { files: [] });
    assert.throws(() => storage.loadRegistry(root, 'tilesets'), /must not use a shared index\.json/);

    console.log('authored-storage node tests: OK');
} finally {
    fs.rmSync(root, { recursive: true, force: true });
}
