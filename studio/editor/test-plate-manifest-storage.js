'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const storage = require('./plate-manifest-storage');

function fixture() {
    return { bounds: [0, 0, 0, 1, 1, 1], anchors: { spawn: { position: [0, 0, 0] } }, preRendered: {
        mode: 'layered_2d', imageSize: [424, 240], slicePositions: [3.15],
        scenes: ['scene.png'], backgrounds: ['scene.png'], foregrounds: ['front.png'],
        lane: { runtimeCenterY: 3.15 }, playerProjection: { centerX: 233.6, screenY: 136, width: 24, height: 48, pixelsPerRuntimeY: 27.4 }
    }};
}

test('Plate Composition storage writes only calibration leaves atomically', () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'second-rite-plate-storage-'));
    const requested = 'assets/environments/town/example/environment.json';
    const file = path.join(root, ...requested.split('/'));
    fs.mkdirSync(path.dirname(file), { recursive: true });
    fs.writeFileSync(file, JSON.stringify(fixture(), null, 2) + '\n');
    try {
        const loaded = storage.read(root, requested);
        const proposed = JSON.parse(JSON.stringify(loaded.manifest));
        proposed.preRendered.playerProjection.centerX = 241;
        proposed.preRendered.imageSize[0] = 512;
        proposed.bounds[0] = 99;
        const saved = storage.write(root, requested, proposed, loaded.version);
        assert.equal(saved.manifest.preRendered.playerProjection.centerX, 241);
        assert.equal(saved.manifest.preRendered.imageSize[0], 512);
        assert.equal(saved.manifest.bounds[0], 0, 'bounds are not writable through calibration');
        assert.throws(() => storage.write(root, requested, proposed, loaded.version), /changed on disk/);
        assert.throws(() => storage.read(root, '../outside/environment.json'), /assets\/environments/);
    } finally { fs.rmSync(root, { recursive: true, force: true }); }
});
