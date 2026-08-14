(function (root, factory) {
    if (typeof module === 'object' && module.exports) module.exports = factory();
    else root.ThestraViewportContract = factory();
}(typeof self !== 'undefined' ? self : this, function () {
    'use strict';

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

    return { transformTriangleStream, runtimePositionToThestra, runtimeNormalToThestra, eventVisualPlan };
}));
