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
        transformTriangleStream, runtimePositionToThestra, runtimeNormalToThestra,
        eventVisualPlan, cellCenter, cellCoordinate, cameraShortcut
    };
}));
