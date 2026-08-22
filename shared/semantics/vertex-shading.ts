/*
 * Shared executable semantic authority for renderer-neutral vertex shading.
 *
 * This source is compiled mechanically to ordinary JavaScript for Studio and
 * ordinary LuaJIT-target Lua for the runtime. Keep it host-neutral: no DOM,
 * Node, filesystem, LÖVE, renderer, or mutable game-state APIs belong here.
 */
namespace ThestraVertexShadingSemantics {
    const MODULUS = 65521;
    const HASH_MULTIPLIER = 25173;
    const HASH_ADDEND = 13849;
    const MAX_SEED = 2147483646;
    const FRACTAL_PERSISTENCE = 0.55;
    const FRACTAL_OCTAVES = [
        [0.8, -0.6, 0.6, 0.8, 3.17, -5.29],
        [0.6, 0.8, -0.8, 0.6, 17.17, -9.31],
        [-0.8, 0.6, -0.6, -0.8, -13.73, 21.47],
        [-0.6, -0.8, 0.8, -0.6, 29.11, 14.53]
    ];

    export interface ShadingLayer {
        type: string;
        colorA: number[];
        colorB: number[];
        strength: number;
        scale: number;
        seed: number;
    }

    function positiveModulo(value: number, modulus: number): number {
        const result = value % modulus;
        return result < 0 ? result + modulus : result;
    }

    function lerp(a: number, b: number, t: number): number {
        return a + (b - a) * t;
    }

    function smoothstep(t: number): number {
        return t * t * (3 - 2 * t);
    }

    // Products deliberately stay far below 2^53 so LuaJIT and JavaScript use
    // the same IEEE-double arithmetic for the numerical contract.
    export function hash01(x: number, y: number, seed: number): number {
        const ix = positiveModulo(Math.floor(x), MODULUS);
        const iy = positiveModulo(Math.floor(y), MODULUS);
        const iseed = positiveModulo(Math.floor(seed || 0), MODULUS);
        let value = (ix * 3749 + iy * 9151 + iseed * 1013) % MODULUS;
        value = (value * HASH_MULTIPLIER + HASH_ADDEND) % MODULUS;
        value = (value * HASH_MULTIPLIER + HASH_ADDEND) % MODULUS;
        return value / (MODULUS - 1);
    }

    export function valueNoise(x: number, y: number, seed: number): number {
        const x0 = Math.floor(x);
        const y0 = Math.floor(y);
        const fx = x - x0;
        const fy = y - y0;
        const sx = smoothstep(fx);
        const sy = smoothstep(fy);
        const top = lerp(hash01(x0, y0, seed), hash01(x0 + 1, y0, seed), sx);
        const bottom = lerp(hash01(x0, y0 + 1, seed), hash01(x0 + 1, y0 + 1, seed), sx);
        return lerp(top, bottom, sy);
    }

    export function fractalNoise(x: number, y: number, seed: number): number {
        let total = 0;
        let amplitude = 1;
        let normalizer = 0;
        let frequency = 1;
        for (let octaveIndex = 0; octaveIndex < FRACTAL_OCTAVES.length; octaveIndex++) {
            const octave = FRACTAL_OCTAVES[octaveIndex];
            const rotatedX = (x * octave[0] + y * octave[1] + octave[4]) * frequency;
            const rotatedY = (x * octave[2] + y * octave[3] + octave[5]) * frequency;
            total += valueNoise(rotatedX, rotatedY, seed + octaveIndex * 7919) * amplitude;
            normalizer += amplitude;
            amplitude *= FRACTAL_PERSISTENCE;
            frequency *= 2;
        }
        return total / normalizer;
    }

    function validateRgb(problems: string[], value: unknown, where: string): void {
        if (!Array.isArray(value) || value.length !== 3) {
            problems.push(where + ' must be an RGB triple');
            return;
        }
        for (let channel = 0; channel < 3; channel++) {
            const sample = value[channel];
            if (typeof sample !== 'number' || !Number.isFinite(sample) || sample < 0 || sample > 1) {
                problems.push(where + ' channel ' + (channel + 1) + ' must be a number in 0..1');
            }
        }
    }

