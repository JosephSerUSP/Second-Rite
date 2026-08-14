'use strict';

const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const FixtureProject = require('./fixture-project.js');

function write(root, relative, text) {
    const destination = path.join(root, relative);
    fs.mkdirSync(path.dirname(destination), { recursive: true });
    fs.writeFileSync(destination, text, 'utf8');
}

const installRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'second-rite-fixture-project-'));
try {
    write(installRoot, 'data/maps.json', '{"maps":["source"]}');
    write(installRoot, 'data/nested/schema.json', '{"version":1}');
    write(installRoot, 'assets/sprites/hero.txt', 'source-sprite');
    write(installRoot, 'assets/models/door/model.txt', 'source-model');

    (function testBootstrapCreatesAnIsolatedProjectShape() {
        const project = FixtureProject.bootstrapFixtureProject({ installRoot, name: 'mist-isle_2' });
        assert.strictEqual(project.projectRoot,
            path.join(installRoot, 'tmp', 'generated-projects', 'mist-isle_2'));
        assert.strictEqual(project.statePath,
            path.join(project.projectRoot, FixtureProject.STATE_FILE));
        assert.strictEqual(fs.readFileSync(path.join(project.dataPath, 'maps.json'), 'utf8'), '{"maps":["source"]}');
        assert.strictEqual(fs.readFileSync(path.join(project.assetsPath, 'models', 'door', 'model.txt'), 'utf8'), 'source-model');

        fs.writeFileSync(path.join(project.dataPath, 'maps.json'), '{"maps":["fixture"]}', 'utf8');
        fs.writeFileSync(path.join(project.assetsPath, 'sprites', 'hero.txt'), 'fixture-sprite', 'utf8');
        assert.strictEqual(fs.readFileSync(path.join(installRoot, 'data', 'maps.json'), 'utf8'), '{"maps":["source"]}');
        assert.strictEqual(fs.readFileSync(path.join(installRoot, 'assets', 'sprites', 'hero.txt'), 'utf8'), 'source-sprite');
    })();

    (function testExistingFixtureIsNeverOverwritten() {
        assert.throws(
            () => FixtureProject.bootstrapFixtureProject({ installRoot, name: 'mist-isle_2' }),
            /already exists/
        );
        assert.strictEqual(
            fs.readFileSync(path.join(installRoot, 'tmp', 'generated-projects', 'mist-isle_2', 'data', 'maps.json'), 'utf8'),
            '{"maps":["fixture"]}'
        );
    })();

    (function testUnsafeNamesCannotBecomeFixturePaths() {
        for (const unsafe of ['', '..', '../outside', 'two/parts', 'has space', 'UPPER', '.hidden']) {
            assert.throws(() => FixtureProject.fixtureProjectPath(installRoot, unsafe), /name must contain/);
        }
    })();

    (function testCleanupCannotEscapeTheFixedRoot() {
        const outside = path.join(installRoot, 'outside.txt');
        fs.writeFileSync(outside, 'keep', 'utf8');
        FixtureProject.cleanFixtureProject({ installRoot, name: 'mist-isle_2' });
        assert.ok(!fs.existsSync(path.join(installRoot, 'tmp', 'generated-projects', 'mist-isle_2')));
        assert.strictEqual(fs.readFileSync(outside, 'utf8'), 'keep');
        assert.throws(
            () => FixtureProject.cleanFixtureProject({ installRoot, name: '../outside' }),
            /name must contain/
        );
    })();

    console.log('Fixture Project tests OK');
} finally {
    fs.rmSync(installRoot, { recursive: true, force: true });
}
