/*
 * Experimental shared semantic source. This file is intentionally NOT wired to
 * production runtime or Studio. It is compiled twice: ordinary JavaScript via
 * tsc, and LuaJIT-target Lua via TypeScriptToLua.
 */
namespace ThestraSharedSemantics {
    export type TokenValue = number | string;
    export interface TokenMap { [key: string]: TokenValue; }

    export interface ParsedSpriteKey {
        fileKey: string;
        tokens: TokenMap;
    }

    export interface SpriteTiming {
        fps: number | null;
        source: 'key' | 'filename' | 'default' | 'resolved';
        token: 'fps' | 'speed' | null;
        value: TokenValue | null;
    }

    export interface SpriteResolution {
        resolved: boolean;
        key: string;
        path: string | null;
        tokenSourcePath: string | null;
        keyTokens: TokenMap;
        filenameTokens: TokenMap;
        tokens: TokenMap;
        timing: SpriteTiming;
    }

    const ASSET_DIRS = [
        'assets/smallBattlers',
        'assets/sprites',
        'assets/system'
    ];

    function isAsciiWhitespace(code: number): boolean {
        return code === 32 || code === 9 || code === 10 || code === 11 || code === 12 || code === 13;
    }

    function trimAscii(value: string): string {
        let first = 0;
        let last = value.length;
        while (first < last && isAsciiWhitespace(value.charCodeAt(first))) first++;
        while (last > first && isAsciiWhitespace(value.charCodeAt(last - 1))) last--;
        return value.substring(first, last);
    }

    function tokenValue(raw: string): TokenValue {
        const trimmed = trimAscii(raw);
        if (trimmed.length === 0) return raw;
        const numeric = Number(trimmed);
        return Number.isFinite(numeric) ? numeric : raw;
    }

    function copyTokens(tokens: TokenMap): TokenMap {
        const result: TokenMap = {};
        for (const key in tokens) result[key] = tokens[key];
        return result;
    }

    export function parseSpriteKey(spriteKey: string): ParsedSpriteKey {
        const tokens: TokenMap = {};
        let fileKey = '';
        let cursor = 0;

        while (cursor < spriteKey.length) {
            const open = spriteKey.indexOf('[', cursor);
            if (open < 0) {
                fileKey += spriteKey.substring(cursor);
                break;
            }
            fileKey += spriteKey.substring(cursor, open);
            const equals = spriteKey.indexOf('=', open + 1);
            const close = equals >= 0 ? spriteKey.indexOf(']', equals + 1) : -1;
            if (equals > open + 1 && close > equals + 1) {
                const key = spriteKey.substring(open + 1, equals);
                const value = spriteKey.substring(equals + 1, close);
                tokens[key] = tokenValue(value);
                cursor = close + 1;
            } else {
                fileKey += '[';
                cursor = open + 1;
            }
        }

        return { fileKey: trimAscii(fileKey), tokens };
    }

    function mergedTokens(keyTokens: TokenMap, filenameTokens: TokenMap): TokenMap {
        const merged = copyTokens(filenameTokens);
        for (const key in keyTokens) merged[key] = keyTokens[key];
        return merged;
    }

    function numericToken(value: TokenValue): number | null {
        if (typeof value === 'number') return Number.isFinite(value) ? value : null;
        const trimmed = trimAscii(value);
        if (trimmed.length === 0) return null;
        const numeric = Number(trimmed);
        return Number.isFinite(numeric) ? numeric : null;
    }

    export function resolveTiming(keyTokens: TokenMap, filenameTokens: TokenMap): SpriteTiming {
        const merged = mergedTokens(keyTokens, filenameTokens);
        if (merged.fps !== undefined) {
            const value = merged.fps;
            const numeric = numericToken(value);
            return {
                fps: numeric,
                source: keyTokens.fps !== undefined ? 'key'
                    : (filenameTokens.fps !== undefined ? 'filename' : 'resolved'),
                token: 'fps',
                value
            };
        }
        if (merged.speed !== undefined) {
            const value = merged.speed;
            const numeric = numericToken(value);
            return {
                fps: numeric === null ? null : 4 * numeric,
                source: keyTokens.speed !== undefined ? 'key'
                    : (filenameTokens.speed !== undefined ? 'filename' : 'resolved'),
                token: 'speed',
                value
            };
        }
        return { fps: 4, source: 'default', token: null, value: null };
    }

    function containsPath(files: string[], path: string): boolean {
        for (let index = 0; index < files.length; index++) {
            if (files[index] === path) return true;
        }
        return false;
    }

    function basename(path: string): string {
        let slash = -1;
        for (let index = 0; index < path.length; index++) {
            const code = path.charCodeAt(index);
            if (code === 47 || code === 92) slash = index;
        }
        return path.substring(slash + 1);
    }

