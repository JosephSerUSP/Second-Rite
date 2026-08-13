'use strict';

const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const test = require('node:test');
const { stageGame } = require('./export-game');
const resolver = require('./rtp-resource-resolver');

function write(filePath, contents = '') {
    fs.mkdirSync(path.dirname(filePath), { recursive: true });
    fs.writeFileSync(filePath, contents, 'utf8');
}

const MANIFEST = {
    version: 1,
    rootFiles: ['main.lua'],
    runtimeDirectories: ['engine', 'presentation'],
    projectDirectories: ['assets'],
    dataRuntimeFiles: ['authored_storage.lua', 'authored_storage_manifest.json', 'json.lua', 'loader.lua'],
    authoredDataExtensions: ['.json'],
    releaseConfig: 'tools/export/release-conf.lua',
};

function makeRuntime(root) {
    write(path.join(root, 'main.lua'), 'runtime-main');
    write(path.join(root, 'engine', 'runtime.lua'), 'runtime-engine');
    write(path.join(root, 'presentation', 'draw.lua'), 'runtime-presentation');
    for (const name of MANIFEST.dataRuntimeFiles) write(path.join(root, 'data', name), '{}');
    write(path.join(root, 'tools', 'export', 'release-conf.lua'), 't.console = false');
}

function makeProject(root, revision = 'A') {
    write(path.join(root, 'data', 'system.json'), JSON.stringify({ id: 'fixture-project', rtp: { revision } }));
    write(path.join(root, 'assets', 'sprite.txt'), 'project-asset');
}

function makeManifest(root) {
    const manifestPath = path.join(root, 'runtime-manifest.json');
    write(manifestPath, JSON.stringify(MANIFEST));
    return manifestPath;
}

function readStageJson(stageDir, relative) {
    return JSON.parse(fs.readFileSync(path.join(stageDir, relative), 'utf8'));
}

test('pinned RTP revision is deterministic and the staged tree is hermetic', () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'sr-rtp-pin-'));
    const runtime = path.join(root, 'install');
    const project = path.join(root, 'project');
    const rtpRoot = path.join(root, 'installed-rtp');
    const stage = path.join(root, 'stage');
    try {
        makeRuntime(runtime);
        makeProject(project, 'A');
        // A exists first. B is installed later and deliberately differs.
        write(path.join(rtpRoot, 'revisions', 'A', 'data', 'sounds.json'), JSON.stringify({ source: 'rtp-A' }));
        write(path.join(rtpRoot, 'revisions', 'B', 'data', 'sounds.json'), JSON.stringify({ source: 'rtp-B-newer' }));
        const manifestPath = makeManifest(root);

        const result = stageGame({ runtimeDir: runtime, projectDir: project, outputDir: stage, manifestPath, rtpRoot });
        assert.equal(readStageJson(stage, 'data/sounds.json').source, 'rtp-A');
        assert.deepEqual(result.resolvedResources.system.provider, { kind: 'project', id: 'project' });
        assert.deepEqual(result.resolvedResources.sounds.provider,
            { kind: 'rtp', id: 'thestra-rtp', revision: 'A' });
        assert.equal(result.resolvedResources.sounds.sourcePath,
            path.resolve(rtpRoot, 'revisions', 'A', 'data', 'sounds.json'));

        // The runnable materialization survives removal of every authoring source.
        fs.rmSync(runtime, { recursive: true, force: true });
        fs.rmSync(project, { recursive: true, force: true });
        fs.rmSync(rtpRoot, { recursive: true, force: true });
        assert.equal(fs.readFileSync(path.join(stage, 'main.lua'), 'utf8'), 'runtime-main');
        assert.equal(readStageJson(stage, 'data/sounds.json').source, 'rtp-A');
        const stagedText = fs.readdirSync(path.join(stage, 'data'))
            .filter(name => name.endsWith('.json'))
            .map(name => fs.readFileSync(path.join(stage, 'data', name), 'utf8')).join('\n');
        assert.ok(!stagedText.includes(root), 'staged player data must not embed source checkout/RTP paths');
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
    }
});

