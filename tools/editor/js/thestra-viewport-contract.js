(function (root, factory) {
    if (typeof module === 'object' && module.exports) module.exports = factory();
    else root.ThestraViewportContract = factory();
}(typeof self !== 'undefined' ? self : this, function () {
    'use strict';

    const DEFAULT_LIGHT_AMBIENT = Object.freeze([0.12, 0.12, 0.12]);
    const DEFAULT_LIGHT_SAMPLE = Object.freeze([1, 1, 1]);

    // The runtime bundle is Z-up.  Thestra is Y-up, but keeps the authored
    // grid's x/y ordering as world x/z.  This is an orientation-reversing
    // axis permutation, so every triangle stream must reverse its last two
    // vertices as it crosses this boundary.  Keeping this tiny contract free
    // of Three.js makes the coordinate rule directly testable.
    function transformTriangleStream(values, stride, transform) {
        if (!Array.isArray(values) || values.length % (stride * 3) !== 0) return [];
        const result = [];
        for (let triangle = 0; triangle < values.length; triangle += stride * 3) {
            for (const vertex of [0, 2, 1]) {
                const start = triangle + vertex * stride;
                const source = values.slice(start, start + stride).map(Number);
                const next = transform ? transform(source) : source;
                result.push(...next);
            }
        }
        return result;
    }

    function runtimePositionToThestra(value, coordinateSystem) {
        const origin = coordinateSystem && coordinateSystem.runtimeGridOrigin || { x: 1, y: 1 };
        return [
            Number(value[0]) - Number(origin.x || 1),
            Number(value[2]),
            Number(value[1]) - Number(origin.y || 1)
        ];
    }

    function runtimeNormalToThestra(value) {
        return [Number(value[0]), Number(value[2]), Number(value[1])];
    }

    function eventVisualPlan(asset) {
        if (asset && typeof asset.model === 'string' && asset.model) return { kind: 'model', path: asset.model };
        if (asset && typeof asset.sprite === 'string' && asset.sprite) return { kind: 'sprite', path: asset.sprite };
        return { kind: 'fallback', path: null };
    }

    function lightingCellMap(sceneModel) {
        const cells = new Map();
        for (const cell of sceneModel && sceneModel.cells || []) {
            if (!cell || !cell.cell) continue;
            cells.set(`${Number(cell.cell.x)},${Number(cell.cell.y)}`, cell.role);
        }
        return cells;
    }

    // Exact browser-side counterpart of engine/lighting.lua for the interactive
    // authoring membrane.  This is deliberately a presentation calculation:
    // authored lightObjects remain the source of truth and LÖVE remains free to
    // rebake/verify the resolved runtime grid asynchronously.
    function bakeAuthoringLighting(sceneModel, sources, ambient) {
        const width = Math.max(0, Number(sceneModel && sceneModel.bounds && sceneModel.bounds.width) || 0);
        const height = Math.max(0, Number(sceneModel && sceneModel.bounds && sceneModel.bounds.height) || 0);
        const baseline = Array.isArray(ambient) && ambient.length >= 3 ? ambient : DEFAULT_LIGHT_AMBIENT;
        const cells = lightingCellMap(sceneModel);

        function isWall(x, y) {
            // Runtime lighting.lua receives one-based grid coordinates here.
            const role = cells.get(`${x - 1},${y - 1}`);
            return role == null || role === 'wall';
        }

        function visible(x0, y0, x1, y1) {
            const dx = Math.abs(x1 - x0), dy = Math.abs(y1 - y0);
            const sx = x0 < x1 ? 1 : -1, sy = y0 < y1 ? 1 : -1;
            let err = dx - dy, x = x0, y = y0;
            while (x !== x1 || y !== y1) {
                if ((x !== x0 || y !== y0) && isWall(x, y)) return false;
                const e2 = err * 2;
                if (e2 > -dy) { err -= dy; x += sx; }
                if (e2 < dx) { err += dx; y += sy; }
            }
            return true;
        }

        const out = [];
        for (let vy = 0; vy <= height; vy++) {
            const row = [];
            for (let vx = 0; vx <= width; vx++) {
                row.push([Number(baseline[0]), Number(baseline[1]), Number(baseline[2])]);
            }
            out.push(row);
        }

        for (const source of sources || []) {
            const sourceX = Number(source && source.x);
            const sourceY = Number(source && source.y);
            if (!Number.isFinite(sourceX) || !Number.isFinite(sourceY)) continue;
            const radius = Math.max(0.1, Number(source.radius) || 4);
            const falloff = source.falloff == null ? 2 : Number(source.falloff);
            const exponent = Number.isFinite(falloff) ? falloff : 2;
            const color = Array.isArray(source.color) && source.color.length >= 3
                ? source.color : [1, 0.65, 0.3];

            const minY = Math.max(0, Math.floor(sourceY - radius));
            const maxY = Math.min(height, Math.ceil(sourceY + radius));
            const minX = Math.max(0, Math.floor(sourceX - radius));
            const maxX = Math.min(width, Math.ceil(sourceX + radius));
            for (let vy = minY; vy <= maxY; vy++) {
                for (let vx = minX; vx <= maxX; vx++) {
                    const dx = vx - (sourceX + 0.5);
                    const dy = vy - (sourceY + 0.5);
                    const distance = Math.sqrt(dx * dx + dy * dy);
                    const targetX = Math.max(1, Math.min(width, vx));
                    const targetY = Math.max(1, Math.min(height, vy));
                    if (distance > radius || !visible(sourceX + 1, sourceY + 1, targetX, targetY)) continue;
                    const strength = Math.pow(1 - distance / radius, exponent);
                    const dst = out[vy][vx];
                    for (let channel = 0; channel < 3; channel++) {
                        dst[channel] = Math.min(1, dst[channel] + Number(color[channel]) * strength);
                    }
                }
            }
        }
        return out;
    }

    function authoringLightCell(light, x, y) {
        const row = Array.isArray(light) ? light[y] : null;
        const value = Array.isArray(row) ? row[x] : null;
        return Array.isArray(value) && value.length >= 3 ? value : DEFAULT_LIGHT_SAMPLE;
    }

    // Three-space x/z coordinates are zero-based authored grid coordinates, so
    // this is the same bilinear sample used by the runtime renderer after the
    // one-based runtime bundle origin has crossed the viewport adapter.
    function sampleAuthoringLighting(light, x, y) {
        if (!Array.isArray(light)) return DEFAULT_LIGHT_SAMPLE;
        const ix = Math.floor(Number(x)), iy = Math.floor(Number(y));
        const fx = Number(x) - ix, fy = Number(y) - iy;
        const c00 = authoringLightCell(light, ix, iy);
        const c10 = authoringLightCell(light, ix + 1, iy);
        const c01 = authoringLightCell(light, ix, iy + 1);
        const c11 = authoringLightCell(light, ix + 1, iy + 1);
        const top = [0, 1, 2].map(channel =>
            Number(c00[channel]) + (Number(c10[channel]) - Number(c00[channel])) * fx
        );
        const bottom = [0, 1, 2].map(channel =>
            Number(c01[channel]) + (Number(c11[channel]) - Number(c01[channel])) * fx
        );
        return top.map((value, channel) => value + (bottom[channel] - value) * fy);
    }

    // Authored cells occupy [n, n + 1] but events/lights live at their
    // centres. Keep the conversion explicit so viewport interaction never
    // accidentally uses Three's integer world grid as the authored grid.
    function cellCenter(value) { return Math.round(Number(value) - 0.5) + 0.5; }
    function cellCoordinate(value) { return Math.round(Number(value) - 0.5); }

    // Keyboard policy is deliberately pure: viewport ownership decides whether
    // to act, while this contract guarantees forms and browser shortcuts keep
    // their ordinary meaning.
    function cameraShortcut(event, viewportFocused) {
        const tag = event && event.target && String(event.target.tagName || '').toLowerCase();
        if (!viewportFocused || !event || event.ctrlKey || event.metaKey || event.altKey
                || event.target && (event.target.isContentEditable || ['input', 'textarea', 'select'].includes(tag))) return null;
        if (event.code === 'Numpad5') return 'toggle-projection';
        if (event.code === 'Numpad7') return 'top';
        if (event.code === 'Numpad1') return 'perspective';
        if (event.code === 'Home') return 'frame-all';
        if (event.code === 'NumpadPeriod' || event.key === '.') return 'frame-selection';
        if (event.code === 'Escape') return 'cancel-navigation';
        return null;
    }

    return {
        DEFAULT_LIGHT_AMBIENT,
        transformTriangleStream, runtimePositionToThestra, runtimeNormalToThestra,
        eventVisualPlan, bakeAuthoringLighting, sampleAuthoringLighting,
        cellCenter, cellCoordinate, cameraShortcut
    };
}));