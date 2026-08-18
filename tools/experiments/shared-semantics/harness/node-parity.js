'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { performance } = require('node:perf_hooks');

const Current = require('../../../editor/js/vertex-shading.js');
const generatedPath = path.join(__dirname, '..', 'generated', 'js', 'shared-semantics.js');
const generatedCode = fs.readFileSync(generatedPath, 'utf8');
vm.runInThisContext(generatedCode + '\n;globalThis.__THestraSpikeShared = ThestraSharedSemantics;', {
    filename: generatedPath
});
const Candidate = globalThis.__THestraSpikeShared;
delete globalThis.__THestraSpikeShared;

function close(actual, expected, epsilon = 1e-12, label = '') {
    assert.ok(Math.abs(actual - expected) <= epsilon,
        `${label}: expected ${expected}, got ${actual}`);
}

const pins = [
    ['hash01', [0, 0, 0], 0.9616300366300367],
    ['hash01', [1, 2, 1729], 0.18543956043956045],
    ['hash01', [-1, 0, 23], 0.6313644688644688],
    ['valueNoise', [0.5, 0.5, 1729], 0.42679334554334547],
    ['fractalNoise', [0.5, 0.5, 1729], 0.4540415838459217],
    ['fractalNoise', [1.25, 2.75, 1729], 0.45447714242048237],
    ['fractalNoise', [-0.25, 0.5, 23], 0.3765472024340493]
];

for (const [fn, args, expected] of pins) {
    const current = Current[fn](...args);
    const candidate = Candidate[fn](...args);
    close(current, expected, 1e-12, `current JS ${fn}`);
    close(candidate, expected, 1e-12, `generated JS ${fn}`);
    close(candidate, current, 1e-12, `generated-v-current JS ${fn}`);
}

const layer = {
    type: 'colorNoise',
    colorA: [0.88, 0.94, 0.90],
    colorB: [0.96, 0.88, 0.93],
    strength: 0.12,
    scale: 5,
    seed: 1729
};
const expectedSample = [0.9897950411471678, 0.9896537191396242, 0.9895731404301878];
const currentSample = Current.sample([layer], 2.5, 3.5);
const candidateSample = Candidate.sample([layer], 2.5, 3.5);
for (let channel = 0; channel < 3; channel++) {
    close(currentSample[channel], expectedSample[channel], 1e-12, `current JS sample ${channel}`);
    close(candidateSample[channel], currentSample[channel], 1e-12, `generated JS sample ${channel}`);
}

const invalid = [{
    type: 'colorNoise', colorA: [1, 1], colorB: [1, 1, 1],
    strength: 2, scale: 0, seed: 1.5
}];
const currentProblems = Current.validate(invalid, 'map demo vertexShadingLayers');
const candidateProblems = Candidate.validate(invalid, 'map demo vertexShadingLayers');
for (const term of ['colorA', 'strength', 'scale', 'seed']) {
    assert.ok(currentProblems.some(problem => problem.includes(term)), `current JS validation lost ${term}`);
    assert.ok(candidateProblems.some(problem => problem.includes(term)), `generated JS validation lost ${term}`);
}
assert.throws(() => Candidate.compile(invalid));

const files = [
    'assets/smallBattlers/Pixie[fps=15].png',
    'assets/system/Cursor.png'
];
function sprite(key, fps, source, token, pathValue = 'assets/smallBattlers/Pixie[fps=15].png') {
    const result = Candidate.resolveSpriteKey(key, files);
    assert.equal(result.resolved, true, `${key} should resolve`);
    assert.equal(result.path, pathValue, `${key} path`);
    assert.equal(result.timing.fps, fps, `${key} fps`);
    assert.equal(result.timing.source, source, `${key} source`);
    assert.equal(result.timing.token, token, `${key} token`);
    return result;
}
const inherited = sprite('pixie', 15, 'filename', 'fps');
assert.equal(inherited.filenameTokens.fps, 15);
const overridden = sprite('pixie[fps=9]', 9, 'key', 'fps');
assert.equal(overridden.keyTokens.fps, 9);
assert.equal(overridden.filenameTokens.fps, 15);
const crossPriority = sprite('pixie[speed=2]', 15, 'filename', 'fps');
assert.equal(crossPriority.keyTokens.speed, 2);
const pathDescription = Candidate.describeSpritePath('assets/smallBattlers/Pixie[fps=15].png');
assert.equal(pathDescription.timing.fps, 15);
assert.equal(pathDescription.timing.source, 'filename');
sprite('Cursor', 4, 'default', null, 'assets/system/Cursor.png');

function bench(fn, iterations) {
    for (let i = 0; i < 2000; i++) fn();
    const started = performance.now();
    for (let i = 0; i < iterations; i++) fn();
    return performance.now() - started;
}

function gridBench(api, width, height) {
    const compiled = api.compile([layer]);
    const result = [];
    const started = performance.now();
    for (let y = 0; y <= height; y++) {
        const row = [];
        for (let x = 0; x <= width; x++) row.push(api.sampleCompiled(compiled, x, y));
        result.push(row);
    }
    const elapsed = performance.now() - started;
    assert.equal(result.length, height + 1);
    assert.equal(result[0].length, width + 1);
    return elapsed;
}

const measurements = {
    node: process.version,
    generated_js_bytes: fs.statSync(generatedPath).size,
    current_js_fractal_100k_ms: bench(() => Current.fractalNoise(1.25, 2.75, 1729), 100000),
    generated_js_fractal_100k_ms: bench(() => Candidate.fractalNoise(1.25, 2.75, 1729), 100000),
    current_grid_map2_17x17_ms: gridBench(Current, 17, 17),
    generated_grid_map2_17x17_ms: gridBench(Candidate, 17, 17),
    current_grid_map3_23x23_ms: gridBench(Current, 23, 23),
    generated_grid_map3_23x23_ms: gridBench(Candidate, 23, 23),
    current_grid_128x128_ms: gridBench(Current, 128, 128),
    generated_grid_128x128_ms: gridBench(Candidate, 128, 128)
};

console.log('NODE PARITY OK');
console.log('MEASURE_NODE ' + JSON.stringify(measurements));
