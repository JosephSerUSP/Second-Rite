'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const WorldPresentation = require('../js/world-presentation.js');
const ROOT = path.resolve(__dirname, '..', '..', '..');

(function testProfilesMatch617Vocabulary() {
    assert.deepStrictEqual(WorldPresentation.PROFILE_IDS, [
        'first_person', 'ortho_oblique', 'rpg_ortho',
        'perspective_oblique', 'rpg_perspective'
    ]);
    assert.deepStrictEqual(WorldPresentation.PROFILE_SPECS.rpg_perspective, {
        projection: 'perspective', rpgCorrection: true, fovDegrees: 26, tilesAcross: 18
    });
})();

(function testStudioValidationMatchesRuntimeRanges() {
    assert.deepStrictEqual(WorldPresentation.validateWorldPresentation({
        pixelsPerTile: 24,
        camera: { profile: 'rpg_perspective', pitchDegrees: 40, yawDegrees: -90, fovDegrees: 26, tilesAcross: 18 }
    }), []);
    assert.match(WorldPresentation.validateWorldPresentation({ pixelsPerTile: 0 })[0], /positive finite/);
    assert.match(WorldPresentation.validateCamera({ profile: 'imaginary' })[0], /unknown profile/);
    assert.match(WorldPresentation.validateCamera({ pitchDegrees: 90 })[0], /> 0 and < 90/);
    assert.match(WorldPresentation.validateCamera({ yawDegrees: Infinity })[0], /finite/);
    assert.match(WorldPresentation.validateCamera({ fovDegrees: 179 })[0], /> 0 and < 179/);
    assert.match(WorldPresentation.validateCamera({ tilesAcross: -1 })[0], /positive finite/);
})();

(function testSceneOwnershipAndRoundTripPreserveUnknownFields() {
    const map = { id: 'town', width: 20, height: 12, collision: { custom: true } };
    const mapBefore = JSON.parse(JSON.stringify(map));
    const scene = {
        id: 'map', draw: 'world', world: 'map', unrelated: { keep: ['all', 'of', 'this'] },
        worldPresentation: {
            pixelsPerTile: 24,
            futurePresentationField: { keep: true },
            camera: {
                profile: 'rpg_perspective', pitchDegrees: 40,
                futureCameraField: { keep: 'verbatim' }
            }
        }
    };

    WorldPresentation.setPixelsPerTile(scene, 32);
    WorldPresentation.setCameraField(scene, 'fovDegrees', 26);
    WorldPresentation.setCameraField(scene, 'tilesAcross', 18);
    WorldPresentation.setCameraField(scene, 'yawDegrees', null);

    assert.deepStrictEqual(map, mapBefore, 'Scene presentation authoring must not mutate Map data');
    assert.deepStrictEqual(scene.unrelated, { keep: ['all', 'of', 'this'] });
    assert.deepStrictEqual(scene.worldPresentation.futurePresentationField, { keep: true });
    assert.deepStrictEqual(scene.worldPresentation.camera.futureCameraField, { keep: 'verbatim' });
    assert.strictEqual(scene.worldPresentation.pixelsPerTile, 32);
    assert.strictEqual(scene.worldPresentation.camera.fovDegrees, 26);
    assert.strictEqual(scene.worldPresentation.camera.tilesAcross, 18);
    assert.strictEqual(Object.prototype.hasOwnProperty.call(scene.worldPresentation.camera, 'yawDegrees'), false);
})();

(function testExplicitUnsetDoesNotEraseUnknownPresentationMembers() {
    const scene = { worldPresentation: { pixelsPerTile: 24, extension: { future: true } } };
    WorldPresentation.setPixelsPerTile(scene, null);
    assert.deepStrictEqual(scene.worldPresentation, { extension: { future: true } });
})();

(function testDesignPixelDensityIsIndependentFromCameraFraming() {
    assert.deepStrictEqual(WorldPresentation.imageSizeInTiles(128, 64, 24), {
        width: 128 / 24, height: 64 / 24
    });
    const cameraA = WorldPresentation.resolveCamera(
        { profile: 'rpg_perspective', pitchDegrees: 40, fovDegrees: 26, tilesAcross: 18 },
        { playerX: 5, playerY: 6, playerDir: 'N' }
    );
    const cameraB = WorldPresentation.resolveCamera(
        { profile: 'rpg_perspective', pitchDegrees: 40, fovDegrees: 26, tilesAcross: 18 },
        { playerX: 5, playerY: 6, playerDir: 'N', pixelsPerTile: 999 }
    );
    assert.deepStrictEqual(cameraA, cameraB,
        'pixelsPerTile is design density and must not move/reframe the runtime camera');
    const expectedDepth = 18 * Math.sin(40 * Math.PI / 180)
        / (2 * Math.tan(26 * Math.PI / 360));
    assert.ok(Math.abs(cameraA.focusDepth - expectedDepth) < 1e-10);
})();

