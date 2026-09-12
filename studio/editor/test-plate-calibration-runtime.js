'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const roots = require('../../tools/semantic-roots');
const Commands = require('./js/second-rite-editor-commands');
const EnvironmentAuthoring = require('./environment-package-authoring');

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

function frame(frames, label) {
    const found = frames.find(candidate => candidate.label === label);
    assert.ok(found, `town proof includes ${label}`);
    assert.ok(found.composition?.player?.screen, `${label} reports real compositor player coordinates`);
    return found;
}

test('camera optics and plate anchor calibration move map 24 independently in the real compositor',
        { timeout: 300000 }, () => {
    const previewExe = process.env.LOVEC || process.env.LOVE_PATH;
    assert.ok(previewExe && fs.existsSync(previewExe), 'Set LOVEC to the console LÖVE executable.');
    const stage = fs.mkdtempSync(path.join(os.tmpdir(), 'second-rite-plate-calibration-'));
    try {
        const stageResult = spawnSync(process.execPath, [
            path.join(roots.DEFAULT_INSTALL_ROOT, 'tools', 'ci', 'stage-project-gates.js'),
            '--output', stage,
        ], { cwd: roots.DEFAULT_INSTALL_ROOT, encoding: 'utf8',
            maxBuffer: 32 * 1024 * 1024, timeout: 120000 });
        assert.equal(stageResult.status, 0, stageResult.stdout + stageResult.stderr);
        const staged = stageResult.stdout.match(/PROJECT GATE STAGE OK\s+(\{.*\})/);
        assert.ok(staged, 'the canonical exporter reported its staged Project root');
        const gameRoot = JSON.parse(staged[1]).stageDir;
        const mapPath = path.join(gameRoot, 'data', 'maps.json');
        const originalMapsRaw = fs.readFileSync(mapPath, 'utf8');
        const maps = JSON.parse(originalMapsRaw);
        const mapIndex = maps.findIndex(candidate => candidate.id === 24);
        const map = maps[mapIndex];
        assert.ok(map, 'staged Project contains Alicia Upstairs (map 24)');

        const environmentPath = map.traversal.environmentPackage;
        const environment = EnvironmentAuthoring.read(gameRoot, environmentPath);
        const plateProjection = environment.value.preRendered.playerProjection;
        assert.equal(map.traversal.camera.projectionFrame.canonicalCenterX, 213);
        assert.equal(plateProjection.centerX, 233.6);
        assert.notEqual(plateProjection.centerX, map.traversal.camera.projectionFrame.canonicalCenterX,
            'off-centre plate anchor remains intentionally independent from the camera principal point');

        const baseline = captureTownFrames(previewExe, gameRoot);
        const baselineEast = frame(baseline, '24-east');
        const baselineCentre = frame(baseline, '24-centre');

        // Camera authority: make the real Map-owned lens narrower through the
        // exact Studio command layer. At a non-centre lane sample, the same
        // world displacement must occupy more pixels relative to the baked
        // plate anchor. The environment package is untouched.
        const originalFov = Number(map.traversal.camera.fovDegrees);
        const narrowerFov = originalFov - 4;
        const cameraEdit = Commands.setTownCameraField(
            { maps }, mapIndex, 'fovDegrees', narrowerFov);
        assert.equal(cameraEdit.ok, true);
        assert.equal(cameraEdit.changed, true);
        fs.writeFileSync(mapPath, JSON.stringify(maps, null, 2) + '\n');

        const cameraFrames = captureTownFrames(previewExe, gameRoot);
        const cameraEast = frame(cameraFrames, '24-east');
        const beforeDx = baselineEast.composition.player.screen.x
            - baselineEast.composition.player.plate.centerX;
        const afterDx = cameraEast.composition.player.screen.x
            - cameraEast.composition.player.plate.centerX;
        assert.equal(Math.sign(afterDx), Math.sign(beforeDx),
            'narrower FOV preserves the side of the plate anchor');
        assert.ok(Math.abs(afterDx) > Math.abs(beforeDx) + 0.05,
            'narrower FOV expands player displacement away from the plate anchor');
        assert.equal(cameraEast.composition.player.plate.centerX,
            baselineEast.composition.player.plate.centerX,
            'Map camera edit does not rewrite the environment player anchor');
        assert.deepEqual(cameraEast.actor, baselineEast.actor,
            'Map camera edit changes composition, not gameplay position');
        assert.notEqual(cameraEast.image, baselineEast.image,
            'the specifically measured east frame changes under the camera edit');

        // Restore Map authority exactly before proving the separate environment
        // calibration authority.
        fs.writeFileSync(mapPath, originalMapsRaw, 'utf8');

        // Plate authority: move only the authored foot line via the guarded
        // environment-package writer. This is a screen-space reanchor, so the
        // real player foot position must move down by exactly the same scaled
        // amount while the Map camera and actor root stay unchanged.
        const footLineDelta = 4;
        const plateEdit = EnvironmentAuthoring.writeCalibration(
            gameRoot, environmentPath,
            { screenY: Number(plateProjection.screenY) + footLineDelta },
            environment.version);
        assert.equal(plateEdit.changed, true);

        const plateFrames = captureTownFrames(previewExe, gameRoot);
        const plateCentre = frame(plateFrames, '24-centre');
        const scale = baselineCentre.composition.player.plate.imageHeight
            / Number(environment.value.preRendered.imageSize[1]);
        const observedDelta = plateCentre.composition.player.screen.y
            - baselineCentre.composition.player.screen.y;
        assert.ok(Math.abs(observedDelta - footLineDelta * scale) < 1e-6,
            `plate foot-line edit moves player down by the expected scaled ${footLineDelta} pixels`);
        assert.equal(plateCentre.composition.player.screen.x,
            baselineCentre.composition.player.screen.x,
            'vertical plate reanchor does not change horizontal composition');
        assert.deepEqual(plateCentre.actor, baselineCentre.actor,
            'plate calibration changes composition, not gameplay position');
        assert.equal(
            JSON.parse(fs.readFileSync(mapPath, 'utf8')).find(candidate => candidate.id === 24)
                .traversal.camera.projectionFrame.canonicalCenterX,
            213,
            'plate calibration does not rewrite the Map principal point');
        assert.equal(
            EnvironmentAuthoring.read(gameRoot, environmentPath)
                .value.preRendered.playerProjection.centerX,
            233.6,
            'vertical calibration does not normalize the off-centre plate anchor');
        assert.notEqual(plateCentre.image, baselineCentre.image,
            'the specifically measured centre frame changes under the plate foot-line edit');
    } finally {
        fs.rmSync(stage, { recursive: true, force: true });
    }
});
