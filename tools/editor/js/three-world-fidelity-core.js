(function (root, factory) {
    if (typeof module === 'object' && module.exports) module.exports = factory();
    else root.ThestraThreeWorldFidelityCore = factory();
}(typeof self !== 'undefined' ? self : this, function () {
    'use strict';

    const OPAQUE_FRAGMENT_MARKER = '#include <opaque_fragment>';
    const STATIC_WORLD_LINE = 'outgoingLight = diffuseColor.rgb + totalEmissiveRadiance;';

    function rewriteFragmentShader(source) {
        if (typeof source !== 'string' || !source.includes(OPAQUE_FRAGMENT_MARKER)) {
            throw new Error('Three world material shader no longer exposes <opaque_fragment>; static-light fidelity patch must be reviewed.');
        }
        if (source.includes(STATIC_WORLD_LINE)) return source;
        return source.replace(
            OPAQUE_FRAGMENT_MARKER,
            [
                '// Thestra Studio world surfaces already carry resolved static lighting in vertex RGB.',
                '// Keep Three scene lights for editor-only objects, but do not relight authored world geometry.',
                STATIC_WORLD_LINE,
                OPAQUE_FRAGMENT_MARKER
            ].join('\n')
        );
    }

    function isResolvedWorldMaterial(material) {
        return !!material
            && material.isMeshStandardMaterial === true
            && material.vertexColors === true
            && Number(material.metalness) === 0
            && Math.abs(Number(material.roughness) - 0.9) < 1e-9;
    }

    function install(THREE) {
        if (!THREE || !THREE.MeshStandardMaterial) {
            throw new Error('Thestra Three world fidelity requires THREE.MeshStandardMaterial.');
        }
        const prototype = THREE.MeshStandardMaterial.prototype;
        if (prototype.__thestraStaticWorldFidelityInstalled) return false;

        const previousCompile = prototype.onBeforeCompile;
        const previousCacheKey = prototype.customProgramCacheKey;

        prototype.onBeforeCompile = function (shader, renderer) {
            if (typeof previousCompile === 'function') previousCompile.call(this, shader, renderer);
            if (!isResolvedWorldMaterial(this)) return;
            shader.fragmentShader = rewriteFragmentShader(shader.fragmentShader);
        };

        prototype.customProgramCacheKey = function () {
            const base = typeof previousCacheKey === 'function'
                ? previousCacheKey.call(this) : '';
            return `${base}|thestra-static-world:${isResolvedWorldMaterial(this) ? 'resolved' : 'three-lit'}`;
        };

        Object.defineProperty(prototype, '__thestraStaticWorldFidelityInstalled', {
            value: true,
            configurable: false,
            enumerable: false,
            writable: false
        });
        return true;
    }

    return {
        OPAQUE_FRAGMENT_MARKER,
        STATIC_WORLD_LINE,
        rewriteFragmentShader,
        isResolvedWorldMaterial,
        install
    };
}));
