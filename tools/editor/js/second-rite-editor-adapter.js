(function (root, factory) {
    if (typeof module === 'object' && module.exports) {
        module.exports = factory(require('./thestra-editor-scene.js'), require('./vertex-shading.js'));
    } else {
        root.SecondRiteEditorAdapter = factory(root.ThestraEditorScene, root.ThestraVertexShading);
    }
}(typeof self !== 'undefined' ? self : this, function (SceneModel, VertexShading) {
    'use strict';

    if (!SceneModel) throw new Error('SecondRiteEditorAdapter requires ThestraEditorScene.');
    if (!VertexShading) throw new Error('SecondRiteEditorAdapter requires ThestraVertexShading.');

    const DEFAULT_RENDERABLE_URL = 'http://127.0.0.1:8082/api/map-renderable';
    const DEFAULT_LIGHT = Object.freeze([1, 1, 1]);
    const SHADING_SAMPLE = [1, 1, 1];
    const SIDE_WALL_FACTOR = 0.76;

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

    function rememberSourceColors(surface) {
        const colors = surface && surface.colors;
        if (!Array.isArray(colors)) return null;
        if (!Array.isArray(surface.sourceColors) || surface.sourceColors.length !== colors.length) {
            surface.sourceColors = Array.isArray(surface.unlitColors)
                && surface.unlitColors.length === colors.length
                ? surface.unlitColors.slice() : colors.slice();
        }
        return surface.sourceColors;
    }

    function surfaceOrientationFactor(surface) {
        const source = surface && surface.source || {};
        const role = source.surface;
        // Runtime viewport_3d.prepareResolvedWallFaces marks north/south faces
        // as sideDarken and colorAt() multiplies them by 0.76. Structural
        // openings do the same for their y-axis orientation. Keep this explicit
        // in the source-color baseline so authored tint + live lamp rebakes
        // preserve the runtime orientation cue instead of relying on Three lights.
        if (role === 'north-wall' || role === 'south-wall') return SIDE_WALL_FACTOR;
        if (role === 'opening' && source.axis === 'y') return SIDE_WALL_FACTOR;
        return 1;
    }

    function applyVertexShading(bundle, layersOverride) {
        if (!bundle) return bundle;
        const layers = layersOverride === undefined ? (bundle.vertexShadingLayers || []) : (layersOverride || []);
        const compiled = VertexShading.compile(layers, 'map vertexShadingLayers');

        for (const surface of bundle.surfaces || []) {
            const positions = surface && surface.positions;
            const sourceColors = rememberSourceColors(surface);
            if (!Array.isArray(positions) || !Array.isArray(sourceColors)) continue;
            const vertexCount = Math.floor(positions.length / 3);
            if (sourceColors.length < vertexCount * 4) continue;
            const shaded = sourceColors.slice();
            const orientation = surfaceOrientationFactor(surface);
            for (let index = 0; index < vertexCount; index++) {
                const x = Number(positions[index * 3]);
                const y = Number(positions[index * 3 + 1]);
                if (!Number.isFinite(x) || !Number.isFinite(y)) continue;
                // Runtime world coordinates are one-based while the authored
                // shading field is defined over zero-based map vertices.
                const tint = VertexShading.sampleCompiled(compiled, x - 1, y - 1, SHADING_SAMPLE);
                const colorIndex = index * 4;
                shaded[colorIndex] = Number(sourceColors[colorIndex]) * tint[0] * orientation;
                shaded[colorIndex + 1] = Number(sourceColors[colorIndex + 1]) * tint[1] * orientation;
                shaded[colorIndex + 2] = Number(sourceColors[colorIndex + 2]) * tint[2] * orientation;
                shaded[colorIndex + 3] = Number(sourceColors[colorIndex + 3]);
            }
            surface.unlitColors = shaded;
            surface.colors = shaded.slice();
        }
        bundle.vertexShadingLayers = layers;
        return bundle;
    }

    function applyVertexLighting(bundle) {
        if (!bundle) return bundle;
        for (const surface of bundle.surfaces || []) {
            rememberSourceColors(surface);
            if (!Array.isArray(surface.unlitColors)) surface.unlitColors = surface.sourceColors.slice();
            surface.colors = surface.unlitColors.slice();
        }
        if (!Array.isArray(bundle.light)) return bundle;

        for (const surface of bundle.surfaces || []) {
            const positions = surface && surface.positions;
            const colors = surface && surface.colors;
            const unlitColors = surface && surface.unlitColors;
            if (!Array.isArray(positions) || !Array.isArray(colors) || !Array.isArray(unlitColors)) continue;
            const vertexCount = Math.floor(positions.length / 3);
            if (colors.length < vertexCount * 4 || unlitColors.length < vertexCount * 4) continue;

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

    function applyVertexModulation(bundle, layersOverride) {
        applyVertexShading(bundle, layersOverride);
        return applyVertexLighting(bundle);
    }

    async function bridgeProcessIsReachable(fetcher, endpoint) {
        try {
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


    // #736/#739 experiment: the bridge may carry vertex streams as quantized
    // Int16 instead of JSON floats. Decode at the boundary so every consumer
    // downstream -- shading, lighting, the Three viewport, OBJ export -- keeps
    // seeing ordinary arrays and no second code path appears.
    function decodeInt16Stream(stream, scale) {
        const binary = typeof atob === 'function'
            ? atob(stream.base64)
            : Buffer.from(stream.base64, 'base64').toString('binary');
        const values = new Array(stream.count);
        for (let index = 0; index < stream.count; index++) {
            const lo = binary.charCodeAt(index * 2);
            const hi = binary.charCodeAt(index * 2 + 1);
            let word = lo + hi * 256;
            if (word > 32767) word -= 65536;
            values[index] = word / scale;
        }
        return values;
    }

    function decodeTransport(bundle) {
        const encoding = bundle && bundle.encoding;
        if (!encoding || encoding.kind !== 'int16-base64') return bundle;
        const scales = encoding.scales || {};
        for (const surface of bundle.surfaces || []) {
            for (const key of ['positions', 'uvs', 'normals', 'colors']) {
                const stream = surface[key];
                if (!stream || stream.kind !== 'int16-base64') continue;
                const scale = Number(scales[key]);
                if (!Number.isFinite(scale) || scale <= 0) {
                    throw new Error(`Renderable bundle declares no scale for ${key}.`);
                }
                surface[key] = decodeInt16Stream(stream, scale);
            }
        }
        delete bundle.encoding;
        return bundle;
    }

    async function loadRenderable(map, options, endpoint) {
        if (!map) throw new Error('SecondRiteEditorAdapter.loadRenderable requires a map snapshot.');
        const legacyFetch = typeof options === 'function' ? options : null;
        const requestOptions = options && typeof options === 'object' ? options : {};
        const fetcher = legacyFetch || requestOptions.fetchImpl || (typeof fetch === 'function' ? fetch.bind(globalThis) : null);
        if (!fetcher) throw new Error('No fetch implementation is available for the runtime renderable bridge.');
        // The bridge is a separate host process on its own port. Electron starts
        // it on the default; tooling that must not collide with a developer's
        // running Studio (the G6 gate) starts its own on a free port and
        // publishes the URL here. Same bridge, same contract -- only the port
        // moves, so this never becomes a second code path.
        const renderableUrl = endpoint
            || (typeof globalThis !== 'undefined' && globalThis.THESTRA_RENDERABLE_URL)
            || DEFAULT_RENDERABLE_URL;

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
        decodeTransport(payload);
        return applyVertexModulation(payload, map.vertexShadingLayers || payload.vertexShadingLayers || []);
    }

    return {
        DEFAULT_RENDERABLE_URL,
        SIDE_WALL_FACTOR,
        buildScene,
        loadRenderable,
        decodeTransport,
        surfaceOrientationFactor,
        applyVertexShading,
        applyVertexLighting,
        applyVertexModulation
    };
}));
