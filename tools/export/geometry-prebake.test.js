'use strict';

const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const test = require('node:test');
const { ENV_OUTPUT, PREBAKE_MAIN, runGeometryPrebake, validateGeneratedPrebakes } = require('./geometry-prebake');

function write(filePath, contents = '') {
    fs.mkdirSync(path.dirname(filePath), { recursive: true });
    fs.writeFileSync(filePath, contents);
}

function makeStage(root) {
    const stageDir = path.join(root, 'stage');
    write(path.join(stageDir, 'main.lua'), '-- real staged runtime\nreturn true\n');
    write(path.join(stageDir, 'engine', 'geometry', 'prebake.lua'), 'return {}\n');
    write(path.join(stageDir, 'data', 'system.json'), '{"title":"fixture"}\n');
    return stageDir;
}

function deterministicCompiler(expectedStage, artifact = 'fixture-bytes') {
    return (_exe, args, options) => {
        assert.deepEqual(args, [path.resolve(expectedStage)]);
        assert.equal(fs.readFileSync(path.join(expectedStage, 'main.lua'), 'utf8'), PREBAKE_MAIN,
            'compiler must run through the temporary prebake entrypoint');
        const output = options.env[ENV_OUTPUT];
        assert.ok(output, 'prebake output environment variable');
        fs.mkdirSync(output, { recursive: true });
        const manifest = {
            version: 1,
            formatVersion: 2,
            compilerVersion: 1,
            quality: 'd1.000:e0.00010',
            geometryClass: 'tileset-height-plane',
            sourceFiles: [{ path: 'data/system.json', digest: 'deadbeef' }],
            entries: [{
                key: 'atlas:v1:fixture|d1.000:e0.00010',
                file: '0123456789abcdef.geo',
                kind: 'tileset-height-plane',
                label: 'fixture',
            }],
        };
        fs.writeFileSync(path.join(output, '0123456789abcdef.geo'), artifact);
        fs.writeFileSync(path.join(output, 'manifest.json'), JSON.stringify(manifest, null, 2) + '\n');
        return { status: 0, stdout: 'GEOMETRY PREBAKE OK entries=1\n', stderr: '' };
    };
}

test('prebake transform writes only inside staging and restores runtime main byte-for-byte', () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'second-rite-geometry-prebake-'));
    try {
        const sourceMain = path.join(root, 'authored', 'main.lua');
        write(sourceMain, '-- authored source sentinel\n');
        const stageDir = makeStage(root);
        const beforeMain = fs.readFileSync(path.join(stageDir, 'main.lua'));
        const beforeSource = fs.readFileSync(sourceMain);

        const result = runGeometryPrebake({
            stageDir,
            lovecPath: path.join(root, 'fake-lovec.exe'),
            spawnSync: deterministicCompiler(stageDir),
        });

        assert.deepEqual(fs.readFileSync(path.join(stageDir, 'main.lua')), beforeMain,
            'staged runtime main was not restored');
        assert.deepEqual(fs.readFileSync(sourceMain), beforeSource,
            'authored source was mutated');
        assert.equal(result.manifest.entries.length, 1);
        assert.ok(fs.existsSync(path.join(stageDir, 'assets', 'generated', 'geometry', '0123456789abcdef.geo')));
        assert.ok(fs.existsSync(path.join(stageDir, 'assets', 'generated', 'geometry', 'manifest.json')));
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
    }
});

test('identical staged inputs can produce byte-identical deterministic prebake outputs', () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'second-rite-geometry-prebake-'));
    try {
        const stageDir = makeStage(root);
        const spawnSync = deterministicCompiler(stageDir, 'same-compiled-geometry');
        const first = runGeometryPrebake({ stageDir, lovecPath: 'fake', spawnSync });
        const artifactPath = path.join(first.outputDir, first.manifest.entries[0].file);
        const firstArtifact = fs.readFileSync(artifactPath);
        const firstManifest = fs.readFileSync(first.manifestPath);

        const second = runGeometryPrebake({ stageDir, lovecPath: 'fake', spawnSync });
        assert.deepEqual(fs.readFileSync(path.join(second.outputDir, second.manifest.entries[0].file)), firstArtifact);
        assert.deepEqual(fs.readFileSync(second.manifestPath), firstManifest);
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
    }
});

test('generated manifest refuses an entry whose artifact is absent', () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'second-rite-geometry-prebake-'));
    try {
        const output = path.join(root, 'geometry');
        write(path.join(output, 'manifest.json'), JSON.stringify({
            version: 1,
            formatVersion: 2,
            compilerVersion: 1,
            quality: 'd1.000:e0.00010',
            sourceFiles: [],
            entries: [{ key: 'k', file: 'aaaaaaaa.geo' }],
        }));
        assert.throws(() => validateGeneratedPrebakes(output), /artifact is missing/);
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
    }
});

test('failed compiler still restores staged runtime main', () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'second-rite-geometry-prebake-'));
    try {
        const stageDir = makeStage(root);
        const before = fs.readFileSync(path.join(stageDir, 'main.lua'));
        assert.throws(() => runGeometryPrebake({
            stageDir,
            lovecPath: 'fake',
            spawnSync: () => ({ status: 1, stdout: '', stderr: 'compiler exploded' }),
        }), /compiler exploded/);
        assert.deepEqual(fs.readFileSync(path.join(stageDir, 'main.lua')), before);
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
    }
});
