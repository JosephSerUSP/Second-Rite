"use strict";
/*
 * Shared executable semantic authority for sprite timing tokens.
 *
 * Filesystem/resource discovery is intentionally excluded. Hosts provide the
 * key-token and filename-token inputs they resolved; this module owns parsing,
 * same-token override, fps-vs-speed precedence, speed conversion, and default.
 */
var ThestraSpriteTimingSemantics;
(function (ThestraSpriteTimingSemantics) {
    function isAsciiWhitespace(code) {
        return code === 32 || code === 9 || code === 10 || code === 11 || code === 12 || code === 13;
    }
    function trimAscii(value) {
        let first = 0;
        let last = value.length;
        while (first < last && isAsciiWhitespace(value.charCodeAt(first)))
            first++;
        while (last > first && isAsciiWhitespace(value.charCodeAt(last - 1)))
            last--;
        return value.substring(first, last);
    }
    // JavaScript Number(...) accepts 0b/0o spellings that LuaJIT tonumber(...)
    // does not, while signed hexadecimal support also differs by host. Keep the
    // historical unsigned 0x form but reject those host-divergent prefixes
    // before either generated target reaches its native numeric conversion.
    function hasUnsupportedNumericPrefix(value) {
        if (value.length < 2)
            return false;
        let first = 0;
        const leading = value.charCodeAt(0);
        if (leading === 43 || leading === 45)
            first = 1; // + / -
        if (first + 1 >= value.length || value.charCodeAt(first) !== 48)
            return false;
        const prefix = value.charCodeAt(first + 1);
        if (prefix === 98 || prefix === 66 || prefix === 111 || prefix === 79)
            return true; // b/B/o/O
        return first > 0 && (prefix === 120 || prefix === 88); // signed x/X
    }
    // Lua's authored contract is `tonumber(v) or v`. Number(...) plus the
    // explicit empty/non-finite and host-divergent-prefix guards keeps the
    // generated JS and Lua targets on one deliberate numeric-token subset
    // instead of inheriting parseFloat prefix parsing or host truthiness.
    function tokenValue(raw) {
        const trimmed = trimAscii(raw);
        if (trimmed.length === 0 || hasUnsupportedNumericPrefix(trimmed))
            return raw;
        const numeric = Number(trimmed);
        return Number.isFinite(numeric) ? numeric : raw;
    }
    function numericToken(value) {
        if (typeof value === 'number')
            return Number.isFinite(value) ? value : null;
        const trimmed = trimAscii(value);
        if (trimmed.length === 0 || hasUnsupportedNumericPrefix(trimmed))
            return null;
        const numeric = Number(trimmed);
        return Number.isFinite(numeric) ? numeric : null;
    }
    function copyTokens(tokens) {
        const result = {};
        if (tokens == null)
            return result;
        for (const key in tokens)
            result[key] = tokens[key];
        return result;
    }
    ThestraSpriteTimingSemantics.copyTokens = copyTokens;
    // Match presentation/sprite_sheet.lua's historical token grammar: every
    // complete [key=value] token is removed from the lookup key and the last
    // occurrence of a repeated key wins.
    function parseKey(spriteKey) {
        const tokens = {};
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
            }
            else {
                fileKey += '[';
                cursor = open + 1;
            }
        }
        return { fileKey: trimAscii(fileKey), tokens };
    }
    ThestraSpriteTimingSemantics.parseKey = parseKey;
    // Filename values are defaults; an authored key replaces the same token.
    function mergeTokens(filenameTokens, keyTokens) {
        const merged = copyTokens(filenameTokens);
        if (keyTokens != null) {
            for (const key in keyTokens)
                merged[key] = keyTokens[key];
        }
        return merged;
    }
    ThestraSpriteTimingSemantics.mergeTokens = mergeTokens;
    function resolveTiming(keyTokens, filenameTokens) {
        const key = keyTokens || {};
        const filename = filenameTokens || {};
        const merged = mergeTokens(filename, key);
        if (merged.fps !== undefined) {
            const value = merged.fps;
            return {
                fps: numericToken(value),
                source: key.fps !== undefined ? 'key'
                    : (filename.fps !== undefined ? 'filename' : 'resolved'),
                token: 'fps',
                value
            };
        }
        if (merged.speed !== undefined) {
            const value = merged.speed;
            const numeric = numericToken(value);
            return {
                fps: numeric === null ? null : 4 * numeric,
                source: key.speed !== undefined ? 'key'
                    : (filename.speed !== undefined ? 'filename' : 'resolved'),
                token: 'speed',
                value
            };
        }
        return { fps: 4, source: 'default', token: null, value: null };
    }
    ThestraSpriteTimingSemantics.resolveTiming = resolveTiming;
    function effectiveFps(tokens) {
        const merged = tokens || {};
        if (merged.fps !== undefined)
            return numericToken(merged.fps);
        if (merged.speed !== undefined) {
            const numeric = numericToken(merged.speed);
            return numeric === null ? null : 4 * numeric;
        }
        return 4;
    }
    ThestraSpriteTimingSemantics.effectiveFps = effectiveFps;
})(ThestraSpriteTimingSemantics || (ThestraSpriteTimingSemantics = {}));
// THES_SHARED_COMMONJS_SPRITE_TIMING: generated host adapter; do not edit.
if (typeof module === 'object' && module.exports) module.exports = ThestraSpriteTimingSemantics;