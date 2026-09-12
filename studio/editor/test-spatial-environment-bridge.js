'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const bridge = require('./runtime-bridge-server');
const roots = require('../../tools/semantic-roots');
const storage = require('./authored-storage');

function captureTownFrames(previewExe, gameRoot) {
    const result = spawnSync(previewExe, [gameRoot, 'town-proof-frames'], {
        cwd: gameRoot,
        encoding: 'utf8',
        maxBuffer: 64 * 1024 * 1024,
        timeout: 120000,
    });
    assert.equal(result.status, 0, result.stdout + result.stderr);
    const match = result.stdout.match(/TOWN PROOF BEGIN\s*([\s\S]*?)\s*TOWN PROOF END/);
    assert.ok(match, 'town proof emitted its framed payload');
    return JSON.parse(match[1]).frames;
}

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

test('a Port walk-profile edit changes runtime grounding and only its affected compositor sample', { timeout: 180000 }, () => {
    const previewExe = process.env.LOVEC || process.env.LOVE_PATH;
    assert.ok(previewExe && fs.existsSync(previewExe), 'Set LOVEC to the console LÖVE executable.');
    const stage = fs.mkdtempSync(path.join(os.tmpdir(), 'second-rite-town-profile-'));
    try {
        const stageResult = spawnSync(process.execPath, [
            path.join(roots.DEFAULT_INSTALL_ROOT, 'tools', 'ci', 'stage-project-gates.js'),
            '--output', stage,
        ], { cwd: roots.DEFAULT_INSTALL_ROOT, encoding: 'utf8', maxBuffer: 32 * 1024 * 1024, timeout: 120000 });
        assert.equal(stageResult.status, 0, stageResult.stdout + stageResult.stderr);
        const staged = stageResult.stdout.match(/PROJECT GATE STAGE OK\s+(\{.*\})/);
        assert.ok(staged, 'the canonical exporter reported its staged Project root');
        const gameRoot = JSON.parse(staged[1]).stageDir;

        const before = captureTownFrames(previewExe, gameRoot);
        const mapPath = path.join(gameRoot, 'data', 'maps.json');
        const maps = JSON.parse(fs.readFileSync(mapPath, 'utf8'));
        const port = maps.find(candidate => candidate.id === 31);
        assert.ok(port?.traversal?.lane?.groundProfile?.length >= 4,
            'the staged Project retains Port as the existing non-flat profile specimen');
        const lane = port.traversal.lane;
        const profile = lane.groundProfile;
        assert.ok(profile[0].y < lane.minY && profile.at(-1).y > lane.maxY,
            'Port calibration points deliberately extend outside the playable lane interval');

        const eastY = Number(lane.minY) + (Number(lane.maxY) - Number(lane.minY)) * 0.9;
        assert.ok(eastY > Number(profile[1].y) && eastY < Number(profile[2].y),
            'the east proof sample lies on Port\'s authored climb');
        const lift = 0.5;
        const interpolation = (eastY - Number(profile[1].y))
            / (Number(profile[2].y) - Number(profile[1].y));
        const expectedLift = interpolation * lift;
        profile[2].z = Number(profile[2].z) + lift;
        fs.writeFileSync(mapPath, JSON.stringify(maps, null, 2) + '\n');

        const after = captureTownFrames(previewExe, gameRoot);
        const frame = (frames, label) => {
            const found = frames.find(candidate => candidate.label === label);
            assert.ok(found, `town proof includes ${label}`);
            return found;
        };
        const beforeWest = frame(before, '31-west');
        const beforeCentre = frame(before, '31-centre');
        const beforeEast = frame(before, '31-east');
        const afterWest = frame(after, '31-west');
        const afterCentre = frame(after, '31-centre');
        const afterEast = frame(after, '31-east');

        assert.equal(afterWest.actor.z, beforeWest.actor.z,
            'an edit confined to the climb must not move Port west grounding');
        assert.equal(afterCentre.actor.z, beforeCentre.actor.z,
            'an edit confined to the climb must not move Port centre grounding');
        assert.ok(Math.abs((afterEast.actor.z - beforeEast.actor.z) - expectedLift) < 1e-6,
            `Port east actor root must rise by the profile interpolation delta ${expectedLift}`);
        assert.equal(afterEast.actor.y, beforeEast.actor.y,
            'editing floor elevation must not move the actor along the lane');
        assert.equal(afterWest.image, beforeWest.image,
            'unaffected west compositor pixels remain byte-identical');
        assert.equal(afterCentre.image, beforeCentre.image,
            'unaffected centre compositor pixels remain byte-identical');
        assert.notEqual(afterEast.image, beforeEast.image,
            'the actual Port east compositor frame changes when its grounded actor rises');
    } finally {
        fs.rmSync(stage, { recursive: true, force: true });
    }
});

test('a supported plate Event lane edit changes the real town compositor', { timeout: 180000 }, () => {
    const previewExe = process.env.LOVEC || process.env.LOVE_PATH;
    assert.ok(previewExe && fs.existsSync(previewExe), 'Set LOVEC to the console LÖVE executable.');
    const stage = fs.mkdtempSync(path.join(os.tmpdir(), 'second-rite-town-composition-'));
    try {
        const stageResult = spawnSync(process.execPath, [
            path.join(roots.DEFAULT_INSTALL_ROOT, 'tools', 'ci', 'stage-project-gates.js'),
            '--output', stage,
        ], { cwd: roots.DEFAULT_INSTALL_ROOT, encoding: 'utf8', maxBuffer: 32 * 1024 * 1024, timeout: 120000 });
        assert.equal(stageResult.status, 0, stageResult.stdout + stageResult.stderr);
        const staged = stageResult.stdout.match(/PROJECT GATE STAGE OK\s+(\{.*\})/);
        assert.ok(staged, 'the canonical exporter reported its staged Project root');
        const gameRoot = JSON.parse(staged[1]).stageDir;

        const before = captureTownFrames(previewExe, gameRoot);
        const mapPath = path.join(gameRoot, 'data', 'maps.json');
        const maps = JSON.parse(fs.readFileSync(mapPath, 'utf8'));
        const map = maps.find(candidate => candidate.id === 16);
        assert.ok(map, 'the staged Project contains Churchyard');
        const guard = map.events.find(event => event.instanceId === 'st-maria-churchyard-guard');
        assert.ok(guard && Array.isArray(guard.worldPosition), 'Churchyard guard is a lane-positioned plate Event');
        guard.worldPosition[1] += 1.25;
        fs.writeFileSync(mapPath, JSON.stringify(maps, null, 2) + '\n');

        const after = captureTownFrames(previewExe, gameRoot);
        assert.deepEqual(after.map(frame => frame.label), before.map(frame => frame.label));
        assert.ok(after.some((frame, index) => frame.image !== before[index].image),
            'moving the lane coordinate changes a frame emitted by the actual town compositor');
    } finally {
        fs.rmSync(stage, { recursive: true, force: true });
    }
});
