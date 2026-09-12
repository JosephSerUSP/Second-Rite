(function (root, factory) {
    if (typeof module === 'object' && module.exports) {
        module.exports = factory(require('./thestra-editor-scene.js'));
    } else {
        root.SecondRiteEditorCommands = factory(root.ThestraEditorScene);
    }
}(typeof self !== 'undefined' ? self : this, function (SceneModel) {
    'use strict';

    if (!SceneModel) throw new Error('SecondRiteEditorCommands requires ThestraEditorScene.');

    const TILE_BY_TOOL = Object.freeze({ wall: '#', floor: '.', opening: 'o' });
    const VALID_TILES = new Set(Object.values(TILE_BY_TOOL));

    function mapAt(payload, mapIndex) {
        const maps = payload && payload.maps || [];
        return maps[mapIndex] || null;
    }

    function integerCell(x, y) {
        const nx = Number(x), ny = Number(y);
        if (!Number.isInteger(nx) || !Number.isInteger(ny)) return null;
        return { x: nx, y: ny };
    }

    function cellBounds(map) {
        if (!map) return null;
        const layout = SceneModel.materializeLayout(map);
        return { width: layout.width, height: layout.height, provisional: layout.provisional };
    }

    function validateCell(map, x, y) {
        const cell = integerCell(x, y);
        if (!cell) return { ok: false, reason: 'invalid-cell' };
        const bounds = cellBounds(map);
        if (!bounds || cell.x < 0 || cell.y < 0 || cell.x >= bounds.width || cell.y >= bounds.height) {
            return { ok: false, reason: 'out-of-bounds', cell, bounds };
        }
        return { ok: true, cell, bounds };
    }

    function tileForTool(toolName) {
        return TILE_BY_TOOL[toolName] || null;
    }

    function paintCell(payload, mapIndex, x, y, tile) {
        const map = mapAt(payload, mapIndex);
        if (!map) return { ok: false, reason: 'missing-map' };
        const valid = validateCell(map, x, y);
        if (!valid.ok) return valid;
        if (!VALID_TILES.has(tile)) return { ok: false, reason: 'invalid-tile', cell: valid.cell };
        if (!Array.isArray(map.layout) || !map.layout[valid.cell.y]) {
            return { ok: false, reason: 'procedural-layout-uneditable', cell: valid.cell };
        }

        const row = String(map.layout[valid.cell.y]);
        if (valid.cell.x >= row.length) return { ok: false, reason: 'out-of-bounds', cell: valid.cell };
        const prior = row[valid.cell.x];
        if (prior === tile) return { ok: true, changed: false, cell: valid.cell, tile, prior };
        map.layout[valid.cell.y] = row.substring(0, valid.cell.x) + tile + row.substring(valid.cell.x + 1);
        return { ok: true, changed: true, cell: valid.cell, tile, prior };
    }

    function eventById(map, eventId) {
        if (!map) return null;
        return (map.events || []).find((event, index) => String(event.id != null ? event.id : index) === String(eventId)) || null;
    }

    function canMoveEvent(payload, mapIndex, eventId, x, y) {
        const map = mapAt(payload, mapIndex);
        if (!map) return { ok: false, reason: 'missing-map' };
        const event = eventById(map, eventId);
        if (!event) return { ok: false, reason: 'missing-event' };
        const valid = validateCell(map, x, y);
        if (!valid.ok) return valid;
        const occupied = (map.events || []).some(other => other !== event && Number(other.x) === valid.cell.x && Number(other.y) === valid.cell.y);
        if (occupied) return { ok: false, reason: 'occupied', cell: valid.cell, entity: event };
        const eventIndex = (map.events || []).indexOf(event);
        const resolvedId = event.id != null ? event.id : eventIndex;
        return {
            ok: true,
            changed: Number(event.x) !== valid.cell.x || Number(event.y) !== valid.cell.y,
            cell: valid.cell,
            entity: event,
            selection: { kind: 'event', key: `event:${resolvedId}`, id: resolvedId, cell: valid.cell }
        };
    }

    function moveEvent(payload, mapIndex, eventId, x, y) {
        const result = canMoveEvent(payload, mapIndex, eventId, x, y);
        if (!result.ok || !result.changed) return result;
        result.entity.x = result.cell.x;
        result.entity.y = result.cell.y;
        return result;
    }

    function moveWorldEvent(payload, mapIndex, eventId, position) {
        const event = eventById(mapAt(payload, mapIndex), eventId);
        if (!event || !Array.isArray(event.worldPosition)) return { ok: false, reason: 'missing-world-event' };
        if (!Array.isArray(position) || position.length !== 3 || !position.every(Number.isFinite)) {
            return { ok: false, reason: 'invalid-world-position' };
        }
        const changed = position.some((value, index) => value !== event.worldPosition[index]);
        if (changed) event.worldPosition = position.slice();
        return { ok: true, changed, entity: event,
            selection: { kind: 'event', key: `event:${eventId}`, id: eventId,
                cell: { x: event.x, y: event.y } } };
    }

    function laneAt(payload, mapIndex) {
        const map = mapAt(payload, mapIndex);
        if (!map?.traversal || map.traversal.provider !== 'bounded_lane') return null;
        const lane = map.traversal.lane;
        if (!lane || typeof lane !== 'object' || Array.isArray(lane)) return null;
        return lane;
    }

    function townCameraAt(payload, mapIndex) {
        const map = mapAt(payload, mapIndex);
        if (!map?.traversal || map.traversal.provider !== 'bounded_lane') return null;
        const camera = map.traversal.camera;
        if (!camera || typeof camera !== 'object' || Array.isArray(camera)) return null;
        return camera;
    }

    function setTownCameraField(payload, mapIndex, field, value) {
        const camera = townCameraAt(payload, mapIndex);
        if (!camera) return { ok: false, reason: 'missing-town-camera' };
        if (field !== 'pitchDegrees' && field !== 'fovDegrees') {
            return { ok: false, reason: 'unsupported-camera-field' };
        }
        const next = Number(value);
        if (!Number.isFinite(next)) return { ok: false, reason: 'invalid-camera-value' };
        if (field === 'pitchDegrees' && (next <= -89 || next >= 89)) {
            return { ok: false, reason: 'invalid-camera-pitch' };
        }
        if (field === 'fovDegrees' && (next <= 0 || next >= 179)) {
            return { ok: false, reason: 'invalid-camera-fov' };
        }
        const changed = Number(camera[field]) !== next;
        if (changed) camera[field] = next;
        return { ok: true, changed, camera, field, value: next };
    }

    function profileSelection(index) {
        return { kind: 'walk-profile-point', key: `walk-profile-point:${index}`, index };
    }

    function createGroundProfile(payload, mapIndex) {
        const lane = laneAt(payload, mapIndex);
        if (!lane) return { ok: false, reason: 'missing-bounded-lane' };
        if (Array.isArray(lane.groundProfile) && lane.groundProfile.length) {
            return { ok: true, changed: false, profile: lane.groundProfile, selection: profileSelection(0) };
        }
        const minimum = Number(lane.minY), maximum = Number(lane.maxY);
        const groundZ = Number(lane.groundZ || 0);
        if (![minimum, maximum, groundZ].every(Number.isFinite) || maximum < minimum) {
            return { ok: false, reason: 'invalid-bounded-lane' };
        }
        lane.groundProfile = [{ y: minimum, z: groundZ }, { y: maximum, z: groundZ }];
        return { ok: true, changed: true, profile: lane.groundProfile, selection: profileSelection(0) };
    }

    function splitGroundProfileSegment(payload, mapIndex, segmentIndex, amount = 0.5) {
        const lane = laneAt(payload, mapIndex);
        const profile = lane && lane.groundProfile;
        const index = Number(segmentIndex), t = Number(amount);
        if (!Array.isArray(profile) || profile.length < 2) return { ok: false, reason: 'missing-ground-profile' };
        if (!Number.isInteger(index) || index < 0 || index >= profile.length - 1) {
            return { ok: false, reason: 'invalid-profile-segment' };
        }
        if (!Number.isFinite(t) || t <= 0 || t >= 1) return { ok: false, reason: 'invalid-split-amount' };
        const left = profile[index], right = profile[index + 1];
        const point = {
            y: Number(left.y) + (Number(right.y) - Number(left.y)) * t,
            z: Number(left.z) + (Number(right.z) - Number(left.z)) * t
        };
        if (![point.y, point.z].every(Number.isFinite)) return { ok: false, reason: 'invalid-ground-profile' };
        profile.splice(index + 1, 0, point);
        return { ok: true, changed: true, profile, point, selection: profileSelection(index + 1) };
    }

    function moveGroundProfilePoint(payload, mapIndex, pointIndex, y, z) {
        const lane = laneAt(payload, mapIndex);
        const profile = lane && lane.groundProfile;
        const index = Number(pointIndex), nextY = Number(y), nextZ = Number(z);
        if (!Array.isArray(profile) || profile.length < 2) return { ok: false, reason: 'missing-ground-profile' };
        if (!Number.isInteger(index) || index < 0 || index >= profile.length) {
            return { ok: false, reason: 'invalid-profile-point' };
        }
        if (!Number.isFinite(nextY) || !Number.isFinite(nextZ)) return { ok: false, reason: 'invalid-profile-point' };
        const previous = index > 0 ? Number(profile[index - 1].y) : -Infinity;
        const following = index + 1 < profile.length ? Number(profile[index + 1].y) : Infinity;
        if (nextY < previous || nextY > following) return { ok: false, reason: 'profile-order' };
        const point = profile[index];
        const changed = Number(point.y) !== nextY || Number(point.z) !== nextZ;
        if (changed) { point.y = nextY; point.z = nextZ; }
        return { ok: true, changed, profile, point, selection: profileSelection(index) };
    }

    function deleteGroundProfilePoint(payload, mapIndex, pointIndex) {
        const lane = laneAt(payload, mapIndex);
        const profile = lane && lane.groundProfile;
        const index = Number(pointIndex);
        if (!Array.isArray(profile) || profile.length < 2) return { ok: false, reason: 'missing-ground-profile' };
        if (!Number.isInteger(index) || index <= 0 || index >= profile.length - 1) {
            return { ok: false, reason: 'profile-endpoint' };
        }
        const removed = profile.splice(index, 1)[0];
        const selected = Math.min(index, profile.length - 1);
        return { ok: true, changed: true, profile, removed, selection: profileSelection(selected) };
    }

    function lightAtIndex(map, lightIndex) {
        if (!map || !Array.isArray(map.lightObjects)) return null;
        const index = Number(lightIndex);
        if (!Number.isInteger(index) || index < 0 || index >= map.lightObjects.length) return null;
        return { light: map.lightObjects[index], index };
    }

    function canMoveLight(payload, mapIndex, lightIndex, x, y) {
        const map = mapAt(payload, mapIndex);
        if (!map) return { ok: false, reason: 'missing-map' };
        const found = lightAtIndex(map, lightIndex);
        if (!found) return { ok: false, reason: 'missing-light' };
        const valid = validateCell(map, x, y);
        if (!valid.ok) return valid;
        const occupied = (map.lightObjects || []).some((other, index) => index !== found.index && Number(other.x) === valid.cell.x && Number(other.y) === valid.cell.y);
        if (occupied) return { ok: false, reason: 'occupied', cell: valid.cell, entity: found.light };
        return {
            ok: true,
            changed: Number(found.light.x) !== valid.cell.x || Number(found.light.y) !== valid.cell.y,
            cell: valid.cell,
            entity: found.light,
            index: found.index,
            selection: { kind: 'light', key: `light:${found.index}`, index: found.index, cell: valid.cell }
        };
    }

    function moveLight(payload, mapIndex, lightIndex, x, y) {
        const result = canMoveLight(payload, mapIndex, lightIndex, x, y);
        if (!result.ok || !result.changed) return result;
        result.entity.x = result.cell.x;
        result.entity.y = result.cell.y;
        return result;
    }

    return {
        TILE_BY_TOOL, tileForTool, cellBounds, validateCell, paintCell, eventById,
        canMoveEvent, moveEvent, moveWorldEvent,
        setTownCameraField,
        createGroundProfile, splitGroundProfileSegment, moveGroundProfilePoint, deleteGroundProfilePoint,
        canMoveLight, moveLight
    };
}));
