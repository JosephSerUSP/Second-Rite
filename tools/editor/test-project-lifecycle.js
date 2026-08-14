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

test('fork may target projects/labs under the same checkout', () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'thestra-in-repo-'));
    try {
        const source = makeProject(root, 'checkout');
        fs.mkdirSync(path.join(source, 'projects', 'labs'), { recursive: true });
        const target = path.join(source, 'projects', 'labs', 'tiny-game');
        lifecycle.forkProject({ source, target, installRoot: source });
        assert.ok(fs.existsSync(path.join(target, 'data', 'system.json')));
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

test('sparse creation reports its current neutral-default dependency', () => {
    const status = lifecycle.sparseProjectAvailability();
    assert.equal(status.available, false);
    assert.equal(status.code, lifecycle.SPARSE_UNAVAILABLE);
    assert.match(status.reason, /#390/);
});
