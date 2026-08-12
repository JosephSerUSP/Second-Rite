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
    const request = { map: { id: 2, width: 17, height: 17 }, seed: 424242 };
    try {
        const value = await bridge.compileInspection(request, {
            installRoot: root,
            projectRoot: root,
            previewExe: process.execPath,
            execFile(exe, args, options, callback) {
                assert.equal(exe, process.execPath);
                assert.deepEqual(args, ['.', 'preview-map-inspection', '2']);
                requestPath = path.join(root, options.env.SECOND_RITE_MAP_INSPECTION_REQUEST);
                assert.deepEqual(JSON.parse(fs.readFileSync(requestPath, 'utf8')), request);
                callback(null, 'MAP INSPECTION BEGIN\n{"kind":"generated-map-inspection"}\nMAP INSPECTION END\n', '');
            },
        });
        assert.equal(value.kind, 'generated-map-inspection');
        assert.equal(fs.existsSync(requestPath), false);
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
    }
});
