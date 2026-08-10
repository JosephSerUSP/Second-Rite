(function (root, factory) {
    if (typeof module === 'object' && module.exports) {
        module.exports = factory();
    } else {
        root.ThestraEditorScene = factory();
    }
}(typeof self !== 'undefined' ? self : this, function () {
    'use strict';

    const SCENE_VERSION = 1;
    const DEFAULT_PROCEDURAL_SIZE = 21;

    function integerOr(value, fallback) {
        const n = Number(value);
        return Number.isFinite(n) && n > 0 ? Math.floor(n) : fallback;
    }

    function materializeLayout(map) {
        if (map && Array.isArray(map.layout) && map.layout.length > 0) {
            const rows = map.layout.map(row => String(row));
            const width = rows.reduce((max, row) => Math.max(max, row.length), 0);
            return { rows, width, height: rows.length, provisional: false, source: 'authored-layout' };
        }

        const width = integerOr(map && map.width, DEFAULT_PROCEDURAL_SIZE);
        const height = integerOr(map && map.height, DEFAULT_PROCEDURAL_SIZE);
        const rows = [];
        for (let y = 0; y < height; y++) {
            let row = '';
            for (let x = 0; x < width; x++) {
                row += (x === 0 || y === 0 || x === width - 1 || y === height - 1) ? '#' : '.';
            }
            rows.push(row);
        }
        return { rows, width, height, provisional: true, source: 'editor-procedural-placeholder' };
    }

    function tileAt(layout, x, y) {
        const row = layout.rows[y] || '';
        return row[x] || '#';
    }

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

    function buildScene(payload, map) {
        if (!map) throw new Error('ThestraEditorScene.buildScene requires a map.');

        const layout = materializeLayout(map);
        const cells = [];
        for (let y = 0; y < layout.height; y++) {
            for (let x = 0; x < layout.width; x++) {
                const tile = tileAt(layout, x, y);
                const semantic = semanticTile(tile);
                cells.push({
                    kind: 'cell',
                    key: `cell:${x}:${y}`,
                    cell: { x, y },
                    tile,
                    role: semantic.role,
                    walkable: semantic.walkable,
                    world: { x: x + 0.5, y: 0, z: y + 0.5 }
                });
            }
        }

        const events = (map.events || [])
            .filter(event => Number.isFinite(Number(event.x)) && Number.isFinite(Number(event.y)))
            .map((event, index) => {
                const x = Number(event.x);
                const y = Number(event.y);
                return {
                    kind: 'event',
                    key: `event:${event.id != null ? event.id : index}`,
                    id: event.id != null ? event.id : index,
                    label: event.label || event.name || `Event ${event.id != null ? event.id : index}`,
                    cell: { x, y },
                    world: { x: x + 0.5, y: 0.5, z: y + 0.5 },
                    size: { x: 1, y: 1, z: 1 },
                    // Metadata for inspectors/annotations only. Visible runtime
                    // geometry is supplied by #287's authoritative bundle.
                    asset: resolvedEventAsset(payload, event),
                    source: event
                };
            });

        return {
            version: SCENE_VERSION,
            map: {
                id: map.id,
                title: map.title || `Map ${map.id != null ? map.id : ''}`.trim(),
                layoutSource: layout.source,
                provisionalGeometry: layout.provisional
            },
            coordinateSystem: {
                authored: 'grid x/y',
                world: 'x/right, y/up, z/map-y',
                cellSize: 1
            },
            bounds: { width: layout.width, height: layout.height },
            cells,
            events,
            annotations: {
                anchors: (map.anchors || []).slice(),
                overrides: (map.overrides || []).slice()
            }
        };
    }

    function selectionForCell(x, y) {
        return { kind: 'cell', key: `cell:${x}:${y}`, cell: { x, y } };
    }

    return {
        SCENE_VERSION,
        materializeLayout,
        resolvedEventAsset,
        buildScene,
        selectionForCell
    };
}));