test('sounds precedence is Project local then one explicit Package then pinned RTP', () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'sr-rtp-precedence-'));
    const runtime = path.join(root, 'install');
    const project = path.join(root, 'project');
    const rtpRoot = path.join(root, 'installed-rtp');
    const packageFile = path.join(root, 'package-dev', 'sounds.json');
    const stage = path.join(root, 'stage');
    try {
        makeRuntime(runtime);
        makeProject(project, 'A');
        write(path.join(rtpRoot, 'revisions', 'A', 'data', 'sounds.json'), JSON.stringify({ source: 'rtp-A' }));
        write(packageFile, JSON.stringify({ source: 'package' }));
        const manifestPath = makeManifest(root);
        const packageContributions = [{ resource: 'sounds', packageId: 'fixture.audio', file: packageFile }];

        let result = stageGame({ runtimeDir: runtime, projectDir: project, outputDir: stage, manifestPath,
            rtpRoot, packageContributions });
        assert.equal(readStageJson(stage, 'data/sounds.json').source, 'package');
        assert.deepEqual(result.resolvedResources.sounds.provider, { kind: 'package', id: 'fixture.audio' });
        fs.rmSync(path.dirname(packageFile), { recursive: true, force: true });
        assert.equal(readStageJson(stage, 'data/sounds.json').source, 'package',
            'staged player tree must not depend on the Package development checkout');

        write(path.join(project, 'data', 'sounds.json'), JSON.stringify({ source: 'project-local' }));
        result = stageGame({ runtimeDir: runtime, projectDir: project, outputDir: stage, manifestPath,
            rtpRoot, packageContributions });
        assert.equal(readStageJson(stage, 'data/sounds.json').source, 'project-local');
        assert.deepEqual(result.resolvedResources.sounds.provider, { kind: 'project', id: 'project' });
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
    }
});

test('Package collision is fail-visible instead of guessed', () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'sr-rtp-package-collision-'));
    try {
        const project = path.join(root, 'project');
        makeProject(project, 'A');
        const system = resolver.projectSystem(project);
        const a = path.join(root, 'a.json');
        const b = path.join(root, 'b.json');
        write(a, '{}');
        write(b, '{}');
        assert.throws(() => resolver.sounds({
            projectDir: project,
            systemValue: system.value,
            packageContributions: [
                { resource: 'sounds', packageId: 'a', file: a },
                { resource: 'sounds', packageId: 'b', file: b },
            ],
        }), /explicit collision rule/);
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
    }
});

test('Project-required system never falls through to RTP', () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'sr-rtp-required-'));
    const runtime = path.join(root, 'install');
    const project = path.join(root, 'project');
    const rtpRoot = path.join(root, 'installed-rtp');
    try {
        makeRuntime(runtime);
        write(path.join(project, 'assets', 'sprite.txt'), 'project-asset');
        fs.mkdirSync(path.join(project, 'data'), { recursive: true });
        write(path.join(rtpRoot, 'revisions', 'A', 'data', 'system.json'), JSON.stringify({ id: 'must-not-fallback' }));
        write(path.join(rtpRoot, 'revisions', 'A', 'data', 'sounds.json'), '{}');
        const manifestPath = makeManifest(root);
        assert.throws(() => stageGame({ runtimeDir: runtime, projectDir: project,
            outputDir: path.join(root, 'stage'), manifestPath, rtpRoot }),
        /Project-required resource is missing: .*data.*system\.json/);
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
    }
});

test('a pinned revision fails if its typed inherited resource is missing', () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'sr-rtp-missing-'));
    try {
        const project = path.join(root, 'project');
        makeProject(project, 'A');
        const system = resolver.projectSystem(project);
        fs.mkdirSync(path.join(root, 'installed-rtp', 'revisions', 'A'), { recursive: true });
        assert.throws(() => resolver.sounds({ projectDir: project, systemValue: system.value,
            rtpRoot: path.join(root, 'installed-rtp') }), /Pinned RTP revision A does not provide inherited sounds/);
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
    }
});

test('no RTP pin means no implicit lookup of installed revisions', () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'sr-rtp-unpinned-'));
    try {
        const project = path.join(root, 'project');
        write(path.join(project, 'data', 'system.json'), JSON.stringify({ id: 'legacy-project' }));
        const system = resolver.projectSystem(project);
        write(path.join(root, 'installed-rtp', 'revisions', 'B', 'data', 'sounds.json'), JSON.stringify({ source: 'must-not-leak' }));
        assert.equal(resolver.sounds({ projectDir: project, systemValue: system.value,
            rtpRoot: path.join(root, 'installed-rtp') }), null);
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
    }
});
