'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const bridge = require('./runtime-bridge-server');

test('validates transient map requests without mutating input', () => {
    const source = { map: { id: 7, layout: ['#.#'] }, seed: '42' };
    const value = bridge.validateRequest(source);
    assert.equal(value.map, source.map);
    assert.equal(value.seed, 42);
});

test('rejects missing map identity', () => {
    assert.throws(() => bridge.validateRequest({ map: {} }), /needs an id/);
});

test('parses the dedicated LÖVE renderable envelope', () => {
    const value = bridge.parseRenderableOutput('noise\nRENDERABLE BEGIN\n{"version":1,"surfaces":[]}\nRENDERABLE END\nmore');
    assert.equal(value.version, 1);
    assert.deepEqual(value.surfaces, []);
});

test('surfaces LÖVE-side bridge errors instead of returning a partial bundle', () => {
    assert.throws(
        () => bridge.parseRenderableOutput('RENDERABLE BEGIN\n{"error":"broken height field"}\nRENDERABLE END'),
        /broken height field/);
});

test('compile bridge passes a short-lived request file to LÖVE and deletes it', async () => {
    const fs = require('node:fs');
    const os = require('node:os');
    const path = require('node:path');
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'second-rite-renderable-'));
    let requestPath = null;
    const request = { map: { id: 12, layout: ['.'] }, seed: 9 };
    const value = await bridge.compileRenderable(request, {
        installRoot: root,
        projectRoot: root,
        previewExe: process.execPath,
        execFile(exe, args, options, callback) {
            assert.equal(exe, process.execPath);
            assert.deepEqual(args, ['.', 'preview-map', '12']);
            requestPath = path.join(root, options.env.SECOND_RITE_RENDERABLE_REQUEST);
            assert.deepEqual(JSON.parse(fs.readFileSync(requestPath, 'utf8')), request);
            callback(null, 'RENDERABLE BEGIN\n{"version":1,"map":{"id":12}}\nRENDERABLE END\n', '');
        },
    });
    assert.equal(value.map.id, 12);
    assert.equal(fs.existsSync(requestPath), false);
    fs.rmSync(root, { recursive: true, force: true });
});
