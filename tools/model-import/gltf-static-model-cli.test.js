'use strict';

const assert = require('node:assert/strict');
const childProcess = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');
const { Accessor, Document, NodeIO } = require('@gltf-transform/core');
const { parseArgs } = require('./gltf-static-model-cli');

const CLI = path.join(__dirname, 'gltf-static-model-cli.js');

function minimalDocument() {
    const document = new Document();
    const buffer = document.createBuffer('buffer');
    const positions = document.createAccessor('positions')
        .setType(Accessor.Type.VEC3)
        .setArray(new Float32Array([
            0, 0, 0,
            1, 0, 0,
            0, 1, 0,
        ]))
        .setBuffer(buffer);
    const primitive = document.createPrimitive('triangle').setAttribute('POSITION', positions);
    const mesh = document.createMesh('triangle').addPrimitive(primitive);
    const node = document.createNode('triangle').setMesh(mesh);
    const scene = document.createScene('main').addChild(node);
    document.getRoot().setDefaultScene(scene);
    return document;
}

test('CLI parsing requires explicit output and meters-to-map-cells policy', () => {
    assert.deepEqual(parseArgs([
        'input.glb',
        '--out', 'bundle.json',
        '--meters-to-map-cells', '2',
        '--source-path', 'assets/models/input.glb',
    ]), {
        input: 'input.glb',
        out: 'bundle.json',
        metersToMapCells: 2,
        sourcePath: 'assets/models/input.glb',
    });
    assert.throws(() => parseArgs(['input.glb', '--out', 'bundle.json']), /meters-to-map-cells/);
    assert.throws(() => parseArgs(['input.glb', '--meters-to-map-cells', '1']), /--out is required/);
});

test('CLI writes only the requested standalone bundle and reports deterministic summary facts', async () => {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'thestra-gltf-cli-'));
    const input = path.join(dir, 'source model.glb');
    const output = path.join(dir, 'nested', 'bundle.json');
    try {
        const glb = await new NodeIO().writeBinary(minimalDocument());
        fs.writeFileSync(input, Buffer.from(glb));

        const result = childProcess.spawnSync(process.execPath, [
            CLI,
            input,
            '--out', output,
            '--meters-to-map-cells', '3',
            '--source-path', 'assets/models/fixtures/triângulo.glb',
        ], {
            encoding: 'utf8',
            windowsHide: true,
        });

        assert.equal(result.status, 0, result.stderr || result.stdout);
        const summary = JSON.parse(result.stdout);
        assert.equal(path.resolve(summary.output), path.resolve(output));
        assert.match(summary.bundleHash, /^[0-9a-f]{64}$/);
        assert.equal(summary.vertices, 3);
        assert.equal(summary.groups, 1);
        assert.equal(summary.materials, 0);
        assert.equal(summary.degradedDiagnostics, 0);

        const bundle = JSON.parse(fs.readFileSync(output, 'utf8'));
        assert.equal(bundle.source.path, 'assets/models/fixtures/triângulo.glb');
        assert.equal(bundle.normalization.metersToMapCells, 3);
        assert.equal(bundle.model.vertexCount, 3);
        assert.equal(fs.existsSync(`${output}.tmp-${process.pid}`), false);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});
