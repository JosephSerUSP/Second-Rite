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

    return { TILE_BY_TOOL, tileForTool, cellBounds, validateCell, paintCell, eventById, canMoveEvent, moveEvent, canMoveLight, moveLight };
}));
