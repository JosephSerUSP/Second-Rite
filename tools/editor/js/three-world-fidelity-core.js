(function (root, factory) {
    if (typeof module === 'object' && module.exports) module.exports = factory();
    else root.ThestraThreeWorldFidelityCore = factory();
}(typeof self !== 'undefined' ? self : this, function () {
    'use strict';

    const OPAQUE_FRAGMENT_MARKER = '#include <opaque_fragment>';
    const STATIC_WORLD_LINE = 'outgoingLight = thestraLinearRgb + totalEmissiveRadiance;';
    const DIRECT_RGB_BLOCK = [
        '// LÖVE 11.5 runs this project without gamma-correct rendering: runtime world RGB is',
        '// literally texel.rgb * authored modulation. Bundle albedo is sampled as raw display RGB',
        '// in Studio, then converted to linear only at the final Three output seam so the renderer',
        '// sRGB transform returns the same direct product on screen.',
        'vec3 thestraDisplayRgb = clamp( diffuseColor.rgb, vec3( 0.0 ), vec3( 1.0 ) );',
        'vec3 thestraLinearRgb = mix(',
        '    thestraDisplayRgb / 12.92,',
        '    pow( ( thestraDisplayRgb + 0.055 ) / 1.055, vec3( 2.4 ) ),',
        '    step( vec3( 0.04045 ), thestraDisplayRgb )',
        ');',
        STATIC_WORLD_LINE
    ].join('\n');

    function rewriteFragmentShader(source) {
        if (typeof source !== 'string' || !source.includes(OPAQUE_FRAGMENT_MARKER)) {
            throw new Error('Three world material shader no longer exposes <opaque_fragment>; static-light fidelity must be reviewed.');
        }
        if (source.includes(STATIC_WORLD_LINE)) return source;
        return source.replace(
            OPAQUE_FRAGMENT_MARKER,
            [
                '// Thestra authoritative world surfaces already carry resolved static lighting in vertex RGB.',
                '// Keep Three scene lights for editor-only objects, but do not relight runtime-resolved world geometry.',
                DIRECT_RGB_BLOCK,
                OPAQUE_FRAGMENT_MARKER
            ].join('\n')
        );
    }

    function decorateResolvedWorldMaterial(material) {
        if (!material || material.isMeshStandardMaterial !== true) {
            throw new Error('Thestra world fidelity can decorate only a MeshStandardMaterial instance.');
        }
        if (material.userData && material.userData.thestraResolvedWorldFidelity) return material;

        const previousCompile = material.onBeforeCompile;
        const previousCacheKey = material.customProgramCacheKey;
        material.onBeforeCompile = function (shader, renderer) {
            if (typeof previousCompile === 'function') previousCompile.call(this, shader, renderer);
            shader.fragmentShader = rewriteFragmentShader(shader.fragmentShader);
        };
        material.customProgramCacheKey = function () {
            const base = typeof previousCacheKey === 'function' ? previousCacheKey.call(this) : '';
            return `${base}|thestra-resolved-world-direct-rgb`;
        };
        material.userData = material.userData || {};
        material.userData.thestraResolvedWorldFidelity = true;
        return material;
    }

    function prepareResolvedWorldAlbedo(THREE, texture) {
        if (!THREE || THREE.NoColorSpace === undefined) {
            throw new Error('Thestra world fidelity requires Three.NoColorSpace.');
        }
        if (!texture) return texture;
        texture.colorSpace = THREE.NoColorSpace;
        texture.needsUpdate = true;
        return texture;
    }

    return {
        OPAQUE_FRAGMENT_MARKER,
        STATIC_WORLD_LINE,
        DIRECT_RGB_BLOCK,
        rewriteFragmentShader,
        decorateResolvedWorldMaterial,
        prepareResolvedWorldAlbedo
    };
}));
