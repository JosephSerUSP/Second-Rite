(function (root, factory) {
    if (typeof module === 'object' && module.exports) module.exports = factory();
    else root.ThestraVertexShading = factory();
}(typeof self !== 'undefined' ? self : this, function () {
    'use strict';

    const MODULUS = 65521;
    const HASH_MULTIPLIER = 25173;
    const HASH_ADDEND = 13849;
    const MAX_SEED = 2147483646;
    const FRACTAL_PERSISTENCE = 0.55;
    const FRACTAL_OCTAVES = Object.freeze([
        Object.freeze([0.8, -0.6, 0.6, 0.8, 3.17, -5.29]),
        Object.freeze([0.6, 0.8, -0.8, 0.6, 17.17, -9.31]),
        Object.freeze([-0.8, 0.6, -0.6, -0.8, -13.73, 21.47]),
        Object.freeze([-0.6, -0.8, 0.8, -0.6, 29.11, 14.53])
    ]);

    function positiveModulo(value, modulus) {
        const result = value % modulus;
        return result < 0 ? result + modulus : result;
    }

    function lerp(a, b, t) { return a + (b - a) * t; }
    function smoothstep(t) { return t * t * (3 - 2 * t); }

    function hash01(x, y, seed) {
        const ix = positiveModulo(Math.floor(x), MODULUS);
        const iy = positiveModulo(Math.floor(y), MODULUS);
        const iseed = positiveModulo(Math.floor(seed || 0), MODULUS);
        let value = (ix * 3749 + iy * 9151 + iseed * 1013) % MODULUS;
        value = (value * HASH_MULTIPLIER + HASH_ADDEND) % MODULUS;
        value = (value * HASH_MULTIPLIER + HASH_ADDEND) % MODULUS;
        return value / (MODULUS - 1);
    }

    function valueNoise(x, y, seed) {
        const x0 = Math.floor(x), y0 = Math.floor(y);
        const fx = x - x0, fy = y - y0;
        const sx = smoothstep(fx), sy = smoothstep(fy);
        const top = lerp(hash01(x0, y0, seed), hash01(x0 + 1, y0, seed), sx);
        const bottom = lerp(hash01(x0, y0 + 1, seed), hash01(x0 + 1, y0 + 1, seed), sx);
        return lerp(top, bottom, sy);
    }

    // Four deterministic, rotated/offset value-noise octaves. Rotation breaks
    // the obvious X/Y interpolation axes while the octave stack supplies both
    // broad regional drift and smaller-scale structure. Constants are literal
    // in the paired Lua implementation so Studio and runtime sample one field.
    function fractalNoise(x, y, seed) {
        let total = 0;
        let amplitude = 1;
        let normalizer = 0;
        let frequency = 1;
        for (let octave = 0; octave < FRACTAL_OCTAVES.length; octave++) {
            const [xx, xy, yx, yy, offsetX, offsetY] = FRACTAL_OCTAVES[octave];
            const rotatedX = (x * xx + y * xy + offsetX) * frequency;
            const rotatedY = (x * yx + y * yy + offsetY) * frequency;
            total += valueNoise(rotatedX, rotatedY, seed + octave * 7919) * amplitude;
            normalizer += amplitude;
            amplitude *= FRACTAL_PERSISTENCE;
            frequency *= 2;
        }
        return total / normalizer;
    }

    function rgbProblems(value, where, problems) {
        if (!Array.isArray(value) || value.length !== 3) {
            problems.push(`${where} must be an RGB triple`);
            return;
        }
        value.forEach((channel, index) => {
            if (!Number.isFinite(channel) || channel < 0 || channel > 1) {
                problems.push(`${where} channel ${index + 1} must be a number in 0..1`);
            }
        });
    }

    function validate(layers, where = 'vertexShadingLayers') {
        const problems = [];
        if (layers == null) return problems;
        if (!Array.isArray(layers)) return [`${where} must be a list`];
        layers.forEach((layer, index) => {
            const desc = `${where}[${index + 1}]`;
            if (!layer || typeof layer !== 'object' || Array.isArray(layer)) {
                problems.push(`${desc} must be an object`);
                return;
            }
            if (layer.type !== 'colorNoise') {
                problems.push(`${desc}.type '${String(layer.type)}' is unsupported (expected colorNoise)`);
                return;
            }
            rgbProblems(layer.colorA, `${desc}.colorA`, problems);
            rgbProblems(layer.colorB, `${desc}.colorB`, problems);
            if (!Number.isFinite(layer.strength) || layer.strength < 0 || layer.strength > 1) {
                problems.push(`${desc}.strength must be a number in 0..1`);
            }
            if (!Number.isFinite(layer.scale) || layer.scale <= 0) {
                problems.push(`${desc}.scale must be a number > 0`);
            }
            if (!Number.isSafeInteger(layer.seed) || Math.abs(layer.seed) > MAX_SEED) {
                problems.push(`${desc}.seed must be an integer between -${MAX_SEED} and ${MAX_SEED}`);
            }
        });
        return problems;
    }

    function compile(layers, where) {
        const problems = validate(layers, where);
        if (problems.length) throw new Error(problems.join('\n'));
        return (layers || []).map(layer => ({
            type: layer.type,
            colorA: layer.colorA.slice(0, 3),
            colorB: layer.colorB.slice(0, 3),
            strength: layer.strength,
            scale: layer.scale,
            seed: layer.seed
        }));
    }

    function sampleCompiled(compiled, x, y, target) {
        const out = target || [1, 1, 1];
        let r = 1, g = 1, b = 1;
        for (const layer of compiled || []) {
            const noise = fractalNoise(x / layer.scale, y / layer.scale, layer.seed);
            const nr = lerp(layer.colorA[0], layer.colorB[0], noise);
            const ng = lerp(layer.colorA[1], layer.colorB[1], noise);
            const nb = lerp(layer.colorA[2], layer.colorB[2], noise);
            r *= lerp(1, nr, layer.strength);
            g *= lerp(1, ng, layer.strength);
            b *= lerp(1, nb, layer.strength);
        }
        out[0] = r; out[1] = g; out[2] = b;
        return out;
    }

    function sample(layers, x, y, target) {
        return sampleCompiled(compile(layers), x, y, target);
    }

    return {
        hash01,
        valueNoise,
        fractalNoise,
        validate,
        compile,
        sample,
        sampleCompiled
    };
}));

