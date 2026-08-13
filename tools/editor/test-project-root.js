'use strict';

// #237/#299: the project/install boundary. These are the gates the design doc
// names -- project paths cannot escape the selected root, and a minimal
// fixture Project can be opened from outside the Second Rite repository.
//
// project-root.js resolves PROJECT_ROOT at require time from the environment,
// so the fixture cases re-require it in a child process with the env set,
// which is also how the editor server will see it.

const assert = require('assert');
const childProcess = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');
const test = require('node:test');

const MODULE = path.join(__dirname, 'project-root.js');
const { INSTALL_ROOT, PROJECT_ENV, isProjectRoot, resolveProjectRoot, resolveWithin } = require(MODULE);

// Somewhere no part of this repository reaches, so "outside the checkout" is
// literally true rather than a subdirectory wearing a different name.
function makeFixtureProject() {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'sr-project-'));
    fs.mkdirSync(path.join(root, 'data'), { recursive: true });
    fs.writeFileSync(path.join(root, 'data', 'system.json'), JSON.stringify({ ui: {} }), 'utf8');
    fs.mkdirSync(path.join(root, 'assets', 'sprites'), { recursive: true });
    fs.writeFileSync(path.join(root, 'assets', 'sprites', 'hero.png'), 'png-bytes');
    return root;
}

// Asks the module, in a fresh process, what it resolved for a given env.
function resolveInChild(projectPath) {
    const script = `const p = require(${JSON.stringify(MODULE)});
        process.stdout.write(JSON.stringify({
            project: p.PROJECT_ROOT,
            install: p.INSTALL_ROOT,
            asset: p.inProject('assets', 'sprites', 'hero.png'),
        }));`;
    const env = Object.assign({}, process.env);
    if (projectPath === null) delete env[PROJECT_ENV];
    else env[PROJECT_ENV] = projectPath;
    const result = childProcess.spawnSync(process.execPath, ['-e', script], { env, encoding: 'utf8' });
    return { status: result.status, stdout: result.stdout, stderr: result.stderr };
}

test('the project root defaults to the installation', () => {
    const out = resolveInChild(null);
    assert.equal(out.status, 0, out.stderr);
    const parsed = JSON.parse(out.stdout);
    assert.equal(parsed.project, parsed.install, 'an ordinary checkout opens itself');
    assert.equal(parsed.install, INSTALL_ROOT);
});

// The load-bearing one: Studio correctness must not depend on being located
// inside the Second Rite source checkout.
test('a minimal project outside the repository can be opened', () => {
    const fixture = makeFixtureProject();
    try {
        const out = resolveInChild(fixture);
        assert.equal(out.status, 0, out.stderr);
        const parsed = JSON.parse(out.stdout);
        assert.equal(parsed.project, fs.realpathSync(fixture) === fixture ? fixture : parsed.project);
        assert.ok(parsed.project.startsWith(path.resolve(os.tmpdir())),
            'the opened project is the fixture, not the checkout');
        assert.notEqual(parsed.project, parsed.install,
            'project and install roots must be able to differ');
        assert.equal(parsed.install, INSTALL_ROOT);
        assert.ok(parsed.asset.startsWith(parsed.project));
        assert.ok(fs.existsSync(parsed.asset), 'the fixture asset resolves to a real file');
    } finally {
        fs.rmSync(fixture, { recursive: true, force: true });
    }
});

test('a project path that escapes its root is refused, not rewritten', () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'sr-escape-'));
    try {
        fs.mkdirSync(path.join(root, 'assets'), { recursive: true });
        assert.equal(resolveWithin(root, 'assets', 'sprites'), path.join(root, 'assets', 'sprites'));
        assert.equal(resolveWithin(root, 'assets', '..', 'assets'), path.join(root, 'assets'));
        assert.equal(resolveWithin(root), path.resolve(root), 'the root itself is inside itself');

        for (const escape of [['..'], ['..', '..', 'Windows'], ['assets', '..', '..', 'secrets.txt'],
                              [path.join(os.tmpdir(), 'elsewhere')], ['C:\\Windows\\System32']]) {
            assert.throws(() => resolveWithin(root, ...escape), /refusing a path outside/,
                'escaped without being refused: ' + escape.join('|'));
        }
        assert.throws(() => resolveWithin(root, '..', path.basename(root) + '-evil'),
            /refusing a path outside/);
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
    }
});

test('a configured project that is missing or not a project fails at boot', () => {
    const empty = fs.mkdtempSync(path.join(os.tmpdir(), 'sr-empty-'));
    try {
        assert.throws(() => resolveProjectRoot(path.join(empty, 'nope')), /does not exist/);
        assert.throws(() => resolveProjectRoot(empty), /is not a project/);
        assert.equal(isProjectRoot(empty), false);

        const out = resolveInChild(empty);
        assert.notEqual(out.status, 0, 'a bad project root must fail loudly at require time');
        assert.match(out.stderr, /is not a project/);
    } finally {
        fs.rmSync(empty, { recursive: true, force: true });
    }
});

test('campaign-shaped directories cannot masquerade as Projects', () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'sr-campaigns-'));
    try {
        fs.mkdirSync(path.join(root, 'campaigns', 'demo'), { recursive: true });
        fs.writeFileSync(path.join(root, 'campaign.json'), '{"active":"demo"}', 'utf8');
        assert.equal(isProjectRoot(root), false,
            'only a Project data/ root is sufficient to define an authored game');
        assert.throws(() => resolveProjectRoot(root), /contains no data\/ directory/);
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
    }
});

require('./test-runtime-bridge.js');
require('./test-project-play.js');
