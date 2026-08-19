'use strict';

const assert = require('node:assert/strict');
const { performance } = require('node:perf_hooks');

const loadStarted = performance.now();
const Vertex = require('../../studio/editor/js/generated/vertex-shading.js');
const SpriteTiming = require('../../studio/editor/js/generated/sprite-timing.js');
const generatedLoadMs = performance.now() - loadStarted;
const VertexStudioAdapter = require('../../studio/editor/js/vertex-shading.js');

const EPSILON = 1e-12;
function close(actual, expected, label, epsilon = EPSILON) {
    assert.ok(Math.abs(actual - expected) <= epsilon,
        `${label}: expected ${expected}, got ${actual}`);
}

// The Studio compatibility surface is only a host adapter now, not another
// implementation. Node and the browser receive the same generated namespace.
assert.strictEqual(VertexStudioAdapter, Vertex);

// Existing runtime/Studio numerical contract, unchanged by the authority move.
close(Vertex.hash01(0, 0, 0), 0.9616300366300367, 'hash 0,0,0');
close(Vertex.hash01(1, 2, 1729), 0.18543956043956045, 'hash 1,2,1729');
close(Vertex.hash01(-1, 0, 23), 0.6313644688644688, 'hash -1,0,23');
close(Vertex.valueNoise(0.5, 0.5, 1729), 0.42679334554334547, 'value noise .5,.5');
close(Vertex.fractalNoise(0.5, 0.5, 1729), 0.4540415838459217, 'fractal .5,.5');
close(Vertex.fractalNoise(1.25, 2.75, 1729), 0.45447714242048237, 'fractal 1.25,2.75');
close(Vertex.fractalNoise(-0.25, 0.5, 23), 0.3765472024340493, 'fractal -.25,.5');

const layer = {
    type: 'colorNoise',
    colorA: [0.8, 0.85, 0.9],
    colorB: [1, 0.95, 0.85],
    strength: 0.5,
    scale: 8,
    seed: 1729,
};
const rgb = Vertex.sample([layer], 3, 4);
close(rgb[0], 0.950024025251864, 'sample r');
close(rgb[1], 0.9500120126259319, 'sample g');
close(rgb[2], 0.937493993687034, 'sample b');

// Boundary/fuzz-style deterministic sweep. The test-side Park-Miller sequence
// stays below IEEE-754's exact-integer limit in both JS and LuaJIT. The checksum
// pins 2,048 independent coordinates/seeds without adding another algorithm.
let state = 1729;
let checksum = 0;
let minimum = 1;
let maximum = 0;
for (let index = 0; index < 2048; index++) {
    state = (state * 48271) % 2147483647;
    const x = (state / 2147483647) * 2048 - 1024;
    state = (state * 48271) % 2147483647;
    const y = (state / 2147483647) * 2048 - 1024;
    state = (state * 48271) % 2147483647;
    const seed = Math.floor((state / 2147483647) * 4294967292) - 2147483646;
    const value = Vertex.fractalNoise(x, y, seed);
    checksum += value * (index + 1);
    minimum = Math.min(minimum, value);
    maximum = Math.max(maximum, value);
}
close(checksum, 1048868.5265851377, '2048-point shading checksum', 1e-7);
close(minimum, 0.11815460869851695, '2048-point minimum');
close(maximum, 0.8671328344589253, '2048-point maximum');

assert.deepEqual(Vertex.validate(null), []);
assert.deepEqual(Vertex.validate([{ type: 'wat' }]), [
    "vertexShadingLayers[1].type 'wat' is unsupported (expected colorNoise)"
]);
assert.throws(() => Vertex.compile([{ type: 'colorNoise', colorA: [1, 1], colorB: [1, 1, 1], strength: 1, scale: 1, seed: 0 }]),
    /colorA must be an RGB triple/);
assert.throws(() => Vertex.compile([{ type: 'colorNoise', colorA: [1, 1, 1], colorB: [1, 1, 1], strength: 1, scale: 0, seed: 0 }]),
    /scale must be a number > 0/);

