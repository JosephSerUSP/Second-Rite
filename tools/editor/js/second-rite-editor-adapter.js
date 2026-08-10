(function (root, factory) {
    if (typeof module === 'object' && module.exports) {
        module.exports = factory(require('./thestra-editor-scene.js'));
    } else {
        root.SecondRiteEditorAdapter = factory(root.ThestraEditorScene);
    }
}(typeof self !== 'undefined' ? self : this, function (SceneModel) {
    'use strict';

    if (!SceneModel) throw new Error('SecondRiteEditorAdapter requires ThestraEditorScene.');

    const POOLS = ['features', 'doors', 'fixturePrefabs'];
    const BASE_POOLS = ['walls', 'floors', 'ceilings', 'skies'];

    function copy(value) {
        if (!value || typeof value !== 'object') return value;
        if (Array.isArray(value)) return value.map(copy);
        const out = {};
        Object.keys(value).forEach(key => { out[key] = copy(value[key]); });
        return out;
    }

    function mergeObject(base, delta) {
        if (!delta || typeof delta !== 'object') return delta;
        if (Array.isArray(delta)) return copy(delta);
        const out = base && typeof base === 'object' && !Array.isArray(base) ? copy(base) : {};
        Object.keys(delta).forEach(key => {
            if (key === 'remove') return;
            const value = delta[key];
            if (value && typeof value === 'object' && !Array.isArray(value)) {
                out[key] = mergeObject(out[key], value);
            } else {
                out[key] = copy(value);
            }
        });
        return out;
    }

    function mergePool(base, delta) {
        const out = copy(base || []);
        const rebuildIndex = () => {
            const index = new Map();
            out.forEach((entry, i) => index.set(entry.id, i));
            return index;
        };
        let index = rebuildIndex();
        (delta || []).forEach(patch => {
            const at = index.get(patch.id);
            if (patch.remove === true) {
                if (at !== undefined) {
                    out.splice(at, 1);
                    index = rebuildIndex();
                }
            } else if (at !== undefined) {
                out[at] = mergeObject(out[at], patch);
            } else {
                out.push(mergeObject(null, patch));
                index.set(patch.id, out.length - 1);
            }
        });
        return out;
    }

    function resolveTileset(base, map) {
        if (!base) return null;
        const delta = map && map.tilesetOverride;
        if (!delta || typeof delta !== 'object' || Object.keys(delta).length === 0) return base;

        const value = mergeObject(base, delta);
        POOLS.forEach(pool => {
            if (delta[pool] !== undefined) value[pool] = mergePool(base[pool], delta[pool]);
        });
        if (delta.base !== undefined) {
            value.base = mergeObject(base.base || {}, delta.base);
            BASE_POOLS.forEach(pool => {
                if (delta.base[pool] !== undefined) {
                    value.base[pool] = mergePool(base.base && base.base[pool], delta.base[pool]);
                }
            });
        }
        value.id = base.id;
        return value;
    }

    async function loadTileset(map, fetchImpl) {
        const fetcher = fetchImpl || (typeof fetch === 'function' ? fetch.bind(globalThis) : null);
        const id = map.tileset || 'dungeon_default';
        if (!fetcher) return { id, tileset: null };
        const response = await fetcher('/api/tilesets');
        if (!response.ok) throw new Error(`Tileset inventory request failed (${response.status}).`);
        const payload = await response.json();
        const base = (payload.tilesets || []).find(entry => entry && entry.id === id) || null;
        return { id, tileset: resolveTileset(base, map) };
    }

    async function buildScene(payload, mapIndex, fetchImpl) {
        const maps = payload && payload.maps || [];
        const map = maps[mapIndex];
        if (!map) throw new Error(`No map at editor index ${mapIndex}.`);
        const resolved = await loadTileset(map, fetchImpl);
        return SceneModel.buildScene(payload, map, {
            tilesetId: resolved.id,
            tileset: resolved.tileset
        });
    }

    return {
        resolveTileset,
        loadTileset,
        buildScene
    };
}));
