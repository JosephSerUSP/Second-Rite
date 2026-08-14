'use strict';

const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const test = require('node:test');
const lifecycle = require('./project-lifecycle');

function write(root, relative, value) {
    const file = path.join(root, relative);
    fs.mkdirSync(path.dirname(file), { recursive: true });
    fs.writeFileSync(file, value, 'utf8');
}

function makeProject(parent, name) {
    const root = path.join(parent, name || 'source');
    fs.mkdirSync(root);
    write(root, 'data/system.json', '{"ui":{}}');
    write(root, 'data/maps.json', '[{"id":1}]');
    write(root, 'assets/sprites/hero.txt', 'source-asset');
    write(root, 'notes.txt', 'not-project-owned');
    return root;
}

function readTreeText(root) {
    const chunks = [];
    function walk(dir) {
        for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
            const full = path.join(dir, entry.name);
            if (entry.isDirectory()) walk(full);
            else chunks.push(fs.readFileSync(full, 'utf8'));
        }
    }
    walk(root);
    return chunks.join('\n');
}

test('fork copies only Project-owned data/assets and isolates later edits', () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'thestra-lifecycle-'));
    try {
        const source = makeProject(root);
        const target = path.join(root, 'forked');
        const sourceMaps = fs.readFileSync(path.join(source, 'data', 'maps.json'), 'utf8');
        const result = lifecycle.forkProject({ source, target, installRoot: root });
        assert.equal(result.mode, 'fork');
        assert.ok(fs.existsSync(path.join(target, 'data', 'system.json')));
        assert.equal(fs.readFileSync(path.join(target, 'assets', 'sprites', 'hero.txt'), 'utf8'), 'source-asset');
        assert.ok(!fs.existsSync(path.join(target, 'notes.txt')));
        write(target, 'data/maps.json', '[{"id":9}]');
        assert.equal(fs.readFileSync(path.join(source, 'data', 'maps.json'), 'utf8'), sourceMaps);
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
    }
});

test('fork may create a missing projects/labs parent under the same checkout', () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'thestra-in-repo-'));
    try {
        const source = makeProject(root, 'checkout');
        const target = path.join(source, 'projects', 'labs', 'tiny-game');
        lifecycle.forkProject({ source, target, installRoot: source });
        assert.ok(fs.existsSync(path.join(target, 'data', 'system.json')));
        assert.ok(fs.existsSync(path.join(source, 'projects', 'labs')));
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
    }
});

test('fork refuses existing destinations and destinations under copied trees', () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'thestra-safety-'));
    try {
        const source = makeProject(root);
        const existing = path.join(root, 'existing');
        fs.mkdirSync(existing);
        assert.throws(() => lifecycle.forkProject({ source, target: existing }), /already exists/);

        const dataParent = path.join(source, 'data', 'generated');
        fs.mkdirSync(dataParent);
        assert.throws(() => lifecycle.forkProject({ source, target: path.join(dataParent, 'game') }), /inside source data/);

        const assetsParent = path.join(source, 'assets', 'generated');
        fs.mkdirSync(assetsParent);
        assert.throws(() => lifecycle.forkProject({ source, target: path.join(assetsParent, 'game') }), /inside source assets/);
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
    }
});

test('installed RTP 1.0 makes sparse New Project available', () => {
    const status = lifecycle.sparseProjectAvailability();
    assert.equal(status.available, true, status.reason);
    assert.equal(status.revision, '1.0');
});

test('sparse Project owns only neutral startup/data skeleton and inherits RTP defaults', () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'thestra-sparse-'));
    try {
        const target = path.join(root, 'tiny-game');
        const result = lifecycle.createSparseProject({ target, name: 'Tiny Game' });
        assert.equal(result.mode, 'sparse');
        assert.equal(result.rtpRevision, '1.0');
        assert.equal(JSON.parse(fs.readFileSync(path.join(target, 'data', 'system.json'), 'utf8')).rtp.revision, '1.0');
        assert.equal(JSON.parse(fs.readFileSync(path.join(target, 'data', 'terms.json'), 'utf8')).project.title, 'Tiny Game');

        assert.ok(!fs.existsSync(path.join(target, 'data', 'engine.json')), 'semantic engine registry must remain inherited');
        for (const inherited of ['save_menu.json', 'items.json', 'status.json', 'controls.json']) {
            assert.ok(!fs.existsSync(path.join(target, 'data', 'scenes', inherited)), `${inherited} must remain inherited`);
        }
        assert.ok(!fs.existsSync(path.join(target, 'data', 'flows', 'quest.json')), 'quest Flow must remain inherited');
        assert.deepEqual(JSON.parse(fs.readFileSync(path.join(target, 'data', 'units', 'index.json'), 'utf8')).files, []);
        assert.deepEqual(JSON.parse(fs.readFileSync(path.join(target, 'data', 'maps', 'index.json'), 'utf8')).files, ['1.json']);
        assert.deepEqual(JSON.parse(fs.readFileSync(path.join(target, 'data', 'scenes', 'index.json'), 'utf8')).files, ['title.json', 'map.json']);

        const text = readTreeText(target);
        for (const forbidden of ['Second Gate', 'Second Rite', 'St. Maria', 'Saban']) {
            assert.ok(!text.includes(forbidden), `sparse skeleton leaked Second Gate content: ${forbidden}`);
        }
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
    }
});

test('sparse Project refuses overwrite and fails when installed RTP baseline is unavailable', () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'thestra-sparse-safety-'));
    try {
        const existing = path.join(root, 'existing');
        fs.mkdirSync(existing);
        assert.throws(() => lifecycle.createSparseProject({ target: existing }), /already exists/);
        const fakeInstall = path.join(root, 'install');
        fs.mkdirSync(fakeInstall);
        const status = lifecycle.sparseProjectAvailability({ installRoot: fakeInstall });
        assert.equal(status.available, false);
        assert.throws(() => lifecycle.createSparseProject({ target: path.join(root, 'new'), installRoot: fakeInstall }), /manifest|RTP|revision/i);
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
    }
});