(function testFirstPersonFallbackAndProfileAwareProjection() {
    const fallback = WorldPresentation.resolveCamera(null, { playerX: 2, playerY: 3, playerDir: 'E' });
    assert.strictEqual(fallback.profile, 'first_person');
    assert.strictEqual(fallback.provenance, 'engine/default fallback');
    assert.strictEqual(fallback.projection, 'perspective');
    assert.deepStrictEqual(
        [fallback.x, fallback.y, fallback.z, fallback.targetX, fallback.targetY, fallback.targetZ],
        [2.5, 3.5, 0.5, 3.5, 3.5, 0.5]
    );
    const ortho = WorldPresentation.resolveCamera(
        { profile: 'rpg_ortho', pitchDegrees: 45 },
        { playerX: 2, playerY: 3, playerDir: 'N' }
    );
    assert.strictEqual(ortho.projection, 'orthographic');
    assert.ok(Math.abs(ortho.projectionScaleX - Math.SQRT1_2) < 1e-12);
})();

(function testPreviewModeRestoresTheExactCapturedSnapshot() {
    const state = WorldPresentation.createPreviewStateMachine();
    const captured = {
        mode: 'perspective',
        perspective: { position: [1.125, 2.25, 3.5], quaternion: [0.1, 0.2, 0.3, 0.9], target: [4, 5, 6] },
        orthographic: { position: [7, 8, 9], zoom: 1.375 }
    };
    let restored = null;
    assert.strictEqual(state.mode(), 'free');
    assert.strictEqual(state.enter(() => captured), captured);
    assert.strictEqual(state.mode(), 'runtime');
    state.enter(() => { throw new Error('runtime refresh must not replace free snapshot'); });
    assert.strictEqual(state.leave(snapshot => { restored = snapshot; }), true);
    assert.strictEqual(restored, captured);
    assert.strictEqual(state.mode(), 'free');
})();

(function testWorldSceneSelectionIsSceneOnly() {
    const payload = { scenes: [
        { id: 'menu', draw: 'windows' },
        { id: 'map-a', draw: 'world', world: 'map' },
        { id: 'other-world', draw: 'world', world: 'battlefield' },
        { id: 'map-b', draw: 'world', world: 'map' }
    ] };
    assert.deepStrictEqual(WorldPresentation.mapWorldScenes(payload).map(scene => scene.id), ['map-a', 'map-b']);
})();

(function testRuntimeAndStudioAdaptersStayLockedTo617Semantics() {
    const cameraLua = fs.readFileSync(path.join(ROOT, 'presentation', 'world_camera.lua'), 'utf8');
    const validatorLua = fs.readFileSync(path.join(ROOT, 'engine', 'project_validator_rules.lua'), 'utf8');
    const viewportSource = fs.readFileSync(path.join(ROOT, 'tools', 'editor', 'js', 'three-editor-viewport.js'), 'utf8');
    const studioSource = fs.readFileSync(path.join(ROOT, 'tools', 'editor', 'js', 'world-presentation-studio.js'), 'utf8');

    assert.match(cameraLua, /rpg_perspective\s*=\s*\{[\s\S]*?fovDegrees\s*=\s*26,\s*tilesAcross\s*=\s*18/);
    assert.match(cameraLua, /focusDepth\s*=\s*world_camera\.focusDepthForTilesAcross/);
    assert.match(cameraLua, /projectionScaleX\s*=\s*world_camera\.rpgGridHorizontalScale\(pitch\)/);
    WorldPresentation.PROFILE_IDS.forEach(profile => {
        assert.match(validatorLua, new RegExp(`\\b${profile}\\s*=\\s*true`));
    });

    assert.match(viewportSource, /three-editor-viewport-base\.js/,
        'runtime preview must adapt the existing semantic Three scene, not build a second map renderer');
    assert.match(viewportSource, /captureCameraState/);
    assert.match(viewportSource, /restoreCameraState/);
    assert.match(viewportSource, /applyRuntimeCamera/);
    assert.match(studioSource, /Free Authoring/);
    assert.match(studioSource, /Runtime Camera/);
    assert.match(studioSource, /Owner: Scene/);
    assert.match(studioSource, /Map topology\/collision is not copied or rewritten here/);
    assert.doesNotMatch(studioSource, /map\.worldPresentation\s*=/,
        'Studio must not create a Map-local worldPresentation convenience copy');
})();

(function testAuthorabilityMarkerIsReadyFor618ToIngest() {
    assert.strictEqual(WorldPresentation.AUTHORING_STATE_MARKER['Scene.worldPresentation.camera'].issue, 619);
    assert.strictEqual(WorldPresentation.AUTHORING_STATE_MARKER['Scene.worldPresentation.camera'].preview,
        'frame-local + runtime-verifiable');
    assert.strictEqual(WorldPresentation.AUTHORING_STATE_MARKER['Scene.worldPresentation.pixelsPerTile'].roundTrip,
        'proven');
})();

console.log('Scene world-presentation Studio tests OK');