// Sprite timing grammar. These pin same-token override, global fps priority,
// speed conversion, default rate, repeated tokens, zero, malformed tokens, and
// numeric spellings where JavaScript Number and LuaJIT tonumber can diverge.
assert.deepEqual(SpriteTiming.parseKey(' Pixie[fps=15] '), {
    fileKey: 'Pixie', tokens: { fps: 15 }
});
assert.deepEqual(SpriteTiming.parseKey('pixie[fps=9][fps=12]'), {
    fileKey: 'pixie', tokens: { fps: 12 }
});
assert.equal(SpriteTiming.effectiveFps(SpriteTiming.parseKey('pixie[speed=2]').tokens), 8);
assert.equal(SpriteTiming.effectiveFps(SpriteTiming.parseKey('Cursor').tokens), 4);
assert.equal(SpriteTiming.effectiveFps(SpriteTiming.parseKey('x[fps=0]').tokens), 0);
assert.equal(SpriteTiming.effectiveFps(SpriteTiming.parseKey('x[speed=0]').tokens), 0);
assert.equal(SpriteTiming.effectiveFps(SpriteTiming.parseKey('x[fps=0x10]').tokens), 16);
assert.equal(SpriteTiming.effectiveFps(SpriteTiming.parseKey('x[fps=+1.5]').tokens), 1.5);
assert.equal(SpriteTiming.effectiveFps(SpriteTiming.parseKey('x[fps=-2.5]').tokens), -2.5);
assert.equal(SpriteTiming.effectiveFps(SpriteTiming.parseKey('x[fps=.5]').tokens), 0.5);
assert.equal(SpriteTiming.effectiveFps(SpriteTiming.parseKey('x[fps=1e2]').tokens), 100);
assert.equal(SpriteTiming.effectiveFps(SpriteTiming.parseKey('x[fps= \t12.5 ]').tokens), 12.5);
assert.equal(SpriteTiming.effectiveFps(SpriteTiming.parseKey('x[fps=0b10]').tokens), null);
assert.equal(SpriteTiming.effectiveFps(SpriteTiming.parseKey('x[fps=0o10]').tokens), null);
assert.equal(SpriteTiming.effectiveFps(SpriteTiming.parseKey('x[fps=-0x10]').tokens), null);
assert.equal(SpriteTiming.effectiveFps(SpriteTiming.parseKey('x[fps=Infinity]').tokens), null);
assert.equal(SpriteTiming.effectiveFps(SpriteTiming.parseKey('x[fps=15oops]').tokens), null);
assert.deepEqual(SpriteTiming.parseKey('x[a=b=c]'), { fileKey: 'x', tokens: { a: 'b=c' } });
assert.deepEqual(SpriteTiming.parseKey('x[=2]'), { fileKey: 'x[=2]', tokens: {} });
assert.deepEqual(SpriteTiming.parseKey('x[a=]'), { fileKey: 'x[a=]', tokens: {} });

assert.deepEqual(SpriteTiming.resolveTiming({ fps: 9 }, { fps: 15 }),
    { fps: 9, source: 'key', token: 'fps', value: 9 });
assert.deepEqual(SpriteTiming.resolveTiming({ speed: 2 }, { fps: 15 }),
    { fps: 15, source: 'filename', token: 'fps', value: 15 });
assert.deepEqual(SpriteTiming.resolveTiming({ fps: 9 }, { speed: 2 }),
    { fps: 9, source: 'key', token: 'fps', value: 9 });
assert.deepEqual(SpriteTiming.resolveTiming({ speed: 2 }, { speed: 3 }),
    { fps: 8, source: 'key', token: 'speed', value: 2 });
assert.deepEqual(SpriteTiming.resolveTiming({}, {}),
    { fps: 4, source: 'default', token: null, value: null });

function bench(fn, iterations) {
    for (let i = 0; i < 2000; i++) fn();
    const started = performance.now();
    for (let i = 0; i < iterations; i++) fn();
    return performance.now() - started;
}

const measurements = {
    node: process.version,
    generated_module_load_ms: generatedLoadMs,
    vertex_fractal_100k_ms: bench(() => Vertex.fractalNoise(1.25, 2.75, 1729), 100000),
    sprite_parse_and_rate_100k_ms: bench(() => {
        const parsed = SpriteTiming.parseKey('Pixie[speed=2][fps=15]');
        return SpriteTiming.effectiveFps(parsed.tokens);
    }, 100000),
};

console.log('SHARED SEMANTICS NODE CONFORMANCE OK');
console.log('MEASURE_SHARED_NODE ' + JSON.stringify(measurements));