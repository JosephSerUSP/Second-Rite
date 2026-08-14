(function (root, factory) {
    if (typeof module === 'object' && module.exports) module.exports = factory();
    else root.ThestraThreeWorldFidelityCore = factory();
}(typeof self !== 'undefined' ? self : this, function () {
    'use strict';

    const OPAQUE_FRAGMENT_MARKER = '#include <opaque_fragment>';
    const STATIC_WORLD_LINE = 'outgoingLight = thestraLinearRgb + totalEmissiveRadiance;';
    const DIRECT_RGB_BLOCK = [
        '// LÖVE 11.5 runs this project without gamma-correct rendering: runtime world RGB is',
        '// literally texel.rgb * authored modulation. Bundle albedo is therefore sampled as raw',
        '// display RGB in Studio, then converted to linear only at the final Three output seam so',
        '// WebGLRenderer\'s sRGB output transform returns that same direct product on screen.',
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
            throw new Error('Three world material shader no longer exposes <opaque_fragment>; static-light fidelity patch must be reviewed.');
        }
        if (source.includes(STATIC_WORLD_LINE)) return source;
        return source.replace(
            OPAQUE_FRAGMENT_MARKER,
            [
                '// Thestra Studio world surfaces already carry resolved static lighting in vertex RGB.',
                '// Keep Three scene lights for editor-only objects, but do not relight authored world geometry.',
                DIRECT_RGB_BLOCK,
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
        if (!THREE || !THREE.MeshStandardMaterial || THREE.NoColorSpace === undefined) {
            throw new Error('Thestra Three world fidelity requires MeshStandardMaterial and NoColorSpace.');
        }
        const prototype = THREE.MeshStandardMaterial.prototype;
        if (prototype.__thestraStaticWorldFidelityInstalled) return false;

        const previousCompile = prototype.onBeforeCompile;
        const previousCacheKey = prototype.customProgramCacheKey;

        prototype.onBeforeCompile = function (shader, renderer) {
            if (typeof previousCompile === 'function') previousCompile.call(this, shader, renderer);
            if (!isResolvedWorldMaterial(this)) return;

            // Runtime LÖVE is not gamma-correct (`conf.lua` leaves that option
            // disabled), so its world shader multiplies the texture's stored RGB
            // directly by static light. Three otherwise decodes SRGBColorSpace
            // albedo before vertex modulation, which makes dark lighting visibly
            // brighter even after the second scene-light response is removed.
            // Retag only authoritative world albedo; sprites/gizmos keep normal
            // Three color management. Texture upload happens after material
            // program preparation, and needsUpdate makes an already-seen texture
            // re-upload with the reviewed color-space contract if necessary.
            if (this.map && this.map.colorSpace !== THREE.NoColorSpace) {
                this.map.colorSpace = THREE.NoColorSpace;
                this.map.needsUpdate = true;
            }
            shader.fragmentShader = rewriteFragmentShader(shader.fragmentShader);
        };

        prototype.customProgramCacheKey = function () {
            const base = typeof previousCacheKey === 'function'
                ? previousCacheKey.call(this) : '';
            return `${base}|thestra-static-world:${isResolvedWorldMaterial(this) ? 'resolved-direct-rgb' : 'three-lit'}`;
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
        DIRECT_RGB_BLOCK,
        rewriteFragmentShader,
        isResolvedWorldMaterial,
        install
    };
}));
