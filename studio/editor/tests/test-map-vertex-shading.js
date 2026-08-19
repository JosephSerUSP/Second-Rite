'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const Shading = require('../js/vertex-shading.js');

function close(actual, expected, epsilon = 1e-12) {
    assert.ok(Math.abs(actual - expected) <= epsilon,
        `expected ${expected}, got ${actual}`);
}

test('vertex shading primitives and rotated fractal samples are pinned for Lua parity', () => {
    close(Shading.hash01(0, 0, 0), 0.9616300366300367);
    close(Shading.hash01(1, 2, 1729), 0.18543956043956045);
    close(Shading.hash01(-1, 0, 23), 0.6313644688644688);

    close(Shading.valueNoise(0.5, 0.5, 1729), 0.42679334554334547);
    close(Shading.fractalNoise(0.5, 0.5, 1729), 0.4540415838459217);
    close(Shading.fractalNoise(1.25, 2.75, 1729), 0.45447714242048237);
    close(Shading.fractalNoise(-0.25, 0.5, 23), 0.3765472024340493);
});

test('fractal field has substantial independent variation across both map axes', () => {
    const field = [];
    for (let y = 0; y < 8; y++) {
        const row = [];
        for (let x = 0; x < 8; x++) row.push(Shading.fractalNoise(x / 5, y / 5, 1729));
        field.push(row);
    }
    const rowRange = Math.max(...field[0]) - Math.min(...field[0]);
    const column = field.map(row => row[0]);
    const columnRange = Math.max(...column) - Math.min(...column);
    assert.ok(rowRange > 0.2, `expected visible X variation, got range ${rowRange}`);
    assert.ok(columnRange > 0.2, `expected visible Y variation, got range ${columnRange}`);
    assert.notDeepEqual(field[0], field[1], 'adjacent rows must not collapse to the same 1D trace');
    assert.notDeepEqual(field.map(row => row[0]), field.map(row => row[1]),
        'adjacent columns must not collapse to the same 1D trace');
});

test('colorNoise is neutral at strength zero and deterministic at authored strength', () => {
    const layer = {
        type: 'colorNoise',
        colorA: [0.88, 0.94, 0.90],
        colorB: [0.96, 0.88, 0.93],
        strength: 0,
        scale: 5,
        seed: 1729
    };
    assert.deepEqual(Shading.sample([layer], 2.5, 3.5), [1, 1, 1]);

    layer.strength = 0.12;
    const sample = Shading.sample([layer], 2.5, 3.5);
    close(sample[0], 0.9897950411471678);
    close(sample[1], 0.9896537191396242);
    close(sample[2], 0.9895731404301878);
    assert.deepEqual(Shading.sample([layer], 2.5, 3.5), sample);
});

test('multiple layers multiply and a seed change changes only the tint field', () => {
    const a = {
        type: 'colorNoise', colorA: [0.8, 0.9, 1], colorB: [1, 0.8, 0.9],
        strength: 0.25, scale: 4, seed: 7
    };
    const b = {
        type: 'colorNoise', colorA: [1, 0.95, 0.85], colorB: [0.9, 1, 0.95],
        strength: 0.2, scale: 9, seed: 31
    };
    const sa = Shading.sample([a], 3, 6);
    const sb = Shading.sample([b], 3, 6);
    const both = Shading.sample([a, b], 3, 6);
    for (let channel = 0; channel < 3; channel++) close(both[channel], sa[channel] * sb[channel]);

    const changed = Shading.sample([{ ...a, seed: 8 }], 3, 6);
    assert.notDeepEqual(changed, sa);
});

test('malformed authored layers fail loudly', () => {
    const invalid = [{
        type: 'colorNoise', colorA: [1, 1], colorB: [1, 1, 1],
        strength: 2, scale: 0, seed: 1.5
    }];
    const problems = Shading.validate(invalid, 'map demo vertexShadingLayers');
    assert.ok(problems.some(problem => problem.includes('colorA')));
    assert.ok(problems.some(problem => problem.includes('strength')));
    assert.ok(problems.some(problem => problem.includes('scale')));
    assert.ok(problems.some(problem => problem.includes('seed')));
    assert.throws(() => Shading.compile(invalid));
});
