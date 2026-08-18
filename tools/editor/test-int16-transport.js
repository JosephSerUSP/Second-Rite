// #736/#739 experiment: the quantized Int16 transport must be a transport, i.e.
// invisible to every consumer once decoded at the boundary.
const test = require('node:test');
const assert = require('node:assert/strict');
const adapter = require('./js/second-rite-editor-adapter.js');

const SCALES = { positions: 256, uvs: 4096, normals: 10000, colors: 4096 };

function encode(values, scale) {
    const bytes = [];
    for (const value of values) {
        let word = Math.round(value * scale);
        if (word < 0) word += 65536;
        bytes.push(word % 256, Math.floor(word / 256));
    }
    return { kind: 'int16-base64', count: values.length, base64: Buffer.from(bytes).toString('base64') };
}

function bundle(streams) {
    return {
        encoding: { kind: 'int16-base64', scales: SCALES },
        materials: [],
        surfaces: [{
            positions: encode(streams.positions, SCALES.positions),
            uvs: encode(streams.uvs, SCALES.uvs),
            normals: encode(streams.normals, SCALES.normals),
            colors: encode(streams.colors, SCALES.colors),
        }],
    };
}

test('decoded streams reproduce the values within the declared grid', () => {
    const source = {
        positions: [0, 13, -0.5, 13.020833333333334, 22.99609375],
        uvs: [0, 1, 0.50390625, 0.00390625],
        normals: [0, 1, -1, 0.7071],
        colors: [0, 1, 0.5, 0.25],
    };
    const decoded = adapter.decodeTransport(bundle(source));
    const surface = decoded.surfaces[0];
    for (const key of Object.keys(source)) {
        assert.equal(surface[key].length, source[key].length, `${key} length`);
        const tolerance = 0.5 / SCALES[key];
        for (let i = 0; i < source[key].length; i++) {
            assert.ok(Math.abs(surface[key][i] - source[key][i]) <= tolerance,
                `${key}[${i}] ${surface[key][i]} vs ${source[key][i]} exceeds ${tolerance}`);
        }
    }
    // The marker is consumed, so nothing downstream can branch on it.
    assert.equal(decoded.encoding, undefined);
});

test('negative and boundary values survive the sign round trip', () => {
    // Int16 is signed; the encoder offsets negatives by 65536 and the decoder
    // must invert exactly that, including at the extremes.
    const source = { positions: [-127, 127, -0.00390625], uvs: [0], normals: [-1, 1], colors: [0] };
    const surface = adapter.decodeTransport(bundle(source)).surfaces[0];
    assert.ok(Math.abs(surface.positions[0] + 127) <= 0.5 / SCALES.positions);
    assert.ok(Math.abs(surface.positions[1] - 127) <= 0.5 / SCALES.positions);
    assert.equal(Math.sign(surface.normals[0]), -1);
    assert.equal(Math.sign(surface.normals[1]), 1);
});

test('an unencoded bundle passes through untouched', () => {
    // The flag is off by default, so the ordinary float path must not be
    // rewritten or even copied.
    const plain = { materials: [], surfaces: [{ positions: [1, 2, 3], uvs: [], normals: [], colors: [] }] };
    const same = adapter.decodeTransport(plain);
    assert.equal(same, plain);
    assert.deepEqual(same.surfaces[0].positions, [1, 2, 3]);
});

test('a stream with no declared scale is refused rather than guessed', () => {
    const broken = bundle({ positions: [1], uvs: [0], normals: [0], colors: [0] });
    delete broken.encoding.scales.positions;
    assert.throws(() => adapter.decodeTransport(broken), /declares no scale for positions/);
});
