(function (root, factory) {
    if (typeof module === 'object' && module.exports) module.exports = factory();
    else root.ThestraVertexShading = factory();
}(typeof self !== 'undefined' ? self : this, function () {
    'use strict';

    const MODULUS = 65521;
    const HASH_MULTIPLIER = 25173;
    const HASH_ADDEND = 13849;
    const MAX_SEED = 2147483646;

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
            const noise = valueNoise(x / layer.scale, y / layer.scale, layer.seed);
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
        validate,
        compile,
        sample,
        sampleCompiled
    };
}));
