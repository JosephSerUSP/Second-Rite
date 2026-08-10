(function (root, factory) {
    if (typeof module === 'object' && module.exports) {
        module.exports = factory(require('./thestra-editor-scene.js'));
    } else {
        root.SecondRiteEditorAdapter = factory(root.ThestraEditorScene);
    }
}(typeof self !== 'undefined' ? self : this, function (SceneModel) {
    'use strict';

    if (!SceneModel) throw new Error('SecondRiteEditorAdapter requires ThestraEditorScene.');

    const DEFAULT_RENDERABLE_URL = 'http://127.0.0.1:8082/api/map-renderable';

    function mapAt(payload, mapIndex) {
        const maps = payload && payload.maps || [];
        const map = maps[mapIndex];
        if (!map) throw new Error(`No map at editor index ${mapIndex}.`);
        return map;
    }

    async function buildScene(payload, mapIndex) {
        return SceneModel.buildScene(payload, mapAt(payload, mapIndex));
    }

    async function loadRenderable(map, fetchImpl, endpoint) {
        if (!map) throw new Error('SecondRiteEditorAdapter.loadRenderable requires a map snapshot.');
        const fetcher = fetchImpl || (typeof fetch === 'function' ? fetch.bind(globalThis) : null);
        if (!fetcher) throw new Error('No fetch implementation is available for the runtime renderable bridge.');

        const response = await fetcher(endpoint || DEFAULT_RENDERABLE_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ map })
        });
        let payload;
        try {
            payload = await response.json();
        } catch (error) {
            throw new Error(`Runtime renderable bridge returned invalid JSON (${response.status}).`);
        }
        if (!response.ok) {
            throw new Error(payload && payload.error
                ? String(payload.error)
                : `Runtime renderable bridge failed (${response.status}).`);
        }
        if (!payload || !Array.isArray(payload.surfaces) || !Array.isArray(payload.materials)) {
            throw new Error('Runtime renderable bridge returned an invalid bundle.');
        }
        return payload;
    }

    return {
        DEFAULT_RENDERABLE_URL,
        buildScene,
        loadRenderable
    };
}));