    function lower(value: string): string { return value.toLowerCase(); }

    function titleCaseFirst(value: string): string {
        if (value.length === 0) return value;
        return value.substring(0, 1).toUpperCase() + value.substring(1).toLowerCase();
    }

    function stripPng(filename: string): string {
        return lower(filename.substring(filename.length - 4)) === '.png'
            ? filename.substring(0, filename.length - 4)
            : filename;
    }

    function indexedFilename(files: string[], fileKey: string): { path: string; tokens: TokenMap } | null {
        const wanted = lower(fileKey);
        for (let dirIndex = 0; dirIndex < ASSET_DIRS.length; dirIndex++) {
            const dir = ASSET_DIRS[dirIndex];
            const prefix = dir + '/';
            for (let fileIndex = 0; fileIndex < files.length; fileIndex++) {
                const path = files[fileIndex];
                if (path.substring(0, prefix.length) !== prefix) continue;
                const localName = path.substring(prefix.length);
                if (localName.indexOf('/') >= 0 || lower(localName.substring(localName.length - 4)) !== '.png') continue;
                const parsed = parseSpriteKey(stripPng(localName));
                if (lower(parsed.fileKey) === wanted) return { path, tokens: parsed.tokens };
            }
        }
        return null;
    }

    export function resolveSpriteKey(spriteKey: string, files: string[]): SpriteResolution {
        const parsed = parseSpriteKey(spriteKey);
        const keyTokens = parsed.tokens;
        const directPaths = [
            'assets/smallBattlers/' + titleCaseFirst(parsed.fileKey) + '.png',
            'assets/smallBattlers/' + parsed.fileKey + '.png',
            'assets/smallBattlers/' + lower(parsed.fileKey) + '.png',
            'assets/sprites/' + parsed.fileKey + '.png',
            'assets/system/' + parsed.fileKey + '.png',
            'assets/system/' + titleCaseFirst(parsed.fileKey) + '.png'
        ];
        const indexed = indexedFilename(files, parsed.fileKey);
        const filenameTokens = indexed ? copyTokens(indexed.tokens) : {};
        const merged = mergedTokens(keyTokens, filenameTokens);

        let path: string | null = null;
        for (let index = 0; index < directPaths.length; index++) {
            if (containsPath(files, directPaths[index])) {
                path = directPaths[index];
                break;
            }
        }
        if (path === null && indexed) path = indexed.path;

        return {
            resolved: path !== null,
            key: spriteKey,
            path,
            tokenSourcePath: indexed ? indexed.path : null,
            keyTokens: copyTokens(keyTokens),
            filenameTokens,
            tokens: merged,
            timing: resolveTiming(keyTokens, filenameTokens)
        };
    }

    export function describeSpritePath(path: string): SpriteResolution {
        const parsed = parseSpriteKey(stripPng(basename(path)));
        const filenameTokens = parsed.tokens;
        return {
            resolved: true,
            key: '',
            path,
            tokenSourcePath: path,
            keyTokens: {},
            filenameTokens: copyTokens(filenameTokens),
            tokens: copyTokens(filenameTokens),
            timing: resolveTiming({}, filenameTokens)
        };
    }

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

    function validateRgb(problems: string[], value: number[], where: string): void {
        if (value == null || typeof value !== 'object' || value.length !== 3) {
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

    export function validate(layers: ShadingLayer[] | null | undefined, where = 'vertexShadingLayers'): string[] {
        const problems: string[] = [];
        if (layers == null) return problems;
        if (typeof layers !== 'object') {
            problems.push(where + ' must be a dense list');
            return problems;
        }
        for (let index = 0; index < layers.length; index++) {
            const layer = layers[index];
            const desc = where + '[' + (index + 1) + ']';
            if (layer == null || typeof layer !== 'object') {
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

    export function compile(layers: ShadingLayer[] | null | undefined, where = 'vertexShadingLayers'): ShadingLayer[] {
        const problems = validate(layers, where);
        if (problems.length > 0) throw new Error(problems.join('\n'));
        const compiled: ShadingLayer[] = [];
        if (layers == null) return compiled;
        for (let index = 0; index < layers.length; index++) {
            const layer = layers[index];
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

    export function sampleCompiled(compiled: ShadingLayer[] | null | undefined, x: number, y: number): number[] {
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
        return [r, g, b];
    }

    export function sample(layers: ShadingLayer[] | null | undefined, x: number, y: number): number[] {
        return sampleCompiled(compile(layers), x, y);
    }

    export function grid(layers: ShadingLayer[] | null | undefined, width: number, height: number): number[][][] {
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
