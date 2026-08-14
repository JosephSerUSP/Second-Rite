'use strict';

const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const test = require('node:test');
const rtp = require('./rtp-resource-resolver');
const engine = require('./engine-registry-resolver');
const defaults = require('./authored-default-resolver');
const materializer = require('./authored-default-materializer');
const authoredStorage = require('../editor/authored-storage');

function write(file, value) {
    fs.mkdirSync(path.dirname(file), { recursive: true });
    fs.writeFileSync(file, typeof value === 'string' ? value : JSON.stringify(value, null, 2) + '\n');
}

function fixture() {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'thestra-authored-defaults-'));
    const project = path.join(root, 'project');
    const rtpRoot = path.join(root, 'rtp');
    const revisionRoot = path.join(rtpRoot, 'revisions', 'A');
    const stage = path.join(root, 'stage');
    write(path.join(project, 'data', 'system.json'), { rtp: { revision: 'A' } });
    write(path.join(project, 'data', 'engine.json'), { projectPolicy: { value: 7 } });
    write(path.join(project, 'data', 'scenes', 'index.json'), { files: ['title.json', 'controls.json'] });
    write(path.join(project, 'data', 'scenes', 'title.json'), { id: 'title', name: 'Project identity' });
    write(path.join(project, 'data', 'scenes', 'controls.json'), { id: 'controls', name: 'Local controls' });
    write(path.join(project, 'data', 'flows', 'battle.json'), { battle_start: [] });

    write(path.join(revisionRoot, 'manifest.json'), {
        version: 1,
        revision: 'A',
        resources: [],
        authored: {
            engineRegistry: 'data/engine.json',
            sceneDefaults: {
                controls: 'data/scenes/controls.json',
                items: 'data/scenes/items.json',
            },
            flowDefaults: { quest: 'data/flows/quest.json' },
        },
    });
    write(path.join(revisionRoot, 'data', 'engine.json'), { commands: [{ id: 'TEXT' }], itemScopes: [{ scope: 'battle' }] });
    write(path.join(revisionRoot, 'data', 'scenes', 'controls.json'), { id: 'controls', name: 'Inherited controls' });
    write(path.join(revisionRoot, 'data', 'scenes', 'items.json'), { id: 'items', name: 'Inherited items' });
    write(path.join(revisionRoot, 'data', 'flows', 'quest.json'), { offer: [], complete: [] });
    write(path.join(stage, 'data', 'system.json'), { rtp: { revision: 'A' } });
    write(path.join(stage, 'data', 'engine.json'), { projectPolicy: { value: 7 } });
    write(path.join(stage, 'data', 'scenes', 'index.json'), { files: ['title.json', 'controls.json'] });
    write(path.join(stage, 'data', 'scenes', 'title.json'), { id: 'title', name: 'Project identity' });
    write(path.join(stage, 'data', 'scenes', 'controls.json'), { id: 'controls', name: 'Local controls' });
    write(path.join(stage, 'data', 'flows', 'battle.json'), { battle_start: [] });
    return { root, project, rtpRoot, stage };
}

test('manifest is the only inventory for inherited engine/Scene/Flow defaults', () => {
    const f = fixture();
    try {
        const system = rtp.projectSystem(f.project);
        const manifest = rtp.revisionManifest({ systemValue: system.value, rtpRoot: f.rtpRoot });
        assert.deepEqual(Object.keys(manifest.authored.sceneDefaults).sort(), ['controls', 'items']);
        assert.deepEqual(Object.keys(manifest.authored.flowDefaults), ['quest']);

        const resolvedEngine = engine.resolve({ projectDir: f.project, systemValue: system.value, rtpRoot: f.rtpRoot });
        assert.deepEqual(resolvedEngine.value.projectPolicy, { value: 7 });
        assert.equal(resolvedEngine.value.commands[0].id, 'TEXT');
        assert.equal(resolvedEngine.provider.kind, 'composed');

        const scenes = defaults.scenes({ projectDir: f.project, systemValue: system.value, rtpRoot: f.rtpRoot });
        assert.deepEqual(scenes.map(entry => [entry.value.id, entry.provider.kind]), [
            ['controls', 'project'],
            ['items', 'rtp'],
        ]);
        const flows = defaults.flows({ projectDir: f.project, systemValue: system.value, rtpRoot: f.rtpRoot });
        assert.deepEqual(flows.map(entry => [entry.resource, entry.provider.kind]), [['flowDefault:quest', 'rtp']]);
    } finally { fs.rmSync(f.root, { recursive: true, force: true }); }
});

