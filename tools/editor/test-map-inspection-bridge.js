'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const bridge = require('./runtime-bridge-server');

test('parses the semantic Map inspection envelope', () => {
    const value = bridge.parseInspectionOutput(
        'MAP INSPECTION BEGIN\n{"kind":"generated-map-inspection","request":{"seed":7}}\nMAP INSPECTION END');
    assert.equal(value.kind, 'generated-map-inspection');
    assert.equal(value.request.seed, 7);
});

test('inspection bridge uses a transient request file and removes it', async () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'second-rite-inspection-'));
    let requestPath = null;
    let removedSnapshot = null;
    const request = { map: { id: 2, width: 17, height: 17 }, seed: 424242 };
    const snapshot = {
        env: { THESTRA_RUNTIME_DATA_ROOT: path.join(root, 'compiled-data') },
    };
    try {
        const value = await bridge.compileInspection(request, {
            installRoot: root,
            projectRoot: root,
            previewExe: process.execPath,
            snapshotSameRoot(options) {
                assert.deepEqual(options, { installRoot: root, projectRoot: root });
                return snapshot;
            },
            removeSnapshot(value) { removedSnapshot = value; },
            execFile(exe, args, options, callback) {
                assert.equal(exe, process.execPath);
                assert.deepEqual(args, ['.', 'preview-map-inspection', '2']);
                assert.equal(options.cwd, root);
                assert.equal(options.env.THESTRA_RUNTIME_DATA_ROOT, snapshot.env.THESTRA_RUNTIME_DATA_ROOT);
                requestPath = path.join(root, options.env.SECOND_RITE_MAP_INSPECTION_REQUEST);
                assert.deepEqual(JSON.parse(fs.readFileSync(requestPath, 'utf8')), request);
                callback(null, 'MAP INSPECTION BEGIN\n{"kind":"generated-map-inspection"}\nMAP INSPECTION END\n', '');
            },
        });
        assert.equal(value.kind, 'generated-map-inspection');
        assert.equal(fs.existsSync(requestPath), false);
        assert.equal(removedSnapshot, snapshot);
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
    }
});

test('inspection bridge stages an external Project before compiling it', async () => {
    const installRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'second-rite-inspection-install-'));
    const externalRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'second-rite-inspection-project-'));
    const stagedRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'second-rite-inspection-stage-'));
    let requestPath = null;
    let removedStage = null;
    try {
        const value = await bridge.compileInspection({ map: { id: 5 }, seed: 9 }, {
            installRoot,
            projectRoot: externalRoot,
            previewExe: process.execPath,
            stageProject(options) {
                assert.deepEqual(options, { installRoot, projectRoot: externalRoot });
                return stagedRoot;
            },
            removeStage(stage) { removedStage = stage; },
            execFile(exe, args, options, callback) {
                assert.equal(exe, process.execPath);
                assert.deepEqual(args, ['.', 'preview-map-inspection', '5']);
                assert.equal(options.cwd, stagedRoot);
                requestPath = path.join(stagedRoot, options.env.SECOND_RITE_MAP_INSPECTION_REQUEST);
                assert.deepEqual(JSON.parse(fs.readFileSync(requestPath, 'utf8')), { map: { id: 5 }, seed: 9 });
                callback(null, 'MAP INSPECTION BEGIN\n{"kind":"generated-map-inspection"}\nMAP INSPECTION END\n', '');
            },
        });
        assert.equal(value.kind, 'generated-map-inspection');
        assert.equal(fs.existsSync(requestPath), false);
        assert.equal(removedStage, stagedRoot);
    } finally {
        fs.rmSync(installRoot, { recursive: true, force: true });
        fs.rmSync(externalRoot, { recursive: true, force: true });
        fs.rmSync(stagedRoot, { recursive: true, force: true });
    }
});