    export function validate(layers: unknown, where = 'vertexShadingLayers'): string[] {
        const problems: string[] = [];
        if (layers == null) return problems;
        if (!Array.isArray(layers)) {
            problems.push(where + ' must be a dense list');
            return problems;
        }
        for (let index = 0; index < layers.length; index++) {
            const layer = layers[index] as ShadingLayer | null;
            const desc = where + '[' + (index + 1) + ']';
            if (layer == null || typeof layer !== 'object' || Array.isArray(layer)) {
                problems.push(desc + ' must be an object');
            } else if (layer.type !== 'colorNoise') {
                problems.push(desc + ".type '" + String(layer.type) + "' is unsupported (expected colorNoise)");
            } else {
                validateRgb(problems, layer.colorA, desc + '.colorA');
                validateRgb(problems, layer.colorB, desc + '.colorB');
                if (typeof layer.strength !== 'number' || !Number.isFinite(layer.strength)
                        || layer.strength < 0 || layer.strength > 1) {
                    problems.push(desc + '.strength must be a number in 0..1');
                }
                if (typeof layer.scale !== 'number' || !Number.isFinite(layer.scale) || layer.scale <= 0) {
                    problems.push(desc + '.scale must be a number > 0');
                }
                if (typeof layer.seed !== 'number' || !Number.isFinite(layer.seed)
                        || Math.floor(layer.seed) !== layer.seed || Math.abs(layer.seed) > MAX_SEED) {
                    problems.push(desc + '.seed must be an integer between -' + MAX_SEED + ' and ' + MAX_SEED);
                }
            }
        }
        return problems;
    }

    export function compile(layers: unknown, where = 'vertexShadingLayers'): ShadingLayer[] {
        const problems = validate(layers, where);
        if (problems.length > 0) throw new Error(problems.join('\n'));
        const source = (layers || []) as ShadingLayer[];
        const compiled: ShadingLayer[] = [];
        for (let index = 0; index < source.length; index++) {
            const layer = source[index];
            compiled.push({
                type: layer.type,
                colorA: [layer.colorA[0], layer.colorA[1], layer.colorA[2]],
                colorB: [layer.colorB[0], layer.colorB[1], layer.colorB[2]],
                strength: layer.strength,
                scale: layer.scale,
                seed: layer.seed
            });
        }
        return compiled;
    }

    export function sampleCompiled(compiled: ShadingLayer[] | null | undefined,
            x: number, y: number, target?: number[]): number[] {
        const out = target || [1, 1, 1];
        let r = 1;
        let g = 1;
        let b = 1;
        if (compiled != null) {
            for (let index = 0; index < compiled.length; index++) {
                const layer = compiled[index];
                const noise = fractalNoise(x / layer.scale, y / layer.scale, layer.seed);
                const nr = lerp(layer.colorA[0], layer.colorB[0], noise);
                const ng = lerp(layer.colorA[1], layer.colorB[1], noise);
                const nb = lerp(layer.colorA[2], layer.colorB[2], noise);
                r *= lerp(1, nr, layer.strength);
                g *= lerp(1, ng, layer.strength);
                b *= lerp(1, nb, layer.strength);
            }
        }
        out[0] = r;
        out[1] = g;
        out[2] = b;
        return out;
    }

    export function sample(layers: unknown, x: number, y: number, target?: number[]): number[] {
        return sampleCompiled(compile(layers), x, y, target);
    }

    export function grid(layers: unknown, width: number, height: number): number[][][] {
        const compiled = compile(layers);
        const result: number[][][] = [];
        for (let y = 0; y <= height; y++) {
            const row: number[][] = [];
            for (let x = 0; x <= width; x++) row.push(sampleCompiled(compiled, x, y));
            result.push(row);
        }
        return result;
    }
}
