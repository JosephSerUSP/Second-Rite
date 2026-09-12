'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const authoring = require('./environment-package-authoring');

function fixture() {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'thestra-env-authoring-'));
    const logical = 'assets/environments/town/test/environment.json';
    const file = path.join(root, ...logical.split('/'));
    fs.mkdirSync(path.dirname(file), { recursive: true });
    const value = {
        contractVersion: 1,
        renderMesh: 'mesh.obj',
        bounds: [0, 0, 0, 1, 1, 1],
        anchors: { spawn: { position: [0, 0, 0] } },
        provenance: { plateSourceViewTransform: 'Standard' },
        preRendered: {
            mode: 'layered_2d',
            imageSize: [424, 240],
            slicePositions: [3.15],
            scenes: ['scene.png'],
            foregrounds: ['fg.png'],
            backgrounds: ['bg.png'],
            lane: { runtimeCenterY: 3.15 },
            playerProjection: {
                centerX: 233.6, screenY: 136, width: 24, height: 48,
                pixelsPerRuntimeY: 27.428571428571427
            }
        }
    };
    fs.writeFileSync(file, JSON.stringify(value, null, 2) + '\n');
    return { root, logical, file, value };
}

test('environment calibration authority reads only normalized environment manifests', () => {
    const { root, logical } = fixture();
    try {
        const loaded = authoring.read(root, logical);
        assert.equal(loaded.path, logical);
        assert.equal(loaded.value.preRendered.playerProjection.centerX, 233.6);
        assert.equal(typeof loaded.version, 'string');
        assert.equal(loaded.version.length, 64);
        assert.throws(() => authoring.read(root, '../outside/environment.json'), /normalized|limited|escapes/);
        assert.throws(() => authoring.read(root, 'assets/models/environment.json'), /limited/);
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
    }
});

test('calibration writes only playerProjection centerX/screenY and preserves all other authority', () => {
    const { root, logical, file } = fixture();
    try {
        const before = authoring.read(root, logical);
        const result = authoring.writeCalibration(root, logical,
            { centerX: 240.25, screenY: 132 }, before.version);
        assert.equal(result.value.preRendered.playerProjection.centerX, 240.25);
        assert.equal(result.value.preRendered.playerProjection.screenY, 132);
        const saved = JSON.parse(fs.readFileSync(file, 'utf8'));
        assert.equal(saved.preRendered.playerProjection.pixelsPerRuntimeY, 27.428571428571427);
        assert.deepEqual(saved.preRendered.imageSize, [424, 240]);
        assert.deepEqual(saved.preRendered.slicePositions, [3.15]);
        assert.deepEqual(saved.preRendered.lane, { runtimeCenterY: 3.15 });
        assert.deepEqual(saved.anchors, { spawn: { position: [0, 0, 0] } });
        assert.deepEqual(saved.provenance, { plateSourceViewTransform: 'Standard' });
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
    }
});

test('calibration patches preserve unrelated manifest bytes', () => {
    const { root, logical, file } = fixture();
    try {
        let raw = fs.readFileSync(file, 'utf8');
        raw = raw.replace('"width": 24,', '"width": 24.0,')
            .replace('"height": 48,', '"height": 48.000,');
        fs.writeFileSync(file, raw, 'utf8');
        const before = authoring.read(root, logical);
        authoring.writeCalibration(root, logical, { centerX: 240.25 }, before.version);
        const after = fs.readFileSync(file, 'utf8');
        assert.match(after, /"width": 24\.0,/,
            'calibration must not normalize unrelated numeric spelling');
        assert.match(after, /"height": 48\.000,/,
            'calibration must preserve unrelated authored bytes');
        assert.match(after, /"centerX": 240\.25,/);
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
    }
});

test('calibration authority rejects stale saves and unsupported framing knobs', () => {
    const { root, logical, file } = fixture();
    try {
        const before = authoring.read(root, logical);
        fs.appendFileSync(file, ' ');
        assert.throws(
            () => authoring.writeCalibration(root, logical, { centerX: 200 }, before.version),
            error => error && error.code === 'STALE_ENVIRONMENT_PACKAGE'
        );
        const fresh = authoring.read(root, logical);
        assert.throws(
            () => authoring.writeCalibration(root, logical, { pixelsPerRuntimeY: 30 }, fresh.version),
            /not authorable/
        );
        assert.throws(
            () => authoring.writeCalibration(root, logical, { imageSize: [400, 240] }, fresh.version),
            /not authorable/
        );
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
    }
});
