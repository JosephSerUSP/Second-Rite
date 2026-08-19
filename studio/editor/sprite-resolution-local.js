'use strict';

// #794: resolve sprite metadata in Studio without asking LÖVE.
//
// This used to be a cold LÖVE subprocess per sprite -- ~3.5-4.8 s each -- to
// answer a question that is filename parsing. It had to ask because the rules
// lived only in `presentation/sprite_sheet.lua`.
//
// Both rule sets now come from the shared executable semantic leaves, which
// compile from one TypeScript source to the JavaScript required here AND to the
// Lua the runtime requires:
//
//   sprite-timing      -- what a resolved sprite's tokens mean
//   sprite-resolution  -- which file a key resolves to
//
// So this is not a Node reimplementation of the runtime resolver that has to be
// kept in step by hand. It is the same rules, executing in the other host, with
// only the inventory and the existence check supplied locally.

const fs = require('fs');
const path = require('path');
const spriteTiming = require('./js/generated/sprite-timing');
const spriteResolution = require('./js/generated/sprite-resolution');

function tokensToPayload(tokens) {
    // The runtime encodes an empty token table as a JSON array, because an
    // empty Lua table is ambiguous. Match that or the editor sees `{}` from one
    // host and `[]` from the other for the same sprite.
    const keys = Object.keys(tokens || {});
    if (keys.length === 0) return [];
    const out = {};
    for (const key of keys) out[key] = tokens[key];
    return out;
}

function tokenText(tokens) {
    const keys = Object.keys(tokens || {}).sort();
    if (keys.length === 0) return 'none';
    return keys.map(key => `${key}=${tokens[key]}`).join(', ');
}

function summaryFor(timing, keyTokens, filenameTokens) {
    let effective;
    if (timing.fps !== null && timing.fps !== undefined) {
        if (timing.source === 'default') {
            effective = 'Effective: 4 fps from the default';
        } else {
            effective = `Effective: ${timing.fps} fps from ${timing.source} [${timing.token}=${timing.value}]`;
        }
    } else {
        effective = `Effective timing is invalid: ${timing.source} [${timing.token}=${timing.value}]`;
    }
    return effective
        + '. Key tokens: ' + tokenText(keyTokens)
        + '. Filename tokens: ' + tokenText(filenameTokens)
        + '. Priority: fps > speed > default; key overrides filename for the same token.';
}

function describeResolved(spriteKey, resolved) {
    const timing = spriteTiming.resolveTiming(resolved.keyTokens, resolved.filenameTokens, resolved.tokens);
    return {
        key: spriteKey,
        resolved: true,
        path: resolved.path,
        tokenSourcePath: resolved.filenameTokenPath,
        keyTokens: tokensToPayload(resolved.keyTokens),
        filenameTokens: tokensToPayload(resolved.filenameTokens),
        tokens: tokensToPayload(resolved.tokens),
        timing: timing,
        summary: summaryFor(timing, resolved.keyTokens, resolved.filenameTokens),
    };
}

function createLocalSpriteResolver(options) {
    options = options || {};
    const projectRoot = options.projectRoot && path.resolve(options.projectRoot);
    if (!projectRoot) throw new Error('projectRoot is required');
    const fsImpl = options.fs || fs;

    const within = relative => path.resolve(projectRoot, ...relative.split('/'));

    // Rebuilt per request. The endpoint's own cache already owns invalidation,
    // and a listing of three directories costs microseconds -- caching it here
    // too would add a second staleness question for no measurable gain.
    function inventory() {
        const entries = [];
        for (const dir of spriteResolution.ASSET_DIRS) {
            let names;
            try {
                names = fsImpl.readdirSync(within(dir));
            } catch (e) {
                continue;
            }
            // LÖVE's getDirectoryItems order is the filesystem's; Node's
            // readdirSync is too. Sort so first-match-wins is decided by a
            // stable rule on both hosts rather than by directory layout.
            names.sort((a, b) => (a < b ? -1 : a > b ? 1 : 0));
            for (const name of names) entries.push({ dir: dir, name: name });
        }
        return entries;
    }

    function fileKeyOf(stem) {
        return spriteTiming.parseKey(stem).fileKey;
    }

    function resolveFile(spriteKey) {
        if (!spriteKey) return null;
        const parsed = spriteTiming.parseKey(String(spriteKey));
        const fileKey = parsed.fileKey;
        const keyTokens = parsed.tokens;

        const index = spriteResolution.buildFileIndex(inventory(), fileKeyOf);
        const indexed = spriteResolution.indexedFor(fileKey, index);

        let filenameTokens = {};
        let filenameTokenPath = null;
        let tokens = keyTokens;
        if (indexed) {
            filenameTokens = spriteTiming.parseKey(indexed.stem).tokens;
            filenameTokenPath = indexed.path;
            tokens = spriteTiming.mergeTokens(filenameTokens, keyTokens);
        }

        for (const candidate of spriteResolution.probeOrder(fileKey, index)) {
            let stat = null;
            try { stat = fsImpl.statSync(within(candidate)); } catch (e) { stat = null; }
            if (stat && stat.isFile()) {
                return {
                    path: candidate,
                    tokens: tokens,
                    keyTokens: keyTokens,
                    filenameTokens: filenameTokens,
                    filenameTokenPath: filenameTokenPath,
                };
            }
        }
        return null;
    }

    function describe(spriteKey) {
        if (!spriteKey) return { key: spriteKey, resolved: false, summary: 'No sprite key selected.' };
        const resolved = resolveFile(spriteKey);
        if (!resolved) {
            return { key: spriteKey, resolved: false, summary: 'Unresolved sprite key: ' + String(spriteKey) };
        }
        return describeResolved(spriteKey, resolved);
    }

    function describePath(spritePath) {
        if (!spritePath) return { path: spritePath, resolved: false, summary: 'No sprite file selected.' };
        const filename = String(spritePath).split(/[/\\]/).pop() || String(spritePath);
        const stem = filename.replace(/\.png$/i, '');
        const filenameTokens = spriteTiming.parseKey(stem).tokens;
        return describeResolved(null, {
            path: spritePath,
            tokens: filenameTokens,
            keyTokens: {},
            filenameTokens: filenameTokens,
            filenameTokenPath: spritePath,
        });
    }

    // Same shape the LÖVE resolver presented, so the endpoint and its cache do
    // not learn which host answered.
    return function resolve(spec) {
        if (!spec || typeof spec !== 'object') throw new Error('sprite metadata request must be an object');
        if (spec.key !== undefined && spec.key !== null) return Promise.resolve(describe(spec.key));
        if (spec.path !== undefined && spec.path !== null) return Promise.resolve(describePath(spec.path));
        throw new Error('sprite metadata request must name key or path');
    };
}

module.exports = {
    createLocalSpriteResolver,
    describeResolved,
};
