'use strict';

const assert = require('node:assert/strict');
const childProcess = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');
const compiler = require('./runtime-data-compiler');
const exporter = require('./export-game');

const REPO_ROOT = path.resolve(__dirname, '..', '..');
const RUNTIME_ROOT = path.join(REPO_ROOT, 'runtime');

function write(filePath, contents) {
    fs.mkdirSync(path.dirname(filePath), { recursive: true });
    fs.writeFileSync(filePath, contents, 'utf8');
}

function writeJson(filePath, value) {
    write(filePath, JSON.stringify(value, null, 2) + '\n');
}

function makeSourceData(dataRoot, { includeTestFlow = false } = {}) {
    writeJson(path.join(dataRoot, 'units', 'index.json'), { files: ['unit-a.json'] });
    writeJson(path.join(dataRoot, 'units', 'unit-a.json'), { id: 'unit-a', name: 'Unit A' });

    writeJson(path.join(dataRoot, 'maps', 'index.json'), { files: [] });
    writeJson(path.join(dataRoot, 'scenes', 'index.json'), { files: ['title.json'] });
    writeJson(path.join(dataRoot, 'scenes', 'title.json'), { id: 'title', kind: 'menu' });

    for (const module of ['battle', 'exploration', 'progression', 'quest']) {
        writeJson(path.join(dataRoot, 'flows', `${module}.json`), { [`${module}.fixture`]: [] });
    }
    if (includeTestFlow) writeJson(path.join(dataRoot, 'flows', '_test.json'), { fixture: [] });

    writeJson(path.join(dataRoot, 'tilesets', 'dungeon_default.json'), {
        id: 'dungeon_default',
        texture: 'fixture.png',
    });
}

function makeStage(root, options) {
    const stageDir = path.join(root, 'stage');
    const dataRoot = path.join(stageDir, 'data');
    makeSourceData(dataRoot, options);
    write(path.join(stageDir, 'engine', 'data', 'authored_storage.lua'), '-- source parser');
    write(path.join(stageDir, 'engine', 'data', 'authored_storage_resolved.lua'), '-- source adapter');
    write(path.join(stageDir, 'engine', 'data', 'authored_storage_manifest.json'), '{}');
    write(path.join(stageDir, 'engine', 'data', 'semantic_resources.lua'), '-- source provider');
    return { stageDir, dataRoot };
}

function readJson(filePath) {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function snapshotCompiled(dataRoot) {
    const out = {};
    for (const stem of compiler.RUNTIME_RESOURCES) {
        out[`${stem}.json`] = fs.readFileSync(path.join(dataRoot, `${stem}.json`), 'utf8');
    }
    out[compiler.MANIFEST_NAME] = fs.readFileSync(path.join(dataRoot, compiler.MANIFEST_NAME), 'utf8');
    return out;
}

test('resolver projects source storage into semantic runtime values with provenance', () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'thestra-runtime-data-'));
    try {
        const dataRoot = path.join(root, 'data');
        makeSourceData(dataRoot);
        const resolved = compiler.resolveRuntimeData({ dataRoot });

        assert.equal(resolved.values.units[0].id, 'unit-a');
        assert.deepEqual(resolved.values.maps, []);
        assert.equal(resolved.values.scenes[0].id, 'title');
        assert.equal(resolved.values.tilesets.dungeon_default.id, 'dungeon_default');
        assert.deepEqual(Object.keys(resolved.values.flows).sort(), ['battle', 'exploration', 'progression', 'quest']);

        assert.deepEqual(resolved.provenance.units.sourceFiles, ['units/index.json', 'units/unit-a.json']);
        assert.deepEqual(resolved.provenance.maps.sourceFiles, ['maps/index.json']);
        assert.deepEqual(resolved.provenance.flows.projections,
            [{ kind: 'omit-source-only-module', module: '_test' }]);
        assert.match(resolved.provenance.units.sourceVersion, /^[0-9a-f]{64}$/);
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
    }
});

test('root development _test Flow survives when it is genuinely authored', () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'thestra-runtime-data-'));
    try {
        const dataRoot = path.join(root, 'data');
        makeSourceData(dataRoot, { includeTestFlow: true });
        const resolved = compiler.resolveRuntimeData({ dataRoot });
        assert.ok(resolved.values.flows._test);
        assert.deepEqual(resolved.provenance.flows.projections, []);
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
    }
});

