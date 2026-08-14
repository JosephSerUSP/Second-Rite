(function (root, factory) {
    if (typeof module === 'object' && module.exports) module.exports = factory();
    else root.ThestraEditorScene = factory();
}(typeof self !== 'undefined' ? self : this, function () {
    'use strict';

    const SCENE_VERSION = 2;
    const DEFAULT_PROCEDURAL_SIZE = 21;

    function integerOr(value, fallback) {
        const n = Number(value);
        return Number.isFinite(n) && n > 0 ? Math.floor(n) : fallback;
    }

    function materializeLayout(map) {
        if (map && Array.isArray(map.layout) && map.layout.length > 0) {
            const rows = map.layout.map(row => String(row));
            return { rows, width: rows.reduce((max, row) => Math.max(max, row.length), 0), height: rows.length, provisional: false, source: 'authored-layout' };
        }
        const width = integerOr(map && map.width, DEFAULT_PROCEDURAL_SIZE);
        const height = integerOr(map && map.height, DEFAULT_PROCEDURAL_SIZE);
        const rows = [];
        for (let y = 0; y < height; y++) {
            let row = '';
            for (let x = 0; x < width; x++) row += (x === 0 || y === 0 || x === width - 1 || y === height - 1) ? '#' : '.';
            rows.push(row);
        }
        return { rows, width, height, provisional: true, source: 'editor-procedural-placeholder' };
    }

    function tileAt(layout, x, y) { return (layout.rows[y] || '')[x] || '#'; }
    function semanticTile(tile) {
        if (tile === '#') return { role: 'wall', walkable: false };
        if (tile === 'o') return { role: 'opening', walkable: true };
        return { role: 'floor', walkable: true };
    }
    function commonEventFor(payload, event) {
        if (!payload || !payload.commonEvents || !event || event.scriptId == null) return null;
        return payload.commonEvents[String(event.scriptId)] || payload.commonEvents[event.scriptId] || null;
    }
    function resolvedEventAsset(payload, event) {
        const commonEvent = commonEventFor(payload, event);
        let model = event && event.model;
        if (model === undefined && commonEvent) model = commonEvent.model;
        if (model === false) model = null;
        let sprite = event && event.sprite;
        if (!sprite && commonEvent) sprite = commonEvent.sprite || null;
        return {
            model: typeof model === 'string' && model ? model : null,
            sprite: typeof sprite === 'string' && sprite ? sprite : null,
            provenance: model ? 'model' : (sprite ? 'sprite' : 'fallback')
        };
    }
    function authoredPoint(value, fallback) {
        const n = Number(value);
        return Number.isFinite(n) ? n : fallback;
    }

    function resolvedPreviewMap(map, inspection) {
        if (!inspection || !inspection.generated || !Array.isArray(inspection.generated.grid)) return map;
        const generated = inspection.generated;
        return Object.assign({}, map, {
            layout: generated.grid.slice(),
            events: (map.events || []).concat(generated.events || []),
            lightObjects: (map.lightObjects || []).concat(generated.lights || [])
        });
    }

    function buildScene(payload, map, inspection) {
        if (!map) throw new Error('ThestraEditorScene.buildScene requires a map.');
        map = resolvedPreviewMap(map, inspection);
        const layout = materializeLayout(map);
        const cells = [];
        for (let y = 0; y < layout.height; y++) {
            for (let x = 0; x < layout.width; x++) {
                const tile = tileAt(layout, x, y);
                const semantic = semanticTile(tile);
                cells.push({ kind: 'cell', key: `cell:${x}:${y}`, cell: { x, y }, tile, role: semantic.role, walkable: semantic.walkable, world: { x: x + 0.5, y: 0, z: y + 0.5 } });
            }
        }

        const events = (map.events || []).filter(event => Number.isFinite(Number(event.x)) && Number.isFinite(Number(event.y))).map((event, index) => {
            const x = Number(event.x), y = Number(event.y);
            return {
                kind: 'event', key: `event:${event.id != null ? event.id : index}`, id: event.id != null ? event.id : index, index,
                label: event.label || event.name || `Event ${event.id != null ? event.id : index}`,
                cell: { x, y }, world: { x: x + 0.5, y: 0.5, z: y + 0.5 }, size: { x: 1, y: 1, z: 1 },
                asset: resolvedEventAsset(payload, event), source: event
            };
        });

        const lights = (map.lightObjects || []).map((light, index) => ({ light, index }))
            .filter(entry => Number.isFinite(Number(entry.light.x)) && Number.isFinite(Number(entry.light.y)))
            .map(entry => {
                const light = entry.light, x = Number(light.x), y = Number(light.y);
                return {
                    kind: 'light', key: `light:${entry.index}`, index: entry.index, cell: { x, y }, world: { x: x + 0.5, y: 0.55, z: y + 0.5 },
                    radius: Math.max(0.1, authoredPoint(light.radius, 4)), falloff: Math.max(0, authoredPoint(light.falloff, 2)),
                    color: Array.isArray(light.color) ? light.color.slice(0, 3) : [1, 0.58, 0.22], material: light.material || null, source: light
                };
            });

        const overrides = (map.overrides || []).map((override, index) => ({ override, index }))
            .filter(entry => Number.isFinite(Number(entry.override.x)) && Number.isFinite(Number(entry.override.y)))
            .map(entry => {
                const x = Number(entry.override.x), y = Number(entry.override.y);
                return { kind: 'override', key: `override:${entry.index}`, index: entry.index, cell: { x, y }, world: { x: x + 0.5, y: 0.035, z: y + 0.5 }, source: entry.override };
            });

        let spawn = null;
        const authoredSpawn = payload && payload.system && payload.system.spawn;
        if (authoredSpawn && String(authoredSpawn.mapId) === String(map.id) && Number.isFinite(Number(authoredSpawn.x)) && Number.isFinite(Number(authoredSpawn.y))) {
            const x = Number(authoredSpawn.x), y = Number(authoredSpawn.y);
            spawn = { kind: 'spawn', key: 'spawn', cell: { x, y }, world: { x: x + 0.5, y: 0.2, z: y + 0.5 }, source: authoredSpawn };
        }

        return {
            version: SCENE_VERSION,
            map: { id: map.id, title: map.title || `Map ${map.id != null ? map.id : ''}`.trim(), layoutSource: layout.source, provisionalGeometry: layout.provisional },
            coordinateSystem: { authored: 'grid x/y', world: 'x/right, y/up, z/map-y', cellSize: 1 },
            bounds: { width: layout.width, height: layout.height },
            cells, events, lights,
            annotations: { anchors: (map.anchors || []).slice(), overrides, spawn }
        };
    }

    function selectionForCell(x, y) { return { kind: 'cell', key: `cell:${x}:${y}`, cell: { x, y } }; }
    return { SCENE_VERSION, materializeLayout, resolvedEventAsset, resolvedPreviewMap, buildScene, selectionForCell };
}));
