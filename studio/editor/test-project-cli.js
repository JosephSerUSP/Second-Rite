'use strict';

const assert = require('assert');
const childProcess = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');
const test = require('node:test');
const lifecycle = require('./project-lifecycle');
const { resolveLoveExecutable, run, usage } = require('./project-cli');

const REPO = path.resolve(__dirname, '..', '..');
const CLI = path.join(__dirname, 'project-cli.js');

test('Project CLI exposes play as a first-class ordinary Project action', () => {
    let played = null;
    const relative = path.join('projects', 'labs', 'scene-benchmarks');
    const code = run(['play', relative], {
        playProject(projectPath) {
            played = projectPath;
        },
    });

    assert.equal(code, 0);
    assert.equal(played, path.resolve(relative));
    assert.match(usage(), /play <project>/);
    assert.match(usage(), /ordinary Test Play boundary/);
});

test('Project CLI exposes generic authored-default inspection and Make Local commands', () => {
    assert.match(usage(), /authored <project> <resource>/);
    assert.match(usage(), /make-local <project> <resource>/);
    assert.match(usage(), /which provider currently supplies one inherited authored resource/);
    assert.match(usage(), /copies that resolved authored resource into the Project/);
});

test('Project CLI authored and make-local operate on a real sparse Project', () => {
    const work = fs.mkdtempSync(path.join(os.tmpdir(), 'thestra-project-cli-authored-'));
    try {
        const project = path.join(work, 'game');
        lifecycle.createSparseProject({ target: project, installRoot: REPO, name: 'CLI Authored Proof' });

        const inspect = childProcess.spawnSync(process.execPath,
            [CLI, 'authored', project, 'progression', '--json'],
            { cwd: REPO, encoding: 'utf8' });
        assert.equal(inspect.status, 0, inspect.stderr);
        const inherited = JSON.parse(inspect.stdout.trim());
        assert.equal(inherited.resource, 'progression');
        assert.equal(inherited.provider, 'rtp');
        assert.equal(inherited.revision, '1.0');

        const materialize = childProcess.spawnSync(process.execPath,
            [CLI, 'make-local', project, 'progression', '--json'],
            { cwd: REPO, encoding: 'utf8' });
        assert.equal(materialize.status, 0, materialize.stderr);
        const local = JSON.parse(materialize.stdout.trim());
        assert.equal(local.madeLocal, true);
        assert.equal(local.provider, 'project');
        assert.equal(fs.existsSync(path.join(project, 'data', 'progression.json')), true);

        const inspectAgain = childProcess.spawnSync(process.execPath,
            [CLI, 'authored', project, 'progression', '--json'],
            { cwd: REPO, encoding: 'utf8' });
        assert.equal(inspectAgain.status, 0, inspectAgain.stderr);
        assert.equal(JSON.parse(inspectAgain.stdout.trim()).provider, 'project');
    } finally {
        fs.rmSync(work, { recursive: true, force: true });
    }
});

test('Project CLI play rejects JSON output mode rather than implying a synchronous result', () => {
    assert.throws(
        () => run(['play', 'projects/labs/scene-benchmarks', '--json'], { playProject() {} }),
        /play does not support --json/,
    );
});

test('LOVE_PATH overrides the platform default for Project Test Play', () => {
    assert.equal(resolveLoveExecutable({ LOVE_PATH: '/custom/love' }, 'linux'), '/custom/love');
    assert.equal(resolveLoveExecutable({}, 'win32'), 'C:\\Program Files\\LOVE\\love.exe');
    assert.equal(resolveLoveExecutable({}, 'linux'), 'love');
});

test('lab:benchmarks invokes the generic Project play command rather than Studio', () => {
    const pkg = require('../../package.json');
    assert.equal(pkg.scripts['lab:benchmarks'], 'node tools/editor/project-cli.js play projects/labs/scene-benchmarks');
});