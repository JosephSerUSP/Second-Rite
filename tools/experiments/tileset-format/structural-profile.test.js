'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const { cornerPolyline, extrude, contained, metrics } = require('./structural-profile');

const ROOT = path.resolve(__dirname, '../../..');
const fixture = JSON.parse(fs.readFileSync(
    path.join(ROOT, 'docs', 'experiments', 'tileset-format', 'structural-profile-candidate.json'),
    'utf8'
));

for (const id of ['square', 'chamfer_small', 'round_lowpoly']) {
    test(`${id} generated corner remains inside the logical solid footprint`, () => {
        const profile = fixture.profiles[id];
        const mesh = extrude(cornerPolyline(profile));
        assert.equal(contained(mesh.vertices), true);
    });
}

test('candidate profiles produce deliberately different low-poly topology', () => {
    const square = metrics(fixture.profiles.square);
    const chamfer = metrics(fixture.profiles.chamfer_small);
    const round = metrics(fixture.profiles.round_lowpoly);

    assert.deepEqual({ segments: square.segments, triangles: square.triangles }, { segments: 2, triangles: 4 });
    assert.deepEqual({ segments: chamfer.segments, triangles: chamfer.triangles }, { segments: 1, triangles: 2 });
    assert.deepEqual({ segments: round.segments, triangles: round.triangles }, { segments: 3, triangles: 6 });
    assert.equal(round.points, 4);
});

test('structural profile reuse is independent from surface identity', () => {
    const uses = fixture.paletteUses;
    assert.equal(uses.wet_stone_round.structuralProfile, 'round_lowpoly');
    assert.equal(uses.plaster_round.structuralProfile, 'round_lowpoly');
    assert.notEqual(uses.wet_stone_round.surface, uses.plaster_round.surface);

    assert.equal(uses.wet_stone_round.surface, uses.wet_stone_square.surface);
    assert.notEqual(uses.wet_stone_round.structuralProfile, uses.wet_stone_square.structuralProfile);
});

test('authored junction escape hatch remains distinct and has explicit precedence', () => {
    assert.equal(fixture.profiles.carved_exception.kind, 'authoredJunctions');
    assert.ok(fixture.profiles.carved_exception.outsideCorner);
    assert.deepEqual(fixture.resolution.precedence, [
        'authored junction override when explicitly present',
        'palette/profile-generated junction',
        'square structural default',
    ]);
});

test('print deterministic structural-profile metrics', () => {
    const evidence = {};
    for (const id of ['square', 'chamfer_small', 'round_lowpoly']) {
        evidence[id] = metrics(fixture.profiles[id]);
    }
    process.stdout.write(`\nSTRUCTURAL_PROFILE_EVIDENCE ${JSON.stringify(evidence)}\n`);
});