test('engine ownership collisions fail instead of deep-merging', () => {
    const f = fixture();
    try {
        write(path.join(f.project, 'data', 'engine.json'), { commands: [] });
        const system = rtp.projectSystem(f.project);
        assert.throws(() => engine.resolve({ projectDir: f.project, systemValue: system.value, rtpRoot: f.rtpRoot }), /ownership collision.*commands/);
    } finally { fs.rmSync(f.root, { recursive: true, force: true }); }
});

test('stage materialization creates a hermetic effective authored view and provenance', () => {
    const f = fixture();
    try {
        const result = materializer.resolveAndMaterialize({
            projectDir: f.project,
            runtimeDir: f.root,
            stageDir: f.stage,
            rtpRoot: f.rtpRoot,
            includeSounds: false,
        });
        const stagedEngine = JSON.parse(fs.readFileSync(path.join(f.stage, 'data', 'engine.json'), 'utf8'));
        assert.equal(stagedEngine.commands[0].id, 'TEXT');
        assert.deepEqual(stagedEngine.projectPolicy, { value: 7 });
        const index = JSON.parse(fs.readFileSync(path.join(f.stage, 'data', 'scenes', 'index.json'), 'utf8'));
        assert.deepEqual(index.files, ['title.json', 'controls.json', 'items.json']);
        assert.ok(fs.existsSync(path.join(f.stage, 'data', 'flows', 'quest.json')));
        const provenance = JSON.parse(fs.readFileSync(path.join(f.stage, 'data', 'authored_resolution.json'), 'utf8'));
        assert.equal(provenance.resources.engineRegistry.provider.kind, 'composed');
        assert.equal(provenance.resources.sceneDefaults.items.provider.kind, 'rtp');
        assert.equal(provenance.resources.sceneDefaults.controls.provider.kind, 'project');
        assert.equal(provenance.resources.flowDefaults.quest.provider.kind, 'rtp');
        assert.ok(!JSON.stringify(provenance).includes(f.root), 'materialized provenance must not embed development checkout paths');
        assert.equal(result.sceneDefaults.length, 2);
    } finally { fs.rmSync(f.root, { recursive: true, force: true }); }
});

test('Studio authored storage exposes effective engine but persists only Project policy', () => {
    const f = fixture();
    const previous = process.env[rtp.RTP_ROOT_ENV];
    process.env[rtp.RTP_ROOT_ENV] = f.rtpRoot;
    try {
        const dataRoot = path.join(f.project, 'data');
        const loaded = authoredStorage.loadResource(dataRoot, 'engine');
        assert.equal(loaded.value.commands[0].id, 'TEXT');
        assert.deepEqual(loaded.value.projectPolicy, { value: 7 });
        const next = Object.assign({}, loaded.value, { projectPolicy: { value: 9 } });
        authoredStorage.writeResource(dataRoot, 'engine', next);
        const local = JSON.parse(fs.readFileSync(path.join(dataRoot, 'engine.json'), 'utf8'));
        assert.deepEqual(local, { projectPolicy: { value: 9 } });
        assert.throws(() => authoredStorage.writeResource(dataRoot, 'engine', Object.assign({}, next, { commands: [] })), /Cannot edit inherited engineRegistry key 'commands'/);
    } finally {
        if (previous === undefined) delete process.env[rtp.RTP_ROOT_ENV]; else process.env[rtp.RTP_ROOT_ENV] = previous;
        fs.rmSync(f.root, { recursive: true, force: true });
    }
});

test('current Second Gate split still resolves both semantic commands and Project policy', () => {
    const project = path.resolve(__dirname, '..', '..');
    const system = rtp.projectSystem(project);
    const resolved = engine.resolve({ projectDir: project, systemValue: system.value, rtpRoot: path.join(project, 'rtp') });
    assert.ok(resolved.value.commands.some(command => command.id === 'SHOW_TEXT'));
    assert.ok(resolved.value.craftRules);
    assert.ok(resolved.value.geometry);
    const scenes = defaults.scenes({ projectDir: project, systemValue: system.value, rtpRoot: path.join(project, 'rtp') });
    assert.equal(scenes.length, 4);
    assert.ok(scenes.every(resource => resource.provider.kind === 'project'), 'Second Gate keeps its local menu Scene copies under #390');
    const flows = defaults.flows({ projectDir: project, systemValue: system.value, rtpRoot: path.join(project, 'rtp') });
    assert.equal(flows.find(resource => resource.resource === 'flowDefault:quest').provider.kind, 'project');
});
