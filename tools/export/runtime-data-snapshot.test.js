'use strict';

const assert = require('node:assert/strict');
const childProcess = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const snapshot = require('./runtime-data-snapshot');
const semanticRoots = require('../semantic-roots');

const REPO_ROOT = path.resolve(__dirname, '..', '..');
const SCENE_BENCHMARKS = path.join(REPO_ROOT, 'projects', 'labs', 'scene-benchmarks');

function readJson(filePath) {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

test('data-only snapshot resolves sparse Project defaults then compiles semantic runtime data', () => {
    const sourceIndexPath = path.join(SCENE_BENCHMARKS, 'data', 'scenes', 'index.json');
    const sourceIndexBefore = fs.readFileSync(sourceIndexPath, 'utf8');
    const inheritedSceneSource = path.join(SCENE_BENCHMARKS, 'data', 'scenes', 'dialogue.json');
    assert.equal(fs.existsSync(inheritedSceneSource), false,
        'fixture must genuinely inherit Dialogue instead of authoring it locally');

    let value;
    try {
        value = snapshot.createRuntimeDataSnapshot({
            projectDir: SCENE_BENCHMARKS,
            runtimeDir: REPO_ROOT,
        });
        assert.match(value.relativeDataRoot, /^tmp\/editor-runtime-data\/snapshot-[^/]+\/data$/);
        assert.equal(value.env[snapshot.RUNTIME_DATA_ENV], value.relativeDataRoot);
        assert.equal(fs.existsSync(path.join(value.snapshotRoot, 'assets')), false,
            'data-only snapshot must not copy Project assets');

        for (const stem of ['units', 'maps', 'flows', 'scenes', 'tilesets']) {
            assert.equal(fs.existsSync(path.join(value.dataRoot, `${stem}.json`)), true,
                `${stem} semantic monolith must exist`);
            assert.equal(fs.existsSync(path.join(value.dataRoot, stem)), false,
                `${stem} source representation must be pruned`);
        }
        assert.equal(fs.existsSync(path.join(value.dataRoot, 'authored_storage_manifest.json')), false);
        assert.equal(fs.existsSync(path.join(value.dataRoot, 'authored_resolution.json')), true,
            'exact RTP/default materialization provenance must survive');
        assert.equal(fs.existsSync(path.join(value.dataRoot, 'engine.json')), true,
            'materialized engine registry must be part of the data snapshot');
        assert.equal(fs.existsSync(path.join(value.dataRoot, 'progression.json')), true,
            'inherited progression must be part of the data snapshot');

        const scenes = readJson(path.join(value.dataRoot, 'scenes.json'));
        const sceneIds = new Set(scenes.map(scene => scene.id));
        for (const expected of ['title', 'map', 'a003_snake', 'dialogue', 'save_menu']) {
            assert.equal(sceneIds.has(expected), true, `resolved snapshot is missing Scene ${expected}`);
        }
        const flows = readJson(path.join(value.dataRoot, 'flows.json'));
        for (const expected of ['battle', 'exploration', 'progression', 'quest']) {
            assert.ok(flows[expected], `resolved snapshot is missing Flow ${expected}`);
        }
        const resolution = readJson(path.join(value.dataRoot, 'authored_resolution.json'));
        assert.equal(resolution.materialized, true);
        assert.equal(resolution.rtpRevision, '1.0');
        assert.equal(resolution.resources.sceneDefaults.dialogue.provider.kind, 'rtp');
        assert.equal(value.manifest.compiler.id, 'thestra-runtime-data');

        assert.equal(fs.readFileSync(sourceIndexPath, 'utf8'), sourceIndexBefore,
            'snapshot compilation must not rewrite Project source index');
        assert.equal(fs.existsSync(inheritedSceneSource), false,
            'RTP Scene materialization must remain inside the snapshot');
    } finally {
        snapshot.removeRuntimeDataSnapshot(value);
    }
    assert.ok(value && !fs.existsSync(value.snapshotRoot), 'snapshot cleanup must remove the disposable tree');
});

const lovec = process.env.LOVEC || process.env.LOVEC_PATH;
test('default Project LÖVE validates through the compiled data snapshot', { skip: !lovec }, () => {
    let value;
    try {
        value = snapshot.createRuntimeDataSnapshot({
            projectDir: semanticRoots.DEFAULT_PROJECT_ROOT,
            runtimeDir: REPO_ROOT,
        });
        const run = childProcess.spawnSync(lovec, ['.', 'validate'], {
            cwd: REPO_ROOT,
            env: Object.assign({}, process.env, value.env, { SDL_AUDIODRIVER: 'dummy' }),
            encoding: 'utf8',
            windowsHide: true,
            timeout: 60000,
        });
        const output = `${run.stdout || ''}${run.stderr || ''}`;
        assert.equal(run.status, 0, output);
        assert.match(output, /VALIDATE OK/);
        assert.equal(fs.existsSync(path.join(value.dataRoot, 'units')), false,
            'real default-Project validation must use a compiled data tree');
    } finally {
        snapshot.removeRuntimeDataSnapshot(value);
    }
});
