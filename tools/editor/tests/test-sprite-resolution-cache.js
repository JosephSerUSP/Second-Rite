'use strict';

const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { SpriteResolutionCache, requestKey } = require('../sprite-resolution-cache');

function write(filePath, body) {
    fs.mkdirSync(path.dirname(filePath), { recursive: true });
    fs.writeFileSync(filePath, body);
}

async function main() {
    const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'thestra-sprite-meta-cache-'));
    try {
        for (const dir of ['assets/smallBattlers', 'assets/sprites', 'assets/system']) {
            fs.mkdirSync(path.join(temp, ...dir.split('/')), { recursive: true });
        }
        const runtimeAuthority = path.join(temp, 'presentation', 'sprite_sheet.lua');
        write(runtimeAuthority, '-- authority v1\n');
        const pixiePath = path.join(temp, 'assets', 'smallBattlers', 'pixie[fps=15].png');
        write(pixiePath, 'pixels-v1');

        const cache = new SpriteResolutionCache({
            projectRoot: temp,
            runtimeAuthorityPath: runtimeAuthority,
        });

        assert.notStrictEqual(
            requestKey({ key: 'assets/sprites/pixie.png' }),
            requestKey({ path: 'assets/sprites/pixie.png' }),
            'authored key and direct path requests must have distinct cache identities'
        );
        assert.strictEqual(
            requestKey({ path: 'assets\\sprites\\pixie.png' }),
            requestKey({ path: 'assets/sprites/pixie.png' }),
            'direct paths should normalize path separators'
        );
        assert.strictEqual(
            cache.resolvedFileToken({ path: '../outside.png' }),
            'outside-project',
            'runtime payload paths must never make cache validation leave the Project root'
        );
        let outsideCalls = 0;
        const outsideResolver = async () => {
            outsideCalls += 1;
            return { resolved: true, path: '../outside.png', summary: 'invalid runtime path' };
        };
        await cache.resolve({ key: 'outside' }, outsideResolver);
        await cache.resolve({ key: 'outside' }, outsideResolver);
        assert.strictEqual(outsideCalls, 2, 'out-of-Project runtime paths must never become reusable cache entries');

        let calls = 0;
        const runtimeResolver = async spec => {
            calls += 1;
            return {
                key: spec.key,
                resolved: true,
                path: 'assets/smallBattlers/pixie[fps=15].png',
                timing: { fps: 15, source: 'filename', token: 'fps', value: 15 },
                summary: 'runtime answer ' + calls,
            };
        };

        const first = await cache.resolve({ key: 'pixie' }, runtimeResolver);
        const second = await cache.resolve({ key: 'pixie' }, runtimeResolver);
        assert.strictEqual(calls, 1, 'repeated identical lookup should reuse the runtime answer');
        assert.strictEqual(second, first, 'cache should preserve the exact runtime payload object');

        cache.clear();
        calls = 0;
        let release;
        let markStarted;
        const gate = new Promise(resolve => { release = resolve; });
        const started = new Promise(resolve => { markStarted = resolve; });
        const slowResolver = async spec => {
            calls += 1;
            markStarted();
            await gate;
            return {
                key: spec.key,
                resolved: true,
                path: 'assets/smallBattlers/pixie[fps=15].png',
                summary: 'coalesced',
            };
        };
        const pendingA = cache.resolve({ key: 'pixie' }, slowResolver);
        const pendingB = cache.resolve({ key: 'pixie' }, slowResolver);
        await started;
        assert.strictEqual(calls, 1, 'concurrent identical misses should launch one runtime resolver');
        release();
        const [coalescedA, coalescedB] = await Promise.all([pendingA, pendingB]);
        assert.strictEqual(coalescedA, coalescedB, 'coalesced callers should receive the same runtime payload');

        calls = 0;
        cache.clear();
        await cache.resolve({ key: 'pixie' }, runtimeResolver);
        write(pixiePath, 'pixels-v2-longer');
        await cache.resolve({ key: 'pixie' }, runtimeResolver);
        assert.strictEqual(calls, 2, 'resolved-file replacement should invalidate cached metadata');

        calls = 0;
        cache.clear();
        await cache.resolve({ key: 'pixie' }, runtimeResolver);
        const alternatePath = path.join(temp, 'assets', 'sprites', 'pixie[speed=2].png');
        write(alternatePath, 'other');
        await cache.resolve({ key: 'pixie' }, runtimeResolver);
        assert.strictEqual(calls, 2, 'lookup-directory inventory addition should invalidate key metadata');
        const renamedAlternatePath = alternatePath.replace('pixie[speed=2]', 'pixie[speed=3]');
        fs.renameSync(alternatePath, renamedAlternatePath);
        await cache.resolve({ key: 'pixie' }, runtimeResolver);
        assert.strictEqual(calls, 3, 'lookup-directory rename should invalidate key metadata');
        fs.rmSync(renamedAlternatePath);
        await cache.resolve({ key: 'pixie' }, runtimeResolver);
        assert.strictEqual(calls, 4, 'lookup-directory removal should invalidate key metadata');

        calls = 0;
        cache.clear();
        await cache.resolve({ key: 'pixie' }, runtimeResolver);
        write(runtimeAuthority, '-- authority v2 changed and longer\n');
        await cache.resolve({ key: 'pixie' }, runtimeResolver);
        assert.strictEqual(calls, 2, 'runtime authority change should invalidate cached metadata');

        cache.clear();
        let errorCalls = 0;
        const errorResolver = async () => {
            errorCalls += 1;
            return { error: 'runtime failed' };
        };
        await cache.resolve({ key: 'pixie' }, errorResolver);
        await cache.resolve({ key: 'pixie' }, errorResolver);
        assert.strictEqual(errorCalls, 2, 'runtime error payloads must not be cached');

        cache.clear();
        let rejectedCalls = 0;
        const rejectedResolver = async () => {
            rejectedCalls += 1;
            throw new Error('transport failed');
        };
        await assert.rejects(cache.resolve({ key: 'pixie' }, rejectedResolver), /transport failed/);
        await assert.rejects(cache.resolve({ key: 'pixie' }, rejectedResolver), /transport failed/);
        assert.strictEqual(rejectedCalls, 2, 'runtime transport failures must remain retryable');

        cache.clear();
        let missingCalls = 0;
        const missingResolver = async spec => {
            missingCalls += 1;
            return { key: spec.key, resolved: false, summary: 'Unresolved sprite key' };
        };
        await cache.resolve({ key: 'missing' }, missingResolver);
        await cache.resolve({ key: 'missing' }, missingResolver);
        assert.strictEqual(missingCalls, 1, 'authoritative unresolved answers should be amortized');
        write(path.join(temp, 'assets', 'system', 'missing.png'), 'new');
        await cache.resolve({ key: 'missing' }, missingResolver);
        assert.strictEqual(missingCalls, 2, 'new asset should invalidate a cached unresolved answer');

        cache.clear();
        calls = 0;
        await cache.resolve({ key: 'pixie' }, runtimeResolver);
        await cache.resolve({ path: 'assets/smallBattlers/pixie[fps=15].png' }, runtimeResolver);
        assert.strictEqual(calls, 2, 'key and direct-path lookups must not alias in the cache');

        cache.clear();
        let raceCalls = 0;
        let releaseRace;
        let markRaceStarted;
        const raceGate = new Promise(resolve => { releaseRace = resolve; });
        const raceStarted = new Promise(resolve => { markRaceStarted = resolve; });
        const raceResolver = async () => {
            raceCalls += 1;
            if (raceCalls === 1) {
                markRaceStarted();
                await raceGate;
            }
            return {
                resolved: true,
                path: 'assets/smallBattlers/pixie[fps=15].png',
                summary: 'race answer ' + raceCalls,
            };
        };
        const racing = cache.resolve({ key: 'pixie' }, raceResolver);
        await raceStarted;
        write(pixiePath, 'pixels-mutated-during-runtime-call-and-longer');
        releaseRace();
        await racing;
        await cache.resolve({ key: 'pixie' }, raceResolver);
        assert.strictEqual(raceCalls, 2,
            'same-name file mutation during an in-flight miss must not install a stale reusable answer');

        cache.clear();
        let clearCalls = 0;
        let releaseClear;
        let markClearStarted;
        const clearGate = new Promise(resolve => { releaseClear = resolve; });
        const clearStarted = new Promise(resolve => { markClearStarted = resolve; });
        const clearResolver = async () => {
            clearCalls += 1;
            if (clearCalls === 1) {
                markClearStarted();
                await clearGate;
            }
            return {
                resolved: true,
                path: 'assets/smallBattlers/pixie[fps=15].png',
                summary: 'clear answer ' + clearCalls,
            };
        };
        const beforeClear = cache.resolve({ key: 'pixie' }, clearResolver);
        await clearStarted;
        cache.clear();
        releaseClear();
        await beforeClear;
        await cache.resolve({ key: 'pixie' }, clearResolver);
        assert.strictEqual(clearCalls, 2, 'clear must prevent older in-flight work from repopulating the cache');

        console.log('sprite resolution cache: OK');
    } finally {
        fs.rmSync(temp, { recursive: true, force: true });
    }
}

main().catch(err => {
    console.error(err);
    process.exitCode = 1;
});
