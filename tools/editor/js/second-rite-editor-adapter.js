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

    async function bridgeProcessIsReachable(fetcher, endpoint) {
        try {
            // A no-cors GET cannot read bridge data or launch LÖVE, but an opaque
            // response proves that something is listening on the bridge port.
            // This lets Studio distinguish "bridge absent" from "bridge alive
            // but refusing this browser origin" without relaxing the CORS gate.
            await fetcher(endpoint, {
                method: 'GET',
                mode: 'no-cors',
                cache: 'no-store'
            });
            return true;
        } catch (error) {
            return false;
        }
    }

    async function loadRenderable(map, fetchImpl, endpoint) {
        if (!map) throw new Error('SecondRiteEditorAdapter.loadRenderable requires a map snapshot.');
        const fetcher = fetchImpl || (typeof fetch === 'function' ? fetch.bind(globalThis) : null);
        if (!fetcher) throw new Error('No fetch implementation is available for the runtime renderable bridge.');
        const renderableUrl = endpoint || DEFAULT_RENDERABLE_URL;

        let response;
        try {
            response = await fetcher(renderableUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ map })
            });
        } catch (error) {
            const reachable = await bridgeProcessIsReachable(fetcher, renderableUrl);
            const failure = new Error(reachable
                ? 'Runtime renderable bridge is running but refused the Studio request. Check EDITOR_PORT and the bridge log.'
                : `Runtime renderable bridge is not reachable at ${renderableUrl}.`);
            failure.code = reachable ? 'bridge-refused' : 'bridge-unreachable';
            failure.cause = error;
            throw failure;
        }

        let payload;
        try {
            payload = await response.json();
        } catch (error) {
            throw new Error(`Runtime renderable bridge returned invalid JSON (${response.status}).`);
        }
        if (!response.ok) {
            const failure = new Error(payload && payload.error
                ? String(payload.error)
                : `Runtime renderable bridge failed (${response.status}).`);
            failure.code = response.status === 403 ? 'bridge-refused' : 'bridge-runtime-error';
            throw failure;
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
