'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const bridge = require('./runtime-bridge-server');
const roots = require('../../tools/semantic-roots');
const storage = require('./authored-storage');

test('live spatial bridge preserves environment authority across Event edits', { timeout: 180000 }, async () => {
    const previewExe = process.env.LOVEC || process.env.LOVE_PATH;
    assert.ok(previewExe && fs.existsSync(previewExe), 'Set LOVEC to the console LÖVE executable.');
    const projectRoot = roots.DEFAULT_PROJECT_ROOT;
    const map = storage.loadResource(path.join(projectRoot, 'data'), 'maps').value.find(m => m.id === 17);
    assert.ok(map && map.traversal && map.traversal.environmentPackage);
    const original = JSON.stringify(map);
    const options = { installRoot: roots.DEFAULT_INSTALL_ROOT, projectRoot, previewExe };
    const compile = value => bridge.compileRenderable({ map: value, seed: 424242,
        renderableEncoding: 'instances' }, options);
    const first = await compile(map);
    const environmentPlacements = bundle => bundle.placements.filter(p => p.source && p.source.kind === 'environment');
    const placements = environmentPlacements(first);
    assert.ok(placements.some(p => p.source.surface === 'render'));
    assert.ok(placements.some(p => p.source.surface === 'collision'));
    assert.ok(placements.every(p => p.source.manifestPath === map.traversal.environmentPackage));
    assert.ok(first.placements.every(p => !p.source || p.source.kind !== 'event'),
        'Studio owns live Event visuals; the static runtime bundle must not duplicate them');
    assert.equal(first.spatialCamera.profile, map.traversal.camera.profile);
    assert.ok(Number.isFinite(first.spatialCamera.x));
    assert.equal(first.compositionPreview, undefined,
        'the runtime bridge must not rasterize authored plate assets for Studio');

    const edited = JSON.parse(original);
    // Plate NPCs are grounded by the runtime lane; world Y is their visible
    // placement axis. Z ownership is covered by the editor movement test.
    edited.events.find(e => e.worldPosition).worldPosition[1] += 0.25;
    const second = await compile(edited);
    assert.deepEqual(environmentPlacements(second), placements, 'Event placement does not rewrite package geometry');
    assert.deepEqual(second.spatialCamera, first.spatialCamera);
    assert.equal(JSON.stringify(map), original);

    const broken = JSON.parse(original);
    broken.traversal.environmentPackage = 'assets/missing-spatial-proof/environment.json';
    await assert.rejects(compile(broken), /environment package missing/);
    const indoor = storage.loadResource(path.join(projectRoot, 'data'), 'maps').value.find(m => m.id === 28);
    const indoorBundle = await compile(indoor);
    assert.equal(indoorBundle.compositionPreview, undefined, 'fully 3D Maps never become images');
});
