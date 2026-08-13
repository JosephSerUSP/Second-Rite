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
const rtpResources = require('../export/rtp-resource-resolver');
const engineRegistry = require('../export/engine-registry-resolver');
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

test('runtime and Studio have no reachable retired Campaign root-selection protocol', () => {
    const server = fs.readFileSync(path.join(__dirname, 'server.js'), 'utf8');
    const loader = fs.readFileSync(path.join(INSTALL_ROOT, 'data', 'loader.lua'), 'utf8');
    const config = fs.readFileSync(path.join(INSTALL_ROOT, 'engine', 'config.lua'), 'utf8');
    const title = fs.readFileSync(path.join(INSTALL_ROOT, 'data', 'scenes', 'title.json'), 'utf8');
    const interpreter = fs.readFileSync(path.join(INSTALL_ROOT, 'engine', 'interpreter_core.lua'), 'utf8');
    const main = fs.readFileSync(path.join(INSTALL_ROOT, 'main.lua'), 'utf8');
    const bridge = fs.readFileSync(path.join(__dirname, 'runtime-bridge-server.js'), 'utf8');
    const markup = fs.readFileSync(path.join(__dirname, 'index.html'), 'utf8');
    const system = rtpResources.projectSystem(INSTALL_ROOT);
    const engine = engineRegistry.resolve({ projectDir: INSTALL_ROOT, systemValue: system.value, rtpRoot: path.join(INSTALL_ROOT, 'rtp') }).value;
    const manifest = JSON.parse(fs.readFileSync(path.join(INSTALL_ROOT, 'tools', 'export', 'runtime-manifest.json'), 'utf8'));
    const metadata = JSON.parse(fs.readFileSync(path.join(INSTALL_ROOT, 'tools', 'export', 'build-metadata.json'), 'utf8'));

    for (const endpoint of ['/campaigns/list', '/campaigns/switch', '/campaign-gen/activate']) {
        assert.ok(!server.includes(endpoint), `retired active-root endpoint survived: ${endpoint}`);
    }
    assert.ok(!loader.includes('resolveRoot'), 'runtime loader must not resolve an alternate content root');
    const listApi = ['list', 'Campaigns'].join('');
    const switchApi = ['switch', 'Campaign'].join('');
    const legacyRoot = ['campaign', 'Root'].join('');
    const pointer = ['campaign', '.json'].join('');
    const cliSelector = ['campaign', '='].join('');
    assert.ok(!loader.includes(listApi), 'runtime loader must not enumerate alternate content roots');
    assert.ok(!config.includes(pointer), 'config must not consult the retired root pointer');

    for (const command of [ ['LIST', 'CAMPAIGNS'].join('_'), ['SWITCH', 'CAMPAIGN'].join('_') ]) {
        assert.ok(!title.includes(command), `title scene still authors ${command}`);
        assert.ok(!engine.commands.some(def => def.id === command), `engine registry still exposes ${command}`);
        assert.ok(!interpreter.includes(command), `interpreter still implements ${command}`);
    }
    assert.ok(!interpreter.includes(listApi), 'SCRIPT API still exposes Campaign enumeration');
    assert.ok(!interpreter.includes(switchApi), 'SCRIPT API still exposes Campaign switching');
    assert.ok(!interpreter.includes(legacyRoot), 'LOAD_GAME still restores a legacy authored root');
    assert.ok(!main.includes(legacyRoot), 'main still carries legacy authored-root state');
    assert.ok(!main.includes(cliSelector), 'main still accepts the retired Campaign CLI selector');
    assert.ok(!bridge.includes(pointer), 'runtime bridge still reads the retired pointer');
    assert.ok(!bridge.includes(cliSelector), 'runtime bridge still injects the retired CLI selector');
    assert.ok(!markup.includes('campaign-picker'), 'Studio still renders the retired Campaign picker');
    assert.ok(!markup.includes('ex-campaign'), 'Export still renders the retired Campaign summary');

    assert.ok(Array.isArray(manifest.authoredDataExtensions));
    assert.ok(!Object.prototype.hasOwnProperty.call(manifest, 'campaignExtensions'));
    assert.ok(!Object.prototype.hasOwnProperty.call(metadata, 'defaultCampaign'));
});

require('./test-runtime-bridge.js');
require('./test-project-play.js');
