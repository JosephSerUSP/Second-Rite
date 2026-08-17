'use strict';

const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { SpriteResolutionCache } = require('../sprite-resolution-cache');

function write(filePath, body) {
    fs.mkdirSync(path.dirname(filePath), { recursive: true });
    fs.writeFileSync(filePath, body);
}

function delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
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
        const gate = new Promise(resolve => { release = resolve; });
        const slowResolver = async spec => {
            calls += 1;
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
        await delay(5);
        assert.strictEqual(calls, 1, 'concurrent identical misses should launch one runtime resolver');
        release();
        const [coalescedA, coalescedB] = await Promise.all([pendingA, pendingB]);
        assert.strictEqual(coalescedA, coalescedB, 'coalesced callers should receive the same runtime payload');

        calls = 0;
        cache.clear();
        await cache.resolve({ key: 'pixie' }, runtimeResolver);
        await delay(5);
        write(pixiePath, 'pixels-v2-longer');
        await cache.resolve({ key: 'pixie' }, runtimeResolver);
        assert.strictEqual(calls, 2, 'resolved-file replacement should invalidate cached metadata');

        calls = 0;
        cache.clear();
        await cache.resolve({ key: 'pixie' }, runtimeResolver);
        write(path.join(temp, 'assets', 'sprites', 'pixie[speed=2].png'), 'other');
        await cache.resolve({ key: 'pixie' }, runtimeResolver);
        assert.strictEqual(calls, 2, 'lookup-directory inventory change should invalidate key metadata');

        calls = 0;
        cache.clear();
        await cache.resolve({ key: 'pixie' }, runtimeResolver);
        await delay(5);
        write(runtimeAuthority, '-- authority v2 changed\n');
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
        assert.strictEqual(errorCalls, 2, 'runtime errors must not be cached');

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

        console.log('sprite resolution cache: OK');
    } finally {
        fs.rmSync(temp, { recursive: true, force: true });
    }
}

main().catch(err => {
    console.error(err);
    process.exitCode = 1;
});