// Environment-lighting authoring bootstrap. This deliberately performs only
// bounded DOM ownership work: no dynamic Three import, no prototype mutation,
// and no MutationObserver. The retired Paint/Blur UI stays out of the visible
// workflow while legacy map.light data remains readable by runtime/editor code.
(function installEnvironmentLightingAuthoring(root) {
    if (typeof window === 'undefined' || typeof document === 'undefined') return;

    function hide(element) {
        if (element) element.style.display = 'none';
    }

    function bridgeLampPropertyInputs(palette) {
        let proxy = document.getElementById('light-object-live-property-proxy');
        if (!proxy) {
            proxy = document.createElement('span');
            proxy.id = 'light-object-live-property-proxy';
            proxy.hidden = true;
            palette.appendChild(proxy);
        }
        ['lamp-color', 'lamp-radius', 'lamp-falloff', 'lamp-material'].forEach(id => {
            const input = document.getElementById(id);
            if (!input || input.dataset.thestraLiveLightingBridge === 'true') return;
            input.dataset.thestraLiveLightingBridge = 'true';
            input.addEventListener('input', () => {
                // map-editor's inline input handler has already mutated the
                // authored Lamp. Reuse the workspace's existing light-property
                // invalidation seam so Three relights on the next frame while
                // LÖVE authority catches up asynchronously. #493 will replace
                // this legacy-control bridge with the contextual Inspector.
                proxy.dispatchEvent(new Event('input', { bubbles: true }));
            });
        });
    }

    function reconcilePalette() {
        const palette = document.getElementById('light-palette-section');
        if (!palette) return false;

        const title = palette.querySelector('.sidebar-title');
        if (title) title.textContent = 'Environment Lighting';
        const intro = title && title.nextElementSibling;
        if (intro && intro.tagName === 'P') {
            intro.textContent = 'Author semantic lamp sources here. Vertex Shading adds environmental color variation independently of illumination.';
        }

        const lampRadio = palette.querySelector('input[name="light-tool"][value="object"]');
        if (lampRadio) {
            lampRadio.checked = true;
            hide(lampRadio.closest('.field-row-stacked'));
        }
        if (typeof root.setLightTool === 'function') root.setLightTool('object');

        hide(document.getElementById('light-color-row'));
        hide(document.getElementById('light-blur-hint'));
        const radius = document.getElementById('light-brush-radius');
        hide(radius && radius.closest('.field-row-stacked'));
        const reset = palette.querySelector('button[onclick*="clearMapLight"]');
        hide(reset);
        const bake = palette.querySelector('button[onclick*="bakeMapLighting"]');
        if (bake) bake.remove();
        bridgeLampPropertyInputs(palette);

        const lampHint = document.getElementById('light-object-hint');
        if (lampHint) {
            lampHint.style.display = 'block';
            lampHint.textContent = 'Click a cell to add/select a lamp, then use the 3D gizmo to move it. Lamps affect illumination and do not alter collision.';
        }
        if (!palette.querySelector('[data-thestra-lamp-heading]') && lampHint) {
            const heading = document.createElement('div');
            heading.className = 'sidebar-title';
            heading.dataset.thestraLampHeading = 'true';
            heading.style.marginTop = '6px';
            heading.textContent = 'Lamp Sources';
            lampHint.parentElement.insertBefore(heading, lampHint);
        }

        // The workspace script is loaded after this module, so give its
        // Vertex Shading panel a short bounded handoff window rather than
        // observing the whole document forever.
        const shading = document.getElementById('vertex-shading-section');
        if (shading && shading.parentElement !== palette) palette.appendChild(shading);
        return !!shading;
    }

    reconcilePalette();
    let attempts = 0;
    function finishPaletteOwnership() {
        if (reconcilePalette()) return;
        attempts += 1;
        if (attempts < 120) window.requestAnimationFrame(finishPaletteOwnership);
    }
    window.requestAnimationFrame(finishPaletteOwnership);
}(typeof self !== 'undefined' ? self : this));
