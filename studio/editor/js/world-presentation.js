(function (root, factory) {
    const api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    else root.ThestraWorldPresentation = api;
}(typeof globalThis !== 'undefined' ? globalThis : this, function () {
    'use strict';

    const PROFILE_SPECS = Object.freeze({
        first_person: Object.freeze({ projection: 'perspective', rpgCorrection: false, firstPerson: true }),
        ortho_oblique: Object.freeze({ projection: 'orthographic', rpgCorrection: false }),
        rpg_ortho: Object.freeze({ projection: 'orthographic', rpgCorrection: true }),
        perspective_oblique: Object.freeze({ projection: 'perspective', rpgCorrection: false, fovDegrees: 26, tilesAcross: 18 }),
        rpg_perspective: Object.freeze({ projection: 'perspective', rpgCorrection: true, fovDegrees: 26, tilesAcross: 18 })
    });
    const PROFILE_IDS = Object.freeze(Object.keys(PROFILE_SPECS));
    const DIRS = Object.freeze({
        N: Object.freeze({ dx: 0, dy: -1, angle: -Math.PI / 2 }),
        E: Object.freeze({ dx: 1, dy: 0, angle: 0 }),
        S: Object.freeze({ dx: 0, dy: 1, angle: Math.PI / 2 }),
        W: Object.freeze({ dx: -1, dy: 0, angle: Math.PI })
    });

    // #618 is still open. Keep this small marker mechanically discoverable so
    // its eventual generator can adopt the completed #619 facts without a
    // hand-maintained docs/AUTHORING-STATE.md edit.
    const AUTHORING_STATE_MARKER = Object.freeze({
        'Scene.worldPresentation.camera': Object.freeze({
            createEdit: 'first-class/shared', roundTrip: 'proven', help: 'first-class/shared',
            preview: 'frame-local + runtime-verifiable', provenance: 'Scene/default source visible', issue: 619
        }),
        'Scene.worldPresentation.pixelsPerTile': Object.freeze({
            createEdit: 'first-class/shared', roundTrip: 'proven', help: 'first-class/shared',
            preview: 'design/world-size readout', provenance: 'Scene/default source visible', issue: 619
        })
    });

    function own(object, key) {
        return !!object && Object.prototype.hasOwnProperty.call(object, key);
    }

    function finiteNumber(value) {
        return typeof value === 'number' && Number.isFinite(value);
    }

    function numeric(value, label) {
        const parsed = typeof value === 'number' ? value : Number(value);
        if (!Number.isFinite(parsed)) throw new Error(`${label} must be finite`);
        return parsed;
    }

    function positive(value, label) {
        const parsed = numeric(value, label);
        if (parsed <= 0) throw new Error(`${label} must be positive`);
        return parsed;
    }

    function validateCamera(camera) {
        const errors = [];
        if (camera == null) return errors;
        if (!camera || typeof camera !== 'object' || Array.isArray(camera)) {
            return ['worldPresentation.camera must be an object'];
        }
        if (camera.profile != null && !PROFILE_SPECS[camera.profile]) {
            errors.push(`worldPresentation.camera has unknown profile '${camera.profile}'`);
        }
        if (camera.pitchDegrees != null && (!finiteNumber(camera.pitchDegrees)
                || camera.pitchDegrees <= 0 || camera.pitchDegrees >= 90)) {
            errors.push('camera.pitchDegrees must be > 0 and < 90');
        }
        if (camera.yawDegrees != null && !finiteNumber(camera.yawDegrees)) {
            errors.push('camera.yawDegrees must be finite');
        }
        if (camera.fovDegrees != null && (!finiteNumber(camera.fovDegrees)
                || camera.fovDegrees <= 0 || camera.fovDegrees >= 179)) {
            errors.push('camera.fovDegrees must be > 0 and < 179');
        }
        if (camera.tilesAcross != null && (!finiteNumber(camera.tilesAcross) || camera.tilesAcross <= 0)) {
            errors.push('camera.tilesAcross must be a positive finite number');
        }
        if (camera.projectionWindowOffsetX != null && !finiteNumber(camera.projectionWindowOffsetX)) {
            errors.push('camera.projectionWindowOffsetX must be finite');
        }
        if (camera.projectionWindowOffsetY != null && !finiteNumber(camera.projectionWindowOffsetY)) {
            errors.push('camera.projectionWindowOffsetY must be finite');
        }
        return errors;
    }

    function validateWorldPresentation(spec) {
        if (spec == null) return [];
        if (!spec || typeof spec !== 'object' || Array.isArray(spec)) {
            return ['worldPresentation must be an object'];
        }
        const errors = [];
        if (spec.pixelsPerTile != null && (!finiteNumber(spec.pixelsPerTile) || spec.pixelsPerTile <= 0)) {
            errors.push('worldPresentation.pixelsPerTile must be a positive finite number');
        }
        return errors.concat(validateCamera(spec.camera));
    }

    function ensurePresentation(scene) {
        if (!scene || typeof scene !== 'object') throw new Error('Scene is required');
        if (scene.worldPresentation == null) scene.worldPresentation = {};
        if (!scene.worldPresentation || typeof scene.worldPresentation !== 'object'
                || Array.isArray(scene.worldPresentation)) {
            throw new Error('worldPresentation must be an object');
        }
        return scene.worldPresentation;
    }

    function prunePresentation(scene) {
        if (scene && scene.worldPresentation && Object.keys(scene.worldPresentation).length === 0) {
            delete scene.worldPresentation;
        }
    }

    function setPixelsPerTile(scene, value) {
        if (value == null || value === '') {
            if (scene && scene.worldPresentation && typeof scene.worldPresentation === 'object') {
                delete scene.worldPresentation.pixelsPerTile;
                prunePresentation(scene);
            }
            return scene;
        }
        const parsed = positive(value, 'worldPresentation.pixelsPerTile');
        ensurePresentation(scene).pixelsPerTile = parsed;
        return scene;
    }

    function ensureCamera(scene) {
        const presentation = ensurePresentation(scene);
        if (presentation.camera == null) presentation.camera = {};
        if (!presentation.camera || typeof presentation.camera !== 'object' || Array.isArray(presentation.camera)) {
            throw new Error('worldPresentation.camera must be an object');
        }
        return presentation.camera;
    }

    function clearCamera(scene) {
        if (scene && scene.worldPresentation && typeof scene.worldPresentation === 'object') {
            delete scene.worldPresentation.camera;
            prunePresentation(scene);
        }
        return scene;
    }

    function setCameraField(scene, key, value) {
        const allowed = ['profile', 'pitchDegrees', 'yawDegrees', 'fovDegrees', 'tilesAcross', 'projectionWindowOffsetX', 'projectionWindowOffsetY'];
        if (!allowed.includes(key)) throw new Error(`Unsupported authored camera field '${key}'`);
        if (value == null || value === '') {
            if (scene && scene.worldPresentation && scene.worldPresentation.camera
                    && typeof scene.worldPresentation.camera === 'object') {
                delete scene.worldPresentation.camera[key];
            }
            return scene;
        }
        const camera = ensureCamera(scene);
        if (key === 'profile') {
            if (!PROFILE_SPECS[value]) throw new Error(`worldPresentation.camera has unknown profile '${value}'`);
            camera.profile = value;
            return scene;
        }
        const parsed = numeric(value, `camera.${key}`);
        if (key === 'pitchDegrees' && (parsed <= 0 || parsed >= 90)) {
            throw new Error('camera.pitchDegrees must be > 0 and < 90');
        }
        if (key === 'fovDegrees' && (parsed <= 0 || parsed >= 179)) {
            throw new Error('camera.fovDegrees must be > 0 and < 179');
        }
        if (key === 'tilesAcross' && parsed <= 0) {
            throw new Error('camera.tilesAcross must be a positive finite number');
        }
        camera[key] = parsed;
        return scene;
    }

    function imageSizeInTiles(width, height, pixelsPerTile) {
        width = numeric(width, 'design image width');
        height = numeric(height, 'design image height');
        pixelsPerTile = positive(pixelsPerTile, 'pixelsPerTile');
        return { width: width / pixelsPerTile, height: height / pixelsPerTile };
    }

    function mapWorldScenes(payload) {
        return ((payload && payload.scenes) || []).filter(scene => scene
            && scene.draw === 'world' && scene.world === 'map');
    }

    function previewFocus(payload, mapIndex, selection) {
        const map = payload && payload.maps && payload.maps[mapIndex];
        if (selection && selection.cell
                && Number.isFinite(Number(selection.cell.x)) && Number.isFinite(Number(selection.cell.y))) {
            return { playerX: Number(selection.cell.x), playerY: Number(selection.cell.y), playerDir: 'N', source: 'selection' };
        }
        const spawn = payload && payload.system && payload.system.spawn;
        if (map && spawn && String(spawn.mapId) === String(map.id)
                && Number.isFinite(Number(spawn.x)) && Number.isFinite(Number(spawn.y))) {
            const candidateDir = String(spawn.dir || spawn.direction || 'N').toUpperCase();
            return {
                playerX: Number(spawn.x), playerY: Number(spawn.y),
                playerDir: DIRS[candidateDir] ? candidateDir : 'N', source: 'player start'
            };
        }
        const width = Math.max(1, Number(map && map.width) || (map && map.layout && map.layout[0] && String(map.layout[0]).length) || 1);
        const height = Math.max(1, Number(map && map.height) || (map && map.layout && map.layout.length) || 1);
        return {
            playerX: Math.max(0, Math.floor(width / 2)),
            playerY: Math.max(0, Math.floor(height / 2)),
            playerDir: 'N', source: 'map center'
        };
    }

    function resolveCamera(authoredCamera, session) {
        const authored = authoredCamera && typeof authoredCamera === 'object' ? authoredCamera : {};
        const profile = authored.profile || 'first_person';
        const preset = PROFILE_SPECS[profile];
        if (!preset) throw new Error(`unknown world camera profile: ${profile}`);
        const state = session || {};
        const playerX = numeric(state.playerX == null ? 0 : state.playerX, 'playerX');
        const playerY = numeric(state.playerY == null ? 0 : state.playerY, 'playerY');
        const playerDir = DIRS[state.playerDir] ? state.playerDir : 'N';
        const provenance = authoredCamera ? 'authored Scene world presentation' : 'engine/default fallback';
        const projectionWindowOffsetX = authored.projectionWindowOffsetX != null
            ? numeric(authored.projectionWindowOffsetX, 'camera.projectionWindowOffsetX') : 0;
        const projectionWindowOffsetY = authored.projectionWindowOffsetY != null
            ? numeric(authored.projectionWindowOffsetY, 'camera.projectionWindowOffsetY') : 0;

        if (preset.firstPerson) {
            const direction = DIRS[playerDir];
            const cameraX = playerX + 0.5;
            const cameraY = playerY + 0.5;
            return {
                profile, projection: 'perspective', rpgCorrection: false, provenance,
                x: cameraX, y: cameraY, z: 0.5,
                targetX: cameraX + direction.dx, targetY: cameraY + direction.dy, targetZ: 0.5,
                angle: direction.angle, pitch: 0,
                fovHalfX: 0.75, fovHalfY: 0.421875,
                projectionScaleX: 1, projectionScaleY: 1,
                orthoHalfX: 1, orthoHalfY: 1,
                tilesAcross: null, fovDegrees: 2 * Math.atan(0.75) * 180 / Math.PI,
                projectionWindowOffsetX, projectionWindowOffsetY
            };
        }

        const pitch = (authored.pitchDegrees == null ? 45 : positive(authored.pitchDegrees, 'camera.pitchDegrees')) * Math.PI / 180;
        if (pitch <= 0 || pitch >= Math.PI / 2) throw new Error('overhead camera pitch must be > 0 and < pi/2');
        const yaw = (authored.yawDegrees == null ? -90 : numeric(authored.yawDegrees, 'camera.yawDegrees')) * Math.PI / 180;
        const dirX = Math.cos(yaw), dirY = Math.sin(yaw);
        const targetX = playerX + 0.5, targetY = playerY + 0.5, targetZ = 0;
        const projectionScaleX = preset.rpgCorrection ? Math.sin(pitch) : 1;
        const projectionScaleY = 1;
        const aspectY = 144 / 256;
        const fovDegrees = authored.fovDegrees == null ? preset.fovDegrees : positive(authored.fovDegrees, 'camera.fovDegrees');
        if (fovDegrees != null && fovDegrees >= 179) throw new Error('camera FOV degrees must be < 179');
        const fovHalfX = fovDegrees != null ? Math.tan(fovDegrees * Math.PI / 360) : 0.75;
        const fovHalfY = fovHalfX * aspectY;
        const tilesAcross = authored.tilesAcross == null ? preset.tilesAcross : positive(authored.tilesAcross, 'camera.tilesAcross');
        let focusDepth, height, groundDistance;
        if (preset.projection === 'perspective' && tilesAcross != null) {
            focusDepth = tilesAcross * projectionScaleX / (2 * fovHalfX);
            height = focusDepth * Math.sin(pitch);
            groundDistance = focusDepth * Math.cos(pitch);
        } else {
            height = 6;
            groundDistance = height / Math.tan(pitch);
            focusDepth = Math.hypot(groundDistance, height);
        }
        const orthoHalfX = 6;
        const orthoHalfY = orthoHalfX * aspectY;
        return {
            profile, projection: preset.projection, rpgCorrection: preset.rpgCorrection, provenance,
            x: targetX - dirX * groundDistance,
            y: targetY - dirY * groundDistance,
            z: targetZ + height,
            targetX, targetY, targetZ,
            angle: yaw, pitch, focusDepth, height, groundDistance,
            fovDegrees: fovDegrees == null ? 2 * Math.atan(fovHalfX) * 180 / Math.PI : fovDegrees,
            fovHalfX, fovHalfY, tilesAcross: tilesAcross == null ? null : tilesAcross,
            orthoHalfX, orthoHalfY, projectionScaleX, projectionScaleY,
            projectionWindowOffsetX, projectionWindowOffsetY
        };
    }

    function createPreviewStateMachine() {
        let freeSnapshot = null;
        let mode = 'free';
        return {
            mode: () => mode,
            enter(capture) {
                if (mode === 'runtime') return freeSnapshot;
                freeSnapshot = capture();
                mode = 'runtime';
                return freeSnapshot;
            },
            leave(restore) {
                if (mode !== 'runtime') return false;
                const snapshot = freeSnapshot;
                freeSnapshot = null;
                mode = 'free';
                restore(snapshot);
                return true;
            },
            snapshot: () => freeSnapshot
        };
    }

    return {
        PROFILE_SPECS, PROFILE_IDS, AUTHORING_STATE_MARKER,
        validateCamera, validateWorldPresentation,
        setPixelsPerTile, setCameraField, clearCamera,
        imageSizeInTiles, mapWorldScenes, previewFocus, resolveCamera,
        createPreviewStateMachine, own
    };
}));
