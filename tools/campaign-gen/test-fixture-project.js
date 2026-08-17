'use strict';

const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const FixtureProject = require('./fixture-project.js');

const installRoot = path.resolve(__dirname, '..', '..');
const projectsRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'thestra-generated-projects-'));
const previousRoot = process.env[FixtureProject.PROJECTS_ROOT_ENV];
const canonicalRolesPath = path.join(installRoot, 'data', 'roles.json');
const canonicalRolesBefore = fs.readFileSync(canonicalRolesPath, 'utf8');

process.env[FixtureProject.PROJECTS_ROOT_ENV] = projectsRoot;
try {
    (function testBootstrapCreatesNeutralSparseProject() {
        const project = FixtureProject.bootstrapFixtureProject({ installRoot, name: 'mist-isle_2' });
        assert.strictEqual(project.projectRoot, path.join(projectsRoot, 'mist-isle_2'));
        assert.strictEqual(project.statePath, path.join(project.projectRoot, FixtureProject.STATE_FILE));
        assert.strictEqual(project.bootstrapMode, 'sparse');
        assert.strictEqual(project.rtpRevision, '1.0');

        const roles = JSON.parse(fs.readFileSync(path.join(project.dataPath, 'roles.json'), 'utf8'));
        const skills = JSON.parse(fs.readFileSync(path.join(project.dataPath, 'skills.json'), 'utf8'));
        const unitsIndex = JSON.parse(fs.readFileSync(path.join(project.dataPath, 'units', 'index.json'), 'utf8'));
        const mapsIndex = JSON.parse(fs.readFileSync(path.join(project.dataPath, 'maps', 'index.json'), 'utf8'));
        const firstMap = JSON.parse(fs.readFileSync(path.join(project.dataPath, 'maps', mapsIndex.files[0]), 'utf8'));
        const system = JSON.parse(fs.readFileSync(path.join(project.dataPath, 'system.json'), 'utf8'));

        assert.deepStrictEqual(roles, {});
        assert.deepStrictEqual(skills, {});
        assert.deepStrictEqual(unitsIndex, { files: [] });
        assert.strictEqual(firstMap.title, 'First Map');
        assert.deepStrictEqual(system.rtp, { revision: '1.0' });
        assert.strictEqual(fs.readFileSync(canonicalRolesPath, 'utf8'), canonicalRolesBefore);
    })();

    (function testExistingFixtureIsNeverOverwritten() {
        assert.throws(
            () => FixtureProject.bootstrapFixtureProject({ installRoot, name: 'mist-isle_2' }),
            /already exists/
        );
        assert.deepStrictEqual(
            JSON.parse(fs.readFileSync(path.join(projectsRoot, 'mist-isle_2', 'data', 'roles.json'), 'utf8')),
            {}
        );
    })();

    (function testUnsafeNamesCannotBecomeFixturePaths() {
        for (const unsafe of ['', '..', '../outside', 'two/parts', 'has space', 'UPPER', '.hidden']) {
            assert.throws(() => FixtureProject.fixtureProjectPath(installRoot, unsafe), /name must contain/);
        }
    })();

    (function testCleanupCannotEscapeConfiguredRoot() {
        const outside = path.join(projectsRoot, '..', 'outside-generated-project-proof.txt');
        fs.writeFileSync(outside, 'keep', 'utf8');
        try {
            FixtureProject.cleanFixtureProject({ installRoot, name: 'mist-isle_2' });
            assert.ok(!fs.existsSync(path.join(projectsRoot, 'mist-isle_2')));
            assert.strictEqual(fs.readFileSync(outside, 'utf8'), 'keep');
            assert.throws(
                () => FixtureProject.cleanFixtureProject({ installRoot, name: '../outside' }),
                /name must contain/
            );
        } finally {
            fs.rmSync(outside, { force: true });
        }
    })();

    assert.strictEqual(fs.readFileSync(canonicalRolesPath, 'utf8'), canonicalRolesBefore);
    console.log('Sparse generator Project isolation tests OK');
} finally {
    if (previousRoot === undefined) delete process.env[FixtureProject.PROJECTS_ROOT_ENV];
    else process.env[FixtureProject.PROJECTS_ROOT_ENV] = previousRoot;
    fs.rmSync(projectsRoot, { recursive: true, force: true });
}
