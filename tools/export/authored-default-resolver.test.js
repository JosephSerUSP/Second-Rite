'use strict';

const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const test = require('node:test');
const { stageGame } = require('./export-game');
const rtp = require('./rtp-resource-resolver');
const engineRegistry = require('./engine-registry-resolver');
const defaults = require('./authored-default-resolver');

function write(filePath, value = '') {
    fs.mkdirSync(path.dirname(filePath), { recursive: true });
    fs.writeFileSync(filePath, typeof value === 'string' ? value : JSON.stringify(value), 'utf8');
}

function readJson(root, relative) {
    return JSON.parse(fs.readFileSync(path.join(root, relative), 'utf8'));
}

function makeRuntime(root) {
    write(path.join(root, 'main.lua'), 'runtime-main');
    write(path.join(root, 'engine', 'runtime.lua'), 'runtime-engine');
    write(path.join(root, 'presentation', 'draw.lua'), 'runtime-presentation');
    for (const file of ['authored_storage.lua', 'authored_storage_manifest.json', 'json.lua', 'loader.lua']) {
        write(path.join(root, 'data', file), '{}');
    }
    write(path.join(root, 'tools', 'export', 'release-conf.lua'), 't.console = false');
}

function makeManifest(root) {
    const file = path.join(root, 'runtime-manifest.json');
    write(file, {
        version: 1,
        rootFiles: ['main.lua'],
        runtimeDirectories: ['engine', 'presentation'],
        projectDirectories: ['assets'],
        dataRuntimeFiles: ['authored_storage.lua', 'authored_storage_manifest.json', 'json.lua', 'loader.lua'],
        authoredDataExtensions: ['.json'],
        releaseConfig: 'tools/export/release-conf.lua',
    });
    return file;
}

test('engineRegistry composes a pinned semantic baseline with disjoint Project policy', () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'sr-engine-registry-'));
    try {
        const project = path.join(root, 'project');
        const rtpRoot = path.join(root, 'rtp');
        write(path.join(project, 'data', 'system.json'), { rtp: { revision: 'A' } });
        write(path.join(project, 'data', 'engine.json'), { craftRules: { alpha: 0.5 } });
        write(path.join(rtpRoot, 'revisions', 'A', 'data', 'engine.json'), { commands: [{ id: 'TEXT' }] });
        const system = rtp.projectSystem(project);
        const resolved = engineRegistry.resolve({ projectDir: project, systemValue: system.value, rtpRoot });
        assert.deepEqual(resolved.value, { commands: [{ id: 'TEXT' }], craftRules: { alpha: 0.5 } });
        assert.equal(resolved.provider.kind, 'composed');
        assert.deepEqual(resolved.provider.base, { kind: 'rtp', id: 'thestra-rtp', revision: 'A' });
        assert.deepEqual(resolved.provider.overlay, { kind: 'project', id: 'project' });
        assert.equal(resolved.sources.length, 2);
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
    }
});

test('engineRegistry ownership collisions fail visible instead of inventing deep precedence', () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'sr-engine-collision-'));
    try {
        const project = path.join(root, 'project');
        const rtpRoot = path.join(root, 'rtp');
        write(path.join(project, 'data', 'system.json'), { rtp: { revision: 'A' } });
        write(path.join(project, 'data', 'engine.json'), { commands: [] });
        write(path.join(rtpRoot, 'revisions', 'A', 'data', 'engine.json'), { commands: [{ id: 'TEXT' }] });
        const system = rtp.projectSystem(project);
        assert.throws(
            () => engineRegistry.resolve({ projectDir: project, systemValue: system.value, rtpRoot }),
            /ownership collision.*commands/,
        );
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
    }
});

test('neutral Project inherits only explicit defaults and staging materializes inspectable provenance', () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'sr-authored-defaults-'));
    const runtime = path.join(root, 'install');
    const project = path.join(root, 'project');
    const rtpRoot = path.join(root, 'rtp');
    const stage = path.join(root, 'stage');
    try {
        makeRuntime(runtime);
        write(path.join(project, 'data', 'system.json'), { id: 'neutral', rtp: { revision: 'A' } });
        write(path.join(project, 'data', 'engine.json'), { projectPolicy: true });
        write(path.join(project, 'data', 'sounds.json'), {});
        write(path.join(project, 'data', 'scenes', 'index.json'), { files: ['title.json'] });
        write(path.join(project, 'data', 'scenes', 'title.json'), { id: 'title', name: 'Neutral identity' });
        write(path.join(project, 'data', 'flows', 'battle.json'), { battle_start: [] });
        write(path.join(project, 'assets', 'sprite.txt'), 'project-asset');
        write(path.join(rtpRoot, 'revisions', 'A', 'data', 'engine.json'), { commands: [{ id: 'TEXT' }] });
        for (const spec of defaults.SCENES) {
            write(path.join(rtpRoot, 'revisions', 'A', 'data', 'scenes', spec.file), { id: spec.id, name: spec.id });
        }
        write(path.join(rtpRoot, 'revisions', 'A', 'data', 'flows', 'quest.json'), { offer: [], complete: [] });

        const result = stageGame({
            runtimeDir: runtime,
            projectDir: project,
            outputDir: stage,
            manifestPath: makeManifest(root),
            rtpRoot,
        });
        assert.deepEqual(readJson(stage, 'data/engine.json'), {
            commands: [{ id: 'TEXT' }],
            projectPolicy: true,
        });
        const sceneFiles = readJson(stage, 'data/scenes/index.json').files;
        assert.equal(sceneFiles[0], 'title.json');
        for (const spec of defaults.SCENES) assert.ok(sceneFiles.includes(spec.file));
        assert.deepEqual(readJson(stage, 'data/flows/quest.json'), { offer: [], complete: [] });
        assert.throws(
            () => defaults.scene({
                id: 'title',
                projectDir: project,
                systemValue: rtp.projectSystem(project).value,
                rtpRoot,
            }),
            /not an inherited Scene default/,
        );

        const provenance = readJson(stage, 'data/authored_resolution.json');
        assert.equal(provenance.materialized, true);
        assert.equal(provenance.resources.engineRegistry.provider.kind, 'composed');
        assert.equal(provenance.resources.sceneDefaults.controls.provider.kind, 'rtp');
        assert.equal(provenance.resources.flowDefaults.quest.provider.kind, 'rtp');
        assert.ok(!JSON.stringify(provenance).includes(root), 'staged provenance must not embed authoring paths');
        assert.equal(result.resolvedResources.sceneDefaults.length, defaults.SCENES.length);
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
    }
});

test('current Second Gate keeps Project policy and explicit local Scene/Flow overrides', () => {
    const project = path.resolve(__dirname, '..', '..');
    const rtpRoot = path.join(project, 'rtp');
    const system = rtp.projectSystem(project);
    const resolved = engineRegistry.resolve({ projectDir: project, systemValue: system.value, rtpRoot });
    assert.equal(resolved.provider.kind, 'composed');
    assert.ok(resolved.value.commands.some(command => command.id === 'SHOW_IMAGE_PICTURE'));
    assert.ok(resolved.value.craftRules && resolved.value.craftLexicon);
    const scenes = defaults.scenes({ projectDir: project, systemValue: system.value, rtpRoot });
    assert.equal(scenes.length, defaults.SCENES.length);
    assert.ok(scenes.every(resource => resource.provider.kind === 'project'));
    assert.equal(defaults.flow({ id: 'quest', projectDir: project, systemValue: system.value, rtpRoot }).provider.kind, 'project');
});
