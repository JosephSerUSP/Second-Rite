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
    const DEFAULT_LIGHT = Object.freeze([1, 1, 1]);

    function mapAt(payload, mapIndex) {
        const maps = payload && payload.maps || [];
        const map = maps[mapIndex];
        if (!map) throw new Error(`No map at editor index ${mapIndex}.`);
        return map;
    }

    async function buildScene(payload, mapIndex, inspection) {
        return SceneModel.buildScene(payload, mapAt(payload, mapIndex), inspection);
    }

    function lightCellAt(light, x, y) {
        // Runtime positions/light coordinates are one-based. JSON arrays in the
        // browser are zero-based, so the same runtime corner (x,y) lives at
        // light[y - 1][x - 1] here.
        const row = Array.isArray(light) ? light[y - 1] : null;
        const value = Array.isArray(row) ? row[x - 1] : null;
        return Array.isArray(value) && value.length >= 3 ? value : DEFAULT_LIGHT;
    }

    function sampleLight(light, x, y, fx, fy) {
        if (!Array.isArray(light)) return DEFAULT_LIGHT;
        const c00 = lightCellAt(light, x, y);
        const c10 = lightCellAt(light, x + 1, y);
        const c01 = lightCellAt(light, x, y + 1);
        const c11 = lightCellAt(light, x + 1, y + 1);
        const top = [0, 1, 2].map(channel =>
            Number(c00[channel]) + (Number(c10[channel]) - Number(c00[channel])) * fx
        );
        const bottom = [0, 1, 2].map(channel =>
            Number(c01[channel]) + (Number(c11[channel]) - Number(c01[channel])) * fx
        );
        return top.map((value, channel) => value + (bottom[channel] - value) * fy);
    }

    function rememberUnlitColors(surface) {
        const colors = surface && surface.colors;
        if (!Array.isArray(colors)) return null;
        if (!Array.isArray(surface.unlitColors) || surface.unlitColors.length !== colors.length) {
            surface.unlitColors = colors.slice();
        }
        return surface.unlitColors;
    }

    function applyVertexLighting(bundle) {
        if (!bundle) return bundle;
        for (const surface of bundle.surfaces || []) rememberUnlitColors(surface);
        if (!Array.isArray(bundle.light)) return bundle;

        for (const surface of bundle.surfaces || []) {
            const positions = surface && surface.positions;
            const colors = surface && surface.colors;
            const unlitColors = rememberUnlitColors(surface);
            if (!Array.isArray(positions) || !Array.isArray(colors) || !Array.isArray(unlitColors)) continue;
            const vertexCount = Math.floor(positions.length / 3);
            if (colors.length < vertexCount * 4 || unlitColors.length < vertexCount * 4) continue;

            // The runtime collector deliberately preserves source/model vertex
            // colors. Lighting is another modulation, not a replacement. Keep
            // the unlit browser-side copy so Light authoring can immediately
            // preview a newly-authored bake without asking LÖVE to rebuild the
            // renderable bundle first.
            for (let index = 0; index < vertexCount; index++) {
                const x = Number(positions[index * 3]);
                const y = Number(positions[index * 3 + 1]);
                if (!Number.isFinite(x) || !Number.isFinite(y)) continue;
                const ix = Math.floor(x), iy = Math.floor(y);
                const lit = sampleLight(bundle.light, ix, iy, x - ix, y - iy);
                const colorIndex = index * 4;
                colors[colorIndex] = Number(unlitColors[colorIndex]) * lit[0];
                colors[colorIndex + 1] = Number(unlitColors[colorIndex + 1]) * lit[1];
                colors[colorIndex + 2] = Number(unlitColors[colorIndex + 2]) * lit[2];
                colors[colorIndex + 3] = Number(unlitColors[colorIndex + 3]);
            }
        }
        return bundle;
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

    async function loadRenderable(map, options, endpoint) {
        if (!map) throw new Error('SecondRiteEditorAdapter.loadRenderable requires a map snapshot.');
        const legacyFetch = typeof options === 'function' ? options : null;
        const requestOptions = options && typeof options === 'object' ? options : {};
        const fetcher = legacyFetch || requestOptions.fetchImpl || (typeof fetch === 'function' ? fetch.bind(globalThis) : null);
        if (!fetcher) throw new Error('No fetch implementation is available for the runtime renderable bridge.');
        const renderableUrl = endpoint || DEFAULT_RENDERABLE_URL;

        let response;
        try {
            response = await fetcher(renderableUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(Object.assign({ map }, Number.isFinite(requestOptions.seed) ? { seed: requestOptions.seed } : {}))
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
        return applyVertexLighting(payload);
    }

    return {
        DEFAULT_RENDERABLE_URL,
        buildScene,
        loadRenderable,
        applyVertexLighting
    };
}));