test('compiled stage contains semantic data and no authored physical-storage machinery', () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'thestra-runtime-data-'));
    try {
        const { stageDir, dataRoot } = makeStage(root);
        const runtimeProvider = path.join(root, 'runtime-provider.lua');
        write(runtimeProvider, '-- compiled provider\nreturn { load = function() end }\n');
        const result = compiler.compileRuntimeStage({ stageDir, runtimeProviderSource: runtimeProvider });

        assert.equal(result.manifest.compiler.id, compiler.COMPILER_ID);
        assert.equal(result.manifest.compiler.version, compiler.COMPILER_VERSION);
        for (const stem of compiler.RUNTIME_RESOURCES) {
            assert.ok(fs.existsSync(path.join(dataRoot, `${stem}.json`)), `${stem}.json must exist`);
            assert.ok(!fs.existsSync(path.join(dataRoot, stem)), `${stem}/ source directory must be removed`);
            assert.match(result.manifest.resources[stem].runtimeSha256, /^[0-9a-f]{64}$/);
        }
        for (const filename of compiler.SOURCE_STORAGE_RUNTIME_FILES) {
            assert.ok(!fs.existsSync(path.join(stageDir, ...filename.split('/'))), `${filename} must be absent from player`);
        }
        assert.equal(fs.readFileSync(path.join(stageDir, 'engine', 'data', 'semantic_resources.lua'), 'utf8'),
            '-- compiled provider\nreturn { load = function() end }\n');
        assert.deepEqual(readJson(path.join(dataRoot, 'units.json'))[0].id, 'unit-a');
        assert.deepEqual(readJson(path.join(dataRoot, 'maps.json')), []);
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
    }
});

test('identical source trees compile to byte-identical semantic data and provenance', () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'thestra-runtime-data-'));
    try {
        const first = makeStage(path.join(root, 'a'));
        const second = makeStage(path.join(root, 'b'));
        const runtimeProvider = path.join(root, 'runtime-provider.lua');
        write(runtimeProvider, 'return {}\n');
        compiler.compileRuntimeStage({ stageDir: first.stageDir, runtimeProviderSource: runtimeProvider });
        compiler.compileRuntimeStage({ stageDir: second.stageDir, runtimeProviderSource: runtimeProvider });
        assert.deepEqual(snapshotCompiled(first.dataRoot), snapshotCompiled(second.dataRoot));
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
    }
});

const lovec = process.env.LOVEC || process.env.LOVEC_PATH;
test('real external Project boots G1 from Candidate A+ stage without source storage', { skip: !lovec }, () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'thestra-runtime-data-love-'));
    try {
        const projectDir = path.join(REPO_ROOT, 'projects', 'labs', 'scene-benchmarks');
        const sourceStage = exporter.stageGame({
            projectDir,
            runtimeDir: RUNTIME_ROOT,
            outputDir: path.join(root, 'stage'),
        });
        const before = compiler.resolveRuntimeData({ dataRoot: path.join(sourceStage.stageDir, 'data') }).values;
        compiler.compileRuntimeStage({ stageDir: sourceStage.stageDir });
        const dataRoot = path.join(sourceStage.stageDir, 'data');

        for (const stem of compiler.RUNTIME_RESOURCES) {
            assert.deepEqual(readJson(path.join(dataRoot, `${stem}.json`)), before[stem]);
            assert.ok(!fs.existsSync(path.join(dataRoot, stem)));
        }
        for (const filename of compiler.SOURCE_STORAGE_RUNTIME_FILES) {
            assert.ok(!fs.existsSync(path.join(sourceStage.stageDir, ...filename.split('/'))));
        }
        assert.doesNotMatch(fs.readFileSync(path.join(sourceStage.stageDir, 'engine', 'data', 'semantic_resources.lua'), 'utf8'), /authored_storage/);

        const run = childProcess.spawnSync(lovec, ['.', 'validate'], {
            cwd: sourceStage.stageDir,
            encoding: 'utf8',
            windowsHide: true,
            timeout: 60000,
        });
        const output = `${run.stdout || ''}${run.stderr || ''}`;
        assert.equal(run.status, 0, output);
        assert.match(output, /VALIDATE OK/);
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
    }
});
