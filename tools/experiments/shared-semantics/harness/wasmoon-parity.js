'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { performance } = require('node:perf_hooks');
const { LuaFactory } = require('wasmoon');

function close(actual, expected, epsilon = 1e-12, label = '') {
    assert.ok(Math.abs(actual - expected) <= epsilon,
        `${label}: expected ${expected}, got ${actual}`);
}

function findWasmFiles(root, out = []) {
    if (!fs.existsSync(root)) return out;
    for (const entry of fs.readdirSync(root, { withFileTypes: true })) {
        const full = path.join(root, entry.name);
        if (entry.isDirectory()) findWasmFiles(full, out);
        else if (entry.name.endsWith('.wasm')) out.push(full);
    }
    return out;
}

(async () => {
    const sourcePath = path.join(__dirname, '..', 'lua', 'shared-semantics.lua');
    const source = fs.readFileSync(sourcePath, 'utf8');
    const createStarted = performance.now();
    const factory = new LuaFactory();
    const lua = await factory.createEngine();
    const engineCreateMs = performance.now() - createStarted;
    try {
        const loadStarted = performance.now();
        await lua.doString(`
SharedSemantics = (function()\n${source}\nend)()
function spike_hash(x, y, seed) return SharedSemantics.hash01(x, y, seed) end
function spike_value(x, y, seed) return SharedSemantics.valueNoise(x, y, seed) end
function spike_fractal(x, y, seed) return SharedSemantics.fractalNoise(x, y, seed) end
function spike_sample_channel(channel)
    local r, g, b = SharedSemantics.sample({{
        type = 'colorNoise', colorA = {0.88, 0.94, 0.90}, colorB = {0.96, 0.88, 0.93},
        strength = 0.12, scale = 5, seed = 1729
    }}, 2.5, 3.5)
    if channel == 1 then return r elseif channel == 2 then return g else return b end
end
function spike_sprite_fps(key)
    local result = SharedSemantics.resolveSpriteKey(key, {
        'assets/smallBattlers/Pixie[fps=15].png',
        'assets/system/Cursor.png'
    })
    return result.timing.fps
end
function spike_sprite_source(key)
    local result = SharedSemantics.resolveSpriteKey(key, {
        'assets/smallBattlers/Pixie[fps=15].png',
        'assets/system/Cursor.png'
    })
    return result.timing.source
end
function spike_batch_fractal(iterations)
    local started = os.clock()
    local sink = 0
    for i = 1, iterations do sink = sink + SharedSemantics.fractalNoise(1.25, 2.75, 1729) end
    return (os.clock() - started) * 1000 + sink * 0
end
`);
        const sourceLoadMs = performance.now() - loadStarted;

        const hash = lua.global.get('spike_hash');
        const value = lua.global.get('spike_value');
        const fractal = lua.global.get('spike_fractal');
        const sampleChannel = lua.global.get('spike_sample_channel');
        const spriteFps = lua.global.get('spike_sprite_fps');
        const spriteSource = lua.global.get('spike_sprite_source');
        const batchFractal = lua.global.get('spike_batch_fractal');

        close(hash(0, 0, 0), 0.9616300366300367, 1e-12, 'Wasmoon hash 0,0,0');
        close(hash(1, 2, 1729), 0.18543956043956045, 1e-12, 'Wasmoon hash 1,2,1729');
        close(hash(-1, 0, 23), 0.6313644688644688, 1e-12, 'Wasmoon hash -1,0,23');
        close(value(0.5, 0.5, 1729), 0.42679334554334547, 1e-12, 'Wasmoon value');
        close(fractal(0.5, 0.5, 1729), 0.4540415838459217, 1e-12, 'Wasmoon fractal .5');
        close(fractal(1.25, 2.75, 1729), 0.45447714242048237, 1e-12, 'Wasmoon fractal 1.25');
        close(fractal(-0.25, 0.5, 23), 0.3765472024340493, 1e-12, 'Wasmoon fractal negative');
        close(sampleChannel(1), 0.9897950411471678, 1e-12, 'Wasmoon sample r');
        close(sampleChannel(2), 0.9896537191396242, 1e-12, 'Wasmoon sample g');
        close(sampleChannel(3), 0.9895731404301878, 1e-12, 'Wasmoon sample b');

        assert.equal(spriteFps('pixie'), 15);
        assert.equal(spriteSource('pixie'), 'filename');
        assert.equal(spriteFps('pixie[fps=9]'), 9);
        assert.equal(spriteSource('pixie[fps=9]'), 'key');
        assert.equal(spriteFps('pixie[speed=2]'), 15);
        assert.equal(spriteSource('pixie[speed=2]'), 'filename');
        assert.equal(spriteFps('Cursor'), 4);
        assert.equal(spriteSource('Cursor'), 'default');

        const interopIterations = 5000;
        for (let i = 0; i < 100; i++) fractal(1.25, 2.75, 1729);
        const bridgeStarted = performance.now();
        for (let i = 0; i < interopIterations; i++) fractal(1.25, 2.75, 1729);
        const bridgeMs = performance.now() - bridgeStarted;
        const luaBatchMs = batchFractal(100000);

        const wasmoonRoot = path.dirname(require.resolve('wasmoon/package.json'));
        const wasmFiles = findWasmFiles(wasmoonRoot);
        const wasmBytes = wasmFiles.reduce((sum, filename) => sum + fs.statSync(filename).size, 0);
        const measurements = {
            node: process.version,
            lua_vm: await lua.doString('return _VERSION'),
            engine_create_ms: engineCreateMs,
            source_load_ms: sourceLoadMs,
            js_to_lua_fractal_5k_ms: bridgeMs,
            in_lua_fractal_100k_ms: luaBatchMs,
            wasmoon_wasm_files: wasmFiles.map(filename => path.relative(wasmoonRoot, filename)),
            wasmoon_wasm_bytes: wasmBytes,
            shared_lua_source_bytes: fs.statSync(sourcePath).size
        };
        console.log('WASMOON PARITY OK');
        console.log('MEASURE_WASMOON ' + JSON.stringify(measurements));
    } finally {
        lua.global.close();
    }
})().catch(error => {
    console.error(error && error.stack || error);
    process.exitCode = 1;
});
